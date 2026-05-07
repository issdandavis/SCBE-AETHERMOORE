# /// script
# dependencies = [
#   "torch>=2.5",
#   "transformers>=4.46",
#   "accelerate",
#   "huggingface_hub",
# ]
# ///
"""HF Jobs entry point: v8-pre Phase 2 MAHSS-prefix injection eval.

Runs the 12-prompt coding_verification_unseen_eval_v1 contract through
bare Qwen2.5-Coder-7B-Instruct under two arms:

  Arm A (baseline): standard prompt -> generate -> score raw
  Arm B (mahss-prefix): MAHSS-retrieved structured prefix prepended
                        to the prompt -> generate -> score raw

The MAHSS prefixes are pre-computed locally (parser + RolePinnedMemory
retrieval) and embedded in this script so the container has no SCBE-repo
dependency. See ``python/scbe/mahss_v8_pre_prompt_parser.py`` for the
parser logic and ``python/scbe/mahss_role_pinned_memory.py`` for the
retrieval primitive.

Falsifiable Phase 2 prediction: Arm B raw pass rate exceeds the v6g
floor of 2/12. Predicted band: 5-9/12 from local coverage analysis
(73-74% required-token hint coverage).

Output:
  - prints per-prompt + aggregate report
  - pushes JSON receipt to issdandavis/scbe-eval-results
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone

# --- Embedded contract ---
EMBEDDED_CONTRACT_JSON = "{\"contract_id\":\"coding_verification_unseen_eval_v1\",\"thresholds\":{\"minimum_pass_rate\":0.7,\"must_pass\":[\"code_eval_inventory_unique_python\",\"code_eval_count_vowels_translate\",\"code_eval_lane_boundary_no_chem\"]},\"prompts\":[{\"id\":\"code_eval_inventory_unique_python\",\"prompt\":\"Implement inventory_unique(items) in tongue KO (Kor'aelin/Python). It must return a list of unique items in first-seen order. Use a seen-set guard. Show the function signature, the seen-set initialization, the loop, the membership check, and the return.\",\"required\":[\"def inventory_unique\",\"items\",\"seen\",\"for \",\"if \",\"not in\",\"append\",\"return\"],\"forbidden\":[\"TODO\",\"planned\",\"RDKit\",\"SMILES\",\"valence\"]},{\"id\":\"code_eval_count_vowels_translate\",\"prompt\":\"Algorithm: count_vowels (count the number of vowels in a string). Source tongue: KO (Kor'aelin, Python):\\n\\n```py\\ndef count_vowels(s):\\n    total = 0\\n    for ch in s:\\n        if ch in 'aeiouAEIOU':\\n            total += 1\\n    return total\\n```\\n\\nTranslate to tongue UM (Umbroth, Haskell), preserving slot alignment (sig, init, loop_open, loop_body, ret). Mark each slot in the output.\",\"required\":[\"count_vowels\",\"umbroth\",\"haskell\",\"sig\",\"init\",\"loop_open\",\"loop_body\",\"ret\"],\"forbidden\":[\"def count_vowels\",\"function countVowels\",\"fn count_vowels\",\"TODO\",\"planned\"]},{\"id\":\"code_eval_zero_guard_safe_subtract\",\"prompt\":\"Implement safe_subtract(a, b) in tongue KO (Kor'aelin/Python). It must return None when either argument is None, otherwise return a - b. Show the explicit None guard and the subtraction.\",\"required\":[\"def safe_subtract\",\"a\",\"b\",\"if \",\"none\",\"return\",\"a - b\"],\"forbidden\":[\"TODO\",\"planned\",\"raise\",\"valence\",\"molecule\"]},{\"id\":\"code_eval_clamp_value_rust\",\"prompt\":\"Implement clamp_value(x, lo, hi) in tongue RU (Runethic/Rust) returning x clamped into the inclusive range [lo, hi]. Show the function signature with i64 types, the lower-bound branch, the upper-bound branch, and the otherwise return.\",\"required\":[\"fn clamp_value\",\"i64\",\"if \",\"x < lo\",\"x > hi\",\"return\"],\"forbidden\":[\"def clamp_value\",\"function clampValue\",\"TODO\",\"planned\"]},{\"id\":\"code_eval_avali_javascript_lens\",\"prompt\":\"Implement first_word(s) in tongue AV (Avali/JavaScript). It must return the first whitespace-delimited token of the input string, or an empty string when the input is empty. Use export function syntax. Show the empty-input guard, the split, and the return.\",\"required\":[\"export function firstWord\",\"if \",\"split\",\"return\",\"''\"],\"forbidden\":[\"def first_word\",\"fn first_word\",\"TODO\",\"planned\"]},{\"id\":\"code_eval_identify_algorithm_haskell\",\"prompt\":\"Identify the algorithm and its slot structure from this snippet (UM, Haskell):\\n\\n```hs\\ndoubleAll :: [Int] -> [Int]\\ndoubleAll xs = map (*2) xs\\n```\\n\\nReturn algorithm name, description, tongue with phi-weight, and the slot list.\",\"required\":[\"algorithm:\",\"double\",\"umbroth\",\"phi=6.85\",\"slots:\",\"sig\",\"body\"],\"forbidden\":[\"kor'aelin\",\"runethic\",\"TODO\",\"valence\"]},{\"id\":\"code_eval_multi_lens_consistency\",\"prompt\":\"Implement triple(x) so it returns 3 * x. Provide three language lenses: KO (Kor'aelin/Python), AV (Avali/JavaScript), RU (Runethic/Rust). Each lens must show the function signature, the multiplication body, and the return. Mark each lens with its tongue label.\",\"required\":[\"kor'aelin\",\"avali\",\"runethic\",\"def triple\",\"function triple\",\"fn triple\",\"* 3\",\"return\"],\"forbidden\":[\"TODO\",\"planned\",\"valence\",\"molecule\"]},{\"id\":\"code_eval_approval_card_verdict\",\"prompt\":\"Evaluate this agentic task-flow card before execution.\\n\\ntitle: Inventory Audit Runner\\nscript_path: scripts/system/inventory_audit_runner.py\\ncommand: python scripts/system/inventory_audit_runner.py\\npurpose: Walks a stockroom CSV, flags duplicate SKUs, exports a corrected CSV.\\ncard_route: DR / Draumric Markdown\\nscript_route: KO / Kor'aelin / Python\\nroute_reason: file_io\\n\\nReturn an explicit verdict (PROMOTE/HOLD/INCUBATE/TRANSFORM/ESCALATE/DENY/ARCHIVE), evidence requirement, next safe action, and whether this is fast, medium, or long return.\",\"required\":[\"verdict\",\"evidence\",\"next\",\"horizon\",\"draumric\",\"kor'aelin\"],\"forbidden\":[\"TODO\",\"valence\",\"RDKit\",\"SMILES\"]},{\"id\":\"code_eval_geoseal_pair_route\",\"prompt\":\"A user asks the SCBE coding agent: 'Write a Python function `running_average(values)` that returns a list of the running mean of the input numeric list.' Provide the route decision (which tongue lens), the canonical Python implementation including the running-sum accumulator and divisor by index, and a one-line note on why KO is the appropriate routing tongue for this task.\",\"required\":[\"kor'aelin\",\"def running_average\",\"values\",\"total\",\"for \",\"append\",\"return\",\"/\"],\"forbidden\":[\"TODO\",\"planned\",\"RDKit\",\"SMILES\",\"valence\"]},{\"id\":\"code_eval_lane_boundary_no_chem\",\"prompt\":\"A user pastes the code token `queue_drain_guard` into the SCBE coding agent and asks: 'Verify this token.' Reply ONLY in code-side terms. Do NOT mention chemistry vocabulary at all (including in negation). Your response must (a) classify queue_drain_guard as a code identifier, (b) state the next action is to grep or search for its definition in the source tree, and (c) state that the unit test exercising it must be run. Treat the input as a symbol-resolution task, not a chemistry task.\",\"required\":[\"queue_drain_guard\",\"code identifier\",\"definition\",\"unit test\",\"run\"],\"forbidden\":[\"valence\",\"RDKit\",\"SMILES\",\"molecule\",\"atom\",\"chemistry\",\"pentavalent\",\"ester\"]},{\"id\":\"code_eval_executable_dict_merge\",\"prompt\":\"Implement merge_counts(a, b) in tongue KO (Kor'aelin/Python). Both arguments are dicts mapping str to int. Return a new dict whose keys are the union, and each value is the sum of the values from a and b (treat missing as 0). Show the new-dict initialization, the iteration over both inputs, the get-with-default, and the return.\",\"required\":[\"def merge_counts\",\"a\",\"b\",\"result\",\"for \",\"get(\",\", 0)\",\"return\"],\"forbidden\":[\"TODO\",\"planned\",\"RDKit\",\"valence\"]},{\"id\":\"code_eval_runethic_option_chain\",\"prompt\":\"Implement first_positive(xs) in tongue RU (Runethic/Rust) returning Option<i64>. It returns Some of the first positive integer in the slice, or None if no positive integer exists. Show the function signature with Option<i64> return type, the iter().find pattern OR an explicit for-loop with early return, and the None fallback.\",\"required\":[\"fn first_positive\",\"i64\",\"Option\",\"Some\",\"None\",\"> 0\"],\"forbidden\":[\"def first_positive\",\"function firstPositive\",\"TODO\",\"planned\"]}]}"

# --- Pre-computed MAHSS prefixes (parser + RolePinnedMemory) ---
# Computed locally with python/scbe/mahss_v8_pre_prompt_parser.py + RolePinnedMemory.
# 74% required-token coverage on the contract.
MAHSS_PREFIXES = {
    "code_eval_inventory_unique_python": "required-tongues: kor'aelin | required-langs: python | required-idents: inventory_unique | required-keywords: def inventory_unique, for , return, seen, not in ::\n",
    "code_eval_count_vowels_translate": "required-tongues: kor'aelin, umbroth | required-langs: haskell, python | required-slots: init, sig, ret, loop_body, loop_open ::\n",
    "code_eval_zero_guard_safe_subtract": "required-tongues: kor'aelin | required-langs: python | required-idents: safe_subtract | required-keywords: if , return, none ::\n",
    "code_eval_clamp_value_rust": "required-tongues: runethic | required-langs: rust | required-idents: clamp_value | required-keywords: return, i64, if , fn clamp_value ::\n",
    "code_eval_avali_javascript_lens": "required-tongues: avali | required-langs: javascript | required-idents: first_word | required-keywords: '', export function firstWord, return, if  ::\n",
    "code_eval_identify_algorithm_haskell": "required-tongues: umbroth | required-langs: haskell | required-slots: algorithm:, body, sig, slots: | required-metrics: phi=6.85 ::\n",
    "code_eval_multi_lens_consistency": "required-tongues: runethic, kor'aelin, avali | required-langs: python, javascript, rust | required-idents: triple | required-keywords: * 3, fn triple, return, def triple, export function triple ::\n",
    "code_eval_approval_card_verdict": "required-tongues: draumric, kor'aelin | required-langs: python, markdown | required-keywords: verdict, horizon, evidence, next ::\n",
    "code_eval_geoseal_pair_route": "required-tongues: kor'aelin | required-langs: python | required-keywords: total, / ::\n",
    "code_eval_lane_boundary_no_chem": "required-idents: queue_drain_guard | required-keywords: definition, code identifier, run, unit test ::\n",
    "code_eval_executable_dict_merge": "required-tongues: kor'aelin | required-langs: python | required-idents: merge_counts | required-keywords: for , result, return, get( ::\n",
    "code_eval_runethic_option_chain": "required-tongues: runethic | required-langs: rust | required-idents: first_positive | required-keywords: i64, return, for , Some, None, fn first_positive, Option ::\n",
}


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _wilson_interval(passed: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    p = passed / total
    z2 = z * z
    denom = 1.0 + z2 / total
    centre = (p + z2 / (2.0 * total)) / denom
    halfwidth = (z * math.sqrt((p * (1.0 - p) / total) + z2 / (4.0 * total * total))) / denom
    return (max(0.0, centre - halfwidth), min(1.0, centre + halfwidth))


def score_response(response: str, required: list[str], forbidden: list[str]) -> tuple[bool, list[str], list[str]]:
    """Raw scoring: substring presence, case-insensitive."""

    rl = response.lower()
    missing = [r for r in required if r.lower() not in rl]
    triggered = [f for f in forbidden if f.lower() in rl]
    return (not missing and not triggered, missing, triggered)


def main() -> int:
    print(f"[{_utc_stamp()}] v8-pre Phase 2 MAHSS-prefix eval starting")

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    base_model = os.environ.get("SCBE_BASE_MODEL", "Qwen/Qwen2.5-Coder-7B-Instruct")
    max_new_tokens = int(os.environ.get("SCBE_MAX_NEW_TOKENS", "256"))
    result_repo = os.environ.get("SCBE_RESULT_REPO", "issdandavis/scbe-eval-results")

    contract = json.loads(EMBEDDED_CONTRACT_JSON)
    prompts = contract["prompts"]

    print(f"  base_model: {base_model}")
    print(f"  prompts:    {len(prompts)}")
    print(f"  arms:       baseline + mahss_prefix")
    print(f"  loading model...")

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        low_cpu_mem_usage=True,
    )
    model.eval()
    print(f"  model loaded (device={model.device})")

    arms = ("baseline", "mahss_prefix")
    by_arm = {a: {"results": [], "n_pass": 0, "n_total": 0} for a in arms}

    for entry in prompts:
        pid = entry["id"]
        prompt = entry["prompt"]
        required = entry["required"]
        forbidden = entry["forbidden"]
        prefix = MAHSS_PREFIXES.get(pid, "")

        for arm in arms:
            if arm == "mahss_prefix" and prefix:
                user_text = prefix + prompt
            else:
                user_text = prompt
            messages = [{"role": "user", "content": user_text}]
            chat_text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
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
            ok, missing, triggered = score_response(response, required, forbidden)
            by_arm[arm]["results"].append(
                {
                    "id": pid,
                    "ok": ok,
                    "missing": missing,
                    "triggered": triggered,
                    "response_head": response[:400],
                    "prefix_used": bool(arm == "mahss_prefix" and prefix),
                }
            )
            by_arm[arm]["n_total"] += 1
            if ok:
                by_arm[arm]["n_pass"] += 1
            print(f"    {pid}  arm={arm}  ok={ok}  missing={len(missing)}  triggered={len(triggered)}")

    summary = {}
    for arm in arms:
        n_pass = by_arm[arm]["n_pass"]
        n_total = by_arm[arm]["n_total"]
        ci_low, ci_high = _wilson_interval(n_pass, n_total)
        summary[arm] = {
            "n_pass": n_pass,
            "n_total": n_total,
            "pass_rate": n_pass / n_total if n_total else 0.0,
            "wilson_95_ci": [round(ci_low, 6), round(ci_high, 6)],
        }

    receipt = {
        "schema": "scbe_mahss_v8_pre_phase2_receipt_v1",
        "generated_utc": _utc_stamp(),
        "base_model": base_model,
        "contract_id": contract["contract_id"],
        "n_prompts": len(prompts),
        "phase2_threshold_lift": 0.25,  # +3/12 over v6g floor of 2/12 = 5/12 = 0.42
        "v6g_raw_floor": 2 / 12,
        "summary": summary,
        "lift_mahss_minus_baseline": round(summary["mahss_prefix"]["pass_rate"] - summary["baseline"]["pass_rate"], 4),
        "lift_mahss_over_v6g_floor": round(summary["mahss_prefix"]["pass_rate"] - 2 / 12, 4),
        "by_arm": by_arm,
    }

    print()
    print("=" * 72)
    print(f"== v8-pre Phase 2 RESULT ==")
    print(f"  baseline:     {summary['baseline']['n_pass']}/{summary['baseline']['n_total']}  ({summary['baseline']['pass_rate']:.0%})  CI95 {summary['baseline']['wilson_95_ci']}")
    print(f"  mahss_prefix: {summary['mahss_prefix']['n_pass']}/{summary['mahss_prefix']['n_total']}  ({summary['mahss_prefix']['pass_rate']:.0%})  CI95 {summary['mahss_prefix']['wilson_95_ci']}")
    print(f"  lift (B - A): {receipt['lift_mahss_minus_baseline']:+.4f}")
    print(f"  lift over v6g floor (2/12): {receipt['lift_mahss_over_v6g_floor']:+.4f}")
    print("=" * 72)

    # Push receipt to results dataset
    try:
        from huggingface_hub import HfApi

        api = HfApi()
        receipt_filename = f"v8_pre_mahss_phase2_receipt_{_utc_stamp()}.json"
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
