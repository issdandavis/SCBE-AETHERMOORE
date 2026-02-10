"""
Tri-Manifold Lattice — Temporal Harmonic Governance (Python Reference)
=====================================================================

Three temporal manifolds over the Poincaré ball with harmonic scaling
H(d, R) = R^(d²) for super-exponential cost amplification.

Components:
  - TemporalWindow: Sliding window for hyperbolic distance averaging
  - harmonicScale: H(d, R) = R^(d²) — super-exponential amplification
  - triadicDistance: Weighted Euclidean norm of 3 manifold distances
  - TriManifoldLattice: Full lattice manager with resonance/anomaly detection

Mathematical Properties:
  - d_tri ≥ 0 (non-negativity)
  - d_tri = 0 ⟺ d₁ = d₂ = d_G = 0 (positive-definiteness)
  - ∂d_tri/∂dᵢ = λᵢ·dᵢ / d_tri ≥ 0 (monotonicity)
  - H(d, R) × H(d, 1/R) = 1 (duality / phase cancellation)
  - H grows super-exponentially: faster than any single exponential

@module ai_brain/tri_manifold_lattice
@layer Layer 5, Layer 11, Layer 12, Layer 14
@version 1.0.0
"""

import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Import from sibling modules
from .unified_state import (
    BRAIN_DIMENSIONS,
    BRAIN_EPSILON,
    PHI,
    hyperbolic_distance_safe,
    safe_poincare_embed,
    _vec_norm as vector_norm,
)

# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════

HARMONIC_R = 1.5
"""Default harmonic ratio: perfect fifth (3:2) from Pythagorean tuning."""

DEFAULT_WINDOW_IMMEDIATE = 5
DEFAULT_WINDOW_MEMORY = 25
DEFAULT_WINDOW_GOVERNANCE = 100

MAX_LATTICE_DEPTH = 1000


@dataclass
class TriadicWeights:
    """Weights for the triadic distance (must sum to 1)."""

    immediate: float = 0.5
    memory: float = 0.3
    governance: float = 0.2

    def normalized(self) -> "TriadicWeights":
        """Return normalized copy that sums to 1."""
        s = self.immediate + self.memory + self.governance
        if s <= 0:
            return TriadicWeights(1 / 3, 1 / 3, 1 / 3)
        return TriadicWeights(self.immediate / s, self.memory / s, self.governance / s)


@dataclass
class LatticeNode:
    """A single lattice node capturing the full tri-manifold state."""

    tick: int
    raw_state: List[float]
    embedded: List[float]
    hyperbolic_dist: float
    manifold_distances: Dict[str, float]
    triadic_distance: float
    harmonic_cost: float
    embedded_norm: float
    timestamp: float


@dataclass
class LatticeSnapshot:
    """Tri-manifold lattice snapshot for external consumption."""

    tick: int
    triadic_distance: float
    harmonic_cost: float
    manifold_distances: Dict[str, float]
    weights: TriadicWeights
    node_count: int
    drift_velocity: float


# ═══════════════════════════════════════════════════════════════
# Harmonic Scaling Law
# ═══════════════════════════════════════════════════════════════


def harmonic_scale(d: int, R: float = HARMONIC_R) -> float:
    """Harmonic Scaling: H(d, R) = R^(d²).

    Super-exponential amplification where each dimension multiplies
    complexity via pairwise interactions (d² exponent).

    Args:
        d: Number of dimensions (typically 1-6).
        R: Harmonic ratio (default: 1.5, the perfect fifth).

    Returns:
        R^(d²) — the amplification factor.
    """
    if d < 0:
        return 1.0
    if R <= 0:
        return 0.0
    return R ** (d * d)


def harmonic_scale_inverse(d: int, R: float = HARMONIC_R) -> float:
    """Inverse harmonic scaling: H(d, 1/R) = (1/R)^(d²).

    Property: harmonic_scale(d, R) * harmonic_scale_inverse(d, R) = 1
    """
    if d < 0 or R <= 0:
        return 1.0
    return (1.0 / R) ** (d * d)


def harmonic_scale_table(
    max_d: int, R: float = HARMONIC_R
) -> List[Dict[str, float]]:
    """Harmonic scaling table for dimensions 1..max_d."""
    table = []
    for d in range(1, max_d + 1):
        s = harmonic_scale(d, R)
        table.append({"d": d, "scale": s, "log_scale": math.log(s) if s > 0 else 0})
    return table


# ═══════════════════════════════════════════════════════════════
# Triadic Distance
# ═══════════════════════════════════════════════════════════════


def triadic_distance(
    d1: float,
    d2: float,
    d_g: float,
    weights: Optional[TriadicWeights] = None,
) -> float:
    """Triadic temporal distance: weighted Euclidean norm of 3 manifold distances.

    d_tri = √(λ₁·d₁² + λ₂·d₂² + λ₃·d_G²)

    Args:
        d1: Immediate manifold distance.
        d2: Memory manifold distance.
        d_g: Governance manifold distance.
        weights: Triadic weights (must sum to 1).

    Returns:
        Combined triadic distance (non-negative).
    """
    if weights is None:
        weights = TriadicWeights()
    sum_sq = weights.immediate * d1 * d1 + weights.memory * d2 * d2 + weights.governance * d_g * d_g
    return math.sqrt(max(0.0, sum_sq))


def triadic_partial(d_i: float, lambda_i: float, d_tri: float) -> float:
    """Partial derivative of triadic distance w.r.t. component i.

    ∂d_tri/∂dᵢ = λᵢ·dᵢ / d_tri
    """
    if d_tri < BRAIN_EPSILON:
        return 0.0
    return (lambda_i * d_i) / d_tri


# ═══════════════════════════════════════════════════════════════
# Temporal Window
# ═══════════════════════════════════════════════════════════════


class TemporalWindow:
    """Sliding window for temporal manifold distance averaging.

    Maintains a fixed-size circular buffer of hyperbolic distances
    and provides the windowed average d_k(t) = (1/W_k) Σ d_H(u(s), ℓ).
    """

    def __init__(self, size: int):
        if size < 1:
            raise ValueError("Window size must be >= 1")
        self.size = size
        self._buffer: deque = deque(maxlen=size)
        self._sum: float = 0.0

    def push(self, distance: float) -> None:
        """Push a new distance sample into the window."""
        if len(self._buffer) >= self.size:
            self._sum -= self._buffer[0]
        self._buffer.append(distance)
        self._sum += distance

    def average(self) -> float:
        """Windowed average distance."""
        if len(self._buffer) == 0:
            return 0.0
        return self._sum / len(self._buffer)

    def filled(self) -> int:
        """Current sample count."""
        return len(self._buffer)

    def is_warmed_up(self) -> bool:
        """Whether the window is fully warmed up."""
        return len(self._buffer) >= self.size

    def latest(self) -> float:
        """Most recent distance sample."""
        if len(self._buffer) == 0:
            return 0.0
        return self._buffer[-1]

    def variance(self) -> float:
        """Variance of distances in the window."""
        n = len(self._buffer)
        if n < 2:
            return 0.0
        avg = self.average()
        return sum((x - avg) ** 2 for x in self._buffer) / (n - 1)

    def reset(self) -> None:
        """Reset window to empty state."""
        self._buffer.clear()
        self._sum = 0.0


# ═══════════════════════════════════════════════════════════════
# Tri-Manifold Lattice
# ═══════════════════════════════════════════════════════════════


class TriManifoldLattice:
    """Tri-Manifold Lattice: three temporal manifolds over the Poincaré ball.

    Each manifold samples hyperbolic distance at a different timescale,
    then the triadic distance combines them into a single governance metric.
    The harmonic scaling law amplifies this across dimensional space.

    Usage:
        lattice = TriManifoldLattice()
        node = lattice.ingest(state_vector)
        print(node.triadic_distance)   # Combined temporal distance
        print(node.harmonic_cost)      # Super-exponential governance cost
    """

    def __init__(
        self,
        *,
        window_immediate: int = DEFAULT_WINDOW_IMMEDIATE,
        window_memory: int = DEFAULT_WINDOW_MEMORY,
        window_governance: int = DEFAULT_WINDOW_GOVERNANCE,
        weights: Optional[TriadicWeights] = None,
        harmonic_r: float = HARMONIC_R,
        harmonic_dimensions: int = 6,
        reference_point: Optional[List[float]] = None,
    ):
        self._immediate = TemporalWindow(window_immediate)
        self._memory = TemporalWindow(window_memory)
        self._governance = TemporalWindow(window_governance)

        self._weights = (weights or TriadicWeights()).normalized()
        self._harmonic_r = harmonic_r
        self._harmonic_dimensions = harmonic_dimensions
        self._reference = reference_point or [0.0] * BRAIN_DIMENSIONS

        self._nodes: List[LatticeNode] = []
        self._tick: int = 0

    def ingest(self, raw_state: List[float]) -> LatticeNode:
        """Ingest a new 21D state vector into the lattice.

        1. Embeds into Poincaré ball
        2. Computes hyperbolic distance from reference
        3. Pushes to all three temporal windows
        4. Computes triadic distance and harmonic cost

        Returns:
            LatticeNode with all computed metrics.
        """
        self._tick += 1

        embedded = safe_poincare_embed(raw_state)
        ref_embedded = safe_poincare_embed(self._reference)
        embedded_norm = vector_norm(embedded)

        h_dist = hyperbolic_distance_safe(embedded, ref_embedded)

        self._immediate.push(h_dist)
        self._memory.push(h_dist)
        self._governance.push(h_dist)

        d1 = self._immediate.average()
        d2 = self._memory.average()
        d_g = self._governance.average()

        d_tri = triadic_distance(d1, d2, d_g, self._weights)

        h_scale = harmonic_scale(self._harmonic_dimensions, self._harmonic_r)
        h_cost = d_tri * h_scale

        node = LatticeNode(
            tick=self._tick,
            raw_state=list(raw_state),
            embedded=embedded,
            hyperbolic_dist=h_dist,
            manifold_distances={"immediate": d1, "memory": d2, "governance": d_g},
            triadic_distance=d_tri,
            harmonic_cost=h_cost,
            embedded_norm=embedded_norm,
            timestamp=time.time(),
        )

        self._nodes.append(node)
        if len(self._nodes) > MAX_LATTICE_DEPTH:
            self._nodes = self._nodes[-MAX_LATTICE_DEPTH:]

        return node

    def drift_velocity(self) -> float:
        """Rate of change of triadic distance (finite difference)."""
        if len(self._nodes) < 2:
            return 0.0
        return self._nodes[-1].triadic_distance - self._nodes[-2].triadic_distance

    def drift_acceleration(self) -> float:
        """Second derivative of triadic distance."""
        if len(self._nodes) < 3:
            return 0.0
        d2 = self._nodes[-1].triadic_distance
        d1 = self._nodes[-2].triadic_distance
        d0 = self._nodes[-3].triadic_distance
        return d2 - 2 * d1 + d0

    def current_triadic_distance(self) -> float:
        """Current triadic distance (0 if no samples)."""
        if not self._nodes:
            return 0.0
        return self._nodes[-1].triadic_distance

    def current_harmonic_cost(self) -> float:
        """Current harmonic cost (0 if no samples)."""
        if not self._nodes:
            return 0.0
        return self._nodes[-1].harmonic_cost

    def temporal_resonance(self) -> float:
        """Temporal resonance coefficient in [0, 1].

        1 = perfect agreement across all three manifolds.
        Lower values indicate temporal drift/divergence.
        """
        if not self._nodes:
            return 1.0
        latest = self._nodes[-1]
        d1 = latest.manifold_distances["immediate"]
        d2 = latest.manifold_distances["memory"]
        d_g = latest.manifold_distances["governance"]
        avg = (d1 + d2 + d_g) / 3.0
        if avg < BRAIN_EPSILON:
            return 1.0
        variance = ((d1 - avg) ** 2 + (d2 - avg) ** 2 + (d_g - avg) ** 2) / 3.0
        return 1.0 / (1.0 + variance / (avg * avg))

    def temporal_anomaly(self) -> float:
        """Temporal anomaly: |d₁ - d_G| / d_G.

        High values indicate immediate window diverges from governance.
        """
        if not self._nodes:
            return 0.0
        latest = self._nodes[-1]
        d1 = latest.manifold_distances["immediate"]
        d_g = latest.manifold_distances["governance"]
        denom = max(d_g, BRAIN_EPSILON)
        return abs(d1 - d_g) / denom

    def snapshot(self) -> LatticeSnapshot:
        """Current lattice snapshot."""
        latest = self._nodes[-1] if self._nodes else None
        return LatticeSnapshot(
            tick=self._tick,
            triadic_distance=latest.triadic_distance if latest else 0.0,
            harmonic_cost=latest.harmonic_cost if latest else 0.0,
            manifold_distances=latest.manifold_distances if latest else {"immediate": 0, "memory": 0, "governance": 0},
            weights=TriadicWeights(self._weights.immediate, self._weights.memory, self._weights.governance),
            node_count=len(self._nodes),
            drift_velocity=self.drift_velocity(),
        )

    def verify_duality(self, d: int) -> Tuple[float, float, float]:
        """Verify H(d, R) * H(d, 1/R) = 1."""
        fwd = harmonic_scale(d, self._harmonic_r)
        inv = harmonic_scale_inverse(d, self._harmonic_r)
        return fwd, inv, fwd * inv

    @property
    def tick(self) -> int:
        return self._tick

    @property
    def weights(self) -> TriadicWeights:
        return self._weights

    def reset(self) -> None:
        """Reset all windows and lattice state."""
        self._immediate.reset()
        self._memory.reset()
        self._governance.reset()
        self._nodes.clear()
        self._tick = 0
