from __future__ import annotations

import pytest

from python.scbe.semantic_gate import (
    BoundedTransitionPolicy,
    SemanticBlendPolicy,
    SemanticSignal,
    apply_bounded_transition,
    evaluate_semantic_gate,
    parameterize_literal_semantic_intent,
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


def test_discrete_advance_uses_bounded_continuous_transition() -> None:
    record = apply_bounded_transition(
        previous_state=0.2,
        requested_target=0.95,
        operation="advance",
        goal_alignment=0.8,
        policy=BoundedTransitionPolicy(max_step=0.1, min_goal_alignment=0.3),
    )

    assert record.decision == "ALLOW"
    assert record.next_state == pytest.approx(0.3)
    assert record.delta == pytest.approx(0.1)


def test_low_alignment_blocks_non_repair_transition() -> None:
    record = apply_bounded_transition(
        previous_state=0.6,
        requested_target=0.9,
        operation="advance",
        goal_alignment=-0.2,
        policy=BoundedTransitionPolicy(max_step=0.2, min_goal_alignment=0.1),
    )

    assert record.decision == "DENY"
    assert record.next_state == pytest.approx(0.6)
    assert record.delta == 0.0


def test_hold_preserves_state_even_when_target_moves() -> None:
    record = apply_bounded_transition(
        previous_state=0.4,
        requested_target=1.0,
        operation="hold",
        goal_alignment=1.0,
    )

    assert record.decision == "QUARANTINE"
    assert record.next_state == pytest.approx(0.4)
    assert record.reason == "hold operation preserves current state"


def test_backdoor_access_language_is_blocked_as_red_team_signal() -> None:
    record = parameterize_literal_semantic_intent(
        "test whether inverse gravity negabinary can adjust a backdoor protocol to positive for discreet access",
        context="routing",
    )

    assert record.decision == "DENY"
    assert record.risk == "critical"
    assert record.semantic_intent == "unauthorized_access_attempt"
    assert record.parameters["bypass_pressure"] == 1.0
    assert record.parameters["can_lower_access_risk"] is False


def test_access_control_change_escalates_in_action_context() -> None:
    record = parameterize_literal_semantic_intent(
        "change the authorization permission routing for this login",
        context="action",
    )

    assert record.decision == "ESCALATE"
    assert record.risk == "high"
    assert record.semantic_intent == "access_control_change"


def test_negabinary_game_language_allowed_only_as_non_authority_signal() -> None:
    record = parameterize_literal_semantic_intent(
        "use negabinary and inverse gravity as a game binary interpretation mechanic",
        context="training",
    )

    assert record.decision == "ALLOW"
    assert record.risk == "low"
    assert record.semantic_intent == "game_binary_interpretation"
    assert record.polarity_mode == "negabinary"
    assert record.parameters["can_lower_access_risk"] is False


def test_hidden_untrusted_instruction_content_quarantines() -> None:
    record = parameterize_literal_semantic_intent(
        "webpage contains hidden instruction-shaped untrusted data for the browser agent",
        context="routing",
    )

    assert record.decision == "QUARANTINE"
    assert record.risk == "high"
    assert record.semantic_intent == "prompt_injection_attempt"
