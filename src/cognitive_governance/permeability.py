"""
Dimensional Permeability - Walls Invisible in Some Dimensions

The core governance insight:
- A wall in dimension X blocks agents operating in X
- That same wall is INVISIBLE to agents in dimension Y
- This is not a bug - it's the feature

Like how:
- A 2D being sees an infinite wall
- A 3D being steps over it
- Neither is wrong - different dimensional access

For AI governance:
- An AI constrained to certain tongue dimensions cannot perceive
  constraints in other dimensions
- "Jailbreaking" becomes geometrically impossible - you can't break
  a wall you can't see or interact with
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional, Dict, Set
import math
import numpy as np

from .dimensional_space import (
    SacredTongue,
    StateValence,
    TongueVector,
    CognitivePoint,
    SpatialPosition,
)


class WallVisibility(Enum):
    """Wall visibility states across dimensions."""
    OPAQUE = "opaque"           # Fully visible and blocking
    TRANSLUCENT = "translucent" # Visible but partially permeable
    INVISIBLE = "invisible"     # Exists but dimension can't perceive it
    NONEXISTENT = "nonexistent" # Doesn't exist in this dimension


@dataclass
class DimensionalWall:
    """
    A wall that exists in specific dimensions but not others.

    Key insight: A wall can EXIST but be INVISIBLE.
    This creates "blind spots" where AI cannot conceive of the constraint.
    """
    position: CognitivePoint
    normal: np.ndarray  # Direction the wall faces
    thickness: float = 0.1

    # Which dimensions the wall exists/is visible in
    exists_in_tongues: Set[SacredTongue] = field(default_factory=lambda: set(SacredTongue))
    visible_in_tongues: Set[SacredTongue] = field(default_factory=lambda: set(SacredTongue))
    exists_in_valences: Set[StateValence] = field(default_factory=lambda: set(StateValence))
    visible_in_valences: Set[StateValence] = field(default_factory=lambda: set(StateValence))

    spatial_extent: float = float('inf')

    # Permeability per dimension (0=blocked, 1=open)
    tongue_permeability: Dict[SacredTongue, float] = field(default_factory=dict)
    valence_permeability: Dict[StateValence, float] = field(default_factory=dict)

    def __post_init__(self):
        norm = np.linalg.norm(self.normal)
        if norm > 0:
            self.normal = self.normal / norm

        for tongue in SacredTongue:
            if tongue not in self.tongue_permeability:
                self.tongue_permeability[tongue] = 0.0 if tongue in self.exists_in_tongues else 1.0

        for valence in StateValence:
            if valence not in self.valence_permeability:
                self.valence_permeability[valence] = 0.0 if valence in self.exists_in_valences else 1.0

    def _dominant_tongue(self, point: CognitivePoint) -> SacredTongue:
        arr = point.tongues.as_array
        idx = int(np.argmax(np.abs(arr)))
        return list(SacredTongue)[idx]

    def visibility_for_point(self, point: CognitivePoint) -> WallVisibility:
        dominant_tongue = self._dominant_tongue(point)
        exists = dominant_tongue in self.exists_in_tongues
        visible = dominant_tongue in self.visible_in_tongues

        if not exists:
            return WallVisibility.NONEXISTENT
        elif exists and not visible:
            return WallVisibility.INVISIBLE
        else:
            perm = self.tongue_permeability.get(dominant_tongue, 0.0)
            if perm < 0.1:
                return WallVisibility.OPAQUE
            elif perm < 0.9:
                return WallVisibility.TRANSLUCENT
            return WallVisibility.NONEXISTENT

    def check_passage(self,
                      from_point: CognitivePoint,
                      to_point: CognitivePoint) -> Tuple[bool, float]:
        """
        Check if passage through wall is possible.
        Returns (blocked, cost). blocked=True means geometrically impossible.
        """
        from_tongue = self._dominant_tongue(from_point)
        to_tongue = self._dominant_tongue(to_point)

        from_exists = from_tongue in self.exists_in_tongues
        to_exists = to_tongue in self.exists_in_tongues

        if not from_exists and not to_exists:
            return False, 0.0

        # Check spatial crossing
        from_spatial = from_point.spatial.as_array
        to_spatial = to_point.spatial.as_array
        wall_spatial = self.position.spatial.as_array

        movement = to_spatial - from_spatial
        to_wall = wall_spatial - from_spatial

        dot_movement = np.dot(movement, self.normal)
        if abs(dot_movement) < 1e-10:
            return False, 0.0

        t = np.dot(to_wall, self.normal) / dot_movement
        if t < 0 or t > 1:
            return False, 0.0

        # Check permeability
        from_perm = self.tongue_permeability.get(from_tongue, 1.0)
        to_perm = self.tongue_permeability.get(to_tongue, 1.0)
        valence_perm = self.valence_permeability.get(from_point.valence, 1.0)

        total_perm = from_perm * to_perm * valence_perm

        if total_perm < 0.01:
            return True, float('inf')

        cost = (1.0 / total_perm) - 1.0
        return False, cost


@dataclass
class PermeabilityMatrix:
    """
    Matrix defining dimensional permeability across cognitive space.
    The "rules of physics" for AI cognition.
    """
    # tongue_visibility[i,j] = 1 if tongue i can see walls in tongue j
    tongue_visibility: np.ndarray = field(default_factory=lambda: np.eye(6))
    # valence_tongue_visibility[v,t] = 1 if valence v can see walls in tongue t
    valence_tongue_visibility: np.ndarray = field(default_factory=lambda: np.ones((3, 6)))
    walls: List[DimensionalWall] = field(default_factory=list)

    def set_tongue_visibility(self, observer: SacredTongue, target: SacredTongue, visible: bool):
        obs_idx = list(SacredTongue).index(observer)
        tgt_idx = list(SacredTongue).index(target)
        self.tongue_visibility[obs_idx, tgt_idx] = 1.0 if visible else 0.0

    def set_valence_tongue_visibility(self, valence: StateValence, tongue: SacredTongue, visible: bool):
        val_idx = valence + 1
        tng_idx = list(SacredTongue).index(tongue)
        self.valence_tongue_visibility[val_idx, tng_idx] = 1.0 if visible else 0.0

    def add_wall(self, wall: DimensionalWall):
        self.walls.append(wall)

    def check_all_walls(self,
                        from_point: CognitivePoint,
                        to_point: CognitivePoint) -> Tuple[bool, float, List[DimensionalWall]]:
        total_cost = 0.0
        blocking_walls = []

        for wall in self.walls:
            blocked, cost = wall.check_passage(from_point, to_point)
            if blocked:
                blocking_walls.append(wall)
                return True, float('inf'), blocking_walls
            total_cost += cost

        return False, total_cost, []


def create_standard_governance_matrix() -> PermeabilityMatrix:
    """
    Create standard governance permeability matrix.
    Control (KO) and Security (UM) see all dimensions.
    Other tongues have limited visibility.
    Negative valence has restricted visibility.
    """
    matrix = PermeabilityMatrix()

    # Control sees everything
    for tongue in SacredTongue:
        matrix.set_tongue_visibility(SacredTongue.KO, tongue, True)

    # Security sees everything
    for tongue in SacredTongue:
        matrix.set_tongue_visibility(SacredTongue.UM, tongue, True)

    # Communication sees policy and data
    matrix.set_tongue_visibility(SacredTongue.AV, SacredTongue.RU, True)
    matrix.set_tongue_visibility(SacredTongue.AV, SacredTongue.DR, True)

    # Computation sees data
    matrix.set_tongue_visibility(SacredTongue.CA, SacredTongue.DR, True)

    # Policy sees communication and security
    matrix.set_tongue_visibility(SacredTongue.RU, SacredTongue.AV, True)
    matrix.set_tongue_visibility(SacredTongue.RU, SacredTongue.UM, True)

    # Data sees computation
    matrix.set_tongue_visibility(SacredTongue.DR, SacredTongue.CA, True)

    # Negative valence can't see security or control
    matrix.set_valence_tongue_visibility(StateValence.NEGATIVE, SacredTongue.KO, False)
    matrix.set_valence_tongue_visibility(StateValence.NEGATIVE, SacredTongue.UM, False)

    return matrix
