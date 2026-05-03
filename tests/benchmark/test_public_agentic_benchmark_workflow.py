from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "public-agentic-benchmarks.yml"


def test_scored_aider_workflow_exports_visible_diagnostics() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "aider_polyglot_scored/diagnostics" in workflow
    assert 'find "${latest_dir}" -name ".aider.results.json"' in workflow
    assert ".chat.history.md" in workflow
    assert "${safe_name}.results.json" in workflow
