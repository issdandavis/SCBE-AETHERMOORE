"""
Crossing Energy Evaluator — Governance at Braid Intersections
==============================================================
Wires together:
    - dual_ternary.py   → E(p,m) = p² + m² + p·m  (structural tension)
    - trinary.py        → ALLOW/QUARANTINE/DENY     (governance routing)
    - hamiltonian_braid → valid_transition + φ^(d²)  (topology + cost)
    - tri_bundle.py     → 3×3×3 cluster encoding     (the data being evaluated)

At every braid crossing point, the evaluator:
    1. Computes the dual ternary energy E(p,m) of the crossing
    2. Checks if the transition is topologically valid (Chebyshev ≤ 1)
    3. Applies the harmonic cost wall C(d) = φ^(d²)
    4. Routes to ALLOW / QUARANTINE / DENY based on total cost

The energy function E(p,m) = p² + m² + p·m has these properties:
    - E(0,0) = 0         → equilibrium (minimum energy)
    - E(1,1) = 3         → constructive resonance (max positive)
    - E(-1,-1) = 1       → negative resonance (retreating coherently)
    - E(1,-1) = 1        → destructive interference (fighting)
    - E(-1,1) = 1        → destructive interference (opposing)

The crossing energy tells you the TENSION at each braid point.
High tension + invalid topology = DENY.
High tension + valid topology = QUARANTINE.
Low tension + valid topology = ALLOW.

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from src.crypto.tri_bundle import (
    PHI,
    Trit,
    TriBundleCluster,
    PolyglotCluster,
    InnerBundle,
)

# ---------------------------------------------------------------------------
# Constants & Thresholds
# ---------------------------------------------------------------------------

# Governance thresholds — calibrated to the E(p,m) energy landscape
QUARANTINE_THRESHOLD = 2.0  # E ≥ 2.0 → suspicious
DENY_THRESHOLD = 5.0  # E ≥ 5.0 → adversarial
COST_CAP = 1e6  # prevent float overflow on extreme d

# Phase labels (from hamiltonian_braid.py, replicated to avoid numpy dep)
PHASE_LABELS: Dict[Tuple[int, int], str] = {
    (-1, -1): "retreat-contract",
    (-1, 0): "retreat-hold",
    (-1, 1): "retreat-advance",
    (0, -1): "hold-contract",
    (0, 0): "equilibrium",
    (0, 1): "hold-advance",
    (1, -1): "advance-contract",
    (1, 0): "advance-hold",
    (1, 1): "advance-advance",
}


class Decision(Enum):
    """Governance routing decision at a braid crossing."""

    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    DENY = "DENY"


# ---------------------------------------------------------------------------
# Dual Ternary Energy (standalone — no numpy needed)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DualTernaryPair:
    """A dual ternary state: primary × mirror in {-1, 0, +1}²."""

    primary: int  # {-1, 0, +1}
    mirror: int  # {-1, 0, +1}

    def __post_init__(self):
        if self.primary not in (-1, 0, 1) or self.mirror not in (-1, 0, 1):
            raise ValueError(f"Values must be in {{-1, 0, 1}}, got ({self.primary}, {self.mirror})")

    @property
    def energy(self) -> float:
        """E(p, m) = p² + m² + p·m — structural tension."""
        p, m = self.primary, self.mirror
        return float(p * p + m * m + p * m)

    @property
    def phase(self) -> str:
        """Phase classification based on sign interaction."""
        p, m = self.primary, self.mirror
        if p > 0 and m > 0:
            return "constructive"
        elif p < 0 and m < 0:
            return "negative_resonance"
        elif (p > 0 and m < 0) or (p < 0 and m > 0):
            return "destructive"
        return "neutral"

    @property
    def label(self) -> str:
        return PHASE_LABELS.get((self.primary, self.mirror), "unknown")

    def index(self) -> int:
        """Unique index 0..8."""
        return (self.primary + 1) * 3 + (self.mirror + 1)


# All 9 states
ALL_STATES = [DualTernaryPair(p, m) for p in (-1, 0, 1) for m in (-1, 0, 1)]


# ---------------------------------------------------------------------------
# Topology: valid transitions (Chebyshev ≤ 1)
# ---------------------------------------------------------------------------


def valid_transition(s1: DualTernaryPair, s2: DualTernaryPair) -> bool:
    """Check if transition preserves braid topology.

    Valid iff Chebyshev distance ≤ 1 in the {-1,0,+1}² grid.
    Each trit can change by at most 1 step per timestep.
    """
    return abs(s1.primary - s2.primary) <= 1 and abs(s1.mirror - s2.mirror) <= 1


def valid_neighbors(state: DualTernaryPair) -> List[DualTernaryPair]:
    """All valid next states (including staying)."""
    return [s for s in ALL_STATES if valid_transition(state, s)]


def phase_deviation(current: DualTernaryPair, expected: DualTernaryPair) -> float:
    """Phase deviation in [0, 1]. 0 = match, 1 = max deviation."""
    dp = abs(current.primary - expected.primary)
    dq = abs(current.mirror - expected.mirror)
    return max(dp, dq) / 2.0


# ---------------------------------------------------------------------------
# Harmonic Cost Wall: C(d) = φ^(d²)
# ---------------------------------------------------------------------------


def harmonic_cost(d: float) -> float:
    """The harmonic wall: C(d) = φ^(d²).

    Deviation from the rail costs exponentially more:
        d ≈ 0: cost ≈ 1.0   (safe)
        d = 1: cost ≈ 1.618  (mild)
        d = 2: cost ≈ 6.854  (significant)
        d = 3: cost ≈ 76.01  (extreme)
        d = 4: cost ≈ 1364   (adversarial)
    """
    try:
        cost = PHI ** (d * d)
    except OverflowError:
        return COST_CAP
    return min(cost, COST_CAP)


def harmonic_cost_gradient(d: float) -> float:
    """dC/dd = 2d · ln(φ) · φ^(d²) — restoring force toward rail."""
    if abs(d) < 1e-12:
        return 0.0
    return 2.0 * d * math.log(PHI) * harmonic_cost(d)


# ---------------------------------------------------------------------------
# Crossing Result
# ---------------------------------------------------------------------------


@dataclass
class CrossingResult:
    """Full evaluation of a single braid crossing point."""

    # The dual ternary state at the crossing
    state: DualTernaryPair

    # Energy E(p,m) — structural tension
    energy: float

    # Phase classification
    phase: str

    # Topology
    topology_valid: bool
    prev_state: Optional[DualTernaryPair]

    # Harmonic cost
    braid_distance: float
    harmonic_cost: float

    # Governance decision
    decision: Decision
    decision_trit: Trit

    # Metadata
    position: int
    tongue_code: str

    @property
    def is_safe(self) -> bool:
        return self.decision == Decision.ALLOW

    @property
    def needs_review(self) -> bool:
        return self.decision == Decision.QUARANTINE

    @property
    def is_blocked(self) -> bool:
        return self.decision == Decision.DENY


# ---------------------------------------------------------------------------
# Core Evaluator
# ---------------------------------------------------------------------------


def _derive_dual_ternary(cluster: TriBundleCluster) -> DualTernaryPair:
    """Derive the dual ternary state from a tri-bundle cluster.

    Primary channel = Light bundle intent (the governance polarity).
    Mirror channel  = Math bundle convergence (the computation result).

    This maps the data payload (Light) against the computation result
    (Math), giving a 9-state characterization of the crossing.
    """
    # Light intent: strand_a[2] is the trit value
    light_intent = int(cluster.light.strand_a[2])

    # Math convergence: strand_a[2] is the result trit
    math_result = int(cluster.math.strand_a[2])

    # Clip to {-1, 0, 1}
    primary = max(-1, min(1, light_intent))
    mirror = max(-1, min(1, math_result))

    return DualTernaryPair(primary=primary, mirror=mirror)


def _compute_braid_distance(
    current: DualTernaryPair,
    expected: DualTernaryPair,
    cluster: TriBundleCluster,
    lambda_phase: float = 0.5,
) -> float:
    """Compute the braid distance incorporating both energy and phase.

    d_braid = √E(p,m) + λ · phase_deviation

    Uses sqrt of energy as the "spatial" component (energy is already
    quadratic), plus the phase deviation as the "topological" component.
    """
    spatial = math.sqrt(current.energy)
    phase_dev = phase_deviation(current, expected)
    return spatial + lambda_phase * phase_dev


def _route_decision(
    energy: float,
    cost: float,
    topology_valid: bool,
) -> Decision:
    """Route to governance decision based on energy, cost, and topology.

    Decision matrix:
        topology_valid + low energy    → ALLOW
        topology_valid + high energy   → QUARANTINE
        topology_invalid               → DENY (always — braid break)
        extreme energy                 → DENY
    """
    if not topology_valid:
        return Decision.DENY

    total_score = energy * cost

    if total_score >= DENY_THRESHOLD:
        return Decision.DENY
    elif total_score >= QUARANTINE_THRESHOLD:
        return Decision.QUARANTINE
    else:
        return Decision.ALLOW


DECISION_TO_TRIT = {
    Decision.ALLOW: Trit.PLUS,
    Decision.QUARANTINE: Trit.ZERO,
    Decision.DENY: Trit.MINUS,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate_crossing(
    cluster: TriBundleCluster,
    prev_state: Optional[DualTernaryPair] = None,
    expected_state: Optional[DualTernaryPair] = None,
    lambda_phase: float = 0.5,
    position: int = 0,
) -> CrossingResult:
    """Evaluate the governance decision at a single braid crossing.

    This is the core function. It:
    1. Derives the dual ternary state from the cluster
    2. Computes E(p,m) structural tension
    3. Checks topology against previous state
    4. Computes braid distance and harmonic cost
    5. Routes to ALLOW / QUARANTINE / DENY

    Args:
        cluster: The tri-bundle cluster at this position.
        prev_state: Previous crossing's dual ternary state (for topology).
        expected_state: Expected state at this position (for phase deviation).
            If None, equilibrium (0,0) is used.
        lambda_phase: Weight for phase deviation in braid distance.
        position: Position index in the sequence.

    Returns:
        CrossingResult with full evaluation.
    """
    # Step 1: Derive state
    state = _derive_dual_ternary(cluster)

    # Step 2: Energy
    energy = state.energy

    # Step 3: Topology
    topology_valid = True
    if prev_state is not None:
        topology_valid = valid_transition(prev_state, state)

    # Step 4: Braid distance and cost
    if expected_state is None:
        expected_state = DualTernaryPair(0, 0)  # equilibrium
    d_braid = _compute_braid_distance(state, expected_state, cluster, lambda_phase)
    cost = harmonic_cost(d_braid)

    # Step 5: Route
    decision = _route_decision(energy, cost, topology_valid)

    return CrossingResult(
        state=state,
        energy=energy,
        phase=state.phase,
        topology_valid=topology_valid,
        prev_state=prev_state,
        braid_distance=d_braid,
        harmonic_cost=cost,
        decision=decision,
        decision_trit=DECISION_TO_TRIT[decision],
        position=position,
        tongue_code=cluster.tongue_code,
    )


def evaluate_sequence(
    clusters: List[TriBundleCluster],
    expected_states: Optional[List[DualTernaryPair]] = None,
    lambda_phase: float = 0.5,
) -> List[CrossingResult]:
    """Evaluate governance across a sequence of braid crossings.

    Tracks topology validity between consecutive crossings.
    """
    results = []
    prev_state = None

    for i, cluster in enumerate(clusters):
        expected = expected_states[i] if expected_states and i < len(expected_states) else None
        result = evaluate_crossing(
            cluster=cluster,
            prev_state=prev_state,
            expected_state=expected,
            lambda_phase=lambda_phase,
            position=i,
        )
        results.append(result)
        prev_state = result.state

    return results


def evaluate_polyglot(
    polyglot: PolyglotCluster,
    prev_states: Optional[Dict[str, DualTernaryPair]] = None,
) -> Dict[str, CrossingResult]:
    """Evaluate all 6 tongue crossings at a single polyglot position.

    Returns a dict of tongue_code → CrossingResult.
    """
    results = {}
    for code, cluster in polyglot.clusters.items():
        prev = prev_states.get(code) if prev_states else None
        results[code] = evaluate_crossing(
            cluster=cluster,
            prev_state=prev,
            position=polyglot.position,
        )
    return results


# ---------------------------------------------------------------------------
# Sequence Governance Summary
# ---------------------------------------------------------------------------


@dataclass
class GovernanceSummary:
    """Summary of governance decisions across a sequence."""

    total: int
    allow_count: int
    quarantine_count: int
    deny_count: int
    mean_energy: float
    max_energy: float
    mean_cost: float
    max_cost: float
    topology_breaks: int
    phases: Dict[str, int]

    @property
    def allow_ratio(self) -> float:
        return self.allow_count / max(1, self.total)

    @property
    def deny_ratio(self) -> float:
        return self.deny_count / max(1, self.total)

    @property
    def is_clean(self) -> bool:
        """No denials and no topology breaks."""
        return self.deny_count == 0 and self.topology_breaks == 0


def summarize_governance(results: List[CrossingResult]) -> GovernanceSummary:
    """Produce a governance summary from a sequence of crossing evaluations."""
    if not results:
        return GovernanceSummary(
            total=0,
            allow_count=0,
            quarantine_count=0,
            deny_count=0,
            mean_energy=0,
            max_energy=0,
            mean_cost=0,
            max_cost=0,
            topology_breaks=0,
            phases={},
        )

    phases: Dict[str, int] = {}
    for r in results:
        phases[r.phase] = phases.get(r.phase, 0) + 1

    energies = [r.energy for r in results]
    costs = [r.harmonic_cost for r in results]

    return GovernanceSummary(
        total=len(results),
        allow_count=sum(1 for r in results if r.decision == Decision.ALLOW),
        quarantine_count=sum(1 for r in results if r.decision == Decision.QUARANTINE),
        deny_count=sum(1 for r in results if r.decision == Decision.DENY),
        mean_energy=sum(energies) / len(energies),
        max_energy=max(energies),
        mean_cost=sum(costs) / len(costs),
        max_cost=max(costs),
        topology_breaks=sum(1 for r in results if not r.topology_valid),
        phases=phases,
    )
