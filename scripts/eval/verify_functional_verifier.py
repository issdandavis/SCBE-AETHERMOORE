#!/usr/bin/env python3
"""Proof: the functional coding verifier distinguishes working code from a stub
BY EXECUTION, with no model in the loop.

This is the honest-stub-recognition claim, decoupled from model flakiness. It
feeds known-good and known-stub TypeScript `evaluate` sources straight into the
same `score_candidate` -> `run_harness` -> node game-debug harness that the
model benchmark uses, and asserts good PASSES and stub FAILS.

Run: python scripts/eval/verify_functional_verifier.py [--json]
Exit 0 only if every good source passes and every stub source fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "eval"))

import functional_coding_agent_benchmark as fb  # noqa: E402

# task_id -> (working source, stub source). Working must satisfy the task's
# checks; stub is a plausible non-working answer a weak model would emit.
CASES = {
    "score_add": (
        "function evaluate(input, state){ state.score += input.points; return state.score; }",
        "function evaluate(input, state){ return 0; }",
    ),
    "inventory_unique": (
        "function evaluate(input, state){ if(!state.inventory.includes(input.item)) "
        "state.inventory.push(input.item); return state.inventory.length; }",
        "function evaluate(input, state){ state.inventory.push(input.item); "
        "return state.inventory.length; }",  # forgets the uniqueness guard
    ),
    "cooldown_gate": (
        "function evaluate(input, state){ if(state.cooldown > 0){ state.cooldown -= 1; return false; } "
        "state.cooldown = input.cooldown; state.actions += 1; return true; }",
        "function evaluate(input, state){ return true; }",  # ignores cooldown
    ),
}


def run() -> dict:
    tasks = {t.task_id: t for t in fb.TASKS}
    rows = []
    ok = True
    for task_id, (good, stub) in CASES.items():
        task = tasks[task_id]
        good_passed = fb.score_candidate(good, task)["passed"]
        stub_score = fb.score_candidate(stub, task)
        stub_passed = stub_score["passed"]
        # honest verifier: good passes, stub fails
        case_ok = bool(good_passed) and not bool(stub_passed)
        ok = ok and case_ok
        rows.append(
            {
                "task_id": task_id,
                "good_passed": bool(good_passed),
                "stub_passed": bool(stub_passed),
                "discriminates": case_ok,
                "stub_first_failure": next((c for c in stub_score["checks"] if not c["passed"]), None),
            }
        )
    return {
        "schema_version": "scbe_verifier_proof_v1",
        "claim": "execution-based functional verifier distinguishes working code from stub, no model in loop",
        "harness": "scripts/run_typescript_debug_scenario.cjs",
        "ok": ok,
        "cases": rows,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    result = run()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for row in result["cases"]:
            verdict = "OK" if row["discriminates"] else "BROKEN"
            print(
                f"[{verdict}] {row['task_id']}: good_passed={row['good_passed']} " f"stub_passed={row['stub_passed']}"
            )
        print(f"\nverifier discriminates working-vs-stub by execution: {result['ok']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
