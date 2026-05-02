"""Tests for PacketLedger (do-not-repeat-known-context dedup).

Guards:
- fingerprint is stable across task_id / created_at variation
- fingerprint changes when intent fields change (request, refs, route, phase)
- seen() returns prior MergeReport on hit, None on miss
- record() filters non-promote when promoted_only=True
- LRU eviction at max_entries
- JSONL persistence round-trips across PacketLedger instances
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agent_comms import (
    AgentPacketV1,
    Budget,
    ContextRef,
    MergeReport,
    PacketLedger,
    Route,
    fingerprint,
    hash_state,
    new_task_id,
)


def _packet(**overrides) -> AgentPacketV1:
    base = dict(
        task_id=new_task_id("test"),
        phase="verify",
        route=Route(tongue="KO", domain="code", permission="read"),
        context_refs=[ContextRef(kind="path", value="README.md")],
        state_hash=hash_state("repo:main"),
        budget=Budget(max_input_tokens=1024, max_output_tokens=256),
        request="Verify the manifest summary at the referenced path.",
        expected_output="verdict",
    )
    base.update(overrides)
    return AgentPacketV1(**base)


def _promote_report(task_id: str = "task-x") -> MergeReport:
    return MergeReport(
        claim="ok",
        delta={"refs_resolved": 1},
        evidence=["test:passed", "hash:matched"],
        contact_points=["hard:pytest"],
        decision="promote",
        task_id=task_id,
    )


def test_fingerprint_stable_across_task_id():
    a = _packet(task_id="task-a")
    b = _packet(task_id="task-b")
    assert fingerprint(a) == fingerprint(b)


def test_fingerprint_changes_with_request():
    a = _packet(request="Do thing one.")
    b = _packet(request="Do thing two.")
    assert fingerprint(a) != fingerprint(b)


def test_fingerprint_changes_with_route():
    a = _packet(route=Route(tongue="KO", domain="code", permission="read"))
    b = _packet(route=Route(tongue="AV", domain="code", permission="read"))
    assert fingerprint(a) != fingerprint(b)


def test_fingerprint_changes_with_refs():
    a = _packet(context_refs=[ContextRef(kind="path", value="README.md")])
    b = _packet(context_refs=[ContextRef(kind="path", value="LICENSE")])
    assert fingerprint(a) != fingerprint(b)


def test_fingerprint_order_stable_for_refs():
    refs1 = [ContextRef(kind="path", value="A"), ContextRef(kind="path", value="B")]
    refs2 = [ContextRef(kind="path", value="B"), ContextRef(kind="path", value="A")]
    a = _packet(context_refs=refs1)
    b = _packet(context_refs=refs2)
    assert fingerprint(a) == fingerprint(b)


def test_ledger_seen_miss_returns_none():
    led = PacketLedger()
    assert led.seen(_packet()) is None


def test_ledger_seen_hit_returns_prior_report():
    led = PacketLedger()
    pkt = _packet()
    led.record(pkt, _promote_report("task-1"))
    recovered = led.seen(_packet(task_id="task-2"))
    assert recovered is not None
    assert recovered.decision == "promote"
    assert recovered.task_id == "task-1"


def test_ledger_skips_non_promote_when_promoted_only():
    led = PacketLedger(promoted_only=True)
    pkt = _packet()
    hold = MergeReport(
        claim="x",
        delta={},
        evidence=["test:flaky"],
        contact_points=["hard:pytest"],
        decision="hold",
    )
    led.record(pkt, hold)
    assert led.seen(pkt) is None
    assert len(led) == 0


def test_ledger_records_non_promote_when_promoted_only_false():
    led = PacketLedger(promoted_only=False)
    pkt = _packet()
    hold = MergeReport(
        claim="x",
        delta={},
        evidence=["test:flaky"],
        contact_points=["hard:pytest"],
        decision="hold",
    )
    led.record(pkt, hold)
    recovered = led.seen(pkt)
    assert recovered is not None
    assert recovered.decision == "hold"


def test_ledger_lru_eviction_at_max_entries():
    led = PacketLedger(max_entries=2)
    p1 = _packet(request="req-1")
    p2 = _packet(request="req-2")
    p3 = _packet(request="req-3")
    led.record(p1, _promote_report("t1"))
    led.record(p2, _promote_report("t2"))
    led.record(p3, _promote_report("t3"))
    # p1 should have been evicted
    assert led.seen(p1) is None
    assert led.seen(p2) is not None
    assert led.seen(p3) is not None
    assert len(led) == 2


def test_ledger_persists_to_jsonl_and_reloads(tmp_path: Path):
    path = tmp_path / "ledger.jsonl"
    pkt = _packet(request="persist me")
    led1 = PacketLedger(path=path)
    led1.record(pkt, _promote_report("t-persist"))
    assert path.is_file()

    led2 = PacketLedger(path=path)
    recovered = led2.seen(pkt)
    assert recovered is not None
    assert recovered.task_id == "t-persist"
    assert recovered.decision == "promote"


def test_ledger_contains_uses_fingerprint():
    led = PacketLedger()
    pkt = _packet()
    assert pkt not in led
    led.record(pkt, _promote_report())
    assert pkt in led


def test_ledger_rejects_zero_max():
    with pytest.raises(ValueError, match="max_entries"):
        PacketLedger(max_entries=0)
