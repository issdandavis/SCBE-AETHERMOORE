#!/usr/bin/env python3
"""Map action vector Z -> workflow plan.

Supports binary and weighted vectors.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from typing import Dict, List

ACTIONS = [
    "notion_sync",
    "obsidian_snapshot",
    "git_commit",
    "dropbox_backup",
    "zapier_emit",
]


def workflow_from_z(z: List[float], threshold: float = 0.5) -> Dict:
    if len(z) != len(ACTIONS):
        raise ValueError(f"Z must have length {len(ACTIONS)}")

    enabled = {}
    for i, action in enumerate(ACTIONS):
        enabled[action] = float(z[i]) >= threshold

    active = [a for a in ACTIONS if enabled[a]]
    signature_src = json.dumps({"z": z, "threshold": threshold, "active": active}, separators=(",", ":"))
    signature = hashlib.sha256(signature_src.encode("utf-8")).hexdigest()[:16]

    return {
        "z": z,
        "threshold": threshold,
        "enabled": enabled,
        "active": active,
        "workflow_signature": signature,
    }


def parse_z(raw: str) -> List[float]:
    vals = [x.strip() for x in raw.split(",") if x.strip()]
    return [float(x) for x in vals]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--z", required=True, help="comma-separated vector, e.g. 1,1,0,1,0")
    p.add_argument("--threshold", type=float, default=0.5)
    args = p.parse_args()

    z = parse_z(args.z)
    out = workflow_from_z(z, threshold=args.threshold)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
