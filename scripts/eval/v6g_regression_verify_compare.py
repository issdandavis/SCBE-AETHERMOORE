"""Read the v6g regression-verify receipt and emit a clean comparison.

Companion to scripts/eval/hf_job_v6g_regression_verify.py. Loads the
JSON receipt (local file or scbe-eval-results dataset) and prints:

  - Headline: bare vs v6g pass rate, regression magnitude
  - Per-prompt outcome matrix (which prompts the adapter broke)
  - Decision rule: regression confirmed / partial / neutral / inverted
  - Phase 2 cross-check: does this match the 7/12 vs 2/12 disparity?
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load_receipt(path: str | None, hf_dataset: str | None) -> dict[str, Any]:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    if hf_dataset:
        from huggingface_hub import HfApi, hf_hub_download

        api = HfApi()
        files = [
            f for f in api.list_repo_files(hf_dataset, repo_type="dataset")
            if f.startswith("v6g_regression_verify_receipt_") and f.endswith(".json")
        ]
        if not files:
            raise SystemExit(f"no v6g_regression_verify receipts in {hf_dataset}")
        latest = sorted(files)[-1]
        local = hf_hub_download(hf_dataset, latest, repo_type="dataset")
        print(f"loaded receipt: {latest}")
        return json.loads(Path(local).read_text(encoding="utf-8"))
    raise SystemExit("must pass --receipt PATH or --hf-dataset REPO")


def _outcome_for(arm: list[dict], pid: str) -> dict[str, Any] | None:
    for r in arm:
        if r["id"] == pid:
            return r
    return None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--receipt", type=str, default=None)
    p.add_argument("--hf-dataset", type=str, default=None)
    args = p.parse_args()

    r = _load_receipt(args.receipt, args.hf_dataset)
    arm_a = r["arm_bare"]
    arm_b = r["arm_v6g"]
    delta_count = arm_a["n_pass"] - arm_b["n_pass"]
    delta_pct = arm_a["pass_rate"] - arm_b["pass_rate"]

    print("=" * 78)
    print("v6g regression verification")
    print(f"  base_model:    {r.get('base_model', '?')}")
    print(f"  v6g_adapter:   {r.get('v6g_adapter', '?')}")
    print(f"  contract:      {r.get('contract_id', '?')}")
    print(f"  generated:     {r.get('generated_utc', '?')}")
    print("=" * 78)

    print(f"\nHeadline:")
    print(f"  Arm A (bare):  {arm_a['n_pass']:>2}/{arm_a['n_total']:<2}  ({arm_a['pass_rate']:.1%})  CI95 {arm_a['wilson_95_ci']}")
    print(f"  Arm B (v6g):   {arm_b['n_pass']:>2}/{arm_b['n_total']:<2}  ({arm_b['pass_rate']:.1%})  CI95 {arm_b['wilson_95_ci']}")
    print(f"  Delta (A-B):   {delta_count:+d}/12  ({delta_pct*100:+.1f}pp)")

    print(f"\nPer-prompt outcome:")
    print(f"  {'prompt':<42}  {'bare':<5}  {'v6g':<5}  delta")
    print(f"  {'-'*42}  {'-'*5}  {'-'*5}  -----")

    transitions = {"regress": 0, "rescue": 0, "stay_pass": 0, "stay_fail": 0}
    for entry in arm_a["results"]:
        pid = entry["id"]
        b = entry["ok"]
        v = _outcome_for(arm_b["results"], pid)
        v_ok = bool(v and v["ok"])
        sym_b = "PASS" if b else "fail"
        sym_v = "PASS" if v_ok else "fail"
        if b and not v_ok:
            tag = "- regress"
            transitions["regress"] += 1
        elif not b and v_ok:
            tag = "+ rescue"
            transitions["rescue"] += 1
        elif b:
            tag = "  =="
            transitions["stay_pass"] += 1
        else:
            tag = "  .."
            transitions["stay_fail"] += 1
        print(f"  {pid:<42}  {sym_b:<5}  {sym_v:<5}  {tag}")

    print(f"\nTransitions:")
    print(f"  - regress (bare PASS, v6g fail):  {transitions['regress']}")
    print(f"  + rescue  (bare fail, v6g PASS):  {transitions['rescue']}")
    print(f"  =         both PASS:              {transitions['stay_pass']}")
    print(f"  .         both fail:              {transitions['stay_fail']}")

    # Headline verdict
    print()
    print("=" * 78)
    if delta_count >= 4:
        verdict = f"REGRESSION CONFIRMED — v6g hurts raw pass rate by {delta_count}/12 ({delta_pct*100:.1f}pp). SFT-against-this-contract is the wrong tool."
    elif delta_count >= 2:
        verdict = f"PARTIAL REGRESSION — v6g hurts by {delta_count}/12. Smaller than the 5/12 the original gate suggested but still negative."
    elif delta_count >= -1:
        verdict = "NEUTRAL — v6g and bare base perform within measurement noise. Original 2/12 number was likely a different decode path."
    else:
        verdict = f"v6g HELPS — bare base scores {-delta_count}/12 LOWER than v6g. Regression interpretation was wrong; need to re-explain v6g gate's 2/12."
    print(f"VERDICT: {verdict}")
    print("=" * 78)

    # Phase 2 cross-check
    print(f"\nPhase 2 cross-check:")
    print(f"  Phase 2 reported bare = 7/12 (this run: {arm_a['n_pass']}/12)")
    print(f"  v6g shipping gate reported 2/12 raw (this run: {arm_b['n_pass']}/12)")
    matches_phase2 = (abs(arm_a['n_pass'] - 7) <= 1) and (abs(arm_b['n_pass'] - 2) <= 1)
    if matches_phase2:
        print(f"  -> matches Phase 2 disparity within 1/12; regression is real, not artifact")
    else:
        print(f"  -> diverges from Phase 2; one or both numbers were measurement-path-dependent")

    return 0


if __name__ == "__main__":
    sys.exit(main())
