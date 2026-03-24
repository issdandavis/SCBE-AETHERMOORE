from __future__ import annotations

from src.governance.hybrid_mesh_chain import (
    AgentMeshState,
    HybridGovernanceConfig,
    append_ledger_block,
    compute_agent_decision,
    effective_tongue_weights,
    run_hybrid_tick,
    verify_ledger,
)


def _l1_distance(a: AgentMeshState, b: AgentMeshState) -> float:
    return sum(abs(float(x) - float(y)) for x, y in zip(a.tongue_state, b.tongue_state))


def test_effective_weights_positive_and_bounded() -> None:
    state = AgentMeshState(
        agent_id="a1",
        tongue_state=[0.3, -0.1, 0.2, -0.4, 0.5, -0.2],
        modifier_bias=0.2,
    )
    weights = effective_tongue_weights(state.tongue_state, modifier_bias=state.modifier_bias)
    assert len(weights) == 6
    assert all(w > 0.0 for w in weights)
    assert all(w < 50.0 for w in weights)


def test_mesh_sync_moves_states_closer_when_sync_gate_passes() -> None:
    cfg = HybridGovernanceConfig(
        damping=0.0,
        breathing_amp=0.0,
        sync_eta=0.4,
        sync_coherence_min=0.5,
        sync_drift_max=0.5,
    )
    s1 = AgentMeshState(
        agent_id="a1",
        tongue_state=[1.0, 1.0, 1.0, -1.0, -1.0, -1.0],
        coherence=0.9,
        drift=0.1,
    )
    s2 = AgentMeshState(
        agent_id="a2",
        tongue_state=[-1.0, -1.0, -1.0, 1.0, 1.0, 1.0],
        coherence=0.9,
        drift=0.1,
    )
    before = _l1_distance(s1, s2)
    next_states, _, _ = run_hybrid_tick(
        {"a1": s1, "a2": s2},
        {"a1": ["a2"], "a2": ["a1"]},
        step_index=1,
        config=cfg,
    )
    after = _l1_distance(next_states["a1"], next_states["a2"])
    assert after < before


def test_mesh_sync_is_blocked_when_coherence_is_low() -> None:
    cfg = HybridGovernanceConfig(
        damping=0.0,
        breathing_amp=0.0,
        sync_eta=0.4,
        sync_coherence_min=0.8,
        sync_drift_max=0.5,
    )
    s1 = AgentMeshState(
        agent_id="a1",
        tongue_state=[1.0, 1.0, 1.0, -1.0, -1.0, -1.0],
        coherence=0.2,
        drift=0.1,
    )
    s2 = AgentMeshState(
        agent_id="a2",
        tongue_state=[-1.0, -1.0, -1.0, 1.0, 1.0, 1.0],
        coherence=0.2,
        drift=0.1,
    )
    before = _l1_distance(s1, s2)
    next_states, _, _ = run_hybrid_tick(
        {"a1": s1, "a2": s2},
        {"a1": ["a2"], "a2": ["a1"]},
        step_index=1,
        config=cfg,
    )
    after = _l1_distance(next_states["a1"], next_states["a2"])
    assert after == before


def test_decision_gate_can_deny_from_conflict_and_drift() -> None:
    risky = AgentMeshState(
        agent_id="a-risky",
        tongue_state=[0.6, 0.7, 0.8, 0.5, 0.9, 0.6],
        coherence=0.2,
        drift=0.9,
        conflict=0.8,
    )
    decision = compute_agent_decision(risky)
    assert decision.decision == "DENY"
    assert decision.risk >= 0.0


def test_hash_linked_ledger_detects_tamper() -> None:
    chain = []
    append_ledger_block(chain, {"step": 1, "decision": "ALLOW"})
    append_ledger_block(chain, {"step": 2, "decision": "QUARANTINE"})
    assert verify_ledger(chain)

    tampered = chain[1]
    tampered.payload["decision"] = "DENY"
    assert not verify_ledger(chain)
