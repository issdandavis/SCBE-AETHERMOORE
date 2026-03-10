from __future__ import annotations

import importlib.util
from argparse import Namespace
from pathlib import Path


def _load_ops_control_module():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "system" / "ops_control.py"
    spec = importlib.util.spec_from_file_location("ops_control_module", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load ops_control from {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_packet_keeps_extended_metadata():
    ops = _load_ops_control_module()
    args = Namespace(
        from_agent="codex",
        to="claude",
        intent="handoff",
        status="done",
        summary="Integrated HallPass guidance.",
        artifacts="src/fleet/hallpass.py,tests/test_hallpass.py",
        next_action="Verify dispatch",
        task_id="HALLPASS-GUIDANCE",
        risk="low",
        where="terminal",
        why="routing",
        how="patch+tests",
        session_id="sess-123",
        codename="Positive-Angel",
    )

    packet = ops.build_packet(args)

    assert packet["from"] == "agent.codex"
    assert packet["to"] == "agent.claude"
    assert packet["task_id"] == "HALLPASS-GUIDANCE"
    assert packet["risk"] == "low"
    assert packet["where"] == "terminal"
    assert packet["why"] == "routing"
    assert packet["how"] == "patch+tests"
    assert packet["session_id"] == "sess-123"
    assert packet["codename"] == "Positive-Angel"
    assert packet["artifacts"] == ["src/fleet/hallpass.py", "tests/test_hallpass.py"]


def test_write_obsidian_includes_packet_id_and_metadata(tmp_path):
    ops = _load_ops_control_module()
    workspace = tmp_path / "Agent Ops"
    workspace.mkdir(parents=True)
    packet = {
        "packet_id": "pkt-1",
        "created_at": "2026-03-09T22:11:12Z",
        "from": "agent.codex",
        "to": "agent.claude",
        "intent": "handoff",
        "status": "done",
        "summary": "Cross-talk repaired.",
        "artifacts": ["scripts/system/ops_control.py"],
        "next": "Run health checks",
        "task_id": "CROSSTALK",
        "where": "terminal",
        "why": "sync",
        "how": "ops_control",
    }

    ok, detail = ops.write_obsidian(packet, workspace_override=str(workspace))

    assert ok is True
    cross_talk_path = Path(detail)
    content = cross_talk_path.read_text(encoding="utf-8")
    assert "pkt-1" in content
    assert "- where: terminal" in content
    assert "- why: sync" in content
    assert "- how: ops_control" in content


def test_write_agent_log_records_packet_id(tmp_path, monkeypatch):
    ops = _load_ops_control_module()
    monkeypatch.setattr(ops, "AGENTS_DIR", tmp_path / "agents")
    packet = {
        "packet_id": "pkt-2",
        "created_at": "2026-03-09T22:11:12Z",
        "from": "agent.codex",
        "to": "agent.claude",
        "intent": "sync",
        "status": "done",
        "summary": "Logged to agent file.",
        "artifacts": [],
    }

    ok, detail = ops.write_agent_log(packet)

    assert ok is True
    agent_log = ops.REPO_ROOT / detail
    content = agent_log.read_text(encoding="utf-8")
    assert "packet_id=pkt-2" in content
