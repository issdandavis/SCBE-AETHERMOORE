#!/usr/bin/env python3
"""B-2a v4 holdout assembler.

Builds bijective_dsl_v4_holdout.sft.jsonl from:
  - bijective_dsl_v1_holdout MINUS 28 repair source_holdout_idxs
  - UNION dsl_b2b_parametric_v1_holdout (14 records)

Subsamples translate_one deterministically so its share <= 15% of the final pool.
Writes a manifest documenting the construction.

Outputs:
  training-data/sft/bijective_dsl_v4_holdout.sft.jsonl
  training-data/sft/bijective_dsl_v4_holdout_manifest.json
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SFT_DIR = PROJECT_ROOT / "training-data/sft"

REPAIR_TRAIN = SFT_DIR / "contract_repair_v1_train.sft.jsonl"
REPAIR_HOLDOUT = SFT_DIR / "contract_repair_v1_holdout.sft.jsonl"
V1_HOLDOUT = SFT_DIR / "bijective_dsl_v1_holdout.sft.jsonl"
PARAMETRIC_HOLDOUT = SFT_DIR / "dsl_b2b_parametric_v1_holdout.sft.jsonl"

OUT_PATH = SFT_DIR / "bijective_dsl_v4_holdout.sft.jsonl"
OUT_MANIFEST = SFT_DIR / "bijective_dsl_v4_holdout_manifest.json"

TRANSLATE_ONE_CAP_PCT = 0.15
SUBSAMPLE_SEED = 314159265

FLOOR_BEARING = {
    "identify",
    "multiline_edit",
    "translate_one",
    "translate_all",
    "align",
    "governance_tag",
    "edit_slot_one",
    "edit_slot_all",
    "dialogue",
}


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _harvest_repair_idxs() -> set[int]:
    seen: set[int] = set()
    for p in [REPAIR_TRAIN, REPAIR_HOLDOUT]:
        for rec in _load_jsonl(p):
            idx = rec.get("meta", {}).get("source_holdout_idx")
            if isinstance(idx, int):
                seen.add(idx)
    return seen


def _category(row: dict) -> str:
    meta = row.get("meta", {})
    return meta.get("task") or meta.get("category") or "unknown"


def _solve_subsample_keep(t1_count: int, other_count: int, cap_pct: float) -> int:
    """Largest k such that k / (k + other_count) <= cap_pct."""
    if t1_count == 0:
        return 0
    for k in range(t1_count, -1, -1):
        total = k + other_count
        if total == 0:
            continue
        if k / total <= cap_pct:
            return k
    return 0


def main() -> int:
    repair_idxs = _harvest_repair_idxs()
    v1_rows = _load_jsonl(V1_HOLDOUT)
    parametric_rows = _load_jsonl(PARAMETRIC_HOLDOUT)

    remaining = [r for i, r in enumerate(v1_rows) if i not in repair_idxs]

    t1_rows = [r for r in remaining if _category(r) == "translate_one"]
    non_t1_remaining = [r for r in remaining if _category(r) != "translate_one"]

    other_count_after_union = len(non_t1_remaining) + len(parametric_rows)
    keep_t1 = _solve_subsample_keep(len(t1_rows), other_count_after_union, TRANSLATE_ONE_CAP_PCT)

    rng = random.Random(SUBSAMPLE_SEED)
    t1_indices = list(range(len(t1_rows)))
    rng.shuffle(t1_indices)
    kept_t1_indices = sorted(t1_indices[:keep_t1])
    dropped_t1_indices = sorted(t1_indices[keep_t1:])
    kept_t1 = [t1_rows[i] for i in kept_t1_indices]

    final_rows = non_t1_remaining + kept_t1 + parametric_rows

    final_categories = Counter(_category(r) for r in final_rows)
    total = len(final_rows)
    t1_final = final_categories.get("translate_one", 0)
    t1_pct = (t1_final / total) if total else 0.0

    floor_violations = {
        cat: final_categories.get(cat, 0)
        for cat in FLOOR_BEARING
        if final_categories.get(cat, 0) < 3
    }

    with OUT_PATH.open("w", encoding="utf-8") as f:
        for rec in final_rows:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    sha = hashlib.sha256(OUT_PATH.read_bytes()).hexdigest()

    manifest = {
        "schema_version": "bijective_dsl_v4_holdout_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "v1_holdout": str(V1_HOLDOUT.relative_to(PROJECT_ROOT).as_posix()),
            "repair_train": str(REPAIR_TRAIN.relative_to(PROJECT_ROOT).as_posix()),
            "repair_holdout": str(REPAIR_HOLDOUT.relative_to(PROJECT_ROOT).as_posix()),
            "parametric_holdout": str(PARAMETRIC_HOLDOUT.relative_to(PROJECT_ROOT).as_posix()),
        },
        "construction": {
            "step_1": "Drop 28 source_holdout_idxs consumed by contract_repair_v1.",
            "step_2": "Deterministic subsample translate_one to honor 15% cap.",
            "step_3": "Union with dsl_b2b_parametric_v1_holdout (14 records).",
            "subsample_seed": SUBSAMPLE_SEED,
            "translate_one_cap_pct": TRANSLATE_ONE_CAP_PCT,
        },
        "counts": {
            "v1_holdout_total": len(v1_rows),
            "repair_idxs_dropped": len(repair_idxs),
            "remaining_after_repair": len(remaining),
            "translate_one_in_remaining": len(t1_rows),
            "translate_one_kept": keep_t1,
            "translate_one_dropped": len(t1_rows) - keep_t1,
            "parametric_added": len(parametric_rows),
            "final_total": total,
        },
        "by_category_final": dict(final_categories),
        "translate_one_final": {
            "count": t1_final,
            "pct": round(t1_pct, 4),
            "cap_pct": TRANSLATE_ONE_CAP_PCT,
            "within_cap": t1_pct <= TRANSLATE_ONE_CAP_PCT,
        },
        "floor_check": {
            "working_minimum_per_category": 3,
            "floor_bearing_categories": sorted(FLOOR_BEARING),
            "violations": floor_violations,
            "violation_count": len(floor_violations),
        },
        "output": {
            "path": str(OUT_PATH.relative_to(PROJECT_ROOT).as_posix()),
            "sha256": sha,
        },
        "verdict": "PASS" if not floor_violations and t1_pct <= TRANSLATE_ONE_CAP_PCT else "FAIL",
        "notes": (
            "v4_holdout = v1_holdout MINUS 28 repair-source idxs UNION parametric holdout, "
            "with translate_one subsampled deterministically to honor the 15% cap. "
            "v5 frozen-eval MUST consume this file (never v1_holdout) to avoid prompt leakage."
        ),
    }

    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"[v4-asm] wrote {OUT_PATH.relative_to(PROJECT_ROOT)} ({total} records)")
    print(f"[v4-asm] by_category={dict(final_categories)}")
    print(f"[v4-asm] translate_one={t1_final}/{total} ({t1_pct:.4f}, cap={TRANSLATE_ONE_CAP_PCT})")
    if floor_violations:
        print(f"[v4-asm] FAIL: floor violations {floor_violations}")
        return 2
    print(f"[v4-asm] PASS: all floors >=3, translate_one within cap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
