#!/usr/bin/env python3
"""Route GitHub work into dual-side tentacle lanes with cross-talk packets.

Lane model:
1) webhook_lane: inbound GitHub events and page/webhook triggers
2) cli_lane: git/gh command execution tasks
3) codespaces_lane: cloud dev environment tasks and heavy CI/code actions

Usage:
    python scripts/system/github_dual_tentacle_router.py --event-type pull_request --task "triage pr #42"
    python scripts/system/github_dual_tentacle_router.py --event-file tmp/github_webhook.json
"""

from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
LANE_ROOT = REPO_ROOT / "artifacts" / "agent_comm" / "github_lanes"
WEBHOOK_LANE = LANE_ROOT / "webhook_lane.jsonl"
CLI_LANE = LANE_ROOT / "cli_lane.jsonl"
CODESPACES_LANE = LANE_ROOT / "codespaces_lane.jsonl"
CROSSTALK_LOG = LANE_ROOT / "cross_talk.jsonl"


@dataclass
class LanePacket:
    packet_id: str
    created_at: str
    sender: str
    recipient_lane: str
    intent: str
    status: str
    repo: str
    event_type: str
    task: str
    payload: dict[str, Any]
    next_action: str
    risk: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "created_at": self.created_at,
            "sender": self.sender,
            "recipient_lane": self.recipient_lane,
            "intent": self.intent,
            "status": self.status,
            "repo": self.repo,
            "event_type": self.event_type,
            "task": self.task,
            "payload": self.payload,
            "next_action": self.next_action,
            "risk": self.risk,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_event(path: str) -> dict[str, Any]:
    p = Path(path).expanduser().resolve()
    return json.loads(p.read_text(encoding="utf-8"))


def choose_lane(event_type: str, task: str) -> str:
    e = event_type.lower()
    t = task.lower()

    if any(k in t for k in ["codespace", "devcontainer", "ci", "build", "integration test", "e2e"]):
        return "codespaces_lane"
    if any(k in e for k in ["push", "pull_request", "issues", "discussion", "release", "workflow_run", "check_run"]):
        return "webhook_lane"
    if any(k in t for k in ["merge", "rebase", "cherry-pick", "branch", "commit", "gh ", "git "]):
        return "cli_lane"
    return "cli_lane"


def lane_path(lane: str) -> Path:
    if lane == "webhook_lane":
        return WEBHOOK_LANE
    if lane == "codespaces_lane":
        return CODESPACES_LANE
    return CLI_LANE


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Route GitHub tasks to dual-tentacle lanes.")
    parser.add_argument("--repo", default="SCBE-AETHERMOORE", help="Repo context label.")
    parser.add_argument("--sender", default="agent.orchestrator", help="Packet sender label.")
    parser.add_argument("--event-type", default="manual", help="GitHub event type or synthetic type.")
    parser.add_argument("--event-file", default="", help="Optional JSON webhook event payload file.")
    parser.add_argument("--task", default="", help="Human task summary.")
    parser.add_argument("--intent", default="handoff", help="Packet intent.")
    parser.add_argument("--status", default="in_progress", help="Packet status.")
    parser.add_argument("--risk", default="medium", choices=["low", "medium", "high"], help="Risk label.")
    args = parser.parse_args()

    payload: dict[str, Any] = {}
    if args.event_file:
        payload = load_event(args.event_file)
        if not args.task:
            args.task = f"handle {args.event_type} event"

    task = args.task.strip() or "triage github work item"
    lane = choose_lane(args.event_type, task)
    packet = LanePacket(
        packet_id=f"gh-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
        created_at=utc_now(),
        sender=args.sender,
        recipient_lane=lane,
        intent=args.intent,
        status=args.status,
        repo=args.repo,
        event_type=args.event_type,
        task=task,
        payload=payload,
        next_action=f"Process task in {lane} and emit ack packet.",
        risk=args.risk,
    )

    packet_dict = packet.to_dict()
    append_jsonl(lane_path(lane), packet_dict)

    # Cross-talk mirror so both sides see each packet.
    append_jsonl(
        CROSSTALK_LOG,
        {
            "created_at": packet.created_at,
            "packet_id": packet.packet_id,
            "from": args.sender,
            "to": lane,
            "repo": args.repo,
            "event_type": args.event_type,
            "task": task,
            "status": args.status,
            "risk": args.risk,
        },
    )

    print(json.dumps({"ok": True, "lane": lane, "packet_id": packet.packet_id, "path": str(lane_path(lane))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
