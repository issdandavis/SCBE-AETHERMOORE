from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
src_path = REPO_ROOT / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import numpy as np
import onnxruntime


def _model_output_to_grid(output: np.ndarray) -> list[list[int]]:
    active = output > 0.0
    _, channels, height, width = active.shape
    grid: list[list[int]] = []
    for row in range(height):
        cells: list[int] = []
        for col in range(width):
            colors = [color for color in range(channels) if bool(active[0, color, row, col])]
            if len(colors) == 1:
                cells.append(colors[0])
            elif colors:
                cells.append(11)
            else:
                cells.append(10)
        while cells and cells[-1] == 10:
            cells.pop()
        grid.append(cells)
    while grid and not grid[-1]:
        grid.pop()
    return grid


def _grid_to_competition_input(grid: np.ndarray) -> np.ndarray:
    out = np.zeros((1, 10, 30, 30), dtype=np.float32)
    rows, cols = grid.shape
    for row in range(rows):
        for col in range(cols):
            out[0, int(grid[row, col]), row, col] = 1.0
    return out


def _load_report(report_path: Path) -> dict[str, Any]:
    return json.loads(report_path.read_text(encoding="utf-8"))


def _score_one(onnx_path: Path, task_json: dict[str, Any]) -> dict[str, Any]:
    session = onnxruntime.InferenceSession(str(onnx_path))
    test_rows = task_json.get("test", [])
    example_reports = []
    passed = 0
    for index, example in enumerate(test_rows):
        input_grid = np.asarray(example["input"], dtype=np.int64)
        expected = example.get("output")
        input_array = _grid_to_competition_input(input_grid)
        actual_array = session.run(["output"], {"input": input_array})[0]
        actual = _model_output_to_grid(actual_array)
        ok = actual == expected
        passed += int(ok)
        example_reports.append(
            {
                "index": index,
                "ok": ok,
                "expected_shape": [len(expected), len(expected[0]) if expected else 0],
                "actual_shape": [len(actual), len(actual[0]) if actual else 0],
            }
        )
    return {
        "test_examples": len(test_rows),
        "test_examples_passed": passed,
        "task_solved": bool(test_rows) and passed == len(test_rows),
        "examples": example_reports,
    }


def score_submission(report_path: Path, tasks_dir: Path, out_path: Path) -> dict[str, Any]:
    submission_report = _load_report(report_path)
    task_rows = submission_report.get("tasks", [])
    task_reports = []
    family_counts: Counter[str] = Counter()
    solved_by_family: Counter[str] = Counter()
    error_counts: Counter[str] = Counter()
    solved = 0
    scored = 0
    test_examples = 0
    test_examples_passed = 0

    for row in task_rows:
        task_id = row["task_id"]
        family = row.get("family", "unknown")
        family_counts[family] += 1
        task_path = tasks_dir / f"{task_id}.json"
        onnx_path = Path(row["onnx_path"])
        task_report: dict[str, Any] = {
            "task_id": task_id,
            "family": family,
            "onnx_path": str(onnx_path),
        }
        try:
            task_json = json.loads(task_path.read_text(encoding="utf-8"))
            score = _score_one(onnx_path, task_json)
            task_report.update(score)
            scored += 1
            test_examples += score["test_examples"]
            test_examples_passed += score["test_examples_passed"]
            if score["task_solved"]:
                solved += 1
                solved_by_family[family] += 1
        except Exception as exc:
            error_counts[type(exc).__name__] += 1
            task_report["error"] = f"{type(exc).__name__}: {exc}"
        task_reports.append(task_report)

    report = {
        "schema": "scbe_neurogolf_submission_score_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "submission_report": str(report_path),
        "tasks_dir": str(tasks_dir),
        "scored_tasks": scored,
        "solved_tasks": solved,
        "task_solve_rate": solved / scored if scored else 0.0,
        "test_examples": test_examples,
        "test_examples_passed": test_examples_passed,
        "test_example_pass_rate": test_examples_passed / test_examples if test_examples else 0.0,
        "family_counts": dict(sorted(family_counts.items())),
        "solved_by_family": dict(sorted(solved_by_family.items())),
        "error_counts": dict(error_counts),
        "claim_boundary": {
            "development_scoring_reads_test_outputs": True,
            "not_a_blind_submission_builder": True,
            "purpose": "measure exact local target gap after building a blind ONNX submission bundle",
        },
        "tasks": task_reports,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Development-only scorer for a NeuroGolf ONNX submission report.")
    parser.add_argument("--report", type=Path, default=Path("artifacts/benchmarks/neurogolf_blind_submission/latest_report.json"))
    parser.add_argument("--tasks-dir", type=Path, default=Path("artifacts/kaggle/neurogolf-2026/data"))
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/benchmarks/neurogolf_blind_submission/latest_score_report.json"),
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = score_submission(args.report, args.tasks_dir, args.out)
    summary = {k: v for k, v in report.items() if k != "tasks"}
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(
            "neurogolf local score: "
            f"solved={report['solved_tasks']}/{report['scored_tasks']} "
            f"rate={report['task_solve_rate']:.4f} "
            f"examples={report['test_examples_passed']}/{report['test_examples']}"
        )
        print(f"report={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
