"""
Unified Brain State - Python Reference Implementation

21D unified brain state vector integrating all SCBE-AETHERMOORE components:
  SCBE Context (6D) + Navigation (6D) + Cognitive (3D) + Semantic (3D) + Swarm (3D)

@module ai_brain/unified_state
@layer Layer 1-14 (Unified Manifold)
@version 1.1.0
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional

# Constants
BRAIN_DIMENSIONS = 21
PHI = (1 + math.sqrt(5)) / 2
BRAIN_EPSILON = 1e-10
POINCARE_MAX_NORM = 1 - 1e-8


def _vec_norm(v: List[float]) -> float:
    """Compute Euclidean norm."""
    return math.sqrt(sum(x * x for x in v))


def _vec_sub(a: List[float], b: List[float]) -> List[float]:
    """Subtract two vectors."""
    return [a[i] - b[i] for i in range(len(a))]


# Golden ratio weights: w_i = phi^i for i in [0, 20]
GOLDEN_WEIGHTS = [PHI**i for i in range(BRAIN_DIMENSIONS)]


def apply_golden_weighting(vector: List[float]) -> List[float]:
    """Apply golden ratio weighting to a 21D vector.

    Creates hierarchical importance: higher dimensions receive
    exponentially more weight.

    Args:
        vector: Raw 21D brain state vector.

    Returns:
        Weighted 21D vector.

    Raises:
        ValueError: If vector is not 21D.
    """
    if len(vector) != BRAIN_DIMENSIONS:
        raise ValueError(f"Expected {BRAIN_DIMENSIONS}D vector, got {len(vector)}D")
    return [v * w for v, w in zip(vector, GOLDEN_WEIGHTS)]


def safe_poincare_embed(vector: List[float], epsilon: float = BRAIN_EPSILON) -> List[float]:
    """Embed a vector into the Poincare ball with numerically stable boundary clamping.

    Uses exponential map from origin: exp_0(v) = tanh(||v||/2) * v/||v||.
    Designed for raw state vectors (components typically in [0, 1]).
    Fixes Theorem 3 boundary failure.

    Args:
        vector: Input vector (any dimension).
        epsilon: Boundary epsilon.

    Returns:
        Point strictly inside the Poincare ball.
    """
    n = _vec_norm(vector)
    if n < epsilon:
        return [0.0] * len(vector)

    mapped_norm = math.tanh(n / 2)
    clamped_norm = min(mapped_norm, POINCARE_MAX_NORM)
    return [v * clamped_norm / n for v in vector]


def hyperbolic_distance_safe(u: List[float], v: List[float]) -> float:
    """Compute hyperbolic distance in the Poincare ball model.

    d_H(u,v) = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))

    Args:
        u: First point in Poincare ball.
        v: Second point in Poincare ball.

    Returns:
        Hyperbolic distance.
    """
    diff = _vec_sub(u, v)
    diff_norm_sq = sum(x * x for x in diff)
    u_norm_sq = sum(x * x for x in u)
    v_norm_sq = sum(x * x for x in v)

    u_factor = max(BRAIN_EPSILON, 1 - u_norm_sq)
    v_factor = max(BRAIN_EPSILON, 1 - v_norm_sq)

    arg = 1 + (2 * diff_norm_sq) / (u_factor * v_factor)
    return math.acosh(max(1, arg))


@dataclass
class SCBEContext:
    """SCBE Core context (6D) - Layers 1-2."""

    device_trust: float = 0.5
    location_trust: float = 0.5
    network_trust: float = 0.5
    behavior_score: float = 0.5
    time_of_day: float = 0.5
    intent_alignment: float = 0.5


@dataclass
class NavigationVector:
    """Dual Lattice navigation vector (6D)."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    time: float = 0.0
    priority: float = 0.5
    confidence: float = 0.5


@dataclass
class CognitivePosition:
    """PHDM cognitive position (3D) in quasicrystal space."""

    px: float = 0.0
    py: float = 0.0
    pz: float = 0.0


@dataclass
class SemanticPhase:
    """Sacred Tongues semantic phase (3D)."""

    active_tongue: float = 0.0
    phase_angle: float = 0.0
    tongue_weight: float = 1.0


@dataclass
class SwarmCoordination:
    """Swarm coordination state (3D)."""

    trust_score: float = 0.5
    byzantine_votes: float = 0.0
    spectral_coherence: float = 0.5


@dataclass
class TrajectoryPoint:
    """Agent trajectory point in the unified manifold."""

    step: int
    state: List[float]
    embedded: List[float]
    distance: float
    curvature: float = 0.0
    timestamp: float = 0.0


class UnifiedBrainState:
    """The 21D manifold integrating all SCBE-AETHERMOORE components.

    Maintains coherent state across:
    - SCBE Core (6D context)
    - Dual Lattice (6D navigation)
    - PHDM (3D cognitive)
    - Sacred Tongues (3D semantic)
    - Swarm (3D coordination)
    """

    def __init__(
        self,
        scbe_context: Optional[SCBEContext] = None,
        navigation: Optional[NavigationVector] = None,
        cognitive_position: Optional[CognitivePosition] = None,
        semantic_phase: Optional[SemanticPhase] = None,
        swarm_coordination: Optional[SwarmCoordination] = None,
    ):
        self.scbe_context = scbe_context or SCBEContext()
        self.navigation = navigation or NavigationVector()
        self.cognitive_position = cognitive_position or CognitivePosition()
        self.semantic_phase = semantic_phase or SemanticPhase()
        self.swarm_coordination = swarm_coordination or SwarmCoordination()

    def to_vector(self) -> List[float]:
        """Flatten to raw 21D vector."""
        ctx = self.scbe_context
        nav = self.navigation
        cog = self.cognitive_position
        sem = self.semantic_phase
        swm = self.swarm_coordination

        return [
            ctx.device_trust, ctx.location_trust, ctx.network_trust,
            ctx.behavior_score, ctx.time_of_day, ctx.intent_alignment,
            nav.x, nav.y, nav.z, nav.time, nav.priority, nav.confidence,
            cog.px, cog.py, cog.pz,
            sem.active_tongue, sem.phase_angle, sem.tongue_weight,
            swm.trust_score, swm.byzantine_votes, swm.spectral_coherence,
        ]

    def to_weighted_vector(self) -> List[float]:
        """Apply golden ratio weighting to the state vector."""
        return apply_golden_weighting(self.to_vector())

    def to_poincare_point(self) -> List[float]:
        """Embed into Poincare ball using raw vector (not golden-weighted)."""
        return safe_poincare_embed(self.to_vector())

    def distance_to(self, other: "UnifiedBrainState") -> float:
        """Compute hyperbolic distance to another brain state."""
        return hyperbolic_distance_safe(
            self.to_poincare_point(), other.to_poincare_point()
        )

    def distance_from_origin(self) -> float:
        """Compute distance from the safe origin (center of Poincare ball)."""
        origin = [0.0] * BRAIN_DIMENSIONS
        return hyperbolic_distance_safe(origin, self.to_poincare_point())

    def boundary_distance(self) -> float:
        """Compute boundary distance (how close to the Poincare ball edge)."""
        point = self.to_poincare_point()
        return 1.0 - _vec_norm(point)

    def to_trajectory_point(self, step: int) -> TrajectoryPoint:
        """Create a trajectory point from the current state."""
        import time as time_mod
        vec = self.to_vector()
        embedded = self.to_poincare_point()
        return TrajectoryPoint(
            step=step,
            state=vec,
            embedded=embedded,
            distance=self.distance_from_origin(),
            curvature=0.0,
            timestamp=time_mod.time(),
        )

    @classmethod
    def from_vector(cls, vector: List[float]) -> "UnifiedBrainState":
        """Reconstruct from a raw 21D vector."""
        if len(vector) != BRAIN_DIMENSIONS:
            raise ValueError(f"Expected {BRAIN_DIMENSIONS}D vector, got {len(vector)}D")

        return cls(
            scbe_context=SCBEContext(
                device_trust=vector[0], location_trust=vector[1],
                network_trust=vector[2], behavior_score=vector[3],
                time_of_day=vector[4], intent_alignment=vector[5],
            ),
            navigation=NavigationVector(
                x=vector[6], y=vector[7], z=vector[8],
                time=vector[9], priority=vector[10], confidence=vector[11],
            ),
            cognitive_position=CognitivePosition(
                px=vector[12], py=vector[13], pz=vector[14],
            ),
            semantic_phase=SemanticPhase(
                active_tongue=vector[15], phase_angle=vector[16],
                tongue_weight=vector[17],
            ),
            swarm_coordination=SwarmCoordination(
                trust_score=vector[18], byzantine_votes=vector[19],
                spectral_coherence=vector[20],
            ),
        )

    @classmethod
    def safe_origin(cls) -> "UnifiedBrainState":
        """Create a safe origin state (center of manifold)."""
        return cls(
            scbe_context=SCBEContext(
                device_trust=1, location_trust=1, network_trust=1,
                behavior_score=1, time_of_day=0.5, intent_alignment=1,
            ),
            navigation=NavigationVector(x=0, y=0, z=0, time=0, priority=0.5, confidence=1),
            cognitive_position=CognitivePosition(px=0, py=0, pz=0),
            semantic_phase=SemanticPhase(active_tongue=0, phase_angle=0, tongue_weight=1),
            swarm_coordination=SwarmCoordination(trust_score=1, byzantine_votes=0, spectral_coherence=1),
        )
