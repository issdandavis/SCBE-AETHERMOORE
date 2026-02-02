"""
Hyperbolic Octree - Sparse Voxel Storage in Poincare Ball
=========================================================

Stores data in a sparse octree structure within the Poincare ball model
of hyperbolic space. Uses true hyperbolic distance for spatial queries.

Key Features:
- Octree subdivision respects Poincare disk boundaries
- Hyperbolic distance metrics (not Euclidean)
- Golden ratio (phi) weighting for depth levels
- Integration with Sacred Tongues coordinate system

Based on SCBE-AETHERMOORE's geometric AI safety architecture.

@layer Layer 5 (Hyperbolic Distance), Layer 8 (Multi-well Realms)
@component VoxelStorage
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Generator
from dataclasses import dataclass, field
from enum import Enum
import hashlib


# =============================================================================
# Constants
# =============================================================================

PHI = (1 + np.sqrt(5)) / 2  # Golden ratio
POINCARE_RADIUS = 1.0  # Boundary of Poincare ball (infinite distance)
EPSILON = 1e-10  # Numerical stability


class SacredTongue(str, Enum):
    """The 6 Sacred Tongues mapped to octant directions."""
    KO = "KO"  # +X+Y+Z - Intent/Purpose (center tendency)
    AV = "AV"  # +X+Y-Z - Context/Wisdom
    RU = "RU"  # +X-Y+Z - Binding/Structure
    CA = "CA"  # +X-Y-Z - Bitcraft/Precision
    UM = "UM"  # -X+Y+Z - Hidden/Mystery
    DR = "DR"  # -X+Y-Z - Nature/Flow


# Octant to Sacred Tongue mapping
OCTANT_TONGUES = {
    (1, 1, 1): SacredTongue.KO,
    (1, 1, -1): SacredTongue.AV,
    (1, -1, 1): SacredTongue.RU,
    (1, -1, -1): SacredTongue.CA,
    (-1, 1, 1): SacredTongue.UM,
    (-1, 1, -1): SacredTongue.DR,
    (-1, -1, 1): SacredTongue.KO,  # Mirror
    (-1, -1, -1): SacredTongue.DR,  # Mirror
}

# Tongue weights (golden ratio powers)
TONGUE_WEIGHTS = {
    SacredTongue.KO: PHI ** 0,  # 1.000
    SacredTongue.AV: PHI ** 1,  # 1.618
    SacredTongue.RU: PHI ** 2,  # 2.618
    SacredTongue.CA: PHI ** 3,  # 4.236
    SacredTongue.UM: PHI ** 4,  # 6.854
    SacredTongue.DR: PHI ** 5,  # 11.090
}


# =============================================================================
# Hyperbolic Distance Functions
# =============================================================================

def poincare_distance(p1: np.ndarray, p2: np.ndarray) -> float:
    """
    Compute hyperbolic distance between two points in the Poincare ball.

    d(p1, p2) = arcosh(1 + 2 * ||p1 - p2||^2 / ((1 - ||p1||^2)(1 - ||p2||^2)))

    Properties:
    - Distance grows exponentially toward boundary
    - Center (origin) is equidistant from all boundary points
    - Geodesics are arcs (not straight lines)
    """
    p1 = np.asarray(p1, dtype=np.float64)
    p2 = np.asarray(p2, dtype=np.float64)

    # Clamp to stay inside ball
    norm1_sq = np.sum(p1 ** 2)
    norm2_sq = np.sum(p2 ** 2)

    if norm1_sq >= POINCARE_RADIUS:
        p1 = p1 * (POINCARE_RADIUS - EPSILON) / np.sqrt(norm1_sq)
        norm1_sq = np.sum(p1 ** 2)

    if norm2_sq >= POINCARE_RADIUS:
        p2 = p2 * (POINCARE_RADIUS - EPSILON) / np.sqrt(norm2_sq)
        norm2_sq = np.sum(p2 ** 2)

    diff_sq = np.sum((p1 - p2) ** 2)

    denom = (1 - norm1_sq) * (1 - norm2_sq)
    if denom < EPSILON:
        return float('inf')

    arg = 1 + 2 * diff_sq / denom

    # arcosh(x) = ln(x + sqrt(x^2 - 1))
    if arg <= 1:
        return 0.0

    return np.arccosh(arg)


def weighted_poincare_distance(p1: np.ndarray, p2: np.ndarray,
                                weights: np.ndarray = None) -> float:
    """
    Weighted hyperbolic distance using Sacred Tongue weights.

    Applies dimensional scaling before computing distance,
    making certain dimensions "heavier" (more significant).
    """
    if weights is None:
        weights = np.ones(len(p1))

    p1_weighted = p1 * weights
    p2_weighted = p2 * weights

    # Renormalize to stay in ball
    norm1 = np.linalg.norm(p1_weighted)
    norm2 = np.linalg.norm(p2_weighted)

    if norm1 >= POINCARE_RADIUS:
        p1_weighted *= (POINCARE_RADIUS - EPSILON) / norm1
    if norm2 >= POINCARE_RADIUS:
        p2_weighted *= (POINCARE_RADIUS - EPSILON) / norm2

    return poincare_distance(p1_weighted, p2_weighted)


def mobius_addition(p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    """
    Mobius addition in the Poincare ball.

    p1 (+) p2 = ((1 + 2<p1,p2> + ||p2||^2)p1 + (1 - ||p1||^2)p2) /
                (1 + 2<p1,p2> + ||p1||^2||p2||^2)

    This is how "translation" works in hyperbolic space.
    """
    p1 = np.asarray(p1, dtype=np.float64)
    p2 = np.asarray(p2, dtype=np.float64)

    dot = np.dot(p1, p2)
    norm1_sq = np.sum(p1 ** 2)
    norm2_sq = np.sum(p2 ** 2)

    numer = (1 + 2 * dot + norm2_sq) * p1 + (1 - norm1_sq) * p2
    denom = 1 + 2 * dot + norm1_sq * norm2_sq

    result = numer / (denom + EPSILON)

    # Clamp to ball
    norm = np.linalg.norm(result)
    if norm >= POINCARE_RADIUS:
        result *= (POINCARE_RADIUS - EPSILON) / norm

    return result


def geodesic_midpoint(p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    """
    Find the midpoint along the geodesic between p1 and p2.

    In hyperbolic space, the midpoint is NOT the Euclidean midpoint.
    """
    # Transform to place p1 at origin (gyrovector space)
    # Then find midpoint, then transform back

    # Simplified: use weighted average with correction
    mid_euclidean = (p1 + p2) / 2

    # Apply hyperbolic correction factor
    norm1_sq = np.sum(p1 ** 2)
    norm2_sq = np.sum(p2 ** 2)

    # Correction pulls midpoint toward center
    correction = 1 - (norm1_sq + norm2_sq) / 4

    result = mid_euclidean * correction

    # Ensure inside ball
    norm = np.linalg.norm(result)
    if norm >= POINCARE_RADIUS:
        result *= (POINCARE_RADIUS - EPSILON) / norm

    return result


# =============================================================================
# Voxel Data Structure
# =============================================================================

@dataclass
class Voxel:
    """
    A single voxel in the hyperbolic octree.

    Attributes:
        position: 3D coordinate in Poincare ball
        data: Arbitrary payload
        tongue: Dominant Sacred Tongue for this region
        hyperbolic_depth: True depth in hyperbolic space
        trust_score: SCBE trust level (0-1)
    """
    position: np.ndarray
    data: Any = None
    tongue: SacredTongue = SacredTongue.KO
    hyperbolic_depth: float = 0.0
    trust_score: float = 1.0

    def __post_init__(self):
        self.position = np.asarray(self.position, dtype=np.float64)
        if len(self.position) != 3:
            raise ValueError("Voxel position must be 3D")

        # Compute hyperbolic depth from origin
        self.hyperbolic_depth = poincare_distance(
            np.zeros(3), self.position
        )

        # Determine dominant tongue from position
        self.tongue = self._determine_tongue()

        # Trust decreases with hyperbolic distance (closer to boundary = less trust)
        self.trust_score = max(0.0, 1.0 - self.hyperbolic_depth / 3.0)

    def _determine_tongue(self) -> SacredTongue:
        """Determine Sacred Tongue from octant."""
        signs = tuple(1 if x >= 0 else -1 for x in self.position)
        return OCTANT_TONGUES.get(signs, SacredTongue.KO)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "position": self.position.tolist(),
            "data": self.data,
            "tongue": self.tongue.value,
            "hyperbolic_depth": self.hyperbolic_depth,
            "trust_score": self.trust_score,
        }


# =============================================================================
# Octree Node
# =============================================================================

@dataclass
class OctreeNode:
    """
    A node in the hyperbolic octree.

    Uses axis-aligned bounding boxes but with hyperbolic distance metrics.
    Each node can have up to 8 children (octants).
    """
    min_corner: np.ndarray  # Minimum corner of bounding box
    max_corner: np.ndarray  # Maximum corner of bounding box
    depth: int = 0
    max_depth: int = 6

    children: Optional[List['OctreeNode']] = None
    voxels: List[Voxel] = field(default_factory=list)
    max_voxels_per_node: int = 8  # Split threshold

    # Cached properties
    _center: np.ndarray = field(default=None, repr=False)
    _hyperbolic_radius: float = field(default=None, repr=False)

    def __post_init__(self):
        self.min_corner = np.asarray(self.min_corner, dtype=np.float64)
        self.max_corner = np.asarray(self.max_corner, dtype=np.float64)

        # Compute center
        self._center = (self.min_corner + self.max_corner) / 2

        # Compute hyperbolic "radius" (distance from center to corner)
        self._hyperbolic_radius = poincare_distance(
            self._center, self.max_corner
        )

    @property
    def center(self) -> np.ndarray:
        return self._center

    @property
    def hyperbolic_radius(self) -> float:
        return self._hyperbolic_radius

    @property
    def is_leaf(self) -> bool:
        return self.children is None

    @property
    def tongue(self) -> SacredTongue:
        """Dominant tongue for this node based on center position."""
        signs = tuple(1 if x >= 0 else -1 for x in self._center)
        return OCTANT_TONGUES.get(signs, SacredTongue.KO)

    def contains(self, point: np.ndarray) -> bool:
        """Check if point is inside this node's bounding box."""
        return np.all(point >= self.min_corner) and np.all(point <= self.max_corner)

    def hyperbolic_contains(self, point: np.ndarray) -> bool:
        """
        Check if point is within this node's hyperbolic region.

        Uses hyperbolic distance from center instead of AABB.
        """
        dist = poincare_distance(self._center, point)
        return dist <= self._hyperbolic_radius * 1.2  # Small tolerance

    def subdivide(self):
        """Split this node into 8 children (octants)."""
        if self.depth >= self.max_depth:
            return

        self.children = []
        center = self._center

        # Create 8 octant children
        for i in range(8):
            # Binary decomposition: 0=min, 1=max for each axis
            new_min = np.array([
                self.min_corner[0] if (i & 1) == 0 else center[0],
                self.min_corner[1] if (i & 2) == 0 else center[1],
                self.min_corner[2] if (i & 4) == 0 else center[2],
            ])
            new_max = np.array([
                center[0] if (i & 1) == 0 else self.max_corner[0],
                center[1] if (i & 2) == 0 else self.max_corner[1],
                center[2] if (i & 4) == 0 else self.max_corner[2],
            ])

            child = OctreeNode(
                min_corner=new_min,
                max_corner=new_max,
                depth=self.depth + 1,
                max_depth=self.max_depth,
                max_voxels_per_node=self.max_voxels_per_node,
            )
            self.children.append(child)

        # Redistribute existing voxels to children
        for voxel in self.voxels:
            self._insert_to_child(voxel)

        self.voxels = []

    def _insert_to_child(self, voxel: Voxel):
        """Insert voxel into appropriate child node."""
        for child in self.children:
            if child.contains(voxel.position):
                child.insert(voxel)
                return

    def insert(self, voxel: Voxel):
        """Insert a voxel into this node or its children."""
        if not self.contains(voxel.position):
            return False

        if self.is_leaf:
            self.voxels.append(voxel)

            # Check if we need to subdivide
            if len(self.voxels) > self.max_voxels_per_node:
                if self.depth < self.max_depth:
                    self.subdivide()
        else:
            self._insert_to_child(voxel)

        return True

    def query_point(self, point: np.ndarray) -> Optional[Voxel]:
        """Find voxel at exact position."""
        if not self.contains(point):
            return None

        if self.is_leaf:
            for voxel in self.voxels:
                if np.allclose(voxel.position, point):
                    return voxel
            return None

        for child in self.children:
            result = child.query_point(point)
            if result is not None:
                return result

        return None

    def query_radius(self, center: np.ndarray, radius: float,
                     use_hyperbolic: bool = True) -> List[Voxel]:
        """
        Find all voxels within radius of center.

        Args:
            center: Query center point
            radius: Search radius
            use_hyperbolic: If True, use hyperbolic distance
        """
        results = []

        # Quick rejection test
        if use_hyperbolic:
            node_dist = poincare_distance(center, self._center)
            if node_dist > radius + self._hyperbolic_radius:
                return results

        if self.is_leaf:
            for voxel in self.voxels:
                if use_hyperbolic:
                    dist = poincare_distance(center, voxel.position)
                else:
                    dist = np.linalg.norm(voxel.position - center)

                if dist <= radius:
                    results.append(voxel)
        else:
            for child in self.children:
                results.extend(child.query_radius(center, radius, use_hyperbolic))

        return results

    def nearest_neighbor(self, point: np.ndarray,
                         use_hyperbolic: bool = True) -> Optional[Tuple[Voxel, float]]:
        """
        Find nearest voxel to point.

        Returns (voxel, distance) or None.
        """
        best_voxel = None
        best_dist = float('inf')

        def search(node: OctreeNode):
            nonlocal best_voxel, best_dist

            if node.is_leaf:
                for voxel in node.voxels:
                    if use_hyperbolic:
                        dist = poincare_distance(point, voxel.position)
                    else:
                        dist = np.linalg.norm(voxel.position - point)

                    if dist < best_dist:
                        best_dist = dist
                        best_voxel = voxel
            else:
                # Sort children by distance to point for better pruning
                child_dists = []
                for child in node.children:
                    if use_hyperbolic:
                        d = poincare_distance(point, child._center)
                    else:
                        d = np.linalg.norm(point - child._center)
                    child_dists.append((d, child))

                child_dists.sort(key=lambda x: x[0])

                for d, child in child_dists:
                    # Prune if this child can't have closer voxels
                    if use_hyperbolic:
                        min_possible = max(0, d - child._hyperbolic_radius)
                    else:
                        half_diag = np.linalg.norm(child.max_corner - child.min_corner) / 2
                        min_possible = max(0, d - half_diag)

                    if min_possible < best_dist:
                        search(child)

        search(self)

        if best_voxel is not None:
            return (best_voxel, best_dist)
        return None

    def all_voxels(self) -> Generator[Voxel, None, None]:
        """Yield all voxels in this subtree."""
        if self.is_leaf:
            yield from self.voxels
        else:
            for child in self.children:
                yield from child.all_voxels()

    def count_voxels(self) -> int:
        """Count total voxels in subtree."""
        if self.is_leaf:
            return len(self.voxels)
        return sum(child.count_voxels() for child in self.children)

    def count_nodes(self) -> int:
        """Count total nodes in subtree."""
        if self.is_leaf:
            return 1
        return 1 + sum(child.count_nodes() for child in self.children)


# =============================================================================
# Hyperbolic Octree
# =============================================================================

class HyperbolicOctree:
    """
    Sparse voxel storage using octree subdivision in the Poincare ball.

    The octree spans [-1, 1]^3, but only points with ||p|| < 1 are valid
    (inside the Poincare ball).

    Features:
    - Hyperbolic distance metrics for spatial queries
    - Sacred Tongue weighting for importance
    - Trust score computation based on boundary distance
    - Efficient nearest-neighbor and range queries
    """

    def __init__(self, max_depth: int = 6, max_voxels_per_node: int = 8):
        """
        Initialize the hyperbolic octree.

        Args:
            max_depth: Maximum subdivision depth (affects memory/speed tradeoff)
            max_voxels_per_node: Voxels per node before splitting
        """
        self.max_depth = max_depth
        self.max_voxels_per_node = max_voxels_per_node

        # Root spans the full Poincare ball bounding box
        self.root = OctreeNode(
            min_corner=np.array([-1.0, -1.0, -1.0]),
            max_corner=np.array([1.0, 1.0, 1.0]),
            depth=0,
            max_depth=max_depth,
            max_voxels_per_node=max_voxels_per_node,
        )

        # Statistics
        self._insert_count = 0
        self._query_count = 0

    def _validate_position(self, position: np.ndarray) -> np.ndarray:
        """Ensure position is inside Poincare ball."""
        position = np.asarray(position, dtype=np.float64)

        if len(position) != 3:
            raise ValueError("Position must be 3D")

        norm = np.linalg.norm(position)
        if norm >= POINCARE_RADIUS:
            # Project to just inside the boundary
            position = position * (POINCARE_RADIUS - EPSILON) / norm

        return position

    def insert(self, position: np.ndarray, data: Any = None) -> Voxel:
        """
        Insert a voxel at the given position.

        Args:
            position: 3D coordinate (will be clamped to Poincare ball)
            data: Arbitrary payload to store

        Returns:
            The created Voxel
        """
        position = self._validate_position(position)
        voxel = Voxel(position=position, data=data)
        self.root.insert(voxel)
        self._insert_count += 1
        return voxel

    def insert_voxel(self, voxel: Voxel) -> bool:
        """Insert a pre-constructed voxel."""
        voxel.position = self._validate_position(voxel.position)
        result = self.root.insert(voxel)
        if result:
            self._insert_count += 1
        return result

    def query_point(self, position: np.ndarray) -> Optional[Voxel]:
        """Find voxel at exact position."""
        self._query_count += 1
        position = self._validate_position(position)
        return self.root.query_point(position)

    def query_radius(self, center: np.ndarray, radius: float,
                     use_hyperbolic: bool = True) -> List[Voxel]:
        """
        Find all voxels within radius of center.

        Uses hyperbolic distance by default (exponentially larger toward boundary).
        """
        self._query_count += 1
        center = self._validate_position(center)
        return self.root.query_radius(center, radius, use_hyperbolic)

    def nearest_neighbor(self, point: np.ndarray,
                         use_hyperbolic: bool = True) -> Optional[Tuple[Voxel, float]]:
        """Find nearest voxel to point."""
        self._query_count += 1
        point = self._validate_position(point)
        return self.root.nearest_neighbor(point, use_hyperbolic)

    def k_nearest_neighbors(self, point: np.ndarray, k: int = 5,
                            use_hyperbolic: bool = True) -> List[Tuple[Voxel, float]]:
        """
        Find k nearest voxels to point.

        Note: This is O(n) for now - could be optimized with priority queue.
        """
        self._query_count += 1
        point = self._validate_position(point)

        # Collect all voxels with distances
        voxel_dists = []
        for voxel in self.root.all_voxels():
            if use_hyperbolic:
                dist = poincare_distance(point, voxel.position)
            else:
                dist = np.linalg.norm(voxel.position - point)
            voxel_dists.append((voxel, dist))

        # Sort and return top k
        voxel_dists.sort(key=lambda x: x[1])
        return voxel_dists[:k]

    def query_tongue(self, tongue: SacredTongue) -> List[Voxel]:
        """Find all voxels belonging to a Sacred Tongue octant."""
        return [v for v in self.root.all_voxels() if v.tongue == tongue]

    def query_trust_range(self, min_trust: float, max_trust: float) -> List[Voxel]:
        """Find all voxels within a trust score range."""
        return [
            v for v in self.root.all_voxels()
            if min_trust <= v.trust_score <= max_trust
        ]

    def all_voxels(self) -> List[Voxel]:
        """Get all voxels in the octree."""
        return list(self.root.all_voxels())

    @property
    def voxel_count(self) -> int:
        """Total number of stored voxels."""
        return self.root.count_voxels()

    @property
    def node_count(self) -> int:
        """Total number of octree nodes."""
        return self.root.count_nodes()

    def statistics(self) -> Dict[str, Any]:
        """Get octree statistics."""
        voxels = list(self.root.all_voxels())

        if not voxels:
            return {
                "voxel_count": 0,
                "node_count": self.node_count,
                "max_depth": self.max_depth,
                "inserts": self._insert_count,
                "queries": self._query_count,
            }

        # Compute statistics
        depths = [v.hyperbolic_depth for v in voxels]
        trusts = [v.trust_score for v in voxels]

        # Tongue distribution
        tongue_counts = {t: 0 for t in SacredTongue}
        for v in voxels:
            tongue_counts[v.tongue] += 1

        return {
            "voxel_count": len(voxels),
            "node_count": self.node_count,
            "max_depth": self.max_depth,
            "depth_stats": {
                "min": min(depths),
                "max": max(depths),
                "mean": np.mean(depths),
                "std": np.std(depths),
            },
            "trust_stats": {
                "min": min(trusts),
                "max": max(trusts),
                "mean": np.mean(trusts),
            },
            "tongue_distribution": {t.value: c for t, c in tongue_counts.items()},
            "inserts": self._insert_count,
            "queries": self._query_count,
        }

    def visualize_2d_projection(self, axis: int = 2) -> str:
        """
        Create ASCII visualization of voxels projected onto 2D plane.

        Args:
            axis: Axis to project out (0=X, 1=Y, 2=Z)
        """
        grid_size = 40
        grid = [[' ' for _ in range(grid_size)] for _ in range(grid_size)]

        # Draw boundary circle
        for i in range(grid_size):
            for j in range(grid_size):
                x = (i - grid_size / 2) / (grid_size / 2)
                y = (j - grid_size / 2) / (grid_size / 2)
                dist = np.sqrt(x**2 + y**2)
                if 0.95 <= dist <= 1.05:
                    grid[j][i] = '.'

        # Plot voxels
        axes = [0, 1, 2]
        axes.remove(axis)

        for voxel in self.root.all_voxels():
            x = voxel.position[axes[0]]
            y = voxel.position[axes[1]]

            i = int((x + 1) / 2 * (grid_size - 1))
            j = int((y + 1) / 2 * (grid_size - 1))

            if 0 <= i < grid_size and 0 <= j < grid_size:
                # Use tongue initial for marker
                grid[grid_size - 1 - j][i] = voxel.tongue.value[0]

        # Mark center
        mid = grid_size // 2
        grid[mid][mid] = '+'

        axis_names = ['X', 'Y', 'Z']
        header = f"Projection onto {axis_names[axes[0]]}-{axis_names[axes[1]]} plane"

        lines = [header, '=' * grid_size]
        for row in grid:
            lines.append(''.join(row))

        return '\n'.join(lines)


# =============================================================================
# Demo
# =============================================================================

def demo():
    """Demonstrate hyperbolic octree functionality."""
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    HYPERBOLIC OCTREE - POINCARE BALL STORAGE                  ║
║                      Sparse Voxels in Hyperbolic Space                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)

    # Create octree
    octree = HyperbolicOctree(max_depth=6)

    # Insert voxels at various positions
    print("Inserting voxels...")

    # Center region (high trust)
    for _ in range(10):
        pos = np.random.randn(3) * 0.1
        octree.insert(pos, data={"type": "center"})

    # Mid-region
    for _ in range(20):
        pos = np.random.randn(3) * 0.3
        octree.insert(pos, data={"type": "mid"})

    # Boundary region (low trust)
    for _ in range(15):
        pos = np.random.randn(3)
        pos = pos / np.linalg.norm(pos) * 0.85  # Near boundary
        octree.insert(pos, data={"type": "boundary"})

    # Show statistics
    stats = octree.statistics()
    print(f"\nOctree Statistics:")
    print(f"  Voxels: {stats['voxel_count']}")
    print(f"  Nodes: {stats['node_count']}")
    print(f"  Depth range: {stats['depth_stats']['min']:.2f} - {stats['depth_stats']['max']:.2f}")
    print(f"  Trust range: {stats['trust_stats']['min']:.2f} - {stats['trust_stats']['max']:.2f}")

    print("\n  Tongue Distribution:")
    for tongue, count in stats['tongue_distribution'].items():
        print(f"    {tongue}: {count}")

    # Test queries
    print("\n" + "=" * 60)
    print("Query Tests")
    print("=" * 60)

    # Nearest neighbor
    query_point = np.array([0.2, 0.3, 0.1])
    result = octree.nearest_neighbor(query_point)
    if result:
        voxel, dist = result
        print(f"\nNearest to {query_point}:")
        print(f"  Position: {voxel.position}")
        print(f"  Hyperbolic distance: {dist:.3f}")
        print(f"  Tongue: {voxel.tongue.value}")
        print(f"  Trust: {voxel.trust_score:.3f}")

    # Range query
    center = np.array([0.0, 0.0, 0.0])
    radius = 0.5  # Hyperbolic radius
    nearby = octree.query_radius(center, radius)
    print(f"\nVoxels within hyperbolic radius {radius} of origin: {len(nearby)}")

    # Euclidean comparison
    nearby_euclidean = octree.query_radius(center, radius, use_hyperbolic=False)
    print(f"Voxels within Euclidean radius {radius}: {len(nearby_euclidean)}")

    # Tongue query
    print("\n" + "=" * 60)
    print("Tongue Queries")
    print("=" * 60)

    for tongue in SacredTongue:
        voxels = octree.query_tongue(tongue)
        print(f"  {tongue.value}: {len(voxels)} voxels")

    # Visualization
    print("\n" + "=" * 60)
    print("2D Projection (XY plane)")
    print("=" * 60)
    print(octree.visualize_2d_projection(axis=2))

    # Distance demonstration
    print("\n" + "=" * 60)
    print("Hyperbolic vs Euclidean Distance")
    print("=" * 60)

    pairs = [
        (np.array([0.0, 0.0, 0.0]), np.array([0.1, 0.0, 0.0])),
        (np.array([0.0, 0.0, 0.0]), np.array([0.5, 0.0, 0.0])),
        (np.array([0.0, 0.0, 0.0]), np.array([0.9, 0.0, 0.0])),
        (np.array([0.5, 0.0, 0.0]), np.array([0.6, 0.0, 0.0])),
        (np.array([0.8, 0.0, 0.0]), np.array([0.9, 0.0, 0.0])),
    ]

    print("\n  Point 1 → Point 2 : Euclidean | Hyperbolic")
    print("  " + "-" * 50)
    for p1, p2 in pairs:
        euclidean = np.linalg.norm(p2 - p1)
        hyperbolic = poincare_distance(p1, p2)
        print(f"  {p1} → {p2}: {euclidean:.3f} | {hyperbolic:.3f}")

    print("\n  Notice: Hyperbolic distance grows EXPONENTIALLY near the boundary!")


if __name__ == "__main__":
    demo()
