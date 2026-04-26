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
