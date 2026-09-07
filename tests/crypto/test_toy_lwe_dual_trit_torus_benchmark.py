from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "toy_lwe_dual_trit_torus_benchmark.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("toy_lwe_dual_trit_torus_benchmark", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_small_benchmark_has_ground_truth_and_matched_accounting(
    tmp_path: Path,
) -> None:
    module = _load_module()
    output = tmp_path / "report.json"
    report = module.run(
        seeds=3,
        dimension=4,
        samples=7,
        budget=30,
        foothold_seeds=8,
        output=output,
    )
    assert output.is_file()
    assert report["status"] in {"UNDERPOWERED", "MEASURED_ADVANTAGE"}
    assert report["controls"]["exact_interval_bound_ground_truth_agreement"] is True
    assert report["controls"]["all_heuristic_objective_budgets_matched"] is True
    assert all(
        row["methods"][method]["objective_evaluations"] == 30 for row in report["rows"] for method in module.METHODS
    )
    assert set(report["source_receipts"]) >= {
        "benchmark_driver",
        "phase_search",
        "exact_30_degree_rotation",
        "dual_ternary_state_space",
        "hypercube_neighbors",
        "toy_lwe_objective_and_bounds",
    }
