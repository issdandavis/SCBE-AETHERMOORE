"""
Hyperbolic Octree - Sparse Hierarchical Voxel Storage for Poincare Ball
=====================================================================

Adaptive depth octree for 3D points in (-1,1) ball.
Each occupied leaf stores realm color AND harmonic fingerprint.
Supports insertion, spectral clustering, and dense export for visualization.

Integration with SCBE:
- Light realm (positive intent/tokens) clusters near origin
- Shadow realm (negative intent/tokens) expands toward boundary
- Negative curvature causes exponential volume growth at edges
- Harmonic fingerprints enable spectral clustering of similar paths
"""

import numpy as np
from typing import Optional, Dict, Set, Tuple, List, Any
from dataclasses import dataclass


@dataclass
class SpectralVoxel:
    """
    Voxel with spectral (harmonic) metadata for clustering.

    Stores both the realm color and harmonic fingerprint,
    enabling spectral similarity queries across the octree.
    """
    color: str
    fingerprint_hash: Optional[str] = None
    spectral_centroid: Optional[float] = None
    dominant_freq: Optional[float] = None
    polarity: Optional[str] = None

    def spectral_distance(self, other: 'SpectralVoxel') -> float:
        """Compute spectral distance between two voxels."""
        if self.spectral_centroid is None or other.spectral_centroid is None:
            return float('inf')

        # Weighted sum of spectral differences
        centroid_diff = abs(self.spectral_centroid - other.spectral_centroid) / 1000.0
        freq_diff = abs((self.dominant_freq or 440) - (other.dominant_freq or 440)) / 500.0

        # Polarity penalty
        polarity_penalty = 0.0 if self.polarity == other.polarity else 0.5

        return centroid_diff + freq_diff + polarity_penalty


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
        self.voxel: Optional[SpectralVoxel] = None  # spectral metadata
        self.children: Dict[int, 'OctreeNode'] = {}  # 0-7 octants
        self.occupied = False

    def insert(
        self,
        coord_3d: np.ndarray,
        color: str,
        voxel: Optional[SpectralVoxel] = None
    ):
        """Insert a point with given color and optional spectral metadata."""
        # Leaf case - maximum depth reached
        if self.depth == self.max_depth:
            self.color = color
            self.voxel = voxel or SpectralVoxel(color=color)
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

        self.children[octant].insert(coord_3d, color, voxel)
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

    def query_voxel(self, coord_3d: np.ndarray) -> Optional[SpectralVoxel]:
        """Query spectral voxel at a specific point."""
        if not self.occupied:
            return None

        if self.depth == self.max_depth:
            return self.voxel

        octant = 0
        if coord_3d[0] >= self.center[0]:
            octant |= 1
        if coord_3d[1] >= self.center[1]:
            octant |= 2
        if coord_3d[2] >= self.center[2]:
            octant |= 4

        if octant in self.children:
            return self.children[octant].query_voxel(coord_3d)
        return None

    def collect_spectral_voxels(self) -> List[Tuple[np.ndarray, SpectralVoxel]]:
        """Collect all spectral voxels with their positions."""
        results = []
        self._collect_spectral(results)
        return results

    def _collect_spectral(self, results: List[Tuple[np.ndarray, SpectralVoxel]]):
        """Recursively collect spectral voxels."""
        if self.occupied:
            if self.depth == self.max_depth and self.voxel:
                results.append((self.center.copy(), self.voxel))
            else:
                for child in self.children.values():
                    child._collect_spectral(results)

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
    - Harmonic fingerprint storage for spectral clustering
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

    def _realm_to_color(self, realm: str) -> str:
        """Map realm label to color."""
        if realm in ('light_realm', 'light'):
            return 'gold'
        elif realm in ('shadow_realm', 'shadow'):
            return 'purple'
        elif realm in ('path', 'geodesic'):
            return 'cyan'
        elif realm == 'red':
            return 'red'
        elif realm == 'magenta':
            return 'magenta'
        return realm  # Use as-is if already a color

    def insert(self, coord_3d: np.ndarray, realm: str):
        """
        Insert a point with realm label.

        Args:
            coord_3d: 3D coordinates in Poincare ball (||v|| < 1)
            realm: Realm label (e.g., 'light_realm', 'shadow_realm')
        """
        color = self._realm_to_color(realm)

        # Only insert interior points
        if np.linalg.norm(coord_3d) < 0.95:
            voxel = SpectralVoxel(color=color)
            self.root.insert(coord_3d, color, voxel)
            self._point_count += 1

    def insert_with_fingerprint(
        self,
        coord_3d: np.ndarray,
        realm: str,
        fingerprint_hash: str,
        spectral_centroid: float,
        dominant_freq: float,
        polarity: str
    ):
        """
        Insert a point with harmonic fingerprint for spectral clustering.

        Args:
            coord_3d: 3D coordinates in Poincare ball (||v|| < 1)
            realm: Realm label
            fingerprint_hash: Hash of harmonic fingerprint
            spectral_centroid: Weighted frequency center
            dominant_freq: Peak frequency component
            polarity: 'light', 'shadow', or 'balanced'
        """
        color = self._realm_to_color(realm)

        if np.linalg.norm(coord_3d) < 0.95:
            voxel = SpectralVoxel(
                color=color,
                fingerprint_hash=fingerprint_hash,
                spectral_centroid=spectral_centroid,
                dominant_freq=dominant_freq,
                polarity=polarity
            )
            self.root.insert(coord_3d, color, voxel)
            self._point_count += 1

    def query(self, coord_3d: np.ndarray) -> Optional[str]:
        """Query the color/realm at a point."""
        return self.root.query_point(coord_3d)

    def query_spectral(self, coord_3d: np.ndarray) -> Optional[SpectralVoxel]:
        """Query spectral voxel at a point."""
        return self.root.query_voxel(coord_3d)

    def get_all_spectral_voxels(self) -> List[Tuple[np.ndarray, SpectralVoxel]]:
        """Get all spectral voxels with positions."""
        return self.root.collect_spectral_voxels()

    def find_spectral_neighbors(
        self,
        target_voxel: SpectralVoxel,
        max_distance: float = 0.5,
        max_results: int = 10
    ) -> List[Tuple[np.ndarray, SpectralVoxel, float]]:
        """
        Find spectrally similar voxels.

        Uses harmonic fingerprint similarity (spectral centroid, dominant freq, polarity).

        Args:
            target_voxel: Voxel to match against
            max_distance: Maximum spectral distance threshold
            max_results: Maximum number of neighbors to return

        Returns:
            List of (position, voxel, distance) tuples sorted by distance
        """
        all_voxels = self.get_all_spectral_voxels()
        neighbors = []

        for pos, voxel in all_voxels:
            dist = target_voxel.spectral_distance(voxel)
            if dist <= max_distance:
                neighbors.append((pos, voxel, dist))

        # Sort by spectral distance
        neighbors.sort(key=lambda x: x[2])
        return neighbors[:max_results]

    def cluster_by_polarity(self) -> Dict[str, List[Tuple[np.ndarray, SpectralVoxel]]]:
        """
        Cluster voxels by polarity (light/shadow/balanced).

        Returns:
            Dictionary mapping polarity -> list of (position, voxel) tuples
        """
        clusters: Dict[str, List[Tuple[np.ndarray, SpectralVoxel]]] = {
            'light': [],
            'shadow': [],
            'balanced': [],
            'unknown': []
        }

        for pos, voxel in self.get_all_spectral_voxels():
            polarity = voxel.polarity or 'unknown'
            if polarity in clusters:
                clusters[polarity].append((pos, voxel))
            else:
                clusters['unknown'].append((pos, voxel))

        return clusters

    def cluster_by_frequency_band(
        self,
        bands: List[Tuple[float, float]] = None
    ) -> Dict[str, List[Tuple[np.ndarray, SpectralVoxel]]]:
        """
        Cluster voxels by dominant frequency band.

        Args:
            bands: List of (min_freq, max_freq) tuples.
                   Default: low (0-300), mid (300-600), high (600+)

        Returns:
            Dictionary mapping band name -> list of (position, voxel) tuples
        """
        if bands is None:
            bands = [(0, 300), (300, 600), (600, float('inf'))]

        band_names = [f"{int(lo)}-{int(hi) if hi != float('inf') else 'inf'}Hz"
                      for lo, hi in bands]

        clusters: Dict[str, List[Tuple[np.ndarray, SpectralVoxel]]] = {
            name: [] for name in band_names
        }
        clusters['unknown'] = []

        for pos, voxel in self.get_all_spectral_voxels():
            if voxel.dominant_freq is None:
                clusters['unknown'].append((pos, voxel))
                continue

            for (lo, hi), name in zip(bands, band_names):
                if lo <= voxel.dominant_freq < hi:
                    clusters[name].append((pos, voxel))
                    break

        return clusters

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
    import hashlib

    print("=" * 70)
    print("  HYPERBOLIC OCTREE - Spectral Clustering Demo")
    print("=" * 70)
    print()

    octree = HyperbolicOctree(grid_size=64, max_depth=6)

    # Insert light realm points with fingerprints (near origin, high freq)
    print("[OCTREE] Inserting light realm points (near origin, high freq)...")
    for i in range(30):
        point = np.random.randn(3) * 0.3
        point = point / (np.linalg.norm(point) + 0.1) * 0.4
        fp_hash = hashlib.md5(f"light_{i}".encode()).hexdigest()[:16]
        octree.insert_with_fingerprint(
            point, 'light_realm',
            fingerprint_hash=fp_hash,
            spectral_centroid=650.0 + np.random.randn() * 50,
            dominant_freq=500.0 + np.random.randn() * 30,
            polarity='light'
        )

    # Insert shadow realm points with fingerprints (near boundary, low freq)
    print("[OCTREE] Inserting shadow realm points (near boundary, low freq)...")
    for i in range(30):
        point = np.random.randn(3)
        point = point / np.linalg.norm(point) * 0.85
        fp_hash = hashlib.md5(f"shadow_{i}".encode()).hexdigest()[:16]
        octree.insert_with_fingerprint(
            point, 'shadow_realm',
            fingerprint_hash=fp_hash,
            spectral_centroid=280.0 + np.random.randn() * 40,
            dominant_freq=220.0 + np.random.randn() * 20,
            polarity='shadow'
        )

    # Insert some balanced/path points
    print("[OCTREE] Inserting balanced path points...")
    for i in range(20):
        point = np.random.randn(3) * 0.5
        norm = np.linalg.norm(point)
        if norm > 0:
            point = point / norm * min(0.7, norm)
        fp_hash = hashlib.md5(f"path_{i}".encode()).hexdigest()[:16]
        octree.insert_with_fingerprint(
            point, 'path',
            fingerprint_hash=fp_hash,
            spectral_centroid=440.0 + np.random.randn() * 30,
            dominant_freq=440.0 + np.random.randn() * 50,
            polarity='balanced'
        )

    print()
    print(f"[OCTREE] Points inserted: {octree.point_count}")
    print(f"[OCTREE] Occupied voxels: {len(octree.get_occupied_voxels())}")
    print(f"[OCTREE] Occupancy ratio: {octree.occupancy_ratio():.6f}")
    print()

    # Test spectral clustering by polarity
    print("-" * 50)
    print("[CLUSTER] Clustering by polarity:")
    polarity_clusters = octree.cluster_by_polarity()
    for polarity, voxels in polarity_clusters.items():
        if voxels:
            avg_centroid = np.mean([v.spectral_centroid for _, v in voxels if v.spectral_centroid])
            print(f"    {polarity}: {len(voxels)} voxels, avg centroid: {avg_centroid:.1f}Hz")

    # Test frequency band clustering
    print()
    print("[CLUSTER] Clustering by frequency band:")
    freq_clusters = octree.cluster_by_frequency_band()
    for band, voxels in freq_clusters.items():
        if voxels:
            print(f"    {band}: {len(voxels)} voxels")

    # Test spectral neighbor search
    print()
    print("[SEARCH] Finding spectrally similar voxels...")
    target = SpectralVoxel(
        color='cyan',
        spectral_centroid=450.0,
        dominant_freq=440.0,
        polarity='balanced'
    )
    neighbors = octree.find_spectral_neighbors(target, max_distance=0.8, max_results=5)
    print(f"    Target: centroid=450Hz, dominant=440Hz, polarity=balanced")
    print(f"    Found {len(neighbors)} spectral neighbors:")
    for pos, voxel, dist in neighbors:
        print(f"      - pos={pos.round(2)}, centroid={voxel.spectral_centroid:.0f}Hz, dist={dist:.3f}")

    print()
    print("=" * 70)
    print("  Spectral clustering complete!")
    print("=" * 70)
