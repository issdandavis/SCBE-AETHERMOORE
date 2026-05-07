"""Run executable_coding_v1_holdout problems against a candidate-responses JSON.

Scores by EXECUTION not by markers. For each holdout problem:
1. Extract the first ```python ... ``` code block from the candidate response.
2. Append the test calls. Run in a subprocess with timeout.
3. Compare stdout (repr of each call) to expected.
4. Pass = all tests for that problem succeed.

Usage:
    python scripts/eval/run_executable_coding_holdout.py \\
        --candidates artifacts/v6h_holdout_responses.json \\
        --out artifacts/eval/v6h_executable_eval.json

Candidate JSON format:
    {
      "candidate_id": "scbe-coding-primary-7b-qlora-v6h-executable",
      "responses": {
        "inventory_unique": "```python\\ndef inventory_unique(items):\\n    ...\\n```",
        ...
      }
    }

This script has zero model dependencies — generation lives elsewhere
(HF Inference API, vLLM, manual eval). It just scores execution.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "artifacts" / "eval" / "executable_coding_holdout_latest.json"

# Reuse the canonical PROBLEMS table from the shard builder so the holdout
# tests stay in one place. If that file moves, this import path moves with it.
sys.path.insert(0, str(REPO_ROOT / "scripts" / "training_data"))
from build_executable_coding_v1_sft import PROBLEMS  # noqa: E402

CODE_BLOCK_RE = re.compile(r"```(?:python)?\s*\n?(.*?)```", re.DOTALL)


def extract_code(response: str) -> str:
    """Pull the first python code block. Falls back to the whole response."""
    if not response:
        return ""
    m = CODE_BLOCK_RE.search(response)
    if m:
        return m.group(1).strip()
    # Fallback: assume the whole response is bare code (the system prompt
    # asked for that). Strip leading/trailing whitespace.
    return response.strip()


def run_problem(problem: dict[str, Any], code: str) -> dict[str, Any]:
    """Run all of problem's tests against the supplied code. Returns per-test detail."""
    if not code:
        return {
            "problem_id": problem["id"],
            "all_pass": False,
            "extracted_code_chars": 0,
            "tests": [{"call": c, "expected": e, "actual": "", "pass": False, "reason": "no code extracted"}
                      for c, e in problem["tests"]],
        }

    test_results = []
    all_pass = True
    for call_str, expected_repr in problem["tests"]:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "candidate.py"
            script.write_text(
                code + f"\n_result = {call_str}\nprint(repr(_result))\n",
                encoding="utf-8",
            )
            try:
                result = subprocess.run(
                    [sys.executable, str(script)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            except subprocess.TimeoutExpired:
                test_results.append({"call": call_str, "expected": expected_repr,
                                      "actual": "", "pass": False, "reason": "timeout"})
                all_pass = False
                continue

            if result.returncode != 0:
                test_results.append({"call": call_str, "expected": expected_repr,
                                      "actual": "", "pass": False,
                                      "reason": f"crash: {result.stderr.strip()[-200:]}"})
                all_pass = False
                continue

            actual = result.stdout.strip()
            test_pass = actual == expected_repr
            test_results.append({"call": call_str, "expected": expected_repr,
                                  "actual": actual, "pass": test_pass,
                                  "reason": "" if test_pass else "output mismatch"})
            if not test_pass:
                all_pass = False

    return {
        "problem_id": problem["id"],
        "all_pass": all_pass,
        "extracted_code_chars": len(code),
        "tests": test_results,
    }


def evaluate(candidates_path: Path, out_path: Path) -> dict[str, Any]:
    payload = json.loads(candidates_path.read_text(encoding="utf-8"))
    candidate_id = payload.get("candidate_id", "<unknown>")
    responses = payload.get("responses") or {}

    by_problem = {}
    n_pass = 0
    n_total = 0
    for problem in PROBLEMS:
        pid = problem["id"]
        response = responses.get(pid, "")
        code = extract_code(response)
        result = run_problem(problem, code)
        by_problem[pid] = result
        n_total += 1
        if result["all_pass"]:
            n_pass += 1

    pass_rate = n_pass / n_total if n_total else 0.0
    report = {
        "schema_version": "scbe_executable_coding_eval_v1",
        "candidate_id": candidate_id,
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "n_total": n_total,
        "n_pass": n_pass,
        "pass_rate": pass_rate,
        "promotion_target": 0.5,
        "promotion_passed": pass_rate >= 0.5,
        "by_problem": by_problem,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True,
                        help="path to candidate responses JSON")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="report output path")
    parser.add_argument("--json", action="store_true",
                        help="print full report JSON instead of summary")
    args = parser.parse_args()

    report = evaluate(args.candidates, args.out)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"executable_coding_holdout: candidate={report['candidate_id']}")
        print(f"  pass_rate: {report['n_pass']}/{report['n_total']} = {report['pass_rate']:.3f}")
        print(f"  promotion (>= {report['promotion_target']}): {'PASS' if report['promotion_passed'] else 'FAIL'}")
        for pid, r in report["by_problem"].items():
            verdict = "OK" if r["all_pass"] else "FAIL"
            n_tests_pass = sum(1 for t in r["tests"] if t["pass"])
            print(f"    {verdict:4} {pid}: {n_tests_pass}/{len(r['tests'])} tests pass")
        print(f"  report: {args.out}")

    return 0 if report["promotion_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
