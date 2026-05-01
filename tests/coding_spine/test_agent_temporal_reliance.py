"""Tests for temporal reliance / execution stack helpers."""

from __future__ import annotations

from src.coding_spine.agent_temporal_reliance import (
    AnchorState,
    PrerequisiteRef,
    ReanchorDecision,
    build_agent_execution_stack_v1,
    evaluate_reanchor,
)


def test_evaluate_reanchor_proceed_observe():
    out = evaluate_reanchor(
        [
            PrerequisiteRef("t1", AnchorState.PROVEN, "abc", stale=False),
        ],
        permission_mode="observe",
    )
    assert out["decision"] == ReanchorDecision.PROCEED.value


def test_evaluate_reanchor_stale_proven_downgrades_for_write():
    out = evaluate_reanchor(
        [
            PrerequisiteRef("t1", AnchorState.PROVEN, "abc", stale=True),
        ],
        permission_mode="workspace-write",
    )
    assert out["decision"] == ReanchorDecision.OBSERVE_ONLY.value
    assert any("stale" in r for r in out["reasons"])


def test_build_agent_execution_stack_has_layers():
    stack = build_agent_execution_stack_v1()
    assert stack["schema_version"] == "scbe_agent_execution_stack_v1"
    assert "execution_layer" in stack
    assert "review_layer" in stack
    assert "temporal_reliance_layer" in stack
    assert stack["bijection_boundary"]["generation_path"] == "non_bijective"
