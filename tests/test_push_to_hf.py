from __future__ import annotations

from pathlib import Path

from scripts.push_to_hf import build_readme
from scripts.push_to_hf import validate_repo_id


def test_validate_repo_id() -> None:
    assert validate_repo_id("issda/aethermore-perplexity")
    assert not validate_repo_id("bad")
    assert not validate_repo_id("bad/")
    assert not validate_repo_id("/bad")


def test_build_readme_contains_core_fields(tmp_path: Path) -> None:
    readme = build_readme(
        repo_id="issda/aethermore-perplexity",
        data_path=tmp_path / "perplexity_normalized.jsonl",
        row_count=12,
        columns=["thread_id", "role", "text"],
    )
    assert "issda/aethermore-perplexity" in readme
    assert "Rows: `12`" in readme
    assert "`thread_id`" in readme

