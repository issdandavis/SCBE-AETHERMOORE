"""Tests for the ARC-AGI-2 local baseline benchmark."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "arc_agi2_local_benchmark.py"
DATA_ROOT = ROOT / "artifacts" / "arc-data" / "data"


def _load_module():
    spec = importlib.util.spec_from_file_location("arc_agi2_local_benchmark", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_data_is_present() -> None:
    assert DATA_ROOT.exists(), (
        "artifacts/arc-data not found — run: "
        "git clone --depth 1 https://github.com/arcprize/ARC-AGI-2 artifacts/arc-data"
    )
    assert (DATA_ROOT / "evaluation").exists()
    assert (DATA_ROOT / "training").exists()
    eval_tasks = list((DATA_ROOT / "evaluation").glob("*.json"))
    assert len(eval_tasks) >= 100, f"expected >=100 eval tasks, got {len(eval_tasks)}"


def test_score_prediction_exact_match() -> None:
    module = _load_module()
    assert module.score_prediction([[1, 2], [3, 4]], [[1, 2], [3, 4]]) is True
    assert module.score_prediction([[1, 2], [3, 4]], [[1, 2], [3, 5]]) is False
    assert module.score_prediction([[1]], [[1, 2]]) is False
    assert module.score_prediction([[1]], []) is False


def test_baselines_run_on_smoke_set(tmp_path: Path) -> None:
    module = _load_module()
    report = module.build_report(
        split="evaluation",
        limit=10,
        solvers=["identity", "last_train_output"],
        out_dir=tmp_path,
        run_id="pytest-arc-smoke",
    )

    assert report["schema_version"] == "scbe_arc_agi2_local_v1"
    assert report["task_count"] == 10
    assert report["split"] == "evaluation"
    assert len(report["baselines"]) == 2
    assert report["best_baseline"]["pass_rate"] >= 0.0

    for b in report["baselines"]:
        assert "solver" in b
        assert "pass_rate" in b
        assert "passes" in b
        assert "task_count" in b
        assert b["task_count"] == 10

    assert (tmp_path / "pytest-arc-smoke" / "report.json").exists()
    assert (tmp_path / "latest_report.json").exists()
    assert (tmp_path / "LATEST.md").exists()


def test_claim_boundary_present() -> None:
    module = _load_module()
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        report = module.build_report(
            split="evaluation", limit=5, out_dir=Path(tmp), run_id="pytest-claim"
        )
    boundary = report["claim_boundary"]
    assert len(boundary) >= 3
    assert any("not a submission" in item.lower() or "leaderboard" in item.lower() for item in boundary)


def test_majority_color_produces_valid_grid() -> None:
    module = _load_module()
    tasks = module._load_tasks("evaluation", limit=5)
    for task in tasks:
        grid = module.solve_majority_color(task)
        rows, cols = module._dims(task.test_input)
        assert len(grid) == rows
        assert all(len(row) == cols for row in grid)


def test_random_solver_consistent_with_seed() -> None:
    import random

    module = _load_module()
    tasks = module._load_tasks("evaluation", limit=3)

    rng1 = random.Random(42)
    rng2 = random.Random(42)
    for task in tasks:
        g1 = module.solve_random(task, rng=rng1)
        g2 = module.solve_random(task, rng=rng2)
        assert g1 == g2
