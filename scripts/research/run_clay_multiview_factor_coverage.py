"""Run the preregistered Clay multi-view factor-coverage campaign."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.clay_multiview_factor_coverage import (  # noqa: E402
    ARMS,
    CONTROLS,
    PRIMARY_ARM,
    run_factor_campaign,
)
from python.scbe.clay_paired_orbit_training import ClaySourceAdapter  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--clay-source-dir", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=(263, 277, 293, 311, 331))
    parser.add_argument("--held-sectors", type=int, nargs="+", default=(1, 4, 7))
    parser.add_argument("--rows-per-view", type=int, default=10_000)
    parser.add_argument("--candidate-rows-per-view", type=int, default=60_000)
    parser.add_argument("--evaluation-records", type=int, default=10_000)
    parser.add_argument("--steps", type=int, default=4_800)
    parser.add_argument("--batch-size", type=int, default=192)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--weight-decay", type=float, default=0.0001)
    parser.add_argument("--log-every", type=int, default=200)
    parser.add_argument("--hidden-width", type=int, default=64)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--data-seed-offset", type=int, default=4_000_000)
    parser.add_argument("--evaluation-min-class-support", type=int, default=32)
    parser.add_argument("--arms", nargs="+", choices=ARMS, default=ARMS)
    parser.add_argument("--primary-arm", choices=ARMS, default=PRIMARY_ARM)
    parser.add_argument("--controls", nargs="+", choices=ARMS, default=CONTROLS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_factor_campaign(
        args.output,
        ClaySourceAdapter(args.clay_source_dir),
        seeds=tuple(args.seeds),
        held_sectors=tuple(args.held_sectors),
        rows_per_view=args.rows_per_view,
        candidate_rows_per_view=args.candidate_rows_per_view,
        evaluation_records=args.evaluation_records,
        steps=args.steps,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        log_every=args.log_every,
        hidden_width=args.hidden_width,
        device_name=args.device,
        data_seed_offset=args.data_seed_offset,
        evaluation_min_class_support=args.evaluation_min_class_support,
        arms=tuple(args.arms),
        primary_arm=args.primary_arm,
        controls=tuple(args.controls),
    )
    print(
        json.dumps(
            {
                "state": result["state"],
                "producer_verdict": result["aggregate"]["verdict"],
                "result_sha256": result["result_sha256"],
                "promotion_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
