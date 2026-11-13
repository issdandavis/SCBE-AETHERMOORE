"""Run the preregistered paired concept-orbit data campaign."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.clay_paired_orbit_training import (  # noqa: E402
    ClaySourceAdapter,
    run_campaign,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--clay-source-dir", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=(11, 29, 47))
    parser.add_argument("--held-sectors", type=int, nargs="+", default=(1, 4, 7))
    parser.add_argument("--orbit-count", type=int, default=2666)
    parser.add_argument("--evaluation-records", type=int, default=1000)
    parser.add_argument("--steps", type=int, default=1200)
    parser.add_argument("--batch-size", type=int, default=192)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--weight-decay", type=float, default=0.0001)
    parser.add_argument("--log-every", type=int, default=100)
    parser.add_argument("--hidden-width", type=int, default=64)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    provider = ClaySourceAdapter(args.clay_source_dir)
    result = run_campaign(
        args.output,
        provider,
        seeds=tuple(args.seeds),
        held_sectors=tuple(args.held_sectors),
        orbit_count=args.orbit_count,
        evaluation_records=args.evaluation_records,
        steps=args.steps,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        log_every=args.log_every,
        hidden_width=args.hidden_width,
        device_name=args.device,
    )
    print(
        json.dumps(
            {
                "state": result["state"],
                "verdict": result["aggregate"]["verdict"],
                "result_sha256": result["result_sha256"],
                "promotion_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
