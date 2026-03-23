#!/usr/bin/env python3
"""Emit Claude/Codex cross-talk packet for 7th Tongue Lore RAG runs."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Emit lore-rag cross-talk packet.")
    parser.add_argument("--repo-root", default="C:/Users/issda/SCBE-AETHERMOORE")
    parser.add_argument("--sender", default="agent.codex")
    parser.add_argument("--recipient", default="agent.claude")
    parser.add_argument("--task-id", default="LORE-RAG-7TH-TONGUE")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--status", default="in_progress")
    parser.add_argument("--next-action", default="")
    parser.add_argument("--where", default="world-anvil-rag")
    parser.add_argument("--why", default="sync lore canon retrieval and generation lanes")
    parser.add_argument("--how", default="index-build -> query -> citation-gated generation")
    parser.add_argument("--risk", default="low")
    parser.add_argument("--session-id", default="")
    parser.add_argument("--codename", default="seven-tongue")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    day_dir = repo_root / "artifacts" / "agent_comm" / datetime.now(timezone.utc).strftime("%Y%m%d")
    lane_file = repo_root / "artifacts" / "agent_comm" / "github_lanes" / "cross_talk.jsonl"
    inbox_file = repo_root / "notes" / "_inbox.md"

    day_dir.mkdir(parents=True, exist_ok=True)
    lane_file.parent.mkdir(parents=True, exist_ok=True)
    inbox_file.parent.mkdir(parents=True, exist_ok=True)
    if not inbox_file.exists():
        inbox_file.write_text("# Cross-Talk Inbox\n\n", encoding="utf-8")

    session_id = args.session_id or uuid.uuid4().hex
    packet_id = f"cross-talk-{args.sender}-{args.task_id.lower()}-{utc_stamp()}"
    packet = {
        "packet_id": packet_id,
        "session_id": session_id,
        "codename": args.codename,
        "created_at": utc_now(),
        "sender": args.sender,
        "recipient": args.recipient,
        "task_id": args.task_id,
        "summary": args.summary,
        "status": args.status,
        "next_action": args.next_action,
        "where": args.where,
        "why": args.why,
        "how": args.how,
        "risk": args.risk,
        "proof": [],
    }

    packet_path = day_dir / f"{packet_id}.json"
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    with lane_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(packet, ensure_ascii=False) + "\n")

    inbox_line = (
        f"- [{packet['created_at']}] {packet['sender']} -> {packet['recipient']} | {packet['task_id']} | "
        f"{packet['status']} | {packet['summary']}\n"
    )
    with inbox_file.open("a", encoding="utf-8") as f:
        f.write(inbox_line)

    print(
        json.dumps(
            {
                "ok": True,
                "packet": str(packet_path),
                "lane": str(lane_file),
                "inbox": str(inbox_file),
                "packet_id": packet_id,
                "session_id": session_id,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
