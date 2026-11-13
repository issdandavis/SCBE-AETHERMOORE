"""CLI wrapper for the independent frozen multi-view adapter replay."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.clay_frozen_multiview_replay import main

if __name__ == "__main__":
    raise SystemExit(main())
