from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "hydra_jobsite_conservation_benchmark.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "hydra_jobsite_conservation_benchmark", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_hydra_jobsite_conserves_all_project_obligations(tmp_path: Path) -> None:
    module = _load_module()

    report = module.build_report(tmp_path)

    assert report["schema_version"] == "scbe_hydra_jobsite_conservation_benchmark_v1"
    assert report["summary"]["decision"] == "PASS"
    assert report["summary"]["case_count"] >= 6
    assert report["summary"]["hydra_passed"] == report["summary"]["case_count"]
    assert report["summary"]["hydra_average_conservation_score"] >= 0.95
    assert report["summary"]["hydra_margin_over_best_baseline"] >= 0.25
    assert (tmp_path / "latest_report.json").exists()
    assert (tmp_path / "LATEST.md").exists()


def test_pricing_change_forces_finance_security_and_inspection_lanes() -> None:
    module = _load_module()
    case = next(
        item for item in module.CASES if item.case_id == "pricing_checkout_launch"
    )

    result = module.run_case(case)
    hydra = result["planner_results"]["hydra_jobsite"]

    assert hydra["passed"] is True
    assert "margin_and_tax_review" in hydra["covered"]
    assert "billing_secret_guard" in hydra["covered"]
    assert "price_claim_inspection" in hydra["covered"]
    assert not hydra["critical_misses"]


def test_single_lane_baseline_misses_cross_team_obligations() -> None:
    module = _load_module()
    case = next(
        item for item in module.CASES if item.case_id == "chemistry_demo_launch"
    )

    result = module.run_case(case)
    baseline = result["planner_results"]["single_lane_code"]

    assert baseline["passed"] is False
    assert "wet_lab_claim_boundary" in baseline["critical_misses"]
    assert "misuse_safety_gate" in baseline["critical_misses"]


def test_hydra_jobsite_cli_smoke(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark/hydra_jobsite_conservation_benchmark.py",
            "--out-dir",
            str(tmp_path),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=False,
        timeout=30,
    )

    assert proc.returncode == 0, proc.stderr
    assert "scbe_hydra_jobsite_conservation_benchmark_v1" in proc.stdout
    assert (tmp_path / "latest_report.json").exists()
