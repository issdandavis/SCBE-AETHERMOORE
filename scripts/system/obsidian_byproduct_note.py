#!/usr/bin/env python3
"""Write a work-session byproduct note into Obsidian."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.obsidian_researcher.byproduct_logger import ByproductLogger


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--vault-path", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--files", default="")
    p.add_argument("--next", default="")
    args = p.parse_args()

    files = [x.strip() for x in args.files.split(",") if x.strip()]
    next_steps = [x.strip() for x in args.next.split("|") if x.strip()]

    logger = ByproductLogger(vault_root=Path(args.vault_path))
    out = logger.log(args.title, args.summary, files, next_steps)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
