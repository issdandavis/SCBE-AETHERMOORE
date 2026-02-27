from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from polly_eggs.gen1_view import run_gen1_game


def main() -> int:
    run_gen1_game(seed="aethermore-v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
