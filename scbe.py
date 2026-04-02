#!/usr/bin/env python3
"""Source-checkout wrapper for the installed Spiralverse CLI."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from spiralverse.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
