#!/usr/bin/env python3
"""CLI wrapper for the prime-token prospective watcher-chain audit."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.prime_token_watch_audit import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
