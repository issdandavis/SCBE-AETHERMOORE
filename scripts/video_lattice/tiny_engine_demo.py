#!/usr/bin/env python3
"""Render the SCBE tiny pocket-dimension world demo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "video_lattice" / "tiny_engine"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.video_lattice import demo_world  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    world = demo_world()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = world.save_json(args.out_dir / "pocket_world.json")
    svg_path = world.save_svg(args.out_dir / "pocket_world.svg", cell=48)
    text_path = args.out_dir / "pocket_world.txt"
    text_path.write_text("\n".join(world.to_symbol_grid()) + "\n", encoding="utf-8")

    print(f"pocket_id: {world.pocket_id}")
    print(f"wrote {json_path}")
    print(f"wrote {svg_path}")
    print(f"wrote {text_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
