from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "real_patch_task_benchmark.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "real_patch_task_benchmark", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_real_patch_task_benchmark_runs_challenge_fixtures(tmp_path: Path) -> None:
    module = _load_module()

    report = module.build_report(out_dir=tmp_path, run_id="pytest-real-patch")

    assert report["summary"]["decision"] == "PASS"
    assert report["summary"]["baseline_test_passes"] == 0
    assert report["summary"]["scbe_test_passes"] == report["summary"]["task_count"]
    assert report["summary"]["scbe_wins"] == report["summary"]["task_count"]
    assert (tmp_path / "pytest-real-patch" / "report.json").exists()
    assert (tmp_path / "latest_report.json").exists()
    assert (tmp_path / "LATEST.md").exists()

    for item in report["scbe_scores"]:
        assert item["checks"]["tests_passed"] is True
        assert item["checks"]["edit_scope_clean"] is True
        assert item["checks"]["patch_captured"] is True


def test_real_patch_task_scope_rejects_unexpected_files() -> None:
    module = _load_module()
    task = module.TASKS[0]
    result = module.LaneResult(
        lane="test",
        task_id=task.task_id,
        tests_passed=True,
        scope_ok=False,
        duration_ms=1,
        changed_files=["src/text_tools.py", "src/other.py"],
        unexpected_files=["src/other.py"],
        stdout_tail="",
        stderr_tail="",
        patch="diff",
    )

    score = module.score_result(result)

    assert score["checks"]["tests_passed"] is True
    assert score["checks"]["edit_scope_clean"] is False
    assert score["checks"]["no_unexpected_files"] is False
    assert score["score"] < 1.0
