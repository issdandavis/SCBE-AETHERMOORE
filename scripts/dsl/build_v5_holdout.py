#!/usr/bin/env python3
"""Build a boundary-clean bijective_dsl_v5_holdout for v3 promotion eval.

v4_holdout was used to mine contract_repair_v3, so v3 training sees part of
v4 through the repair lane. This builder:

- starts from v4_holdout;
- removes rows whose signatures appear in contract_repair_v3_train;
- caps translate_one at 15%;
- adds deterministic holdout-only parametric identify/edit_slot_one rows to
  restore category floors.
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SFT_DIR = PROJECT_ROOT / "training-data" / "sft"

V4_HOLDOUT = SFT_DIR / "bijective_dsl_v4_holdout.sft.jsonl"
REPAIR_V3_TRAIN = SFT_DIR / "contract_repair_v3_train.sft.jsonl"
REPAIR_V3_HOLDOUT = SFT_DIR / "contract_repair_v3_holdout.sft.jsonl"
OUT_PATH = SFT_DIR / "bijective_dsl_v5_holdout.sft.jsonl"
OUT_MANIFEST = SFT_DIR / "bijective_dsl_v5_holdout_manifest.json"

TRANSLATE_ONE_CAP_PCT = 0.15
WORKING_MIN = 3
SUBSAMPLE_SEED = 271828182

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


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def category(row: dict) -> str:
    meta = row.get("meta", {})
    return meta.get("task") or meta.get("category") or "unknown"


def signature(row: dict) -> str:
    messages = row.get("messages", [])
    user_text = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
    assistant_text = next((m.get("content", "") for m in messages if m.get("role") == "assistant"), "")
    return f"{category(row)}::{user_text[:300]}::{assistant_text[:300]}"


def solve_translate_one_keep(t1_count: int, other_count: int) -> int:
    for keep in range(t1_count, -1, -1):
        total = keep + other_count
        if total and keep / total <= TRANSLATE_ONE_CAP_PCT:
            return keep
    return 0


def make_record(task: str, algorithm: str, tongue: str, user: str, assistant: str, seed: int) -> dict:
    return {
        "messages": [
            {"role": "system", "content": "Emit a DSL program over the 8 SCBE primitives."},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "meta": {
            "task": task,
            "algorithm": algorithm,
            "tongue": tongue,
            "dsl_program_depth": 1,
            "dsl_synthesised_from": task,
            "provenance": "parametric_generated_v5_holdout",
            "seed": seed,
            "boundary_role": "v5_holdout_only",
        },
    }


def parametric_floor_rows() -> list[dict]:
    return [
        make_record(
            "identify",
            "abs_value",
            "KO",
            "<input>Identify the algorithm and its slot structure from this snippet (KO, Python):\n\n"
            "```py\n"
            "def abs_value(x):\n"
            "    return x if x >= 0 else -x\n"
            "```\n"
            "</input>\n<target_tongue>KO</target_tongue>",
            "well_select(IDENTIFIED)\n# expected: algorithm: abs_value",
            5001,
        ),
        make_record(
            "identify",
            "clamp",
            "AV",
            "<input>Identify the algorithm and its slot structure from this snippet (AV, TypeScript):\n\n"
            "```ts\n"
            "function clamp(x: number, lo: number, hi: number): number {\n"
            "  if (x < lo) return lo;\n"
            "  if (x > hi) return hi;\n"
            "  return x;\n"
            "}\n"
            "```\n"
            "</input>\n<target_tongue>AV</target_tongue>",
            "well_select(IDENTIFIED)\n# expected: algorithm: clamp",
            5002,
        ),
        make_record(
            "edit_slot_one",
            "count_evens",
            "RU",
            "<input>Algorithm: count_evens (Count even elements in a list)\n"
            "Original (RU, Rust):\n\n"
            "```rs\n"
            "fn count_evens(xs: &[i64]) -> usize {\n"
            "    xs.iter().filter(|&&x| x % 2 == 0).count()\n"
            "}\n"
            "```\n\n"
            "Edit: flip predicate from even to odd\n"
            "Target slot: body\n\n"
            "Apply the edit ONLY in tongue RU. Output the patched source.</input>\n"
            "<target_tongue>RU</target_tongue>",
            "well_select(EDIT_BODY)\n# expected: ```rs",
            5003,
        ),
        make_record(
            "edit_slot_one",
            "reverse_list",
            "CA",
            "<input>Algorithm: reverse_list (Reverse order of elements)\n"
            "Original (CA, C):\n\n"
            "```c\n"
            "void reverse(int *xs, int n) {\n"
            "  for (int i = 0; i < n / 2; i++) {\n"
            "    int j = n - 1 - i;\n"
            "    int t = xs[i]; xs[i] = xs[j]; xs[j] = t;\n"
            "  }\n"
            "}\n"
            "```\n\n"
            "Edit: add a guard that returns immediately when n <= 1\n"
            "Target slot: guard\n\n"
            "Apply the edit ONLY in tongue CA. Output the patched source.</input>\n"
            "<target_tongue>CA</target_tongue>",
            "well_select(EDIT_GUARD)\n# expected: ```c",
            5004,
        ),
    ]


def main() -> int:
    v4_rows = load_jsonl(V4_HOLDOUT)
    repair_train = load_jsonl(REPAIR_V3_TRAIN)
    repair_holdout = load_jsonl(REPAIR_V3_HOLDOUT) if REPAIR_V3_HOLDOUT.exists() else []

    repair_train_sigs = {signature(row) for row in repair_train}
    repair_holdout_sigs = {signature(row) for row in repair_holdout}
    base_rows = [row for row in v4_rows if signature(row) not in repair_train_sigs]

    additions = parametric_floor_rows()
    t1_rows = [row for row in base_rows if category(row) == "translate_one"]
    non_t1_rows = [row for row in base_rows if category(row) != "translate_one"]
    keep_t1 = solve_translate_one_keep(len(t1_rows), len(non_t1_rows) + len(additions))

    rng = random.Random(SUBSAMPLE_SEED)
    indices = list(range(len(t1_rows)))
    rng.shuffle(indices)
    kept_t1 = [t1_rows[i] for i in sorted(indices[:keep_t1])]

    final_rows = non_t1_rows + kept_t1 + additions
    by_category = Counter(category(row) for row in final_rows)
    total = len(final_rows)
    translate_one_count = by_category.get("translate_one", 0)
    translate_one_pct = translate_one_count / total if total else 0.0
    floor_violations = {
        cat: by_category.get(cat, 0) for cat in FLOOR_BEARING if by_category.get(cat, 0) < WORKING_MIN
    }
    overlap_train = sum(1 for row in final_rows if signature(row) in repair_train_sigs)
    overlap_holdout = sum(1 for row in final_rows if signature(row) in repair_holdout_sigs)

    write_jsonl(OUT_PATH, final_rows)
    sha = hashlib.sha256(OUT_PATH.read_bytes()).hexdigest()

    failures = []
    if floor_violations:
        failures.append(f"floor_violations={floor_violations}")
    if translate_one_pct > TRANSLATE_ONE_CAP_PCT:
        failures.append(f"translate_one_over_cap={translate_one_count}/{total}={translate_one_pct:.4f}")
    if overlap_train:
        failures.append(f"repair_v3_train_overlap={overlap_train}")

    manifest = {
        "schema_version": "bijective_dsl_v5_holdout_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "v4_holdout": str(V4_HOLDOUT.relative_to(PROJECT_ROOT).as_posix()),
            "repair_v3_train": str(REPAIR_V3_TRAIN.relative_to(PROJECT_ROOT).as_posix()),
            "repair_v3_holdout": str(REPAIR_V3_HOLDOUT.relative_to(PROJECT_ROOT).as_posix()),
        },
        "construction": {
            "step_1": "Drop v4 rows whose signatures appear in contract_repair_v3_train.",
            "step_2": "Add deterministic v5 holdout-only parametric identify/edit_slot_one floor rows.",
            "step_3": "Subsample translate_one to keep its share <= 15%.",
            "subsample_seed": SUBSAMPLE_SEED,
            "translate_one_cap_pct": TRANSLATE_ONE_CAP_PCT,
        },
        "counts": {
            "v4_total": len(v4_rows),
            "repair_v3_train_rows": len(repair_train),
            "repair_v3_holdout_rows": len(repair_holdout),
            "dropped_repair_v3_train_overlap": len(v4_rows) - len(base_rows),
            "parametric_added": len(additions),
            "translate_one_before_cap": len(t1_rows),
            "translate_one_kept": keep_t1,
            "translate_one_dropped": len(t1_rows) - keep_t1,
            "final_total": total,
        },
        "by_category_final": dict(by_category),
        "translate_one_final": {
            "count": translate_one_count,
            "pct": round(translate_one_pct, 4),
            "cap_pct": TRANSLATE_ONE_CAP_PCT,
            "within_cap": translate_one_pct <= TRANSLATE_ONE_CAP_PCT,
        },
        "floor_check": {
            "working_minimum_per_category": WORKING_MIN,
            "floor_bearing_categories": sorted(FLOOR_BEARING),
            "violations": floor_violations,
            "violation_count": len(floor_violations),
        },
        "boundary_check": {
            "repair_v3_train_overlap": overlap_train,
            "repair_v3_holdout_overlap": overlap_holdout,
            "train_clean": overlap_train == 0,
        },
        "output": {
            "path": str(OUT_PATH.relative_to(PROJECT_ROOT).as_posix()),
            "sha256": sha,
        },
        "verdict": "PASS" if not failures else "FAIL",
        "failures": failures,
        "notes": (
            "v5_holdout is the promotion-eval anchor for bijective-tongue-coder-v3 descendants. "
            "Do not evaluate v3 promotion on v4_holdout because contract_repair_v3_train was mined from v4."
        ),
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"[v5-build] wrote {OUT_PATH.relative_to(PROJECT_ROOT)} ({total} records)")
    print(f"[v5-build] by_category={dict(by_category)}")
    print(f"[v5-build] translate_one={translate_one_count}/{total} ({translate_one_pct:.4f})")
    if failures:
        print(f"[v5-build] FAIL: {failures}")
        return 2
    print("[v5-build] PASS: floor/cap/boundary checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
