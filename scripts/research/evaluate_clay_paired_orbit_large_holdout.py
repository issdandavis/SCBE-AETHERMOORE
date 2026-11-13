"""Evaluate saved paired-orbit weights on a larger independent holdout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.clay_paired_orbit_evaluation import (  # noqa: E402
    evaluate_saved_campaign,
)
from python.scbe.clay_paired_orbit_training import ClaySourceAdapter  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--clay-source-dir", type=Path, required=True)
    parser.add_argument("--records", type=int, default=10_000)
    parser.add_argument("--seed-offset", type=int, default=500_000)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = evaluate_saved_campaign(
        args.run_root,
        ClaySourceAdapter(args.clay_source_dir),
        records=args.records,
        seed_offset=args.seed_offset,
        device_name=args.device,
    )
    print(
        json.dumps(
            {
                "state": "COMPLETE_DIAGNOSTIC_NO_PROMOTION",
                "diagnostic_sha256": report["diagnostic_sha256"],
                "promotion_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
