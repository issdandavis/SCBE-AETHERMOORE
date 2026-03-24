#!/usr/bin/env python3
"""Cross-talk reliability checker and repair utility.

Checks packet delivery across:
1) artifacts/agent_comm/<day>/*.json packet files
2) artifacts/agent_comm/github_lanes/cross_talk.jsonl bus
3) notes/_inbox.md
4) notes/_context.md
5) agents/codex.md

Optionally repairs missing mirrors.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKET_ROOT = REPO_ROOT / "artifacts" / "agent_comm"
LANE_PATH = PACKET_ROOT / "github_lanes" / "cross_talk.jsonl"
INBOX_PATH = REPO_ROOT / "notes" / "_inbox.md"
CONTEXT_PATH = REPO_ROOT / "notes" / "_context.md"
AGENT_CODEX_PATH = REPO_ROOT / "agents" / "codex.md"


@dataclass
class PacketIssue:
    packet_id: str
    packet_path: str
    missing_lane: bool
    missing_inbox: bool
    missing_context: bool
    missing_agent_codex: bool


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _today_yyyymmdd() -> str:
    return _utc_now().strftime("%Y%m%d")


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _ensure_header(path: Path, header: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(header.rstrip() + "\n", encoding="utf-8")


def _append_line(path: Path, line: str, *, header: str) -> None:
    _ensure_header(path, header)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")


def _iter_packet_paths(day: str) -> Iterable[Path]:
    day_dir = PACKET_ROOT / day
    if not day_dir.exists():
        return []
    return sorted(
        [
            p
            for p in day_dir.glob("*.json")
            if "monetization-swarm-status-" not in p.name and "crosstalk-reliability-report-" not in p.name
        ],
        key=lambda p: p.stat().st_mtime,
    )


def _read_packet(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Packet is not a JSON object: {path}")
    return data


def _read_lane_rows() -> List[Dict[str, Any]]:
    if not LANE_PATH.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for raw in LANE_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _packet_markdown_line(packet: Dict[str, Any], packet_path: Path) -> str:
    created_at = str(packet.get("created_at", ""))
    sender = str(packet.get("sender", "agent.unknown"))
    recipient = str(packet.get("recipient", "agent.unknown"))
    intent = str(packet.get("intent", "handoff"))
    status = str(packet.get("status", "in_progress"))
    task_id = str(packet.get("task_id", "UNSPECIFIED"))
    summary = str(packet.get("summary", "")).replace("\n", " ").strip()
    session_id = str(packet.get("session_id", "")).strip()
    codename = str(packet.get("codename", "")).strip()
    where = str(packet.get("where", "")).strip()
    why = str(packet.get("why", "")).strip()
    how = str(packet.get("how", "")).strip()

    prefix = f"- {created_at} "
    if session_id or codename:
        prefix += f"[{session_id or 'sess'}] [{codename or 'agent'}] "

    line = f"{prefix}{sender} -> {recipient} | {intent} | {status} | {task_id} | {summary}"
    if where:
        line += f" | where={where}"
    if why:
        line += f" | why={why}"
    if how:
        line += f" | how={how}"
    line += f" ({packet_path})"
    return line


def _has_packet_marker(text: str, packet: Dict[str, Any], packet_path: Path) -> bool:
    packet_id = str(packet.get("packet_id", "")).strip()
    marker_path = str(packet_path)
    if packet_id and packet_id in text:
        return True
    if marker_path in text:
        return True
    return False


def analyze_day(day: str) -> Tuple[List[PacketIssue], Dict[str, Any]]:
    lane_rows = _read_lane_rows()
    lane_ids = {str(row.get("packet_id", "")).strip() for row in lane_rows if row.get("packet_id")}

    inbox_text = _read_text(INBOX_PATH)
    context_text = _read_text(CONTEXT_PATH)
    codex_text = _read_text(AGENT_CODEX_PATH)

    issues: List[PacketIssue] = []
    packet_count = 0
    ack_count = 0
    for packet_path in _iter_packet_paths(day):
        packet = _read_packet(packet_path)
        packet_id = str(packet.get("packet_id", "")).strip()
        if not packet_id:
            continue
        packet_count += 1
        if str(packet.get("intent", "")).lower() == "ack":
            ack_count += 1

        issue = PacketIssue(
            packet_id=packet_id,
            packet_path=str(packet_path),
            missing_lane=packet_id not in lane_ids,
            missing_inbox=not _has_packet_marker(inbox_text, packet, packet_path),
            missing_context=not _has_packet_marker(context_text, packet, packet_path),
            missing_agent_codex=not _has_packet_marker(codex_text, packet, packet_path),
        )
        if issue.missing_lane or issue.missing_inbox or issue.missing_context or issue.missing_agent_codex:
            issues.append(issue)

    summary = {
        "day": day,
        "packet_count": packet_count,
        "ack_count": ack_count,
        "issues_count": len(issues),
        "issue_breakdown": {
            "missing_lane": sum(1 for i in issues if i.missing_lane),
            "missing_inbox": sum(1 for i in issues if i.missing_inbox),
            "missing_context": sum(1 for i in issues if i.missing_context),
            "missing_agent_codex": sum(1 for i in issues if i.missing_agent_codex),
        },
    }
    return issues, summary


def repair_issues(issues: List[PacketIssue]) -> Dict[str, int]:
    fixed = {
        "lane_appends": 0,
        "inbox_appends": 0,
        "context_appends": 0,
        "agent_codex_appends": 0,
    }

    for issue in issues:
        packet_path = Path(issue.packet_path)
        packet = _read_packet(packet_path)
        line = _packet_markdown_line(packet, packet_path)

        if issue.missing_lane:
            LANE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with LANE_PATH.open("a", encoding="utf-8") as lane:
                lane.write(json.dumps(packet, ensure_ascii=False) + "\n")
            fixed["lane_appends"] += 1

        if issue.missing_inbox:
            _append_line(INBOX_PATH, line, header="## AI-to-AI Packet Inbox")
            fixed["inbox_appends"] += 1

        if issue.missing_context:
            _append_line(CONTEXT_PATH, line, header="## AI-to-AI Packet")
            fixed["context_appends"] += 1

        if issue.missing_agent_codex:
            _append_line(AGENT_CODEX_PATH, line, header="## AI-to-AI Packet")
            fixed["agent_codex_appends"] += 1

    return fixed


def _issue_to_dict(issue: PacketIssue) -> Dict[str, Any]:
    return {
        "packet_id": issue.packet_id,
        "packet_path": issue.packet_path,
        "missing_lane": issue.missing_lane,
        "missing_inbox": issue.missing_inbox,
        "missing_context": issue.missing_context,
        "missing_agent_codex": issue.missing_agent_codex,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check and repair SCBE cross-talk reliability surfaces.")
    parser.add_argument("--day", default=_today_yyyymmdd(), help="UTC day folder in YYYYMMDD")
    parser.add_argument("--repair", action="store_true", help="Append missing entries to lane + note mirrors")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    issues, summary = analyze_day(args.day)
    repaired = {"lane_appends": 0, "inbox_appends": 0, "context_appends": 0, "agent_codex_appends": 0}
    if args.repair and issues:
        repaired = repair_issues(issues)

    report = {
        "generated_at": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": summary,
        "repair_mode": bool(args.repair),
        "repaired": repaired,
        "issues": [_issue_to_dict(i) for i in issues],
    }

    out_dir = PACKET_ROOT / args.day
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"crosstalk-reliability-report-{_utc_now().strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps({"ok": True, "report_path": str(out_path), "summary": summary, "repaired": repaired}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
