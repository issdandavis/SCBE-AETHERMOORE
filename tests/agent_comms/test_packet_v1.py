"""Tests for agent_packet_v1 (compact AI-to-AI task packet).

Guards:
- packet validates phase, permission, expected_output, tongue against canonical sets
- context_ref kinds are bounded (sha256 / path / url / manifest_id)
- pack() round-trips through AgentMessage.payload without information loss
- enforce_budget rejects packets whose own input cost overruns their budget
- hash_state is order-stable (same parts -> same hash regardless of order)
- MergeReport rejects evidence/contact_point tags missing the 'channel:value' shape
"""

from __future__ import annotations

import pytest

from src.agent_comms import (
    AgentMessage,
    AgentPacketV1,
    Budget,
    BudgetExceeded,
    ContextRef,
    MergeReport,
    Route,
    enforce_budget,
    hash_state,
    new_task_id,
    pack,
    packet_input_tokens,
    unpack,
)
from src.agent_comms.packet import SCHEMA


def _minimal_packet(**overrides) -> AgentPacketV1:
    base = dict(
        task_id=new_task_id("test"),
        phase="plan",
        route=Route(tongue="KO", domain="code", permission="read"),
        context_refs=[ContextRef(kind="sha256", value="a" * 64)],
        state_hash=hash_state("repo:main", "branch:test"),
        budget=Budget(max_input_tokens=1024, max_output_tokens=256),
        request="Summarize the manifest at the referenced sha256.",
        expected_output="delta",
    )
    base.update(overrides)
    return AgentPacketV1(**base)


def test_packet_validates_phase():
    pkt = _minimal_packet(phase="invalid_phase")
    with pytest.raises(ValueError, match="phase"):
        pkt.validate()


def test_packet_validates_tongue():
    bad_route = Route(tongue="ZZ", domain="code", permission="read")
    pkt = _minimal_packet(route=bad_route)
    with pytest.raises(ValueError, match="tongue"):
        pkt.validate()


def test_packet_validates_permission():
    bad_route = Route(tongue="KO", domain="code", permission="DESTROY")
    pkt = _minimal_packet(route=bad_route)
    with pytest.raises(ValueError, match="permission"):
        pkt.validate()


def test_packet_validates_expected_output():
    pkt = _minimal_packet(expected_output="prose")
    with pytest.raises(ValueError, match="expected_output"):
        pkt.validate()


def test_context_ref_validates_kind():
    pkt = _minimal_packet(context_refs=[ContextRef(kind="bittorrent", value="abc")])
    with pytest.raises(ValueError, match="context_ref.kind"):
        pkt.validate()


def test_packet_round_trip_through_agent_message():
    pkt = _minimal_packet()
    msg: AgentMessage = pack(pkt, sender_id="agent_a", recipient_id="agent_b")
    assert msg.tongue == "KO"
    assert msg.target == "code"
    assert msg.payload["schema"] == SCHEMA
    assert msg.sender_id == "agent_a"
    assert msg.recipient_id == "agent_b"

    recovered = unpack(msg)
    assert recovered.task_id == pkt.task_id
    assert recovered.phase == pkt.phase
    assert recovered.route.tongue == pkt.route.tongue
    assert recovered.route.domain == pkt.route.domain
    assert recovered.state_hash == pkt.state_hash
    assert recovered.context_refs[0].value == pkt.context_refs[0].value
    assert recovered.expected_output == pkt.expected_output


def test_unpack_rejects_non_packet_payload():
    msg = AgentMessage(sender_id="a", recipient_id="b", payload={"foo": "bar"})
    with pytest.raises(ValueError, match="agent_packet_v1"):
        unpack(msg)


def test_enforce_budget_passes_when_under():
    pkt = _minimal_packet(budget=Budget(max_input_tokens=10000, max_output_tokens=512))
    enforce_budget(pkt)


def test_enforce_budget_fails_when_request_too_large():
    big_request = "x" * 10_000
    pkt = _minimal_packet(
        request=big_request,
        budget=Budget(max_input_tokens=64, max_output_tokens=64),
    )
    with pytest.raises(BudgetExceeded):
        enforce_budget(pkt)


def test_packet_input_tokens_is_monotonic_in_request_size():
    small = _minimal_packet(request="short")
    big = _minimal_packet(request="x" * 4000)
    assert packet_input_tokens(big) > packet_input_tokens(small)


def test_hash_state_is_order_stable():
    a = hash_state("branch:main", "manifest:v2", "router:6/6")
    b = hash_state("router:6/6", "branch:main", "manifest:v2")
    assert a == b
    assert a.startswith("sha256:")


def test_hash_state_changes_with_content():
    a = hash_state("branch:main")
    b = hash_state("branch:dev")
    assert a != b


def test_merge_report_validates_decision():
    report = MergeReport(
        claim="router stays at 6/6",
        delta={"deterministic_route_acc": 1.0},
        evidence=["test:passed", "hash:matched"],
        contact_points=["hard:pytest", "near:router"],
        decision="rubber_stamp",
    )
    with pytest.raises(ValueError, match="decision"):
        report.validate()


def test_merge_report_rejects_untagged_evidence():
    report = MergeReport(
        claim="all green",
        delta={},
        evidence=["passed"],
        contact_points=["hard:pytest"],
        decision="promote",
    )
    with pytest.raises(ValueError, match="channel:value"):
        report.validate()


def test_merge_report_round_trip():
    report = MergeReport(
        claim="v2 manifest verified",
        delta={"files": 5, "concept_ids": 95},
        evidence=["test:8/8", "hash:matched"],
        contact_points=["hard:pytest", "near:manifest"],
        decision="promote",
        task_id="task-abc",
    )
    report.validate()
    recovered = MergeReport.from_dict(report.to_dict())
    assert recovered.claim == report.claim
    assert recovered.decision == report.decision
    assert recovered.evidence == report.evidence
