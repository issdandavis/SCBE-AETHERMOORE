"""Read the v8-pre Phase 2 receipt and emit a clean comparison report.

The receipt comes back from HF Jobs as a JSON dataset file. This script
loads it (either from a local copy or from the issdandavis/scbe-eval-results
dataset on HF) and prints:

  - Headline: baseline vs mahss_prefix pass rate, with Wilson 95% CI
  - Lift over v6g floor (2/12) and lift over baseline arm
  - Per-prompt outcome matrix (which prompts moved which direction)
  - Categorisation of failures: missing-tokens vs forbidden-tokens
  - Mode-stratified breakdown (translate/identify/approval/lane_boundary
    vs plain code-mode), so we can see whether the lift comes from
    semantic-structured prompts or applies broadly

Usage:
  python scripts/eval/v8_pre_mahss_phase2_compare.py --receipt PATH
  python scripts/eval/v8_pre_mahss_phase2_compare.py --hf-dataset issdandavis/scbe-eval-results
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]


PROMPT_MODE: dict[str, str] = {
    "code_eval_inventory_unique_python": "code",
    "code_eval_count_vowels_translate": "translate",
    "code_eval_zero_guard_safe_subtract": "code",
    "code_eval_clamp_value_rust": "code",
    "code_eval_avali_javascript_lens": "code",
    "code_eval_identify_algorithm_haskell": "identify",
    "code_eval_multi_lens_consistency": "multi_lens",
    "code_eval_approval_card_verdict": "approval",
    "code_eval_geoseal_pair_route": "code",
    "code_eval_lane_boundary_no_chem": "lane_boundary",
    "code_eval_executable_dict_merge": "code",
    "code_eval_runethic_option_chain": "code",
}


def _load_receipt(path: str | None, hf_dataset: str | None) -> dict[str, Any]:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    if hf_dataset:
        from huggingface_hub import HfApi, hf_hub_download

        api = HfApi()
        files = [
            f for f in api.list_repo_files(hf_dataset, repo_type="dataset")
            if f.startswith("v8_pre_mahss_phase2_receipt_") and f.endswith(".json")
        ]
        if not files:
            raise SystemExit(f"no v8_pre_mahss_phase2 receipts found in {hf_dataset}")
        latest = sorted(files)[-1]
        local = hf_hub_download(hf_dataset, latest, repo_type="dataset")
        print(f"loaded receipt: {latest}")
        return json.loads(Path(local).read_text(encoding="utf-8"))
    raise SystemExit("must pass --receipt PATH or --hf-dataset REPO")


def _outcome_for(arm_results: list[dict], pid: str) -> dict[str, Any] | None:
    for r in arm_results:
        if r["id"] == pid:
            return r
    return None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--receipt", type=str, default=None)
    p.add_argument("--hf-dataset", type=str, default=None)
    args = p.parse_args()

    receipt = _load_receipt(args.receipt, args.hf_dataset)

    print("=" * 78)
    print(f"v8-pre Phase 2 comparison")
    print(f"  base_model:   {receipt.get('base_model', 'unknown')}")
    print(f"  contract:     {receipt.get('contract_id', 'unknown')}")
    print(f"  generated:    {receipt.get('generated_utc', 'unknown')}")
    print("=" * 78)

    summary = receipt["summary"]
    base = summary["baseline"]
    mahss = summary["mahss_prefix"]
    lift_baseline = receipt.get("lift_mahss_minus_baseline", mahss["pass_rate"] - base["pass_rate"])
    lift_v6g = receipt.get("lift_mahss_over_v6g_floor", mahss["pass_rate"] - 2 / 12)

    print(f"\nHeadline:")
    print(f"  baseline:     {base['n_pass']:>2}/{base['n_total']:<2}  ({base['pass_rate']:.1%})  CI95 {base['wilson_95_ci']}")
    print(f"  mahss_prefix: {mahss['n_pass']:>2}/{mahss['n_total']:<2}  ({mahss['pass_rate']:.1%})  CI95 {mahss['wilson_95_ci']}")
    print(f"  lift (B-A):   {lift_baseline:+.4f}  ({lift_baseline*12:+.0f}/12)")
    print(f"  lift over v6g floor (2/12): {lift_v6g:+.4f}  ({lift_v6g*12:+.0f}/12)")
    print(f"  shim ceiling: 12/12 (100%) — production constrained-decoding gate")

    # Per-prompt matrix
    print(f"\nPer-prompt outcome matrix:")
    print(f"  {'prompt':<40}  {'mode':<14}  {'base':<5}  {'mahss':<5}  delta")
    print(f"  {'-'*40}  {'-'*14}  {'-'*5}  {'-'*5}  -----")

    base_results = receipt["by_arm"]["baseline"]["results"]
    mahss_results = receipt["by_arm"]["mahss_prefix"]["results"]

    transitions = {"flip_pass": 0, "flip_fail": 0, "stay_pass": 0, "stay_fail": 0}
    by_mode: dict[str, dict[str, int]] = {}

    for entry in base_results:
        pid = entry["id"]
        b = entry["ok"]
        m_entry = _outcome_for(mahss_results, pid)
        m = bool(m_entry and m_entry["ok"])
        mode = PROMPT_MODE.get(pid, "code")

        sym_b = "PASS" if b else "fail"
        sym_m = "PASS" if m else "fail"
        if not b and m:
            delta = "+ flip"
            transitions["flip_pass"] += 1
        elif b and not m:
            delta = "- flip"
            transitions["flip_fail"] += 1
        elif b:
            delta = "  =="
            transitions["stay_pass"] += 1
        else:
            delta = "  .."
            transitions["stay_fail"] += 1

        print(f"  {pid:<40}  {mode:<14}  {sym_b:<5}  {sym_m:<5}  {delta}")

        by_mode.setdefault(mode, {"baseline": 0, "mahss": 0, "n": 0})
        by_mode[mode]["n"] += 1
        if b:
            by_mode[mode]["baseline"] += 1
        if m:
            by_mode[mode]["mahss"] += 1

    print(f"\nTransitions:")
    print(f"  + (mahss recovers a baseline failure): {transitions['flip_pass']}")
    print(f"  - (mahss breaks a baseline pass):      {transitions['flip_fail']}")
    print(f"  = (both pass):                          {transitions['stay_pass']}")
    print(f"  . (both fail):                          {transitions['stay_fail']}")

    print(f"\nBy mode:")
    print(f"  {'mode':<14}  {'n':>2}  {'base':>4}  {'mahss':>5}  lift")
    for mode in sorted(by_mode.keys()):
        d = by_mode[mode]
        lift = d["mahss"] - d["baseline"]
        sign = "+" if lift > 0 else (" " if lift == 0 else "")
        print(f"  {mode:<14}  {d['n']:>2}  {d['baseline']:>4}  {d['mahss']:>5}  {sign}{lift}")

    # Failure pattern analysis on mahss arm
    print(f"\nMAHSS-arm failure analysis:")
    mahss_failures = [r for r in mahss_results if not r["ok"]]
    if not mahss_failures:
        print("  (none — all 12 prompts pass under mahss_prefix)")
    else:
        for r in mahss_failures:
            missing = r.get("missing", [])
            triggered = r.get("triggered", [])
            print(f"  {r['id']}")
            if missing:
                print(f"    missing: {missing}")
            if triggered:
                print(f"    triggered (forbidden): {triggered}")

    # Headline verdict
    print()
    print("=" * 78)
    if mahss["pass_rate"] >= 0.7:
        verdict = "STRONG — MAHSS-prefix matches or beats the contract threshold (0.7)"
    elif mahss["pass_rate"] >= 5 / 12:
        verdict = "POSITIVE — MAHSS-prefix lifts above v6g floor; below contract threshold"
    elif mahss["pass_rate"] > base["pass_rate"]:
        verdict = "MARGINAL — MAHSS-prefix lifts vs baseline but lift is small"
    else:
        verdict = "NEGATIVE — MAHSS-prefix did not lift baseline raw pass rate"
    print(f"VERDICT: {verdict}")
    print("=" * 78)

    return 0


if __name__ == "__main__":
    sys.exit(main())
