#!/usr/bin/env python3
"""Run a 3-way matched-budget A/B/C code benchmark on Kaggle.

Extends the 2-way A/B trainer to test three conditions:
  A (baseline):   L3 only — surface code, what mainstream LLMs learn from
  B (multiview):  L0-L3 — structural multi-view (substrate + coordination + threat + code)
  C (canonical):  L-1 + L0-L3 — canonical IR (code notes + graph + spectral + hyperbolic)

The question: does adding the canonical representation layer (Stage -1)
on top of multi-view training produce a measurable improvement?

All three conditions train on the SAME model, SAME steps, SAME token budget.
Only the training data richness differs.

Usage:
    python scripts/research/train_code_abc_kaggle.py --allow-cpu-smoke  # smoke test
    python scripts/research/train_code_abc_kaggle.py                    # GPU required
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

# Reuse the existing 2-way trainer's infrastructure
from train_code_ab_kaggle_safe import (
    REPO_ROOT,
    DEFAULT_MODEL,
    detect_accelerator,
    build_runtime_plan,
    is_kaggle_runtime,
    resolve_output_root,
    load_jsonl_text_rows,
    train_condition,
)

# Default dataset paths
SFT_DIR = REPO_ROOT / "training-data" / "sft"
DEFAULT_A = SFT_DIR / "round5_code_baseline_l3.jsonl"
DEFAULT_B = SFT_DIR / "round5_code_multiview_l0l3.jsonl"
DEFAULT_C = SFT_DIR / "round6_canonical_ir_l3.jsonl"


def prepare_matched_budget(
    *,
    path_a: Path,
    path_b: Path,
    path_c: Path,
    artifact_dir: Path,
    max_rows: int,
    seed: int,
) -> dict[str, Any]:
    """Load all three datasets and match to the smallest token budget.

    Token budget matching ensures fair comparison: all three conditions
    see the same total number of tokens during training.
    """
    import random

    rng = random.Random(seed)

    rows_a = load_jsonl_text_rows(path_a)
    rows_b = load_jsonl_text_rows(path_b)
    rows_c = load_jsonl_text_rows(path_c)

    # Cap each at max_rows
    if len(rows_a) > max_rows:
        rows_a = rng.sample(rows_a, max_rows)
    if len(rows_b) > max_rows:
        rows_b = rng.sample(rows_b, max_rows)
    if len(rows_c) > max_rows:
        rows_c = rng.sample(rows_c, max_rows)

    def estimate_tokens(rows: list[dict]) -> int:
        return sum(max(1, len(r["text"]) // 4) for r in rows)

    budget_a = estimate_tokens(rows_a)
    budget_b = estimate_tokens(rows_b)
    budget_c = estimate_tokens(rows_c)

    # Match to smallest budget (A is always smallest — L3 only is shortest)
    target_budget = min(budget_a, budget_b, budget_c)

    def trim_to_budget(rows: list[dict], budget: int) -> list[dict]:
        """Keep rows until token budget is reached."""
        result = []
        total = 0
        for r in rows:
            tok = max(1, len(r["text"]) // 4)
            if total + tok > budget:
                break
            result.append(r)
            total += tok
        return result

    matched_a = trim_to_budget(rows_a, target_budget)
    matched_b = trim_to_budget(rows_b, target_budget)
    matched_c = trim_to_budget(rows_c, target_budget)

    # Write matched datasets
    artifact_dir.mkdir(parents=True, exist_ok=True)
    for name, data in [("a_baseline", matched_a), ("b_multiview", matched_b), ("c_canonical", matched_c)]:
        path = artifact_dir / f"{name}_matched.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for r in data:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    return {
        "raw_rows": {"a": len(rows_a), "b": len(rows_b), "c": len(rows_c)},
        "raw_tokens": {"a": budget_a, "b": budget_b, "c": budget_c},
        "target_budget": target_budget,
        "matched_rows": {"a": len(matched_a), "b": len(matched_b), "c": len(matched_c)},
        "matched_tokens": {
            "a": estimate_tokens(matched_a),
            "b": estimate_tokens(matched_b),
            "c": estimate_tokens(matched_c),
        },
    }


def summarize_abc(
    loss_a: float | None,
    loss_b: float | None,
    loss_c: float | None,
) -> dict[str, Any]:
    """Compare all three conditions."""
    results: dict[str, Any] = {}

    losses = {"a_baseline": loss_a, "b_multiview": loss_b, "c_canonical": loss_c}
    results["losses"] = losses

    # Pairwise deltas
    if loss_a is not None and loss_b is not None:
        delta_ab = loss_b - loss_a
        results["b_vs_a"] = {
            "delta": round(delta_ab, 4),
            "improvement_pct": round(abs(delta_ab) / loss_a * 100, 2) if loss_a else None,
            "winner": "b_multiview" if delta_ab < 0 else "a_baseline" if delta_ab > 0 else "tie",
        }

    if loss_a is not None and loss_c is not None:
        delta_ac = loss_c - loss_a
        results["c_vs_a"] = {
            "delta": round(delta_ac, 4),
            "improvement_pct": round(abs(delta_ac) / loss_a * 100, 2) if loss_a else None,
            "winner": "c_canonical" if delta_ac < 0 else "a_baseline" if delta_ac > 0 else "tie",
        }

    if loss_b is not None and loss_c is not None:
        delta_bc = loss_c - loss_b
        results["c_vs_b"] = {
            "delta": round(delta_bc, 4),
            "improvement_pct": round(abs(delta_bc) / loss_b * 100, 2) if loss_b else None,
            "winner": "c_canonical" if delta_bc < 0 else "b_multiview" if delta_bc > 0 else "tie",
        }

    # Overall ranking
    valid = {k: v for k, v in losses.items() if v is not None}
    if valid:
        ranked = sorted(valid.items(), key=lambda x: x[1])
        results["ranking"] = [{"condition": k, "loss": round(v, 4)} for k, v in ranked]
        results["overall_winner"] = ranked[0][0]

    return results


def run_abc_benchmark(
    *,
    path_a: Path,
    path_b: Path,
    path_c: Path,
    artifact_dir: Path,
    output_root: Path,
    model_name: str,
    max_rows: int,
    seed: int,
    allow_cpu_smoke: bool,
) -> dict[str, Any]:
    """Run the full 3-way A/B/C benchmark."""
    accelerator = detect_accelerator()
    plan = build_runtime_plan(accelerator, allow_cpu_smoke=allow_cpu_smoke)

    print(f"Accelerator: {accelerator}")
    print(f"Mode: {plan['mode']}")
    print(f"Max steps: {plan['max_steps']}")
    print()

    # Prepare matched-budget data
    print("Preparing matched-budget datasets...")
    manifest = prepare_matched_budget(
        path_a=path_a,
        path_b=path_b,
        path_c=path_c,
        artifact_dir=artifact_dir,
        max_rows=max_rows,
        seed=seed,
    )
    print(f"  Token budget: {manifest['target_budget']}")
    print(f"  Matched rows: A={manifest['matched_rows']['a']}, "
          f"B={manifest['matched_rows']['b']}, C={manifest['matched_rows']['c']}")
    print()

    run_root = output_root / "code_abc_matched_budget"
    run_root.mkdir(parents=True, exist_ok=True)

    # Train condition A (baseline)
    print("=" * 60)
    print("CONDITION A: Baseline (L3 only)")
    print("=" * 60)
    result_a = train_condition(
        data_path=artifact_dir / "a_baseline_matched.jsonl",
        model_name=model_name,
        output_dir=run_root / "a_baseline",
        plan=plan,
    )
    print(f"  -> Loss: {result_a['final_loss']}")
    print()

    # Train condition B (multiview)
    print("=" * 60)
    print("CONDITION B: Multiview (L0-L3)")
    print("=" * 60)
    result_b = train_condition(
        data_path=artifact_dir / "b_multiview_matched.jsonl",
        model_name=model_name,
        output_dir=run_root / "b_multiview",
        plan=plan,
    )
    print(f"  -> Loss: {result_b['final_loss']}")
    print()

    # Train condition C (canonical)
    print("=" * 60)
    print("CONDITION C: Canonical IR (L-1 + L0-L3)")
    print("=" * 60)
    result_c = train_condition(
        data_path=artifact_dir / "c_canonical_matched.jsonl",
        model_name=model_name,
        output_dir=run_root / "c_canonical",
        plan=plan,
    )
    print(f"  -> Loss: {result_c['final_loss']}")
    print()

    # Summarize
    comparison = summarize_abc(
        result_a.get("final_loss"),
        result_b.get("final_loss"),
        result_c.get("final_loss"),
    )

    summary = {
        "model": model_name,
        "runtime_plan": plan,
        "manifest": manifest,
        "conditions": {
            "a_baseline": result_a,
            "b_multiview": result_b,
            "c_canonical": result_c,
        },
        "comparison": comparison,
    }

    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a", "--baseline", type=Path, default=DEFAULT_A, dest="path_a")
    parser.add_argument("--b", "--multiview", type=Path, default=DEFAULT_B, dest="path_b")
    parser.add_argument("--c", "--canonical", type=Path, default=DEFAULT_C, dest="path_c")
    parser.add_argument(
        "--artifact-dir", type=Path,
        default=REPO_ROOT / "artifacts" / "research" / "code_abc",
    )
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-rows", type=int, default=5000)
    parser.add_argument("--allow-cpu-smoke", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = resolve_output_root(args.output_root)

    print("=" * 60)
    print("SCBE A/B/C CODE BENCHMARK — 3-Way Comparison")
    print("=" * 60)
    print(f"Model: {args.model}")
    print(f"A: {args.path_a}")
    print(f"B: {args.path_b}")
    print(f"C: {args.path_c}")
    print()

    summary = run_abc_benchmark(
        path_a=args.path_a,
        path_b=args.path_b,
        path_c=args.path_c,
        artifact_dir=args.artifact_dir,
        output_root=output_root,
        model_name=args.model,
        max_rows=args.max_rows,
        seed=args.seed,
        allow_cpu_smoke=args.allow_cpu_smoke,
    )

    # Print results
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    comp = summary["comparison"]
    for entry in comp.get("ranking", []):
        marker = " <-- WINNER" if entry["condition"] == comp.get("overall_winner") else ""
        print(f"  {entry['condition']:15s} loss={entry['loss']}{marker}")

    print()
    for key in ("b_vs_a", "c_vs_a", "c_vs_b"):
        if key in comp:
            d = comp[key]
            print(f"  {key}: delta={d['delta']}, improvement={d['improvement_pct']}%, winner={d['winner']}")

    # Save
    summary_path = output_root / "code_abc_matched_budget_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nSummary: {summary_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
