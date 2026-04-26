from __future__ import annotations

import importlib.util
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_telegram_token_redaction_does_not_expose_secret_suffix() -> None:
    module = load_module(ROOT / "scripts" / "system" / "telegram_alert_ops.py", "telegram_alert_ops_test")

    assert module.redacted_token("12345:secret-token") == "12345:***"
    assert "secret-token" not in module.redacted_token("12345:secret-token")


def test_telegram_inbound_command_classification() -> None:
    module = load_module(ROOT / "scripts" / "system" / "telegram_alert_ops.py", "telegram_alert_ops_command_test")

    assert module.classify_inbound_text("/ping")["kind"] == "ping"
    task = module.classify_inbound_text("/task check kaggle")
    assert task["kind"] == "task_request"
    assert task["summary"] == "check kaggle"
    implicit = module.classify_inbound_text("check the DIBBS letter")
    assert implicit["kind"] == "task_request"
    assert "DIBBS" in implicit["summary"]


def test_telegram_shell_like_text_is_still_only_a_task_request() -> None:
    module = load_module(ROOT / "scripts" / "system" / "telegram_alert_ops.py", "telegram_alert_ops_shell_gate_test")

    command = module.classify_inbound_text("/task run git status && delete temp files")

    assert command["kind"] == "task_request"
    assert "git status" in command["summary"]
    assert "shell" not in command
    assert "execute" not in command


def test_message_triplet_ledger_verifies_and_detects_tamper(tmp_path: Path) -> None:
    module = load_module(ROOT / "scripts" / "system" / "message_triplet_ledger.py", "message_triplet_ledger_test")
    ledger = tmp_path / "ledger.jsonl"

    first = module.append_record(ledger, {"sender": "human", "body": "hello"}, channel="telegram")
    second = module.append_record(
        ledger,
        {"sender": "ai", "body": "ack"},
        ack_payload={"message_id": 10},
        channel="telegram",
    )

    assert first["triplet"]["previous_hash"] == module.GENESIS_HASH
    assert first["tokenizers"]["tokenizer_a"]["name"] == "utf8_hex_bytes_v1"
    assert first["tokenizers"]["tokenizer_b"]["name"] == "canonical_word_shape_v1"
    assert len(first["tokenizer_pair_hash"]) == 64
    assert second["triplet"]["previous_hash"] == first["triplet"]["current_hash"]
    assert module.verify_records(module.read_records(ledger))["ok"] is True

    lines = ledger.read_text(encoding="utf-8").splitlines()
    tampered = lines[0].replace("hello", "hacked")
    ledger.write_text(tampered + "\n" + "\n".join(lines[1:]) + "\n", encoding="utf-8")

    result = module.verify_records(module.read_records(ledger))
    assert result["ok"] is False
    assert any(item["reason"] == "envelope_hash_mismatch" for item in result["failures"])


def test_telegram_owner_chat_gate() -> None:
    module = load_module(ROOT / "scripts" / "system" / "telegram_alert_ops.py", "telegram_alert_ops_gate_test")
    message = {"chat": {"id": 12345}, "text": "/ping"}

    assert module.is_authorized_message(message, "12345") is True
    assert module.is_authorized_message(message, "99999") is False


def test_dibbs_telegram_message_contains_no_phone_number(tmp_path: Path) -> None:
    module = load_module(
        ROOT / "scripts" / "system" / "dibbs_address_verification_reminder.py",
        "dibbs_address_verification_reminder_test",
    )

    out = module.write_telegram_message(tmp_path / "dibbs.txt")
    text = out.read_text(encoding="utf-8")

    assert "DIBBS reminder" in text
    assert "verification number privately" in text
    assert re.search(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", text) is None
