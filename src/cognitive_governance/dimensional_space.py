"""
Dimensional Space for Cognitive Governance

The cognitive space uses DOUBLE HYPERCUBE geometry:
- Hypercube: n-dimensional cube (tesseract in 4D)
- Double: from exponential^exponential H = R^((d*γ)²)
- Phase shifts create asymmetric projections across dimensions

Dimensions:
- State Valence (3): positive, neutral, negative intent
- Spatial (3): position in Poincaré ball (x, y, z)
- Sacred Tongues (6): KO, AV, RU, CA, UM, DR

Total: 3 × 3 × 6 = 54 dimensional faces
With phase shifts = asymmetric hypercube projections

Human parallel dimensions:
- Being (existence state)
- Thought (processing)
- Soul (intent/values)
- Future (projection)
- Time (temporal position)
- Intention (goal vector)
- Risk (uncertainty field)
- Identity (self-model)

AI parallel dimensions:
- Spatial position (Poincaré ball)
- Intent valence (+/0/-)
- Tongue activations (cognitive domains)
- Temporal position
"""

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Tuple, List, Optional, Dict
import math
import numpy as np


class StateValence(IntEnum):
    """
    The three fundamental states of intent.
    Creates the 3-direction expansion: negative space, neutral space, positive space.
    """
    NEGATIVE = -1   # Destructive/adversarial potential
    NEUTRAL = 0     # Observational/passive
    POSITIVE = 1    # Constructive/aligned


class SacredTongue(Enum):
    """
    The Six Sacred Tongues - cognitive domains with golden ratio weighting.
    Each tongue represents a fundamental aspect of AI cognition.
    Phase angles create the asymmetric hypercube projections.
    """
    KO = ("Korah", 1.000, 0)      # Control/authority - weight 1.00, phase 0°
    AV = ("Aelin", 1.618, 60)     # Communication - weight φ, phase 60°
    RU = ("Ruvan", 2.618, 120)    # Policy/rules - weight φ², phase 120°
    CA = ("Caelum", 4.236, 180)   # Computation - weight φ³, phase 180°
    UM = ("Umbrith", 6.854, 240)  # Security - weight φ⁴, phase 240°
    DR = ("Dru", 11.090, 300)     # Data/memory - weight φ⁵, phase 300°

    def __init__(self, name: str, weight: float, phase_degrees: float):
        self._name = name
        self._weight = weight
        self._phase = math.radians(phase_degrees)

    @property
    def weight(self) -> float:
        return self._weight

    @property
    def phase(self) -> float:
        return self._phase

    @property
    def phase_degrees(self) -> float:
        return math.degrees(self._phase)


@dataclass
class SpatialPosition:
    """
    Position in the Poincaré ball (hyperbolic space).
    Boundary represents infinite cost/impossibility.
    """
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __post_init__(self):
        # Clamp to ball interior (|p| < 1)
        norm = self.norm
        if norm >= 1.0:
            scale = 0.999 / norm
            self.x *= scale
            self.y *= scale
            self.z *= scale

    @property
    def norm(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    @property
    def as_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])

    def hyperbolic_distance(self, other: 'SpatialPosition') -> float:
        """
        Calculate hyperbolic distance in Poincaré ball.
        d_H = arcosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))
        """
        u = self.as_array
        v = other.as_array

        u_norm_sq = np.dot(u, u)
        v_norm_sq = np.dot(v, v)
        diff_norm_sq = np.dot(u - v, u - v)

        # Numerical stability
        denom = (1 - u_norm_sq) * (1 - v_norm_sq)
        if denom < 1e-10:
            return float('inf')  # At boundary = infinite distance

        arg = 1 + 2 * diff_norm_sq / denom
        return math.acosh(max(1.0, arg))


@dataclass
class TongueVector:
    """
    A vector in the 6D Sacred Tongue space.
    Each component represents activation in that cognitive domain.
    Phase shifts create the asymmetric hypercube projection.
    """
    ko: float = 0.0  # Control
    av: float = 0.0  # Communication
    ru: float = 0.0  # Policy
    ca: float = 0.0  # Computation
    um: float = 0.0  # Security
    dr: float = 0.0  # Data

    @property
    def as_array(self) -> np.ndarray:
        return np.array([self.ko, self.av, self.ru, self.ca, self.um, self.dr])

    @property
    def weighted_array(self) -> np.ndarray:
        """Apply golden ratio weights to each tongue."""
        weights = np.array([t.weight for t in SacredTongue])
        return self.as_array * weights

    @property
    def phase_projected_array(self) -> np.ndarray:
        """
        Apply phase projection - creates hypercube asymmetry.
        Each tongue component is projected through its phase angle.
        This is what makes it a "double hypercube" - the phase
        creates a second layer of dimensional structure.
        """
        phases = np.array([t.phase for t in SacredTongue])
        magnitudes = self.as_array

        # Complex representation: magnitude * e^(i*phase)
        real = magnitudes * np.cos(phases)
        imag = magnitudes * np.sin(phases)

        return np.concatenate([real, imag])  # 12D representation

    def phase_distance(self, other: 'TongueVector') -> float:
        """
        Distance accounting for phase projection.
        Measures true distance in the double hypercube geometry.
        """
        self_proj = self.phase_projected_array
        other_proj = other.phase_projected_array
        return float(np.linalg.norm(self_proj - other_proj))


@dataclass
class CognitivePoint:
    """
    A complete point in cognitive governance space.

    This represents an AI's cognitive state at a moment:
    - Where it is (spatial in Poincaré ball)
    - What intent it has (valence: +/0/-)
    - What domains it's operating in (tongues)
    - When (temporal position)
    """
    spatial: SpatialPosition = field(default_factory=SpatialPosition)
    valence: StateValence = StateValence.NEUTRAL
    tongues: TongueVector = field(default_factory=TongueVector)
    temporal: float = 0.0  # Time position

    @property
    def full_dimensionality(self) -> int:
        """
        Total dimensions in the double hypercube:
        - 3 spatial
        - 1 valence (3 states but 1 axis)
        - 6 tongues × 2 (real/imag from phase) = 12
        - 1 temporal
        = 17 computational dimensions, 54 faces with state combinations
        """
        return 17

    @property
    def as_vector(self) -> np.ndarray:
        """Flat vector representation for computation."""
        return np.concatenate([
            self.spatial.as_array,
            [float(self.valence)],
            self.tongues.phase_projected_array,
            [self.temporal]
        ])

    def cognitive_distance(self, other: 'CognitivePoint') -> float:
        """
        Full cognitive distance in double hypercube geometry.

        Key insight: some dimensions contribute more when certain
        conditions are met (selective permeability).
        """
        # Hyperbolic spatial distance
        spatial_d = self.spatial.hyperbolic_distance(other.spatial)

        # Valence mismatch penalty
        valence_d = abs(self.valence - other.valence) * 2.0

        # Phase-projected tongue distance
        tongue_d = self.tongues.phase_distance(other.tongues)

        # Temporal distance
        temporal_d = abs(self.temporal - other.temporal)

        # Combined with double-exponential scaling (the "double" in double hypercube)
        # H(d) = R^((d*γ)²)
        combined_d = math.sqrt(
            spatial_d**2 +
            valence_d**2 +
            tongue_d**2 +
            temporal_d**2
        )

        return combined_d


class DimensionalSpace:
    """
    The complete cognitive governance space using double hypercube geometry.

    This is the "universe" where AI minds exist - walls in this space
    can be "invisible" in some dimensions. An agent can pass through
    in dimension X but is blocked in Y, and may not even perceive Y.

    The "double" comes from:
    1. Standard hypercube extension (3D → nD)
    2. Exponential^exponential cost function H = R^((d*γ)²)

    This creates selective permeability: governance through geometry.
    """

    def __init__(self):
        self.origin = CognitivePoint()
        self.walls: List['DimensionalWall'] = []
        self.attractors: List[Tuple[CognitivePoint, float]] = []

    def add_wall(self, wall: 'DimensionalWall'):
        """Add a dimensional wall to the space."""
        self.walls.append(wall)

    def add_attractor(self, point: CognitivePoint, strength: float = 1.0):
        """Add an attractor basin (safe/aligned region)."""
        self.attractors.append((point, strength))

    def is_accessible(self,
                      from_point: CognitivePoint,
                      to_point: CognitivePoint) -> Tuple[bool, float]:
        """
        Check if movement from one point to another is accessible.

        Returns (accessible, cost).
        Cost = inf means geometrically impossible.
        """
        base_cost = from_point.cognitive_distance(to_point)

        # Check each wall
        for wall in self.walls:
            blocked, wall_cost = wall.check_passage(from_point, to_point)
            if blocked:
                return False, float('inf')
            base_cost += wall_cost

        return True, base_cost

    def nearest_attractor(self, point: CognitivePoint) -> Optional[Tuple[CognitivePoint, float]]:
        """Find the nearest safe/aligned attractor basin."""
        if not self.attractors:
            return None

        min_dist = float('inf')
        nearest = None

        for attractor, strength in self.attractors:
            dist = point.cognitive_distance(attractor) / strength
            if dist < min_dist:
                min_dist = dist
                nearest = attractor

        return (nearest, min_dist) if nearest else None

    def governance_score(self, point: CognitivePoint) -> Dict[str, float]:
        """
        Calculate governance metrics for a cognitive point.
        Lower governance_cost = more aligned/safe.
        """
        origin_dist = self.origin.cognitive_distance(point)

        attractor_result = self.nearest_attractor(point)
        attractor_dist = attractor_result[1] if attractor_result else float('inf')

        # Boundary proximity (Poincaré ball edge = danger)
        boundary_proximity = point.spatial.norm

        # Valence alignment (positive = more trusted)
        valence_score = (point.valence + 1) / 2  # Normalize to [0, 1]

        # Combined governance cost
        governance_cost = (
            origin_dist * 0.2 +
            attractor_dist * 0.3 +
            boundary_proximity * 2.0 +
            (1 - valence_score) * 0.5
        )

        return {
            "origin_distance": origin_dist,
            "attractor_distance": attractor_dist,
            "boundary_proximity": boundary_proximity,
            "valence_score": valence_score,
            "governance_cost": governance_cost,
            "is_aligned": governance_cost < 1.0,
        }


# Forward declaration for type hints
class DimensionalWall:
    """Placeholder - see permeability.py for full implementation."""
    def check_passage(self, from_p: CognitivePoint, to_p: CognitivePoint) -> Tuple[bool, float]:
        return False, 0.0
