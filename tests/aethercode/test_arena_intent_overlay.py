from __future__ import annotations

import pytest

from src.aethercode.arena_intent_overlay import (
    SCHEMA_VERSION,
    build_intent_block,
    build_intent_overlay,
    render_intent_block_text,
)


def test_intent_overlay_builds_one_block_per_requested_seat() -> None:
    overlay = build_intent_overlay(
        problem="Prove whether this arena design can converge on a hard math task.",
        shared_code="def check(x): return x",
        previous_receipt="abc123",
        seat_ids=["ollama", "huggingface"],
    )

    assert overlay["schema_version"] == SCHEMA_VERSION
    assert overlay["seat_count"] == 2
    assert [block["seat"]["seat_id"] for block in overlay["blocks"]] == ["ollama", "huggingface"]
    assert all(block["previous_receipt"] == "abc123" for block in overlay["blocks"])
    assert all("receipt" in block["receipt_contract"].lower() for block in overlay["blocks"])
    assert all("capability" in block["build_state_contract"] for block in overlay["blocks"])


def test_intent_block_keeps_imaginary_paths_labeled_as_alternatives() -> None:
    block = build_intent_block(
        seat_id="google_ai",
        problem="Use imaginary inverse paths to explore a proof chain.",
        shared_code="",
    )

    assert block["seat"]["tongue"] == "DR"
    assert "Imaginary or inverse paths are allowed only as labeled alternatives" in block["route_contract"]
    assert "-0 HOLD" in block["advancement_rule"]


def test_intent_block_text_is_compact_and_agent_readable() -> None:
    block = build_intent_block(seat_id="cerebras", problem="Find the bug.")
    text = render_intent_block_text(block)

    assert "ARENA INTENT BLOCK" in text
    assert "problem_hash=" in text
    assert "build_state=" in text
    assert "advance=" in text


def test_unknown_seat_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown arena seat"):
        build_intent_block(seat_id="missing", problem="x")
