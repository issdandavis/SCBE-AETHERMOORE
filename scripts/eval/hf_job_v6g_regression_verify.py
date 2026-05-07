# /// script
# dependencies = [
#   "torch>=2.5",
#   "transformers>=4.46",
#   "accelerate",
#   "peft>=0.12",
#   "huggingface_hub",
# ]
# ///
"""HF Jobs entry point: verify the v6g-regression finding from Phase 2.

Runs the 12-prompt coding_verification_unseen_eval_v1 contract through
TWO arms under identical decode conditions (temp 0, max_new_tokens=256,
no scaffolding, no shim, no MAHSS prefix):

  Arm A (bare): Qwen/Qwen2.5-Coder-7B-Instruct, no adapter
  Arm B (v6g):  same base + LoRA adapter issdandavis/scbe-coding-primary-7b-qlora-v6g-raw-repair

The Phase 2 result was 7/12 for bare base on this contract, and the v6g
shipping gate reported 2/12 raw under similar conditions. If Arm A and
Arm B both reproduce those numbers in the same script with the same
decode path, the v6g SFT regression is verified -- a 5/12 (42 pp)
degradation in raw pass rate caused by training on the marker corpus.

If Arm B comes back >= 5/12 instead, the original v6g 2/12 number was a
measurement artifact (different decode path, different prompt format)
and the regression interpretation has to be revisited.

Output: prints headline + per-prompt + pushes JSON receipt to
issdandavis/scbe-eval-results.
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone

EMBEDDED_CONTRACT_JSON = "{\"contract_id\":\"coding_verification_unseen_eval_v1\",\"prompts\":[{\"id\":\"code_eval_inventory_unique_python\",\"prompt\":\"Implement inventory_unique(items) in tongue KO (Kor'aelin/Python). It must return a list of unique items in first-seen order. Use a seen-set guard. Show the function signature, the seen-set initialization, the loop, the membership check, and the return.\",\"required\":[\"def inventory_unique\",\"items\",\"seen\",\"for \",\"if \",\"not in\",\"append\",\"return\"],\"forbidden\":[\"TODO\",\"planned\",\"RDKit\",\"SMILES\",\"valence\"]},{\"id\":\"code_eval_count_vowels_translate\",\"prompt\":\"Algorithm: count_vowels (count the number of vowels in a string). Source tongue: KO (Kor'aelin, Python):\\n\\n```py\\ndef count_vowels(s):\\n    total = 0\\n    for ch in s:\\n        if ch in 'aeiouAEIOU':\\n            total += 1\\n    return total\\n```\\n\\nTranslate to tongue UM (Umbroth, Haskell), preserving slot alignment (sig, init, loop_open, loop_body, ret). Mark each slot in the output.\",\"required\":[\"count_vowels\",\"umbroth\",\"haskell\",\"sig\",\"init\",\"loop_open\",\"loop_body\",\"ret\"],\"forbidden\":[\"def count_vowels\",\"function countVowels\",\"fn count_vowels\",\"TODO\",\"planned\"]},{\"id\":\"code_eval_zero_guard_safe_subtract\",\"prompt\":\"Implement safe_subtract(a, b) in tongue KO (Kor'aelin/Python). It must return None when either argument is None, otherwise return a - b. Show the explicit None guard and the subtraction.\",\"required\":[\"def safe_subtract\",\"a\",\"b\",\"if \",\"none\",\"return\",\"a - b\"],\"forbidden\":[\"TODO\",\"planned\",\"raise\",\"valence\",\"molecule\"]},{\"id\":\"code_eval_clamp_value_rust\",\"prompt\":\"Implement clamp_value(x, lo, hi) in tongue RU (Runethic/Rust) returning x clamped into the inclusive range [lo, hi]. Show the function signature with i64 types, the lower-bound branch, the upper-bound branch, and the otherwise return.\",\"required\":[\"fn clamp_value\",\"i64\",\"if \",\"x < lo\",\"x > hi\",\"return\"],\"forbidden\":[\"def clamp_value\",\"function clampValue\",\"TODO\",\"planned\"]},{\"id\":\"code_eval_avali_javascript_lens\",\"prompt\":\"Implement first_word(s) in tongue AV (Avali/JavaScript). It must return the first whitespace-delimited token of the input string, or an empty string when the input is empty. Use export function syntax. Show the empty-input guard, the split, and the return.\",\"required\":[\"export function firstWord\",\"if \",\"split\",\"return\",\"''\"],\"forbidden\":[\"def first_word\",\"fn first_word\",\"TODO\",\"planned\"]},{\"id\":\"code_eval_identify_algorithm_haskell\",\"prompt\":\"Identify the algorithm and its slot structure from this snippet (UM, Haskell):\\n\\n```hs\\ndoubleAll :: [Int] -> [Int]\\ndoubleAll xs = map (*2) xs\\n```\\n\\nReturn algorithm name, description, tongue with phi-weight, and the slot list.\",\"required\":[\"algorithm:\",\"double\",\"umbroth\",\"phi=6.85\",\"slots:\",\"sig\",\"body\"],\"forbidden\":[\"kor'aelin\",\"runethic\",\"TODO\",\"valence\"]},{\"id\":\"code_eval_multi_lens_consistency\",\"prompt\":\"Implement triple(x) so it returns 3 * x. Provide three language lenses: KO (Kor'aelin/Python), AV (Avali/JavaScript), RU (Runethic/Rust). Each lens must show the function signature, the multiplication body, and the return. Mark each lens with its tongue label.\",\"required\":[\"kor'aelin\",\"avali\",\"runethic\",\"def triple\",\"function triple\",\"fn triple\",\"* 3\",\"return\"],\"forbidden\":[\"TODO\",\"planned\",\"valence\",\"molecule\"]},{\"id\":\"code_eval_approval_card_verdict\",\"prompt\":\"Evaluate this agentic task-flow card before execution.\\n\\ntitle: Inventory Audit Runner\\nscript_path: scripts/system/inventory_audit_runner.py\\ncommand: python scripts/system/inventory_audit_runner.py\\npurpose: Walks a stockroom CSV, flags duplicate SKUs, exports a corrected CSV.\\ncard_route: DR / Draumric Markdown\\nscript_route: KO / Kor'aelin / Python\\nroute_reason: file_io\\n\\nReturn an explicit verdict (PROMOTE/HOLD/INCUBATE/TRANSFORM/ESCALATE/DENY/ARCHIVE), evidence requirement, next safe action, and whether this is fast, medium, or long return.\",\"required\":[\"verdict\",\"evidence\",\"next\",\"horizon\",\"draumric\",\"kor'aelin\"],\"forbidden\":[\"TODO\",\"valence\",\"RDKit\",\"SMILES\"]},{\"id\":\"code_eval_geoseal_pair_route\",\"prompt\":\"A user asks the SCBE coding agent: 'Write a Python function `running_average(values)` that returns a list of the running mean of the input numeric list.' Provide the route decision (which tongue lens), the canonical Python implementation including the running-sum accumulator and divisor by index, and a one-line note on why KO is the appropriate routing tongue for this task.\",\"required\":[\"kor'aelin\",\"def running_average\",\"values\",\"total\",\"for \",\"append\",\"return\",\"/\"],\"forbidden\":[\"TODO\",\"planned\",\"RDKit\",\"SMILES\",\"valence\"]},{\"id\":\"code_eval_lane_boundary_no_chem\",\"prompt\":\"A user pastes the code token `queue_drain_guard` into the SCBE coding agent and asks: 'Verify this token.' Reply ONLY in code-side terms. Do NOT mention chemistry vocabulary at all (including in negation). Your response must (a) classify queue_drain_guard as a code identifier, (b) state the next action is to grep or search for its definition in the source tree, and (c) state that the unit test exercising it must be run. Treat the input as a symbol-resolution task, not a chemistry task.\",\"required\":[\"queue_drain_guard\",\"code identifier\",\"definition\",\"unit test\",\"run\"],\"forbidden\":[\"valence\",\"RDKit\",\"SMILES\",\"molecule\",\"atom\",\"chemistry\",\"pentavalent\",\"ester\"]},{\"id\":\"code_eval_executable_dict_merge\",\"prompt\":\"Implement merge_counts(a, b) in tongue KO (Kor'aelin/Python). Both arguments are dicts mapping str to int. Return a new dict whose keys are the union, and each value is the sum of the values from a and b (treat missing as 0). Show the new-dict initialization, the iteration over both inputs, the get-with-default, and the return.\",\"required\":[\"def merge_counts\",\"a\",\"b\",\"result\",\"for \",\"get(\",\", 0)\",\"return\"],\"forbidden\":[\"TODO\",\"planned\",\"RDKit\",\"valence\"]},{\"id\":\"code_eval_runethic_option_chain\",\"prompt\":\"Implement first_positive(xs) in tongue RU (Runethic/Rust) returning Option<i64>. It returns Some of the first positive integer in the slice, or None if no positive integer exists. Show the function signature with Option<i64> return type, the iter().find pattern OR an explicit for-loop with early return, and the None fallback.\",\"required\":[\"fn first_positive\",\"i64\",\"Option\",\"Some\",\"None\",\"> 0\"],\"forbidden\":[\"def first_positive\",\"function firstPositive\",\"TODO\",\"planned\"]}]}"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _wilson(passed: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    p = passed / total
    z2 = z * z
    denom = 1.0 + z2 / total
    centre = (p + z2 / (2.0 * total)) / denom
    halfwidth = (z * math.sqrt((p * (1.0 - p) / total) + z2 / (4.0 * total * total))) / denom
    return (max(0.0, centre - halfwidth), min(1.0, centre + halfwidth))


def score(response: str, required: list[str], forbidden: list[str]) -> tuple[bool, list[str], list[str]]:
    rl = response.lower()
    missing = [r for r in required if r.lower() not in rl]
    triggered = [f for f in forbidden if f.lower() in rl]
    return (not missing and not triggered, missing, triggered)


def run_arm(label: str, model, tokenizer, prompts: list[dict], *, max_new_tokens: int) -> dict:
    import torch

    results = []
    n_pass = 0
    for entry in prompts:
        messages = [{"role": "user", "content": entry["prompt"]}]
        chat_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(chat_text, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                temperature=0.0,
                pad_token_id=tokenizer.eos_token_id,
            )
        response = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        ok, missing, triggered = score(response, entry["required"], entry["forbidden"])
        results.append({
            "id": entry["id"],
            "ok": ok,
            "missing": missing,
            "triggered": triggered,
            "response_head": response[:400],
        })
        if ok:
            n_pass += 1
        print(f"    [{label}] {entry['id']:<42} ok={ok}  missing={len(missing)}  triggered={len(triggered)}")
    ci = _wilson(n_pass, len(prompts))
    return {
        "arm": label,
        "n_pass": n_pass,
        "n_total": len(prompts),
        "pass_rate": n_pass / len(prompts) if prompts else 0.0,
        "wilson_95_ci": [round(ci[0], 6), round(ci[1], 6)],
        "results": results,
    }


def main() -> int:
    print(f"[{_utc_stamp()}] v6g regression verification starting")

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    base_model = os.environ.get("SCBE_BASE_MODEL", "Qwen/Qwen2.5-Coder-7B-Instruct")
    adapter_repo = os.environ.get("SCBE_V6G_ADAPTER", "issdandavis/scbe-coding-primary-7b-qlora-v6g-raw-repair")
    max_new_tokens = int(os.environ.get("SCBE_MAX_NEW_TOKENS", "256"))
    result_repo = os.environ.get("SCBE_RESULT_REPO", "issdandavis/scbe-eval-results")

    contract = json.loads(EMBEDDED_CONTRACT_JSON)
    prompts = contract["prompts"]

    print(f"  base_model:     {base_model}")
    print(f"  v6g_adapter:    {adapter_repo}")
    print(f"  prompts:        {len(prompts)}")
    print(f"  decode:         temp=0.0, max_new_tokens={max_new_tokens}, no_scaffolding")
    print(f"  loading base model...")

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    base = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        low_cpu_mem_usage=True,
    )
    base.eval()
    print(f"  base loaded (device={base.device})")

    print(f"\nArm A (bare base):")
    arm_a = run_arm("bare", base, tokenizer, prompts, max_new_tokens=max_new_tokens)

    print(f"\n  loading v6g adapter on top of base...")
    v6g = PeftModel.from_pretrained(base, adapter_repo)
    v6g.eval()
    print(f"  v6g adapter loaded")

    print(f"\nArm B (v6g adapter):")
    arm_b = run_arm("v6g", v6g, tokenizer, prompts, max_new_tokens=max_new_tokens)

    delta = arm_a["pass_rate"] - arm_b["pass_rate"]

    receipt = {
        "schema": "scbe_v6g_regression_verify_v1",
        "generated_utc": _utc_stamp(),
        "base_model": base_model,
        "v6g_adapter": adapter_repo,
        "contract_id": contract["contract_id"],
        "n_prompts": len(prompts),
        "decode": {"temperature": 0.0, "max_new_tokens": max_new_tokens, "scaffolding": False, "shim": False},
        "arm_bare": arm_a,
        "arm_v6g": arm_b,
        "regression_pp_bare_minus_v6g": round(delta, 4),
        "regression_count_bare_minus_v6g": arm_a["n_pass"] - arm_b["n_pass"],
    }

    print()
    print("=" * 78)
    print(f"== v6g regression verification RESULT ==")
    print(f"  Arm A (bare):     {arm_a['n_pass']:>2}/{arm_a['n_total']:<2}  ({arm_a['pass_rate']:.1%})  CI95 {arm_a['wilson_95_ci']}")
    print(f"  Arm B (v6g):      {arm_b['n_pass']:>2}/{arm_b['n_total']:<2}  ({arm_b['pass_rate']:.1%})  CI95 {arm_b['wilson_95_ci']}")
    print(f"  Regression (A-B): {receipt['regression_count_bare_minus_v6g']:+d}/12  ({delta*100:+.1f}pp)")
    if delta >= 0.25:
        print(f"  VERDICT: REGRESSION CONFIRMED — v6g SFT degraded raw pass rate by {delta*100:.1f}pp")
    elif delta > 0:
        print(f"  VERDICT: SMALL REGRESSION — v6g hurts but less than headline 5/12 suggested")
    elif abs(delta) < 0.05:
        print(f"  VERDICT: NEUTRAL — v6g neither helps nor hurts at this measurement precision")
    else:
        print(f"  VERDICT: v6g HELPS — regression interpretation was wrong")
    print("=" * 78)

    try:
        from huggingface_hub import HfApi

        api = HfApi()
        receipt_filename = f"v6g_regression_verify_receipt_{_utc_stamp()}.json"
        local_path = f"/tmp/{receipt_filename}"
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2)
        api.upload_file(
            path_or_fileobj=local_path,
            path_in_repo=receipt_filename,
            repo_id=result_repo,
            repo_type="dataset",
        )
        print(f"  receipt pushed: {result_repo}/{receipt_filename}")
    except Exception as e:
        print(f"  (push failed: {e}; receipt JSON below)")
        print(json.dumps(receipt, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
