#!/usr/bin/env python3
"""Run Aethermoor Spiral Engine MVP demo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.spiralverse.aethermoor_spiral_engine import run_demo


def main() -> int:
    parser = argparse.ArgumentParser(description="Aethermoor Spiral Engine demo")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--turns", type=int, default=12)
    parser.add_argument("--output-json", default="")
    args = parser.parse_args()

    payload = run_demo(seed=args.seed, turns=args.turns)
    text = json.dumps(payload, indent=2)
    if args.output_json:
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

