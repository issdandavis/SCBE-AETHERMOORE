#!/usr/bin/env python3
"""Run SCBE's local SWE-style coding benchmark lane.

This is not an official SWE-bench Verified score. It is an offline, executable
issue-repair style lane that uses repo-local tasks modeled after SWE-bench,
Terminal-Bench, Aider Polyglot, EvalPlus, RepoBench, and cost reporting.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TASK_FILE = REPO_ROOT / "config" / "eval" / "common_agentic_benchmark_tasks.v1.json"
DEFAULT_CANDIDATE_FILE = REPO_ROOT / "artifacts" / "benchmarks" / "scbe_harness_controls" / "stub_candidate.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "swe_local_benchmark"


def _ensure_default_stub_candidate(path: Path) -> None:
    """Create the default negative-control candidate when absent.

    The default candidate lives under the gitignored artifacts/ tree, so fresh
    checkouts do not ship it. The stub intentionally provides no task
    solutions; it is a harness control that exercises command shape and
    scoring plumbing deterministically.
    """
    if path.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "scbe_swe_local_stub_candidate_v1",
        "candidates": [
            {
                "name": "stub_candidate",
                "description": "Harness control candidate with no task solutions.",
                "tasks": {},
            }
        ],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def _load_report(output_root: Path) -> dict[str, Any]:
    report_path = output_root / "latest" / "report.json"
    if not report_path.is_file():
        raise FileNotFoundError(f"expected report not found: {report_path}")
    return json.loads(report_path.read_text(encoding="utf-8"))


def _compact_report(report: dict[str, Any], output_root: Path, returncode: int) -> dict[str, Any]:
    results = report.get("results") or []
    ensemble = report.get("mechanical_ensemble") or {}
    suite_rows = []
    for result in results:
        summary = result.get("summary") or {}
        suite_rows.append(
            {
                "adapter": result.get("adapter"),
                "tasks": summary.get("tasks", 0),
                "passed": summary.get("passed", 0),
                "pass_rate": summary.get("pass_rate", 0),
            }
        )
    ensemble_summary = ensemble.get("summary") or {}
    return {
        "schema_version": "scbe_swe_local_benchmark_summary_v1",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ok": returncode == 0,
        "claim_boundary": "local_swe_style_not_official_swe_bench_verified",
        "task_file": str(DEFAULT_TASK_FILE.relative_to(REPO_ROOT)),
        "candidate_file": str(DEFAULT_CANDIDATE_FILE.relative_to(REPO_ROOT)),
        "report_json": str((output_root / "latest" / "report.json").relative_to(REPO_ROOT)),
        "report_md": str((output_root / "latest" / "report.md").relative_to(REPO_ROOT)),
        "results": suite_rows,
        "mechanical_ensemble": {
            "tasks": ensemble_summary.get("tasks", 0),
            "passed": ensemble_summary.get("passed", 0),
            "pass_rate": ensemble_summary.get("pass_rate", 0),
            "unresolved_tasks": ensemble_summary.get("unresolved_tasks", []),
            "contributing_models": ensemble_summary.get("contributing_models", {}),
        },
    }


def _write_summary(summary: dict[str, Any], output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "latest_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    md = [
        "# SCBE Local SWE-Style Benchmark",
        "",
        f"- ok: `{summary['ok']}`",
        f"- claim_boundary: `{summary['claim_boundary']}`",
        f"- report_json: `{summary['report_json']}`",
        "",
        "| Lane | Tasks | Passed | Pass Rate |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in summary["results"]:
        md.append(
            f"| `{row['adapter']}` | {row['tasks']} | {row['passed']} | {float(row['pass_rate']):.2%} |"
        )
    ens = summary["mechanical_ensemble"]
    md.append(
        f"| `mechanical_ensemble` | {ens['tasks']} | {ens['passed']} | {float(ens['pass_rate']):.2%} |"
    )
    md.extend(
        [
            "",
            "This is an offline repo-native SWE-style lane. It does not claim official SWE-bench Verified parity.",
            "",
        ]
    )
    (output_root / "latest_summary.md").write_text("\n".join(md), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-file", type=Path, default=DEFAULT_TASK_FILE)
    parser.add_argument("--candidate-file", type=Path, default=DEFAULT_CANDIDATE_FILE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--task-limit", type=int, default=0)
    parser.add_argument("--min-pass-rate", type=float, default=1.0)
    parser.add_argument("--timeout-sec", type=int, default=240)
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and print command without running.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.task_file.is_file():
        raise SystemExit(f"missing task file: {args.task_file}")
    if args.candidate_file == DEFAULT_CANDIDATE_FILE:
        _ensure_default_stub_candidate(args.candidate_file)
    if not args.candidate_file.is_file():
        raise SystemExit(f"missing candidate file: {args.candidate_file}")

    cmd = [
        sys.executable,
        "scripts/eval/functional_coding_agent_benchmark.py",
        "--candidate-file",
        str(args.candidate_file),
        "--task-file",
        str(args.task_file),
        "--replace-default-tasks",
        "--output-root",
        str(args.output_root),
        "--min-pass-rate",
        str(args.min_pass_rate),
    ]
    if args.task_limit > 0:
        cmd.extend(["--task-limit", str(args.task_limit)])

    if args.dry_run:
        print(json.dumps({"ok": True, "command": cmd}, indent=2))
        return 0

    proc = _run(cmd, timeout=args.timeout_sec)
    if proc.stdout:
        print(proc.stdout, file=sys.stderr, end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")
    report = _load_report(args.output_root)
    summary = _compact_report(report, args.output_root, proc.returncode)
    _write_summary(summary, args.output_root)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
