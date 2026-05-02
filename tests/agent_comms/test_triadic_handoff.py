from __future__ import annotations

from src.agent_comms import AgentPacketV1, Budget, ContextRef, Route, hash_state
from src.agent_comms.triadic_handoff import build_tri_bundle_receipt, evaluate_triadic_handoff


def _packet() -> AgentPacketV1:
    return AgentPacketV1(
        task_id="triadic-handoff-001",
        phase="verify",
        route=Route(tongue="RU", domain="agentic-harness", permission="read"),
        context_refs=[ContextRef(kind="path", value="docs/specs/TRIADIC_BRAID_SOURCE_MAP.md", bytes=4096)],
        state_hash=hash_state("triadic", "handoff"),
        budget=Budget(max_input_tokens=1024, max_output_tokens=256),
        request="Verify the triadic handoff gate against the source map.",
        expected_output="verdict",
        created_at=1.0,
    )


def test_tri_bundle_receipt_is_deterministic_for_packet() -> None:
    packet = _packet()

    left = build_tri_bundle_receipt(packet)
    right = build_tri_bundle_receipt(packet)

    assert left == right
    assert left.schema == "tri_bundle_receipt_v1"
    assert left.tongue == "ru"
    assert left.packet_sha256.startswith("sha256:")
    assert left.cluster_count > 0
    assert len(left.first_cluster_id) == 64
    assert len(left.last_cluster_id) == 64


def test_triadic_handoff_allows_low_risk_signaled_cross_provider_handoff() -> None:
    result = evaluate_triadic_handoff(
        _packet(),
        model_refs=["ollama:local-a", "deepseek:deepseek-chat"],
        lane_signal="provider-pair:ollama->deepseek:verify",
        fast_signal=0.2,
        memory_signal=0.2,
        governance_signal=0.2,
    )

    assert result.decision == "ALLOW"
    assert result.lane_switch.signal_required is True
    assert result.lane_switch.signal_present is True
    assert result.sheaf_gate["decision"] == "ALLOW"
    assert result.shadow["task_id"] == "triadic-handoff-001"


def test_triadic_handoff_denies_unsignaled_cross_provider_handoff() -> None:
    result = evaluate_triadic_handoff(
        _packet(),
        model_refs=["ollama:local-a", "deepseek:deepseek-chat"],
        fast_signal=0.8,
        memory_signal=0.7,
        governance_signal=0.75,
    )

    assert result.decision == "DENY"
    assert result.lane_switch.signal_required is True
    assert result.lane_switch.signal_present is False
    assert "lane switch" in result.reason


def test_triadic_handoff_quarantines_unstable_three_watcher_consensus() -> None:
    result = evaluate_triadic_handoff(
        _packet(),
        model_refs=["ollama:local-a"],
        fast_signal=0.9,
        memory_signal=0.1,
        governance_signal=0.1,
    )

    assert result.decision == "QUARANTINE"
    assert result.sheaf_gate["decision"] == "QUARANTINE"
    assert result.sheaf_gate["sheaf_obstructions"] > 0
