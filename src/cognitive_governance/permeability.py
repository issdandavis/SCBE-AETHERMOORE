"""
Dimensional Permeability for Cognitive Governance
=================================================

Implements selective dimensional permeability - the concept that
governance walls exist in some dimensions but are invisible in others.

Example: An AI agent might freely read data (KO tongue permeable)
but be blocked from modifying security settings (UM tongue impermeable).
The wall is real in the security dimension but doesn't exist in the
read dimension.

@module cognitive_governance/permeability
@layer L6-L7 (Breathing transform, Mobius phase)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .dimensional_space import TONGUE_NAMES, TONGUES, CognitivePoint, StateValence


class WallVisibility(Enum):
    """How a wall appears in a given dimension."""

    INVISIBLE = 0  # Wall doesn't exist in this dimension
    TRANSLUCENT = 1  # Wall exists but can be crossed with cost
    OPAQUE = 2  # Wall exists and blocks passage
    REFLECTIVE = 3  # Wall exists and reverses momentum


@dataclass
class DimensionalWall:
    """
    A wall that exists in some dimensions but not others.

    This is the key innovation of the hypercube governance model:
    selective dimensional permeability. A wall can be:
    - Invisible in the KO (Control) dimension
    - Translucent in the RU (Policy) dimension
    - Opaque in the UM (Security) dimension
    - Reflective in the DR (Structure) dimension

    This means an agent can freely control (KO) while being
    blocked from security operations (UM).
    """

    wall_id: str
    # Visibility per tongue dimension
    visibility: Dict[str, WallVisibility] = field(
        default_factory=lambda: {t: WallVisibility.TRANSLUCENT for t in TONGUE_NAMES}
    )
    # Position along the dimension (0.0 = center, 1.0 = boundary)
    position: float = 0.5
    # Base cost to cross (when translucent)
    base_cost: float = 1.0
    # Description of what this wall protects
    description: str = ""

    def get_visibility(self, tongue: str) -> WallVisibility:
        """Get visibility in a specific tongue dimension."""
        return self.visibility.get(tongue, WallVisibility.TRANSLUCENT)

    def set_visibility(self, tongue: str, vis: WallVisibility):
        """Set visibility for a specific tongue dimension."""
        self.visibility[tongue] = vis

    def crossing_cost(self, tongue: str, momentum: float = 0.0) -> float:
        """
        Cost to cross this wall in a specific tongue dimension.

        Returns:
        - 0.0 for INVISIBLE walls
        - base_cost * tongue_weight for TRANSLUCENT
        - inf for OPAQUE
        - inf for REFLECTIVE (plus momentum reversal)
        """
        vis = self.get_visibility(tongue)
        if vis == WallVisibility.INVISIBLE:
            return 0.0
        elif vis == WallVisibility.OPAQUE or vis == WallVisibility.REFLECTIVE:
            return float("inf")
        else:  # TRANSLUCENT
            weight = TONGUES[tongue]["weight"]
            return self.base_cost * weight * (1.0 + abs(momentum))

    def can_cross(self, tongue: str) -> bool:
        """Check if crossing is possible in a specific tongue dimension."""
        vis = self.get_visibility(tongue)
        return vis in (WallVisibility.INVISIBLE, WallVisibility.TRANSLUCENT)

    def visible_dimensions(self) -> List[str]:
        """Return tongues where this wall is visible (not invisible)."""
        return [t for t in TONGUE_NAMES if self.visibility[t] != WallVisibility.INVISIBLE]

    def invisible_dimensions(self) -> List[str]:
        """Return tongues where this wall is invisible."""
        return [t for t in TONGUE_NAMES if self.visibility[t] == WallVisibility.INVISIBLE]


@dataclass
class PermeabilityMatrix:
    """
    Full permeability matrix for the governance space.

    Maps every (wall, tongue) pair to a crossing cost.
    Used to quickly evaluate whether an agent's action can
    proceed in a specific direction.

    The matrix captures the non-commutative nature of the space:
    crossing wall A then wall B may have different cost than
    crossing wall B then wall A (T o I != I o T).
    """

    walls: List[DimensionalWall] = field(default_factory=list)
    # Cache of computed costs
    _cost_cache: Dict[Tuple[str, str], float] = field(default_factory=dict, repr=False)

    def add_wall(self, wall: DimensionalWall):
        """Add a wall to the permeability matrix."""
        self.walls.append(wall)
        self._cost_cache.clear()

    def remove_wall(self, wall_id: str):
        """Remove a wall by ID."""
        self.walls = [w for w in self.walls if w.wall_id != wall_id]
        self._cost_cache.clear()

    def get_wall(self, wall_id: str) -> Optional[DimensionalWall]:
        """Get a wall by ID."""
        for w in self.walls:
            if w.wall_id == wall_id:
                return w
        return None

    def total_cost(self, tongue: str, momentum: float = 0.0) -> float:
        """
        Total cost to move through all walls in a specific tongue dimension.

        If any wall is opaque in this dimension, cost is infinite.
        """
        cache_key = (tongue, f"{momentum:.4f}")
        if cache_key in self._cost_cache:
            return self._cost_cache[cache_key]

        total = 0.0
        for wall in self.walls:
            cost = wall.crossing_cost(tongue, momentum)
            if cost == float("inf"):
                self._cost_cache[cache_key] = float("inf")
                return float("inf")
            total += cost

        self._cost_cache[cache_key] = total
        return total

    def can_traverse(self, tongue: str) -> bool:
        """Check if any path exists through all walls for this tongue."""
        return all(w.can_cross(tongue) for w in self.walls)

    def passable_tongues(self) -> List[str]:
        """Return tongues that can traverse all walls."""
        return [t for t in TONGUE_NAMES if self.can_traverse(t)]

    def blocked_tongues(self) -> List[str]:
        """Return tongues blocked by at least one wall."""
        return [t for t in TONGUE_NAMES if not self.can_traverse(t)]

    def cheapest_tongue(self, momentum: float = 0.0) -> Tuple[str, float]:
        """Find the tongue with the lowest total crossing cost."""
        best_tongue = TONGUE_NAMES[0]
        best_cost = float("inf")
        for tongue in TONGUE_NAMES:
            cost = self.total_cost(tongue, momentum)
            if cost < best_cost:
                best_cost = cost
                best_tongue = tongue
        return best_tongue, best_cost

    def evaluate_point(self, point: CognitivePoint) -> Dict[str, float]:
        """
        Evaluate crossing costs for a cognitive point across all tongue dimensions.

        Returns a dict mapping tongue -> total cost for that point's movement.
        """
        result = {}
        for tongue in TONGUE_NAMES:
            # Use the dominant coordinate for this tongue as momentum
            momentum = max(abs(point.get_coordinate(v, s, tongue)) for v in StateValence for s in range(3))
            result[tongue] = self.total_cost(tongue, momentum)
        return result

    def non_commutative_cost(
        self, wall_a_id: str, wall_b_id: str, tongue: str, momentum: float = 0.0
    ) -> Tuple[float, float]:
        """
        Demonstrate non-commutativity: cost(A then B) vs cost(B then A).

        After crossing wall A, momentum changes, affecting cost of wall B.
        T o I != I o T (order of operations matters).

        Returns (cost_AB, cost_BA).
        """
        wall_a = self.get_wall(wall_a_id)
        wall_b = self.get_wall(wall_b_id)
        if not wall_a or not wall_b:
            return (float("inf"), float("inf"))

        # A then B
        cost_a1 = wall_a.crossing_cost(tongue, momentum)
        if cost_a1 == float("inf"):
            cost_ab = float("inf")
        else:
            # Momentum increases after crossing A
            new_momentum_ab = momentum + cost_a1 * 0.1
            cost_b1 = wall_b.crossing_cost(tongue, new_momentum_ab)
            cost_ab = cost_a1 + cost_b1

        # B then A
        cost_b2 = wall_b.crossing_cost(tongue, momentum)
        if cost_b2 == float("inf"):
            cost_ba = float("inf")
        else:
            new_momentum_ba = momentum + cost_b2 * 0.1
            cost_a2 = wall_a.crossing_cost(tongue, new_momentum_ba)
            cost_ba = cost_b2 + cost_a2

        return (cost_ab, cost_ba)


def create_security_walls() -> PermeabilityMatrix:
    """
    Create a standard set of security walls for governance.

    Default configuration:
    1. Read wall: invisible in KO/AV, translucent elsewhere
    2. Write wall: opaque in UM/DR, translucent elsewhere
    3. Execute wall: opaque in UM/DR, reflective in CA
    4. Admin wall: opaque everywhere except KO
    """
    matrix = PermeabilityMatrix()

    # Read wall - mostly permeable
    read_wall = DimensionalWall(wall_id="read", position=0.3, base_cost=0.5, description="Read operations")
    read_wall.set_visibility("KO", WallVisibility.INVISIBLE)
    read_wall.set_visibility("AV", WallVisibility.INVISIBLE)
    read_wall.set_visibility("RU", WallVisibility.TRANSLUCENT)
    read_wall.set_visibility("CA", WallVisibility.TRANSLUCENT)
    read_wall.set_visibility("UM", WallVisibility.TRANSLUCENT)
    read_wall.set_visibility("DR", WallVisibility.TRANSLUCENT)
    matrix.add_wall(read_wall)

    # Write wall - restricted in security dimensions
    write_wall = DimensionalWall(wall_id="write", position=0.5, base_cost=1.0, description="Write operations")
    write_wall.set_visibility("KO", WallVisibility.TRANSLUCENT)
    write_wall.set_visibility("AV", WallVisibility.TRANSLUCENT)
    write_wall.set_visibility("RU", WallVisibility.TRANSLUCENT)
    write_wall.set_visibility("CA", WallVisibility.TRANSLUCENT)
    write_wall.set_visibility("UM", WallVisibility.OPAQUE)
    write_wall.set_visibility("DR", WallVisibility.OPAQUE)
    matrix.add_wall(write_wall)

    # Execute wall - heavily restricted
    exec_wall = DimensionalWall(wall_id="execute", position=0.7, base_cost=2.0, description="Execute operations")
    exec_wall.set_visibility("KO", WallVisibility.TRANSLUCENT)
    exec_wall.set_visibility("AV", WallVisibility.TRANSLUCENT)
    exec_wall.set_visibility("RU", WallVisibility.TRANSLUCENT)
    exec_wall.set_visibility("CA", WallVisibility.REFLECTIVE)
    exec_wall.set_visibility("UM", WallVisibility.OPAQUE)
    exec_wall.set_visibility("DR", WallVisibility.OPAQUE)
    matrix.add_wall(exec_wall)

    # Admin wall - almost everything blocked
    admin_wall = DimensionalWall(wall_id="admin", position=0.9, base_cost=5.0, description="Admin operations")
    admin_wall.set_visibility("KO", WallVisibility.TRANSLUCENT)
    admin_wall.set_visibility("AV", WallVisibility.OPAQUE)
    admin_wall.set_visibility("RU", WallVisibility.OPAQUE)
    admin_wall.set_visibility("CA", WallVisibility.OPAQUE)
    admin_wall.set_visibility("UM", WallVisibility.OPAQUE)
    admin_wall.set_visibility("DR", WallVisibility.OPAQUE)
    matrix.add_wall(admin_wall)

    return matrix
