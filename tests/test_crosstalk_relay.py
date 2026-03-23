from __future__ import annotations

import importlib.util
import json
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


def test_resolve_obsidian_workspace_from_desktop_config(tmp_path, monkeypatch):
    vault = tmp_path / "Avalon Files"
    vault.mkdir()
    appdata = tmp_path / "AppData" / "Roaming"
    config_dir = appdata / "Obsidian"
    config_dir.mkdir(parents=True)
    (config_dir / "obsidian.json").write_text(
        json.dumps({"vaults": {"live": {"path": str(vault), "open": True}}}),
        encoding="utf-8",
    )

    monkeypatch.delenv("OBSIDIAN_WORKSPACE", raising=False)
    monkeypatch.setenv("APPDATA", str(appdata))

    relay = _load_relay_module()

    assert relay._resolve_obsidian_workspace() == vault
    assert relay._resolve_obsidian_crosstalk() == vault / "Cross Talk.md"


def test_emit_packet_creates_cross_talk_note_in_resolved_vault(tmp_path, monkeypatch):
    vault = tmp_path / "Avalon Files"
    vault.mkdir()
    appdata = tmp_path / "AppData" / "Roaming"
    config_dir = appdata / "Obsidian"
    config_dir.mkdir(parents=True)
    (config_dir / "obsidian.json").write_text(
        json.dumps({"vaults": {"live": {"path": str(vault), "open": True}}}),
        encoding="utf-8",
    )

    monkeypatch.delenv("OBSIDIAN_WORKSPACE", raising=False)
    monkeypatch.setenv("APPDATA", str(appdata))

    relay = _load_relay_module()
    monkeypatch.setattr(relay, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        relay,
        "CROSSTALK_LANE",
        tmp_path / "artifacts" / "agent_comm" / "github_lanes" / "cross_talk.jsonl",
    )
    monkeypatch.setattr(
        relay,
        "ACK_LANE",
        tmp_path / "artifacts" / "agent_comm" / "github_lanes" / "cross_talk_acks.jsonl",
    )

    result = relay.emit_packet(
        sender="agent.codex",
        recipient="agent.claude",
        intent="sync",
        task_id="OBSIDIAN-LIVE",
        summary="Exercise live vault fallback.",
        next_action="Verify packet on all lanes.",
    )

    note_path = vault / "Cross Talk.md"
    content = note_path.read_text(encoding="utf-8")

    assert result["all_delivered"] is True
    assert result["lanes"]["obsidian"]["ok"] is True
    assert note_path.exists()
    assert "Packet ID" in content
    assert result["packet_id"] in content


def test_emit_packet_persists_parallel_browser_metadata(tmp_path, monkeypatch):
    vault = tmp_path / "Avalon Files"
    vault.mkdir()
    appdata = tmp_path / "AppData" / "Roaming"
    config_dir = appdata / "Obsidian"
    config_dir.mkdir(parents=True)
    (config_dir / "obsidian.json").write_text(
        json.dumps({"vaults": {"live": {"path": str(vault), "open": True}}}),
        encoding="utf-8",
    )

    monkeypatch.delenv("OBSIDIAN_WORKSPACE", raising=False)
    monkeypatch.setenv("APPDATA", str(appdata))

    relay = _load_relay_module()
    monkeypatch.setattr(relay, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        relay,
        "CROSSTALK_LANE",
        tmp_path / "artifacts" / "agent_comm" / "github_lanes" / "cross_talk.jsonl",
    )
    monkeypatch.setattr(
        relay,
        "ACK_LANE",
        tmp_path / "artifacts" / "agent_comm" / "github_lanes" / "cross_talk_acks.jsonl",
    )

    result = relay.emit_packet(
        sender="agent.codex",
        recipient="agent.claude",
        intent="swarm_sync",
        task_id="HYDRA-LATTICE",
        summary="Emit four-rail packet.",
        packet_class="governance",
        mission_id="mission-hydra-01",
        worker_id="worker-colab-01",
        lease={"provider": "colab", "resource_class": "t4", "lease_seconds": 1800},
        rails={
            "P+": [{"type": "action", "action": "navigate", "target": "https://example.com"}],
            "P-": [{"type": "blocked_actions", "count": 1}],
            "D+": [{"type": "decision", "value": "QUARANTINE"}],
            "D-": [{"type": "antivirus_turnstile", "action": "HOLD"}],
        },
        layer14={"energy": 0.75, "flux": 0.25, "stability": 0.8, "channel": "layer14-comms"},
    )

    packet_path = Path(result["lanes"]["dated_json"]["path"])
    packet = json.loads(packet_path.read_text(encoding="utf-8"))

    assert result["packet_class"] == "governance"
    assert result["mission_id"] == "mission-hydra-01"
    assert result["worker_id"] == "worker-colab-01"
    assert packet["lease"]["provider"] == "colab"
    assert packet["rails"]["P+"][0]["action"] == "navigate"
    assert packet["rails"]["D-"][0]["action"] == "HOLD"
    assert packet["layer14"]["channel"] == "layer14-comms"
    assert packet["ledger"]["packet_class"] == "governance"
    assert packet["ledger"]["integrity_hint"] == packet["_integrity"]
