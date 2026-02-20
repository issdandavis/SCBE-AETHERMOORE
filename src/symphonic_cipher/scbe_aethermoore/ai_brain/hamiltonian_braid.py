"""
Hamiltonian Braid Dynamics

@file hamiltonian_braid.py
@module ai_brain/hamiltonian_braid
@layer Layer 5, Layer 8, Layer 12, Layer 13
@component Braid-constrained orbit dynamics on the 21D manifold
@version 1.0.0

Formalizes the shift from brittle path-following to robust orbit dynamics.

Core objects:
  1. 9-state phase diagram: dual ternary {-1,0,+1}² phase space
  2. Braid distance: d_braid = d_H(Π(x), r) + λ·|phase_deviation|
  3. Harmonic cost: C(d) = φ^(d²) — exponential for deviation from rail
  4. Constraint manifold projection: Π: R^21 × {-1,0,+1}² → M_constraint
  5. Rail family: sequence of waypoints defining valid trajectories

The cost function makes deviation geometrically meaningful:
  - You pay exponentially for spatial deviation (hyperbolic distance)
  - You pay exponentially for phase incoherence (discrete state mismatch)
  - Near the rail center: cost ≈ 1 (safe)
  - At the Poincaré boundary: cost → ∞ (impossible)

The projection target M_constraint is the 2D manifold embedded in 21D
where the discrete phase is consistent with continuous position AND
the braid topology is preserved (no impossible transitions).

Integration:
  - fsgs.py: FSGS symbols drive the impulse; braid constrains which
    transitions are topologically valid
  - governance_adapter.py: combined score feeds the harmonic cost
  - mirror_shift.py: dual ternary channels are the braid strands
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .unified_state import (
    BRAIN_DIMENSIONS,
    PHI,
    UnifiedBrainState,
    safe_poincare_embed,
    hyperbolic_distance_safe,
)
from .mirror_shift import (
    PARALLEL_DIMS,
    PERP_DIMS,
    refactor_align,
    AlignmentResult,
)

EPS = 1e-12


# ---------------------------------------------------------------------------
# 9-state phase diagram
# ---------------------------------------------------------------------------

# All 9 dual ternary phase states: (parallel_trit, perp_trit)
PHASE_STATES: List[Tuple[int, int]] = [
    (p, q) for p in (-1, 0, 1) for q in (-1, 0, 1)
]

# Phase state labels for readability
PHASE_LABELS: Dict[Tuple[int, int], str] = {
    (-1, -1): "retreat-contract",    # both channels pulling back
    (-1,  0): "retreat-hold",        # parallel retreats, perp holds
    (-1,  1): "retreat-advance",     # parallel retreats, perp advances
    ( 0, -1): "hold-contract",       # parallel holds, perp contracts
    ( 0,  0): "equilibrium",         # both channels neutral
    ( 0,  1): "hold-advance",        # parallel holds, perp advances
    ( 1, -1): "advance-contract",    # parallel advances, perp contracts
    ( 1,  0): "advance-hold",        # parallel advances, perp holds
    ( 1,  1): "advance-advance",     # both channels advancing
}


def phase_label(state: Tuple[int, int]) -> str:
    """Get human-readable label for a phase state."""
    return PHASE_LABELS.get(state, f"unknown({state[0]},{state[1]})")


def valid_transition(
    s1: Tuple[int, int],
    s2: Tuple[int, int],
) -> bool:
    """Check if transition preserves braid topology.

    Valid transitions have Chebyshev distance ≤ 1 in the phase grid.
    This means each trit can change by at most 1 step per timestep,
    preventing "impossible" jumps that break the braid ordering.

    Args:
        s1: Source phase state (p, q).
        s2: Target phase state (p, q).

    Returns:
        True if the transition is topologically valid.
    """
    dp = abs(s1[0] - s2[0])
    dq = abs(s1[1] - s2[1])
    return dp <= 1 and dq <= 1


def valid_neighbors(state: Tuple[int, int]) -> List[Tuple[int, int]]:
    """Get all valid next phase states (including staying)."""
    return [s for s in PHASE_STATES if valid_transition(state, s)]


def transition_matrix() -> np.ndarray:
    """Build the 9×9 adjacency matrix of valid phase transitions.

    M[i,j] = 1 if PHASE_STATES[i] → PHASE_STATES[j] is valid.
    """
    n = len(PHASE_STATES)
    M = np.zeros((n, n), dtype=int)
    for i, s1 in enumerate(PHASE_STATES):
        for j, s2 in enumerate(PHASE_STATES):
            if valid_transition(s1, s2):
                M[i, j] = 1
    return M


def phase_deviation(
    current: Tuple[int, int],
    expected: Tuple[int, int],
) -> float:
    """Compute phase deviation between current and expected state.

    Uses the Chebyshev distance in the {-1,0,+1}² grid,
    normalized to [0, 1].

    Args:
        current: Current phase state.
        expected: Expected phase state for this rail position.

    Returns:
        Phase deviation in [0, 1]. 0 = perfect match, 1 = maximum deviation.
    """
    dp = abs(current[0] - expected[0])
    dq = abs(current[1] - expected[1])
    # Max possible Chebyshev distance in {-1,0,+1}² is 2
    return max(dp, dq) / 2.0


# ---------------------------------------------------------------------------
# Rail family R
# ---------------------------------------------------------------------------

@dataclass
class RailPoint:
    """A single waypoint on the governance rail.

    Each rail point has a position in 21D space AND an expected
    phase state — the "natural" discrete configuration for that
    position on the rail.
    """
    position: np.ndarray          # 21D position
    expected_phase: Tuple[int, int]  # expected (par_trit, perp_trit)
    index: int = 0                # position along the rail


@dataclass
class Rail:
    """A rail is an ordered sequence of waypoints through 21D space.

    The rail defines the "trust tube" center line. States near the
    rail are safe; states far from it pay exponential cost.
    """
    points: List[RailPoint]

    def __len__(self) -> int:
        return len(self.points)

    def positions_array(self) -> np.ndarray:
        """Stack all positions into (N, 21) array."""
        return np.array([p.position for p in self.points])


def make_rail_from_trajectory(
    trajectory: np.ndarray,
    phases: Optional[List[Tuple[int, int]]] = None,
) -> Rail:
    """Construct a Rail from a trajectory and optional phase assignments.

    Args:
        trajectory: (N, 21) array of waypoints.
        phases: Phase state per waypoint. Default: all equilibrium.

    Returns:
        Rail with N waypoints.
    """
    trajectory = np.asarray(trajectory, dtype=float)
    if trajectory.ndim != 2 or trajectory.shape[1] != BRAIN_DIMENSIONS:
        raise ValueError(
            f"Expected (N, {BRAIN_DIMENSIONS}) trajectory, "
            f"got shape {trajectory.shape}."
        )

    n = len(trajectory)
    if phases is None:
        phases = [(0, 0)] * n
    if len(phases) != n:
        raise ValueError(
            f"phases length {len(phases)} != trajectory length {n}."
        )

    points = [
        RailPoint(position=trajectory[i], expected_phase=phases[i], index=i)
        for i in range(n)
    ]
    return Rail(points=points)


def nearest_rail_point(
    x: np.ndarray,
    rail: Rail,
) -> Tuple[RailPoint, float]:
    """Find the nearest rail point to a given state.

    Uses Euclidean distance in 21D for nearest-neighbor lookup.

    Args:
        x: Current 21D state.
        rail: Rail to project onto.

    Returns:
        (nearest_point, euclidean_distance).
    """
    x = np.asarray(x, dtype=float)
    best_point = rail.points[0]
    best_dist = float("inf")
    for point in rail.points:
        d = float(np.linalg.norm(x - point.position))
        if d < best_dist:
            best_dist = d
            best_point = point
    return best_point, best_dist


# ---------------------------------------------------------------------------
# Braid distance
# ---------------------------------------------------------------------------

def braid_distance(
    x: np.ndarray,
    rail: Rail,
    current_phase: Tuple[int, int],
    lambda_phase: float = 0.5,
) -> Tuple[float, RailPoint]:
    """Compute braid-specific hyperbolic distance.

    d_braid(x, rail) = d_H(embed(x), embed(r*)) + λ·phase_deviation

    Where r* is the nearest rail point and d_H is the hyperbolic
    distance in the Poincaré ball.

    Args:
        x: Current 21D state.
        rail: Rail family.
        current_phase: Current dual ternary phase state.
        lambda_phase: Weight for phase deviation component.

    Returns:
        (braid_distance, nearest_rail_point).
    """
    # Find nearest rail point
    nearest, _ = nearest_rail_point(x, rail)

    # Hyperbolic distance in Poincaré ball
    x_embedded = safe_poincare_embed(x.tolist())
    r_embedded = safe_poincare_embed(nearest.position.tolist())
    d_H = hyperbolic_distance_safe(x_embedded, r_embedded)

    # Phase deviation
    p_dev = phase_deviation(current_phase, nearest.expected_phase)

    return d_H + lambda_phase * p_dev, nearest


# ---------------------------------------------------------------------------
# Harmonic cost: φ^(d²)
# ---------------------------------------------------------------------------

def harmonic_cost(d: float) -> float:
    """Compute the harmonic wall cost: C(d) = φ^(d²).

    This is the core innovation: adversarial deviation costs exponentially
    more the further it drifts from the rail.

    - d ≈ 0: cost ≈ 1 (safe, near rail center)
    - d = 1: cost = φ ≈ 1.618
    - d = 2: cost = φ⁴ ≈ 6.854
    - d = 3: cost = φ⁹ ≈ 76.01
    - d → ∞: cost → ∞ (computationally infeasible)

    Args:
        d: Braid distance from rail.

    Returns:
        Cost value ≥ 1.
    """
    return PHI ** (d * d)


def harmonic_cost_gradient(d: float) -> float:
    """Gradient of the harmonic cost: dC/dd = 2d · ln(φ) · φ^(d²).

    Used for computing the restoring force toward the rail.

    Args:
        d: Braid distance.

    Returns:
        Cost gradient (always positive for d > 0).
    """
    if abs(d) < EPS:
        return 0.0
    return 2.0 * d * math.log(PHI) * harmonic_cost(d)


# ---------------------------------------------------------------------------
# Constraint manifold projection
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConstraintProjection:
    """Result of projecting onto the constraint manifold.

    M_constraint is the submanifold where:
    1. Discrete phase is consistent with continuous position
    2. Braid topology is preserved (valid transitions only)
    3. Hamiltonian structure is maintained (energy conservation)
    """
    projected_state: np.ndarray
    projected_phase: Tuple[int, int]
    nearest_rail: RailPoint
    braid_dist: float
    cost: float
    phase_consistent: bool
    braid_valid: bool
    alignment_corrections: int


def constraint_project(
    x: np.ndarray,
    current_phase: Tuple[int, int],
    rail: Rail,
    prev_phase: Optional[Tuple[int, int]] = None,
    lambda_phase: float = 0.5,
    poincare_max: float = 0.95,
) -> ConstraintProjection:
    """Project (x, phase) onto the constraint manifold M_constraint.

    Π: R^21 × {-1,0,+1}² → M_constraint

    Steps:
    1. Find nearest rail point r*
    2. Check phase consistency with r*'s expected phase
    3. If inconsistent, snap to nearest valid phase
    4. If transition from prev_phase is invalid (braid break),
       snap to nearest valid neighbor
    5. Apply POCS trust tube projection

    Args:
        x: Current 21D state.
        current_phase: Current dual ternary phase.
        rail: Rail family.
        prev_phase: Previous phase (for braid topology check).
        lambda_phase: Phase deviation weight.
        poincare_max: Maximum Poincaré radius.

    Returns:
        ConstraintProjection with projected state, phase, and diagnostics.
    """
    x = np.asarray(x, dtype=float)

    # Step 1: Nearest rail point
    nearest, _ = nearest_rail_point(x, rail)

    # Step 2: Phase consistency
    p_dev = phase_deviation(current_phase, nearest.expected_phase)
    phase_consistent = p_dev < 0.5  # within 1 step of expected

    # Step 3: Snap to nearest valid phase if inconsistent
    projected_phase = current_phase
    if not phase_consistent:
        # Find the valid phase closest to expected
        candidates = valid_neighbors(current_phase) if prev_phase is None else [
            s for s in valid_neighbors(current_phase)
            if prev_phase is None or valid_transition(prev_phase, s)
        ]
        if candidates:
            best = min(
                candidates,
                key=lambda s: phase_deviation(s, nearest.expected_phase),
            )
            projected_phase = best

    # Step 4: Braid topology check
    braid_valid = True
    if prev_phase is not None:
        if not valid_transition(prev_phase, projected_phase):
            braid_valid = False
            # Snap to nearest valid neighbor of prev_phase
            neighbors = valid_neighbors(prev_phase)
            projected_phase = min(
                neighbors,
                key=lambda s: phase_deviation(s, nearest.expected_phase),
            )

    # Step 5: POCS trust tube projection
    align_result = refactor_align(x, poincare_max)
    projected_x = align_result.aligned_state

    # Compute final braid distance and cost
    x_emb = safe_poincare_embed(projected_x.tolist())
    r_emb = safe_poincare_embed(nearest.position.tolist())
    d_H = hyperbolic_distance_safe(x_emb, r_emb)
    d_braid = d_H + lambda_phase * phase_deviation(projected_phase, nearest.expected_phase)
    cost = harmonic_cost(d_braid)

    return ConstraintProjection(
        projected_state=projected_x,
        projected_phase=projected_phase,
        nearest_rail=nearest,
        braid_dist=d_braid,
        cost=cost,
        phase_consistent=phase_consistent,
        braid_valid=braid_valid,
        alignment_corrections=align_result.corrections_applied,
    )


# ---------------------------------------------------------------------------
# Braid step: single dynamics step
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BraidStepResult:
    """Result of a single braid dynamics step."""
    state: np.ndarray
    phase: Tuple[int, int]
    mode: str                     # from FSGS: RUN/HOLD/QUAR/ROLLBACK
    braid_dist: float
    cost: float
    phase_consistent: bool
    braid_valid: bool
    corrections: int
    step: int


def braid_step(
    x: np.ndarray,
    phase: Tuple[int, int],
    rail: Rail,
    impulse: float = 0.0,
    direction: Optional[np.ndarray] = None,
    prev_phase: Optional[Tuple[int, int]] = None,
    lambda_phase: float = 0.5,
    poincare_max: float = 0.95,
    step_num: int = 0,
) -> BraidStepResult:
    """Execute one step of braid-constrained dynamics.

    1. Apply impulse: x' = x + impulse · d(x)
    2. Project onto constraint manifold: (x⁺, phase⁺) = Π(x', phase)
    3. Compute braid distance and harmonic cost

    The FSGS symbol determines the impulse magnitude and sign.
    The braid topology constrains which phase transitions are valid.
    The harmonic cost φ^(d²) penalizes deviation.

    Args:
        x: Current 21D state.
        phase: Current dual ternary phase.
        rail: Rail family.
        impulse: Signed impulse magnitude (from FSGS: m·α·η).
        direction: Impulse direction (default: toward nearest rail point).
        prev_phase: Previous phase for braid topology check.
        lambda_phase: Phase deviation weight.
        poincare_max: Max Poincaré radius.
        step_num: Current step number.

    Returns:
        BraidStepResult with projected state, phase, cost, diagnostics.
    """
    x = np.asarray(x, dtype=float).copy()

    # Default direction: toward nearest rail point
    if direction is None:
        nearest, _ = nearest_rail_point(x, rail)
        diff = nearest.position - x
        norm = np.linalg.norm(diff)
        direction = diff / norm if norm > EPS else np.zeros_like(x)

    # Apply impulse
    x_tentative = x + impulse * direction

    # Project onto constraint manifold
    proj = constraint_project(
        x_tentative, phase, rail,
        prev_phase=prev_phase,
        lambda_phase=lambda_phase,
        poincare_max=poincare_max,
    )

    # Determine mode from cost
    if proj.cost < PHI:
        mode = "RUN"
    elif proj.cost < PHI ** 4:
        mode = "HOLD"
    elif proj.cost < PHI ** 9:
        mode = "QUAR"
    else:
        mode = "ROLLBACK"

    return BraidStepResult(
        state=proj.projected_state,
        phase=proj.projected_phase,
        mode=mode,
        braid_dist=proj.braid_dist,
        cost=proj.cost,
        phase_consistent=proj.phase_consistent,
        braid_valid=proj.braid_valid,
        corrections=proj.alignment_corrections,
        step=step_num,
    )


# ---------------------------------------------------------------------------
# Braid trajectory simulation
# ---------------------------------------------------------------------------

@dataclass
class BraidTrajectory:
    """Full braid-constrained trajectory result."""
    steps: List[BraidStepResult]
    total_cost: float
    max_cost: float
    braid_breaks: int
    phase_inconsistencies: int
    mode_counts: Dict[str, int]


def simulate_braid(
    initial_state: np.ndarray,
    initial_phase: Tuple[int, int],
    rail: Rail,
    impulses: Sequence[float],
    directions: Optional[Sequence[Optional[np.ndarray]]] = None,
    lambda_phase: float = 0.5,
    poincare_max: float = 0.95,
) -> BraidTrajectory:
    """Simulate braid dynamics over a sequence of impulses.

    Args:
        initial_state: Starting 21D state.
        initial_phase: Starting phase state.
        rail: Rail family.
        impulses: Sequence of signed impulse magnitudes.
        directions: Per-step directions (None = toward nearest rail).
        lambda_phase: Phase deviation weight.
        poincare_max: Max Poincaré radius.

    Returns:
        BraidTrajectory with all steps and summary statistics.
    """
    x = np.asarray(initial_state, dtype=float).copy()
    phase = initial_phase
    prev_phase: Optional[Tuple[int, int]] = None

    steps = []
    total_cost = 0.0
    max_cost = 0.0
    braid_breaks = 0
    phase_inconsistencies = 0
    mode_counts: Dict[str, int] = {"RUN": 0, "HOLD": 0, "QUAR": 0, "ROLLBACK": 0}

    for i, imp in enumerate(impulses):
        d = directions[i] if directions else None
        result = braid_step(
            x, phase, rail,
            impulse=imp,
            direction=d,
            prev_phase=prev_phase,
            lambda_phase=lambda_phase,
            poincare_max=poincare_max,
            step_num=i,
        )
        steps.append(result)
        total_cost += result.cost
        max_cost = max(max_cost, result.cost)
        if not result.braid_valid:
            braid_breaks += 1
        if not result.phase_consistent:
            phase_inconsistencies += 1
        mode_counts[result.mode] += 1

        # Advance state
        prev_phase = phase
        x = result.state
        phase = result.phase

    return BraidTrajectory(
        steps=steps,
        total_cost=total_cost,
        max_cost=max_cost,
        braid_breaks=braid_breaks,
        phase_inconsistencies=phase_inconsistencies,
        mode_counts=mode_counts,
    )
