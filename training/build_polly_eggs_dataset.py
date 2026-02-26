#!/usr/bin/env python3
"""Build Polly Eggs dataset artifacts for Hugging Face upload."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def load_jsonl(path: Path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--src", default="training-data/hf-digimon-egg/episodes_seed.jsonl")
    p.add_argument("--out", default="training-data/hf-digimon-egg/data")
    args = p.parse_args()

    src = Path(args.src)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = load_jsonl(src)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    records = out_dir / f"egg_episodes_{stamp}.jsonl"
    with records.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")

    index = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source": str(src),
        "count": len(rows),
        "artifact": str(records),
    }
    (out_dir / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")

    print(json.dumps(index, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
