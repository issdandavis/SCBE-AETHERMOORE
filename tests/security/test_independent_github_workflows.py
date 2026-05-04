from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def _workflow_text(name: str) -> str:
    path = WORKFLOWS / name
    return path.read_text(encoding="utf-8")


def test_claude_workflows_are_local_only_and_do_not_call_external_ai_actions() -> None:
    for name in ("claude.yml", "claude-code-review.yml"):
        text = _workflow_text(name)
        yaml.safe_load(text)

        assert "anthropics/claude-code-action" not in text
        assert "CLAUDE_CODE_OAUTH_TOKEN" not in text
        assert "id-token: write" not in text
        assert "pull-requests: write" not in text
        assert "External AI invoked: no" in text


def test_daily_dependency_audit_uses_one_rolling_issue_not_daily_issue_spam() -> None:
    text = _workflow_text("daily-dep-audit.yml")
    yaml.safe_load(text)

    assert "Dependency Vulnerabilities - rolling" in text
    assert "Dependency Vulnerabilities - ${today}" not in text
    assert "issues.update" in text
    assert "updates one rolling issue" in text
