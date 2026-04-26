from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "agentbus_competitive_wedge.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "agentbus_competitive_wedge", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_baseline_scores_completion_but_not_bus_artifacts() -> None:
    module = _load_module()
    task = module.TASKS[0]
    result = module.run_baseline(task)
    score = module.score_baseline(result)

    assert result.ok is True
    assert score["checks"]["task_completed"] is True
    assert score["checks"]["local_private"] is True
    assert score["checks"]["zero_cost"] is True
    assert score["checks"]["provider_selected"] is False
    assert score["checks"]["observable_state_artifact"] is False
    assert score["score"] < 0.5


def test_agentbus_competitive_wedge_report_passes(tmp_path: Path) -> None:
    module = _load_module()
    report = module.build_report(out_dir=tmp_path, run_id="pytest-wedge")

    assert report["summary"]["decision"] == "PASS"
    assert report["summary"]["bus_wins"] == report["summary"]["task_count"]
    assert report["summary"]["scbe_bus_avg"] >= 0.9
    assert report["summary"]["scbe_bus_avg"] > report["summary"]["baseline_avg"]
    assert (tmp_path / "pytest-wedge" / "report.json").exists()
    assert (tmp_path / "LATEST.md").exists()

    for score in report["scbe_bus_scores"]:
        assert score["checks"]["task_completed"] is True
        assert score["checks"]["operation_shape"] is True
        assert score["checks"]["dispatch_event"] is True
        assert score["checks"]["observable_state_artifact"] is True
