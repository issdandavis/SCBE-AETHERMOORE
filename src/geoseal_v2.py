"""
GeoSeal v2: Mixed-Curvature Geometric Access Control Kernel
============================================================

Product manifold H^a x S^b x R^c where:
- Hyperbolic (H^a): hierarchy, trust zones, boundary quarantine
- Spherical  (S^b): tongue phase discipline, cyclic role coherence
- Gaussian   (R^c): retrieval uncertainty, memory write gating

Each agent carries three coordinate families:
  u in B^n   (Poincare ball position)     -- hierarchy / containment
  p in S^1   (phase as [cos t, sin t])    -- tongue discipline
  (mu, s^2)  (diagonal Gaussian)          -- retrieval confidence

Scoring fuses three independent geometry scores:
  trust = w_H * s_H + w_S * s_S + w_G * s_G
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple

from src.geoseal import (
    TONGUE_PHASES,
    SUSPICION_DECAY,
    SUSPICION_THRESHOLD,
    QUARANTINE_CONSENSUS,
    TRUST_DENOMINATOR,
    hyperbolic_distance,
    phase_deviation,
    clamp_to_ball,
)

# ---------------------------------------------------------------------------
# Fusion weights
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS: Tuple[float, float, float] = (0.4, 0.35, 0.25)  # wH, wS, wG
QUARANTINE_TRUST_THRESHOLD = 0.3
MEMORY_WRITE_THRESHOLD = 0.7

Action = Literal["ALLOW", "QUARANTINE", "DENY"]


# ---------------------------------------------------------------------------
# Mixed-geometry Agent (v2)
# ---------------------------------------------------------------------------


@dataclass
class MixedAgent:
    """Agent with hyperbolic position, spherical phase, and Gaussian uncertainty."""

    id: str
    position: List[float]
    phase: Optional[float]
    sigma: float = 0.0
    tongue: Optional[str] = None
    suspicion_count: Dict[str, float] = field(default_factory=dict)
    is_quarantined: bool = False
    trust_score: float = 0.5
    score_hyperbolic: float = 0.0
    score_phase: float = 0.0
    score_certainty: float = 0.0

    @property
    def phase_vec(self) -> Tuple[float, float]:
        """Phase as [cos theta, sin theta]."""
        if self.phase is not None:
            return (math.cos(self.phase), math.sin(self.phase))
        return (0.0, 0.0)


# ---------------------------------------------------------------------------
# Individual geometry scores
# ---------------------------------------------------------------------------


def score_hyperbolic(a: MixedAgent, b: MixedAgent) -> float:
    """s_H = 1 / (1 + d_H). High when close in Poincare ball."""
    d_h = hyperbolic_distance(a.position, b.position)
    return 1.0 / (1.0 + d_h)


def score_phase(a: MixedAgent, b: MixedAgent) -> float:
    """s_S = 1 - phaseDeviation. High when same tongue phase."""
    return 1.0 - phase_deviation(a.phase, b.phase)


def score_certainty(b: MixedAgent) -> float:
    """s_G = 1 / (1 + sigma). High when low uncertainty."""
    return 1.0 / (1.0 + b.sigma)


# ---------------------------------------------------------------------------
# Product manifold fusion
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FusedScore:
    trust: float
    s_h: float
    s_s: float
    s_g: float
    anomaly: bool
    action: Action


def fuse_scores(
    anchor: MixedAgent,
    candidate: MixedAgent,
    weights: Tuple[float, float, float] = DEFAULT_WEIGHTS,
) -> FusedScore:
    """Fuse three geometry scores into a single trust value."""
    w_h, w_s, w_g = weights
    s_h = score_hyperbolic(anchor, candidate)
    s_s = score_phase(anchor, candidate)
    s_g = score_certainty(candidate)

    trust = w_h * s_h + w_s * s_s + w_g * s_g
    anomaly = s_s < 0.5 or s_g < 0.5

    if trust >= MEMORY_WRITE_THRESHOLD:
        action: Action = "ALLOW"
    elif trust >= QUARANTINE_TRUST_THRESHOLD:
        action = "QUARANTINE"
    else:
        action = "DENY"

    return FusedScore(trust=trust, s_h=s_h, s_s=s_s, s_g=s_g, anomaly=anomaly, action=action)


# ---------------------------------------------------------------------------
# Suspicion (same algorithm as v1)
# ---------------------------------------------------------------------------


def update_suspicion_v2(agent: MixedAgent, neighbor_id: str, is_anomaly: bool) -> None:
    if is_anomaly:
        agent.suspicion_count[neighbor_id] = (
            agent.suspicion_count.get(neighbor_id, 0) + 1
        )
    else:
        agent.suspicion_count[neighbor_id] = max(
            0, agent.suspicion_count.get(neighbor_id, 0) - SUSPICION_DECAY
        )

    suspicious_neighbors = sum(
        1 for c in agent.suspicion_count.values() if c >= SUSPICION_THRESHOLD
    )
    agent.is_quarantined = suspicious_neighbors >= QUARANTINE_CONSENSUS

    total_suspicion = sum(agent.suspicion_count.values())
    agent.trust_score = max(0, 1.0 - total_suspicion / TRUST_DENOMINATOR)


# ---------------------------------------------------------------------------
# v2 Repulsion
# ---------------------------------------------------------------------------


def compute_repel_force_v2(
    agent_a: MixedAgent,
    agent_b: MixedAgent,
    anchor: Optional[MixedAgent] = None,
    base_strength: float = 1.0,
    weights: Tuple[float, float, float] = DEFAULT_WEIGHTS,
) -> Tuple[List[float], float, bool, FusedScore]:
    """v2 repulsion with uncertainty amplification.

    Returns (force, amplification, anomaly_flag, fused_score).
    """
    d_h = hyperbolic_distance(agent_a.position, agent_b.position)
    base_repulsion = base_strength / (d_h + 1e-6)

    amplification = 1.0
    anomaly_flag = False

    if agent_b.phase is None:
        amplification = 2.0
        anomaly_flag = True
    elif agent_a.phase is not None:
        deviation = phase_deviation(agent_a.phase, agent_b.phase)
        if d_h < 1.0 and deviation > 0.5:
            amplification = 1.5 + deviation
            anomaly_flag = True

    if agent_b.is_quarantined:
        amplification *= 1.5

    # v2: uncertainty amplification
    if agent_b.sigma > 0.5:
        amplification += 0.5
        anomaly_flag = True

    # v2: fused score
    # Only apply fused anomaly when source has valid phase; a null-phase source
    # would always produce sS=0, falsely flagging legitimate targets.
    ref = anchor or agent_a
    fused = fuse_scores(ref, agent_b, weights)
    if fused.anomaly and ref.phase is not None:
        amplification += 0.25
        anomaly_flag = True

    direction = [a - b for a, b in zip(agent_a.position, agent_b.position)]
    force = [d * base_repulsion * amplification for d in direction]

    agent_b.score_hyperbolic = fused.s_h
    agent_b.score_phase = fused.s_s
    agent_b.score_certainty = fused.s_g

    return force, amplification, anomaly_flag, fused


# ---------------------------------------------------------------------------
# v2 Swarm dynamics
# ---------------------------------------------------------------------------


def swarm_step_v2(
    agents: List[MixedAgent],
    drift_rate: float = 0.01,
    sigma_decay: float = 0.01,
    weights: Tuple[float, float, float] = DEFAULT_WEIGHTS,
) -> List[MixedAgent]:
    """One v2 swarm update step with uncertainty evolution."""
    n = len(agents)
    if n == 0:
        return agents

    dim = len(agents[0].position)

    for i in range(n):
        net_force = [0.0] * dim

        for j in range(n):
            if i == j:
                continue

            force, _amp, anomaly, _fused = compute_repel_force_v2(
                agents[i], agents[j], None, 1.0, weights
            )
            for k in range(dim):
                net_force[k] += force[k]

            update_suspicion_v2(agents[j], agents[i].id, anomaly)

        # Apply force
        for k in range(dim):
            agents[i].position[k] += net_force[k] * drift_rate
        agents[i].position = clamp_to_ball(agents[i].position, 0.99)

        # v2: uncertainty evolution
        # Sigma is driven by how much others flag THIS agent (suspicion_count),
        # not by how many anomalies it detects on others.
        total_incoming = sum(agents[i].suspicion_count.values())
        if total_incoming > 3:
            agents[i].sigma = min(10.0, agents[i].sigma + sigma_decay * 2)
        else:
            agents[i].sigma = max(0, agents[i].sigma - sigma_decay)

    return agents


def run_swarm_v2(
    agents: List[MixedAgent],
    num_steps: int = 10,
    drift_rate: float = 0.01,
    sigma_decay: float = 0.01,
    weights: Tuple[float, float, float] = DEFAULT_WEIGHTS,
) -> List[MixedAgent]:
    """Run multiple v2 swarm steps."""
    for _ in range(num_steps):
        swarm_step_v2(agents, drift_rate, sigma_decay, weights)
    return agents


# ---------------------------------------------------------------------------
# Batch scoring
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScoredCandidate:
    id: str
    trust: float
    action: Action
    s_h: float
    s_s: float
    s_g: float
    is_quarantined: bool
    sigma: float


def score_all_candidates(
    anchors: List[MixedAgent],
    candidates: List[MixedAgent],
    weights: Tuple[float, float, float] = DEFAULT_WEIGHTS,
) -> List[ScoredCandidate]:
    """Score all candidates against tongue anchors. Returns sorted by trust desc."""
    results: List[ScoredCandidate] = []

    for candidate in candidates:
        best: Optional[FusedScore] = None
        for anchor in anchors:
            fused = fuse_scores(anchor, candidate, weights)
            if best is None or fused.trust > best.trust:
                best = fused

        if best is not None:
            results.append(
                ScoredCandidate(
                    id=candidate.id,
                    trust=best.trust,
                    action=best.action,
                    s_h=best.s_h,
                    s_s=best.s_s,
                    s_g=best.s_g,
                    is_quarantined=candidate.is_quarantined,
                    sigma=candidate.sigma,
                )
            )

    results.sort(key=lambda x: x.trust, reverse=True)
    return results
