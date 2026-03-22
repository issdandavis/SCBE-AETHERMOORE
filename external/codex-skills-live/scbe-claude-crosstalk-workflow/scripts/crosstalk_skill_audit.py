#!/usr/bin/env python3
"""Audit and repair cross-talk packet delivery for Codex/Claude lanes."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
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


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=True) + "\n")


def append_note_line(path: Path, packet: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("# Inbox\n", encoding="utf-8")
    line = "- [{time}] {sender} -> {recipient} | {task} | {status} | {summary}".format(
        time=packet.get("created_at", utc_now_iso()),
        sender=packet.get("sender", "agent.unknown"),
        recipient=packet.get("recipient", "agent.unknown"),
        task=packet.get("task_id", "TASK"),
        status=packet.get("status", "in_progress"),
        summary=packet.get("summary", ""),
    )
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def build_note_signature(packet: dict[str, Any]) -> str:
    return "{sender} -> {recipient} | {task} | {status} | {summary}".format(
        sender=packet.get("sender", "agent.unknown"),
        recipient=packet.get("recipient", "agent.unknown"),
        task=packet.get("task_id", "TASK"),
        status=packet.get("status", "in_progress"),
        summary=packet.get("summary", ""),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit/repair cross-talk packet delivery")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--day", default=utc_day())
    parser.add_argument("--repair", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    day_dir = repo / "artifacts" / "agent_comm" / args.day
    lane_path = repo / "artifacts" / "agent_comm" / "github_lanes" / "cross_talk.jsonl"
    inbox_path = repo / "notes" / "_inbox.md"

    packets: list[dict[str, Any]] = []
    for path in sorted(day_dir.glob("cross-talk-*.json")):
        obj = read_json(path, {})
        if isinstance(obj, dict):
            obj.setdefault("_path", str(path))
            packets.append(obj)

    lane_rows = read_jsonl(lane_path)
    lane_ids = {str(row.get("packet_id", "")).strip() for row in lane_rows if isinstance(row, dict)}

    inbox_text = inbox_path.read_text(encoding="utf-8", errors="replace") if inbox_path.exists() else ""

    missing_lane: list[dict[str, Any]] = []
    missing_notes: list[dict[str, Any]] = []

    for packet in packets:
        packet_id = str(packet.get("packet_id", "")).strip()
        if not packet_id:
            continue
        if packet_id not in lane_ids:
            missing_lane.append(packet)
        signature = build_note_signature(packet)
        if signature not in inbox_text:
            missing_notes.append(packet)

    repaired_lane = 0
    repaired_notes = 0

    if args.repair:
        for packet in missing_lane:
            append_jsonl(lane_path, packet)
            repaired_lane += 1
        for packet in missing_notes:
            append_note_line(inbox_path, packet)
            repaired_notes += 1

    report = {
        "generated_at": utc_now_iso(),
        "repo_root": str(repo),
        "day": args.day,
        "packet_count": len(packets),
        "missing_lane_entries": len(missing_lane),
        "missing_notes_entries": len(missing_notes),
        "repaired_lane_entries": repaired_lane,
        "repaired_notes_entries": repaired_notes,
        "missing_lane_packet_ids": [str(p.get("packet_id", "")) for p in missing_lane],
        "missing_notes_packet_ids": [str(p.get("packet_id", "")) for p in missing_notes],
        "lane_path": str(lane_path),
        "inbox_path": str(inbox_path),
    }

    out_dir = day_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / ("crosstalk-skill-report-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps({"ok": True, "report": str(out_path), **report}, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
