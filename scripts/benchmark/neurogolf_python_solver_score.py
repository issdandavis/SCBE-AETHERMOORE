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

from neurogolf.arc_io import load_arc_task
from neurogolf.solver import execute_program, synthesize_program


def _task_number(path: Path) -> int:
    digits = "".join(ch for ch in path.stem if ch.isdigit())
    return int(digits) if digits else 0


def score_python_solver(tasks_dir: Path, out_path: Path) -> dict[str, Any]:
    task_paths = sorted(tasks_dir.glob("task*.json"), key=_task_number)
    solved = 0
    scored = 0
    test_examples = 0
    test_examples_passed = 0
    family_counts: Counter[str] = Counter()
    solved_by_family: Counter[str] = Counter()
    error_counts: Counter[str] = Counter()
    task_reports: list[dict[str, Any]] = []

    for task_path in task_paths:
        task_id = task_path.stem
        task_report: dict[str, Any] = {"task_id": task_id}
        try:
            raw = json.loads(task_path.read_text(encoding="utf-8"))
            task = load_arc_task(task_path)
            solution = synthesize_program(task)
            family_counts[solution.family] += 1
            task_report["family"] = solution.family
            example_reports = []
            passed = 0
            for index, example in enumerate(raw.get("test", [])):
                prediction = execute_program(task.test_inputs[index], solution.program).tolist()
                ok = prediction == example["output"]
                passed += int(ok)
                test_examples_passed += int(ok)
                test_examples += 1
                example_reports.append(
                    {
                        "index": index,
                        "ok": ok,
                        "expected_shape": [
                            len(example["output"]),
                            len(example["output"][0]) if example["output"] else 0,
                        ],
                        "actual_shape": [
                            len(prediction),
                            len(prediction[0]) if prediction else 0,
                        ],
                    }
                )
            task_report["test_examples"] = len(raw.get("test", []))
            task_report["test_examples_passed"] = passed
            task_report["task_solved"] = bool(raw.get("test")) and passed == len(raw.get("test", []))
            task_report["examples"] = example_reports
            scored += 1
            if task_report["task_solved"]:
                solved += 1
                solved_by_family[solution.family] += 1
        except Exception as exc:
            error_counts[type(exc).__name__] += 1
            task_report["error"] = f"{type(exc).__name__}: {exc}"
        task_reports.append(task_report)

    report = {
        "schema": "scbe_neurogolf_python_solver_score_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "tasks_dir": str(tasks_dir),
        "scored_tasks": scored,
        "solved_tasks": solved,
        "task_solve_rate": solved / len(task_paths) if task_paths else 0.0,
        "test_examples": test_examples,
        "test_examples_passed": test_examples_passed,
        "test_example_pass_rate": test_examples_passed / test_examples if test_examples else 0.0,
        "family_counts": dict(sorted(family_counts.items())),
        "solved_by_family": dict(sorted(solved_by_family.items())),
        "error_counts": dict(error_counts),
        "claim_boundary": {
            "synthesis_reads_test_outputs": False,
            "development_scoring_reads_test_outputs": True,
            "purpose": "measure blind-from-train Python solver upper bound before ONNX lowering",
        },
        "tasks": task_reports,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Score NeuroGolf Python solver using train-only synthesis.")
    parser.add_argument("--tasks-dir", type=Path, default=Path("artifacts/kaggle/neurogolf-2026/data"))
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/benchmarks/neurogolf_blind_submission/python_solver_score.json"),
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = score_python_solver(args.tasks_dir, args.out)
    summary = {k: v for k, v in report.items() if k != "tasks"}
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(
            "neurogolf python solver: "
            f"solved={report['solved_tasks']}/400 "
            f"rate={report['task_solve_rate']:.4f} "
            f"examples={report['test_examples_passed']}/{report['test_examples']}"
        )
        print(f"report={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
