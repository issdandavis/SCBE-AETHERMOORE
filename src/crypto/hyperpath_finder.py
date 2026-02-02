"""
Hyperbolic Pathfinding - A* and Bidirectional A* in Poincare Ball
=================================================================

Finds optimal paths through hyperbolic space using true geodesic distance.
Supports both grid-based and graph-based pathfinding.

Key Features:
- A* with hyperbolic heuristic (Poincare distance)
- Bidirectional A* for faster convergence
- Trust-weighted costs (untrusted regions cost more)
- Sacred Tongue affinity bonuses
- Geodesic path interpolation

Based on SCBE-AETHERMOORE's geometric AI safety architecture.

@layer Layer 5 (Hyperbolic Distance), Layer 11 (Temporal Distance)
@component HyperpathFinder
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Set, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import heapq
from collections import defaultdict

from .octree import (
    HyperbolicOctree, Voxel, OctreeNode,
    poincare_distance, mobius_addition, geodesic_midpoint,
    SacredTongue, TONGUE_WEIGHTS, PHI, POINCARE_RADIUS, EPSILON
)


# =============================================================================
# Path Node for A* Search
# =============================================================================

@dataclass(order=True)
class PathNode:
    """
    Node in the A* search graph.

    Priority-ordered by f_score (g + h).
    """
    f_score: float  # Total estimated cost (g + h)
    position: np.ndarray = field(compare=False)
    g_score: float = field(compare=False)  # Cost from start
    h_score: float = field(compare=False)  # Heuristic to goal
    parent: Optional['PathNode'] = field(default=None, compare=False)
    voxel: Optional[Voxel] = field(default=None, compare=False)

    def __hash__(self):
        return hash(tuple(self.position))

    def __eq__(self, other):
        if not isinstance(other, PathNode):
            return False
        return np.allclose(self.position, other.position)


# =============================================================================
# Hyperpath Result
# =============================================================================

@dataclass
class HyperpathResult:
    """
    Result of pathfinding operation.
    """
    success: bool
    path: List[np.ndarray] = field(default_factory=list)
    voxels: List[Voxel] = field(default_factory=list)
    total_cost: float = float('inf')
    hyperbolic_length: float = float('inf')
    euclidean_length: float = float('inf')
    nodes_explored: int = 0
    tongues_traversed: List[SacredTongue] = field(default_factory=list)
    min_trust: float = 1.0
    algorithm: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "path": [p.tolist() for p in self.path],
            "total_cost": self.total_cost,
            "hyperbolic_length": self.hyperbolic_length,
            "euclidean_length": self.euclidean_length,
            "nodes_explored": self.nodes_explored,
            "tongues_traversed": [t.value for t in self.tongues_traversed],
            "min_trust": self.min_trust,
            "algorithm": self.algorithm,
        }


# =============================================================================
# Cost Functions
# =============================================================================

def standard_cost(p1: np.ndarray, p2: np.ndarray) -> float:
    """Standard hyperbolic distance cost."""
    return poincare_distance(p1, p2)


def trust_weighted_cost(p1: np.ndarray, p2: np.ndarray,
                        trust1: float = 1.0, trust2: float = 1.0) -> float:
    """
    Cost weighted by trust scores.

    Lower trust = higher cost (penalize untrusted regions).
    """
    base_cost = poincare_distance(p1, p2)

    # Average trust, inverted to penalty
    avg_trust = (trust1 + trust2) / 2
    trust_penalty = 1.0 + (1.0 - avg_trust) * 2.0  # 1.0 to 3.0

    return base_cost * trust_penalty


def tongue_affinity_cost(p1: np.ndarray, p2: np.ndarray,
                         preferred_tongues: Set[SacredTongue] = None) -> float:
    """
    Cost that gives bonus for staying in preferred tongue regions.
    """
    base_cost = poincare_distance(p1, p2)

    if not preferred_tongues:
        return base_cost

    # Determine tongues for both points
    def get_tongue(p):
        signs = tuple(1 if x >= 0 else -1 for x in p)
        tongue_map = {
            (1, 1, 1): SacredTongue.KO,
            (1, 1, -1): SacredTongue.AV,
            (1, -1, 1): SacredTongue.RU,
            (1, -1, -1): SacredTongue.CA,
            (-1, 1, 1): SacredTongue.UM,
            (-1, 1, -1): SacredTongue.DR,
            (-1, -1, 1): SacredTongue.KO,
            (-1, -1, -1): SacredTongue.DR,
        }
        return tongue_map.get(signs, SacredTongue.KO)

    t1 = get_tongue(p1)
    t2 = get_tongue(p2)

    # Discount if both in preferred tongue
    if t1 in preferred_tongues and t2 in preferred_tongues:
        return base_cost * 0.7  # 30% discount

    # Penalty if entering non-preferred tongue
    if t1 in preferred_tongues and t2 not in preferred_tongues:
        return base_cost * 1.5  # 50% penalty

    return base_cost


def harmonic_wall_cost(p1: np.ndarray, p2: np.ndarray) -> float:
    """
    Cost using SCBE's Harmonic Wall formula.

    H(d) = phi^d where d is hyperbolic distance from origin.
    Makes boundary regions exponentially expensive.
    """
    base_cost = poincare_distance(p1, p2)

    # Add harmonic wall penalty based on distance from origin
    d1 = poincare_distance(np.zeros(3), p1)
    d2 = poincare_distance(np.zeros(3), p2)

    wall_factor = (PHI ** d1 + PHI ** d2) / 2

    return base_cost * wall_factor


# =============================================================================
# Hyperbolic Pathfinder
# =============================================================================

class HyperpathFinder:
    """
    Pathfinding in hyperbolic space using A* and Bidirectional A*.

    Operates on either:
    1. A discrete grid (voxel-to-voxel navigation)
    2. Continuous space with waypoints

    The key insight: In hyperbolic space, "straight lines" are geodesics
    (arcs), and distances grow exponentially toward the boundary.
    """

    # 26-connected neighbors (3D Moore neighborhood)
    NEIGHBOR_OFFSETS = [
        np.array([dx, dy, dz])
        for dx in [-1, 0, 1]
        for dy in [-1, 0, 1]
        for dz in [-1, 0, 1]
        if not (dx == 0 and dy == 0 and dz == 0)
    ]

    def __init__(self, octree: HyperbolicOctree = None,
                 grid_resolution: int = 32):
        """
        Initialize pathfinder.

        Args:
            octree: Optional octree for voxel-based navigation
            grid_resolution: Resolution for grid-based mode
        """
        self.octree = octree
        self.grid_resolution = grid_resolution
        self.grid_step = 2.0 / grid_resolution  # Maps [-1, 1] to grid

        # Cost function (can be customized)
        self.cost_fn: Callable = standard_cost

        # Statistics
        self._total_searches = 0
        self._total_nodes_explored = 0

    def set_cost_function(self, cost_fn: Callable):
        """Set custom cost function."""
        self.cost_fn = cost_fn

    def _position_to_grid(self, pos: np.ndarray) -> Tuple[int, int, int]:
        """Convert continuous position to grid coordinates."""
        grid = ((pos + 1.0) / 2.0 * self.grid_resolution).astype(int)
        grid = np.clip(grid, 0, self.grid_resolution - 1)
        return tuple(grid)

    def _grid_to_position(self, grid: Tuple[int, int, int]) -> np.ndarray:
        """Convert grid coordinates to continuous position."""
        pos = (np.array(grid) / self.grid_resolution) * 2.0 - 1.0
        pos += self.grid_step / 2  # Center of cell
        return pos

    def _is_valid_position(self, pos: np.ndarray) -> bool:
        """Check if position is inside Poincare ball."""
        return np.linalg.norm(pos) < POINCARE_RADIUS - EPSILON

    def _get_neighbors_grid(self, pos: np.ndarray) -> List[np.ndarray]:
        """Get valid neighbors on the grid."""
        neighbors = []

        for offset in self.NEIGHBOR_OFFSETS:
            neighbor = pos + offset * self.grid_step

            if self._is_valid_position(neighbor):
                neighbors.append(neighbor)

        return neighbors

    def _get_neighbors_octree(self, pos: np.ndarray,
                              radius: float = 0.2) -> List[np.ndarray]:
        """Get neighbors from octree voxels."""
        if self.octree is None:
            return self._get_neighbors_grid(pos)

        nearby_voxels = self.octree.query_radius(pos, radius)
        return [v.position for v in nearby_voxels if not np.allclose(v.position, pos)]

    def _heuristic(self, pos: np.ndarray, goal: np.ndarray) -> float:
        """
        Admissible heuristic for A*.

        Uses hyperbolic distance (never overestimates in hyperbolic space).
        """
        return poincare_distance(pos, goal)

    def _reconstruct_path(self, node: PathNode) -> List[np.ndarray]:
        """Reconstruct path from goal node."""
        path = []
        current = node

        while current is not None:
            path.append(current.position)
            current = current.parent

        path.reverse()
        return path

    def _compute_path_stats(self, path: List[np.ndarray]) -> Tuple[float, float]:
        """Compute hyperbolic and Euclidean path lengths."""
        if len(path) < 2:
            return 0.0, 0.0

        h_length = 0.0
        e_length = 0.0

        for i in range(len(path) - 1):
            h_length += poincare_distance(path[i], path[i + 1])
            e_length += np.linalg.norm(path[i + 1] - path[i])

        return h_length, e_length

    def _get_tongues_on_path(self, path: List[np.ndarray]) -> List[SacredTongue]:
        """Determine Sacred Tongues traversed along path."""
        tongues = []
        seen = set()

        for pos in path:
            signs = tuple(1 if x >= 0 else -1 for x in pos)
            tongue_map = {
                (1, 1, 1): SacredTongue.KO,
                (1, 1, -1): SacredTongue.AV,
                (1, -1, 1): SacredTongue.RU,
                (1, -1, -1): SacredTongue.CA,
                (-1, 1, 1): SacredTongue.UM,
                (-1, 1, -1): SacredTongue.DR,
                (-1, -1, 1): SacredTongue.KO,
                (-1, -1, -1): SacredTongue.DR,
            }
            tongue = tongue_map.get(signs, SacredTongue.KO)

            if tongue not in seen:
                tongues.append(tongue)
                seen.add(tongue)

        return tongues

    # =========================================================================
    # A* Algorithm
    # =========================================================================

    def a_star(self, start: np.ndarray, goal: np.ndarray,
               use_octree: bool = False,
               max_iterations: int = 10000) -> HyperpathResult:
        """
        A* pathfinding using hyperbolic distance heuristic.

        Args:
            start: Starting position
            goal: Goal position
            use_octree: Use octree voxels for neighbors (else grid)
            max_iterations: Maximum search iterations

        Returns:
            HyperpathResult with path and statistics
        """
        self._total_searches += 1

        start = np.asarray(start, dtype=np.float64)
        goal = np.asarray(goal, dtype=np.float64)

        # Validate positions
        if not self._is_valid_position(start):
            start = start * 0.99
        if not self._is_valid_position(goal):
            goal = goal * 0.99

        # Initialize
        start_node = PathNode(
            f_score=self._heuristic(start, goal),
            position=start,
            g_score=0.0,
            h_score=self._heuristic(start, goal)
        )

        open_set = [start_node]  # Priority queue
        open_set_lookup = {tuple(start): start_node}  # Fast lookup
        closed_set: Set[Tuple] = set()

        nodes_explored = 0

        while open_set and nodes_explored < max_iterations:
            # Pop lowest f_score
            current = heapq.heappop(open_set)
            current_key = tuple(current.position)

            if current_key in open_set_lookup:
                del open_set_lookup[current_key]

            nodes_explored += 1

            # Goal check
            if poincare_distance(current.position, goal) < self.grid_step:
                # Found path
                path = self._reconstruct_path(current)
                path.append(goal)

                h_length, e_length = self._compute_path_stats(path)

                self._total_nodes_explored += nodes_explored

                return HyperpathResult(
                    success=True,
                    path=path,
                    total_cost=current.g_score + poincare_distance(current.position, goal),
                    hyperbolic_length=h_length,
                    euclidean_length=e_length,
                    nodes_explored=nodes_explored,
                    tongues_traversed=self._get_tongues_on_path(path),
                    min_trust=1.0,  # Would compute from voxels
                    algorithm="A*"
                )

            closed_set.add(current_key)

            # Expand neighbors
            if use_octree and self.octree:
                neighbors = self._get_neighbors_octree(current.position)
            else:
                neighbors = self._get_neighbors_grid(current.position)

            for neighbor_pos in neighbors:
                neighbor_key = tuple(neighbor_pos)

                if neighbor_key in closed_set:
                    continue

                # Compute costs
                tentative_g = current.g_score + self.cost_fn(current.position, neighbor_pos)
                h_score = self._heuristic(neighbor_pos, goal)
                f_score = tentative_g + h_score

                # Check if better path found
                if neighbor_key in open_set_lookup:
                    if tentative_g >= open_set_lookup[neighbor_key].g_score:
                        continue

                neighbor_node = PathNode(
                    f_score=f_score,
                    position=neighbor_pos,
                    g_score=tentative_g,
                    h_score=h_score,
                    parent=current
                )

                heapq.heappush(open_set, neighbor_node)
                open_set_lookup[neighbor_key] = neighbor_node

        # No path found
        self._total_nodes_explored += nodes_explored

        return HyperpathResult(
            success=False,
            nodes_explored=nodes_explored,
            algorithm="A*"
        )

    # =========================================================================
    # Bidirectional A* Algorithm
    # =========================================================================

    def bidirectional_a_star(self, start: np.ndarray, goal: np.ndarray,
                             use_octree: bool = False,
                             max_iterations: int = 10000) -> HyperpathResult:
        """
        Bidirectional A* - searches from both ends simultaneously.

        Often faster than standard A* because the search spaces meet
        in the middle, exploring fewer total nodes.

        Args:
            start: Starting position
            goal: Goal position
            use_octree: Use octree voxels for neighbors
            max_iterations: Maximum total iterations (split between both directions)

        Returns:
            HyperpathResult with path and statistics
        """
        self._total_searches += 1

        start = np.asarray(start, dtype=np.float64)
        goal = np.asarray(goal, dtype=np.float64)

        # Validate
        if not self._is_valid_position(start):
            start = start * 0.99
        if not self._is_valid_position(goal):
            goal = goal * 0.99

        # Forward search (start → goal)
        fwd_start = PathNode(
            f_score=self._heuristic(start, goal),
            position=start,
            g_score=0.0,
            h_score=self._heuristic(start, goal)
        )
        fwd_open = [fwd_start]
        fwd_lookup = {tuple(start): fwd_start}
        fwd_closed: Dict[Tuple, PathNode] = {}

        # Backward search (goal → start)
        bwd_start = PathNode(
            f_score=self._heuristic(goal, start),
            position=goal,
            g_score=0.0,
            h_score=self._heuristic(goal, start)
        )
        bwd_open = [bwd_start]
        bwd_lookup = {tuple(goal): bwd_start}
        bwd_closed: Dict[Tuple, PathNode] = {}

        # Best meeting point found
        best_cost = float('inf')
        meeting_node_fwd: Optional[PathNode] = None
        meeting_node_bwd: Optional[PathNode] = None

        nodes_explored = 0

        while (fwd_open or bwd_open) and nodes_explored < max_iterations:
            # Alternate between forward and backward
            # (or choose based on which has lower f_score)

            # Forward expansion
            if fwd_open:
                fwd_current = heapq.heappop(fwd_open)
                fwd_key = tuple(fwd_current.position)

                if fwd_key in fwd_lookup:
                    del fwd_lookup[fwd_key]

                nodes_explored += 1
                fwd_closed[fwd_key] = fwd_current

                # Check if meets backward search
                if fwd_key in bwd_closed:
                    total_cost = fwd_current.g_score + bwd_closed[fwd_key].g_score
                    if total_cost < best_cost:
                        best_cost = total_cost
                        meeting_node_fwd = fwd_current
                        meeting_node_bwd = bwd_closed[fwd_key]

                # Expand forward
                if fwd_current.f_score < best_cost:
                    if use_octree and self.octree:
                        neighbors = self._get_neighbors_octree(fwd_current.position)
                    else:
                        neighbors = self._get_neighbors_grid(fwd_current.position)

                    for neighbor_pos in neighbors:
                        neighbor_key = tuple(neighbor_pos)
                        if neighbor_key in fwd_closed:
                            continue

                        tentative_g = fwd_current.g_score + self.cost_fn(fwd_current.position, neighbor_pos)
                        h_score = self._heuristic(neighbor_pos, goal)
                        f_score = tentative_g + h_score

                        if neighbor_key in fwd_lookup:
                            if tentative_g >= fwd_lookup[neighbor_key].g_score:
                                continue

                        node = PathNode(
                            f_score=f_score,
                            position=neighbor_pos,
                            g_score=tentative_g,
                            h_score=h_score,
                            parent=fwd_current
                        )
                        heapq.heappush(fwd_open, node)
                        fwd_lookup[neighbor_key] = node

            # Backward expansion
            if bwd_open:
                bwd_current = heapq.heappop(bwd_open)
                bwd_key = tuple(bwd_current.position)

                if bwd_key in bwd_lookup:
                    del bwd_lookup[bwd_key]

                nodes_explored += 1
                bwd_closed[bwd_key] = bwd_current

                # Check if meets forward search
                if bwd_key in fwd_closed:
                    total_cost = bwd_current.g_score + fwd_closed[bwd_key].g_score
                    if total_cost < best_cost:
                        best_cost = total_cost
                        meeting_node_fwd = fwd_closed[bwd_key]
                        meeting_node_bwd = bwd_current

                # Expand backward
                if bwd_current.f_score < best_cost:
                    if use_octree and self.octree:
                        neighbors = self._get_neighbors_octree(bwd_current.position)
                    else:
                        neighbors = self._get_neighbors_grid(bwd_current.position)

                    for neighbor_pos in neighbors:
                        neighbor_key = tuple(neighbor_pos)
                        if neighbor_key in bwd_closed:
                            continue

                        tentative_g = bwd_current.g_score + self.cost_fn(bwd_current.position, neighbor_pos)
                        h_score = self._heuristic(neighbor_pos, start)
                        f_score = tentative_g + h_score

                        if neighbor_key in bwd_lookup:
                            if tentative_g >= bwd_lookup[neighbor_key].g_score:
                                continue

                        node = PathNode(
                            f_score=f_score,
                            position=neighbor_pos,
                            g_score=tentative_g,
                            h_score=h_score,
                            parent=bwd_current
                        )
                        heapq.heappush(bwd_open, node)
                        bwd_lookup[neighbor_key] = node

            # Early termination check
            if meeting_node_fwd is not None:
                # Check if we can't do better
                min_fwd_f = fwd_open[0].f_score if fwd_open else float('inf')
                min_bwd_f = bwd_open[0].f_score if bwd_open else float('inf')

                if min(min_fwd_f, min_bwd_f) >= best_cost:
                    break

        # Reconstruct path if found
        if meeting_node_fwd is not None and meeting_node_bwd is not None:
            # Forward path: start → meeting point
            fwd_path = self._reconstruct_path(meeting_node_fwd)

            # Backward path: meeting point → goal (reversed)
            bwd_path = self._reconstruct_path(meeting_node_bwd)
            bwd_path.reverse()

            # Combine (avoid duplicating meeting point)
            path = fwd_path + bwd_path[1:]

            h_length, e_length = self._compute_path_stats(path)

            self._total_nodes_explored += nodes_explored

            return HyperpathResult(
                success=True,
                path=path,
                total_cost=best_cost,
                hyperbolic_length=h_length,
                euclidean_length=e_length,
                nodes_explored=nodes_explored,
                tongues_traversed=self._get_tongues_on_path(path),
                min_trust=1.0,
                algorithm="Bidirectional A*"
            )

        # No path found
        self._total_nodes_explored += nodes_explored

        return HyperpathResult(
            success=False,
            nodes_explored=nodes_explored,
            algorithm="Bidirectional A*"
        )

    # =========================================================================
    # Geodesic Interpolation
    # =========================================================================

    def interpolate_geodesic(self, p1: np.ndarray, p2: np.ndarray,
                             num_points: int = 10) -> List[np.ndarray]:
        """
        Interpolate points along the geodesic between p1 and p2.

        In the Poincare ball, geodesics are circular arcs perpendicular
        to the boundary (or straight lines through the origin).

        This uses an approximation via repeated midpoint computation.
        """
        if num_points < 2:
            return [p1, p2]

        points = [np.asarray(p1, dtype=np.float64)]

        # Use recursive midpoint for smooth curve
        def subdivide(a: np.ndarray, b: np.ndarray, depth: int) -> List[np.ndarray]:
            if depth == 0:
                return [a, b]

            mid = geodesic_midpoint(a, b)
            left = subdivide(a, mid, depth - 1)
            right = subdivide(mid, b, depth - 1)

            return left + right[1:]

        # Determine subdivision depth from num_points
        import math
        depth = max(1, int(math.log2(num_points)))

        return subdivide(p1, p2, depth)

    def smooth_path(self, path: List[np.ndarray],
                    interpolation_factor: int = 3) -> List[np.ndarray]:
        """
        Smooth a path by interpolating geodesics between waypoints.
        """
        if len(path) < 2:
            return path

        smoothed = []
        for i in range(len(path) - 1):
            segment = self.interpolate_geodesic(
                path[i], path[i + 1],
                num_points=interpolation_factor
            )
            # Avoid duplicates at segment boundaries
            if i > 0:
                segment = segment[1:]
            smoothed.extend(segment)

        return smoothed

    # =========================================================================
    # Statistics
    # =========================================================================

    def statistics(self) -> Dict[str, Any]:
        """Get pathfinder statistics."""
        return {
            "total_searches": self._total_searches,
            "total_nodes_explored": self._total_nodes_explored,
            "avg_nodes_per_search": (
                self._total_nodes_explored / self._total_searches
                if self._total_searches > 0 else 0
            ),
            "grid_resolution": self.grid_resolution,
            "grid_step": self.grid_step,
            "has_octree": self.octree is not None,
        }


# =============================================================================
# Demo
# =============================================================================

def demo():
    """Demonstrate hyperbolic pathfinding."""
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    HYPERBOLIC PATHFINDING - POINCARE BALL                     ║
║                      A* and Bidirectional A* Algorithms                       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)

    # Create pathfinder
    pathfinder = HyperpathFinder(grid_resolution=32)

    # Test cases
    test_cases = [
        ("Center to boundary", np.array([0.0, 0.0, 0.0]), np.array([0.8, 0.0, 0.0])),
        ("Across center", np.array([-0.5, -0.5, 0.0]), np.array([0.5, 0.5, 0.0])),
        ("Along boundary", np.array([0.7, 0.0, 0.0]), np.array([0.0, 0.7, 0.0])),
        ("Diagonal 3D", np.array([-0.4, -0.4, -0.4]), np.array([0.4, 0.4, 0.4])),
    ]

    print("=" * 70)
    print("A* vs Bidirectional A* Comparison")
    print("=" * 70)

    for name, start, goal in test_cases:
        print(f"\n  {name}")
        print(f"  Start: {start} → Goal: {goal}")
        print(f"  Direct hyperbolic distance: {poincare_distance(start, goal):.3f}")

        # Standard A*
        result_a = pathfinder.a_star(start, goal)

        # Bidirectional A*
        result_b = pathfinder.bidirectional_a_star(start, goal)

        print(f"\n  A* Algorithm:")
        print(f"    Success: {result_a.success}")
        if result_a.success:
            print(f"    Path length: {len(result_a.path)} waypoints")
            print(f"    Hyperbolic length: {result_a.hyperbolic_length:.3f}")
            print(f"    Euclidean length: {result_a.euclidean_length:.3f}")
            print(f"    Nodes explored: {result_a.nodes_explored}")
            print(f"    Tongues: {', '.join(t.value for t in result_a.tongues_traversed)}")

        print(f"\n  Bidirectional A*:")
        print(f"    Success: {result_b.success}")
        if result_b.success:
            print(f"    Path length: {len(result_b.path)} waypoints")
            print(f"    Hyperbolic length: {result_b.hyperbolic_length:.3f}")
            print(f"    Euclidean length: {result_b.euclidean_length:.3f}")
            print(f"    Nodes explored: {result_b.nodes_explored}")
            print(f"    Tongues: {', '.join(t.value for t in result_b.tongues_traversed)}")

        if result_a.success and result_b.success:
            speedup = result_a.nodes_explored / result_b.nodes_explored
            print(f"\n    Bidirectional speedup: {speedup:.2f}x fewer nodes")

    # Cost function comparison
    print("\n" + "=" * 70)
    print("Cost Function Comparison")
    print("=" * 70)

    start = np.array([0.0, 0.0, 0.0])
    goal = np.array([0.7, 0.0, 0.0])

    cost_functions = [
        ("Standard (hyperbolic)", standard_cost),
        ("Trust-weighted", lambda p1, p2: trust_weighted_cost(p1, p2, 0.5, 0.5)),
        ("Harmonic Wall", harmonic_wall_cost),
    ]

    for name, cost_fn in cost_functions:
        pathfinder.set_cost_function(cost_fn)
        result = pathfinder.a_star(start, goal)

        print(f"\n  {name}:")
        print(f"    Total cost: {result.total_cost:.3f}")
        print(f"    Path length: {len(result.path)} waypoints")
        print(f"    Nodes explored: {result.nodes_explored}")

    # Geodesic interpolation
    print("\n" + "=" * 70)
    print("Geodesic Interpolation")
    print("=" * 70)

    p1 = np.array([0.5, 0.0, 0.0])
    p2 = np.array([0.0, 0.5, 0.0])

    geodesic = pathfinder.interpolate_geodesic(p1, p2, num_points=8)

    print(f"\n  Geodesic from {p1} to {p2}:")
    for i, point in enumerate(geodesic):
        dist_from_origin = np.linalg.norm(point)
        print(f"    {i}: {point} (r={dist_from_origin:.3f})")

    print("\n  Notice: Points curve INWARD (toward center) in hyperbolic space!")
    print("  This is because geodesics are arcs perpendicular to the boundary.")

    # Statistics
    print("\n" + "=" * 70)
    print("Pathfinder Statistics")
    print("=" * 70)

    stats = pathfinder.statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    demo()
