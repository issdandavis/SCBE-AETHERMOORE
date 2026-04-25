from __future__ import annotations

import pytest

from python.scbe.semantic_gate import (
    SemanticBlendPolicy,
    SemanticSignal,
    evaluate_semantic_gate,
)


def test_analogy_does_not_override_fact_for_high_risk_action() -> None:
    record = evaluate_semantic_gate(
        [
            SemanticSignal("measured-latency", 10.0, "fact", 0.95, "benchmark"),
            SemanticSignal(
                "metaphor-pressure", 1000.0, "analogy", 0.99, "creative-bridge"
            ),
        ],
        SemanticBlendPolicy(context="action", risk="critical", allow_analogy=False),
    )

    assert record.decision == "ESCALATE"
    assert record.blended_value == 10.0
    assert record.allowed_sources == ("fact",)
    assert record.blocked_sources == ("analogy",)
    assert record.blocked_labels == ("metaphor-pressure",)


def test_sandbox_can_allow_controlled_analogy_blending() -> None:
    record = evaluate_semantic_gate(
        [
            SemanticSignal("measured-fit", 0.7, "fact", 1.0, "unit-test"),
            SemanticSignal("shape-fit", 0.9, "analogy", 0.5, "geometry-probe"),
        ],
        SemanticBlendPolicy(context="sandbox", risk="low", allow_analogy=True),
    )

    assert record.decision == "ALLOW"
    assert record.allowed_sources == ("fact", "analogy")
    assert record.blocked_sources == ()
    assert record.blended_value == pytest.approx(((0.7 * 1.0) + (0.9 * 0.5)) / 1.5)


def test_fact_required_for_action() -> None:
    record = evaluate_semantic_gate(
        [
            SemanticSignal("semantic-intent", 0.8, "semantic", 0.8, "classifier"),
            SemanticSignal("route-analogy", 0.6, "analogy", 0.9, "geometry-probe"),
        ],
        SemanticBlendPolicy(context="action", risk="high", allow_analogy=True),
    )

    assert record.decision == "DENY"
    assert record.reason == "required fact channel missing"
    assert record.blended_value is None


def test_experimental_signal_quarantined_without_explicit_policy() -> None:
    record = evaluate_semantic_gate(
        [
            SemanticSignal(
                "verified-lane-score", 0.62, "fact", 0.9, "rename-benchmark"
            ),
            SemanticSignal("eml-tree-fit", 0.98, "experimental", 0.9, "eml-prototype"),
        ],
        SemanticBlendPolicy(context="routing", risk="medium", allow_experimental=False),
    )

    assert record.decision == "QUARANTINE"
    assert record.blended_value == pytest.approx(0.62)
    assert record.blocked_sources == ("experimental",)


def test_low_confidence_signal_is_blocked() -> None:
    record = evaluate_semantic_gate(
        [
            SemanticSignal("measured-fit", 0.7, "fact", 0.9, "benchmark"),
            SemanticSignal("weak-inference", 1.0, "inference", 0.2, "classifier"),
        ],
        SemanticBlendPolicy(context="routing", risk="medium", min_confidence=0.5),
    )

    assert record.decision == "ALLOW"
    assert record.blended_value == 0.7
    assert record.blocked_labels == ("weak-inference",)


def test_invalid_confidence_fails_closed() -> None:
    with pytest.raises(ValueError, match="confidence out of range"):
        evaluate_semantic_gate(
            [SemanticSignal("bad-signal", 1.0, "fact", 1.2, "bad-source")],
            SemanticBlendPolicy(context="routing", risk="low"),
        )
