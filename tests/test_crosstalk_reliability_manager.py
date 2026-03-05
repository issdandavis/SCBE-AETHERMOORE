import json
from pathlib import Path
import shutil
import uuid

from scripts.system import crosstalk_reliability_manager as crm


def _write_packet(path: Path, packet_id: str) -> None:
    payload = {
        "packet_id": packet_id,
        "created_at": "2026-03-04T03:00:00Z",
        "sender": "agent.codex",
        "recipient": "agent.claude",
        "intent": "handoff",
        "status": "in_progress",
        "repo": "SCBE-AETHERMOORE",
        "branch": "clean-sync",
        "task_id": "TEST-TASK",
        "summary": "test summary",
        "proof": [],
        "next_action": "ack",
        "risk": "low",
        "where": "terminal",
        "why": "test",
        "how": "test",
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _repo_local_tmp_root() -> Path:
    base = crm.REPO_ROOT / "artifacts" / "test_tmp_crosstalk"
    root = base / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_analyze_day_detects_missing_surfaces(monkeypatch) -> None:
    tmp_path = _repo_local_tmp_root()
    try:
        day = "20260304"
        packet_root = tmp_path / "artifacts" / "agent_comm"
        packet_dir = packet_root / day
        packet_dir.mkdir(parents=True)
        packet_path = packet_dir / "packet.json"
        _write_packet(packet_path, "pkt-1")

        lane_path = packet_root / "github_lanes" / "cross_talk.jsonl"
        inbox_path = tmp_path / "notes" / "_inbox.md"
        context_path = tmp_path / "notes" / "_context.md"
        agent_codex_path = tmp_path / "agents" / "codex.md"

        monkeypatch.setattr(crm, "PACKET_ROOT", packet_root)
        monkeypatch.setattr(crm, "LANE_PATH", lane_path)
        monkeypatch.setattr(crm, "INBOX_PATH", inbox_path)
        monkeypatch.setattr(crm, "CONTEXT_PATH", context_path)
        monkeypatch.setattr(crm, "AGENT_CODEX_PATH", agent_codex_path)

        issues, summary = crm.analyze_day(day)
        assert summary["packet_count"] == 1
        assert len(issues) == 1
        assert issues[0].missing_lane is True
        assert issues[0].missing_inbox is True
        assert issues[0].missing_context is True
        assert issues[0].missing_agent_codex is True
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_repair_issues_appends_all_missing_surfaces(monkeypatch) -> None:
    tmp_path = _repo_local_tmp_root()
    try:
        day = "20260304"
        packet_root = tmp_path / "artifacts" / "agent_comm"
        packet_dir = packet_root / day
        packet_dir.mkdir(parents=True)
        packet_path = packet_dir / "packet.json"
        _write_packet(packet_path, "pkt-2")

        lane_path = packet_root / "github_lanes" / "cross_talk.jsonl"
        inbox_path = tmp_path / "notes" / "_inbox.md"
        context_path = tmp_path / "notes" / "_context.md"
        agent_codex_path = tmp_path / "agents" / "codex.md"

        monkeypatch.setattr(crm, "PACKET_ROOT", packet_root)
        monkeypatch.setattr(crm, "LANE_PATH", lane_path)
        monkeypatch.setattr(crm, "INBOX_PATH", inbox_path)
        monkeypatch.setattr(crm, "CONTEXT_PATH", context_path)
        monkeypatch.setattr(crm, "AGENT_CODEX_PATH", agent_codex_path)

        issues, _summary = crm.analyze_day(day)
        repaired = crm.repair_issues(issues)
        assert repaired["lane_appends"] == 1
        assert repaired["inbox_appends"] == 1
        assert repaired["context_appends"] == 1
        assert repaired["agent_codex_appends"] == 1

        assert "pkt-2" in lane_path.read_text(encoding="utf-8")
        assert "TEST-TASK" in inbox_path.read_text(encoding="utf-8")
        assert "TEST-TASK" in context_path.read_text(encoding="utf-8")
        assert "TEST-TASK" in agent_codex_path.read_text(encoding="utf-8")
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
