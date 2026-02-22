#!/usr/bin/env python3
"""
Convenience wrapper for Code Prism CLI.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from code_prism.cli import main


if __name__ == "__main__":
    main()

