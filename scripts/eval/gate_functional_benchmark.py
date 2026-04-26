#!/usr/bin/env python3
"""Promotion gate for functional coding-agent benchmark reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "report",
        type=Path,
        nargs="?",
        default=Path("artifacts/coding_agent_benchmarks/latest/report.json"),
        help="Benchmark report JSON path.",
    )
    parser.add_argument("--adapter", default=None, help="Adapter/model name to gate. Defaults to all non-BASE results.")
    parser.add_argument("--min-pass-rate", type=float, default=0.85, help="Required pass rate, 0.0-1.0.")
    parser.add_argument("--min-passed", type=int, default=0, help="Optional required number of passed tasks.")
    parser.add_argument(
        "--beat-base",
        action="store_true",
        help="Require gated adapter pass rate to be greater than the BASE pass rate in the same report.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.loads(args.report.read_text(encoding="utf-8"))
    results = payload.get("results") or []
    base = next((row for row in results if row.get("adapter") == "BASE"), None)
    base_rate = (base or {}).get("summary", {}).get("pass_rate")

    if args.adapter:
        gated = [row for row in results if row.get("adapter") == args.adapter]
    else:
        gated = [row for row in results if row.get("adapter") != "BASE"]

    if not gated:
        print(f"FAIL: no benchmark results matched adapter={args.adapter!r}", file=sys.stderr)
        return 2

    failed = []
    for row in gated:
        summary = row.get("summary", {})
        pass_rate = float(summary.get("pass_rate", 0.0))
        passed = int(summary.get("passed", 0))
        reasons = []
        if pass_rate < args.min_pass_rate:
            reasons.append(f"pass_rate {pass_rate:.2%} < {args.min_pass_rate:.2%}")
        if args.min_passed and passed < args.min_passed:
            reasons.append(f"passed {passed} < {args.min_passed}")
        if args.beat_base and base_rate is not None and pass_rate <= float(base_rate):
            reasons.append(f"pass_rate {pass_rate:.2%} <= BASE {float(base_rate):.2%}")
        if reasons:
            failed.append((row.get("adapter"), reasons))
        else:
            print(f"PASS: {row.get('adapter')} passed gate at {pass_rate:.2%} ({passed} tasks)")

    if failed:
        for adapter, reasons in failed:
            print(f"FAIL: {adapter}: {'; '.join(reasons)}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
