#!/usr/bin/env python3
"""Build contract-repair SFT corpus from on-disk DSL failure logs.

Joins ``sample_diagnostics`` rows from one or more
``*_executable_accuracy.json`` reports back to the source holdout JSONL,
emitting ``(prompt, canonical contract form)`` SFT pairs annotated with the
failed prediction the model originally produced.

Inputs (defaults reflect the 2026-04-27 Kaggle pull):

  --report  artifacts/dsl_eval_reports/polly-bijective-tongue-coder-v2_executable_accuracy.json
  --report  artifacts/dsl_eval_reports/polly-regularized-coding-v8_executable_accuracy.json
  --holdout training-data/sft/bijective_dsl_v1_holdout.sft.jsonl

Outputs:

  training-data/sft/contract_repair_v1_train.sft.jsonl
  training-data/sft/contract_repair_v1_holdout.sft.jsonl
  training-data/sft/contract_repair_v1_manifest.json

Boundary policy (matches atomic_workflow_stage6_repair_manifest_v1):
the source holdout MUST NOT be used as the v5 frozen-eval holdout, since
prompts now appear in training. v5 must eval against a NEW holdout
(``bijective_dsl_v4_holdout.sft.jsonl`` per v4 spec, Lever B-2a).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_jsonl(path: Path) -> List[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _load_report(path: Path) -> Tuple[str, List[dict]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    adapter = payload.get("adapter", path.stem)
    diags = payload.get("sample_diagnostics", [])
    return adapter, diags


def _hash_prompt(messages: List[dict]) -> str:
    user = next((m for m in messages if m.get("role") == "user"), {})
    return hashlib.sha256(user.get("content", "").encode("utf-8")).hexdigest()[:16]


def _build_repair_record(
    holdout_row: dict,
    diag: dict,
    source_round: str,
) -> dict:
    msgs = holdout_row["messages"]
    src_meta = holdout_row.get("meta", {})
    return {
        "messages": msgs,
        "meta": {
            "lane": "contract_repair_v1",
            "source_round": source_round,
            "source_holdout_idx": diag.get("idx"),
            "category": diag.get("category"),
            "repair_label": diag.get("failure_mode"),
            "predicted_wrong": diag.get("predicted"),
            "expected_truncated_in_log": diag.get("expected"),
            "task": src_meta.get("task"),
            "algorithm": src_meta.get("algorithm"),
            "tongue": src_meta.get("tongue") or src_meta.get("dst") or src_meta.get("src"),
            "prompt_sha256_16": _hash_prompt(msgs),
        },
    }


def _stratified_split(
    records: List[dict],
    holdout_frac: float,
    seed: int,
) -> Tuple[List[dict], List[dict]]:
    by_cat: Dict[str, List[dict]] = defaultdict(list)
    for rec in records:
        by_cat[rec["meta"]["category"]].append(rec)
    rng = random.Random(seed)
    train, holdout = [], []
    for cat, items in by_cat.items():
        rng.shuffle(items)
        n_holdout = max(1, int(round(len(items) * holdout_frac))) if len(items) > 1 else 0
        holdout.extend(items[:n_holdout])
        train.extend(items[n_holdout:])
    return train, holdout


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--report",
        action="append",
        default=None,
        help="Path to *_executable_accuracy.json (repeatable).",
    )
    ap.add_argument(
        "--holdout",
        default="training-data/sft/bijective_dsl_v1_holdout.sft.jsonl",
        help="Source holdout JSONL whose idx values the reports reference.",
    )
    ap.add_argument(
        "--out-prefix",
        default="training-data/sft/contract_repair_v1",
        help="Prefix for *_train.sft.jsonl, *_holdout.sft.jsonl, *_manifest.json.",
    )
    ap.add_argument("--holdout-frac", type=float, default=0.20)
    ap.add_argument("--seed", type=int, default=20260427)
    args = ap.parse_args()

    if not args.report:
        args.report = [
            "artifacts/dsl_eval_reports/polly-bijective-tongue-coder-v2_executable_accuracy.json",
            "artifacts/dsl_eval_reports/polly-regularized-coding-v8_executable_accuracy.json",
        ]

    holdout_path = (PROJECT_ROOT / args.holdout).resolve()
    holdout_rows = _load_jsonl(holdout_path)

    seen_keys: set = set()
    repair_records: List[dict] = []
    per_round_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for rep_path in args.report:
        rp = (PROJECT_ROOT / rep_path).resolve()
        adapter, diags = _load_report(rp)
        for diag in diags:
            if diag.get("ok") or diag.get("failure_mode") in (None, "unknown"):
                continue
            idx = diag.get("idx")
            if idx is None or idx >= len(holdout_rows):
                continue
            row = holdout_rows[idx]
            key = (adapter, idx, diag.get("failure_mode"))
            if key in seen_keys:
                continue
            seen_keys.add(key)
            rec = _build_repair_record(row, diag, source_round=adapter)
            repair_records.append(rec)
            per_round_counts[adapter][diag["category"]] += 1

    if not repair_records:
        print("[contract-repair] no failure rows extracted; nothing to write.")
        return 1

    train, holdout = _stratified_split(repair_records, args.holdout_frac, args.seed)

    out_prefix = (PROJECT_ROOT / args.out_prefix).resolve()
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    train_path = out_prefix.with_name(out_prefix.name + "_train.sft.jsonl")
    holdout_path_out = out_prefix.with_name(out_prefix.name + "_holdout.sft.jsonl")
    manifest_path = out_prefix.with_name(out_prefix.name + "_manifest.json")

    train_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in train) + "\n",
        encoding="utf-8",
    )
    holdout_path_out.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in holdout) + "\n",
        encoding="utf-8",
    )

    cat_totals: Dict[str, int] = defaultdict(int)
    label_totals: Dict[str, int] = defaultdict(int)
    for rec in repair_records:
        cat_totals[rec["meta"]["category"]] += 1
        label_totals[rec["meta"]["repair_label"]] += 1

    manifest = {
        "schema_version": "contract_repair_manifest_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_reports": [str(Path(p).as_posix()) for p in args.report],
        "source_holdout": str(holdout_path.relative_to(PROJECT_ROOT).as_posix()),
        "outputs": {
            "train": str(train_path.relative_to(PROJECT_ROOT).as_posix()),
            "holdout": str(holdout_path_out.relative_to(PROJECT_ROOT).as_posix()),
        },
        "counts": {
            "total": len(repair_records),
            "train": len(train),
            "holdout": len(holdout),
            "by_category": dict(cat_totals),
            "by_repair_label": dict(label_totals),
            "by_round": {k: dict(v) for k, v in per_round_counts.items()},
        },
        "boundary": (
            "Source rows are bijective_dsl_v1_holdout. v5 frozen-eval MUST use a "
            "different holdout (e.g. bijective_dsl_v4_holdout per v4 spec Lever B-2a) "
            "to avoid prompt leakage."
        ),
        "notes": (
            "Records pulled from sample_diagnostics arrays only (cap 24 per report). "
            "predicted_wrong is truncated to 160 chars by the source scorer; "
            "full assistant target is taken from the holdout, not the truncated 'expected' field."
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"[contract-repair] wrote {train_path.relative_to(PROJECT_ROOT)}  ({len(train)} rows)")
    print(f"[contract-repair] wrote {holdout_path_out.relative_to(PROJECT_ROOT)}  ({len(holdout)} rows)")
    print(f"[contract-repair] wrote {manifest_path.relative_to(PROJECT_ROOT)}")
    print(f"[contract-repair] by_category={dict(cat_totals)}")
    print(f"[contract-repair] by_repair_label={dict(label_totals)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
