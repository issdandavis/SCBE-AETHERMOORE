#!/usr/bin/env python3
"""v5 promotion gate: per-category coverage of bijective_dsl_v5_holdout.sft.jsonl.

The v3 repair corpus was mined from v4_holdout, so v4 is no longer a clean
promotion target. This audit reads the assembled v5_holdout file directly and
validates that the file frozen-eval will consume satisfies floors and remains
disjoint from contract_repair_v3_train.

Outputs:
  artifacts/dsl_eval_reports/v5_holdout_gate.json

Exit codes:
  0  PASS (all floors >=3, translate_one within cap, no repair-train overlap)
  2  FAIL_LAUNCH_BLOCKED
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

V5_HOLDOUT = PROJECT_ROOT / "training-data/sft/bijective_dsl_v5_holdout.sft.jsonl"
PARAMETRIC_TRAIN = PROJECT_ROOT / "training-data/sft/dsl_b2b_parametric_v1_train.sft.jsonl"
PARAMETRIC_HOLDOUT = PROJECT_ROOT / "training-data/sft/dsl_b2b_parametric_v1_holdout.sft.jsonl"
REPAIR_V3_TRAIN = PROJECT_ROOT / "training-data/sft/contract_repair_v3_train.sft.jsonl"
OUT_PATH = PROJECT_ROOT / "artifacts/dsl_eval_reports/v5_holdout_gate.json"

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


def _category(row: dict) -> str:
    meta = row.get("meta", {})
    return meta.get("task") or meta.get("category") or "unknown"


def _signature(row: dict) -> str:
    """Stable identity for cross-split overlap detection."""
    msgs = row.get("messages", [])
    user_text = next((m.get("content", "") for m in msgs if m.get("role") == "user"), "")
    asst_text = next((m.get("content", "") for m in msgs if m.get("role") == "assistant"), "")
    return f"{_category(row)}::{user_text[:200]}::{asst_text[:200]}"


def main() -> int:
    rows = _load_jsonl(V5_HOLDOUT)
    n = len(rows)

    by_cat = Counter(_category(r) for r in rows)
    floor_violations = {
        cat: by_cat.get(cat, 0)
        for cat in FLOOR_BEARING_CATEGORIES
        if by_cat.get(cat, 0) < WORKING_MIN
    }

    t1_count = by_cat.get("translate_one", 0)
    t1_pct = (t1_count / n) if n else 0.0
    t1_within_cap = t1_pct <= TRANSLATE_ONE_CAP_PCT

    parametric_count = sum(
        1
        for r in rows
        if r.get("meta", {}).get("provenance") == "parametric_generated_v1"
    )

    train_sigs = {_signature(r) for r in _load_jsonl(PARAMETRIC_TRAIN)}
    repair_v3_train_sigs = {_signature(r) for r in _load_jsonl(REPAIR_V3_TRAIN)}
    holdout_sigs = [_signature(r) for r in rows]
    cross_split_overlap = sum(1 for s in holdout_sigs if s in train_sigs)
    repair_v3_train_overlap = sum(1 for s in holdout_sigs if s in repair_v3_train_sigs)

    parametric_holdout_canonical = _load_jsonl(PARAMETRIC_HOLDOUT)
    parametric_in_holdout_match = sum(
        1
        for r in rows
        if r.get("meta", {}).get("provenance") == "parametric_generated_v1"
    )

    failures = []
    if floor_violations:
        failures.append(f"floor_violations={floor_violations}")
    if not t1_within_cap:
        failures.append(f"translate_one_over_cap={t1_count}/{n}={t1_pct:.4f}")
    if cross_split_overlap > 0:
        failures.append(f"cross_split_overlap={cross_split_overlap}")
    if repair_v3_train_overlap > 0:
        failures.append(f"repair_v3_train_overlap={repair_v3_train_overlap}")
    if parametric_in_holdout_match != len(parametric_holdout_canonical):
        failures.append(
            f"parametric_holdout_count_mismatch="
            f"{parametric_in_holdout_match} vs canonical {len(parametric_holdout_canonical)}"
        )

    payload = {
        "schema_version": "v5_holdout_gate_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input": str(V5_HOLDOUT.relative_to(PROJECT_ROOT).as_posix()),
        "counts": {
            "total": n,
            "parametric_generated_v1": parametric_count,
            "non_parametric": n - parametric_count,
        },
        "by_category": dict(by_cat),
        "floor_check": {
            "working_minimum": WORKING_MIN,
            "violations": floor_violations,
        },
        "translate_one_cap": {
            "cap_pct": TRANSLATE_ONE_CAP_PCT,
            "count": t1_count,
            "pct": round(t1_pct, 4),
            "within_cap": t1_within_cap,
        },
        "cross_split_overlap_with_parametric_train": cross_split_overlap,
        "repair_v3_train_overlap": repair_v3_train_overlap,
        "parametric_holdout_count_match": (
            parametric_in_holdout_match >= len(parametric_holdout_canonical)
        ),
        "verdict": "PASS" if not failures else "FAIL_LAUNCH_BLOCKED",
        "failures": failures,
        "notes": (
            "v5 promotion gate. PASS = v5_holdout is safe to use as frozen-eval "
            "target for the v3 contract-repair training round. FAIL = promotion "
            "is blocked; investigate failures before proceeding."
        ),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"[v5-gate] total={n} by_category={dict(by_cat)}")
    print(
        f"[v5-gate] translate_one={t1_count}/{n} ({t1_pct:.4f}) "
        f"cap={TRANSLATE_ONE_CAP_PCT} within={t1_within_cap}"
    )
    print(f"[v5-gate] parametric={parametric_count} cross_split_overlap={cross_split_overlap}")
    print(f"[v5-gate] repair_v3_train_overlap={repair_v3_train_overlap}")
    if failures:
        print(f"[v5-gate] FAIL_LAUNCH_BLOCKED: {failures}")
        return 2
    print(f"[v5-gate] PASS: v5 launch gate cleared")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
