#!/usr/bin/env python3
"""
scripts/scbe.py — compatibility wrapper

Some local wrappers/docs call `python scripts/scbe.py ...`.
The canonical unified CLI entry point is repo-root `scbe.py`.

This file forwards all args to the root CLI so both paths keep working.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ENTRY = ROOT / "scbe.py"


def main() -> int:
    if not ENTRY.exists():
        print(f"error: missing CLI entrypoint: {ENTRY}", file=sys.stderr)
        return 1
    cmd = [sys.executable, str(ENTRY), *sys.argv[1:]]
    return subprocess.run(cmd, cwd=str(ROOT), check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())

