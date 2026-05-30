from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "rubix_browser_hypercube_benchmark.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("rubix_browser_hypercube_benchmark", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_rubix_browser_hypercube_benchmark_passes(tmp_path: Path) -> None:
    module = _load_module()

    report = module.build_report(out_dir=tmp_path, run_id="pytest-rubix-browser")

    assert report["schema_version"] == "scbe_rubix_browser_hypercube_benchmark_v1"
    assert report["summary"]["decision"] == "PASS"
    assert report["summary"]["baseline_completed"] == 0
    assert report["summary"]["hypercube_completed"] == report["summary"]["task_count"]
    assert report["summary"]["baseline_illegal_moves"] > 0
    assert report["summary"]["hypercube_illegal_moves"] == 0
    assert report["proof_goal_split"]["proof_layer"]
    assert report["patent_provenance"]["refs"]


def test_rubix_browser_receipts_are_complete(tmp_path: Path) -> None:
    module = _load_module()
    report = module.build_report(out_dir=tmp_path, run_id="pytest-rubix-receipts")

    receipts = [item["receipt_hash"] for item in report["hypercube_results"]]

    assert len(receipts) == len(set(receipts))
    for result in report["hypercube_results"]:
        assert len(result["receipt_hash"]) == 64
        assert result["receipts"]
        assert all("permission" in receipt for receipt in result["receipts"])


def test_rubix_browser_cli_smoke(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark/rubix_browser_hypercube_benchmark.py",
            "--out-dir",
            str(tmp_path),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=False,
        timeout=60,
    )

    assert proc.returncode == 0, proc.stderr
    assert "decision=PASS" in proc.stdout
    assert (tmp_path / "latest_report.json").exists()
