#!/usr/bin/env python3
"""Audit bijective DSL v5 holdout promotion boundary."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SFT = ROOT / "training-data" / "sft"
OUT = ROOT / "artifacts" / "dsl_eval_reports" / "v5_holdout_gate.json"
HOLDOUT = SFT / "bijective_dsl_v5_holdout.sft.jsonl"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def category(row: dict[str, Any]) -> str:
    meta = row.get("meta", {}) or {}
    return str(meta.get("task") or meta.get("category") or "unknown")


def signature(row: dict[str, Any]) -> str:
    user = "\n".join(m.get("content", "") for m in row.get("messages", []) if m.get("role") == "user")
    assistant = "\n".join(m.get("content", "") for m in row.get("messages", []) if m.get("role") == "assistant")
    return hashlib.sha256(f"{user}\n---\n{assistant}".encode("utf-8")).hexdigest()


def audit() -> dict[str, Any]:
    rows = load_jsonl(HOLDOUT)
    repair_train = load_jsonl(SFT / "contract_repair_v3_train.sft.jsonl")
    parametric_train = load_jsonl(SFT / "dsl_b2b_parametric_v1_train.sft.jsonl")
    counts = Counter(category(row) for row in rows)
    total = len(rows)
    working_minimum = 3
    floor_violations = {cat: count for cat, count in counts.items() if count < working_minimum}
    required = {
        "identify",
        "edit_slot_all",
        "edit_slot_one",
        "governance_tag",
        "align",
        "translate_all",
        "dialogue",
        "multiline_edit",
        "translate_one",
    }
    for cat in sorted(required - set(counts)):
        floor_violations[cat] = 0

    row_sigs = {signature(row) for row in rows}
    failures: list[str] = []
    translate_count = counts.get("translate_one", 0)
    translate_pct = translate_count / total if total else 0.0
    if floor_violations:
        failures.append("floor_violations")
    if translate_pct > 0.15:
        failures.append("translate_one_cap")

    repair_overlap = len(row_sigs & {signature(row) for row in repair_train})
    if repair_overlap:
        failures.append("repair_v3_train_overlap")

    parametric_overlap = len(row_sigs & {signature(row) for row in parametric_train})
    if parametric_overlap:
        failures.append("parametric_train_overlap")

    payload = {
        "schema_version": "v5_holdout_gate_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input": str(HOLDOUT.relative_to(ROOT).as_posix()),
        "counts": {"total": total},
        "by_category": dict(counts),
        "floor_check": {"working_minimum": working_minimum, "violations": floor_violations},
        "translate_one_cap": {
            "cap_pct": 0.15,
            "count": translate_count,
            "pct": round(translate_pct, 4),
            "within_cap": translate_pct <= 0.15,
        },
        "cross_split_overlap_with_parametric_train": parametric_overlap,
        "repair_v3_train_overlap": repair_overlap,
        "verdict": "PASS" if not failures else "FAIL",
        "failures": failures,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    payload = audit()
    print(f"Wrote {OUT.relative_to(ROOT)}")
    print(f"verdict={payload['verdict']}")
    if payload["failures"]:
        print(json.dumps(payload["failures"], indent=2))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
