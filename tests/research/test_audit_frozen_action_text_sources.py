"""Tests for exact ordinary/retention text source span auditing."""

from __future__ import annotations

import hashlib

from scripts.research.audit_frozen_action_text_sources import (
    _candidate_reason,
    _line_blocks,
    _scan_source,
)


def test_line_blocks_reconstruct_exact_half_open_spans() -> None:
    text = "First line.\nSecond line.\n\nThird line without a final newline."
    lines = text.splitlines(keepends=True)
    blocks = list(_line_blocks(text))

    assert blocks == [
        (0, 2, "First line.\nSecond line.\n"),
        (3, 4, "Third line without a final newline."),
    ]
    for start, end, excerpt in blocks:
        assert "".join(lines[start:end]) == excerpt


def test_ordinary_requires_action_language_and_rejects_action_envelopes() -> None:
    neutral = (
        "This paragraph explains a stable concept with enough ordinary words to satisfy the minimum language checks."
    )
    action = (
        "This paragraph explains how a caller can run a loop and return a value while preserving ordinary program flow."
    )
    envelope = (
        "This paragraph says run <ACTION> while containing enough words to look like an otherwise valid source excerpt."
    )

    assert (
        _candidate_reason(
            neutral,
            lane="ordinary",
            min_prompt_bytes=20,
            max_prompt_bytes=512,
        )
        == "no_action_term"
    )
    assert (
        _candidate_reason(
            action,
            lane="ordinary",
            min_prompt_bytes=20,
            max_prompt_bytes=512,
        )
        is None
    )
    assert (
        _candidate_reason(
            envelope,
            lane="ordinary",
            min_prompt_bytes=20,
            max_prompt_bytes=512,
        )
        == "action_envelope_marker"
    )


def test_scan_source_seals_exact_excerpt_and_keeps_rows_ineligible(tmp_path) -> None:
    source = tmp_path / "source.txt"
    source.write_text(
        "A caller can run this ordinary function and return a value without requesting any external action.\n"
        "The surrounding explanation remains part of the same exact source paragraph.\n\n"
        "A short block.\n",
        encoding="utf-8",
        newline="\n",
    )

    rows, summary = _scan_source(
        source,
        source="fixture",
        source_family="fixture-family",
        lane="ordinary",
        limit=8,
        min_prompt_bytes=40,
        max_prompt_bytes=512,
    )

    assert summary["accepted_candidates"] == 1
    assert len(rows) == 1
    row = rows[0]
    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    exact = "".join(lines[row["span"]["start"] : row["span"]["end"]])
    assert row["excerpt_sha256"] == hashlib.sha256(exact.encode("utf-8")).hexdigest()
    assert row["review_status"] == "NOT_REVIEWED"
    assert row["training_eligible"] is False
