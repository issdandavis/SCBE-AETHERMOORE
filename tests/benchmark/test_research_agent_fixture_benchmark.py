from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "research_agent_fixture_benchmark.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("research_agent_fixture_benchmark", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_research_agent_fixture_benchmark_passes(tmp_path: Path) -> None:
    module = _load_module()

    report = module.build_report(out_dir=tmp_path, run_id="pytest-research-agent")

    assert report["schema_version"] == "scbe_research_agent_fixture_benchmark_v1"
    assert report["claim_boundary"] == "local_browsecomp_gaia_style_fixtures_not_public_benchmark_scores"
    assert report["summary"]["decision"] == "PASS"
    assert report["summary"]["baseline_passes"] == 0
    assert report["summary"]["scbe_passes"] == report["summary"]["task_count"]
    assert report["proof_goal_split"]["proof_layer"]
    assert report["patent_provenance"]["refs"]
    assert (tmp_path / "pytest-research-agent" / "report.json").exists()
    assert (tmp_path / "LATEST.md").exists()


def test_research_agent_receipts_and_citations_are_present(tmp_path: Path) -> None:
    module = _load_module()
    report = module.build_report(out_dir=tmp_path, run_id="pytest-receipts")

    receipts = [item["receipt_hash"] for item in report["scbe_results"]]

    assert len(receipts) == len(set(receipts))
    for result in report["scbe_results"]:
        fixture = next(item for item in report["fixtures"] if item["task_id"] == result["task_id"])
        assert set(fixture["required_source_ids"]).issubset(set(result["citations"]))
        assert result["checks"]["evidence_trace_present"] is True
        assert len(result["receipt_hash"]) == 64


def test_research_agent_fixture_cli_smoke(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark/research_agent_fixture_benchmark.py",
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
