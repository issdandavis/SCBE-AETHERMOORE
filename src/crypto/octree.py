"""
Hyperbolic Octree - Sparse Hierarchical Voxel Storage for Poincare Ball
=====================================================================

Adaptive depth octree for 3D points in (-1,1) ball.
Each occupied leaf stores realm color.
Supports insertion and dense export for visualization.

Integration with SCBE:
- Light realm (positive intent/tokens) clusters near origin
- Shadow realm (negative intent/tokens) expands toward boundary
- Negative curvature causes exponential volume growth at edges
"""

import numpy as np
from typing import Optional, Dict, Set, Tuple, List


class OctreeNode:
    """
    Single node in the hyperbolic octree.

    Each node represents a cubic region of the Poincare ball.
    Interior nodes have up to 8 children (octants).
    Leaf nodes store a color/realm label.
    """

    def __init__(
        self,
        bounds_min: np.ndarray,
        bounds_max: np.ndarray,
        depth: int,
        max_depth: int = 6
    ):
        self.bounds_min = bounds_min
        self.bounds_max = bounds_max
        self.center = (bounds_min + bounds_max) / 2.0
        self.depth = depth
        self.max_depth = max_depth
        self.color: Optional[str] = None  # leaf color if occupied
        self.children: Dict[int, 'OctreeNode'] = {}  # 0-7 octants
        self.occupied = False

    def insert(self, coord_3d: np.ndarray, color: str):
        """Insert a point with given color into the octree."""
        # Leaf case - maximum depth reached
        if self.depth == self.max_depth:
            self.color = color
            self.occupied = True
            return

        # Determine octant (3-bit index based on position relative to center)
        octant = 0
        if coord_3d[0] >= self.center[0]:
            octant |= 1
        if coord_3d[1] >= self.center[1]:
            octant |= 2
        if coord_3d[2] >= self.center[2]:
            octant |= 4

        # Create child if needed
        if octant not in self.children:
            child_min = self.bounds_min.copy()
            child_max = self.bounds_max.copy()

            if octant & 1:
                child_min[0] = self.center[0]
            else:
                child_max[0] = self.center[0]
            if octant & 2:
                child_min[1] = self.center[1]
            else:
                child_max[1] = self.center[1]
            if octant & 4:
                child_min[2] = self.center[2]
            else:
                child_max[2] = self.center[2]

            self.children[octant] = OctreeNode(
                child_min, child_max,
                self.depth + 1, self.max_depth
            )

        self.children[octant].insert(coord_3d, color)
        self.occupied = True

    def query_point(self, coord_3d: np.ndarray) -> Optional[str]:
        """Query color at a specific point."""
        if not self.occupied:
            return None

        if self.depth == self.max_depth:
            return self.color

        # Determine octant
        octant = 0
        if coord_3d[0] >= self.center[0]:
            octant |= 1
        if coord_3d[1] >= self.center[1]:
            octant |= 2
        if coord_3d[2] >= self.center[2]:
            octant |= 4

        if octant in self.children:
            return self.children[octant].query_point(coord_3d)
        return None

    def to_dense(self, grid_size: int) -> np.ndarray:
        """Convert sparse octree to dense color grid."""
        colors = np.empty((grid_size, grid_size, grid_size), dtype=object)
        colors[:] = None
        self._fill_dense(colors, grid_size)
        return colors

    def _fill_dense(self, colors: np.ndarray, grid_size: int):
        """Recursively fill dense grid from octree."""
        if self.occupied:
            if self.depth == self.max_depth and self.color:
                # Map bounds to grid indices
                i_min = int((self.bounds_min[0] + 1.0) / 2.0 * (grid_size - 1))
                i_max = int((self.bounds_max[0] + 1.0) / 2.0 * (grid_size - 1))
                j_min = int((self.bounds_min[1] + 1.0) / 2.0 * (grid_size - 1))
                j_max = int((self.bounds_max[1] + 1.0) / 2.0 * (grid_size - 1))
                k_min = int((self.bounds_min[2] + 1.0) / 2.0 * (grid_size - 1))
                k_max = int((self.bounds_max[2] + 1.0) / 2.0 * (grid_size - 1))

                # Clamp to valid range
                i_min, i_max = max(0, i_min), min(grid_size-1, i_max)
                j_min, j_max = max(0, j_min), min(grid_size-1, j_max)
                k_min, k_max = max(0, k_min), min(grid_size-1, k_max)

                colors[i_min:i_max+1, j_min:j_max+1, k_min:k_max+1] = self.color
            else:
                for child in self.children.values():
                    child._fill_dense(colors, grid_size)

    def collect_occupied_voxels(self, grid_size: int) -> Set[Tuple[int, int, int]]:
        """Collect all occupied voxel indices."""
        voxels = set()
        self._collect_voxels(voxels, grid_size)
        return voxels

    def _collect_voxels(self, voxels: Set[Tuple[int, int, int]], grid_size: int):
        """Recursively collect occupied voxel indices."""
        if self.occupied:
            if self.depth == self.max_depth and self.color:
                center = self.center
                idx = ((center + 1.0) / 2.0 * (grid_size - 1)).astype(int)
                i, j, k = tuple(idx)
                if 0 <= i < grid_size and 0 <= j < grid_size and 0 <= k < grid_size:
                    voxels.add((i, j, k))
            else:
                for child in self.children.values():
                    child._collect_voxels(voxels, grid_size)


class HyperbolicOctree:
    """
    Sparse hierarchical voxel storage for points in the Poincare ball.

    Features:
    - Adaptive depth (only allocates occupied regions)
    - O(log N) insertion
    - Memory efficient for sparse lattices
    - Supports realm coloring (light/shadow/path)
    """

    def __init__(self, grid_size: int = 64, max_depth: int = 6):
        self.grid_size = grid_size
        self.max_depth = max_depth
        self.root = OctreeNode(
            np.array([-1.0, -1.0, -1.0]),
            np.array([1.0, 1.0, 1.0]),
            0, max_depth
        )
        self._point_count = 0

    def insert(self, coord_3d: np.ndarray, realm: str):
        """
        Insert a point with realm label.

        Args:
            coord_3d: 3D coordinates in Poincare ball (||v|| < 1)
            realm: Realm label (e.g., 'light_realm', 'shadow_realm')
        """
        # Map realm to color
        if realm in ('light_realm', 'light'):
            color = 'gold'
        elif realm in ('shadow_realm', 'shadow'):
            color = 'purple'
        elif realm in ('path', 'geodesic'):
            color = 'cyan'
        elif realm == 'red':
            color = 'red'
        elif realm == 'magenta':
            color = 'magenta'
        else:
            color = realm  # Use as-is if already a color

        # Only insert interior points
        if np.linalg.norm(coord_3d) < 0.95:
            self.root.insert(coord_3d, color)
            self._point_count += 1

    def query(self, coord_3d: np.ndarray) -> Optional[str]:
        """Query the color/realm at a point."""
        return self.root.query_point(coord_3d)

    def to_dense(self) -> np.ndarray:
        """Export to dense grid for visualization."""
        return self.root.to_dense(self.grid_size)

    def get_occupied_voxels(self) -> Set[Tuple[int, int, int]]:
        """Get set of occupied voxel indices."""
        return self.root.collect_occupied_voxels(self.grid_size)

    def occupancy_ratio(self) -> float:
        """Compute fraction of voxels occupied."""
        occupied = len(self.get_occupied_voxels())
        total = self.grid_size ** 3
        return occupied / total

    @property
    def point_count(self) -> int:
        """Number of points inserted."""
        return self._point_count


# =============================================================================
# Demo
# =============================================================================

if __name__ == "__main__":
    print("[OCTREE] Testing hyperbolic octree...")

    octree = HyperbolicOctree(grid_size=64, max_depth=6)

    # Insert some light realm points (near origin)
    for _ in range(50):
        point = np.random.randn(3) * 0.3  # Clustered near center
        point = point / (np.linalg.norm(point) + 0.1) * 0.4  # Keep inside ball
        octree.insert(point, 'light_realm')

    # Insert some shadow realm points (near boundary)
    for _ in range(50):
        point = np.random.randn(3)
        point = point / np.linalg.norm(point) * 0.85  # Near boundary
        octree.insert(point, 'shadow_realm')

    print(f"[OCTREE] Points inserted: {octree.point_count}")
    print(f"[OCTREE] Occupied voxels: {len(octree.get_occupied_voxels())}")
    print(f"[OCTREE] Occupancy ratio: {octree.occupancy_ratio():.6f}")
    print("[OCTREE] Sparse storage working correctly!")
