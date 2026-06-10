import json
import subprocess
import sys
from pathlib import Path

from scbe_polly_pad import append_event, export_ledger, verify_ledger


def test_audit_receipts_hash_chain_and_export(tmp_path):
    ledger = tmp_path / "audit.jsonl"

    first = append_event(ledger, actor="human", action="init", subject="pad")
    second = append_event(ledger, actor="polly", action="note.add", subject="video", payload={"title": "demo"})

    assert second.prev_hash == first.event_hash
    verified = verify_ledger(ledger)
    assert verified.ok is True
    assert verified.count == 2
    assert verified.head_hash == second.event_hash

    exported = export_ledger(ledger)
    assert exported["ok"] is True
    assert exported["events"][1]["payload"]["title"] == "demo"


def test_audit_verify_detects_tampering(tmp_path):
    ledger = tmp_path / "audit.jsonl"
    append_event(ledger, actor="human", action="init", subject="pad")

    line = ledger.read_text(encoding="utf-8").strip()
    event = json.loads(line)
    event["subject"] = "tampered"
    ledger.write_text(json.dumps(event, sort_keys=True) + "\n", encoding="utf-8")

    verified = verify_ledger(ledger)
    assert verified.ok is False
    assert verified.broken_at == 1
    assert verified.reason == "event hash mismatch"


def test_cli_audit_append_list_verify(tmp_path):
    ledger = tmp_path / "audit.jsonl"
    append_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scbe_polly_pad",
            "audit",
            "append",
            "--ledger",
            str(ledger),
            "--actor",
            "human",
            "--action",
            "task.add",
            "--subject",
            "youtube",
            "--payload-json",
            '{"step":"title"}',
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    receipt = json.loads(append_result.stdout)
    assert receipt["actor"] == "human"

    list_result = subprocess.run(
        [sys.executable, "-m", "scbe_polly_pad", "audit", "list", "--ledger", str(ledger)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(list_result.stdout)[0]["payload"]["step"] == "title"

    verify_result = subprocess.run(
        [sys.executable, "-m", "scbe_polly_pad", "audit", "verify", "--ledger", str(ledger)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(verify_result.stdout)["ok"] is True


def test_cli_audit_verify_returns_nonzero_on_tamper(tmp_path):
    ledger = Path(tmp_path / "audit.jsonl")
    append_event(ledger, actor="human", action="init", subject="pad")
    ledger.write_text(ledger.read_text(encoding="utf-8").replace('"pad"', '"changed"'), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "scbe_polly_pad", "audit", "verify", "--ledger", str(ledger)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["ok"] is False
