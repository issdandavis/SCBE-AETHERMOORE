from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ai-issue-summary.yml"


def test_ai_issue_summary_has_no_ai_write_path() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "actions/ai-inference" not in text
    assert "models: read" not in text
    assert "issues: write" not in text
    assert "createComment" not in text
    assert "github.rest.issues.createComment" not in text


def test_ai_issue_summary_records_only_deterministic_metadata() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "AI model invoked: no" in text
    assert "Public comment written: no" in text
    assert "Title characters" in text
    assert "Body characters" in text
    assert "Please summarize this GitHub issue" not in text
