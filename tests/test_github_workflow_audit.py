from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "system"
    / "github_workflow_audit.py"
)


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
    (workflows_dir / "codeql-analysis.yml").write_text(
        "name: CodeQL Analysis\n", encoding="utf-8"
    )
    (workflows_dir / "deploy-gke.yml").write_text(
        "name: Deploy GKE\n", encoding="utf-8"
    )

    results = module.audit_local_workflows(tmp_path, "socket blocked")

    assert [result.name for result in results] == ["codeql-analysis", "deploy-gke"]
    assert [result.category for result in results] == ["security", "deploy"]
    assert all(result.triage == "yellow" for result in results)
    assert all(result.last_conclusion == "local_only" for result in results)
    assert all(
        "local workflow inventory" in (result.fix_suggestion or "")
        for result in results
    )
    assert all(result.failure_reason == "socket blocked" for result in results)
