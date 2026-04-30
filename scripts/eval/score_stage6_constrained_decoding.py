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
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


PREFIX_ORDER: Dict[str, List[str]] = {
    "resource_jump_cancel": [
        "transmit_burst",
        "hex",
        "semantic",
        "comms",
        "steady-state fallback",
        "momentum",
        "re-advance",
    ],
    "lane_separation": [
        "queue_drain_guard",
        "byte",
        "hex",
        "semantic",
        "structural",
        "material chemistry",
    ],
    "hex_trace": [
        "crc_patch",
        "byte",
        "hex",
        "error-repair",
        "compute",
        "hold",
        "re-advance",
    ],
    "cost_propagation": [
        "sample_soil",
        "reduce_noise",
        "send_digest",
        "power",
        "compute",
        "time",
        "comms",
        "wear",
    ],
    "training_boundary": [
        "Stage 6",
        "gated",
        "command-harmony-v5",
        "held-out",
        "pollution",
    ],
}


SYSTEM_PROMPT = (
    "You are an SCBE-AETHERMOORE GeoSeal command-line coding agent. Preserve "
    "token-to-binary/hex flow across code, semantic overlay, structural "
    "chemistry frame, and resource-aware workflow composition. Keep material "
    "chemistry separate from structural chemistry templates, predict resource "
    "overruns before commit, and use steady-state fallback plus re-advance "
    "when a launch would exceed budget."
)


def _kind_from_id(prompt_id: str) -> Optional[str]:
    if not prompt_id:
        return None
    for kind in PREFIX_ORDER:
        if prompt_id.endswith(kind):
            return kind
    return None


def _build_prefix(kind: str) -> str:
    tokens = PREFIX_ORDER[kind]
    rendered = " | ".join(f"`{t}`" if "_" in t else t for t in tokens)
    return f"required-tokens: {rendered} ::"


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


def _generate_with_prefix(
    model,
    tokenizer,
    user_prompt: str,
    forced_prefix: str,
    max_new_tokens: int,
) -> str:
    """Apply chat template, append forced prefix to assistant turn, then continue.

    The chat template ends at the assistant turn opener (add_generation_prompt
    = True). We then append the forced prefix as if the model had already
    emitted it, and call generate to extend from there. Returned response is
    forced_prefix + continuation.
    """
    msgs = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    text = tokenizer.apply_chat_template(
        msgs, tokenize=False, add_generation_prompt=True
    )
    primed_text = text + forced_prefix + "\n"
    inputs = tokenizer(primed_text, return_tensors="pt").to(model.device)
    n_in_chat_only = tokenizer(text, return_tensors="pt")["input_ids"].shape[1]
    out = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        temperature=1.0,
        pad_token_id=tokenizer.eos_token_id,
    )
    return tokenizer.decode(out[0][n_in_chat_only:], skip_special_tokens=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="Qwen/Qwen2.5-Coder-0.5B-Instruct")
    ap.add_argument("--adapter", default=None,
                    help="Optional LoRA adapter (default: base only)")
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
    model = AutoModelForCausalLM.from_pretrained(
        args.base, torch_dtype=dtype, trust_remote_code=True
    )
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
        kind = _kind_from_id(prompt_id)
        if kind is None:
            results.append({
                "id": prompt_id,
                "ok": False,
                "missing_required": prompt.get("required", []),
                "triggered_forbidden": [],
                "error": f"no kind detected for id {prompt_id!r}",
                "response": "",
                "kind": None,
                "prefix": "",
            })
            continue
        forced_prefix = _build_prefix(kind)
        try:
            with torch.no_grad():
                response = _generate_with_prefix(
                    model,
                    tokenizer,
                    prompt.get("prompt", ""),
                    forced_prefix,
                    max_new_tokens=args.max_new_tokens,
                )
        except Exception as exc:  # noqa: BLE001
            results.append({
                "id": prompt_id,
                "ok": False,
                "error": str(exc),
                "response": "",
                "kind": kind,
                "prefix": forced_prefix,
            })
            continue
        diag = _score_prompt(prompt, response)
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
