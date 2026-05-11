#!/usr/bin/env python3
"""Compare functional coding-agent benchmark reports.

This is intentionally small: it lets the package script emit a stable delta
between two `functional_coding_agent_benchmark.py` reports without loading any
models or mutating repo state.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_REPORT = Path("artifacts/coding_agent_benchmarks/latest/report.json")


def load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def result_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = {str(row.get("adapter")): row for row in report.get("results") or []}
    ensemble = report.get("mechanical_ensemble")
    if isinstance(ensemble, dict) and ensemble.get("adapter"):
        rows[str(ensemble["adapter"])] = ensemble
    return rows


def summarize(report: dict[str, Any]) -> dict[str, dict[str, float]]:
    rows: dict[str, dict[str, float]] = {}
    for adapter, row in result_map(report).items():
        summary = row.get("summary") or {}
        rows[adapter] = {
            "tasks": float(summary.get("tasks") or 0),
            "passed": float(summary.get("passed") or 0),
            "pass_rate": float(summary.get("pass_rate") or 0.0),
        }
    return rows


def compare_reports(candidate: dict[str, Any], baseline: dict[str, Any] | None = None) -> dict[str, Any]:
    candidate_rows = summarize(candidate)
    baseline_rows = summarize(baseline or {"results": []})
    adapters = sorted(set(candidate_rows) | set(baseline_rows))
    deltas = []
    for adapter in adapters:
        current = candidate_rows.get(adapter, {"tasks": 0.0, "passed": 0.0, "pass_rate": 0.0})
        previous = baseline_rows.get(adapter, {"tasks": 0.0, "passed": 0.0, "pass_rate": 0.0})
        deltas.append(
            {
                "adapter": adapter,
                "candidate_pass_rate": round(current["pass_rate"], 6),
                "baseline_pass_rate": round(previous["pass_rate"], 6),
                "delta_pass_rate": round(current["pass_rate"] - previous["pass_rate"], 6),
                "candidate_passed": int(current["passed"]),
                "baseline_passed": int(previous["passed"]),
                "candidate_tasks": int(current["tasks"]),
                "baseline_tasks": int(previous["tasks"]),
            }
        )
    return {
        "schema": "scbe_functional_coding_agent_report_compare_v1",
        "claim_boundary": "Compares executable benchmark report summaries only; does not run models.",
        "deltas": deltas,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Functional Coding Agent Benchmark Comparison",
        "",
        f"- schema: `{payload['schema']}`",
        f"- claim_boundary: {payload['claim_boundary']}",
        "",
        "| Adapter | Candidate Pass Rate | Baseline Pass Rate | Delta | Candidate Passed | Baseline Passed |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in payload["deltas"]:
        lines.append(
            "| `{adapter}` | {candidate:.2%} | {baseline:.2%} | {delta:+.2%} | {candidate_passed} | {baseline_passed} |".format(
                adapter=row["adapter"],
                candidate=row["candidate_pass_rate"],
                baseline=row["baseline_pass_rate"],
                delta=row["delta_pass_rate"],
                candidate_passed=row["candidate_passed"],
                baseline_passed=row["baseline_passed"],
            )
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", nargs="?", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--baseline", type=Path, default=None)
    parser.add_argument("--json", action="store_true", help="Print JSON instead of markdown.")
    parser.add_argument("--output", type=Path, default=None, help="Optional output file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidate = load_report(args.candidate)
    baseline = load_report(args.baseline) if args.baseline else None
    payload = compare_reports(candidate, baseline)
    text = json.dumps(payload, indent=2) + "\n" if args.json else render_markdown(payload)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
