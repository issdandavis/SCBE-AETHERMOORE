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


def test_nightly_ops_is_parseable_and_keeps_job_env_outside_steps() -> None:
    workflow = yaml.safe_load(_workflow_text("nightly-ops.yml"))
    job = workflow["jobs"]["orchestrate"]

    assert workflow["permissions"] == {"contents": "read"}
    assert job["env"] == {"SCBE_MODE": "ci"}
    assert [step["uses"] for step in job["steps"] if "uses" in step] == [
        "actions/checkout@v6",
        "actions/setup-node@v6",
        "actions/setup-python@v6",
    ]
    assert [step["id"] for step in job["steps"] if "id" in step] == [
        "step_01_smoke",
        "step_02_plan",
        "step_03_packetize",
    ]
