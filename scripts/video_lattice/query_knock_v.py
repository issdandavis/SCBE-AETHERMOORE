#!/usr/bin/env python3
"""Return a hash-verified KNOCK-V time window for an agent."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from video_lattice.knock_v import inspect_window


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--start", type=float, required=True)
    parser.add_argument("--end", type=float, required=True)
    args = parser.parse_args()
    print(json.dumps(inspect_window(args.bundle, args.start, args.end), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
