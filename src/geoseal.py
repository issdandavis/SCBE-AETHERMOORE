"""
GeoSeal: Geometric Access Control Kernel (Python Reference Implementation)
==========================================================================

Immune-like dynamics for Spiralverse RAG latent space using hyperbolic
geometry and phase-discipline to quarantine adversarial or off-grammar
retrievals.

Core mechanisms:
- Phase validity -> repulsion amplification (null phase = 2.0x, wrong = 1.5x + deviation)
- Per-neighbor suspicion counters (temporal integration, filters transient flukes)
- Spatial consensus threshold (3+ neighbors agreeing = quarantine mode)
- Second-stage amplification (force x 1.5 when quarantined)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Sacred Tongues phase mapping
# ---------------------------------------------------------------------------

TONGUE_PHASES: Dict[str, float] = {
    "KO": 0.0,
    "AV": math.pi / 3,
    "RU": 2 * math.pi / 3,
    "CA": math.pi,
    "UM": 4 * math.pi / 3,
    "DR": 5 * math.pi / 3,
}

# Suspicion / quarantine parameters
SUSPICION_DECAY = 0.5
SUSPICION_THRESHOLD = 3
QUARANTINE_CONSENSUS = 3
TRUST_DENOMINATOR = 20.0


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


@dataclass
class Agent:
    """An agent in the GeoSeal swarm (retrieval chunk, tongue, or memory)."""

    id: str
    position: List[float]
    phase: Optional[float]
    tongue: Optional[str] = None
    suspicion_count: Dict[str, float] = field(default_factory=dict)
    is_quarantined: bool = False
    trust_score: float = 1.0


# ---------------------------------------------------------------------------
# Poincaré ball primitives
# ---------------------------------------------------------------------------


def _norm_sq(v: List[float]) -> float:
    return sum(x * x for x in v)


def _norm(v: List[float]) -> float:
    return math.sqrt(_norm_sq(v))


def hyperbolic_distance(u: List[float], v: List[float]) -> float:
    """Compute hyperbolic distance in Poincaré ball model.

    d_H(u, v) = arcosh(1 + 2 * ||u - v||² / ((1 - ||u||²)(1 - ||v||²)))
    """
    diff = [a - b for a, b in zip(u, v)]
    diff_norm_sq = _norm_sq(diff)
    u_norm_sq = _norm_sq(u)
    v_norm_sq = _norm_sq(v)

    denom = (1 - u_norm_sq) * (1 - v_norm_sq)
    if denom <= 0:
        return float("inf")

    arg = 1 + 2 * diff_norm_sq / denom
    return math.acosh(max(1.0, arg))


def phase_deviation(phase1: Optional[float], phase2: Optional[float]) -> float:
    """Compute normalized phase deviation in [0, 1].

    None phase = maximum deviation (1.0).
    """
    if phase1 is None or phase2 is None:
        return 1.0

    diff = abs(phase1 - phase2)
    if diff > math.pi:
        diff = 2 * math.pi - diff

    return diff / math.pi


def clamp_to_ball(v: List[float], r_max: float = 0.99) -> List[float]:
    """Clamp a vector to the Poincaré ball of radius r_max."""
    n = _norm(v)
    if n >= r_max:
        scale = r_max / n
        return [x * scale for x in v]
    return list(v)


# ---------------------------------------------------------------------------
# Repulsion force
# ---------------------------------------------------------------------------


def compute_repel_force(
    agent_a: Agent,
    agent_b: Agent,
    base_strength: float = 1.0,
) -> Tuple[List[float], float, bool]:
    """Core GeoSeal repulsion computation.

    Returns (force_vector, amplification, anomaly_flag).
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

    direction = [a - b for a, b in zip(agent_a.position, agent_b.position)]
    force = [d * base_repulsion * amplification for d in direction]

    return force, amplification, anomaly_flag


# ---------------------------------------------------------------------------
# Suspicion tracking
# ---------------------------------------------------------------------------


def update_suspicion(agent: Agent, neighbor_id: str, is_anomaly: bool) -> None:
    """Update suspicion counters and quarantine status."""
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
# Swarm dynamics
# ---------------------------------------------------------------------------


def swarm_step(agents: List[Agent], drift_rate: float = 0.01) -> List[Agent]:
    """Run one swarm update step for all agents."""
    n = len(agents)
    if n == 0:
        return agents

    dim = len(agents[0].position)

    for i in range(n):
        net_force = [0.0] * dim

        for j in range(n):
            if i == j:
                continue

            force, _amp, anomaly = compute_repel_force(agents[i], agents[j])
            for k in range(dim):
                net_force[k] += force[k]

            # Update suspicion on the TARGET (j) from the SOURCE (i)
            # When i flags j as anomalous, j's suspicion record grows
            update_suspicion(agents[j], agents[i].id, anomaly)

        # Apply force
        for k in range(dim):
            agents[i].position[k] += net_force[k] * drift_rate

        # Clamp to Poincaré ball
        agents[i].position = clamp_to_ball(agents[i].position, 0.99)

    return agents


def run_swarm(
    agents: List[Agent],
    num_steps: int = 10,
    drift_rate: float = 0.01,
) -> List[Agent]:
    """Run multiple swarm steps."""
    for _ in range(num_steps):
        swarm_step(agents, drift_rate)
    return agents


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


@dataclass
class GeoSealMetrics:
    """Benchmarking metrics for a GeoSeal run."""

    time_to_isolation: int
    boundary_norm: float
    suspicion_consensus: float
    collateral_flags: int
    final_trust_scores: Dict[str, float]


def compute_metrics(agents: List[Agent], rogue_id: str) -> GeoSealMetrics:
    """Compute GeoSeal metrics for a completed swarm run."""
    rogue = next((a for a in agents if a.id == rogue_id), None)
    if rogue is None:
        raise ValueError(f"Rogue agent not found: {rogue_id}")

    norm = _norm(rogue.position)

    suspicious = sum(1 for c in rogue.suspicion_count.values() if c >= SUSPICION_THRESHOLD)
    total_neighbors = len(rogue.suspicion_count)
    consensus = suspicious / total_neighbors if total_neighbors > 0 else 0.0

    collateral = sum(1 for a in agents if a.is_quarantined and a.phase is not None)

    trust_scores = {a.id: a.trust_score for a in agents}

    return GeoSealMetrics(
        time_to_isolation=len(agents) if rogue.is_quarantined else -1,
        boundary_norm=norm,
        suspicion_consensus=consensus,
        collateral_flags=collateral,
        final_trust_scores=trust_scores,
    )
