"""
Hamiltonian Braid — Ternary Spiral Governance (Mirror-Shift-Refactor Algebra).

Upgrades the Hamiltonian Path (1D rail) into a Hamiltonian Braid (3D trust tube)
using the Dual Ternary algebra {-1, 0, +1}².

Generators:
    M      — Mirror swap:    (a, b) ↔ (b, a)
    S(φ)   — Mirror shift:   Symmetric rotation toward/from diagonal
    Π      — Refactor align: Project onto valid manifold (trust tube surface)
    0      — Zero gravity:   Fixed-point attractor

Relations:
    M² = I                    (Mirror is involution)
    S(0) = I                  (No shift = identity)
    S(π/4) · M = M · S(π/4)  (Diagonal is M-invariant)
    Π² = Π                    (Projection is idempotent)
    M · 0 = 0                (Zero is M-invariant)

Property: iterated MSR cycles converge to φ-dimensional attractors.
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

PHI = (1 + math.sqrt(5)) / 2


# ═══════════════════════════════════════════════════════════════
# Braid State Types
# ═══════════════════════════════════════════════════════════════


class BraidState(Enum):
    """The 9 discrete governance states of the Hamiltonian Braid."""
    RESONANT_LOCK = "resonant_lock"           # (+1, +1)
    FORWARD_THRUST = "forward_thrust"         # (+1,  0)
    CREATIVE_TENSION_A = "creative_tension_a" # (+1, -1)
    PERPENDICULAR_POS = "perpendicular_pos"   # ( 0, +1)
    ZERO_GRAVITY = "zero_gravity"             # ( 0,  0)
    PERPENDICULAR_NEG = "perpendicular_neg"   # ( 0, -1)
    CREATIVE_TENSION_B = "creative_tension_b" # (-1, +1)
    BACKWARD_CHECK = "backward_check"         # (-1,  0)
    COLLAPSE_ATTRACTOR = "collapse_attractor" # (-1, -1)


class TrustLevel(Enum):
    """Trust level associated with each braid state."""
    MAXIMUM = "maximum"
    HIGH = "high"
    MEDIUM = "medium"
    CONSENSUS = "consensus"
    LOW = "low"
    AUDIT = "audit"
    BLOCK = "block"


class SecurityAction(Enum):
    """Security action prescribed by each braid state."""
    INSTANT_APPROVE = "instant_approve"
    STANDARD_PATH = "standard_path"
    FRACTAL_INSPECT = "fractal_inspect"
    HOLD_QUORUM = "hold_quorum"
    REANCHOR = "reanchor"
    ROLLBACK = "rollback"
    HARD_DENY = "hard_deny"


@dataclass(frozen=True)
class BraidGovernance:
    """Complete governance descriptor for a braid state."""
    state: BraidState
    primary: int
    mirror: int
    trust_level: TrustLevel
    action: SecurityAction


@dataclass(frozen=True)
class BraidCycleResult:
    """Result of a braid cycle iteration."""
    final_vector: Tuple[float, float]
    governance: BraidGovernance
    trajectory: List[Tuple[float, float]]
    fractal_dimension: float
    steps_to_converge: int
    equilibrium_distance: float


@dataclass
class BraidConfig:
    """Configuration for the Hamiltonian Braid system."""
    tube_radius: float = 0.15
    quantize_threshold: float = 0.33
    max_iterations: int = 500
    convergence_threshold: float = 0.01
    shift_scale: float = 0.1
    refactor_trigger: float = 3.0
    lambda_: float = 0.5  # Phase deviation weight in d_braid


# ═══════════════════════════════════════════════════════════════
# Governance Mapping
# ═══════════════════════════════════════════════════════════════


def classify_braid_state(primary: int, mirror: int) -> BraidState:
    """Map dual ternary pair to braid state."""
    mapping = {
        (1, 1): BraidState.RESONANT_LOCK,
        (1, 0): BraidState.FORWARD_THRUST,
        (1, -1): BraidState.CREATIVE_TENSION_A,
        (0, 1): BraidState.PERPENDICULAR_POS,
        (0, 0): BraidState.ZERO_GRAVITY,
        (0, -1): BraidState.PERPENDICULAR_NEG,
        (-1, 1): BraidState.CREATIVE_TENSION_B,
        (-1, 0): BraidState.BACKWARD_CHECK,
        (-1, -1): BraidState.COLLAPSE_ATTRACTOR,
    }
    return mapping.get((primary, mirror), BraidState.COLLAPSE_ATTRACTOR)


_TRUST_MAP = {
    BraidState.RESONANT_LOCK: TrustLevel.MAXIMUM,
    BraidState.FORWARD_THRUST: TrustLevel.HIGH,
    BraidState.CREATIVE_TENSION_A: TrustLevel.MEDIUM,
    BraidState.PERPENDICULAR_POS: TrustLevel.LOW,
    BraidState.ZERO_GRAVITY: TrustLevel.CONSENSUS,
    BraidState.PERPENDICULAR_NEG: TrustLevel.LOW,
    BraidState.CREATIVE_TENSION_B: TrustLevel.MEDIUM,
    BraidState.BACKWARD_CHECK: TrustLevel.AUDIT,
    BraidState.COLLAPSE_ATTRACTOR: TrustLevel.BLOCK,
}

_ACTION_MAP = {
    BraidState.RESONANT_LOCK: SecurityAction.INSTANT_APPROVE,
    BraidState.FORWARD_THRUST: SecurityAction.STANDARD_PATH,
    BraidState.CREATIVE_TENSION_A: SecurityAction.FRACTAL_INSPECT,
    BraidState.PERPENDICULAR_POS: SecurityAction.REANCHOR,
    BraidState.ZERO_GRAVITY: SecurityAction.HOLD_QUORUM,
    BraidState.PERPENDICULAR_NEG: SecurityAction.REANCHOR,
    BraidState.CREATIVE_TENSION_B: SecurityAction.FRACTAL_INSPECT,
    BraidState.BACKWARD_CHECK: SecurityAction.ROLLBACK,
    BraidState.COLLAPSE_ATTRACTOR: SecurityAction.HARD_DENY,
}


def braid_trust_level(state: BraidState) -> TrustLevel:
    """Map braid state to trust level."""
    return _TRUST_MAP[state]


def braid_security_action(state: BraidState) -> SecurityAction:
    """Map braid state to security action."""
    return _ACTION_MAP[state]


def build_governance(primary: int, mirror: int) -> BraidGovernance:
    """Build the full governance descriptor."""
    state = classify_braid_state(primary, mirror)
    return BraidGovernance(
        state=state,
        primary=primary,
        mirror=mirror,
        trust_level=braid_trust_level(state),
        action=braid_security_action(state),
    )


# ═══════════════════════════════════════════════════════════════
# Algebra Generators
# ═══════════════════════════════════════════════════════════════


def mirror_swap(v: Tuple[float, float]) -> Tuple[float, float]:
    """Generator M: (a, b) → (b, a). M² = I."""
    return (v[1], v[0])


def mirror_shift(v: Tuple[float, float], phi: float) -> Tuple[float, float]:
    """Generator S(φ): Symmetric rotation. S(0) = I."""
    c = math.cos(phi)
    s = math.sin(phi)
    return (v[0] * c + v[1] * s, v[0] * s + v[1] * c)


def refactor_align(v: Tuple[float, float]) -> Tuple[float, float]:
    """Generator Π: Project onto mirror diagonal. Π² = Π."""
    sqrt2_inv = 1.0 / math.sqrt(2)
    dot = v[0] * sqrt2_inv + v[1] * sqrt2_inv
    px = dot * sqrt2_inv
    py = dot * sqrt2_inv
    norm = math.sqrt(px * px + py * py)
    if norm > 1.0:
        px /= norm
        py /= norm
    return (px, py)


def zero_gravity_distance(v: Tuple[float, float]) -> float:
    """Distance from the zero-gravity equilibrium (0, 0)."""
    return math.sqrt(v[0] * v[0] + v[1] * v[1])


# ═══════════════════════════════════════════════════════════════
# Quantization
# ═══════════════════════════════════════════════════════════════


def quantize(x: float, threshold: float = 0.33) -> int:
    """Quantize a continuous value to ternary {-1, 0, +1}."""
    if x > threshold:
        return 1
    if x < -threshold:
        return -1
    return 0


def quantize_vector(
    v: Tuple[float, float], threshold: float = 0.33
) -> Tuple[int, int]:
    """Quantize a 2D vector to dual ternary."""
    return (quantize(v[0], threshold), quantize(v[1], threshold))


# ═══════════════════════════════════════════════════════════════
# Harmonic Tube
# ═══════════════════════════════════════════════════════════════


def harmonic_tube_cost(distance: float, tube_radius: float) -> float:
    """Compute Harmonic Wall energy: φ^(d²) outside tube, 0 inside."""
    if distance <= tube_radius:
        return 0.0
    excess = distance - tube_radius
    return PHI ** (excess * excess)


def is_inside_tube(v: Tuple[float, float], tube_radius: float) -> bool:
    """Check whether a vector is inside the trust tube."""
    return zero_gravity_distance(v) <= tube_radius


BRAIN_EPSILON = 1e-10
POINCARE_MAX_NORM = 1 - 1e-8


# ═══════════════════════════════════════════════════════════════
# Hyperbolic Distance (2D Poincaré Disk)
# ═══════════════════════════════════════════════════════════════


def hyperbolic_distance_2d(
    u: Tuple[float, float], v: Tuple[float, float]
) -> float:
    """Hyperbolic distance in the 2D Poincaré disk."""
    dx, dy = u[0] - v[0], u[1] - v[1]
    diff_sq = dx * dx + dy * dy
    u_sq = u[0] * u[0] + u[1] * u[1]
    v_sq = v[0] * v[0] + v[1] * v[1]
    u_factor = max(BRAIN_EPSILON, 1 - u_sq)
    v_factor = max(BRAIN_EPSILON, 1 - v_sq)
    arg = 1 + (2 * diff_sq) / (u_factor * v_factor)
    return math.acosh(max(1.0, arg))


# ═══════════════════════════════════════════════════════════════
# Phase Deviation
# ═══════════════════════════════════════════════════════════════


def ternary_center(t: int, threshold: float = 0.33) -> float:
    """Compute the center of a ternary quantization zone."""
    if t == 1:
        return (1 + threshold) / 2
    if t == -1:
        return -(1 + threshold) / 2
    return 0.0


def phase_deviation(
    v: Tuple[float, float], threshold: float = 0.33
) -> float:
    """Phase deviation: distance from quantized state center."""
    qp = quantize(v[0], threshold)
    qm = quantize(v[1], threshold)
    cp = ternary_center(qp, threshold)
    cm = ternary_center(qm, threshold)
    dp, dm = v[0] - cp, v[1] - cm
    return math.sqrt(dp * dp + dm * dm)


# ═══════════════════════════════════════════════════════════════
# Phase-Aware Projection
# ═══════════════════════════════════════════════════════════════


def _phase_range(t: int, threshold: float) -> Tuple[float, float]:
    """Constraint range for a ternary value."""
    if t == 1:
        return (threshold, 1.0)
    if t == -1:
        return (-1.0, -threshold)
    return (-threshold, threshold)


def phase_aware_project(
    v: Tuple[float, float],
    phase: Optional[Tuple[int, int]] = None,
    threshold: float = 0.33,
) -> Tuple[float, float]:
    """Phase-aware projection Π: ℝ² × {-1,0,+1}² → M_constraint."""
    if phase is None:
        phase = quantize_vector(v, threshold)
    x_min, x_max = _phase_range(phase[0], threshold)
    y_min, y_max = _phase_range(phase[1], threshold)
    x = max(x_min, min(x_max, v[0]))
    y = max(y_min, min(y_max, v[1]))
    norm = math.sqrt(x * x + y * y)
    if norm >= POINCARE_MAX_NORM:
        scale = (POINCARE_MAX_NORM - BRAIN_EPSILON) / norm
        x *= scale
        y *= scale
    return (x, y)


# ═══════════════════════════════════════════════════════════════
# Braid Rail Reference Points
# ═══════════════════════════════════════════════════════════════


def compute_rail_centers(
    threshold: float = 0.33,
) -> List[Tuple[float, float]]:
    """Compute the 9 rail center points in continuous space."""
    centers = []
    for p in [1, 0, -1]:
        for m in [1, 0, -1]:
            centers.append((ternary_center(p, threshold), ternary_center(m, threshold)))
    return centers


BRAID_RAIL_CENTERS = compute_rail_centers(0.33)


# ═══════════════════════════════════════════════════════════════
# d_braid Distance
# ═══════════════════════════════════════════════════════════════


def d_braid(
    v: Tuple[float, float],
    lambda_: float = 0.5,
    threshold: float = 0.33,
    rail: Optional[List[Tuple[float, float]]] = None,
) -> float:
    """d_braid(x, rail) = min_{r∈Rail} d_H(Π(x), r) + λ·|phase_deviation|."""
    if rail is None:
        rail = BRAID_RAIL_CENTERS
    projected = phase_aware_project(v, None, threshold)
    phase_dev = phase_deviation(v, threshold)
    min_dist = float("inf")
    for r in rail:
        r_norm = math.sqrt(r[0] * r[0] + r[1] * r[1])
        if r_norm >= POINCARE_MAX_NORM:
            s = (POINCARE_MAX_NORM - BRAIN_EPSILON) / r_norm
            r_safe = (r[0] * s, r[1] * s)
        else:
            r_safe = r
        d = hyperbolic_distance_2d(projected, r_safe)
        if d < min_dist:
            min_dist = d
    return min_dist + lambda_ * phase_dev


# ═══════════════════════════════════════════════════════════════
# Braid Transition Validation
# ═══════════════════════════════════════════════════════════════


def is_valid_braid_transition(
    from_state: Tuple[int, int], to_state: Tuple[int, int]
) -> bool:
    """Check whether a transition is topologically valid (Chebyshev ≤ 1)."""
    return abs(from_state[0] - to_state[0]) <= 1 and abs(from_state[1] - to_state[1]) <= 1


def braid_state_distance(
    from_state: Tuple[int, int], to_state: Tuple[int, int]
) -> int:
    """Chebyshev distance in the 3×3 ternary grid."""
    return max(abs(from_state[0] - to_state[0]), abs(from_state[1] - to_state[1]))


# ═══════════════════════════════════════════════════════════════
# Fractal Dimension
# ═══════════════════════════════════════════════════════════════


def estimate_braid_fractal_dimension(
    trajectory: List[Tuple[float, float]],
    scales: Optional[List[float]] = None,
) -> float:
    """Box-counting fractal dimension of a 2D trajectory."""
    if len(trajectory) < 2:
        return 0.0

    if scales is None:
        scales = [0.2, 0.1, 0.05, 0.025]

    counts = []
    for scale in scales:
        boxes = set()
        for p in trajectory:
            bx = int(p[0] // scale) if scale > 0 else 0
            by = int(p[1] // scale) if scale > 0 else 0
            boxes.add((bx, by))
        counts.append((scale, len(boxes)))

    log_eps = [math.log(1.0 / c[0]) for c in counts]
    log_n = [math.log(c[1]) if c[1] > 0 else 0 for c in counts]

    n = len(log_eps)
    sum_x = sum(log_eps)
    sum_y = sum(log_n)
    sum_xy = sum(x * y for x, y in zip(log_eps, log_n))
    sum_x2 = sum(x * x for x in log_eps)

    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-10:
        return 1.0

    return (n * sum_xy - sum_x * sum_y) / denom


# ═══════════════════════════════════════════════════════════════
# AetherBraid System
# ═══════════════════════════════════════════════════════════════


class AetherBraid:
    """
    The Hamiltonian Braid — ternary spiral governance system.

    Replaces the single 1D Hamiltonian rail with a 3D trust tube.
    The AI can spiral around the central axis (exploring options)
    as long as the net momentum stays within the tube boundaries.
    """

    def __init__(self, config: Optional[BraidConfig] = None):
        self.config = config or BraidConfig()

    def classify(self, v: Tuple[float, float]) -> BraidGovernance:
        """Classify a continuous 2D vector to its governance state."""
        p, m = quantize_vector(v, self.config.quantize_threshold)
        return build_governance(p, m)

    def evaluate(
        self,
        primary_vector: Tuple[float, float],
        orthogonal_vector: Tuple[float, float],
    ) -> dict:
        """Evaluate a trajectory pair (forward + perpendicular check)."""
        coherence = (
            primary_vector[0] * orthogonal_vector[0]
            + primary_vector[1] * orthogonal_vector[1]
        )
        combined = (
            (primary_vector[0] + orthogonal_vector[0]) / 2,
            (primary_vector[1] + orthogonal_vector[1]) / 2,
        )
        dist = zero_gravity_distance(combined)
        cost = harmonic_tube_cost(dist, self.config.tube_radius)
        inside = dist <= self.config.tube_radius
        governance = self.classify(combined)

        return {
            "governance": governance,
            "coherence": coherence,
            "distance_from_center": dist,
            "tube_cost": cost,
            "inside_tube": inside,
        }

    def iterate_cycle(
        self,
        initial: Tuple[float, float],
        max_steps: Optional[int] = None,
    ) -> BraidCycleResult:
        """Run the Mirror-Shift-Refactor cycle."""
        steps = max_steps or self.config.max_iterations
        trajectory: List[Tuple[float, float]] = [initial]
        v = initial
        converged_at = steps

        for i in range(steps):
            phi = (i * PHI) % (math.pi / 2)
            v = mirror_shift(v, phi * self.config.shift_scale)

            dist = zero_gravity_distance(v)
            if dist < self.config.convergence_threshold:
                converged_at = i + 1
                trajectory.append(v)
                break

            if dist > self.config.tube_radius * self.config.refactor_trigger:
                v = refactor_align(v)

            trajectory.append(v)

        fractal_dim = estimate_braid_fractal_dimension(trajectory)
        governance = self.classify(v)
        eq_dist = zero_gravity_distance(v)

        return BraidCycleResult(
            final_vector=v,
            governance=governance,
            trajectory=trajectory,
            fractal_dimension=fractal_dim,
            steps_to_converge=converged_at,
            equilibrium_distance=eq_dist,
        )

    def compute_tube_cost(self, v: Tuple[float, float]) -> float:
        """Compute the Harmonic Wall energy for a given vector."""
        return harmonic_tube_cost(zero_gravity_distance(v), self.config.tube_radius)

    def compute_d_braid(
        self,
        v: Tuple[float, float],
        rail: Optional[List[Tuple[float, float]]] = None,
    ) -> float:
        """Compute the refined d_braid distance using instance config."""
        r = rail if rail is not None else compute_rail_centers(self.config.quantize_threshold)
        return d_braid(v, self.config.lambda_, self.config.quantize_threshold, r)

    def project(
        self,
        v: Tuple[float, float],
        phase: Optional[Tuple[int, int]] = None,
    ) -> Tuple[float, float]:
        """Phase-aware projection using instance threshold."""
        return phase_aware_project(v, phase, self.config.quantize_threshold)

    def is_valid_transition(
        self,
        from_v: Tuple[float, float],
        to_v: Tuple[float, float],
    ) -> bool:
        """Check if a governance transition is topologically valid."""
        q_from = quantize_vector(from_v, self.config.quantize_threshold)
        q_to = quantize_vector(to_v, self.config.quantize_threshold)
        return is_valid_braid_transition(q_from, q_to)


# ═══════════════════════════════════════════════════════════════
# Governance Table (all 9 states)
# ═══════════════════════════════════════════════════════════════

BRAID_GOVERNANCE_TABLE = [
    build_governance(p, m)
    for p in [1, 0, -1]
    for m in [1, 0, -1]
]
