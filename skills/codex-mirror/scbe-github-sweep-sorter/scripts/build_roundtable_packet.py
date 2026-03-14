#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


ROLE_MAP = {
    "KO": "architecture-curator",
    "AV": "transport-discovery",
    "RU": "policy-governance",
    "CA": "implementation-engineer",
    "UM": "security-auditor",
    "DR": "schema-release-memory",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_work_packets(formation: str) -> list[dict[str, object]]:
    if formation == "tetrahedral":
        tongues = ["KO", "CA", "UM", "DR"]
    else:
        tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]

    return [
        {
            "tongue": tongue,
            "role": ROLE_MAP[tongue],
            "goal": "Fill in the goal for this role.",
            "allowed_paths": [],
            "blocked_paths": [],
            "done_criteria": [],
        }
        for tongue in tongues
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a roundtable sweep packet.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--formation", required=True)
    parser.add_argument("--quorum-required", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--risk", choices=["low", "medium", "high", "critical"], default="medium")
    parser.add_argument("--sender", default="codex")
    parser.add_argument("--recipient", default="claude")
    parser.add_argument("--ordered-attestation", action="store_true")
    args = parser.parse_args()

    packet = {
        "packet_id": f"{args.task_id}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        "created_at": utc_now(),
        "sender": args.sender,
        "recipient": args.recipient,
        "repo": args.repo,
        "branch": args.branch,
        "task_id": args.task_id,
        "formation": args.formation,
        "quorum_required": args.quorum_required,
        "ordered_attestation": args.ordered_attestation,
        "summary": args.summary,
        "risk": args.risk,
        "work_packets": default_work_packets(args.formation),
        "next_action": "Route through scbe-ai-to-ai-communication.",
        "proof": [],
    }
    print(json.dumps(packet, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
