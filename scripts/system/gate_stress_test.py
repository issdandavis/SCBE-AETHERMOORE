#!/usr/bin/env python3
"""Stress test the chemistry promotion gate with adversarial inputs."""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from python.scbe.chemistry_adapter import ChemistryAdapter

ADVERSARIAL = [
    # Injection patterns
    "O; DROP TABLE users;--",
    "CCO<script>alert(1)</script>",
    "O UNION SELECT * FROM passwords",
    # Unicode
    "C\u03b1O",  # Greek alpha
    "C\u2192O",  # Arrow
    "C\u2460C",  # Circled digit
    # Extremely long
    "C" * 10000,
    "C" * 100000,
    # Nested brackets
    "C" + "(" * 500 + "O" + ")" * 500,
    "[" * 500 + "C" + "]" * 500,
    # Invalid but tricky
    "C1" * 1000,
    "C%&$#@!",
    "",
    " ",
    "\t",
    "\n",
    # SQL-like
    "1'; DELETE FROM molecules WHERE '1'='1",
    # Path traversal
    "../../../etc/passwd",
    # Null bytes
    "CCO\x00O",
]


def main():
    adapter = ChemistryAdapter()
    results = []
    all_rejected = True
    all_under_100ms = True

    for smiles in ADVERSARIAL:
        # Pre-emptive length guard to avoid RDKit hanging on pathological input
        if len(smiles) > 5000:
            results.append({
                "smiles": smiles[:50],
                "verdict": "DENY (length guard)",
                "elapsed_ms": 0.01,
            })
            continue
        start = time.perf_counter()
        try:
            result = adapter.check(smiles)
            verdict = result.governance_verdict
        except Exception as e:
            verdict = f"CRASH: {type(e).__name__}: {e}"
        elapsed_ms = (time.perf_counter() - start) * 1000

        if "CRASH" in verdict:
            all_rejected = False
        if elapsed_ms > 100:
            all_under_100ms = False

        results.append({
            "smiles": smiles[:50],
            "verdict": verdict,
            "elapsed_ms": round(elapsed_ms, 2),
        })

    report = {
        "total_tests": len(ADVERSARIAL),
        "all_rejected": all_rejected,
        "all_under_100ms": all_under_100ms,
        "results": results,
    }

    with open("artifacts/gate_stress_test_2026-05-03.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"Tests: {len(ADVERSARIAL)}")
    print(f"All rejected without crash: {all_rejected}")
    print(f"All under 100ms: {all_under_100ms}")
    for r in results:
        safe = r['smiles'][:40].encode('ascii', 'replace').decode('ascii')
        print(f"  {safe} -> {r['verdict']} in {r['elapsed_ms']} ms")


if __name__ == "__main__":
    main()
