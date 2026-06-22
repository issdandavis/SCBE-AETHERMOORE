#!/usr/bin/env python3
"""Build a JSONL eval set from failed rows in a functional benchmark report.

The functional benchmark report tells us which task_ids a base model failed.
This script joins those ids back to executable task definitions and emits a
JSONL file consumable by functional_coding_agent_benchmark.py --eval-jsonl.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_tasks(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("tasks") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError(f"{path} must contain a task list or an object with tasks")
    tasks: dict[str, dict[str, Any]] = {}
    for row in rows:
        task_id = str(row.get("task_id") or "")
        if not task_id:
            continue
        tasks[task_id] = {
            "task_id": task_id,
            "prompt": row["prompt"],
            "checks": row["checks"],
            "benchmark_family": row.get("benchmark_family"),
        }
    return tasks


def _failed_task_ids(report: dict[str, Any], *, adapter: str | None) -> list[str]:
    results = report.get("results") or []
    if not isinstance(results, list):
        raise ValueError("report.results must be a list")
    selected = None
    if adapter:
        selected = next((row for row in results if row.get("adapter") == adapter), None)
        if selected is None:
            raise ValueError(f"adapter not found in report: {adapter}")
    else:
        selected = results[0] if results else None
    if not selected:
        raise ValueError("report has no benchmark results")
    failed: list[str] = []
    for row in selected.get("tasks") or []:
        if not row.get("passed"):
            task_id = str(row.get("task_id") or "")
            if task_id:
                failed.append(task_id)
    return failed


def build_eval(report_path: Path, task_files: list[Path], out_path: Path, *, adapter: str | None) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    failed_ids = _failed_task_ids(report, adapter=adapter)
    task_index: dict[str, dict[str, Any]] = {}
    for path in task_files:
        task_index.update(_load_tasks(path))

    missing = [task_id for task_id in failed_ids if task_id not in task_index]
    if missing:
        raise ValueError(f"failed task ids missing from task files: {missing}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as handle:
        for rank, task_id in enumerate(failed_ids, start=1):
            task = dict(task_index[task_id])
            task["source_report"] = str(report_path)
            task["source_adapter"] = adapter or (report.get("results") or [{}])[0].get("adapter")
            task["base_failure_rank"] = rank
            handle.write(json.dumps(task, ensure_ascii=False, sort_keys=True) + "\n")

    return {
        "out": str(out_path),
        "source_report": str(report_path),
        "adapter": adapter or (report.get("results") or [{}])[0].get("adapter"),
        "failed_tasks": len(failed_ids),
        "task_ids": failed_ids,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True, help="functional benchmark report.json")
    parser.add_argument("--task-file", type=Path, action="append", required=True, help="task JSON file; may repeat")
    parser.add_argument("--out", type=Path, required=True, help="output eval JSONL")
    parser.add_argument("--adapter", default=None, help="optional adapter name in report.results")
    args = parser.parse_args()

    result = build_eval(args.report, args.task_file, args.out, adapter=args.adapter)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
