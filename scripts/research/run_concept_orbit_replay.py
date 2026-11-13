"""Run the preregistered source-disjoint concept-orbit replay campaign."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.concept_orbit_replay import ARMS, run_campaign  # noqa: E402

PREREGISTRATION = REPO_ROOT / "docs/research/CONCEPT_ORBIT_REPLAY_PREREGISTRATION_20261113.md"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare static repetition with transformed concept-orbit replay.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=(11, 29, 47))
    parser.add_argument("--steps", type=int, default=1500)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=0.003)
    parser.add_argument("--log-every", type=int, default=50)
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    result = run_campaign(
        arguments.output.resolve(),
        seeds=tuple(arguments.seeds),
        arms=ARMS,
        steps=arguments.steps,
        batch_size=arguments.batch_size,
        learning_rate=arguments.learning_rate,
        log_every=arguments.log_every,
        implementation_path=Path(__file__).resolve().parents[2] / "python/scbe/concept_orbit_replay.py",
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
