from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.tokenizer.atomic_workflow_units import ResourceBudget, compose_workflow


DEFAULT_MARS_DRONE_SEQUENCE = (
    "scan_area",
    "measure_state",
    "plan_route",
    "fly_forward",
    "stabilize_pose",
    "send_report",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the atomic workflow composition model against a falling resource budget."
    )
    parser.add_argument("tokens", nargs="*", default=list(DEFAULT_MARS_DRONE_SEQUENCE))
    parser.add_argument("--power", type=float, default=1.0)
    parser.add_argument("--compute", type=float, default=1.0)
    parser.add_argument("--time", type=float, default=1.0)
    parser.add_argument("--comms", type=float, default=1.0)
    parser.add_argument("--wear", type=float, default=1.0)
    parser.add_argument("--decay-floor", type=float, default=0.20)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = compose_workflow(
        args.tokens,
        budget=ResourceBudget(
            power=args.power,
            compute=args.compute,
            time=args.time,
            comms=args.comms,
            wear=args.wear,
        ),
        decay_floor=args.decay_floor,
    )
    text = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

