#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json


def choose_formation(
    repo_count: int,
    item_count: int,
    risk: str,
    shared_files: int,
    needs_ordering: bool,
    needs_discovery: bool,
) -> dict[str, object]:
    if needs_ordering or risk == "critical":
        formation = "ring"
    elif needs_discovery or repo_count > 1 or item_count > 20:
        formation = "scatter"
    elif shared_files > 0 and item_count <= 6 and risk in {"medium", "high"}:
        formation = "tetrahedral"
    else:
        formation = "hexagonal-ring"

    quorum = {
        "low": "3/6",
        "medium": "4/6",
        "high": "4/6",
        "critical": "5/6",
    }[risk]

    return {
        "formation": formation,
        "quorum_required": quorum,
        "ordered_attestation": formation == "ring",
        "rationale": {
            "repo_count": repo_count,
            "item_count": item_count,
            "risk": risk,
            "shared_files": shared_files,
            "needs_ordering": needs_ordering,
            "needs_discovery": needs_discovery,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Choose a HYDRA formation for a GitHub or repo sweep.")
    parser.add_argument("--repo-count", type=int, default=1)
    parser.add_argument("--item-count", type=int, default=1)
    parser.add_argument("--risk", choices=["low", "medium", "high", "critical"], default="medium")
    parser.add_argument("--shared-files", type=int, default=0)
    parser.add_argument("--needs-ordering", action="store_true")
    parser.add_argument("--needs-discovery", action="store_true")
    args = parser.parse_args()

    print(json.dumps(
        choose_formation(
            repo_count=args.repo_count,
            item_count=args.item_count,
            risk=args.risk,
            shared_files=args.shared_files,
            needs_ordering=args.needs_ordering,
            needs_discovery=args.needs_discovery,
        ),
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
