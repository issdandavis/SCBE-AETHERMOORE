import pytest

from src.interop.view_token_envelope import (
    ViewFrame,
    assess_overlay_worth,
    create_view_token_envelope,
    resolve_frame,
)


def _payload():
    return {
        "command": "route_candidate",
        "candidate_id": "cand-ko-dr-1",
        "schema_ref": "sysmlv2://scbe/example/control-transform",
        "payload": {"intent": "routing", "transform": "normalize"},
    }


def test_view_token_envelope_is_deterministic_and_payload_stable():
    frame_a = ViewFrame("KO", "control_flow", "sysmlv2://scbe/control")
    frame_b = ViewFrame("DR", "structure_verification", "protobuf://scbe/transform")

    first = create_view_token_envelope(_payload(), frame_a, frame_b)
    second = create_view_token_envelope(_payload(), frame_a, frame_b)

    assert first.token_id == second.token_id
    assert first.canonical_payload_sha256 == second.canonical_payload_sha256
    assert first.formation == "tetrahedral"
    assert len(first.state21) == 21

    resolved_a, decision_a = resolve_frame(first, "A")
    resolved_b, decision_b = resolve_frame(first, "B")

    assert decision_a.decision == "ALLOW"
    assert decision_b.decision == "ALLOW"
    assert resolved_a["active_tongue"] == "KO"
    assert resolved_b["active_tongue"] == "DR"
    assert resolved_a["role"] != resolved_b["role"]
    assert resolved_a["canonical_payload_sha256"] == resolved_b["canonical_payload_sha256"]


def test_invalid_frame_and_weak_visual_constraints_fail_closed():
    envelope = create_view_token_envelope(
        _payload(),
        ViewFrame("KO", "control_flow", "sysmlv2://scbe/control"),
        ViewFrame("DR", "structure_verification", "protobuf://scbe/transform"),
        visual_constraints={"complementarity_min": 0.4},
    )

    missing, missing_decision = resolve_frame(envelope, "C")
    weak, weak_decision = resolve_frame(envelope, "A")

    assert missing is None
    assert missing_decision.decision == "QUARANTINE"
    assert "unknown_frame" in missing_decision.reasons
    assert weak is None
    assert weak_decision.decision == "QUARANTINE"
    assert "low_complementarity" in weak_decision.reasons


def test_critical_command_payload_routes_to_ring_formation():
    envelope = create_view_token_envelope(
        _payload(),
        ViewFrame("KO", "control_flow", "xtce://scbe/command"),
        ViewFrame("DR", "structure_verification", "protobuf://scbe/command"),
        payload_formats=("xtce", "protobuf"),
        critical=True,
    )

    assert envelope.formation == "ring"
    decision = assess_overlay_worth(envelope)
    assert decision.decision == "ALLOW"
    assert decision.reasons == ("worth_test_pass",)
    assert decision.confidence >= 0.85


def test_non_dual_low_value_overlay_is_quarantined_not_promoted():
    envelope = create_view_token_envelope(
        _payload(),
        ViewFrame("KO", "control_flow", "json://scbe/control"),
        ViewFrame("AV", "transport_context", "json://scbe/context"),
        payload_formats=("json",),
    )

    decision = assess_overlay_worth(envelope)

    assert envelope.formation == "scatter"
    assert decision.decision == "QUARANTINE"
    assert "non_hodge_tongue_pair" in decision.reasons
    assert "weak_formation_route" in decision.reasons


def test_same_tongue_frame_is_rejected_at_construction_boundary():
    with pytest.raises(ValueError):
        ViewFrame("NOPE", "bad", "json://bad")
