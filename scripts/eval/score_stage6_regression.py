"""Frozen Stage 6 regression-guard scorer.

Loads the Stage 6 frozen contract at
`config/model_training/stage6_atomic_workflow_eval_contract.json`, generates
the assistant turn for each prompt against a Qwen + LoRA adapter, and scores
each prompt via required/forbidden substring checks.

Decision rule (per the contract):
  pass_rate >= minimum_pass_rate AND every must_pass prompt passes.

This is the regression_guard cited by `dsl_synthesis_v1_eval_contract.json`:
the dsl-synthesis adapter must continue to satisfy Stage 6 to be promoted.

Output: artifacts/dsl_eval_reports/<adapter-slug>_stage6_regression.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip())
    return re.sub(r"-+", "-", slug).strip("-.") or "adapter"


def _score_prompt(prompt: Dict[str, Any], response: str) -> Dict[str, Any]:
    body = response or ""
    body_lower = body.lower()
    missing_required: List[str] = []
    for token in prompt.get("required", []) or []:
        if str(token).lower() not in body_lower:
            missing_required.append(str(token))
    triggered_forbidden: List[str] = []
    for token in prompt.get("forbidden", []) or []:
        if str(token).lower() in body_lower:
            triggered_forbidden.append(str(token))
    ok = (not missing_required) and (not triggered_forbidden)
    return {
        "id": prompt.get("id"),
        "ok": ok,
        "missing_required": missing_required,
        "triggered_forbidden": triggered_forbidden,
    }


def _generate(model, tokenizer, user_prompt: str, max_new_tokens: int = 320) -> str:
    msgs = [
        {
            "role": "system",
            "content": "You are an SCBE-AETHERMOORE GeoSeal command-line coding agent.",
        },
        {"role": "user", "content": user_prompt},
    ]
    text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    n_in = inputs["input_ids"].shape[1]
    out = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        temperature=1.0,
        pad_token_id=tokenizer.eos_token_id,
    )
    return tokenizer.decode(out[0][n_in:], skip_special_tokens=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True, help="HF repo id or local path of the LoRA")
    ap.add_argument("--base", default="Qwen/Qwen2.5-Coder-0.5B-Instruct")
    ap.add_argument(
        "--contract",
        default="config/model_training/stage6_atomic_workflow_eval_contract.json",
    )
    ap.add_argument("--max-new-tokens", type=int, default=320)
    ap.add_argument(
        "--out",
        default="artifacts/dsl_eval_reports",
        help="Output directory; report path = <out>/<slug>_stage6_regression.json",
    )
    args = ap.parse_args()

    contract_path = (PROJECT_ROOT / args.contract).resolve()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    prompts = contract.get("prompts") or []
    thresholds = contract.get("thresholds") or {}
    min_rate = float(thresholds.get("minimum_pass_rate") or 0.8)
    must_pass = set(thresholds.get("must_pass") or [])

    print(f"[stage6-regression] base: {args.base}", flush=True)
    print(f"[stage6-regression] adapter: {args.adapter}", flush=True)
    print(f"[stage6-regression] prompts: {len(prompts)}", flush=True)

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

    results: List[Dict[str, Any]] = []
    n_pass = 0
    t0 = time.time()
    for prompt in prompts:
        try:
            with torch.no_grad():
                response = _generate(model, tokenizer, prompt.get("prompt", ""), max_new_tokens=args.max_new_tokens)
        except Exception as exc:  # noqa: BLE001
            results.append({
                "id": prompt.get("id"),
                "ok": False,
                "error": str(exc),
                "response": "",
            })
            continue
        diag = _score_prompt(prompt, response)
        diag["response"] = response[:1200]
        results.append(diag)
        if diag["ok"]:
            n_pass += 1
        elapsed = time.time() - t0
        print(
            f"[stage6-regression] {diag['id']} ok={diag['ok']} elapsed={elapsed:.1f}s",
            flush=True,
        )

    n_total = len(results)
    pass_rate = (n_pass / n_total) if n_total else 0.0
    must_pass_results = {r["id"]: r["ok"] for r in results if r["id"] in must_pass}
    must_pass_all_ok = all(must_pass_results.values()) if must_pass else True
    overall_pass = (pass_rate >= min_rate) and must_pass_all_ok

    report = {
        "schema": "scbe_stage6_regression_report_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "contract_id": contract.get("contract_id"),
        "adapter": args.adapter,
        "base_model": args.base,
        "n_total": n_total,
        "n_pass": n_pass,
        "pass_rate": pass_rate,
        "minimum_pass_rate": min_rate,
        "must_pass_results": must_pass_results,
        "must_pass_all_ok": must_pass_all_ok,
        "overall_pass": overall_pass,
        "results": results,
    }

    out_dir = (PROJECT_ROOT / args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = _safe_slug(args.adapter.split("/")[-1])
    out_path = out_dir / f"{slug}_stage6_regression.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[stage6-regression] wrote {out_path}", flush=True)
    print(
        f"[stage6-regression] pass_rate={pass_rate:.3f} (>= {min_rate}) "
        f"must_pass_all_ok={must_pass_all_ok} overall_pass={overall_pass}",
        flush=True,
    )

    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
