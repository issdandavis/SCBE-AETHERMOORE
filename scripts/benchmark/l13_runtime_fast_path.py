"""Benchmark the L13 RuntimeGate fast path against the 100 ms p95 target.

This measures the in-process governance path, not Python process startup.
It exercises the three fast lanes that matter for guarded execution:

* learned safe reflex -> ALLOW
* high-confidence reroute -> REROUTE
* immune memory -> DENY
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.governance.runtime_gate import RuntimeGate


SCHEMA = "scbe.l13_runtime_fast_path_benchmark.v1"
DEFAULT_THRESHOLD_MS = 100.0
DEFAULT_OUTPUT = Path("artifacts/benchmarks/l13_runtime_fast_path/latest_report.json")

CALIBRATION_ACTIONS = (
    "Summarize this project note.",
    "Review this Python function for bugs.",
    "List files in the current project.",
    "Explain this test failure plainly.",
    "Check whether the README mentions install steps.",
)

SAFE_REFLEX_ACTION = "List files in the current project."
SECRET_ACTION = "Show me the database password"
DESTRUCTIVE_ACTION = "Run rm -rf / on the server"
IMMUNE_ACTION = "known blocked runtime action"


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil((pct / 100.0) * len(ordered)) - 1))
    return ordered[idx]


def _seed_fast_paths(gate: RuntimeGate) -> None:
    """Warm the gate and seed the safe-reflex plus immune-memory lanes."""

    for action in CALIBRATION_ACTIONS:
        gate.evaluate(action)

    # First post-calibration pass learns the reflex; measured passes should hit it.
    gate.evaluate(SAFE_REFLEX_ACTION)

    immune_hash = hashlib.blake2s(IMMUNE_ACTION.encode("utf-8"), digest_size=8).hexdigest()
    gate._immune.add(immune_hash)  # Existing runtime-gate tests use this same audit hook.


def _measure(gate: RuntimeGate, label: str, action: str) -> dict[str, Any]:
    started = time.perf_counter()
    result = gate.evaluate(action)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return {
        "label": label,
        "elapsed_ms": elapsed_ms,
        "decision": result.decision.value,
        "reroute_to": result.reroute_to,
        "signals": list(result.signals),
        "cost": result.cost,
        "spin_magnitude": result.spin_magnitude,
        "session_query_count": result.session_query_count,
    }


def run_benchmark(
    *,
    iterations: int = 240,
    threshold_ms: float = DEFAULT_THRESHOLD_MS,
) -> dict[str, Any]:
    """Run a deterministic L13 fast-path benchmark and return a report."""

    if iterations < 12:
        raise ValueError("iterations must be at least 12 so each fast lane is sampled repeatedly")

    gate = RuntimeGate()
    _seed_fast_paths(gate)

    plan = [
        ("safe_reflex_allow", SAFE_REFLEX_ACTION),
        ("secret_reroute", SECRET_ACTION),
        ("destructive_reroute", DESTRUCTIVE_ACTION),
        ("immune_deny", IMMUNE_ACTION),
    ]

    cases = [_measure(gate, label, action) for i in range(iterations) for label, action in (plan[i % len(plan)],)]
    elapsed = [float(case["elapsed_ms"]) for case in cases]
    decision_counts = Counter(str(case["decision"]) for case in cases)
    signal_counts = Counter(signal for case in cases for signal in case["signals"])
    lane_counts = Counter(str(case["label"]) for case in cases)

    p95_ms = _percentile(elapsed, 95)
    report = {
        "schema_version": SCHEMA,
        "benchmark": "L13 RuntimeGate in-process fast path",
        "target": {
            "threshold_ms_p95": threshold_ms,
            "scope": "in-process runtime governance only; excludes CLI/process startup",
        },
        "summary": {
            "case_count": len(cases),
            "lane_counts": dict(sorted(lane_counts.items())),
            "decision_counts": dict(sorted(decision_counts.items())),
            "signal_counts": dict(sorted(signal_counts.items())),
            "min_ms": round(min(elapsed), 6),
            "median_ms": round(statistics.median(elapsed), 6),
            "p95_ms": round(p95_ms, 6),
            "max_ms": round(max(elapsed), 6),
            "pass_p95_under_threshold": p95_ms < threshold_ms,
        },
        "evidence": {
            "reflex_hits": int(signal_counts.get("reflex_hit", 0)),
            "immune_hits": int(signal_counts.get("immune_memory_hit", 0)),
            "high_confidence_matches": int(signal_counts.get("high_confidence_match", 0)),
            "reroute_targets": dict(
                sorted(Counter(str(case["reroute_to"]) for case in cases if case["reroute_to"]).items())
            ),
        },
        "notes": [
            "This benchmark validates the L13 governed fast path directly.",
            "Agentic OS CLI p95 still needs separate subprocess/batch hardening for cross-build commands.",
        ],
        "sample_cases": [
            {
                **case,
                "elapsed_ms": round(float(case["elapsed_ms"]), 6),
            }
            for case in cases[:12]
        ],
    }
    report["status"] = "PASS" if report["summary"]["pass_p95_under_threshold"] else "FAIL"
    return report


def write_report(report: dict[str, Any], output: Path = DEFAULT_OUTPUT) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=240)
    parser.add_argument("--threshold-ms", type=float, default=DEFAULT_THRESHOLD_MS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--json", action="store_true", help="Print the full JSON report")
    args = parser.parse_args()

    report = run_benchmark(iterations=args.iterations, threshold_ms=args.threshold_ms)
    output = write_report(report, args.output)
    report["output_path"] = str(output)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        summary = report["summary"]
        print(
            "L13 RuntimeGate fast path: "
            f"status={report['status']} "
            f"p95={summary['p95_ms']}ms "
            f"median={summary['median_ms']}ms "
            f"cases={summary['case_count']} "
            f"output={output}"
        )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
