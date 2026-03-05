from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


def _load_relay_module():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "system" / "crosstalk_relay.py"
    spec = importlib.util.spec_from_file_location("crosstalk_relay_module", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load relay module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_emit_defaults_without_required_args(monkeypatch):
    relay = _load_relay_module()
    captured: dict[str, Any] = {}

    def fake_emit_packet(**kwargs):
        captured.update(kwargs)
        return {
            "packet_id": "test-packet",
            "all_delivered": True,
            "lanes": {"dated_json": {"ok": True}},
        }

    monkeypatch.setattr(relay, "emit_packet", fake_emit_packet)
    monkeypatch.setattr(sys, "argv", ["crosstalk_relay.py", "emit", "--summary", "quick note"])

    relay.main()

    assert captured["sender"] == "agent.codex"
    assert captured["recipient"] == "agent.claude"
    assert captured["task_id"] == "NOTE"
    assert captured["summary"] == "quick note"


def test_emit_uses_env_defaults(monkeypatch):
    relay = _load_relay_module()
    captured: dict[str, Any] = {}

    def fake_emit_packet(**kwargs):
        captured.update(kwargs)
        return {
            "packet_id": "test-packet",
            "all_delivered": True,
            "lanes": {"dated_json": {"ok": True}},
        }

    monkeypatch.setattr(relay, "emit_packet", fake_emit_packet)
    monkeypatch.setenv("SCBE_CROSSTALK_SENDER", "agent.envsender")
    monkeypatch.setenv("SCBE_CROSSTALK_RECIPIENT", "agent.envrecipient")
    monkeypatch.setenv("SCBE_CROSSTALK_TASK_ID", "ENV-TASK")
    monkeypatch.setenv("SCBE_CROSSTALK_SUMMARY", "env summary")
    monkeypatch.setattr(sys, "argv", ["crosstalk_relay.py", "emit"])

    relay.main()

    assert captured["sender"] == "agent.envsender"
    assert captured["recipient"] == "agent.envrecipient"
    assert captured["task_id"] == "ENV-TASK"
    assert captured["summary"] == "env summary"


def test_emit_explicit_values_override_env(monkeypatch):
    relay = _load_relay_module()
    captured: dict[str, Any] = {}

    def fake_emit_packet(**kwargs):
        captured.update(kwargs)
        return {
            "packet_id": "test-packet",
            "all_delivered": True,
            "lanes": {"dated_json": {"ok": True}},
        }

    monkeypatch.setattr(relay, "emit_packet", fake_emit_packet)
    monkeypatch.setenv("SCBE_CROSSTALK_SENDER", "agent.envsender")
    monkeypatch.setenv("SCBE_CROSSTALK_RECIPIENT", "agent.envrecipient")
    monkeypatch.setenv("SCBE_CROSSTALK_TASK_ID", "ENV-TASK")
    monkeypatch.setenv("SCBE_CROSSTALK_SUMMARY", "env summary")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "crosstalk_relay.py",
            "emit",
            "--sender",
            "agent.cli",
            "--recipient",
            "agent.other",
            "--task-id",
            "CLI-TASK",
            "--summary",
            "cli summary",
        ],
    )

    relay.main()

    assert captured["sender"] == "agent.cli"
    assert captured["recipient"] == "agent.other"
    assert captured["task_id"] == "CLI-TASK"
    assert captured["summary"] == "cli summary"
