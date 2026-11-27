from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "system" / "github_workflow_audit.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("github_workflow_audit", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_categorize_workflow_name_groups_common_lanes() -> None:
    module = _load_module()
    assert module.categorize_workflow_name("codeql-analysis") == "security"
    assert module.categorize_workflow_name("deploy-gke") == "deploy"
    assert module.categorize_workflow_name("programmatic-hf-training") == "training"
    assert module.categorize_workflow_name("nightly-ops") == "automation"
    assert module.categorize_workflow_name("ci") == "ci"


def test_audit_local_workflows_builds_offline_inventory(tmp_path: Path) -> None:
    module = _load_module()
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "codeql-analysis.yml").write_text("name: CodeQL Analysis\n", encoding="utf-8")
    (workflows_dir / "deploy-gke.yml").write_text("name: Deploy GKE\n", encoding="utf-8")

    results = module.audit_local_workflows(tmp_path, "socket blocked")

    assert [result.name for result in results] == ["codeql-analysis", "deploy-gke"]
    assert [result.category for result in results] == ["security", "deploy"]
    assert all(result.triage == "yellow" for result in results)
    assert all(result.last_conclusion == "local_only" for result in results)
    assert all("local workflow inventory" in (result.fix_suggestion or "") for result in results)
    assert all(result.failure_reason == "socket blocked" for result in results)


def test_cube_projection_fix_calls_direct_runner_with_apply(monkeypatch, tmp_path: Path) -> None:
    module = _load_module()
    runner = tmp_path / "scripts" / "system" / "scbe_cube_pipeline.py"
    pipeline = tmp_path / "workflows" / "pipelines" / "nightly-ops.pipeline.json"
    runner.parent.mkdir(parents=True)
    pipeline.parent.mkdir(parents=True)
    runner.write_text("# runner\n", encoding="utf-8")
    pipeline.write_text("{}\n", encoding="utf-8")
    seen: list[list[str]] = []

    def fake_run(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        seen.append(command)
        assert kwargs["shell"] is False
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"changed": True, "after": {"solved": True}}),
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    reports = module.repair_cube_pipeline_projections(tmp_path, apply=True)

    assert reports == [
        {
            "spec": "workflows/pipelines/nightly-ops.pipeline.json",
            "returncode": 0,
            "applied": True,
            "changed": True,
            "solved": True,
        }
    ]
    assert seen[0][0] == sys.executable
    assert seen[0][-1] == "--apply"
