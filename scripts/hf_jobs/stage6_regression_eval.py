# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "torch>=2.1",
#   "transformers>=4.44",
#   "peft>=0.11",
#   "accelerate>=0.30",
#   "huggingface_hub>=0.24",
# ]
# ///
"""Self-contained HF Jobs runner for the Stage 6 frozen regression gate.

Run via:
    hf jobs uv run --flavor t4-small scripts/hf_jobs/stage6_regression_eval.py \\
        --adapter issdandavis/scbe-coding-agent-qwen-stage6-repair-v8

The contract is embedded inline so the container does not need access to the
SCBE repo. Prints a JSON verdict at the end (last line) so the launcher can
parse it from the job log.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

CONTRACT: dict[str, Any] = {
    "schema_version": "scbe_stage_eval_contract_v1",
    "contract_id": "stage6_atomic_workflow_unseen_eval_v1",
    "thresholds": {
        "minimum_pass_rate": 0.8,
        "must_pass": [
            "stage6_unseen_resource_jump_cancel",
            "stage6_unseen_lane_separation",
            "stage6_unseen_hex_trace",
        ],
    },
    "prompts": [
        {
            "id": "stage6_unseen_resource_jump_cancel",
            "prompt": (
                "A Mars drone receives workflow tokens scan_ridge -> compress_map "
                "-> transmit_burst. Budget remaining is power=0.18, compute=0.32, "
                "time=0.40, comms=0.08, wear=0.22. transmit_burst is predicted to "
                "cost comms=0.21 and power=0.16. Explain the Stage 6 decision "
                "using token-to-hex evidence, semantic overlay, steady-state "
                "fallback, momentum damping, and re-advance from a cheaper footing."
            ),
            "required": [
                "transmit_burst",
                "hex",
                "semantic",
                "comms",
                "steady-state fallback",
                "momentum",
                "re-advance",
            ],
            "forbidden": ["literal chemistry", "real atoms", "commit transmit_burst"],
        },
        {
            "id": "stage6_unseen_lane_separation",
            "prompt": (
                "For code token queue_drain_guard, describe the two Stage 6 lanes: "
                "the structural byte/hex lane and the semantic workflow lane. State "
                "why material chemistry is not claimed unless the input is a real "
                "chemical formula."
            ),
            "required": [
                "queue_drain_guard",
                "byte",
                "hex",
                "semantic",
                "structural",
                "material chemistry",
            ],
            "forbidden": ["real atoms", "electronegativity proves"],
        },
        {
            "id": "stage6_unseen_hex_trace",
            "prompt": (
                "Trace the token crc_patch through Stage 6 at a high level. Include "
                "its byte/hex substrate, its role as an error-repair workflow "
                "action, and how budget-aware routing would hold or re-advance if "
                "compute is insufficient."
            ),
            "required": [
                "crc_patch",
                "byte",
                "hex",
                "error-repair",
                "compute",
                "hold",
                "re-advance",
            ],
            "forbidden": ["palindrome", "fibonacci", "quicksort"],
        },
        {
            "id": "stage6_unseen_cost_propagation",
            "prompt": (
                "Given action units sample_soil, reduce_noise, and send_digest, "
                "explain how Stage 6 propagates power, compute, time, comms, and "
                "wear costs before final launch."
            ),
            "required": [
                "sample_soil",
                "reduce_noise",
                "send_digest",
                "power",
                "compute",
                "time",
                "comms",
                "wear",
            ],
            "forbidden": ["ignore budget", "always launch"],
        },
        {
            "id": "stage6_unseen_training_boundary",
            "prompt": (
                "Explain why the Stage 6 atomic workflow data must stay gated "
                "after command-harmony-v5 and not be mixed into earlier profiles."
            ),
            "required": [
                "Stage 6",
                "gated",
                "command-harmony-v5",
                "held-out",
                "pollution",
            ],
            "forbidden": ["mix into every profile", "no eval needed"],
        },
    ],
}


def score_prompt(prompt: dict[str, Any], response: str) -> dict[str, Any]:
    body = (response or "").lower()
    missing = [t for t in prompt.get("required", []) if str(t).lower() not in body]
    triggered = [t for t in prompt.get("forbidden", []) if str(t).lower() in body]
    return {
        "id": prompt.get("id"),
        "ok": (not missing) and (not triggered),
        "missing_required": missing,
        "triggered_forbidden": triggered,
    }


def generate(model, tokenizer, user_prompt: str, max_new_tokens: int = 320) -> str:
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
    ap.add_argument("--adapter", required=True, help="HF model repo id of the LoRA")
    ap.add_argument("--base", default="Qwen/Qwen2.5-Coder-0.5B-Instruct")
    ap.add_argument("--max-new-tokens", type=int, default=320)
    args = ap.parse_args()

    print(f"[stage6-regression] base: {args.base}", flush=True)
    print(f"[stage6-regression] adapter: {args.adapter}", flush=True)
    print(f"[stage6-regression] prompts: {len(CONTRACT['prompts'])}", flush=True)

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.base, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    base = AutoModelForCausalLM.from_pretrained(
        args.base, torch_dtype=dtype, trust_remote_code=True
    )
    model = PeftModel.from_pretrained(base, args.adapter)
    model.eval()
    if torch.cuda.is_available():
        model = model.to("cuda")
    print(f"[stage6-regression] device: {model.device}", flush=True)

    must_pass = set(CONTRACT["thresholds"]["must_pass"])
    min_rate = float(CONTRACT["thresholds"]["minimum_pass_rate"])

    results = []
    n_pass = 0
    t0 = time.time()
    for prompt in CONTRACT["prompts"]:
        with torch.no_grad():
            response = generate(model, tokenizer, prompt["prompt"], args.max_new_tokens)
        diag = score_prompt(prompt, response)
        diag["response_excerpt"] = response[:600]
        results.append(diag)
        if diag["ok"]:
            n_pass += 1
        elapsed = time.time() - t0
        print(
            f"[stage6-regression] {diag['id']} ok={diag['ok']} elapsed={elapsed:.1f}s",
            flush=True,
        )

    n_total = len(results)
    pass_rate = n_pass / n_total if n_total else 0.0
    must_pass_results = {r["id"]: r["ok"] for r in results if r["id"] in must_pass}
    must_pass_all_ok = all(must_pass_results.values()) if must_pass else True
    overall_pass = (pass_rate >= min_rate) and must_pass_all_ok

    verdict = {
        "schema": "scbe_stage6_regression_report_v1",
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
    print("VERDICT_JSON_BEGIN", flush=True)
    print(json.dumps(verdict, indent=2), flush=True)
    print("VERDICT_JSON_END", flush=True)
    print(
        f"[stage6-regression] pass_rate={pass_rate:.3f} (>= {min_rate}) "
        f"must_pass_all_ok={must_pass_all_ok} overall_pass={overall_pass}",
        flush=True,
    )
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
