"""Run the preregistered factor-balanced transform-coverage campaign."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.concept_factor_coverage import ARMS, run_factor_campaign  # noqa: E402

PREREGISTRATION = REPO_ROOT / "docs/research/CONCEPT_FACTOR_COVERAGE_PREREGISTRATION_20261113.md"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare correlated and factor-balanced transform lattices.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=(11, 29, 47))
    parser.add_argument("--steps", type=int, default=1500)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=0.003)
    parser.add_argument("--log-every", type=int, default=50)
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    result = run_factor_campaign(
        arguments.output.resolve(),
        seeds=tuple(arguments.seeds),
        arms=ARMS,
        steps=arguments.steps,
        batch_size=arguments.batch_size,
        learning_rate=arguments.learning_rate,
        log_every=arguments.log_every,
        implementation_path=REPO_ROOT / "python/scbe/concept_factor_coverage.py",
        preregistration_path=PREREGISTRATION,
    )
    print(
        json.dumps(
            {
                "state": result["state"],
                "verdict": result["aggregate"]["verdict"],
                "result_sha256": result["result_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
