from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "arc_style_grid_benchmark.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("arc_style_grid_benchmark", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_arc_style_grid_benchmark_passes_local_fixtures(tmp_path: Path) -> None:
    module = _load_module()

    report = module.build_report(tmp_path)

    assert report["schema_version"] == "scbe_arc_style_grid_benchmark_v1"
    assert report["claim_boundary"] == "synthetic_arc_style_local_pretest_not_official_arc_agi_2"
    assert report["summary"]["decision"] in {"PASS", "HOLD"}
    assert report["summary"]["identity_passes"] < report["summary"]["neurogolf_passes"]
    assert report["summary"]["neurogolf_passes"] >= 4
    assert "unresolved_tasks" in report["summary"]
    assert report["patent_provenance"]["chain_of_provenance"]
    assert "proof_layer" in report["patent_provenance"]["proof_goal_split"]
    assert "goal_layer" in report["patent_provenance"]["proof_goal_split"]
    assert any(ref["path"] == "docs/PATENT_DETAILED_DESCRIPTION.md" for ref in report["patent_provenance"]["refs"])
    for fixture in report["fixtures"]:
        bifurcated = fixture["bifurcated_reasoning"]
        assert bifurcated["constructive_branch"]
        assert bifurcated["defender_branch"]
        assert "accept only" in bifurcated["merge_rule"]
        assert bifurcated["flow_model"]["merge"] == "restricted IR program plus receipt hash"
    assert (tmp_path / "latest_report.json").exists()
    assert (tmp_path / "LATEST.md").exists()


def test_arc_style_grid_receipts_are_unique(tmp_path: Path) -> None:
    module = _load_module()
    report = module.build_report(tmp_path)

    receipts = [item["receipt_hash"] for item in report["neurogolf_results"]]

    assert len(receipts) == len(set(receipts))
    assert all(len(receipt) == 64 for receipt in receipts)


def test_arc_style_grid_cli_smoke(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark/arc_style_grid_benchmark.py",
            "--out-dir",
            str(tmp_path),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=False,
        timeout=120,
    )

    assert proc.returncode == 0, proc.stderr
    assert "arc-style grid benchmark:" in proc.stdout
    assert (tmp_path / "latest_report.json").exists()
