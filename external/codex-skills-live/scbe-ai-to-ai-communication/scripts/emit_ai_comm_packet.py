#!/usr/bin/env python
"""Emit an SCBE AI-to-AI communication packet."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


def to_iso(ts: datetime | None = None) -> str:
    return (ts or datetime.now(timezone.utc)).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--sender", required=True)
    p.add_argument("--recipient", required=True)
    p.add_argument("--intent", required=True)
    p.add_argument("--status", default="in_progress", choices=["in_progress", "blocked", "done"])
    p.add_argument("--task-id", dest="task_id", default="")
    p.add_argument("--summary", required=True)
    p.add_argument("--proof", nargs="*", default=[])
    p.add_argument("--next-action", dest="next_action", default="")
    p.add_argument("--risk", default="low", choices=["low", "medium", "high"])
    p.add_argument("--repo", default="SCBE-AETHERMOORE")
    p.add_argument("--branch", default="clean-sync")
    p.add_argument("--packet-id", default="")
    p.add_argument("--out-dir", default=str(Path.home() / "OneDrive" / "Dropbox" / "SCBE-AI-Comm" / "packets"))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    packet_id = args.packet_id or f"a2a-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
    payload = {
        "packet_id": packet_id,
        "created_at": to_iso(),
        "sender": args.sender,
        "recipient": args.recipient,
        "intent": args.intent,
        "status": args.status,
        "repo": args.repo,
        "branch": args.branch,
        "task_id": args.task_id,
        "summary": args.summary,
        "proof": args.proof,
        "next_action": args.next_action,
        "risk": args.risk,
        "gates": {
            "governance_packet": True,
            "has_proof": bool(args.proof),
        },
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{packet_id}.json"
    out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(out_file)


if __name__ == "__main__":
    main()
