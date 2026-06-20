from __future__ import annotations

from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ai-issue-summary.yml"


def test_ai_issue_summary_has_no_ai_write_path() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "actions/ai-inference" not in text
    assert "models: read" not in text
    assert "issues: write" not in text
    assert "pull-requests: write" not in text
    assert "createComment" not in text
    assert "github.rest.issues.createComment" not in text
    assert "actions/github-script" not in text
    assert "gh issue comment" not in text


def test_ai_issue_summary_records_only_deterministic_metadata() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "GHSA-g3f6-xrm9-h8gp remediated" in text
    assert "AI model invoked: no" in text
    assert "Public comment written: no" in text
    assert "Title characters" in text
    assert "Body characters" in text
    assert "Please summarize this GitHub issue" not in text
    assert "github.event.issue.title" not in text
    assert "github.event.issue.body" not in text


def test_ai_issue_summary_permissions_are_read_only() -> None:
    parsed = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))

    assert parsed["permissions"] == {"contents": "read"}


def test_ai_issue_summary_does_not_echo_untrusted_issue_text() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    forbidden_echoes = [
        r"echo\s+.*\$\{title\}",
        r"echo\s+.*\$\{body\}",
        r"\$\{\{\s*github\.event\.issue\.title\s*\}\}",
        r"\$\{\{\s*github\.event\.issue\.body\s*\}\}",
    ]
    for pattern in forbidden_echoes:
        assert re.search(pattern, text, flags=re.IGNORECASE) is None
