#!/usr/bin/env python3
"""Build a non-launchable four-lane action-data staging manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.frozen_action_material_manifest import (
    build_frozen_action_material_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", required=True, type=Path)
    parser.add_argument("--admission-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--minimum-free-gib", type=float, default=25.0)
    args = parser.parse_args()
    receipt = build_frozen_action_material_manifest(
        candidate_dir=args.candidate_dir,
        admission_dir=args.admission_dir,
        output_dir=args.output,
        minimum_free_gib=args.minimum_free_gib,
    )
    print(
        json.dumps(
            {
                "counts": receipt["counts"],
                "output": str(args.output.resolve()),
                "status": receipt["status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
