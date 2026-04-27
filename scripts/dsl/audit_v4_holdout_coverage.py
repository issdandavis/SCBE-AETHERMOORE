#!/usr/bin/env python3
"""B-2a precondition audit: per-category coverage of v1_holdout MINUS contract-repair sources.

Non-destructive read + report. Determines whether v5 launch can proceed on a
v4_holdout pool constructed as `bijective_dsl_v1_holdout` MINUS the 46 idxs
already consumed as contract-repair source rows, or whether B-2b synthesis
must land first because some required-floor category drops below the
working minimum (>=3 records per floor-bearing category, per v5 spec sec 2.5
pool-thinness consequence).

Outputs:
  artifacts/dsl_eval_reports/v4_holdout_coverage_audit.json

Exit codes:
  0  every floor-bearing category has >=3 records remaining
  2  one or more floor-bearing categories drop below 3 (B-2b synthesis required)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REPAIR_TRAIN = PROJECT_ROOT / "training-data/sft/contract_repair_v1_train.sft.jsonl"
REPAIR_HOLDOUT = PROJECT_ROOT / "training-data/sft/contract_repair_v1_holdout.sft.jsonl"
SOURCE_HOLDOUT = PROJECT_ROOT / "training-data/sft/bijective_dsl_v1_holdout.sft.jsonl"
OUT_PATH = PROJECT_ROOT / "artifacts/dsl_eval_reports/v4_holdout_coverage_audit.json"

WORKING_MIN = 3
TRANSLATE_ONE_CAP_PCT = 0.15

FLOOR_BEARING_CATEGORIES = {
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


def _harvest_repair_idxs(*paths: Path) -> set[int]:
    seen: set[int] = set()
    for p in paths:
        for rec in _load_jsonl(p):
            idx = rec.get("meta", {}).get("source_holdout_idx")
            if isinstance(idx, int):
                seen.add(idx)
    return seen


def _category_of(row: dict) -> str:
    meta = row.get("meta", {})
    cat = meta.get("task") or meta.get("category")
    return cat or "unknown"


def main() -> int:
    repair_idxs = _harvest_repair_idxs(REPAIR_TRAIN, REPAIR_HOLDOUT)
    source_rows = _load_jsonl(SOURCE_HOLDOUT)

    source_categories = Counter(_category_of(r) for r in source_rows)
    consumed_categories = Counter(
        _category_of(r) for i, r in enumerate(source_rows) if i in repair_idxs
    )
    remaining_rows = [r for i, r in enumerate(source_rows) if i not in repair_idxs]
    remaining_categories = Counter(_category_of(r) for r in remaining_rows)

    n_total = len(source_rows)
    n_consumed = sum(1 for i in range(n_total) if i in repair_idxs)
    n_remaining = len(remaining_rows)

    floor_violations: dict[str, int] = {}
    for cat in FLOOR_BEARING_CATEGORIES:
        count = remaining_categories.get(cat, 0)
        if count < WORKING_MIN:
            floor_violations[cat] = count

    translate_one_count = remaining_categories.get("translate_one", 0)
    translate_one_pct = (translate_one_count / n_remaining) if n_remaining else 0.0
    translate_one_cap_records = int(round(n_remaining * TRANSLATE_ONE_CAP_PCT))
    translate_one_over_cap = max(0, translate_one_count - translate_one_cap_records)

    payload = {
        "schema_version": "v4_holdout_coverage_audit_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "source_holdout": str(SOURCE_HOLDOUT.relative_to(PROJECT_ROOT).as_posix()),
            "repair_train": str(REPAIR_TRAIN.relative_to(PROJECT_ROOT).as_posix()),
            "repair_holdout": str(REPAIR_HOLDOUT.relative_to(PROJECT_ROOT).as_posix()),
        },
        "counts": {
            "n_v1_holdout_total": n_total,
            "n_consumed_by_repair": n_consumed,
            "n_remaining_for_v4_holdout": n_remaining,
            "expected_consumed": 46,
            "expected_remaining": 60,
        },
        "by_category": {
            "v1_holdout_source": dict(source_categories),
            "consumed_by_repair": dict(consumed_categories),
            "remaining_for_v4_holdout": dict(remaining_categories),
        },
        "floor_check": {
            "working_minimum_per_category": WORKING_MIN,
            "floor_bearing_categories": sorted(FLOOR_BEARING_CATEGORIES),
            "violations": floor_violations,
            "violation_count": len(floor_violations),
        },
        "translate_one_cap": {
            "cap_pct": TRANSLATE_ONE_CAP_PCT,
            "cap_records_at_current_pool": translate_one_cap_records,
            "current_count": translate_one_count,
            "current_pct": round(translate_one_pct, 4),
            "over_cap_by": translate_one_over_cap,
        },
        "verdict": (
            "PASS" if not floor_violations
            else "FAIL_B2B_REQUIRED"
        ),
        "notes": (
            "v4_holdout pool = v1_holdout MINUS all source_holdout_idxs consumed "
            "by contract_repair_v1 (both train and holdout splits). If any "
            "floor-bearing category drops below WORKING_MIN, B-2b synthesis must "
            "land BEFORE v5 launch (uncomputable gate, not just unmet)."
        ),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"[v4-audit] consumed={n_consumed} remaining={n_remaining}")
    print(f"[v4-audit] remaining_by_category={dict(remaining_categories)}")
    print(f"[v4-audit] translate_one cap={translate_one_cap_records} cur={translate_one_count} over={translate_one_over_cap}")
    if floor_violations:
        print(f"[v4-audit] FAIL: floor violations (need >={WORKING_MIN}): {floor_violations}")
        print(f"[v4-audit] -> B-2b synthesis must land BEFORE v5 launch.")
    else:
        print(f"[v4-audit] PASS: every floor-bearing category has >={WORKING_MIN} records.")
    print(f"[v4-audit] wrote {OUT_PATH.relative_to(PROJECT_ROOT)}")

    return 0 if not floor_violations else 2


if __name__ == "__main__":
    raise SystemExit(main())
