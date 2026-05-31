from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
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
from neurogolf.ir import make_identity_program
from neurogolf.onnx_emit import export_program_onnx
from neurogolf.package import build_submission_zip
from neurogolf.solver import synthesize_program
from neurogolf.validate import validate_submission_model


def _utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _task_number(path: Path) -> int:
    digits = "".join(ch for ch in path.stem if ch.isdigit())
    return int(digits) if digits else 0


def _load_official_check(tasks_dir: Path):
    official_path = tasks_dir / "neurogolf_utils" / "neurogolf_utils.py"
    if not official_path.exists():
        return None, f"missing {official_path}"
    import importlib.util

    spec = importlib.util.spec_from_file_location("neurogolf_official_utils", official_path)
    if spec is None or spec.loader is None:
        return None, f"could not load import spec for {official_path}"
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    return getattr(module, "check_network", None), None


def _runtime_smoke(onnx_path: Path, task_path: Path) -> dict[str, Any]:
    import numpy as np
    import onnxruntime

    task = load_arc_task(task_path)
    if not task.test_inputs:
        return {"ok": False, "reason": "no test inputs"}

    session = onnxruntime.InferenceSession(str(onnx_path))
    input_array = np.zeros((1, 10, 30, 30), dtype=np.float32)
    for row, col in np.ndindex(task.test_inputs[0].shape):
        input_array[0, int(task.test_inputs[0][row, col]), row, col] = 1.0
    output = session.run(["output"], {"input": input_array})[0]
    return {
        "ok": True,
        "input_name": session.get_inputs()[0].name,
        "output_name": session.get_outputs()[0].name,
        "output_shape": list(output.shape),
    }


def build_blind_submission(
    *,
    tasks_dir: Path,
    out_dir: Path,
    limit: int | None,
    validate: bool,
    official_check: bool,
    smoke_limit: int,
) -> dict[str, Any]:
    task_paths = sorted(tasks_dir.glob("task*.json"), key=_task_number)
    if limit is not None:
        task_paths = task_paths[:limit]
    if not task_paths:
        raise FileNotFoundError(f"No task*.json files found under {tasks_dir}")

    onnx_dir = out_dir / "onnx"
    if onnx_dir.exists():
        shutil.rmtree(onnx_dir)
    onnx_dir.mkdir(parents=True, exist_ok=True)

    official = None
    official_load_error = None
    if official_check:
        official, official_load_error = _load_official_check(tasks_dir)

    task_to_onnx: dict[str, Path] = {}
    task_reports: list[dict[str, Any]] = []
    family_counts: Counter[str] = Counter()
    export_errors: Counter[str] = Counter()
    validation_errors: Counter[str] = Counter()
    official_errors: Counter[str] = Counter()
    fallback_count = 0
    synthesized_count = 0
    smoke_reports: list[dict[str, Any]] = []

    start = time.perf_counter()
    for index, task_path in enumerate(task_paths, start=1):
        task_id = task_path.stem
        out_path = onnx_dir / f"{task_id}.onnx"
        task_report: dict[str, Any] = {
            "task_id": task_id,
            "source_path": str(task_path),
            "used_test_outputs": False,
            "status": "unknown",
        }

        try:
            task = load_arc_task(task_path)
            solution = synthesize_program(task)
            program = solution.program
            family = solution.family
            synthesized_count += 1
        except Exception as exc:
            program = make_identity_program()
            family = "identity_fallback"
            fallback_count += 1
            task_report["synthesis_error"] = f"{type(exc).__name__}: {exc}"

        try:
            export_program_onnx(program, out_path)
            task_report["status"] = "exported"
        except Exception as exc:
            export_errors[type(exc).__name__] += 1
            program = make_identity_program()
            family = "identity_fallback_after_export_error"
            fallback_count += 1
            task_report["export_error"] = f"{type(exc).__name__}: {exc}"
            export_program_onnx(program, out_path)
            task_report["status"] = "fallback_exported"

        family_counts[family] += 1
        task_report["family"] = family
        task_report["onnx_path"] = str(out_path)
        task_report["file_size_bytes"] = out_path.stat().st_size

        if validate:
            try:
                validation = validate_submission_model(out_path)
                task_report["local_validation"] = {
                    "ok": True,
                    "score": validation.score,
                    "op_types": list(validation.op_types),
                    "cost_total": validation.cost.total,
                }
            except Exception as exc:
                validation_errors[type(exc).__name__] += 1
                task_report["local_validation"] = {
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }

        if official is not None:
            try:
                task_report["official_check_network"] = bool(official(str(out_path)))
                if not task_report["official_check_network"]:
                    official_errors["check_network_false"] += 1
            except Exception as exc:
                official_errors[type(exc).__name__] += 1
                task_report["official_check_network"] = False
                task_report["official_check_error"] = f"{type(exc).__name__}: {exc}"

        if len(smoke_reports) < smoke_limit:
            try:
                smoke = _runtime_smoke(out_path, task_path)
            except Exception as exc:
                smoke = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            smoke["task_id"] = task_id
            smoke_reports.append(smoke)

        task_to_onnx[task_id] = out_path
        task_reports.append(task_report)

        if index % 50 == 0:
            print(f"[neurogolf] built {index}/{len(task_paths)}", file=sys.stderr)

    submission_zip = build_submission_zip(task_to_onnx, out_dir / "submission.zip")
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    validation_ok = sum(1 for row in task_reports if row.get("local_validation", {}).get("ok") is True)
    official_ok = sum(1 for row in task_reports if row.get("official_check_network") is True)

    report = {
        "schema": "scbe_neurogolf_blind_submission_v1",
        "run_id": out_dir.name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "tasks_dir": str(tasks_dir),
        "out_dir": str(out_dir),
        "submission_zip": str(submission_zip),
        "elapsed_ms": elapsed_ms,
        "tasks_total": len(task_paths),
        "synthesized_count": synthesized_count,
        "fallback_count": fallback_count,
        "family_counts": dict(sorted(family_counts.items())),
        "export_error_counts": dict(export_errors),
        "validation_enabled": validate,
        "validation_ok": validation_ok,
        "validation_error_counts": dict(validation_errors),
        "official_check_requested": official_check,
        "official_check_enabled": official is not None,
        "official_check_load_error": official_load_error,
        "official_check_ok": official_ok,
        "official_check_error_counts": dict(official_errors),
        "runtime_smoke": smoke_reports,
        "claim_boundary": {
            "blind_with_respect_to_test_outputs": True,
            "loader_reads": "train input/output plus test input only",
            "local_validation_is_not_official_score": True,
            "official_score_requires_kaggle_submission": True,
        },
        "tasks": task_reports,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a blind NeuroGolf Kaggle ONNX submission bundle.")
    parser.add_argument("--tasks-dir", type=Path, default=Path("artifacts/kaggle/neurogolf-2026/data"))
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--official-check", action="store_true")
    parser.add_argument("--smoke-limit", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    out_dir = args.out_dir or Path("artifacts/benchmarks/neurogolf_blind_submission") / _utc_run_id()
    report = build_blind_submission(
        tasks_dir=args.tasks_dir,
        out_dir=out_dir,
        limit=args.limit,
        validate=args.validate,
        official_check=args.official_check,
        smoke_limit=args.smoke_limit,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    latest_path = Path("artifacts/benchmarks/neurogolf_blind_submission/latest_report.json")
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps({k: v for k, v in report.items() if k != "tasks"}, indent=2, sort_keys=True))
    else:
        print(
            "neurogolf blind submission: "
            f"tasks={report['tasks_total']} synthesized={report['synthesized_count']} "
            f"fallback={report['fallback_count']} validation_ok={report['validation_ok']} "
            f"zip={report['submission_zip']}"
        )
        print(f"report={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
