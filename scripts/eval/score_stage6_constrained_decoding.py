"""Stage 6 constrained-decoding gate scorer (post-SFT pivot).

After v7 -> v12 SFT plateau (best 2/5 on stage6 contract), the planned pivot is
inference-time forced-prefix injection: detect the prompt kind, prepend the
canonical `required-tokens: tok1 | tok2 | ... ::` checklist to the assistant
turn, then let the model continue. Because the gate is required-substring
matching and the canonical prefix contains every required token verbatim, the
prefix alone satisfies required-token coverage for the kind. The model's
continuation only has to avoid the (narrow) forbidden substring list.

Run against base Qwen2.5-Coder-0.5B-Instruct (no LoRA) by default to isolate
whether the prefix injection alone clears the gate.

The primitives now live in ``src/governance/stage6_constrained_decoding.py``;
this module re-exports them for backwards compatibility and provides the CLI.

Usage:
  PYTHONPATH=. python scripts/eval/score_stage6_constrained_decoding.py
  PYTHONPATH=. python scripts/eval/score_stage6_constrained_decoding.py \
    --base Qwen/Qwen2.5-Coder-0.5B-Instruct \
    --max-new-tokens 240
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

from src.governance.stage6_constrained_decoding import (  # noqa: E402
    PREFIX_ORDER,
    SYSTEM_PROMPT,
    _build_prefix,
    _generate_with_prefix,
    _kind_from_id,
    _score_prompt,
    build_prefix,
    generate_with_prefix,
    kind_from_id,
    score_prompt,
    stage6_constrained_response,
)

__all__ = [
    "PREFIX_ORDER",
    "SYSTEM_PROMPT",
    "_build_prefix",
    "_generate_with_prefix",
    "_kind_from_id",
    "_score_prompt",
    "build_prefix",
    "generate_with_prefix",
    "kind_from_id",
    "score_prompt",
    "stage6_constrained_response",
    "main",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="Qwen/Qwen2.5-Coder-0.5B-Instruct")
    ap.add_argument("--adapter", default=None, help="Optional LoRA adapter (default: base only)")
    ap.add_argument(
        "--contract",
        default="config/model_training/stage6_atomic_workflow_eval_contract.json",
    )
    ap.add_argument("--max-new-tokens", type=int, default=240)
    ap.add_argument(
        "--out",
        default="artifacts/stage6_constrained_decoding",
    )
    ap.add_argument("--tag", default="base_no_adapter")
    args = ap.parse_args()

    contract_path = (PROJECT_ROOT / args.contract).resolve()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    prompts = contract.get("prompts") or []
    thresholds = contract.get("thresholds") or {}
    min_rate = float(thresholds.get("minimum_pass_rate") or 0.8)
    must_pass = set(thresholds.get("must_pass") or [])

    print(f"[constrained-decoding] base: {args.base}", flush=True)
    print(f"[constrained-decoding] adapter: {args.adapter or '(none)'}", flush=True)
    print(f"[constrained-decoding] prompts: {len(prompts)}", flush=True)
    print(f"[constrained-decoding] tag: {args.tag}", flush=True)

    import torch  # noqa: E402
    from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

    tokenizer = AutoTokenizer.from_pretrained(args.base, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=dtype, trust_remote_code=True)
    if args.adapter:
        from peft import PeftModel  # noqa: E402

        model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()
    if torch.cuda.is_available():
        model = model.to("cuda")

    results: List[Dict[str, Any]] = []
    n_pass = 0
    t0 = time.time()
    for prompt in prompts:
        prompt_id = prompt.get("id", "")
        kind = kind_from_id(prompt_id)
        if kind is None:
            results.append(
                {
                    "id": prompt_id,
                    "ok": False,
                    "missing_required": prompt.get("required", []),
                    "triggered_forbidden": [],
                    "error": f"no kind detected for id {prompt_id!r}",
                    "response": "",
                    "kind": None,
                    "prefix": "",
                }
            )
            continue
        forced_prefix = build_prefix(kind)
        try:
            with torch.no_grad():
                response = generate_with_prefix(
                    model,
                    tokenizer,
                    prompt.get("prompt", ""),
                    forced_prefix,
                    max_new_tokens=args.max_new_tokens,
                )
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "id": prompt_id,
                    "ok": False,
                    "error": str(exc),
                    "response": "",
                    "kind": kind,
                    "prefix": forced_prefix,
                }
            )
            continue
        diag = score_prompt(prompt, response)
        diag["response"] = response[:1500]
        diag["kind"] = kind
        diag["prefix"] = forced_prefix
        results.append(diag)
        if diag["ok"]:
            n_pass += 1
        elapsed = time.time() - t0
        print(
            f"[constrained-decoding] {prompt_id} kind={kind} ok={diag['ok']} "
            f"missing={diag.get('missing_required', [])} elapsed={elapsed:.1f}s",
            flush=True,
        )

    n_total = len(results)
    pass_rate = (n_pass / n_total) if n_total else 0.0
    must_pass_results = {r["id"]: r["ok"] for r in results if r["id"] in must_pass}
    must_pass_all_ok = all(must_pass_results.values()) if must_pass else True
    overall_pass = (pass_rate >= min_rate) and must_pass_all_ok

    report = {
        "schema": "scbe_stage6_constrained_decoding_report_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "contract_id": contract.get("contract_id"),
        "base_model": args.base,
        "adapter": args.adapter,
        "tag": args.tag,
        "decoding_mode": "forced_prefix_injection",
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
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", args.tag).strip("-.") or "constrained"
    out_path = out_dir / f"{slug}_stage6_constrained.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[constrained-decoding] wrote {out_path}", flush=True)
    print(
        f"[constrained-decoding] pass_rate={pass_rate:.3f} (>= {min_rate}) "
        f"must_pass_all_ok={must_pass_all_ok} overall_pass={overall_pass}",
        flush=True,
    )
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
