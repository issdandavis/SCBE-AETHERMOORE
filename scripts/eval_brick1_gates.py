"""Brick 1 gate evaluator — per docs/BRICK1_CONTINUAL_LEARNING_PLAN.md §4.

Loads the Brick 1 final LoRA adapter on top of the frozen base model, runs the
same structural benchmark + drill map eval that Brick 0 used, compares against
the committed Brick 0 baseline, and emits a gate report with pass/fail per gate.

Gates (absolute fractions, NOT deltas):

  G1 structural overall validator_pass_rate  target >= 0.70  floor >= 0.60
  G2 causal_transform    validator_pass_rate  target >= 0.60  floor >= 0.40
  G3 route_governance    validator_pass_rate  target >= 0.40  floor >= 0.25
  G4 KO tongue           validator_pass_rate  target >= 0.55  floor >= 0.45
  G5 braid_helix         validator_pass_rate  target >= 0.90  floor >= 0.85
  G6 drill map eval      avg_loss within +/- 2% of Brick 0 baseline

Exit codes:
    0 - all six gates pass at target level
    1 - any gate below target but all above hard floor (amber)
    2 - any gate below hard floor (red; stop, investigate)
    3 - setup/io error (adapter or baseline missing)

Usage:
    python scripts/eval_brick1_gates.py
    python scripts/eval_brick1_gates.py --adapter artifacts/tongue-table-lora-brick1-v1/lora_final
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_ADAPTER = REPO_ROOT / "artifacts" / "tongue-table-lora-brick1-v1" / "lora_final"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "tongue-table-lora-brick1-v1" / "brick1_gate_report.json"
DEFAULT_BASE_MODEL = "Qwen/Qwen2.5-0.5B"
DEFAULT_DATA = REPO_ROOT / "data" / "tongue_drill" / "drill_langues_full.jsonl"
BRICK0_ROOT = REPO_ROOT / "artifacts" / "tongue-table-lora-brick0-v5"
BRICK0_STRUCT = BRICK0_ROOT / "final_structural_benchmark.json"
BRICK0_DRILL = BRICK0_ROOT / "final_drill_map_eval.json"

GATE_SPEC = {
    "G1_structural_overall": {"target": 0.70, "floor": 0.60, "source": "structural.summary.validator_pass_rate"},
    "G2_causal_transform":   {"target": 0.60, "floor": 0.40, "source": "structural.by_stage.causal_transform.validator_pass_rate"},
    "G3_route_governance":   {"target": 0.40, "floor": 0.25, "source": "structural.by_stage.route_governance.validator_pass_rate"},
    "G4_KO_tongue":          {"target": 0.55, "floor": 0.45, "source": "structural.by_tongue.KO.validator_pass_rate"},
    "G5_braid_helix":        {"target": 0.90, "floor": 0.85, "source": "structural.by_stage.braid_helix.validator_pass_rate"},
    "G6_drill_map_loss":     {"tolerance": 0.02, "source": "drill._summary.avg_loss"},
}


def _dig(obj: Any, dotted: str) -> Any:
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _load_brick1_model(adapter_dir: Path, base_model: str, device: str):
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    dtype = torch.float16 if device == "cuda" else torch.float32
    base = AutoModelForCausalLM.from_pretrained(
        base_model,
        low_cpu_mem_usage=True,
        dtype=dtype,
    )
    model = PeftModel.from_pretrained(base, str(adapter_dir), is_trainable=False)
    if device != "cpu":
        model = model.to(device)
    model.eval()
    return tokenizer, model


def _evaluate_gate(name: str, spec: dict, brick1_val: float | None, brick0_val: float | None) -> dict:
    if brick1_val is None:
        return {
            "gate": name,
            "status": "MISSING",
            "brick1_value": None,
            "brick0_value": brick0_val,
            "reason": f"metric not present in structural/drill summary ({spec.get('source')})",
        }

    if "tolerance" in spec:
        tol = spec["tolerance"]
        if brick0_val is None or brick0_val <= 0:
            return {
                "gate": name,
                "status": "MISSING",
                "brick1_value": brick1_val,
                "brick0_value": brick0_val,
                "reason": "Brick 0 baseline missing or zero; tolerance gate needs a non-zero anchor",
            }
        delta = (brick1_val - brick0_val) / brick0_val
        status = "PASS" if abs(delta) <= tol else "FAIL"
        return {
            "gate": name,
            "status": status,
            "brick1_value": brick1_val,
            "brick0_value": brick0_val,
            "relative_delta": delta,
            "tolerance": tol,
            "reason": f"|delta|={abs(delta):.4f} vs tolerance={tol:.4f}",
        }

    target = spec["target"]
    floor = spec["floor"]
    if brick1_val >= target:
        status = "PASS"
    elif brick1_val >= floor:
        status = "AMBER"
    else:
        status = "FAIL"
    return {
        "gate": name,
        "status": status,
        "brick1_value": brick1_val,
        "brick0_value": brick0_val,
        "target": target,
        "floor": floor,
        "reason": f"value={brick1_val:.4f} vs target={target} floor={floor}",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", type=Path, default=DEFAULT_ADAPTER)
    ap.add_argument("--base_model", default=DEFAULT_BASE_MODEL)
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--holdout_mod", type=int, default=10)
    ap.add_argument("--holdout_bucket", type=int, default=0)
    ap.add_argument("--max_per_stage", type=int, default=12)
    ap.add_argument("--max_per_cell", type=int, default=10)
    ap.add_argument("--max_length", type=int, default=256)
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args(argv)

    if not args.adapter.exists():
        print(f"[GATE] adapter missing: {args.adapter}", file=sys.stderr)
        return 3
    if not BRICK0_STRUCT.exists() or not BRICK0_DRILL.exists():
        print(f"[GATE] Brick 0 baseline JSONs missing under {BRICK0_ROOT}", file=sys.stderr)
        return 3

    brick0_struct = json.loads(BRICK0_STRUCT.read_text(encoding="utf-8"))
    brick0_drill = json.loads(BRICK0_DRILL.read_text(encoding="utf-8"))

    print(f"[GATE] loading Brick 1 adapter: {args.adapter}")
    t0 = time.perf_counter()
    tokenizer, model = _load_brick1_model(args.adapter, args.base_model, args.device)
    print(f"[GATE] model loaded in {time.perf_counter() - t0:.1f}s")

    from scripts.train.lora_tongue_table import (
        run_drill_map_eval,
        run_structural_benchmark_eval,
    )

    print(f"[GATE] running structural benchmark (holdout {args.holdout_bucket}/{args.holdout_mod})")
    t1 = time.perf_counter()
    struct_summary = run_structural_benchmark_eval(
        model,
        tokenizer,
        data_path=str(args.data),
        split="holdout",
        holdout_mod=args.holdout_mod,
        holdout_bucket=args.holdout_bucket,
        max_per_stage=args.max_per_stage,
    )
    print(f"[GATE] structural benchmark done in {time.perf_counter() - t1:.1f}s")

    print("[GATE] running drill map eval (holdout)")
    t2 = time.perf_counter()
    drill_summary = run_drill_map_eval(
        model,
        tokenizer,
        data_path=str(args.data),
        split="holdout",
        holdout_mod=args.holdout_mod,
        holdout_bucket=args.holdout_bucket,
        max_per_cell=args.max_per_cell,
        max_length=args.max_length,
    )
    print(f"[GATE] drill map eval done in {time.perf_counter() - t2:.1f}s")

    brick1_bundle = {"structural": struct_summary, "drill": drill_summary}
    brick0_bundle = {"structural": brick0_struct, "drill": brick0_drill}

    gate_results: list[dict] = []
    worst = "PASS"
    rank = {"PASS": 0, "AMBER": 1, "FAIL": 2, "MISSING": 2}
    for gate_name, spec in GATE_SPEC.items():
        brick1_val = _dig(brick1_bundle, spec["source"])
        brick0_val = _dig(brick0_bundle, spec["source"])
        if isinstance(brick1_val, (int, float)):
            brick1_val = float(brick1_val)
        else:
            brick1_val = None
        if isinstance(brick0_val, (int, float)):
            brick0_val = float(brick0_val)
        else:
            brick0_val = None
        result = _evaluate_gate(gate_name, spec, brick1_val, brick0_val)
        gate_results.append(result)
        if rank[result["status"]] > rank[worst]:
            worst = result["status"]

    overall_status = {
        "PASS": "ALL_GATES_PASS",
        "AMBER": "AMBER_BELOW_TARGET_ABOVE_FLOOR",
        "FAIL": "RED_BELOW_FLOOR",
        "MISSING": "MISSING_METRIC",
    }[worst]

    report = {
        "schema_version": "brick1_gate_report_v1",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "adapter": str(args.adapter.resolve()),
        "base_model": args.base_model,
        "data": str(args.data.resolve()),
        "holdout": {"mod": args.holdout_mod, "bucket": args.holdout_bucket},
        "brick0_reference": {
            "structural": str(BRICK0_STRUCT.resolve()),
            "drill": str(BRICK0_DRILL.resolve()),
        },
        "overall_status": overall_status,
        "gates": gate_results,
        "brick1_structural_summary": struct_summary.get("summary"),
        "brick1_by_stage": struct_summary.get("by_stage"),
        "brick1_by_tongue": struct_summary.get("by_tongue"),
        "brick1_drill_summary": drill_summary.get("_summary"),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print()
    print(f"=== BRICK 1 GATE REPORT ({overall_status}) ===")
    for r in gate_results:
        bv = r.get("brick1_value")
        bv_str = f"{bv:.4f}" if isinstance(bv, float) else "N/A"
        print(f"  [{r['status']:7s}] {r['gate']:22s} brick1={bv_str}  {r['reason']}")
    print(f"wrote: {args.output}")

    return {"PASS": 0, "AMBER": 1, "FAIL": 2, "MISSING": 2}[worst]


if __name__ == "__main__":
    raise SystemExit(main())
