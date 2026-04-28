"""Boosted executable-accuracy scorer for the L_dsl_synthesis lane.

Wraps the v1 scorer logic with an optional constrained-decoding pass that is
only engaged when the variable-booster (`TrendGrowthBooster`) decides, based
on in-session and prior-session telemetry, that the adapter has under-grown
relative to expectation. Latches once fired.

Booster modes (CLI flag `--booster`):
  off    : never wrap generate()
  on     : always wrap generate() with the regex-grammar logits processor
  auto   : replay the adapter's *_training_curve_*.json file through the
           booster, fire if expectation shortfall is detected, then act.

When engaged, generation goes through `lm-format-enforcer` if available, else
falls back to a post-hoc regex extractor that strips the longest leading run
matching the SCBE DSL grammar before scoring (cheap, still A/B-meaningful).

Output: artifacts/dsl_eval_reports/<adapter-slug>_executable_accuracy_boosted.json
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

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
from src.training.callbacks.trend_growth_booster import DSL_GRAMMAR, TrendGrowthBooster  # noqa: E402

ALLOWED_OPS = {"tongue_shift", "phi_weight", "mobius_phase", "breath", "compose", "vote", "well_select", "seal"}
_DSL_LINE_RE = re.compile(
    r"^(?:well_select\([A-Z][A-Z0-9_]*\)|tongue_shift\([A-Z]+ -> [A-Z]+\)|seal\(\))$"
)


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip())
    return re.sub(r"-+", "-", slug).strip("-.") or "adapter"


def _load_holdout(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _strip_comments(text: str) -> str:
    rows: list[str] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if line.strip():
            rows.append(line)
    return "\n".join(rows)


def _category(meta: Dict[str, Any]) -> str:
    return str(meta.get("task") or meta.get("category") or "unknown")


def _build_prompt(messages: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], str]:
    prompt_msgs = [m for m in messages if m.get("role") != "assistant"]
    expected = ""
    for m in messages:
        if m.get("role") == "assistant":
            expected = m.get("content", "")
            break
    return prompt_msgs, expected


def _post_hoc_grammar_filter(text: str) -> str:
    """Fallback boost: keep only leading lines that match the DSL line grammar."""
    cleaned = _strip_comments(text)
    kept: list[str] = []
    for line in cleaned.splitlines():
        if _DSL_LINE_RE.match(line.strip()):
            kept.append(line.strip())
        else:
            break
    return "\n".join(kept)


def _try_load_lmfe(grammar: str):
    try:
        # lmformatenforcer 0.11.3 imports PreTrainedTokenizerBase from the legacy
        # `transformers.tokenization_utils` path; newer transformers expose it on
        # `tokenization_utils_base`. Bridge the two before importing the integration.
        import transformers.tokenization_utils as _tok_legacy
        import transformers.tokenization_utils_base as _tok_base
        if not hasattr(_tok_legacy, "PreTrainedTokenizerBase"):
            _tok_legacy.PreTrainedTokenizerBase = _tok_base.PreTrainedTokenizerBase  # type: ignore[attr-defined]
        lmfe = importlib.import_module("lmformatenforcer")
        integrations = importlib.import_module("lmformatenforcer.integrations.transformers")
    except Exception:
        return None
    try:
        parser = lmfe.RegexParser(grammar)
        return integrations, parser
    except Exception:
        return None


def _score_record(record: Dict[str, Any], predicted_program: str) -> Dict[str, Any]:
    meta = record.get("meta", {}) or {}
    shape, _realms, init_tongue = _shape_for(meta)
    if shape is None or not init_tongue:
        return {"ok": False, "failure_mode": "unscoreable_meta", "category": _category(meta)}
    cleaned = _strip_comments(predicted_program)
    try:
        ops: List[Op] = parse_program(cleaned)
    except (ValueError, KeyError) as exc:
        return {"ok": False, "failure_mode": "unparseable_output", "category": _category(meta), "error": str(exc)}
    if any(op.name not in ALLOWED_OPS for op in ops):
        return {"ok": False, "failure_mode": "extra_primitives", "category": _category(meta)}
    try:
        final_state = run_program(ops, initial_state(init_tongue))
    except Exception as exc:
        return {"ok": False, "failure_mode": "runtime_error", "category": _category(meta), "error": str(exc)}
    well_ok = (shape.well is None) or (final_state.well == shape.well)
    tongue_ok = (shape.tongue is None) or (final_state.tongue == shape.tongue)
    if well_ok and tongue_ok:
        return {"ok": True, "category": _category(meta)}
    return {
        "ok": False,
        "failure_mode": "wrong_well" if not well_ok else "wrong_tongue",
        "category": _category(meta),
        "expected_well": shape.well,
        "actual_well": final_state.well,
        "expected_tongue": shape.tongue,
        "actual_tongue": final_state.tongue,
    }


def _generate(
    model,
    tokenizer,
    prompt_msgs,
    *,
    max_new_tokens: int,
    booster_engaged: bool,
    lmfe_handles,
):
    text = tokenizer.apply_chat_template(prompt_msgs, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    n_in = inputs["input_ids"].shape[1]
    gen_kwargs = dict(
        max_new_tokens=max_new_tokens,
        do_sample=False,
        temperature=1.0,
        pad_token_id=tokenizer.eos_token_id,
    )
    if booster_engaged and lmfe_handles is not None:
        integrations, parser = lmfe_handles
        try:
            prefix_fn = integrations.build_transformers_prefix_allowed_tokens_fn(tokenizer, parser)
            gen_kwargs["prefix_allowed_tokens_fn"] = prefix_fn
        except Exception:
            pass
    out = model.generate(**inputs, **gen_kwargs)
    decoded = tokenizer.decode(out[0][n_in:], skip_special_tokens=True)
    if booster_engaged and lmfe_handles is None:
        decoded = _post_hoc_grammar_filter(decoded)
    return decoded


def _replay_booster_on_adapter(
    booster: TrendGrowthBooster,
    adapter_path: str,
    reports_dir: Path,
) -> dict:
    slug_keys = [Path(adapter_path).name]
    matches: list[Path] = []
    for key in slug_keys:
        matches.extend(reports_dir.glob(f"*{key}*training_curve*.json"))
    if not matches:
        return {"replayed": False, "reason": "no matching training_curve report"}
    latest = max(matches, key=lambda p: p.stat().st_mtime)
    payload = json.loads(latest.read_text(encoding="utf-8"))
    metrics = payload.get("metrics") or []
    fake_log: list[dict] = []
    decisions: list[dict] = []
    for i, m in enumerate(metrics):
        if not isinstance(m, dict):
            continue
        entry = {"step": float(m.get("epoch", i)), **{k: v for k, v in m.items() if isinstance(v, (int, float))}}
        fake_log.append(entry)
        decisions.append(booster.evaluate(list(fake_log)))
    return {
        "replayed": True,
        "report": str(latest),
        "n_metrics": len(metrics),
        "engaged_after_replay": booster.is_engaged(),
        "last_decision": decisions[-1] if decisions else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--base", default="Qwen/Qwen2.5-Coder-0.5B-Instruct")
    ap.add_argument("--holdout", default="training-data/sft/bijective_dsl_v5_holdout.sft.jsonl")
    ap.add_argument("--contract", default="config/model_training/dsl_synthesis_v1_eval_contract.json")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-new-tokens", type=int, default=96)
    ap.add_argument("--out", default="artifacts/dsl_eval_reports")
    ap.add_argument("--booster", choices=["off", "on", "auto"], default="auto")
    ap.add_argument(
        "--prior-reports-dir",
        default="artifacts/training_reports",
        help="Source for prior-session slope baseline.",
    )
    args = ap.parse_args()

    holdout_path = (PROJECT_ROOT / args.holdout).resolve()
    contract_path = (PROJECT_ROOT / args.contract).resolve()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    records = _load_holdout(holdout_path)
    if args.limit:
        records = records[: args.limit]
    print(f"[dsl-eval-boosted] holdout records: {len(records)}", flush=True)
    print(f"[dsl-eval-boosted] base: {args.base}", flush=True)
    print(f"[dsl-eval-boosted] adapter: {args.adapter}", flush=True)
    print(f"[dsl-eval-boosted] booster mode: {args.booster}", flush=True)

    booster = TrendGrowthBooster(prior_reports_dir=args.prior_reports_dir)
    booster_meta: dict[str, Any] = {"mode": args.booster}
    if args.booster == "on":
        booster._engaged = True
    elif args.booster == "auto":
        booster_meta["replay"] = _replay_booster_on_adapter(
            booster, args.adapter, PROJECT_ROOT / args.prior_reports_dir
        )
    booster_meta["engaged"] = booster.is_engaged()
    booster_meta["grammar"] = DSL_GRAMMAR

    lmfe_handles = _try_load_lmfe(DSL_GRAMMAR) if booster.is_engaged() else None
    booster_meta["lm_format_enforcer_available"] = lmfe_handles is not None

    import torch  # noqa: E402
    from peft import PeftModel  # noqa: E402
    from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

    tokenizer = AutoTokenizer.from_pretrained(args.base, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    base = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=dtype, trust_remote_code=True)
    model = PeftModel.from_pretrained(base, args.adapter)
    model.eval()
    if torch.cuda.is_available():
        model = model.to("cuda")

    n_total = 0
    n_pass = 0
    cat_total: Dict[str, int] = defaultdict(int)
    cat_pass: Dict[str, int] = defaultdict(int)
    failure_counts: Dict[str, int] = defaultdict(int)
    sample_diags: list[dict] = []
    t0 = time.time()
    for idx, rec in enumerate(records):
        msgs = rec.get("messages") or []
        prompt_msgs, expected = _build_prompt(msgs)
        if not prompt_msgs:
            continue
        try:
            with torch.no_grad():
                prediction = _generate(
                    model,
                    tokenizer,
                    prompt_msgs,
                    max_new_tokens=args.max_new_tokens,
                    booster_engaged=booster.is_engaged(),
                    lmfe_handles=lmfe_handles,
                )
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
            sample_diags.append(
                {
                    "idx": idx,
                    "category": diag["category"],
                    "ok": diag["ok"],
                    "failure_mode": diag.get("failure_mode"),
                    "expected": expected[:160],
                    "predicted": prediction[:240],
                }
            )
        if (idx + 1) % 10 == 0:
            elapsed = time.time() - t0
            print(
                f"[dsl-eval-boosted] {idx + 1}/{len(records)} pass={n_pass} "
                f"acc={(n_pass / n_total):.3f} elapsed={elapsed:.1f}s",
                flush=True,
            )

    overall = (n_pass / n_total) if n_total else 0.0
    cat_acc = {c: (cat_pass[c] / cat_total[c]) if cat_total[c] else 0.0 for c in cat_total}
    floors = (contract.get("must_pass_categories") or {}).get("floors") or {}
    floor_failures = [f"{c}: {cat_acc[c]:.3f} < {f}" for c, f in floors.items() if c in cat_acc and cat_acc[c] < f]
    gate = ((contract.get("metrics") or {}).get("executable_accuracy") or {}).get("gate") or 0.50
    overall_pass = overall >= gate
    floor_pass = not floor_failures

    report = {
        "schema": "scbe_dsl_executable_accuracy_boosted_report_v1",
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
        "booster": booster_meta,
        "sample_diagnostics": sample_diags,
    }
    out_dir = (PROJECT_ROOT / args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = _safe_slug(args.adapter.split("/")[-1])
    out_path = out_dir / f"{slug}_executable_accuracy_boosted.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[dsl-eval-boosted] wrote {out_path}", flush=True)
    print(
        f"[dsl-eval-boosted] executable_accuracy={overall:.3f} gate={gate} "
        f"overall_pass={overall_pass} floors_pass={floor_pass} "
        f"booster_engaged={booster.is_engaged()}",
        flush=True,
    )
    return 0 if (overall_pass and floor_pass) else 1


if __name__ == "__main__":
    raise SystemExit(main())
