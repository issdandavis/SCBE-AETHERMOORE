"""
Double Hypercube Geometry for Cognitive Governance
==================================================

Implements the double hypercube (tesseract) structure that forms
the outer boundary of the cognitive governance space.

Key concept: The Poincare ball (inner hyperbolic space) is enclosed
by a double hypercube whose faces represent governance boundaries.
Different faces have different permeability - creating selective
dimensional walls.

3 valences x 3 spatial x 6 tongues = 54 faces on the hypercube.

@module cognitive_governance/hypercube_geometry
@layer L3-L4 (Weighted transform, Poincare embedding)
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .dimensional_space import (
    PHI,
    TONGUE_NAMES,
    TONGUES,
    CognitivePoint,
    StateValence,
    TongueVector,
)


@dataclass
class HypercubeFace:
    """
    A single face of the 54-face hypercube.

    Each face corresponds to one (valence, spatial, tongue) triple.
    The face has a normal vector, a permeability level, and a cost
    function for crossing.
    """
    valence: StateValence
    spatial_dim: int  # 0, 1, or 2
    tongue: str
    # Permeability: 0.0 = impenetrable wall, 1.0 = fully open
    permeability: float = 0.5
    # Cost multiplier for crossing this face
    crossing_cost: float = 1.0
    # Whether this face is currently active
    active: bool = True

    @property
    def face_id(self) -> str:
        """Unique identifier for this face."""
        return f"{self.valence.name}:{self.spatial_dim}:{self.tongue}"

    @property
    def tongue_weight(self) -> float:
        """Phi-scaled weight of the tongue for this face."""
        return TONGUES[self.tongue]["weight"]

    @property
    def effective_cost(self) -> float:
        """
        Effective cost of crossing, scaled by tongue weight.
        Higher tongues (UM, DR) have higher crossing costs.
        """
        return self.crossing_cost * self.tongue_weight

    def cost_to_cross(self, momentum: float) -> float:
        """
        Cost to cross this face given a momentum value.

        If permeability is 0, cost is infinite.
        If permeability is 1, cost equals the base effective cost.
        """
        if not self.active:
            return 0.0
        if self.permeability <= 0.0:
            return float("inf")
        return self.effective_cost / self.permeability * (1.0 + abs(momentum))


@dataclass
class Hypercube:
    """
    A single hypercube with 54 faces.

    Represents a governance boundary in the cognitive space.
    The hypercube is axis-aligned and centered at the origin,
    with face normals along each of the 54 dimensions.
    """
    faces: Dict[str, HypercubeFace] = field(default_factory=dict)
    # Half-width of the hypercube in each dimension
    half_width: float = 1.0

    def __post_init__(self):
        if not self.faces:
            self._init_faces()

    def _init_faces(self):
        """Initialize all 54 faces with default permeability."""
        for valence in StateValence:
            for spatial in range(3):
                for tongue in TONGUE_NAMES:
                    face = HypercubeFace(
                        valence=valence,
                        spatial_dim=spatial,
                        tongue=tongue,
                    )
                    self.faces[face.face_id] = face

    def get_face(self, valence: StateValence, spatial: int, tongue: str) -> HypercubeFace:
        """Get a specific face."""
        face_id = f"{valence.name}:{spatial}:{tongue}"
        return self.faces[face_id]

    def set_permeability(self, valence: StateValence, spatial: int, tongue: str, perm: float):
        """Set permeability for a specific face."""
        face = self.get_face(valence, spatial, tongue)
        face.permeability = max(0.0, min(1.0, perm))

    def set_tongue_permeability(self, tongue: str, perm: float):
        """Set permeability for all faces of a specific tongue."""
        for valence in StateValence:
            for spatial in range(3):
                self.set_permeability(valence, spatial, tongue, perm)

    def total_crossing_cost(self, point: CognitivePoint) -> float:
        """
        Total cost for a point to cross all faces it intersects.

        Points near faces incur crossing costs proportional to
        their proximity and the face's permeability.
        """
        total = 0.0
        for valence in StateValence:
            for spatial in range(3):
                for tongue in TONGUE_NAMES:
                    coord = point.get_coordinate(valence, spatial, tongue)
                    face = self.get_face(valence, spatial, tongue)
                    # Proximity to face boundary
                    proximity = abs(coord) / self.half_width if self.half_width > 0 else 0
                    if proximity > 0.8:  # Near the boundary
                        momentum = coord  # Use coordinate as momentum proxy
                        cost = face.cost_to_cross(momentum)
                        # Scale by how close to the boundary
                        scale = (proximity - 0.8) / 0.2
                        total += cost * scale
        return total

    @property
    def face_count(self) -> int:
        """Number of faces (should be 54)."""
        return len(self.faces)

    def active_faces(self) -> List[HypercubeFace]:
        """Return all currently active faces."""
        return [f for f in self.faces.values() if f.active]


@dataclass
class PhaseProjection:
    """
    Projects points between the hypercube boundary and the
    Poincare ball interior using tongue phase angles.

    The phase projection creates coupling between tongue dimensions:
    adjacent tongues (60deg apart) have stronger coupling than
    opposing tongues (180deg apart).

    @axiom A3: Symmetry (gauge invariance under phase rotation)
    """
    # Coupling strength between tongues
    coupling_matrix: Dict[Tuple[str, str], float] = field(default_factory=dict)

    def __post_init__(self):
        if not self.coupling_matrix:
            self._compute_coupling()

    def _compute_coupling(self):
        """
        Compute phase coupling between all tongue pairs.

        Coupling = cos(phase_i - phase_j), giving:
        - Adjacent tongues (60deg): coupling = 0.5
        - Opposite tongues (180deg): coupling = -1.0
        - Same tongue (0deg): coupling = 1.0
        """
        for t1 in TONGUE_NAMES:
            for t2 in TONGUE_NAMES:
                p1 = math.radians(TONGUES[t1]["phase"])
                p2 = math.radians(TONGUES[t2]["phase"])
                self.coupling_matrix[(t1, t2)] = math.cos(p1 - p2)

    def coupling(self, tongue1: str, tongue2: str) -> float:
        """Get coupling between two tongues."""
        return self.coupling_matrix.get((tongue1, tongue2), 0.0)

    def project_to_poincare(self, point: CognitivePoint, radius: float = 0.95) -> CognitivePoint:
        """
        Project a point from hypercube coordinates into the Poincare ball.

        Uses phase-weighted projection that couples adjacent tongue dimensions.
        The result is clamped to stay within the Poincare ball (norm < 1).
        """
        projected = CognitivePoint(agent_id=point.agent_id)

        for valence in StateValence:
            for spatial in range(3):
                for tongue in TONGUE_NAMES:
                    # Start with original coordinate
                    val = point.get_coordinate(valence, spatial, tongue)
                    # Add phase-coupled contributions from other tongues
                    for other in TONGUE_NAMES:
                        if other != tongue:
                            coupling = self.coupling(tongue, other)
                            other_val = point.get_coordinate(valence, spatial, other)
                            val += coupling * other_val * 0.1  # Weak coupling
                    # Clamp to Poincare ball radius
                    val = max(-radius, min(radius, val))
                    projected.set_coordinate(valence, spatial, tongue, val)

        return projected

    def project_to_hypercube(self, point: CognitivePoint) -> CognitivePoint:
        """
        Project from Poincare ball to hypercube boundary.

        Inverse of project_to_poincare (approximate).
        Used for determining which hypercube faces are relevant.
        """
        result = CognitivePoint(agent_id=point.agent_id)
        norm = point.norm()
        if norm < 1e-10:
            return result

        # Scale to hypercube boundary
        scale = 1.0 / norm if norm > 0 else 1.0

        for valence in StateValence:
            for spatial in range(3):
                for tongue in TONGUE_NAMES:
                    val = point.get_coordinate(valence, spatial, tongue)
                    result.set_coordinate(valence, spatial, tongue, val * scale)

        return result


@dataclass
class DoubleHypercube:
    """
    The Double Hypercube - two nested hypercubes forming the
    governance boundary structure.

    The outer hypercube defines hard limits (impenetrable walls).
    The inner hypercube defines soft limits (permeable, with cost).
    Between them is the "governance zone" where decisions are made.

    Key property: Different faces of the inner hypercube have different
    permeabilities - creating selective dimensional walls. A thought can
    pass freely through some dimensions but be blocked in others.

    This is the core of the "CUBES not CUPS" insight:
    - Hypercubes have flat faces (discrete boundaries)
    - Each face can independently control permeability
    - The double structure creates a governance gap
    """
    outer: Hypercube = field(default_factory=lambda: Hypercube(half_width=1.0))
    inner: Hypercube = field(default_factory=lambda: Hypercube(half_width=0.7))
    phase_projection: PhaseProjection = field(default_factory=PhaseProjection)

    def __post_init__(self):
        # Outer hypercube: all faces impenetrable (hard boundary)
        for face in self.outer.faces.values():
            face.permeability = 0.0
            face.crossing_cost = float("inf")

        # Inner hypercube: variable permeability (governance zone)
        self._configure_inner_permeability()

    def _configure_inner_permeability(self):
        """
        Configure default permeability for inner hypercube faces.

        Control tongues (KO, AV) are more permeable (easier to use).
        Security tongues (UM, DR) are less permeable (harder to abuse).
        """
        permeability_map = {
            "KO": 0.9,   # Control: very permeable
            "AV": 0.8,   # I/O: mostly permeable
            "RU": 0.6,   # Policy: moderately restricted
            "CA": 0.5,   # Compute: moderately restricted
            "UM": 0.3,   # Security: heavily restricted
            "DR": 0.2,   # Structure: heavily restricted
        }
        for tongue, perm in permeability_map.items():
            self.inner.set_tongue_permeability(tongue, perm)

    def governance_cost(self, point: CognitivePoint) -> float:
        """
        Total governance cost for a point in the double hypercube.

        Combines:
        1. Hyperbolic distance cost (exponential scaling)
        2. Inner hypercube face crossing costs
        3. Phase coupling penalties

        @axiom A4: Harmonic wall (Layer 12)
        """
        # Distance from center (hyperbolic)
        norm = point.poincare_norm()
        d_h = 0.0
        if norm > 1e-10:
            d_h = math.acosh(1 + 2 * norm ** 2 / (1 - norm ** 2))

        # Exponential cost: H = R^((d * gamma)^2)
        R = 2.0
        gamma = PHI
        exp_cost = R ** ((d_h * gamma) ** 2) if d_h < 5 else float("inf")

        # Face crossing costs from inner hypercube
        face_cost = self.inner.total_crossing_cost(point)

        return exp_cost + face_cost

    def classify_point(self, point: CognitivePoint) -> str:
        """
        Classify a point's position relative to the double hypercube.

        Returns:
        - "interior": Inside inner hypercube (safe zone)
        - "governance": Between inner and outer (governance zone)
        - "exterior": Outside outer hypercube (denied)
        """
        norm = point.norm()
        if norm <= self.inner.half_width:
            return "interior"
        elif norm <= self.outer.half_width:
            return "governance"
        else:
            return "exterior"

    def selective_wall_check(
        self, point: CognitivePoint, direction_tongue: str
    ) -> Tuple[bool, float]:
        """
        Check if a point can move in a specific tongue direction.

        Returns (can_pass, cost).
        This implements selective dimensional permeability:
        walls exist in some dimensions but not others.
        """
        # Check all faces for this tongue
        total_cost = 0.0
        blocked = False

        for valence in StateValence:
            for spatial in range(3):
                inner_face = self.inner.get_face(valence, spatial, direction_tongue)
                coord = point.get_coordinate(valence, spatial, direction_tongue)
                proximity = abs(coord) / self.inner.half_width if self.inner.half_width > 0 else 0

                if proximity > 0.8:
                    if inner_face.permeability <= 0.0:
                        blocked = True
                        break
                    cost = inner_face.cost_to_cross(coord)
                    total_cost += cost

            if blocked:
                break

        return (not blocked, total_cost)
