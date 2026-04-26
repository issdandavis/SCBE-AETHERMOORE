from __future__ import annotations

from scripts.system.repo_cleanliness_audit import (
    action_for,
    classify_path,
    normalize_status_path,
)


def test_cleanliness_audit_classifies_generated_and_local_state_paths() -> None:
    assert classify_path("docs-build-local/index.html") == "generated_or_build_output"
    assert classify_path(".scbe/geoseal_calls.jsonl") == "local_state"
    assert (
        action_for("??", "generated_or_build_output")
        == "ignore_or_offload_if_not_intentional_source"
    )


def test_cleanliness_audit_classifies_source_docs_and_private_lanes() -> None:
    assert classify_path("src/coding_spine/shared_ir.py") == "source_or_tests"
    assert classify_path("tests/test_repo_cleanliness_audit.py") == "source_or_tests"
    assert (
        classify_path("docs/CODING_SYSTEMS_MASTER_REFERENCE.md") == "docs_or_canonical"
    )
    assert (
        classify_path("docs/legal/patent_63_961_403_nonprovisional/notes.md")
        == "notes_or_private_proposal"
    )


def test_cleanliness_audit_normalizes_renamed_status_path() -> None:
    assert (
        normalize_status_path('"old path.md -> docs/new path.md"') == "docs/new path.md"
    )
