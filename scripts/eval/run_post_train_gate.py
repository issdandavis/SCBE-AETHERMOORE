#!/usr/bin/env python3
"""Run the post-train gate against an adapter's pre-generated candidate responses.

Splits the gate workflow into two steps so generation is decoupled from scoring:

1. Generation lives elsewhere (Kaggle output, HF Inference, local vLLM, manual).
   Whatever produced the candidate responses writes a JSON file shaped::

       {
         "candidates": [
           {
             "candidate_id": "scbe-chemistry-0.5b-qlora-v5",
             "metadata": {"adapter_repo": "issdandavis/...", "step": 180},
             "responses": {"chem_eval_ethanol_route": "...", ...}
           },
           ...
         ]
       }

2. This runner loads the contract separately and combines them into the
   shape that ``scripts/eval/double_blind_training_eval`` accepts, runs the
   double-blind round, writes the report, and exits non-zero if any
   candidate fails its ``minimum_pass_rate`` or ``must_pass`` threshold.

The split exists so the contract stays a stable, version-pinned source of
truth and the candidate file becomes the per-run artifact. It also means
the runner has zero model dependencies (no torch, no transformers).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.eval.double_blind_training_eval import (  # noqa: E402
    build_double_blind_round,
    write_report,
)

DEFAULT_CONTRACT = REPO_ROOT / "config" / "model_training" / "chemistry_verification_eval_contract.json"
DEFAULT_OUT = REPO_ROOT / "artifacts" / "eval" / "post_train_gate_latest.json"


def load_contract(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"contract at {path} must be a JSON object")
    if not isinstance(payload.get("prompts"), list) or not payload["prompts"]:
        raise ValueError(f"contract at {path} missing non-empty 'prompts' list")
    return payload


def load_candidates(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("candidates"), list):
        raise ValueError(f"candidates at {path} must be a JSON object with a 'candidates' list")
    if not payload["candidates"]:
        raise ValueError(f"candidates at {path} has empty 'candidates' list")
    return payload["candidates"]


def build_payload(contract: dict[str, Any], candidates: list[dict[str, Any]], seed: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "scbe_double_blind_eval_input_v1",
        "contract": contract,
        "candidates": candidates,
    }
    if seed:
        payload["seed"] = seed
    return payload


def evaluate(
    contract_path: Path,
    candidates_path: Path,
    out_path: Path,
    *,
    seed: str | None = None,
) -> dict[str, Any]:
    contract = load_contract(contract_path)
    candidates = load_candidates(candidates_path)
    payload = build_payload(contract, candidates, seed)
    report = build_double_blind_round(payload)
    write_report(report, out_path)
    return report


def gate_passed(report: dict[str, Any]) -> bool:
    return all(row.get("overall_pass") for row in report.get("candidate_results", []))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT, help="path to eval contract JSON")
    parser.add_argument("--candidates", type=Path, required=True, help="path to candidate responses JSON")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="report output path")
    parser.add_argument("--seed", type=str, default=None, help="optional explicit seed for blind shuffle")
    parser.add_argument("--json", action="store_true", help="print full report JSON instead of summary")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = evaluate(args.contract, args.candidates, args.out, seed=args.seed)
    if args.json:
        print(json.dumps({**report, "artifact_path": str(args.out)}, indent=2, sort_keys=True, ensure_ascii=True))
    else:
        passed = sum(1 for row in report["candidate_results"] if row["overall_pass"])
        thresholds = report.get("contract_id", "<unknown>")
        print(
            f"post-train gate: contract={thresholds} candidates={report['candidate_count']} "
            f"passed={passed}/{report['candidate_count']} report={args.out}"
        )
        for row in report["candidate_results"]:
            verdict = "PASS" if row["overall_pass"] else "FAIL"
            print(
                f"  {verdict} {row['candidate_id']}: "
                f"pass_rate={row['pass_rate']:.3f} (>= {row['minimum_pass_rate']}) "
                f"must_pass_all_ok={row['must_pass_all_ok']}"
            )
    return 0 if gate_passed(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
