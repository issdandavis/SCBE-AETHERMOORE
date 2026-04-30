"""Asymmetric v12: filter signal_shape_boost to the 3 prompts that v10 still failed
(resource_jump_cancel, lane_separation, training_boundary) and duplicate 3x.

Skip hex_trace and cost_propagation entirely — both passed in v10 without forced-prefix
and adding boost rows for them in v11 caused regressions (advisor: "you'd be amplifying
the thing that broke them").

Output v12 train+holdout shards alongside the v1 shards so v10 base corpus is untouched.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SFT_DIR = ROOT / "training-data" / "sft"

SRC_TRAIN = SFT_DIR / "atomic_workflow_stage6_signal_shape_boost_train.sft.jsonl"
SRC_HOLDOUT = SFT_DIR / "atomic_workflow_stage6_signal_shape_boost_holdout.sft.jsonl"

DST_TRAIN = SFT_DIR / "atomic_workflow_stage6_signal_shape_boost_v12_train.sft.jsonl"
DST_HOLDOUT = SFT_DIR / "atomic_workflow_stage6_signal_shape_boost_v12_holdout.sft.jsonl"
DST_MANIFEST = SFT_DIR / "atomic_workflow_stage6_signal_shape_boost_v12_manifest.json"

KEEP_KINDS = {"resource_jump_cancel", "lane_separation", "training_boundary"}
TRAIN_DUPLICATE = 3
HOLDOUT_DUPLICATE = 1  # do not inflate eval


def filter_and_dup(src: Path, dst: Path, dup: int) -> dict:
    by_kind: dict[str, int] = {}
    with src.open(encoding="utf-8") as fin, dst.open("w", encoding="utf-8") as fout:
        for line in fin:
            row = json.loads(line)
            kind = row.get("meta", {}).get("kind")
            if kind not in KEEP_KINDS:
                continue
            for _ in range(dup):
                fout.write(json.dumps(row, ensure_ascii=False) + "\n")
            by_kind[kind] = by_kind.get(kind, 0) + dup
    return by_kind


def main() -> None:
    train_counts = filter_and_dup(SRC_TRAIN, DST_TRAIN, TRAIN_DUPLICATE)
    holdout_counts = filter_and_dup(SRC_HOLDOUT, DST_HOLDOUT, HOLDOUT_DUPLICATE)
    manifest = {
        "schema_version": "atomic_workflow_stage6_signal_shape_boost_v12_manifest_v1",
        "design": (
            "Asymmetric v12: keep v10 base corpus intact, add forced-prefix only for the "
            "3 prompts that v10 still failed (jump_cancel, lane_separation, training_boundary). "
            "Skip hex_trace + cost_propagation (passed in v10; v11 forced-prefix on them "
            "caused regressions). Duplicate 3x to push concentration without bringing back "
            "competing shards. Source v1 shards untouched."
        ),
        "source": {
            "train": str(SRC_TRAIN.name),
            "holdout": str(SRC_HOLDOUT.name),
        },
        "outputs": {
            "train": str(DST_TRAIN),
            "holdout": str(DST_HOLDOUT),
        },
        "filter": {
            "keep_kinds": sorted(KEEP_KINDS),
            "train_duplicate": TRAIN_DUPLICATE,
            "holdout_duplicate": HOLDOUT_DUPLICATE,
        },
        "counts": {
            "train": sum(train_counts.values()),
            "holdout": sum(holdout_counts.values()),
            "train_by_kind": train_counts,
            "holdout_by_kind": holdout_counts,
        },
    }
    DST_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
