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

# Suspicion / quarantine parameters (defaults; tune per deployment via GeoSealConfig)
SUSPICION_DECAY = 0.5
SUSPICION_THRESHOLD = 3
QUARANTINE_CONSENSUS = 3
TRUST_DENOMINATOR = 20.0


@dataclass(frozen=True)
class GeoSealConfig:
    """Tunable GeoSeal parameters. Defaults preserve historical behavior exactly.

    Lets deployments (and hyperparameter sweeps) tune suspicion dynamics
    without editing module constants.
    """

    suspicion_decay: float = SUSPICION_DECAY
    suspicion_threshold: float = SUSPICION_THRESHOLD
    quarantine_consensus: int = QUARANTINE_CONSENSUS
    trust_denominator: float = TRUST_DENOMINATOR
    ball_radius: float = 0.99

    def __post_init__(self) -> None:
        if self.suspicion_decay < 0:
            raise ValueError(f"suspicion_decay must be >= 0, got {self.suspicion_decay}")
        if self.suspicion_threshold <= 0:
            raise ValueError(f"suspicion_threshold must be > 0, got {self.suspicion_threshold}")
        if self.quarantine_consensus < 1:
            raise ValueError(f"quarantine_consensus must be >= 1, got {self.quarantine_consensus}")
        if self.trust_denominator <= 0:
            raise ValueError(f"trust_denominator must be > 0, got {self.trust_denominator}")
        if not 0.0 < self.ball_radius < 1.0:
            raise ValueError(f"ball_radius must be in (0, 1), got {self.ball_radius}")


DEFAULT_CONFIG = GeoSealConfig()


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

    Raises ValueError on dimension mismatch (zip would silently truncate;
    the TypeScript port throws RangeError — behavior is now consistent).
    """
    if len(u) != len(v):
        raise ValueError(f"dimension mismatch: len(u)={len(u)} != len(v)={len(v)}")
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


def update_suspicion(
    agent: Agent,
    neighbor_id: str,
    is_anomaly: bool,
    config: Optional[GeoSealConfig] = None,
) -> None:
    """Update suspicion counters and quarantine status."""
    cfg = config or DEFAULT_CONFIG
    if is_anomaly:
        agent.suspicion_count[neighbor_id] = agent.suspicion_count.get(neighbor_id, 0) + 1
    else:
        agent.suspicion_count[neighbor_id] = max(0, agent.suspicion_count.get(neighbor_id, 0) - cfg.suspicion_decay)

    suspicious_neighbors = sum(1 for c in agent.suspicion_count.values() if c >= cfg.suspicion_threshold)
    agent.is_quarantined = suspicious_neighbors >= cfg.quarantine_consensus

    total_suspicion = sum(agent.suspicion_count.values())
    agent.trust_score = max(0, 1.0 - total_suspicion / cfg.trust_denominator)


# ---------------------------------------------------------------------------
# Swarm dynamics
# ---------------------------------------------------------------------------


def swarm_step(
    agents: List[Agent],
    drift_rate: float = 0.01,
    config: Optional[GeoSealConfig] = None,
) -> List[Agent]:
    """Run one swarm update step for all agents.

    Raises ValueError if agents carry positions of different dimensions —
    catching embedding mismatches here instead of deep in the force loop.
    """
    cfg = config or DEFAULT_CONFIG
    n = len(agents)
    if n == 0:
        return agents

    dim = len(agents[0].position)
    for a in agents:
        if len(a.position) != dim:
            raise ValueError(f"agent {a.id!r} has dimension {len(a.position)}, expected {dim} (from {agents[0].id!r})")

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
            update_suspicion(agents[j], agents[i].id, anomaly, cfg)

        # Apply force
        for k in range(dim):
            agents[i].position[k] += net_force[k] * drift_rate

        # Clamp to Poincaré ball
        agents[i].position = clamp_to_ball(agents[i].position, cfg.ball_radius)

    return agents


def run_swarm(
    agents: List[Agent],
    num_steps: int = 10,
    drift_rate: float = 0.01,
    config: Optional[GeoSealConfig] = None,
) -> List[Agent]:
    """Run multiple swarm steps."""
    for _ in range(num_steps):
        swarm_step(agents, drift_rate, config)
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


def compute_metrics(
    agents: List[Agent],
    rogue_id: str,
    config: Optional[GeoSealConfig] = None,
) -> GeoSealMetrics:
    """Compute GeoSeal metrics for a completed swarm run."""
    cfg = config or DEFAULT_CONFIG
    rogue = next((a for a in agents if a.id == rogue_id), None)
    if rogue is None:
        raise ValueError(f"Rogue agent not found: {rogue_id}")

    norm = _norm(rogue.position)

    suspicious = sum(1 for c in rogue.suspicion_count.values() if c >= cfg.suspicion_threshold)
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
