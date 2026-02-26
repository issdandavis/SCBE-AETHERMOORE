from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from polly_eggs.trainer import Trainer


def main() -> int:
    trainer = Trainer(world_seed="aethermore-v1")
    lessons = ["navigation-basics", "resource-discipline", "geoseal-boundary-test"]
    rows = trainer.run_batch(batch_size=3, lessons=lessons)

    out = Path("training-data/hf-digimon-egg/episodes_generated.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")

    print(f"wrote {len(rows)} rows -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
