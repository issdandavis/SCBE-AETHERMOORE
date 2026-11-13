"""CLI entry point for the source-disjoint frozen multi-view adapter campaign."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.clay_frozen_multiview_adapter import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
