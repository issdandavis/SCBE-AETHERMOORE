"""
Dimensional Space for Cognitive Governance
==========================================

Defines the 54-dimensional cognitive space using:
- 3 valences: negative, neutral, positive
- 3 spatial dimensions per valence
- 6 Sacred Tongues with golden ratio (phi) weighting

Each CognitivePoint lives in this space and represents an AI agent's
current cognitive state. Movement cost scales exponentially with
hyperbolic distance from the safe center.

@module cognitive_governance/dimensional_space
@layer L1-L4 (Context Embedding)
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

# Golden ratio for tongue weighting
PHI = (1 + math.sqrt(5)) / 2

# Six Sacred Tongues with phase angles and phi-scaled weights
TONGUES = {
    "KO": {"phase": 0, "weight": 1.00},  # Kor'aelin (Control)
    "AV": {"phase": 60, "weight": PHI},  # Avali (I/O)
    "RU": {"phase": 120, "weight": PHI**2},  # Runethic (Policy)
    "CA": {"phase": 180, "weight": PHI**3},  # Cassisivadan (Compute)
    "UM": {"phase": 240, "weight": PHI**4},  # Umbroth (Security)
    "DR": {"phase": 300, "weight": PHI**5},  # Draumric (Structure)
}

TONGUE_NAMES = list(TONGUES.keys())


class StateValence(Enum):
    """Three-state valence for cognitive dimensions."""

    NEGATIVE = -1
    NEUTRAL = 0
    POSITIVE = 1


@dataclass
class TongueVector:
    """
    A vector in one of the six Sacred Tongue dimensions.

    Each tongue contributes a weighted component to the overall
    cognitive state. The phase angle determines coupling between tongues.
    """

    tongue: str
    magnitude: float = 0.0
    phase_offset: float = 0.0  # Additional phase beyond base tongue phase

    @property
    def weight(self) -> float:
        """Phi-scaled weight for this tongue."""
        return TONGUES[self.tongue]["weight"]

    @property
    def base_phase(self) -> float:
        """Base phase angle in degrees."""
        return TONGUES[self.tongue]["phase"]

    @property
    def total_phase_rad(self) -> float:
        """Total phase in radians (base + offset)."""
        return math.radians(self.base_phase + self.phase_offset)

    @property
    def weighted_magnitude(self) -> float:
        """Magnitude scaled by tongue weight."""
        return self.magnitude * self.weight

    def project_real(self) -> float:
        """Real component of phase projection."""
        return self.weighted_magnitude * math.cos(self.total_phase_rad)

    def project_imag(self) -> float:
        """Imaginary component of phase projection."""
        return self.weighted_magnitude * math.sin(self.total_phase_rad)


@dataclass
class CognitivePoint:
    """
    A point in the 54-dimensional cognitive space.

    Structure: 3 valences x 3 spatial x 6 tongues = 54 faces.
    Each face has a magnitude and optional phase offset.

    The point's position determines governance decisions:
    - Near center (0,0,...,0) = safe operation
    - Near boundary = increasingly expensive/restricted
    - Beyond boundary = denied (infinite cost)
    """

    # Core coordinates: valence -> spatial_dim -> tongue -> magnitude
    coordinates: Dict[StateValence, Dict[int, Dict[str, float]]] = field(
        default_factory=lambda: {v: {d: {t: 0.0 for t in TONGUE_NAMES} for d in range(3)} for v in StateValence}
    )
    # Phase offsets per tongue (beyond base phase)
    phase_offsets: Dict[str, float] = field(default_factory=lambda: {t: 0.0 for t in TONGUE_NAMES})
    # Metadata
    agent_id: Optional[str] = None
    timestamp: float = 0.0

    def get_coordinate(self, valence: StateValence, spatial: int, tongue: str) -> float:
        """Get a single coordinate value."""
        return self.coordinates[valence][spatial][tongue]

    def set_coordinate(self, valence: StateValence, spatial: int, tongue: str, value: float):
        """Set a single coordinate value."""
        self.coordinates[valence][spatial][tongue] = value

    def to_flat_vector(self) -> List[float]:
        """Flatten to 54-element vector for distance calculations."""
        vec = []
        for valence in StateValence:
            for spatial in range(3):
                for tongue in TONGUE_NAMES:
                    vec.append(self.coordinates[valence][spatial][tongue])
        return vec

    @classmethod
    def from_flat_vector(cls, vec: List[float], agent_id: Optional[str] = None) -> "CognitivePoint":
        """Construct from 54-element flat vector."""
        assert len(vec) == 54, f"Expected 54 dimensions, got {len(vec)}"
        point = cls(agent_id=agent_id)
        idx = 0
        for valence in StateValence:
            for spatial in range(3):
                for tongue in TONGUE_NAMES:
                    point.coordinates[valence][spatial][tongue] = vec[idx]
                    idx += 1
        return point

    def norm_squared(self) -> float:
        """Squared Euclidean norm of the flat vector."""
        return sum(x * x for x in self.to_flat_vector())

    def norm(self) -> float:
        """Euclidean norm."""
        return math.sqrt(self.norm_squared())

    def poincare_norm(self) -> float:
        """
        Norm in the Poincare ball model.
        Clamped to [0, 1) to stay within the ball.
        """
        n = self.norm()
        return min(n, 0.9999)

    def tongue_energy(self, tongue: str) -> float:
        """Total energy in a specific tongue dimension across all valences/spatial."""
        total = 0.0
        for valence in StateValence:
            for spatial in range(3):
                val = self.coordinates[valence][spatial][tongue]
                total += val * val
        return total

    def valence_energy(self, valence: StateValence) -> float:
        """Total energy in a specific valence across all spatial/tongue dimensions."""
        total = 0.0
        for spatial in range(3):
            for tongue in TONGUE_NAMES:
                val = self.coordinates[valence][spatial][tongue]
                total += val * val
        return total

    def dominant_tongue(self) -> str:
        """The tongue with the highest energy."""
        return max(TONGUE_NAMES, key=self.tongue_energy)

    def dominant_valence(self) -> StateValence:
        """The valence with the highest energy."""
        return max(StateValence, key=self.valence_energy)


@dataclass
class DimensionalSpace:
    """
    The full 54-dimensional cognitive space with hyperbolic geometry.

    Implements the Poincare ball model where:
    - The center represents safe, neutral operation
    - The boundary (unit sphere) represents infinity
    - Distance grows exponentially near the boundary

    Key formula:
        d_H(u,v) = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))
    """

    # Curvature parameter (negative = hyperbolic)
    curvature: float = -1.0
    # Cost base for exponential scaling
    R: float = 2.0
    # Gamma multiplier for cost exponent
    gamma: float = PHI

    def hyperbolic_distance(self, p1: CognitivePoint, p2: CognitivePoint) -> float:
        """
        Poincare ball distance between two cognitive points.

        @axiom A5: Hyperbolic distance (Layer 5)
        """
        v1 = p1.to_flat_vector()
        v2 = p2.to_flat_vector()

        norm1_sq = sum(x * x for x in v1)
        norm2_sq = sum(x * x for x in v2)
        diff_sq = sum((a - b) ** 2 for a, b in zip(v1, v2))

        # Clamp to stay within Poincare ball
        norm1_sq = min(norm1_sq, 0.9999)
        norm2_sq = min(norm2_sq, 0.9999)

        denom = (1 - norm1_sq) * (1 - norm2_sq)
        if denom <= 0:
            return float("inf")

        delta = 2 * diff_sq / denom
        if delta < 0:
            return 0.0

        return math.acosh(1 + delta)

    def distance_from_center(self, point: CognitivePoint) -> float:
        """Hyperbolic distance from the safe center (origin)."""
        origin = CognitivePoint()
        return self.hyperbolic_distance(point, origin)

    def cost_multiplier(self, distance: float) -> float:
        """
        Exponential cost scaling: H = R^((d * gamma)^2)

        This is the core innovation - adversarial intent costs
        exponentially more the further from safe operation.

        @axiom A4: Harmonic wall (Layer 12)
        """
        exponent = (distance * self.gamma) ** 2
        return self.R**exponent

    def safety_score(self, point: CognitivePoint) -> float:
        """
        Bounded safety score in (0, 1].

        H(d, pd) = 1 / (1 + d_H + 2*pd)

        Where pd is the Poincare disk radius.
        """
        d_h = self.distance_from_center(point)
        pd = point.poincare_norm()
        return 1.0 / (1.0 + d_h + 2.0 * pd)

    def tongue_weighted_distance(self, p1: CognitivePoint, p2: CognitivePoint) -> float:
        """
        Distance weighted by tongue phi-scaling.

        Higher tongues (UM, DR) contribute more to perceived distance,
        meaning security and structural deviations are penalized more.
        """
        v1 = p1.to_flat_vector()
        v2 = p2.to_flat_vector()

        weighted_diff_sq = 0.0
        num_valences = len(StateValence)
        num_spatial = 3
        for idx in range(num_valences * num_spatial * len(TONGUE_NAMES)):
            tongue = TONGUE_NAMES[idx % len(TONGUE_NAMES)]
            w = TONGUES[tongue]["weight"]
            diff = v1[idx] - v2[idx]
            weighted_diff_sq += w * diff * diff

        return math.sqrt(weighted_diff_sq)

    def phase_coupling(self, p1: CognitivePoint, p2: CognitivePoint) -> float:
        """
        Measure phase alignment between two points.

        Returns value in [-1, 1]:
        - 1.0 = perfectly aligned phases
        - 0.0 = orthogonal
        - -1.0 = anti-aligned

        @axiom A3: Symmetry (Layer 5, 9, 10, 12)
        """
        total_coupling = 0.0
        count = 0

        for tongue in TONGUE_NAMES:
            e1 = p1.tongue_energy(tongue)
            e2 = p2.tongue_energy(tongue)
            if e1 > 1e-10 and e2 > 1e-10:
                phase1 = math.radians(TONGUES[tongue]["phase"] + p1.phase_offsets[tongue])
                phase2 = math.radians(TONGUES[tongue]["phase"] + p2.phase_offsets[tongue])
                total_coupling += math.cos(phase1 - phase2)
                count += 1

        return total_coupling / max(count, 1)

    def embed_action(
        self,
        agent_id: str,
        action: str,
        target: str,
        trust: float = 0.5,
        sensitivity: float = 0.5,
    ) -> CognitivePoint:
        """
        Embed an agent action into the cognitive space.

        Maps (agent_id, action, target) to a point in the 54D space.
        Trust score controls distance from center.
        Sensitivity controls which tongue dimensions are activated.

        @axiom A1: Context embedding (Layers 1-4)
        """
        import hashlib

        # Deterministic seed from action context
        seed = hashlib.sha256(f"{agent_id}:{action}:{target}".encode()).digest()

        point = CognitivePoint(agent_id=agent_id)

        # Radius scales with inverse trust (low trust = further from center)
        radius = (1 - trust) * 0.8 + 0.05

        idx = 0
        for valence in StateValence:
            for spatial in range(3):
                for _i, tongue in enumerate(TONGUE_NAMES):
                    # Use seed bytes to determine coordinate
                    byte_val = seed[idx % len(seed)] / 255.0
                    # Scale by radius and tongue weight
                    coord = (byte_val - 0.5) * radius
                    # Higher sensitivity activates security tongues more
                    if tongue in ("UM", "DR") and sensitivity > 0.5:
                        coord *= 1 + sensitivity
                    point.set_coordinate(valence, spatial, tongue, coord)
                    idx += 1

        return point
