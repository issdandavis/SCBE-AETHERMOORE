from __future__ import annotations

import dataclasses
import json
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "real_patch_task_benchmark.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("real_patch_task_benchmark", MODULE_PATH)
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
    assert report["summary"]["schematic_test_passes"] == report["summary"]["task_count"]
    assert report["summary"]["scbe_test_passes"] == report["summary"]["task_count"]
    assert report["summary"]["schematic_wins"] == report["summary"]["task_count"]
    assert report["summary"]["scbe_wins"] == report["summary"]["task_count"]
    assert (tmp_path / "pytest-real-patch" / "report.json").exists()
    assert (tmp_path / "latest_report.json").exists()
    assert (tmp_path / "LATEST.md").exists()

    for item in report["schematic_scores"]:
        assert item["checks"]["tests_passed"] is True
        assert item["checks"]["edit_scope_clean"] is True
        assert item["checks"]["patch_captured"] is True

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


def test_prime_schematic_repair_selects_from_evidence_not_task_id(
    tmp_path: Path,
) -> None:
    module = _load_module()
    task = module.TASKS[0]
    renamed_task = dataclasses.replace(task, task_id="renamed_hidden_anchor")

    result = module.run_lane(
        renamed_task,
        lane="prime_schematic_repair",
        root=tmp_path / "renamed",
        repair=module.schematic_repair,
    )

    assert result.tests_passed is True
    assert result.scope_ok is True
    receipt = json.loads((tmp_path / "renamed" / ".scbe_schematic_receipt.json").read_text(encoding="utf-8"))
    assert receipt["task_id"] == "renamed_hidden_anchor"
    assert receipt["selected_schematic"] == "slugify_separator_normal_form"
    assert receipt["selected_prime"] == 2
    assert receipt["prime_route"][0] == 2
