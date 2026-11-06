#!/usr/bin/env python3
"""Build an analysis-only KNOCK-V evidence bundle from a local video."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from video_lattice.knock_v import main

if __name__ == "__main__":
    raise SystemExit(main())
