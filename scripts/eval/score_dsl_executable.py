"""Frozen executable-accuracy scorer for the L_dsl_synthesis lane.

Evaluates a Qwen + LoRA adapter against `bijective_dsl_v1_holdout` per the
contract at `config/model_training/dsl_synthesis_v1_eval_contract.json`:

  * Generates the assistant turn for each holdout record.
  * Parses with `python.scbe.dsl.primitives.parse_program`.
  * Runs against the meta-derived initial state and target shape from
    `scripts/dsl/synthesize_triples._shape_for`.
  * Match = predicted final state's (well, tongue) tuple equals the expected
    shape (well + tongue when the task contract requires both).
  * Reports overall executable_accuracy, per-task-type accuracy, and gate
    pass/fail vs the frozen contract.

Output: artifacts/dsl_eval_reports/<adapter-slug>_executable_accuracy.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python.scbe.dsl.primitives import (  # noqa: E402
    Op,
    initial_state,
    parse_program,
    run_program,
)
from scripts.dsl.synthesize_triples import _shape_for  # noqa: E402


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip())
    return re.sub(r"-+", "-", slug).strip("-.") or "adapter"


def _load_holdout(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _strip_comments(text: str) -> str:
    """Drop trailing `# ...` comment lines per the contract."""
    out = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if line.strip():
            out.append(line)
    return "\n".join(out)


def _category_from_meta(meta: Dict[str, Any]) -> str:
    return str(meta.get("task") or meta.get("category") or "unknown")


def _score_record(
    record: Dict[str, Any],
    predicted_program: str,
) -> Dict[str, Any]:
    """Return per-record diagnostics including pass/fail and failure_mode tag."""
    meta = record.get("meta", {}) or {}
    shape, _realms, init_tongue = _shape_for(meta)
    if shape is None or not init_tongue:
        return {
            "ok": False,
            "failure_mode": "unscoreable_meta",
            "category": _category_from_meta(meta),
        }

    cleaned = _strip_comments(predicted_program)
    try:
        ops: List[Op] = parse_program(cleaned)
    except (ValueError, KeyError) as exc:
        return {
            "ok": False,
            "failure_mode": "unparseable_output",
            "category": _category_from_meta(meta),
            "error": str(exc),
        }

    if any(op.name not in {"tongue_shift", "phi_weight", "mobius_phase",
                            "breath", "compose", "vote", "well_select", "seal"} for op in ops):
        return {
            "ok": False,
            "failure_mode": "extra_primitives",
            "category": _category_from_meta(meta),
        }

    depth_violation = len(ops) > 3
    try:
        final_state = run_program(ops, initial_state(init_tongue))
    except Exception as exc:  # ValueError, RuntimeError, etc.
        return {
            "ok": False,
            "failure_mode": "runtime_error",
            "category": _category_from_meta(meta),
            "error": str(exc),
        }

    well_ok = (shape.well is None) or (final_state.well == shape.well)
    tongue_ok = (shape.tongue is None) or (final_state.tongue == shape.tongue)

    if well_ok and tongue_ok:
        return {
            "ok": True,
            "category": _category_from_meta(meta),
            "depth_violation": depth_violation,
        }

    failure_mode = "wrong_well" if not well_ok else "wrong_tongue"
    return {
        "ok": False,
        "failure_mode": failure_mode,
        "category": _category_from_meta(meta),
        "depth_violation": depth_violation,
        "expected_well": shape.well,
        "actual_well": final_state.well,
        "expected_tongue": shape.tongue,
        "actual_tongue": final_state.tongue,
    }


def _build_prompt(messages: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], str]:
    """Take all non-assistant messages as the prompt, expected = last assistant."""
    prompt_msgs = [m for m in messages if m.get("role") != "assistant"]
    expected = ""
    for m in messages:
        if m.get("role") == "assistant":
            expected = m.get("content", "")
            break
    return prompt_msgs, expected


def _generate(model, tokenizer, prompt_msgs: List[Dict[str, str]], max_new_tokens: int = 96) -> str:
    text = tokenizer.apply_chat_template(prompt_msgs, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    n_in = inputs["input_ids"].shape[1]
    out = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        temperature=1.0,
        pad_token_id=tokenizer.eos_token_id,
    )
    decoded = tokenizer.decode(out[0][n_in:], skip_special_tokens=True)
    return decoded


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True, help="HF repo id or local path of the LoRA")
    ap.add_argument("--base", default="Qwen/Qwen2.5-Coder-0.5B-Instruct")
    ap.add_argument(
        "--holdout",
        default="training-data/sft/bijective_dsl_v1_holdout.sft.jsonl",
    )
    ap.add_argument(
        "--contract",
        default="config/model_training/dsl_synthesis_v1_eval_contract.json",
    )
    ap.add_argument("--limit", type=int, default=0, help="0 = full holdout")
    ap.add_argument("--max-new-tokens", type=int, default=96)
    ap.add_argument(
        "--out",
        default="artifacts/dsl_eval_reports",
        help="Output directory; report path = <out>/<slug>_executable_accuracy.json",
    )
    args = ap.parse_args()

    holdout_path = (PROJECT_ROOT / args.holdout).resolve()
    contract_path = (PROJECT_ROOT / args.contract).resolve()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))

    records = _load_holdout(holdout_path)
    if args.limit:
        records = records[: args.limit]

    print(f"[dsl-eval] holdout records: {len(records)}", flush=True)
    print(f"[dsl-eval] base: {args.base}", flush=True)
    print(f"[dsl-eval] adapter: {args.adapter}", flush=True)

    import torch  # noqa: E402
    from peft import PeftModel  # noqa: E402
    from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

    tokenizer = AutoTokenizer.from_pretrained(args.base, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    base = AutoModelForCausalLM.from_pretrained(
        args.base,
        torch_dtype=dtype,
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(base, args.adapter)
    model.eval()
    if torch.cuda.is_available():
        model = model.to("cuda")

    n_total = 0
    n_pass = 0
    cat_total: Dict[str, int] = defaultdict(int)
    cat_pass: Dict[str, int] = defaultdict(int)
    failure_counts: Dict[str, int] = defaultdict(int)
    sample_diags: List[Dict[str, Any]] = []
    t0 = time.time()
    for idx, rec in enumerate(records):
        msgs = rec.get("messages") or []
        prompt_msgs, expected = _build_prompt(msgs)
        if not prompt_msgs:
            continue
        try:
            with torch.no_grad():
                prediction = _generate(model, tokenizer, prompt_msgs, max_new_tokens=args.max_new_tokens)
        except Exception as exc:
            failure_counts["generation_error"] += 1
            sample_diags.append({"idx": idx, "error": str(exc)})
            continue
        diag = _score_record(rec, prediction)
        n_total += 1
        cat_total[diag["category"]] += 1
        if diag["ok"]:
            n_pass += 1
            cat_pass[diag["category"]] += 1
        else:
            failure_counts[diag.get("failure_mode", "unknown")] += 1
        if idx < 8 or (not diag["ok"] and len(sample_diags) < 24):
            sample_diags.append({
                "idx": idx,
                "category": diag["category"],
                "ok": diag["ok"],
                "failure_mode": diag.get("failure_mode"),
                "expected": expected[:160],
                "predicted": prediction[:240],
            })
        if (idx + 1) % 10 == 0:
            elapsed = time.time() - t0
            print(
                f"[dsl-eval] {idx + 1}/{len(records)} pass={n_pass} acc={n_pass/n_total:.3f} "
                f"elapsed={elapsed:.1f}s",
                flush=True,
            )

    overall = (n_pass / n_total) if n_total else 0.0
    cat_acc: Dict[str, float] = {
        cat: (cat_pass[cat] / cat_total[cat]) if cat_total[cat] else 0.0
        for cat in cat_total
    }

    floors = (contract.get("must_pass_categories") or {}).get("floors") or {}
    floor_failures: List[str] = []
    for cat, floor in floors.items():
        if cat in cat_acc and cat_acc[cat] < floor:
            floor_failures.append(f"{cat}: {cat_acc[cat]:.3f} < {floor}")

    gate = ((contract.get("metrics") or {}).get("executable_accuracy") or {}).get("gate") or 0.50
    overall_pass = overall >= gate
    floor_pass = not floor_failures

    report = {
        "schema": "scbe_dsl_executable_accuracy_report_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "contract_id": contract.get("contract_id"),
        "adapter": args.adapter,
        "base_model": args.base,
        "holdout_path": str(holdout_path.relative_to(PROJECT_ROOT)),
        "n_total": n_total,
        "n_pass": n_pass,
        "executable_accuracy": overall,
        "gate": gate,
        "overall_pass": overall_pass,
        "category_accuracy": cat_acc,
        "category_totals": dict(cat_total),
        "category_passes": dict(cat_pass),
        "floor_violations": floor_failures,
        "floors_pass": floor_pass,
        "decision": (overall_pass and floor_pass),
        "failure_counts": dict(failure_counts),
        "sample_diagnostics": sample_diags,
    }

    out_dir = (PROJECT_ROOT / args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = _safe_slug(args.adapter.split("/")[-1])
    out_path = out_dir / f"{slug}_executable_accuracy.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[dsl-eval] wrote {out_path}", flush=True)
    print(
        f"[dsl-eval] executable_accuracy={overall:.3f} gate={gate} "
        f"overall_pass={overall_pass} floors_pass={floor_pass}",
        flush=True,
    )

    return 0 if (overall_pass and floor_pass) else 1


if __name__ == "__main__":
    raise SystemExit(main())
