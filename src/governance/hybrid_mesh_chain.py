"""Hybrid governance: coupled tongue dynamics + hash-linked audit chain.

This module provides a bounded 6D governance mesh update and an append-only
hash-linked ledger for tamper-evident decision history.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence

TONGUES: tuple[str, ...] = ("KO", "AV", "RU", "CA", "UM", "DR")
DEFAULT_BASE_WEIGHTS: tuple[float, ...] = (1.00, 1.62, 2.62, 4.24, 6.85, 11.09)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _softplus(x: float) -> float:
    # Stable softplus.
    if x > 30.0:
        return x
    if x < -30.0:
        return math.exp(x)
    return math.log1p(math.exp(x))


def _vec6(values: Sequence[float], *, name: str) -> List[float]:
    if len(values) != 6:
        raise ValueError(f"{name} must have 6 elements, got {len(values)}")
    return [float(v) for v in values]


def _mat6(values: Sequence[Sequence[float]], *, name: str) -> List[List[float]]:
    if len(values) != 6:
        raise ValueError(f"{name} must be 6x6, got {len(values)} rows")
    out: List[List[float]] = []
    for row in values:
        out.append(_vec6(row, name=name))
    return out


def _matvec6(mat: Sequence[Sequence[float]], vec: Sequence[float]) -> List[float]:
    v = _vec6(vec, name="vec")
    m = _mat6(mat, name="mat")
    out: List[float] = []
    for i in range(6):
        acc = 0.0
        for j in range(6):
            acc += m[i][j] * v[j]
        out.append(acc)
    return out


def _ring_coupling(scale: float) -> List[List[float]]:
    mat = [[0.0 for _ in range(6)] for _ in range(6)]
    for i in range(6):
        mat[i][(i - 1) % 6] = scale
        mat[i][(i + 1) % 6] = scale
    return mat


@dataclass(frozen=True)
class HybridGovernanceConfig:
    base_weights: Sequence[float] = DEFAULT_BASE_WEIGHTS
    explicit_coupling: Sequence[Sequence[float]] = tuple(tuple(x) for x in _ring_coupling(0.08))
    implicit_coupling: Sequence[Sequence[float]] = tuple(tuple(x) for x in _ring_coupling(0.03))
    damping: float = 0.08
    breathing_amp: float = 0.03
    breathing_freq: float = 0.07
    state_bound: float = 4.0
    sync_eta: float = 0.15
    sync_coherence_min: float = 0.70
    sync_drift_max: float = 0.45
    risk_quarantine: float = 0.50
    risk_deny: float = 0.85


@dataclass(frozen=True)
class AgentMeshState:
    agent_id: str
    tongue_state: Sequence[float]
    drift: float = 0.0
    conflict: float = 0.0
    coherence: float = 1.0
    modifier_bias: float = 0.0
    breathing_phase: float = 0.0

    def __post_init__(self) -> None:
        _vec6(self.tongue_state, name="tongue_state")


@dataclass(frozen=True)
class GovernanceDecision:
    agent_id: str
    risk: float
    decision: str
    reasons: List[str]
    effective_weights: List[float]


@dataclass(frozen=True)
class LedgerBlock:
    index: int
    timestamp: str
    prev_hash: str
    payload: Dict[str, Any]
    block_hash: str


def effective_tongue_weights(
    tongue_state: Sequence[float],
    *,
    config: Optional[HybridGovernanceConfig] = None,
    modifier_bias: float = 0.0,
    max_weight: float = 50.0,
) -> List[float]:
    cfg = config or HybridGovernanceConfig()
    s = _vec6(tongue_state, name="tongue_state")
    base = _vec6(cfg.base_weights, name="base_weights")

    explicit = _matvec6(cfg.explicit_coupling, s)
    implicit = _matvec6(cfg.implicit_coupling, s)
    out: List[float] = []
    for i in range(6):
        b = math.log(max(1e-9, base[i]))
        val = _softplus(b + float(modifier_bias) + explicit[i] + implicit[i])
        out.append(_clamp(val, 1e-6, max_weight))
    return out


def step_agent_state(
    state: AgentMeshState,
    *,
    step_index: int,
    control: Optional[Sequence[float]] = None,
    config: Optional[HybridGovernanceConfig] = None,
) -> AgentMeshState:
    cfg = config or HybridGovernanceConfig()
    current = _vec6(state.tongue_state, name="tongue_state")
    ctrl = _vec6(control if control is not None else [0.0] * 6, name="control")

    angle = (2.0 * math.pi * cfg.breathing_freq * float(step_index)) + float(state.breathing_phase)
    breath = cfg.breathing_amp * math.sin(angle)
    next_state: List[float] = []
    for i in range(6):
        val = current[i] + ctrl[i] - (cfg.damping * current[i]) + breath
        next_state.append(_clamp(val, -cfg.state_bound, cfg.state_bound))
    return replace(state, tongue_state=next_state)


def _can_sync(state: AgentMeshState, cfg: HybridGovernanceConfig) -> bool:
    return float(state.coherence) >= float(cfg.sync_coherence_min) and float(state.drift) <= float(cfg.sync_drift_max)


def _mesh_sync(
    states: Mapping[str, AgentMeshState],
    adjacency: Mapping[str, Sequence[str]],
    *,
    config: HybridGovernanceConfig,
) -> Dict[str, AgentMeshState]:
    out: Dict[str, AgentMeshState] = dict(states)
    for agent_id, state in states.items():
        if not _can_sync(state, config):
            continue
        neighbors = [n for n in adjacency.get(agent_id, []) if n in states]
        if not neighbors:
            continue
        avg = [0.0] * 6
        for n in neighbors:
            vec = _vec6(states[n].tongue_state, name="tongue_state")
            for i in range(6):
                avg[i] += vec[i]
        inv = 1.0 / float(len(neighbors))
        avg = [x * inv for x in avg]
        current = _vec6(state.tongue_state, name="tongue_state")
        synced = []
        for i in range(6):
            moved = current[i] + (config.sync_eta * (avg[i] - current[i]))
            synced.append(_clamp(moved, -config.state_bound, config.state_bound))
        out[agent_id] = replace(state, tongue_state=synced)
    return out


def compute_agent_decision(
    state: AgentMeshState,
    *,
    config: Optional[HybridGovernanceConfig] = None,
) -> GovernanceDecision:
    cfg = config or HybridGovernanceConfig()
    weights = effective_tongue_weights(
        state.tongue_state,
        config=cfg,
        modifier_bias=state.modifier_bias,
    )
    abs_state = [abs(x) for x in _vec6(state.tongue_state, name="tongue_state")]
    denom = max(1e-9, sum(weights))
    activation = sum(w * x for w, x in zip(weights, abs_state)) / denom
    risk_input = (
        (1.4 * activation) + (1.2 * float(state.drift)) + (1.1 * float(state.conflict)) - (1.5 * float(state.coherence))
    )
    risk = _sigmoid(risk_input)

    reasons: List[str] = []
    decision = "ALLOW"
    if float(state.conflict) > 0.75 or float(state.drift) > 0.80:
        decision = "DENY"
        reasons.append("hard_gate_conflict_or_drift")
    elif (
        float(state.conflict) > 0.45
        or float(state.drift) > cfg.sync_drift_max
        or float(state.coherence) < cfg.sync_coherence_min
    ):
        decision = "QUARANTINE"
        reasons.append("sync_guard_violated")
    elif risk >= cfg.risk_deny:
        decision = "DENY"
        reasons.append("risk_above_deny")
    elif risk >= cfg.risk_quarantine:
        decision = "QUARANTINE"
        reasons.append("risk_above_quarantine")
    else:
        reasons.append("risk_within_allow")

    return GovernanceDecision(
        agent_id=state.agent_id,
        risk=risk,
        decision=decision,
        reasons=reasons,
        effective_weights=weights,
    )


def _canonical_payload(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash_block(index: int, timestamp: str, prev_hash: str, payload: Mapping[str, Any]) -> str:
    raw = f"{index}|{timestamp}|{prev_hash}|{_canonical_payload(payload)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def append_ledger_block(
    chain: List[LedgerBlock],
    payload: Mapping[str, Any],
    *,
    timestamp: Optional[str] = None,
) -> LedgerBlock:
    index = len(chain)
    ts = timestamp or _utc_now_iso()
    prev_hash = chain[-1].block_hash if chain else ("0" * 64)
    payload_dict = dict(payload)
    block_hash = _hash_block(index, ts, prev_hash, payload_dict)
    block = LedgerBlock(
        index=index,
        timestamp=ts,
        prev_hash=prev_hash,
        payload=payload_dict,
        block_hash=block_hash,
    )
    chain.append(block)
    return block


def verify_ledger(chain: Sequence[LedgerBlock]) -> bool:
    if not chain:
        return True
    expected_prev = "0" * 64
    for idx, block in enumerate(chain):
        if block.index != idx:
            return False
        if block.prev_hash != expected_prev:
            return False
        expected_hash = _hash_block(block.index, block.timestamp, block.prev_hash, block.payload)
        if block.block_hash != expected_hash:
            return False
        expected_prev = block.block_hash
    return True


def run_hybrid_tick(
    states: Mapping[str, AgentMeshState],
    adjacency: Mapping[str, Sequence[str]],
    *,
    step_index: int = 0,
    controls: Optional[Mapping[str, Sequence[float]]] = None,
    config: Optional[HybridGovernanceConfig] = None,
    ledger: Optional[List[LedgerBlock]] = None,
) -> tuple[Dict[str, AgentMeshState], Dict[str, GovernanceDecision], List[LedgerBlock]]:
    cfg = config or HybridGovernanceConfig()
    ctl = controls or {}
    local_next: Dict[str, AgentMeshState] = {}
    for agent_id, state in states.items():
        local_next[agent_id] = step_agent_state(
            state,
            step_index=step_index,
            control=ctl.get(agent_id),
            config=cfg,
        )
    synced = _mesh_sync(local_next, adjacency, config=cfg)

    decisions: Dict[str, GovernanceDecision] = {}
    for agent_id, state in synced.items():
        decisions[agent_id] = compute_agent_decision(state, config=cfg)

    active_ledger = ledger if ledger is not None else []
    decision_summary = {aid: d.decision for aid, d in decisions.items()}
    risk_summary = {aid: round(d.risk, 6) for aid, d in decisions.items()}
    append_ledger_block(
        active_ledger,
        {
            "type": "hybrid_tick",
            "step_index": int(step_index),
            "agents": sorted(list(states.keys())),
            "decisions": decision_summary,
            "risk": risk_summary,
        },
    )
    return synced, decisions, active_ledger


__all__ = [
    "TONGUES",
    "DEFAULT_BASE_WEIGHTS",
    "HybridGovernanceConfig",
    "AgentMeshState",
    "GovernanceDecision",
    "LedgerBlock",
    "effective_tongue_weights",
    "step_agent_state",
    "compute_agent_decision",
    "append_ledger_block",
    "verify_ledger",
    "run_hybrid_tick",
]
