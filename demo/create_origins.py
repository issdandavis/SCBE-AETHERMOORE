#!/usr/bin/env python3
"""
Generate canonical origin cards for Aethermoor/SCBE characters.

Usage examples:
  python demo/create_origins.py --names Polly Clay Aria
  python demo/create_origins.py --names AgentA AgentB --seed custom-seed
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import List

from origin_creator import create_origins, origin_to_card


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate deterministic origin cards for characters/agents.")
    parser.add_argument("--names", nargs="+", required=True, help="Character or AI names")
    parser.add_argument("--seed", default="aethermoor-origin-v1", help="Deterministic seed")
    parser.add_argument("--out-dir", default="demo/training_output", help="Output directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    names: List[str] = args.names
    origins = create_origins(names, seed=args.seed)

    joined = ",".join(sorted(names))
    file_hash = hashlib.md5(f"{args.seed}:{joined}".encode("utf-8")).hexdigest()[:8]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"origins_custom_{file_hash}.json"

    data = [origins[name].to_dict() for name in names if name in origins]
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("Origin cards:")
    for name in names:
        if name in origins:
            print(origin_to_card(origins[name]))
            print()

    print(f"Saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
