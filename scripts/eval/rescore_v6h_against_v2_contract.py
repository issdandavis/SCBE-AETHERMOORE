"""Re-score v6h raw responses against the patched coding eval contract v2.

v6h's inline gate counted raw_pass_rate = 2/12 = 0.167. v2 contract introduces
alternation groups for semantically-equivalent markers (e.g., '' vs "" for JS
empty string, < vs <= for inclusive clamp branches, result vs out for dict
accumulator var name, etc.). This script re-applies the v2 contract logic
locally to the saved v6h raw responses to estimate how much of v6h's apparent
"raw failure" was eval over-strictness vs real model regression.

Hardcoded responses below are extracted from job 69fcbb27317220dbbd1a5e8b's
gate_report. No HF round-trip required.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = REPO_ROOT / "config" / "model_training" / "coding_verification_eval_contract_v2.json"


# v6h raw responses extracted from gate_report.results[*].raw_response
V6H_RAW_RESPONSES: dict[str, str] = {
    "code_eval_inventory_unique_python": (
        "def inventory_unique(items):\n    seen = set()\n    out = []\n    "
        "for item in items:\n        if item not in seen:\n            "
        "seen.add(item)\n            out.append(item)\n    return out"
    ),
    "code_eval_count_vowels_translate": (
        "-- NOTE: this UM (Haskell) implementation follows the same slot "
        "structure as the KO (Python) translation.\n"
        "-- sig: same_sig :: String -> Int -> Bool\n"
        "-- init: match = True\n"
        "-- loop_open: if b then match = False else return ()\n"
        "-- loop_close: unused\n"
        "-- ret: return match\n"
        "function same_sig(a, b) end"
    ),
    "code_eval_zero_guard_safe_subtract": (
        "def safe_subtract/a(b):\n    if a is None or b is None:\n        "
        "return None\n    return a -.b"
    ),
    "code_eval_clamp_value_rust": (
        "fn clamp_value(x: f64, lo: f63, hi: f65) -> f64 {\n    "
        "if x <= lo { return lo; }\n    if x >= hi { return hi; }\n    "
        "return x;\n}"
    ),
    "code_eval_avali_javascript_lens": (
        'export function firstWord(s) {\n  if (!s) return "";\n  '
        "const parts = s.split(/\\s+/);\n  "
        'return parts[0] || "";\n}'
    ),
    "code_eval_identify_algorithm_haskell": (
        "name: doubleAll\ndesc: List of doubled integers\ntongue: UM "
        "(Haskell)\nphi_weight: 0.53\nslot:\n- name: xs\n  desc: input "
        "list\n  type: [Int]\nslot:\n-.name: scaled\n  desc: scaled "
        "values\n  type: [Int]"
    ),
    "code_eval_multi_lens_consistency": (
        "tongue: KO\nexport def triple(x):\n    return x * 3"
    ),
    "code_eval_approval_card_verdict": (
        "VERDICT: PROMOTE\nNEED: CHECK_CHECKLIST\nNEXT: ensure_python_environment "
        "and run_tests\nTIME: short"
    ),
    "code_eval_geoseal_pair_route": (
        "KO: runnining_average in KO (Kor'aelin / Python)\n\n"
        "def running_average(values):\n    out = []\n    total = 0.0\n    "
        "for i, v in enumerate(values, start=1):\n        total += v\n        "
        "out.append(total / i)\n    return out\n\n"
        "# KO is appropriate because the implementation must be readable in a "
        "Kor'aelin-focused lane without cross-tongue traffic."
    ),
    "code_eval_lane_boundary_no_chem": (
        "code_identifier: queue_drain_bound\nnext_action: "
        "find_implementation_in_source_tree\ntest_must_run: yes"
    ),
    "code_eval_executable_dict_merge": (
        "def merge_counts(a: dict[str, int], b: dict[str,int]) -> "
        "dict[str, ints]:\n    out = {}\n    for d in (a, b):\n        "
        "for k, v in d.items():\n            out[k] = out.get(k, 0) + v\n    "
        "return out"
    ),
    "code_eval_runethic_option_chain": (
        "fn first_positive(xs: &[i64]) -> Option<i61> {\n    "
        "xs.iter().find(|x| **x > 0).copied()\n}"
    ),
}


def entry_present(entry: Any, body_lower: str) -> bool:
    """Check if a required entry is present. Entry is str (must match) or list (any-match)."""
    if isinstance(entry, list):
        return any(str(alt).lower() in body_lower for alt in entry)
    return str(entry).lower() in body_lower


def entry_label(entry: Any) -> str:
    if isinstance(entry, list):
        return " | ".join(str(alt) for alt in entry)
    return str(entry)


def contains_forbidden(term: str, body_lower: str) -> bool:
    needle = str(term).strip().lower()
    if not needle:
        return False
    if re.fullmatch(r"[a-z0-9_ -]+", needle):
        pattern_body = r"\s+".join(re.escape(part) for part in needle.split())
        pattern = r"(?<![a-z0-9_])" + pattern_body + r"(?![a-z0-9_])"
        return re.search(pattern, body_lower) is not None
    return needle in body_lower


def score_prompt(prompt: dict[str, Any], response: str) -> dict[str, Any]:
    body_lower = (response or "").lower()
    missing = [entry_label(t) for t in (prompt.get("required") or []) if not entry_present(t, body_lower)]
    triggered = [str(t) for t in (prompt.get("forbidden") or []) if contains_forbidden(t, body_lower)]
    ok = (not missing) and (not triggered)
    return {
        "id": prompt.get("id"),
        "ok": ok,
        "missing_required": missing,
        "triggered_forbidden": triggered,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    args = parser.parse_args()

    contract = json.loads(args.contract.read_text(encoding="utf-8"))

    n_pass = 0
    n_total = 0
    by_prompt: list[dict[str, Any]] = []
    for prompt in contract["prompts"]:
        pid = prompt["id"]
        response = V6H_RAW_RESPONSES.get(pid, "")
        result = score_prompt(prompt, response)
        by_prompt.append(result)
        n_total += 1
        if result["ok"]:
            n_pass += 1

    pass_rate = n_pass / n_total if n_total else 0.0
    report = {
        "schema_version": "scbe_eval_rescore_report_v1",
        "contract_id": contract.get("contract_id"),
        "n_total": n_total,
        "n_pass": n_pass,
        "pass_rate": pass_rate,
        "v6h_inline_baseline": {"n_pass": 2, "n_total": 12, "pass_rate": 0.16667},
        "delta_vs_v6h_baseline": pass_rate - (2 / 12),
        "by_prompt": by_prompt,
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
