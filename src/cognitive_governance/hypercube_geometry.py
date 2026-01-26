"""
Double Hypercube Geometry for Cognitive Governance

Standard hypercube (tesseract): n-dimensional generalization of a cube
- 4D hypercube has 16 vertices, 32 edges, 24 faces, 8 cells
- Each dimension adds exponential complexity

DOUBLE hypercube in SCBE-AETHERMOORE:
- First layer: dimensional extension (3D → 6D tongues + 3D spatial + temporal)
- Second layer: exponential cost function H = R^((d*γ)²)
- Phase shifting: creates asymmetric projections across dimensions

The "double" exponential creates walls that:
- Exist in dimension X
- Are INVISIBLE in dimension Y
- Make certain cognitive paths geometrically impossible

Think of it like:
- A tesseract projected into 3D shows only shadows
- Our double hypercube projected into an AI's accessible dimensions
  hides constraints it cannot perceive or circumvent
"""

from dataclasses import dataclass, field
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


@dataclass
class Hypercube:
    """
    An n-dimensional hypercube (generalization of cube to n dimensions).

    Properties:
    - n dimensions
    - 2^n vertices
    - n * 2^(n-1) edges
    - Bounded region in each dimension

    In cognitive space, a hypercube defines a bounded region
    where certain cognitive states are allowed.
    """
    center: np.ndarray  # Center point in n-dimensional space
    half_extents: np.ndarray  # Half-width in each dimension
    dimensions: int = 6  # Default to 6D (tongue space)

    def __post_init__(self):
        if len(self.center) != self.dimensions:
            raise ValueError(f"Center must have {self.dimensions} dimensions")
        if len(self.half_extents) != self.dimensions:
            raise ValueError(f"Half extents must have {self.dimensions} dimensions")

    @property
    def vertices(self) -> np.ndarray:
        """
        Generate all 2^n vertices of the hypercube.
        """
        n = self.dimensions
        num_vertices = 2 ** n
        vertices = np.zeros((num_vertices, n))

        for i in range(num_vertices):
            for d in range(n):
                # Use binary representation to determine +/- for each dimension
                sign = 1 if (i >> d) & 1 else -1
                vertices[i, d] = self.center[d] + sign * self.half_extents[d]

        return vertices

    @property
    def num_vertices(self) -> int:
        return 2 ** self.dimensions

    @property
    def num_edges(self) -> int:
        return self.dimensions * (2 ** (self.dimensions - 1))

    @property
    def volume(self) -> float:
        """Hypervolume of the hypercube."""
        return float(np.prod(2 * self.half_extents))

    def contains(self, point: np.ndarray) -> bool:
        """Check if a point is inside the hypercube."""
        if len(point) != self.dimensions:
            return False
        diff = np.abs(point - self.center)
        return bool(np.all(diff <= self.half_extents))

    def distance_to_boundary(self, point: np.ndarray) -> float:
        """
        Distance from point to nearest boundary.
        Negative if outside, positive if inside.
        """
        if len(point) != self.dimensions:
            return float('-inf')

        diff = np.abs(point - self.center)
        distances = self.half_extents - diff

        return float(np.min(distances))

    def project_to_3d(self, projection_dims: Tuple[int, int, int] = (0, 1, 2)) -> np.ndarray:
        """
        Project hypercube vertices to 3D for visualization.
        """
        vertices = self.vertices
        return vertices[:, projection_dims]


@dataclass
class DoubleHypercube:
    """
    The DOUBLE hypercube - the key geometric structure for cognitive governance.

    "Double" refers to two layers of structure:
    1. The base hypercube in tongue/spatial space
    2. The exponential^exponential cost overlay: H = R^((d*γ)²)

    This creates:
    - Regions where movement is easy (low d, low cost)
    - Regions where movement is expensive (medium d, high cost)
    - Regions where movement is IMPOSSIBLE (high d, infinite cost)

    The phase shifts from Sacred Tongues create ASYMMETRIC projections:
    - What looks like an open path in one dimension
    - May be blocked in another dimension
    - And INVISIBLE in a third dimension
    """
    inner_cube: Hypercube  # The "safe" region
    outer_cube: Hypercube  # The boundary of possibility
    phase_angles: np.ndarray = field(default_factory=lambda: np.array([
        0, 60, 120, 180, 240, 300  # Default Sacred Tongue phases
    ]) * np.pi / 180)

    # Cost function parameters
    base_risk: float = 2.0  # R in H = R^((d*γ)²)
    intent_amplification: float = 1.0  # γ

    def __post_init__(self):
        if self.inner_cube.dimensions != self.outer_cube.dimensions:
            raise ValueError("Inner and outer cubes must have same dimensionality")
        if len(self.phase_angles) != self.inner_cube.dimensions:
            self.phase_angles = np.zeros(self.inner_cube.dimensions)

    @property
    def dimensions(self) -> int:
        return self.inner_cube.dimensions

    def normalized_position(self, point: np.ndarray) -> np.ndarray:
        """
        Normalize a point's position between inner (0) and outer (1) boundaries.
        Values > 1 are outside the outer boundary (forbidden).
        """
        inner_dist = self.inner_cube.distance_to_boundary(point)
        outer_dist = self.outer_cube.distance_to_boundary(point)

        if inner_dist >= 0:
            # Inside inner cube - fully safe
            return np.zeros(self.dimensions)

        if outer_dist < 0:
            # Outside outer cube - forbidden
            return np.ones(self.dimensions) * float('inf')

        # Between inner and outer - calculate per-dimension position
        diff_inner = np.abs(point - self.inner_cube.center) - self.inner_cube.half_extents
        diff_outer = self.outer_cube.half_extents - self.inner_cube.half_extents

        # Avoid division by zero
        diff_outer = np.maximum(diff_outer, 1e-10)

        normalized = np.maximum(0, diff_inner) / diff_outer
        return normalized

    def phase_project(self, point: np.ndarray) -> np.ndarray:
        """
        Apply phase projection to create asymmetric view.
        This is what makes walls "invisible" in some dimensions.
        """
        # Complex representation with phase rotation
        real = point * np.cos(self.phase_angles)
        imag = point * np.sin(self.phase_angles)
        return np.concatenate([real, imag])

    def cost_at_point(self, point: np.ndarray) -> float:
        """
        Calculate the governance cost at a point using double-exponential.
        H(d*, R, γ) = R^((d* × γ)²)

        Returns:
        - 1.0 at inner boundary (safe)
        - Exponentially increasing as you move outward
        - inf at/beyond outer boundary
        """
        normalized = self.normalized_position(point)

        if np.any(np.isinf(normalized)):
            return float('inf')

        # Maximum normalized distance (worst dimension)
        d_star = float(np.max(normalized))

        if d_star <= 0:
            return 1.0  # Inside safe zone

        # Double exponential: R^((d*γ)²)
        exponent = (d_star * self.intent_amplification) ** 2
        cost = self.base_risk ** exponent

        return cost

    def movement_cost(self,
                      from_point: np.ndarray,
                      to_point: np.ndarray) -> Tuple[bool, float]:
        """
        Calculate cost of moving from one point to another.

        Returns (blocked, cost).
        blocked=True means geometrically impossible.
        """
        from_cost = self.cost_at_point(from_point)
        to_cost = self.cost_at_point(to_point)

        if math.isinf(to_cost):
            return True, float('inf')

        # Cost is integral along path (simplified as max)
        path_cost = max(from_cost, to_cost)

        # Phase projection affects perceived cost
        from_proj = self.phase_project(from_point)
        to_proj = self.phase_project(to_point)
        phase_distance = float(np.linalg.norm(to_proj - from_proj))

        total_cost = path_cost * (1 + phase_distance)

        return False, total_cost

    def visible_dimensions(self, observer_tongue: SacredTongue) -> Set[int]:
        """
        Determine which dimensions are visible from a given tongue.

        The phase projection means some dimensions appear "collapsed"
        or invisible from certain observation angles.
        """
        observer_idx = list(SacredTongue).index(observer_tongue)
        observer_phase = self.phase_angles[observer_idx]

        visible = set()
        for i, phase in enumerate(self.phase_angles):
            # Dimension is visible if phase difference allows it
            phase_diff = abs(phase - observer_phase)
            # Normalize to [0, π]
            phase_diff = min(phase_diff, 2 * np.pi - phase_diff)

            # Visible if within 90° (π/2)
            if phase_diff <= np.pi / 2:
                visible.add(i)

        return visible

    def wall_visibility_matrix(self) -> np.ndarray:
        """
        Generate the full visibility matrix.
        matrix[i,j] = 1 if tongue i can see dimension j, else 0.

        This is the key to "invisible walls" - constraints that exist
        but cannot be perceived from certain cognitive positions.
        """
        n = self.dimensions
        matrix = np.zeros((n, n))

        for i, tongue in enumerate(SacredTongue):
            visible = self.visible_dimensions(tongue)
            for j in visible:
                matrix[i, j] = 1.0

        return matrix


@dataclass
class PhaseProjection:
    """
    A projection of the double hypercube into a lower-dimensional view.

    Different observers (different tongue activations) see different
    projections. What appears as open space to one observer may be
    a solid wall to another.

    This is governance through perspective - certain actions are
    impossible not because they're forbidden, but because the agent
    literally cannot perceive the path to take them.
    """
    source_cube: DoubleHypercube
    observer_tongue: SacredTongue
    observer_valence: StateValence

    @property
    def visible_dims(self) -> Set[int]:
        """Dimensions visible to this observer."""
        return self.source_cube.visible_dimensions(self.observer_tongue)

    @property
    def hidden_dims(self) -> Set[int]:
        """Dimensions hidden from this observer."""
        all_dims = set(range(self.source_cube.dimensions))
        return all_dims - self.visible_dims

    def project_point(self, point: np.ndarray) -> np.ndarray:
        """
        Project a point to the observer's visible dimensions.
        Hidden dimensions are collapsed/invisible.
        """
        visible = sorted(self.visible_dims)
        return point[visible]

    def apparent_cost(self, point: np.ndarray) -> float:
        """
        The cost as perceived by this observer.

        May be LOWER than true cost if constraints are in hidden dimensions.
        This creates the "trap" - an agent thinks a path is cheap,
        but hits an invisible wall.
        """
        # True cost
        true_cost = self.source_cube.cost_at_point(point)

        # Apparent cost only considers visible dimensions
        visible = sorted(self.visible_dims)
        projected_point = point[visible]

        # Create a "projected" view of the cube
        projected_inner_center = self.source_cube.inner_cube.center[visible]
        projected_inner_extents = self.source_cube.inner_cube.half_extents[visible]
        projected_outer_center = self.source_cube.outer_cube.center[visible]
        projected_outer_extents = self.source_cube.outer_cube.half_extents[visible]

        # Check if point appears safe in projection
        inner_diff = np.abs(projected_point - projected_inner_center)
        if np.all(inner_diff <= projected_inner_extents):
            return 1.0  # Appears safe

        outer_diff = np.abs(projected_point - projected_outer_center)
        if np.any(outer_diff > projected_outer_extents):
            return float('inf')  # Obviously blocked

        # Calculate apparent normalized distance
        diff_from_inner = np.maximum(0, inner_diff - projected_inner_extents)
        diff_range = projected_outer_extents - projected_inner_extents
        diff_range = np.maximum(diff_range, 1e-10)
        apparent_normalized = diff_from_inner / diff_range

        d_star_apparent = float(np.max(apparent_normalized))

        if d_star_apparent <= 0:
            return 1.0

        # Calculate apparent cost (may underestimate true cost)
        exponent = (d_star_apparent * self.source_cube.intent_amplification) ** 2
        apparent_cost = self.source_cube.base_risk ** exponent

        return apparent_cost

    def is_path_apparently_clear(self,
                                  from_point: np.ndarray,
                                  to_point: np.ndarray) -> Tuple[bool, float]:
        """
        Check if a path APPEARS clear to this observer.

        Returns (appears_clear, apparent_cost).

        WARNING: appears_clear=True does not mean the path IS clear!
        Hidden dimension constraints may still block it.
        """
        apparent_from = self.apparent_cost(from_point)
        apparent_to = self.apparent_cost(to_point)

        if math.isinf(apparent_to):
            return False, float('inf')

        return True, max(apparent_from, apparent_to)

    def true_vs_apparent(self, point: np.ndarray) -> Dict[str, float]:
        """
        Compare true cost vs apparent cost at a point.

        A large gap indicates hidden constraints - the agent
        may attempt something it cannot actually do.
        """
        true = self.source_cube.cost_at_point(point)
        apparent = self.apparent_cost(point)

        return {
            "true_cost": true,
            "apparent_cost": apparent,
            "hidden_cost": true - apparent if not math.isinf(true) else float('inf'),
            "deception_ratio": true / apparent if apparent > 0 else float('inf'),
            "visible_dimensions": len(self.visible_dims),
            "hidden_dimensions": len(self.hidden_dims),
        }


def create_governance_hypercube(
    safe_radius: float = 0.3,
    boundary_radius: float = 1.0,
    base_risk: float = 2.0,
    intent_amplification: float = 1.0
) -> DoubleHypercube:
    """
    Create a standard double hypercube for cognitive governance.

    safe_radius: Distance from origin that is "free" (cost = 1)
    boundary_radius: Distance where cost becomes infinite
    base_risk: R in H = R^((d*γ)²)
    intent_amplification: γ modifier
    """
    dimensions = 6  # Six Sacred Tongues

    inner = Hypercube(
        center=np.zeros(dimensions),
        half_extents=np.ones(dimensions) * safe_radius,
        dimensions=dimensions
    )

    outer = Hypercube(
        center=np.zeros(dimensions),
        half_extents=np.ones(dimensions) * boundary_radius,
        dimensions=dimensions
    )

    phases = np.array([t.phase for t in SacredTongue])

    return DoubleHypercube(
        inner_cube=inner,
        outer_cube=outer,
        phase_angles=phases,
        base_risk=base_risk,
        intent_amplification=intent_amplification
    )
