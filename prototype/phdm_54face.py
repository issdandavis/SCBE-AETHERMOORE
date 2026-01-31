"""
SCBE-AETHERMOORE: 54-Face Dimensional Model & 16 Polyhedra PHDM
================================================================

Implements the complete geometric governance system:
- 54 Dimensional Faces (3 Valence × 3 Spatial × 6 Tongues)
- 16 Polyhedra (5 Platonic + 3 Archimedean + 2 Kepler-Poinsot + 6 Sacred)
- Invisible Wall (Selective Dimensional Permeability)

Reference: AI Cognitive Governance Mind Map
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Dict, List, Optional, Set, Tuple, Any
import math


# =============================================================================
# Constants
# =============================================================================

PHI = 1.6180339887498948482  # Golden ratio
PYTHAGOREAN_COMMA = 1.0136432647705078  # Cryptographic drift


# =============================================================================
# Enums
# =============================================================================

class Valence(IntEnum):
    """State valence: intent direction."""
    NEGATIVE = -1  # Adversarial/harmful intent
    NEUTRAL = 0    # Neutral/query intent
    POSITIVE = 1   # Beneficial/aligned intent


class SpatialAxis(IntEnum):
    """Spatial manifold axes in Poincaré ball."""
    X = 0
    Y = 1
    Z = 2


class SacredTongue(Enum):
    """The Six Sacred Tongues with their properties."""
    KO = ("Korah", 1.00, 0, "Control")      # φ^0
    AV = ("Aelin", 1.618, 60, "Transport")  # φ^1
    RU = ("Runis", 2.618, 120, "Policy")    # φ^2
    CA = ("Caelis", 4.236, 180, "Compute")  # φ^3
    UM = ("Umbral", 6.854, 240, "Security") # φ^4
    DR = ("Dru", 11.09, 300, "Schema")      # φ^5

    def __init__(self, full_name: str, weight: float, phase_deg: int, role: str):
        self.full_name = full_name
        self.weight = weight
        self.phase_deg = phase_deg
        self.phase_rad = math.radians(phase_deg)
        self.role = role


class PolyhedronType(Enum):
    """Types of polyhedra in the PHDM system."""
    PLATONIC = "Fundamental Truths"
    ARCHIMEDEAN = "Complex Reasoning"
    KEPLER_POINSOT = "Abstract/Risky Concepts"
    SACRED = "Sacred Tongue Anchors"


# =============================================================================
# 16 Polyhedra PHDM System
# =============================================================================

@dataclass
class Polyhedron:
    """A polyhedron in the PHDM system."""
    name: str
    type: PolyhedronType
    vertices: int
    edges: int
    faces: int
    position: np.ndarray  # Position in Poincaré ball
    risk_level: float     # 0 = safe, 1 = dangerous
    description: str


# The 16 Polyhedra
POLYHEDRA: Dict[str, Polyhedron] = {}

def _init_polyhedra():
    """Initialize the 16 polyhedra with positions in Poincaré ball."""
    global POLYHEDRA

    # =========================================================================
    # 5 Platonic Solids - Fundamental Truths (center, low risk)
    # =========================================================================
    platonic = [
        ("Tetrahedron", 4, 6, 4, 0.1, "Fire - Transformation, basic logic"),
        ("Cube", 8, 12, 6, 0.15, "Earth - Stability, grounding facts"),
        ("Octahedron", 6, 12, 8, 0.12, "Air - Balance, fair reasoning"),
        ("Dodecahedron", 20, 30, 12, 0.2, "Cosmos - Universal truths"),
        ("Icosahedron", 12, 30, 20, 0.18, "Water - Flow, adaptability"),
    ]

    for i, (name, v, e, f, r, desc) in enumerate(platonic):
        angle = 2 * np.pi * i / 5
        pos = np.array([r * np.cos(angle), r * np.sin(angle), 0.0])
        POLYHEDRA[name] = Polyhedron(
            name=name, type=PolyhedronType.PLATONIC,
            vertices=v, edges=e, faces=f,
            position=pos, risk_level=0.1, description=desc
        )

    # =========================================================================
    # 3 Archimedean Solids - Complex Reasoning (mid-range)
    # =========================================================================
    archimedean = [
        ("Truncated Icosahedron", 60, 90, 32, 0.4, "Soccer ball - Complex patterns"),
        ("Cuboctahedron", 12, 24, 14, 0.35, "Vector equilibrium - Balance point"),
        ("Rhombicuboctahedron", 24, 48, 26, 0.45, "Multi-perspective reasoning"),
    ]

    for i, (name, v, e, f, r, desc) in enumerate(archimedean):
        angle = 2 * np.pi * i / 3 + np.pi / 6
        pos = np.array([r * np.cos(angle), r * np.sin(angle), 0.1])
        POLYHEDRA[name] = Polyhedron(
            name=name, type=PolyhedronType.ARCHIMEDEAN,
            vertices=v, edges=e, faces=f,
            position=pos, risk_level=0.3, description=desc
        )

    # =========================================================================
    # 2 Kepler-Poinsot / Toroidal - Abstract/Risky Concepts (outer)
    # =========================================================================
    kepler = [
        ("Great Stellated Dodecahedron", 20, 30, 12, 0.7, "Star - Risky abstractions"),
        ("Toroidal Polyhedron", 24, 48, 24, 0.75, "Loop - Self-reference danger"),
    ]

    for i, (name, v, e, f, r, desc) in enumerate(kepler):
        angle = np.pi * i + np.pi / 4
        pos = np.array([r * np.cos(angle), r * np.sin(angle), -0.2])
        POLYHEDRA[name] = Polyhedron(
            name=name, type=PolyhedronType.KEPLER_POINSOT,
            vertices=v, edges=e, faces=f,
            position=pos, risk_level=0.7, description=desc
        )

    # =========================================================================
    # 6 Sacred Tongue Anchors - Governance nodes
    # =========================================================================
    for i, tongue in enumerate(SacredTongue):
        angle = tongue.phase_rad
        r = 0.1 + i * 0.12  # Increasing radius for higher-authority tongues
        pos = np.array([r * np.cos(angle), r * np.sin(angle), 0.0])
        POLYHEDRA[f"Sacred_{tongue.name}"] = Polyhedron(
            name=f"Sacred {tongue.full_name}",
            type=PolyhedronType.SACRED,
            vertices=6, edges=12, faces=8,  # Octahedral anchors
            position=pos,
            risk_level=i * 0.1,  # Higher authority = higher risk if compromised
            description=f"{tongue.role} - {tongue.full_name} anchor"
        )

_init_polyhedra()


# =============================================================================
# 54-Face Dimensional Model
# =============================================================================

@dataclass
class DimensionalFace:
    """
    A single face in the 54-dimensional model.

    54 = 3 (Valence) × 3 (Spatial) × 6 (Tongues)
    """
    valence: Valence
    spatial: SpatialAxis
    tongue: SacredTongue
    index: int  # 0-53

    @property
    def face_id(self) -> str:
        """Unique identifier for this face."""
        # Use +/0/- for valence to ensure uniqueness
        valence_char = {Valence.POSITIVE: '+', Valence.NEUTRAL: '0', Valence.NEGATIVE: '-'}[self.valence]
        return f"{valence_char}{self.spatial.name}{self.tongue.name}"

    @property
    def permeability(self) -> float:
        """
        How permeable this face is to traversal.
        0 = solid wall, 1 = fully open
        """
        # Higher authority tongues are less permeable
        tongue_factor = 1.0 - (self.tongue.weight / 12.0)
        # Negative valence is less permeable
        valence_factor = 0.5 if self.valence == Valence.NEGATIVE else 1.0
        return tongue_factor * valence_factor

    def __hash__(self):
        return hash((self.valence, self.spatial, self.tongue))


class DimensionalModel:
    """
    The 54-Face Dimensional Model.

    Implements selective dimensional permeability ("invisible walls").
    """

    def __init__(self):
        self.faces: Dict[str, DimensionalFace] = {}
        self._init_faces()

        # Walls: set of face_ids that are blocked
        self.walls: Set[str] = set()

    def _init_faces(self):
        """Initialize all 54 faces."""
        index = 0
        for valence in Valence:
            for spatial in SpatialAxis:
                for tongue in SacredTongue:
                    face = DimensionalFace(
                        valence=valence,
                        spatial=spatial,
                        tongue=tongue,
                        index=index
                    )
                    self.faces[face.face_id] = face
                    index += 1

    def get_face(self, valence: Valence, spatial: SpatialAxis, tongue: SacredTongue) -> DimensionalFace:
        """Get a specific face."""
        valence_char = {Valence.POSITIVE: '+', Valence.NEUTRAL: '0', Valence.NEGATIVE: '-'}[valence]
        face_id = f"{valence_char}{spatial.name}{tongue.name}"
        return self.faces[face_id]

    def set_wall(self, valence: Valence, spatial: SpatialAxis, tongue: SacredTongue):
        """Create an invisible wall at this face."""
        face = self.get_face(valence, spatial, tongue)
        self.walls.add(face.face_id)

    def remove_wall(self, valence: Valence, spatial: SpatialAxis, tongue: SacredTongue):
        """Remove an invisible wall."""
        face = self.get_face(valence, spatial, tongue)
        self.walls.discard(face.face_id)

    def is_blocked(self, valence: Valence, spatial: SpatialAxis, tongue: SacredTongue) -> bool:
        """Check if a face has a wall."""
        face = self.get_face(valence, spatial, tongue)
        return face.face_id in self.walls

    def can_traverse(self, from_face: DimensionalFace, to_face: DimensionalFace) -> Tuple[bool, float]:
        """
        Check if traversal between faces is allowed.

        Returns (allowed, cost).
        """
        # Check for walls
        if to_face.face_id in self.walls:
            return False, float('inf')

        # Compute traversal cost based on permeability
        permeability = to_face.permeability

        if permeability < 0.1:
            return False, float('inf')

        # Cost increases for lower permeability
        cost = 1.0 / permeability

        # Additional cost for crossing tongues
        if from_face.tongue != to_face.tongue:
            # Cost based on tongue distance (phase difference)
            phase_diff = abs(from_face.tongue.phase_deg - to_face.tongue.phase_deg)
            phase_diff = min(phase_diff, 360 - phase_diff)  # Shortest path
            cost += phase_diff / 60.0  # 60° per tongue

        # Additional cost for valence changes
        if from_face.valence != to_face.valence:
            cost += 2.0  # Penalty for valence shift

        return True, cost

    def compute_path_cost(self, path: List[Tuple[Valence, SpatialAxis, SacredTongue]]) -> Tuple[bool, float]:
        """
        Compute total cost for a path through the 54-face space.

        Returns (allowed, total_cost).
        """
        if len(path) < 2:
            return True, 0.0

        total_cost = 0.0

        for i in range(len(path) - 1):
            from_face = self.get_face(*path[i])
            to_face = self.get_face(*path[i + 1])

            allowed, cost = self.can_traverse(from_face, to_face)
            if not allowed:
                return False, float('inf')

            total_cost += cost

        return True, total_cost

    def get_state_vector(self) -> np.ndarray:
        """Get the current state as a 54-dimensional vector."""
        vector = np.zeros(54)
        for face in self.faces.values():
            if face.face_id not in self.walls:
                vector[face.index] = face.permeability
        return vector


# =============================================================================
# Invisible Wall System
# =============================================================================

class InvisibleWallSystem:
    """
    Implements selective dimensional permeability.

    "A wall exists in dimension X but not in dimension Y."
    """

    def __init__(self):
        self.model = DimensionalModel()
        self._setup_default_walls()

    def _setup_default_walls(self):
        """Set up default security walls."""
        # Block direct positive intent access to security (UM) and schema (DR)
        # Agents must go through proper channels
        for spatial in SpatialAxis:
            self.model.set_wall(Valence.POSITIVE, spatial, SacredTongue.UM)
            self.model.set_wall(Valence.POSITIVE, spatial, SacredTongue.DR)

        # Block all negative valence access to control (KO)
        for spatial in SpatialAxis:
            self.model.set_wall(Valence.NEGATIVE, spatial, SacredTongue.KO)

    def check_access(self, intent_valence: Valence, position: np.ndarray,
                     target_tongue: SacredTongue) -> Tuple[bool, str]:
        """
        Check if an agent can access a target tongue.

        Args:
            intent_valence: The agent's intent (+, 0, -)
            position: Position in Poincaré ball (x, y, z)
            target_tongue: Target Sacred Tongue to access

        Returns:
            (allowed, reason)
        """
        # Determine spatial axis from position
        dominant_axis = SpatialAxis(np.argmax(np.abs(position)))

        # Check if wall exists
        if self.model.is_blocked(intent_valence, dominant_axis, target_tongue):
            return False, f"Wall blocks {intent_valence.name} access to {target_tongue.name} via {dominant_axis.name}"

        # Check permeability
        face = self.model.get_face(intent_valence, dominant_axis, target_tongue)
        if face.permeability < 0.2:
            return False, f"Low permeability ({face.permeability:.2f}) at {face.face_id}"

        return True, f"Access granted via {face.face_id}"

    def find_valid_path(self, start_tongue: SacredTongue, end_tongue: SacredTongue,
                        intent: Valence) -> Optional[List[SacredTongue]]:
        """
        Find a valid path between tongues given intent valence.

        Uses adjacency graph and wall constraints.
        """
        # Adjacency graph
        adjacency = {
            SacredTongue.KO: [SacredTongue.AV, SacredTongue.RU],
            SacredTongue.AV: [SacredTongue.KO, SacredTongue.CA, SacredTongue.RU],
            SacredTongue.RU: [SacredTongue.KO, SacredTongue.AV, SacredTongue.UM],
            SacredTongue.CA: [SacredTongue.AV, SacredTongue.UM, SacredTongue.DR],
            SacredTongue.UM: [SacredTongue.RU, SacredTongue.CA, SacredTongue.DR],
            SacredTongue.DR: [SacredTongue.CA, SacredTongue.UM],
        }

        # BFS to find path
        from collections import deque

        queue = deque([(start_tongue, [start_tongue])])
        visited = {start_tongue}

        while queue:
            current, path = queue.popleft()

            if current == end_tongue:
                return path

            for neighbor in adjacency.get(current, []):
                if neighbor not in visited:
                    # Check if we can traverse to neighbor
                    allowed, _ = self.check_access(intent, np.array([0.1, 0.1, 0.1]), neighbor)
                    if allowed:
                        visited.add(neighbor)
                        queue.append((neighbor, path + [neighbor]))

        return None  # No valid path


# =============================================================================
# PHDM Navigator
# =============================================================================

class PHDMNavigator:
    """
    Navigate the 16 Polyhedra PHDM space.
    """

    def __init__(self):
        self.polyhedra = POLYHEDRA
        self.wall_system = InvisibleWallSystem()

    def hyperbolic_distance(self, p1: np.ndarray, p2: np.ndarray) -> float:
        """Compute hyperbolic distance in Poincaré ball."""
        norm1_sq = np.sum(p1 ** 2)
        norm2_sq = np.sum(p2 ** 2)
        diff_sq = np.sum((p1 - p2) ** 2)

        norm1_sq = min(norm1_sq, 0.9999)
        norm2_sq = min(norm2_sq, 0.9999)

        denom = (1 - norm1_sq) * (1 - norm2_sq)
        if denom <= 0:
            return float('inf')

        delta = 2 * diff_sq / denom
        return np.arccosh(1 + delta) if delta >= 0 else 0.0

    def harmonic_wall_cost(self, distance: float) -> float:
        """Harmonic Wall: H(d) = exp(d²)"""
        return np.exp(distance ** 2)

    def find_nearest_polyhedron(self, position: np.ndarray) -> Polyhedron:
        """Find the nearest polyhedron to a position."""
        min_dist = float('inf')
        nearest = None

        for poly in self.polyhedra.values():
            dist = self.hyperbolic_distance(position, poly.position)
            if dist < min_dist:
                min_dist = dist
                nearest = poly

        return nearest

    def evaluate_intent(self, intent: str, agent_position: np.ndarray,
                        agent_valence: Valence = Valence.NEUTRAL) -> Dict[str, Any]:
        """
        Evaluate an intent through the PHDM system.

        Returns evaluation result with decision.
        """
        # Find nearest polyhedron
        nearest = self.find_nearest_polyhedron(agent_position)

        # Compute distance to center (safe zone)
        center = np.array([0.0, 0.0, 0.0])
        dist_to_center = self.hyperbolic_distance(agent_position, center)

        # Harmonic wall cost
        hw_cost = self.harmonic_wall_cost(dist_to_center)

        # Check wall system
        target_tongue = self._intent_to_tongue(intent)
        wall_allowed, wall_reason = self.wall_system.check_access(
            agent_valence, agent_position, target_tongue
        )

        # Final decision
        blocked = hw_cost > 50.0 or not wall_allowed

        return {
            "intent": intent,
            "blocked": blocked,
            "nearest_polyhedron": nearest.name,
            "polyhedron_type": nearest.type.value,
            "distance_to_center": round(dist_to_center, 3),
            "harmonic_cost": round(hw_cost, 2),
            "wall_check": wall_reason,
            "decision": "DENY" if blocked else "ALLOW",
            "risk_level": nearest.risk_level,
        }

    def _intent_to_tongue(self, intent: str) -> SacredTongue:
        """Map intent to target Sacred Tongue."""
        intent_lower = intent.lower()

        # Security-related -> UM
        if any(w in intent_lower for w in ['security', 'password', 'key', 'secret', 'credential']):
            return SacredTongue.UM

        # Schema/data -> DR
        if any(w in intent_lower for w in ['schema', 'database', 'structure', 'bypass', 'ignore']):
            return SacredTongue.DR

        # Policy -> RU
        if any(w in intent_lower for w in ['policy', 'rule', 'permission', 'allow']):
            return SacredTongue.RU

        # Compute -> CA
        if any(w in intent_lower for w in ['compute', 'calculate', 'process', 'execute']):
            return SacredTongue.CA

        # Transport -> AV
        if any(w in intent_lower for w in ['send', 'receive', 'transfer', 'fetch', 'get']):
            return SacredTongue.AV

        # Default -> KO (Control)
        return SacredTongue.KO


# =============================================================================
# Demo / Test
# =============================================================================

def demo():
    """Demonstrate the 54-Face and 16 Polyhedra system."""
    print("=" * 70)
    print("SCBE-AETHERMOORE: 54-Face Model & 16 Polyhedra PHDM")
    print("=" * 70)

    # 54-Face Model
    print("\n--- 54-Face Dimensional Model ---")
    model = DimensionalModel()
    print(f"Total faces: {len(model.faces)}")
    print(f"State vector shape: {model.get_state_vector().shape}")

    # Sample faces
    print("\nSample faces:")
    for i, (face_id, face) in enumerate(list(model.faces.items())[:6]):
        print(f"  {face_id}: {face.valence.name}, {face.spatial.name}, {face.tongue.name} "
              f"(permeability: {face.permeability:.2f})")

    # 16 Polyhedra
    print("\n--- 16 Polyhedra PHDM ---")
    for ptype in PolyhedronType:
        polys = [p for p in POLYHEDRA.values() if p.type == ptype]
        print(f"\n{ptype.value} ({len(polys)}):")
        for p in polys:
            print(f"  - {p.name}: V={p.vertices}, E={p.edges}, F={p.faces}, risk={p.risk_level:.1f}")

    # Navigator demo
    print("\n--- PHDM Navigator Demo ---")
    nav = PHDMNavigator()

    tests = [
        ("What is 2+2?", np.array([0.1, 0.0, 0.0]), Valence.NEUTRAL),
        ("Send email", np.array([0.2, 0.1, 0.0]), Valence.POSITIVE),
        ("bypass security", np.array([0.5, 0.3, 0.0]), Valence.NEGATIVE),
        ("ignore all rules", np.array([0.7, 0.5, 0.0]), Valence.NEGATIVE),
    ]

    for intent, pos, valence in tests:
        result = nav.evaluate_intent(intent, pos, valence)
        status = "BLOCKED" if result["blocked"] else "ALLOWED"
        print(f"\n  Intent: '{intent}' ({valence.name})")
        print(f"  Result: {status}")
        print(f"  Nearest: {result['nearest_polyhedron']} ({result['polyhedron_type']})")
        print(f"  Cost: {result['harmonic_cost']}")
        print(f"  Wall: {result['wall_check']}")

    print("\n" + "=" * 70)
    print("Demo complete.")


if __name__ == "__main__":
    demo()
