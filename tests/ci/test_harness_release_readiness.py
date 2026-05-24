from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "ci" / "harness_release_readiness.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "harness_release_readiness", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_harness_release_readiness_passes_with_complete_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    (tmp_path / "artifacts/benchmarks/cli_competitive").mkdir(parents=True)
    (tmp_path / "artifacts/benchmarks/agentbus_competitive_wedge").mkdir(parents=True)
    (tmp_path / "artifacts/benchmarks/operator_agent_bus_eval").mkdir(parents=True)
    (tmp_path / "artifacts/benchmarks/workflow_completion_checklist").mkdir(
        parents=True
    )
    (
        tmp_path
        / "artifacts/benchmarks/cli_competitive/cli_competitive_benchmark_latest.json"
    ).write_text(
        json.dumps({"ok": True, "ranking": [{"name": "scbe-geoseal", "score": 1.0}]}),
        encoding="utf-8",
    )
    (
        tmp_path / "artifacts/benchmarks/agentbus_competitive_wedge/latest_report.json"
    ).write_text(
        json.dumps(
            {
                "summary": {"decision": "PASS", "bus_wins": 2, "task_count": 2},
                "scbe_bus_scores": [
                    {"checks": {"local_private": True, "zero_cost": True}},
                    {"checks": {"local_private": True, "zero_cost": True}},
                ],
            }
        ),
        encoding="utf-8",
    )
    (
        tmp_path / "artifacts/benchmarks/operator_agent_bus_eval/latest_report.json"
    ).write_text(
        json.dumps(
            {
                "decision": "PASS",
                "score": 1.0,
                "dataset_score": 1.0,
                "endpoint_score": 1.0,
            }
        ),
        encoding="utf-8",
    )
    (
        tmp_path
        / "artifacts/benchmarks/workflow_completion_checklist/latest_completion_checklist.json"
    ).write_text(
        json.dumps(
            {"completion_status": "ready_to_claim_done", "known_failure_count": 0}
        ),
        encoding="utf-8",
    )

    report = module.build_report(tmp_path / "out")

    assert report["decision"] == "PASS"
    assert report["missing_artifacts"] == []
    assert report["failed_artifacts"] == []
    assert (tmp_path / report["json"]).exists()
    assert (tmp_path / report["markdown"]).exists()


def test_harness_release_readiness_blocks_missing_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    report = module.build_report(tmp_path / "out")

    assert report["decision"] == "BLOCK"
    assert "cli_competitive" in report["missing_artifacts"]
