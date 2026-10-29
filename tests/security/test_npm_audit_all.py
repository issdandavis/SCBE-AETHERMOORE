from __future__ import annotations

import json
from pathlib import Path

from scripts.security import npm_audit_all

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_dependency_tree(root: Path, relative: str) -> None:
    directory = root / relative
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "package.json").write_text('{"name":"fixture","version":"1.0.0"}\n', encoding="utf-8")
    (directory / "package-lock.json").write_text('{"lockfileVersion":3}\n', encoding="utf-8")


def test_discovery_finds_nested_projects_and_prunes_generated_or_archived_trees(tmp_path: Path) -> None:
    _write_dependency_tree(tmp_path, ".")
    _write_dependency_tree(tmp_path, "apps/active")
    _write_dependency_tree(tmp_path, "archive/retired")
    _write_dependency_tree(tmp_path, "node_modules/vendor")

    projects = npm_audit_all.discover_projects(tmp_path)

    assert [project.relative_directory for project in projects] == [".", "apps/active"]


def test_discovery_reports_orphan_lockfile_for_auditor_error(tmp_path: Path) -> None:
    (tmp_path / "package-lock.json").write_text('{"lockfileVersion":3}\n', encoding="utf-8")

    projects = npm_audit_all.discover_projects(tmp_path)

    assert len(projects) == 1
    assert projects[0].manifest_exists is False


def test_parser_recovers_json_after_cli_warning() -> None:
    payload = {
        "metadata": {"vulnerabilities": {"info": 0, "low": 0, "moderate": 1, "high": 0, "critical": 0, "total": 1}}
    }

    parsed = npm_audit_all.parse_json_document("npm warning fixture\n" + json.dumps(payload))

    assert npm_audit_all.vulnerability_counts(parsed)["moderate"] == 1


def test_threshold_only_fails_at_or_above_selected_severity() -> None:
    totals = {"info": 0, "low": 2, "moderate": 1, "high": 0, "critical": 0, "total": 3}

    assert npm_audit_all.exceeds_threshold(totals, "high") is False
    assert npm_audit_all.exceeds_threshold(totals, "moderate") is True
    assert npm_audit_all.exceeds_threshold(totals, "none") is False


def test_repository_inventory_covers_every_active_lockfile() -> None:
    projects = npm_audit_all.discover_projects(REPO_ROOT)
    paths = {project.relative_directory for project in projects}

    assert {
        ".",
        "apps/aether-desktop/shell",
        "apps/mobile/pwa",
        "conference-app",
        "game/spiral-engine",
        "packages/agent-bus",
        "packages/cli",
        "scbe-visual-system",
        "services/scbe-shim",
        "src",
    }.issubset(paths)
    assert not any(path == "archive" or path.startswith("archive/") for path in paths)


def test_security_workflows_use_the_repository_wide_auditor() -> None:
    workflows = REPO_ROOT / ".github" / "workflows"
    expected = {
        "npm-security-gate.yml",
        "security-checks.yml",
        "weekly-security-scan.yml",
    }

    for filename in expected:
        text = (workflows / filename).read_text(encoding="utf-8")
        assert "scripts/security/npm_audit_all.py" in text

    raw_workflow_audits = []
    for workflow in workflows.glob("*.yml"):
        if "run: npm audit" in workflow.read_text(encoding="utf-8"):
            raw_workflow_audits.append(workflow.name)
    assert raw_workflow_audits == []


def test_public_npm_publish_workflows_have_blocking_audits() -> None:
    workflows = REPO_ROOT / ".github" / "workflows"
    root_publish = (workflows / "npm-publish.yml").read_text(encoding="utf-8")
    assert "npm run security:audit:npm" in root_publish

    for filename in ("npm-publish-agent-bus.yml", "npm-publish-cli.yml"):
        text = (workflows / filename).read_text(encoding="utf-8")
        assert "npm audit --audit-level=high" in text
        assert "npm ci --ignore-scripts" in text


def test_agent_bus_ci_does_not_rewrite_the_lockfile() -> None:
    workflows = REPO_ROOT / ".github" / "workflows"
    for filename in (
        "agent-bus-auto-format.yml",
        "agent-bus-format-check.yml",
        "agent-bus-lint-and-test.yml",
    ):
        text = (workflows / filename).read_text(encoding="utf-8")
        assert "npm ci --ignore-scripts" in text
        assert "npm install --ignore-scripts" not in text


def test_weekly_scan_does_not_reintroduce_trivy() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "weekly-security-scan.yml").read_text(encoding="utf-8")

    assert "trivy" not in workflow.lower()


def test_dependabot_recursively_covers_monorepo_manifests() -> None:
    config = (REPO_ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")

    assert config.count('- "**/*"') >= 2
    assert 'package-ecosystem: "github-actions"' in config
