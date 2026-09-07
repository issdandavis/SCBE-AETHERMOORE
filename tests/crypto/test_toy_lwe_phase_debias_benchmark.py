"""Small integration check for phase-debias measurement accounting."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "toy_lwe_phase_debias_benchmark.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("toy_lwe_phase_debias_benchmark", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_small_debias_benchmark_preserves_exactness_and_accounting(tmp_path: Path) -> None:
    module = _load_module()
    output = tmp_path / "report.json"
    report = module.run(
        seed_start=500,
        seeds=3,
        dimension=4,
        samples=7,
        budget=30,
        bound_seeds=12,
        random_coverage_controls=3,
        exhaustive_audit_seeds=3,
        output=output,
    )
    assert output.is_file()
    assert report["status"] in {
        "INTERFERENCE_REMOVED_MEASURED_END_TO_END_ADVANTAGE",
        "INTERFERENCE_REMOVED_OBJECTIVE_UNDERPOWERED",
    }
    assert report["coverage"]["orbit_cover_phase"]["candidates"] == 30
    assert all(
        row["methods"][method]["objective_evaluations"] == 30 for row in report["rows"] for method in module.METHODS
    )
    assert all(row["bounds"][method]["exact"] is True for row in report["rows"] for method in module.BOUND_METHODS)
    assert all(row["exhaustive_audited"] is True for row in report["rows"])
