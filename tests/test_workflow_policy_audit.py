from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "workflow_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("workflow_policy_audit", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_retired_workflow_alias_is_a_high_severity_finding(tmp_path: Path) -> None:
    module = load_module()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "pages-auto-deploy.yml").write_text("name: duplicate pages deploy\n", encoding="utf-8")

    results = module.scan_workflows(tmp_path)

    assert len(results) == 1
    assert len(results[0].issues) == 1
    assert results[0].issues[0].severity == "high"
    assert results[0].issues[0].rule == "RETIRED_REDUNDANT_WORKFLOW (use pages-deploy.yml)"


def test_canonical_workflow_is_not_marked_redundant(tmp_path: Path) -> None:
    module = load_module()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "pages-deploy.yml").write_text("name: canonical pages deploy\n", encoding="utf-8")

    results = module.scan_workflows(tmp_path)

    assert len(results) == 1
    assert results[0].issues == []
