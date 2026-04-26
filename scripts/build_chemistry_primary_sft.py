"""Build a chemistry-primary Sacred Tongues SFT lane from existing drill corpora.

This promotes chemistry from an incidental transport task to an explicit
teaching lane. It keeps the chemistry packets (`transport_atomic`) and the
closest semantic support rows (`atomic_semantic`) in a standalone train/eval
pair under `training-data/sft/`.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SFT_ROOT = REPO_ROOT / "training-data" / "sft"

TRAIN_SRC = SFT_ROOT / "drill_langues_full_train.sft.jsonl"
EVAL_SRC = SFT_ROOT / "drill_langues_full_holdout.sft.jsonl"

TRAIN_OUT = SFT_ROOT / "chemistry_primary_train.sft.jsonl"
EVAL_OUT = SFT_ROOT / "chemistry_primary_holdout.sft.jsonl"
MANIFEST_OUT = SFT_ROOT / "chemistry_primary_manifest.json"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def record_map(rec: dict) -> str:
    return str(rec.get("meta", {}).get("map", "")).strip()


def record_kind(rec: dict) -> str:
    return str(rec.get("meta", {}).get("kind", "")).strip()


def chemistry_keep(rec: dict) -> bool:
    map_name = record_map(rec)
    kind = record_kind(rec)
    if map_name == "transport_atomic":
        return True
    if map_name == "atomic_semantic" and kind in {"state", "rationale"}:
        return True
    return False


def summarize(rows: list[dict]) -> dict:
    maps = Counter(record_map(r) for r in rows)
    kinds = Counter(f"{record_map(r)}::{record_kind(r)}" for r in rows)
    tongues = Counter(str(r.get("meta", {}).get("tongue", "")).strip() for r in rows)
    return {
        "count": len(rows),
        "maps": dict(sorted(maps.items())),
        "kinds": dict(sorted(kinds.items())),
        "tongues": dict(sorted(tongues.items())),
    }


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    train_rows = load_jsonl(TRAIN_SRC)
    eval_rows = load_jsonl(EVAL_SRC)

    chemistry_train = [row for row in train_rows if chemistry_keep(row)]
    chemistry_eval = [row for row in eval_rows if chemistry_keep(row)]

    write_jsonl(TRAIN_OUT, chemistry_train)
    write_jsonl(EVAL_OUT, chemistry_eval)

    manifest = {
        "schema_version": "chemistry_primary_manifest_v1",
        "sources": {
            "train": str(TRAIN_SRC.relative_to(REPO_ROOT)),
            "eval": str(EVAL_SRC.relative_to(REPO_ROOT)),
        },
        "outputs": {
            "train": str(TRAIN_OUT.relative_to(REPO_ROOT)),
            "eval": str(EVAL_OUT.relative_to(REPO_ROOT)),
        },
        "selection_rule": {
            "include_maps": ["transport_atomic"],
            "support_maps": ["atomic_semantic"],
            "support_kinds": ["state", "rationale"],
        },
        "train_summary": summarize(chemistry_train),
        "eval_summary": summarize(chemistry_eval),
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"[chemistry_primary] wrote {len(chemistry_train)} train rows -> {TRAIN_OUT}")
    print(f"[chemistry_primary] wrote {len(chemistry_eval)} eval rows -> {EVAL_OUT}")
    print(f"[chemistry_primary] manifest -> {MANIFEST_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
