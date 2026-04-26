#!/usr/bin/env python3
"""Compare functional coding-agent benchmark reports.

This turns separate benchmark runs into one promotion-readable table. It is
intentionally report-only: no model loading, no generation, no hidden side
effects. Use it after BASE/v1/v2/specialty adapters have been scored.
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_ROOT = Path("artifacts/coding_agent_benchmarks/comparisons")


@dataclass(frozen=True)
class ReportRef:
    label: str
    path: Path
    payload: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path, help="report.json path or benchmark output directory.")
    parser.add_argument("--label", action="append", default=[], help="Optional label for each report, in order.")
    parser.add_argument("--baseline", default="BASE", help="Adapter/model name to use as same-report baseline.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def resolve_report_path(path: Path) -> Path:
    if path.is_dir():
        return path / "report.json"
    return path


def load_reports(paths: list[Path], labels: list[str]) -> list[ReportRef]:
    reports: list[ReportRef] = []
    for index, raw_path in enumerate(paths):
        path = resolve_report_path(raw_path)
        if not path.exists():
            raise FileNotFoundError(f"benchmark report not found: {path}")
        label = labels[index] if index < len(labels) else raw_path.parent.name if path.name == "report.json" else path.stem
        reports.append(ReportRef(label=label, path=path, payload=json.loads(path.read_text(encoding="utf-8"))))
    return reports


def summarize_result(result: dict[str, Any]) -> dict[str, Any]:
    summary = result.get("summary") or {}
    tasks = result.get("tasks") or []
    failed = [task.get("task_id") for task in tasks if not task.get("passed")]
    passed = [task.get("task_id") for task in tasks if task.get("passed")]
    return {
        "adapter": result.get("adapter"),
        "base_model": result.get("base_model"),
        "tasks": int(summary.get("tasks") or len(tasks)),
        "passed": int(summary.get("passed") or len(passed)),
        "pass_rate": float(summary.get("pass_rate") or 0.0),
        "passed_tasks": passed,
        "failed_tasks": failed,
    }


def first_failure(task: dict[str, Any]) -> str:
    checks = task.get("checks") or []
    bad = next((check for check in checks if not check.get("passed")), None)
    if not bad:
        return str(task.get("error") or "")
    return (
        f"check {bad.get('index')}: status={bad.get('receipt_status')} "
        f"expected_result={bad.get('expected_result')!r} actual_result={bad.get('actual_result')!r}"
    )


def task_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for task in result.get("tasks") or []:
        rows.append(
            {
                "adapter": result.get("adapter"),
                "task_id": task.get("task_id"),
                "passed": bool(task.get("passed")),
                "first_failure": "" if task.get("passed") else first_failure(task),
            }
        )
    return rows


def build_comparison(reports: list[ReportRef], baseline_name: str) -> dict[str, Any]:
    report_rows = []
    detail_rows = []
    global_baseline_rate = None
    for report in reports:
        for result in report.payload.get("results") or []:
            if result.get("adapter") == baseline_name:
                global_baseline_rate = summarize_result(result)["pass_rate"]
                break
        if global_baseline_rate is not None:
            break

    for report in reports:
        results = report.payload.get("results") or []
        summaries = [summarize_result(result) for result in results]
        baseline = next((row for row in summaries if row["adapter"] == baseline_name), None)
        baseline_rate = baseline["pass_rate"] if baseline else global_baseline_rate
        for result, summary in zip(results, summaries):
            delta = None if baseline_rate is None else summary["pass_rate"] - baseline_rate
            report_rows.append(
                {
                    "report": report.label,
                    "report_path": str(report.path),
                    **summary,
                    "delta_vs_baseline": delta,
                }
            )
            for row in task_rows(result):
                detail_rows.append({"report": report.label, **row})
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline": baseline_name,
        "reports": report_rows,
        "tasks": detail_rows,
    }


def write_outputs(payload: dict[str, Any], output_root: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = output_root / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    report_json = out_dir / "comparison.json"
    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Functional Benchmark Comparison",
        "",
        f"Baseline: `{payload['baseline']}`",
        "",
        "| Report | Adapter | Tasks | Passed | Pass Rate | Delta vs Baseline | Failed Tasks |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in payload["reports"]:
        delta = row.get("delta_vs_baseline")
        delta_text = "" if delta is None else f"{delta:+.2%}"
        failed = ", ".join(row.get("failed_tasks") or [])
        lines.append(
            f"| `{row['report']}` | `{row['adapter']}` | {row['tasks']} | {row['passed']} | "
            f"{row['pass_rate']:.2%} | {delta_text} | {failed} |"
        )

    lines.extend(["", "## Task Failures", "", "| Report | Adapter | Task | Failure |", "| --- | --- | --- | --- |"])
    for row in payload["tasks"]:
        if row["passed"]:
            continue
        failure = str(row["first_failure"]).replace("|", "\\|")
        lines.append(f"| `{row['report']}` | `{row['adapter']}` | `{row['task_id']}` | {failure} |")

    report_md = out_dir / "comparison.md"
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    latest = output_root / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(report_json, latest / "comparison.json")
    shutil.copyfile(report_md, latest / "comparison.md")
    return out_dir


def main() -> int:
    args = parse_args()
    reports = load_reports(args.reports, args.label)
    payload = build_comparison(reports, args.baseline)
    out_dir = write_outputs(payload, args.output_root)
    print(f"Comparison JSON: {out_dir / 'comparison.json'}")
    print(f"Comparison MD:   {out_dir / 'comparison.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
