from __future__ import annotations

from scripts.system.local_git_hygiene import (
    DEFAULT_UNTRACKED_EXCLUDES,
    SCBE_END,
    SCBE_START,
    merge_exclude_block,
    remove_exclude_block,
    unique_preserve,
)


def test_merge_exclude_block_replaces_prior_scbe_block() -> None:
    existing = "\n".join(
        [
            "*.tmp",
            SCBE_START,
            "old/path/",
            SCBE_END,
            "node_modules/",
            "",
        ]
    )

    updated = merge_exclude_block(existing, ["notes/agent-memory/", "notes/experiments/"])

    assert "*.tmp" in updated
    assert "node_modules/" in updated
    assert "old/path/" not in updated
    assert updated.count(SCBE_START) == 1
    assert updated.count(SCBE_END) == 1
    assert "notes/agent-memory/" in updated
    assert "notes/experiments/" in updated


def test_remove_exclude_block_preserves_non_scbe_entries() -> None:
    existing = "\n".join(
        [
            "*.tmp",
            SCBE_START,
            *DEFAULT_UNTRACKED_EXCLUDES,
            SCBE_END,
            "node_modules/",
            "",
        ]
    )

    stripped = remove_exclude_block(existing)

    assert SCBE_START not in stripped
    assert SCBE_END not in stripped
    assert "*.tmp" in stripped
    assert "node_modules/" in stripped
    for pattern in DEFAULT_UNTRACKED_EXCLUDES:
        assert pattern not in stripped


def test_unique_preserve_normalizes_and_deduplicates() -> None:
    values = ["notes\\agent-memory\\", "notes/agent-memory/", " docs-build-smoke "]

    assert unique_preserve(values) == ["notes/agent-memory/", "docs-build-smoke"]
