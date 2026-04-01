"""
HYDRA 2.5D Quadtree — Adaptive Terrain-Style Spatial Index with Octree Bridge
===============================================================================

Fuses classical 2.5D quadtree concepts (terrain LOD, variance-based subdivision,
DEM meshing, LiDAR point clouds) with the SCBE octree/lattice stack:

  - hydra/octree_sphere_grid.py  (SignedOctree, HyperbolicLattice25D, SphereGrid)
  - hydra/lattice25d_ops.py      (NoteRecord, text_metrics, build_lattice25d_payload)
  - hydra/color_dimension.py     (Sacred Tongue weights, ColorChannel)
  - hydra/voxel_storage.py       (6D Voxel, chladni_amplitude)

Concepts from the research (Grok 2.5D quadtree survey):
  1. Variance-based subdivision  — split when z-range in a quad exceeds threshold
  2. LOD (level of detail)       — coarser quads at distance, finer near camera/query
  3. DEM terrain meshing         — height-aware adaptive mesh from elevation data
  4. LiDAR point cloud storage   — Hermite data per quad leaf
  5. Overlap detection           — multiple layers per cell (buildings on terrain)
  6. Range queries               — spatial + height window searches
  7. Toroidal/hyperbolic bridge  — project quads into octree sign-space

Usage:
    from hydra.quadtree25d import Quadtree25D, QuadPoint

    qt = Quadtree25D(bounds=(-1, -1, 1, 1), max_depth=8)
    qt.insert(QuadPoint(0.3, 0.5, z=12.7, tongue="RU", authority="sealed"))
    qt.insert(QuadPoint(-0.2, 0.8, z=3.1, tongue="KO"))
    results = qt.range_query(-0.5, 0.0, 0.5, 1.0, z_min=0, z_max=15)
    mesh = qt.to_terrain_mesh()
    octree_projection = qt.project_to_octree(max_depth=6)
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np

from hydra.color_dimension import PHI, TONGUE_WEIGHTS
from hydra.voxel_storage import (
    chladni_amplitude,
    normalize_intent,
    intent_similarity,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_VARIANCE_THRESHOLD = 0.5  # z-range threshold to trigger subdivision
_DEFAULT_MAX_POINTS_PER_LEAF = 8  # max points before forced split
_DEFAULT_MAX_DEPTH = 10
_DEFAULT_LOD_BIAS = 1.0  # LOD distance scaling factor


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class QuadPoint:
    """A 2.5D point: (x, y) planar position + z height + semantic metadata."""

    x: float
    y: float
    z: float = 0.0
    tongue: str = "KO"
    authority: str = "public"
    intent_vector: Optional[List[float]] = None
    payload: Optional[Dict[str, Any]] = None
    point_id: str = ""

    def __post_init__(self):
        if not self.point_id:
            digest = hashlib.blake2s(
                f"{self.x:.8f}:{self.y:.8f}:{self.z:.8f}".encode(),
                digest_size=6,
            ).hexdigest()
            self.point_id = f"qp_{digest}"

    @property
    def tongue_weight(self) -> float:
        return TONGUE_WEIGHTS.get(self.tongue, 1.0)


class SubdivisionCriterion(Enum):
    """Why a quad node was subdivided."""

    NONE = "none"  # leaf, no subdivision
    VARIANCE = "variance"  # z-range exceeded threshold
    DENSITY = "density"  # too many points in leaf
    FORCED = "forced"  # explicit subdivision request
    LOD = "lod"  # level-of-detail refinement


@dataclass
class QuadBounds:
    """Axis-aligned bounding box for a quad node."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def cx(self) -> float:
        return (self.x_min + self.x_max) / 2.0

    @property
    def cy(self) -> float:
        return (self.y_min + self.y_max) / 2.0

    @property
    def width(self) -> float:
        return self.x_max - self.x_min

    @property
    def height(self) -> float:
        return self.y_max - self.y_min

    @property
    def area(self) -> float:
        return self.width * self.height

    def contains(self, x: float, y: float) -> bool:
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max

    def intersects(self, other: QuadBounds) -> bool:
        return not (
            self.x_max < other.x_min or self.x_min > other.x_max or self.y_max < other.y_min or self.y_min > other.y_max
        )

    def quadrant(self, index: int) -> QuadBounds:
        """Return child quadrant bounds. 0=SW, 1=SE, 2=NW, 3=NE."""
        cx, cy = self.cx, self.cy
        if index == 0:  # SW
            return QuadBounds(self.x_min, self.y_min, cx, cy)
        elif index == 1:  # SE
            return QuadBounds(cx, self.y_min, self.x_max, cy)
        elif index == 2:  # NW
            return QuadBounds(self.x_min, cy, cx, self.y_max)
        elif index == 3:  # NE
            return QuadBounds(cx, cy, self.x_max, self.y_max)
        raise ValueError(f"quadrant index must be 0-3, got {index}")


# ---------------------------------------------------------------------------
# QuadNode — recursive quadtree node
# ---------------------------------------------------------------------------


class QuadNode:
    """Adaptive quadtree node with z-variance subdivision.

    Each leaf stores points with (x, y, z) + semantic metadata.
    Interior nodes store aggregate z-statistics for LOD queries.
    Chladni modes scale by phi^depth (fractal resonance from octree system).
    """

    def __init__(
        self,
        bounds: QuadBounds,
        depth: int = 0,
        max_depth: int = _DEFAULT_MAX_DEPTH,
        max_points: int = _DEFAULT_MAX_POINTS_PER_LEAF,
        variance_threshold: float = _DEFAULT_VARIANCE_THRESHOLD,
        chladni_base_mode: Tuple[int, int] = (3, 2),
    ):
        self.bounds = bounds
        self.depth = depth
        self.max_depth = max_depth
        self.max_points = max_points
        self.variance_threshold = variance_threshold
        self.chladni_base_mode = chladni_base_mode

        self.children: Dict[int, QuadNode] = {}  # 0-3 (SW, SE, NW, NE)
        self.points: List[QuadPoint] = []
        self.is_leaf = True
        self.subdivision_reason = SubdivisionCriterion.NONE

        # Aggregate z-stats (updated on insert)
        self.z_min: float = float("inf")
        self.z_max: float = float("-inf")
        self.z_sum: float = 0.0
        self.point_count: int = 0

    @property
    def chladni_mode(self) -> Tuple[float, float]:
        """Fractal Chladni: modes scale by phi at each depth level."""
        m, n = self.chladni_base_mode
        scale = PHI**self.depth
        return (m * scale, n * scale)

    @property
    def chladni_value(self) -> float:
        """Chladni amplitude at node center, scaled by depth."""
        m, n = self.chladni_mode
        return chladni_amplitude(self.bounds.cx, self.bounds.cy, m, n)

    @property
    def z_range(self) -> float:
        if self.point_count == 0:
            return 0.0
        return self.z_max - self.z_min

    @property
    def z_mean(self) -> float:
        if self.point_count == 0:
            return 0.0
        return self.z_sum / self.point_count

    @property
    def z_variance(self) -> float:
        """Approximate z-variance from range (fast heuristic)."""
        return self.z_range

    def _update_z_stats(self, z: float) -> None:
        self.z_min = min(self.z_min, z)
        self.z_max = max(self.z_max, z)
        self.z_sum += z
        self.point_count += 1

    def _should_subdivide(self) -> Tuple[bool, SubdivisionCriterion]:
        """Check if this leaf should split based on variance or density."""
        if self.depth >= self.max_depth:
            return False, SubdivisionCriterion.NONE
        if len(self.points) > self.max_points:
            return True, SubdivisionCriterion.DENSITY
        if self.z_range > self.variance_threshold and len(self.points) > 1:
            return True, SubdivisionCriterion.VARIANCE
        return False, SubdivisionCriterion.NONE

    def _quadrant_for(self, x: float, y: float) -> int:
        """Determine which quadrant (0-3) a point falls into."""
        cx, cy = self.bounds.cx, self.bounds.cy
        if x < cx:
            return 2 if y >= cy else 0  # NW or SW
        else:
            return 3 if y >= cy else 1  # NE or SE

    def _subdivide(self, reason: SubdivisionCriterion) -> None:
        """Split this leaf into 4 children, redistribute points."""
        self.is_leaf = False
        self.subdivision_reason = reason

        for i in range(4):
            child_bounds = self.bounds.quadrant(i)
            self.children[i] = QuadNode(
                bounds=child_bounds,
                depth=self.depth + 1,
                max_depth=self.max_depth,
                max_points=self.max_points,
                variance_threshold=self.variance_threshold,
                chladni_base_mode=self.chladni_base_mode,
            )

        # Redistribute existing points
        for pt in self.points:
            q = self._quadrant_for(pt.x, pt.y)
            self.children[q]._insert_point(pt)
        self.points = []

    def _insert_point(self, point: QuadPoint) -> None:
        """Insert a point into this node (recursive)."""
        self._update_z_stats(point.z)

        if not self.is_leaf:
            q = self._quadrant_for(point.x, point.y)
            self.children[q]._insert_point(point)
            return

        self.points.append(point)
        should, reason = self._should_subdivide()
        if should:
            self._subdivide(reason)

    def query_range(
        self,
        region: QuadBounds,
        z_min: float = float("-inf"),
        z_max: float = float("inf"),
    ) -> List[QuadPoint]:
        """Range query: find all points in (x,y) region with z in [z_min, z_max]."""
        if not self.bounds.intersects(region):
            return []
        # Prune by z-range
        if self.point_count > 0 and (self.z_max < z_min or self.z_min > z_max):
            return []

        results: List[QuadPoint] = []
        if self.is_leaf:
            for pt in self.points:
                if region.contains(pt.x, pt.y) and z_min <= pt.z <= z_max:
                    results.append(pt)
        else:
            for child in self.children.values():
                results.extend(child.query_range(region, z_min, z_max))
        return results

    def query_nearest_k(
        self,
        x: float,
        y: float,
        k: int = 5,
        z_weight: float = 0.3,
    ) -> List[Tuple[QuadPoint, float]]:
        """Brute-force k-nearest in this subtree (2.5D distance)."""
        all_pts = self.all_points()
        scored = []
        for pt in all_pts:
            dx = pt.x - x
            dy = pt.y - y
            d2d = math.sqrt(dx * dx + dy * dy)
            d_total = d2d + z_weight * abs(pt.z)
            scored.append((pt, d_total))
        scored.sort(key=lambda t: t[1])
        return scored[:k]

    def all_points(self) -> List[QuadPoint]:
        """Collect all points in this subtree."""
        if self.is_leaf:
            return list(self.points)
        result: List[QuadPoint] = []
        for child in self.children.values():
            result.extend(child.all_points())
        return result

    def leaf_count(self) -> int:
        if self.is_leaf:
            return 1
        return sum(c.leaf_count() for c in self.children.values())

    def max_actual_depth(self) -> int:
        if self.is_leaf:
            return self.depth
        return max(c.max_actual_depth() for c in self.children.values())

    def visit_leaves(self, callback: Callable[[QuadNode], None]) -> None:
        """Visit every leaf node."""
        if self.is_leaf:
            callback(self)
        else:
            for child in self.children.values():
                child.visit_leaves(callback)


# ---------------------------------------------------------------------------
# Terrain mesh generation
# ---------------------------------------------------------------------------


@dataclass
class TerrainVertex:
    """Vertex in a terrain mesh generated from quadtree leaves."""

    x: float
    y: float
    z: float
    normal: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    chladni_amplitude: float = 0.0
    depth: int = 0
    tongue: str = "KO"


@dataclass
class TerrainTriangle:
    """A triangle in the terrain mesh, referencing vertex indices."""

    v0: int
    v1: int
    v2: int
    depth: int = 0


@dataclass
class TerrainMesh:
    """Adaptive terrain mesh produced from 2.5D quadtree."""

    vertices: List[TerrainVertex]
    triangles: List[TerrainTriangle]

    @property
    def vertex_count(self) -> int:
        return len(self.vertices)

    @property
    def triangle_count(self) -> int:
        return len(self.triangles)


def _build_mesh_from_quadtree(root: QuadNode) -> TerrainMesh:
    """Generate adaptive terrain mesh from quadtree leaves.

    Each leaf becomes 2 triangles (quad split diagonally).
    Finer leaves (deeper) produce denser mesh in high-variance terrain.
    """
    vertices: List[TerrainVertex] = []
    triangles: List[TerrainTriangle] = []
    vertex_cache: Dict[Tuple[float, float], int] = {}

    def _get_or_add_vertex(x: float, y: float, z: float, depth: int, tongue: str) -> int:
        key = (round(x, 8), round(y, 8))
        if key in vertex_cache:
            return vertex_cache[key]
        idx = len(vertices)
        m, n = root.chladni_base_mode
        scale = PHI**depth
        amp = chladni_amplitude(x, y, m * scale, n * scale)
        vertices.append(
            TerrainVertex(
                x=x,
                y=y,
                z=z,
                chladni_amplitude=amp,
                depth=depth,
                tongue=tongue,
            )
        )
        vertex_cache[key] = idx
        return idx

    def _process_leaf(node: QuadNode) -> None:
        b = node.bounds
        z_avg = node.z_mean
        tongue = "KO"
        if node.points:
            # Use the dominant tongue from points in this leaf
            tongue_counts: Dict[str, float] = {}
            for pt in node.points:
                tongue_counts[pt.tongue] = tongue_counts.get(pt.tongue, 0) + pt.tongue_weight
            tongue = max(tongue_counts, key=tongue_counts.get)

        # 4 corners of the quad leaf
        v_sw = _get_or_add_vertex(b.x_min, b.y_min, z_avg, node.depth, tongue)
        v_se = _get_or_add_vertex(b.x_max, b.y_min, z_avg, node.depth, tongue)
        v_nw = _get_or_add_vertex(b.x_min, b.y_max, z_avg, node.depth, tongue)
        v_ne = _get_or_add_vertex(b.x_max, b.y_max, z_avg, node.depth, tongue)

        # 2 triangles per quad (diagonal split)
        triangles.append(TerrainTriangle(v_sw, v_se, v_ne, depth=node.depth))
        triangles.append(TerrainTriangle(v_sw, v_ne, v_nw, depth=node.depth))

    root.visit_leaves(_process_leaf)
    return TerrainMesh(vertices=vertices, triangles=triangles)


# ---------------------------------------------------------------------------
# LOD (Level of Detail) evaluator
# ---------------------------------------------------------------------------


@dataclass
class LODQuery:
    """Camera/query position for LOD-based traversal."""

    x: float
    y: float
    z: float = 0.0
    max_screen_error: float = 2.0  # max geometric error in screen pixels
    viewport_height: int = 1080
    fov_rad: float = math.pi / 3.0  # 60 degrees


def lod_select(
    root: QuadNode,
    query: LODQuery,
    bias: float = _DEFAULT_LOD_BIAS,
) -> List[QuadNode]:
    """Select quadtree nodes at appropriate LOD for a given viewpoint.

    Uses geometric error metric: nodes farther from camera can be coarser.
    Returns the set of nodes (mix of leaves and interior) that satisfy LOD.
    """
    selected: List[QuadNode] = []

    def _traverse(node: QuadNode) -> None:
        dx = node.bounds.cx - query.x
        dy = node.bounds.cy - query.y
        dz = node.z_mean - query.z
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        dist = max(dist, 0.001)

        # Geometric error: z_range of this node / (distance * K)
        k = 2.0 * math.tan(query.fov_rad / 2.0) / query.viewport_height
        screen_error = (node.z_range * bias) / (dist * k) if k > 0 else 0

        if node.is_leaf or screen_error <= query.max_screen_error:
            selected.append(node)
        else:
            for child in node.children.values():
                _traverse(child)

    _traverse(root)
    return selected


# ---------------------------------------------------------------------------
# Quadtree25D — main interface, bridges to octree/lattice
# ---------------------------------------------------------------------------


class Quadtree25D:
    """Adaptive 2.5D quadtree with terrain-style subdivision.

    Bridges to:
      - SignedOctree (3D projection via z-height)
      - HyperbolicLattice25D (phase = normalized z-height)
      - SphereGrid (per-leaf embedded sphere slots)

    Subdivision is triggered by:
      - z-variance exceeding threshold (terrain-style)
      - point density exceeding max_points (classical quadtree)
      - explicit LOD refinement

    Sacred Tongue integration:
      - Each leaf aggregates tongue weights from contained points
      - Chladni modes scale by phi^depth (fractal resonance)
    """

    def __init__(
        self,
        bounds: Tuple[float, float, float, float] = (-1, -1, 1, 1),
        max_depth: int = _DEFAULT_MAX_DEPTH,
        max_points: int = _DEFAULT_MAX_POINTS_PER_LEAF,
        variance_threshold: float = _DEFAULT_VARIANCE_THRESHOLD,
        chladni_mode: Tuple[int, int] = (3, 2),
    ):
        x_min, y_min, x_max, y_max = bounds
        self.root = QuadNode(
            bounds=QuadBounds(x_min, y_min, x_max, y_max),
            depth=0,
            max_depth=max_depth,
            max_points=max_points,
            variance_threshold=variance_threshold,
            chladni_base_mode=chladni_mode,
        )
        self._point_index: Dict[str, QuadPoint] = {}

    def insert(self, point: QuadPoint) -> QuadPoint:
        """Insert a 2.5D point into the quadtree."""
        if not self.root.bounds.contains(point.x, point.y):
            raise ValueError(
                f"Point ({point.x}, {point.y}) outside bounds "
                f"[{self.root.bounds.x_min}, {self.root.bounds.x_max}] x "
                f"[{self.root.bounds.y_min}, {self.root.bounds.y_max}]"
            )
        self.root._insert_point(point)
        self._point_index[point.point_id] = point
        return point

    def insert_batch(self, points: List[QuadPoint]) -> int:
        """Insert multiple points. Returns count inserted."""
        count = 0
        for pt in points:
            try:
                self.insert(pt)
                count += 1
            except ValueError:
                pass
        return count

    def range_query(
        self,
        x_min: float,
        y_min: float,
        x_max: float,
        y_max: float,
        z_min: float = float("-inf"),
        z_max: float = float("inf"),
        tongue: Optional[str] = None,
        authority: Optional[str] = None,
    ) -> List[QuadPoint]:
        """Query points within a 2.5D bounding box, optionally filtered by tongue/authority."""
        region = QuadBounds(x_min, y_min, x_max, y_max)
        results = self.root.query_range(region, z_min, z_max)
        if tongue:
            results = [p for p in results if p.tongue == tongue]
        if authority:
            results = [p for p in results if p.authority == authority]
        return results

    def nearest(
        self,
        x: float,
        y: float,
        k: int = 5,
        z_weight: float = 0.3,
    ) -> List[Tuple[QuadPoint, float]]:
        """Find k nearest points using 2.5D distance."""
        return self.root.query_nearest_k(x, y, k, z_weight)

    def lod_nodes(self, query: LODQuery, bias: float = 1.0) -> List[QuadNode]:
        """Get LOD-appropriate nodes for a viewpoint."""
        return lod_select(self.root, query, bias)

    def to_terrain_mesh(self) -> TerrainMesh:
        """Generate adaptive terrain mesh from current quadtree state."""
        return _build_mesh_from_quadtree(self.root)

    def to_dem_grid(self, resolution: int = 64) -> np.ndarray:
        """Rasterize quadtree to a regular DEM grid via leaf interpolation.

        Returns a (resolution x resolution) array of z-values.
        Uses nearest-leaf z_mean for each grid cell.
        """
        b = self.root.bounds
        grid = np.zeros((resolution, resolution), dtype=np.float64)
        dx = b.width / resolution
        dy = b.height / resolution

        for iy in range(resolution):
            for ix in range(resolution):
                x = b.x_min + (ix + 0.5) * dx
                y = b.y_min + (iy + 0.5) * dy
                results = self.nearest(x, y, k=1, z_weight=0.0)
                if results:
                    grid[iy, ix] = results[0][0].z
                else:
                    grid[iy, ix] = self.root.z_mean

        return grid

    # -------------------------------------------------------------------
    # Bridge to SignedOctree
    # -------------------------------------------------------------------

    def project_to_octree(
        self,
        max_depth: int = 6,
        chladni_mode: Tuple[int, int] = (3, 2),
        z_scale: float = 0.98,
    ):
        """Project all 2.5D points into a SignedOctree (3D).

        z-height is normalized to [-0.99, 0.99] for octree unit ball.
        Returns a new SignedOctree with all points projected.
        """
        from hydra.octree_sphere_grid import SignedOctree

        octree = SignedOctree(max_depth=max_depth, chladni_mode=chladni_mode)
        all_pts = self.root.all_points()
        if not all_pts:
            return octree

        # Normalize z to [-1, 1] range
        z_vals = [p.z for p in all_pts]
        z_lo, z_hi = min(z_vals), max(z_vals)
        z_span = z_hi - z_lo if z_hi > z_lo else 1.0

        for pt in all_pts:
            z_norm = ((pt.z - z_lo) / z_span) * 2.0 - 1.0  # map to [-1, 1]
            z_clamped = max(-0.99, min(0.99, z_norm * z_scale))
            octree.insert(
                x=max(-0.99, min(0.99, pt.x)),
                y=max(-0.99, min(0.99, pt.y)),
                z=z_clamped,
                tongue=pt.tongue,
                authority=pt.authority,
                intent_vector=list(pt.intent_vector or [0, 0, 0]),
                intent_label=pt.point_id,
                payload=pt.payload or {},
                create_sphere_grid=True,
            )
        return octree

    # -------------------------------------------------------------------
    # Bridge to HyperbolicLattice25D
    # -------------------------------------------------------------------

    def project_to_lattice(
        self,
        cell_size: float = 0.25,
        max_depth: int = 6,
        phase_weight: float = 0.35,
    ):
        """Project all 2.5D points into a HyperbolicLattice25D.

        z-height is mapped to phase angle [0, 2π) for the cyclic dimension.
        Returns a new HyperbolicLattice25D with all points as bundles.
        """
        from hydra.octree_sphere_grid import HyperbolicLattice25D

        lattice = HyperbolicLattice25D(
            cell_size=cell_size,
            max_depth=max_depth,
            phase_weight=phase_weight,
        )
        all_pts = self.root.all_points()
        if not all_pts:
            return lattice

        z_vals = [p.z for p in all_pts]
        z_lo, z_hi = min(z_vals), max(z_vals)
        z_span = z_hi - z_lo if z_hi > z_lo else 1.0

        for pt in all_pts:
            z_norm = (pt.z - z_lo) / z_span  # [0, 1]
            phase_rad = z_norm * 2.0 * math.pi  # [0, 2π)
            lattice.insert_bundle(
                x=max(-0.99, min(0.99, pt.x)),
                y=max(-0.99, min(0.99, pt.y)),
                phase_rad=phase_rad,
                tongue=pt.tongue,
                authority=pt.authority,
                intent_vector=list(pt.intent_vector or [0, 0, 0]),
                intent_label=pt.point_id,
                payload=pt.payload or {},
                bundle_id=pt.point_id,
            )
        return lattice

    # -------------------------------------------------------------------
    # Stats & introspection
    # -------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """Quadtree statistics."""
        leaf_depths: List[int] = []
        leaf_sizes: List[int] = []
        variance_splits = 0
        density_splits = 0

        def _collect(node: QuadNode) -> None:
            nonlocal variance_splits, density_splits
            if node.is_leaf:
                leaf_depths.append(node.depth)
                leaf_sizes.append(len(node.points))
            else:
                if node.subdivision_reason == SubdivisionCriterion.VARIANCE:
                    variance_splits += 1
                elif node.subdivision_reason == SubdivisionCriterion.DENSITY:
                    density_splits += 1
                for child in node.children.values():
                    _collect(child)

        _collect(self.root)

        tongue_dist: Dict[str, int] = {}
        for pt in self._point_index.values():
            tongue_dist[pt.tongue] = tongue_dist.get(pt.tongue, 0) + 1

        return {
            "point_count": len(self._point_index),
            "leaf_count": len(leaf_depths),
            "max_depth_used": max(leaf_depths) if leaf_depths else 0,
            "avg_leaf_depth": sum(leaf_depths) / len(leaf_depths) if leaf_depths else 0,
            "avg_leaf_size": sum(leaf_sizes) / len(leaf_sizes) if leaf_sizes else 0,
            "variance_splits": variance_splits,
            "density_splits": density_splits,
            "z_range": [self.root.z_min, self.root.z_max] if self.root.point_count > 0 else [0, 0],
            "z_mean": self.root.z_mean,
            "chladni_base_mode": list(self.root.chladni_base_mode),
            "tongue_distribution": tongue_dist,
            "bounds": [
                self.root.bounds.x_min,
                self.root.bounds.y_min,
                self.root.bounds.x_max,
                self.root.bounds.y_max,
            ],
        }

    def leaf_heatmap(self) -> List[Dict[str, Any]]:
        """Return leaf bounds + z_mean for visualization."""
        cells: List[Dict[str, Any]] = []

        def _collect_leaf(node: QuadNode) -> None:
            cells.append(
                {
                    "bounds": [node.bounds.x_min, node.bounds.y_min, node.bounds.x_max, node.bounds.y_max],
                    "z_mean": node.z_mean,
                    "z_range": node.z_range,
                    "depth": node.depth,
                    "point_count": len(node.points),
                    "chladni_value": node.chladni_value,
                    "subdivision_reason": node.subdivision_reason.value,
                }
            )

        self.root.visit_leaves(_collect_leaf)
        return cells


# ---------------------------------------------------------------------------
# DEM loader — generate terrain from heightmap functions
# ---------------------------------------------------------------------------


def generate_terrain_points(
    func: Callable[[float, float], float],
    bounds: Tuple[float, float, float, float] = (-1, -1, 1, 1),
    resolution: int = 32,
    tongue: str = "KO",
    authority: str = "public",
) -> List[QuadPoint]:
    """Sample a height function on a grid to produce QuadPoints.

    Useful for testing with synthetic terrain (sine hills, fractal noise, etc).
    """
    x_min, y_min, x_max, y_max = bounds
    dx = (x_max - x_min) / resolution
    dy = (y_max - y_min) / resolution
    points: List[QuadPoint] = []
    tongues = list(TONGUE_WEIGHTS.keys()) or ["KO"]

    for iy in range(resolution):
        for ix in range(resolution):
            x = x_min + (ix + 0.5) * dx
            y = y_min + (iy + 0.5) * dy
            z = func(x, y)
            t = tongues[(ix + iy) % len(tongues)] if tongue == "auto" else tongue
            points.append(QuadPoint(x=x, y=y, z=z, tongue=t, authority=authority))

    return points


def sine_hills(x: float, y: float) -> float:
    """Synthetic terrain: overlapping sine hills."""
    return 3.0 * math.sin(x * 2.5) * math.cos(y * 2.5) + 1.5 * math.sin(x * 5.0 + 1.0) + 0.8 * math.cos(y * 7.0 - 0.5)


def ridge_terrain(x: float, y: float) -> float:
    """Synthetic terrain: sharp ridge along diagonal."""
    d = abs(x - y) / math.sqrt(2)
    return 5.0 * math.exp(-d * d * 8.0) + 0.5 * math.sin(x * 3) * math.cos(y * 3)


def flat_with_spikes(x: float, y: float) -> float:
    """Synthetic terrain: mostly flat with a few sharp spikes."""
    base = 0.1
    for cx, cy, h in [(-0.5, 0.3, 8.0), (0.4, -0.2, 6.0), (0.0, 0.7, 10.0)]:
        dx, dy = x - cx, y - cy
        r2 = dx * dx + dy * dy
        base += h * math.exp(-r2 * 50.0)
    return base


# ---------------------------------------------------------------------------
# INTEROP_MATRIX extension for 2.5D quadtree
# ---------------------------------------------------------------------------

QUADTREE25D_INTEROP = {
    "QuadPoint": {
        "python": "QuadPoint(x, y, z, tongue, authority, intent_vector, payload)",
        "typescript": "interface QuadPoint { x: number; y: number; z: number; tongue: string; authority: string; }",
        "rust": "struct QuadPoint { x: f64, y: f64, z: f64, tongue: String, authority: String }",
        "sql": "CREATE TABLE quad_points (id TEXT, x REAL, y REAL, z REAL, tongue TEXT, authority TEXT)",
        "wasm": "QuadPoint { x: f64, y: f64, z: f64 } via wasm-bindgen",
        "html_css": "<div class='quad-point' data-x data-y data-z style='left: calc(x%); top: calc(y%); height: calc(z*scale)'></div>",
        "solidity": "struct QuadPoint { int256 x; int256 y; int256 z; string tongue; }",
        "go": "type QuadPoint struct { X, Y, Z float64; Tongue, Authority string }",
        "glsl": "struct QuadPoint { vec3 pos; float tongue_weight; };",
    },
    "QuadNode": {
        "python": "QuadNode(bounds, depth, children, points, z_stats)",
        "typescript": "class QuadNode { bounds: QuadBounds; children: Map<number, QuadNode>; points: QuadPoint[]; }",
        "rust": "struct QuadNode { bounds: QuadBounds, children: [Option<Box<QuadNode>>; 4], points: Vec<QuadPoint> }",
        "sql": "CREATE TABLE quad_nodes (id TEXT, x_min REAL, y_min REAL, x_max REAL, y_max REAL, depth INT, z_min REAL, z_max REAL)",
        "go": "type QuadNode struct { Bounds QuadBounds; Children [4]*QuadNode; Points []QuadPoint }",
        "glsl": "uniform sampler2D quadtree_texture; // encoded node hierarchy",
    },
    "variance_subdivision": {
        "python": "z_range > threshold → subdivide into 4 children",
        "typescript": "if (zRange > threshold) { this.subdivide(); }",
        "rust": "if z_range > threshold { self.subdivide() }",
        "sql": "SELECT * FROM quad_nodes WHERE z_max - z_min > :threshold",
        "glsl": "if (z_variance > threshold) { /* sample finer LOD */ }",
    },
    "terrain_mesh": {
        "python": "TerrainMesh(vertices, triangles) — 2 tris per leaf quad",
        "typescript": "interface TerrainMesh { vertices: Float32Array; indices: Uint32Array; }",
        "rust": "struct TerrainMesh { vertices: Vec<TerrainVertex>, indices: Vec<[u32; 3]> }",
        "wasm": "export terrain mesh as flat f32/u32 buffers for WebGL",
        "html_css": "<canvas id='terrain'> with WebGL or Three.js rendering",
        "glsl": "attribute vec3 position; attribute float chladni_amp; // terrain vertex shader",
        "go": "type TerrainMesh struct { Vertices []TerrainVertex; Triangles [][3]int }",
    },
    "lod_select": {
        "python": "lod_select(root, LODQuery) → nodes at appropriate detail level",
        "typescript": "lodSelect(root: QuadNode, camera: LODQuery): QuadNode[]",
        "rust": "fn lod_select(root: &QuadNode, query: &LODQuery) -> Vec<&QuadNode>",
        "glsl": "// GPU-side LOD: mipmap terrain texture based on distance",
        "go": "func LODSelect(root *QuadNode, query LODQuery) []*QuadNode",
    },
    "octree_bridge": {
        "python": "quadtree25d.project_to_octree() → SignedOctree with z-normalized points",
        "typescript": "quadtree.projectToOctree(): SignedOctree",
        "rust": "fn project_to_octree(&self) -> SignedOctree",
    },
    "lattice_bridge": {
        "python": "quadtree25d.project_to_lattice() → HyperbolicLattice25D with z→phase mapping",
        "typescript": "quadtree.projectToLattice(): HyperbolicLattice25D",
        "rust": "fn project_to_lattice(&self) -> HyperbolicLattice25D",
    },
}


# ---------------------------------------------------------------------------
# Demo / CLI
# ---------------------------------------------------------------------------


def demo() -> Dict[str, Any]:
    """Run a full demo: synthetic terrain → quadtree → mesh → octree → lattice."""
    print("=== HYDRA 2.5D Quadtree Demo ===\n")

    # 1. Create quadtree with terrain
    qt = Quadtree25D(
        bounds=(-1, -1, 1, 1),
        max_depth=8,
        max_points=4,
        variance_threshold=0.8,
    )

    # 2. Generate terrain points (sine hills)
    points = generate_terrain_points(sine_hills, resolution=24, tongue="auto")
    inserted = qt.insert_batch(points)
    print(f"[1] Inserted {inserted} terrain points (sine hills, 24x24 grid)")

    # 3. Generate more terrain (ridge) for high-variance area
    ridge_pts = generate_terrain_points(
        ridge_terrain,
        bounds=(-0.5, -0.5, 0.5, 0.5),
        resolution=16,
        tongue="DR",
        authority="sealed",
    )
    inserted2 = qt.insert_batch(ridge_pts)
    print(f"[2] Inserted {inserted2} ridge terrain points (16x16, tongue=DR)")

    # 4. Add spike points for extreme variance
    spike_pts = generate_terrain_points(
        flat_with_spikes,
        bounds=(-0.8, -0.8, 0.8, 0.8),
        resolution=12,
        tongue="RU",
    )
    inserted3 = qt.insert_batch(spike_pts)
    print(f"[3] Inserted {inserted3} spike terrain points (12x12, tongue=RU)")

    # 5. Stats
    stats = qt.stats()
    print(f"\n[4] Quadtree stats:")
    print(f"    Points: {stats['point_count']}")
    print(f"    Leaves: {stats['leaf_count']}")
    print(f"    Max depth used: {stats['max_depth_used']}")
    print(f"    Avg leaf depth: {stats['avg_leaf_depth']:.2f}")
    print(f"    Variance splits: {stats['variance_splits']}")
    print(f"    Density splits: {stats['density_splits']}")
    print(f"    Z range: [{stats['z_range'][0]:.2f}, {stats['z_range'][1]:.2f}]")
    print(f"    Tongues: {stats['tongue_distribution']}")

    # 6. Range query
    results = qt.range_query(-0.3, -0.3, 0.3, 0.3, z_min=2.0, z_max=8.0)
    print(f"\n[5] Range query (-0.3..0.3, z=2..8): {len(results)} points")

    # 7. LOD query
    lod_q = LODQuery(x=0.0, y=0.0, z=10.0, max_screen_error=4.0)
    lod_nodes = qt.lod_nodes(lod_q)
    print(f"[6] LOD query (overhead view, z=10): {len(lod_nodes)} nodes selected")

    # 8. Terrain mesh
    mesh = qt.to_terrain_mesh()
    print(f"[7] Terrain mesh: {mesh.vertex_count} vertices, {mesh.triangle_count} triangles")

    # 9. DEM grid
    dem = qt.to_dem_grid(resolution=16)
    print(f"[8] DEM grid (16x16): min={dem.min():.2f}, max={dem.max():.2f}, mean={dem.mean():.2f}")

    # 10. Project to octree
    octree = qt.project_to_octree(max_depth=6)
    octree_stats = octree.stats()
    print(f"\n[9] Octree projection: {octree_stats.get('count', 0)} voxels")

    # 11. Project to lattice
    lattice = qt.project_to_lattice(cell_size=0.3)
    lattice_stats = lattice.stats()
    print(
        f"[10] Lattice projection: {lattice_stats['bundle_count']} bundles, "
        f"{lattice_stats['overlap_cells']} overlap cells, "
        f"{lattice_stats['lace_edges']} lace edges"
    )

    # 12. Leaf heatmap
    heatmap = qt.leaf_heatmap()
    variance_leaves = [h for h in heatmap if h["subdivision_reason"] == "variance"]
    density_leaves = [h for h in heatmap if h["point_count"] > 0]
    print(
        f"\n[11] Leaf heatmap: {len(heatmap)} total, "
        f"{len(variance_leaves)} from variance splits, "
        f"{len(density_leaves)} occupied"
    )

    print(
        f"\n[12] Interop matrix covers {len(QUADTREE25D_INTEROP)} concepts "
        f"across {len(set(lang for concept in QUADTREE25D_INTEROP.values() for lang in concept))} languages"
    )

    print("\n=== Demo complete ===")
    return {
        "stats": stats,
        "mesh": {"vertices": mesh.vertex_count, "triangles": mesh.triangle_count},
        "dem_shape": list(dem.shape),
        "octree_voxels": octree_stats.get("count", 0),
        "lattice_bundles": lattice_stats["bundle_count"],
        "lod_nodes": len(lod_nodes),
        "range_query_hits": len(results),
        "interop_concepts": len(QUADTREE25D_INTEROP),
    }


# ---------------------------------------------------------------------------
# Grok-style AdaptiveQuadTree25D — classic variant with np.var subdivision
# ---------------------------------------------------------------------------
# Merged from Grok research reference implementation.
# Provides AABB-based (origin+size) API for game-engine / GIS compatibility.
# Bridges to Quadtree25D via .to_hydra_quadtree() for octree/lattice interop.


class Point2D5:
    """Simple 2.5D point (game-engine / GIS style)."""

    __slots__ = ("x", "y", "z")

    def __init__(self, x: float, y: float, z: float = 0.0):
        self.x = x
        self.y = y
        self.z = z


class AABB2D:
    """Axis-aligned bounding box (origin + size, GIS convention)."""

    __slots__ = ("x", "y", "width", "height")

    def __init__(self, x: float, y: float, width: float, height: float):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def contains(self, point: Point2D5) -> bool:
        return self.x <= point.x < self.x + self.width and self.y <= point.y < self.y + self.height

    def intersects(self, other: AABB2D) -> bool:
        return not (
            other.x > self.x + self.width
            or other.x + other.width < self.x
            or other.y > self.y + self.height
            or other.y + other.height < self.y
        )


class AdaptiveQuadTree25D:
    """Classic adaptive 2.5D quadtree with np.var-based subdivision.

    Game-engine / GIS convention: AABB origin+size, capacity-based splitting,
    variance threshold for terrain-aware refinement.

    Use .to_hydra_quadtree() to bridge into the HYDRA octree/lattice stack.
    """

    def __init__(
        self,
        boundary: AABB2D,
        capacity: int = 4,
        max_depth: int = 8,
        variance_threshold: float = 1.0,
    ):
        self.boundary = boundary
        self.capacity = capacity
        self.max_depth = max_depth
        self.variance_threshold = variance_threshold
        self.points: List[Point2D5] = []
        self.divided = False
        self.northwest: Optional[AdaptiveQuadTree25D] = None
        self.northeast: Optional[AdaptiveQuadTree25D] = None
        self.southwest: Optional[AdaptiveQuadTree25D] = None
        self.southeast: Optional[AdaptiveQuadTree25D] = None
        self.lod_level: int = 0

    def subdivide(self) -> None:
        x, y = self.boundary.x, self.boundary.y
        w, h = self.boundary.width / 2, self.boundary.height / 2

        self.northwest = AdaptiveQuadTree25D(
            AABB2D(x, y, w, h), self.capacity, self.max_depth - 1, self.variance_threshold
        )
        self.northeast = AdaptiveQuadTree25D(
            AABB2D(x + w, y, w, h), self.capacity, self.max_depth - 1, self.variance_threshold
        )
        self.southwest = AdaptiveQuadTree25D(
            AABB2D(x, y + h, w, h), self.capacity, self.max_depth - 1, self.variance_threshold
        )
        self.southeast = AdaptiveQuadTree25D(
            AABB2D(x + w, y + h, w, h), self.capacity, self.max_depth - 1, self.variance_threshold
        )

        for child in (self.northwest, self.northeast, self.southwest, self.southeast):
            child.lod_level = self.lod_level + 1

        self.divided = True

        for p in self.points:
            self._insert_to_child(p)
        self.points = []

    def _compute_variance(self) -> float:
        if not self.points:
            return 0.0
        heights = np.array([p.z for p in self.points])
        return float(np.var(heights))

    def insert(self, point: Point2D5) -> bool:
        if not self.boundary.contains(point):
            return False

        if len(self.points) < self.capacity and not self.divided and self.max_depth > 0:
            self.points.append(point)
            if self._compute_variance() > self.variance_threshold:
                self.subdivide()
            return True

        if not self.divided and self.max_depth > 0:
            self.subdivide()

        return self._insert_to_child(point)

    def _insert_to_child(self, point: Point2D5) -> bool:
        for child in (self.northwest, self.northeast, self.southwest, self.southeast):
            if child and child.boundary.contains(point):
                return child.insert(point)
        return False

    def query_range(self, range_aabb: AABB2D) -> List[Point2D5]:
        result: List[Point2D5] = []
        if not self.boundary.intersects(range_aabb):
            return result

        for p in self.points:
            if range_aabb.contains(p):
                result.append(p)

        if self.divided:
            for child in (self.northwest, self.northeast, self.southwest, self.southeast):
                if child:
                    result.extend(child.query_range(range_aabb))
        return result

    def all_points(self) -> List[Point2D5]:
        """Collect all points recursively."""
        if not self.divided:
            return list(self.points)
        result = list(self.points)
        for child in (self.northwest, self.northeast, self.southwest, self.southeast):
            if child:
                result.extend(child.all_points())
        return result

    def get_lod_mesh(self) -> Any:
        """Generate LOD mesh representation for rendering."""
        if not self.divided:
            if self.points:
                avg_z = sum(p.z for p in self.points) / len(self.points)
                return {
                    "boundary": {
                        "x": self.boundary.x,
                        "y": self.boundary.y,
                        "width": self.boundary.width,
                        "height": self.boundary.height,
                    },
                    "height": avg_z,
                    "lod": self.lod_level,
                }
            return None

        mesh = []
        for child in (self.northwest, self.northeast, self.southwest, self.southeast):
            if child:
                m = child.get_lod_mesh()
                if m is not None:
                    mesh.append(m)
        return mesh if mesh else None

    def leaf_count(self) -> int:
        if not self.divided:
            return 1
        total = 0
        for child in (self.northwest, self.northeast, self.southwest, self.southeast):
            if child:
                total += child.leaf_count()
        return total

    # -------------------------------------------------------------------
    # Hyperbolic lattice integration (refined from stub)
    # -------------------------------------------------------------------

    def integrate_hyperbolic_lattice(self, lattice) -> None:
        """Fuse quadtree leaves into HyperbolicLattice25D as bundles.

        For each leaf node, compute centroid position and insert as a bundle.
        LOD level controls bundle density — deeper leaves get finer lattice cells.
        Semantic tongue weighting can force higher subdivision in priority areas.
        """
        if self.divided:
            for child in (self.northwest, self.northeast, self.southwest, self.southeast):
                if child:
                    child.integrate_hyperbolic_lattice(lattice)
        elif self.points:
            avg_x = sum(p.x for p in self.points) / len(self.points)
            avg_y = sum(p.y for p in self.points) / len(self.points)
            avg_z = sum(p.z for p in self.points) / len(self.points)

            # Normalize to Poincare disk
            b = self.boundary
            nx = 2.0 * (avg_x - b.x) / b.width - 1.0 if b.width > 0 else 0.0
            ny = 2.0 * (avg_y - b.y) / b.height - 1.0 if b.height > 0 else 0.0
            nx = max(-0.99, min(0.99, nx * 0.95))
            ny = max(-0.99, min(0.99, ny * 0.95))

            # z → phase mapping for cyclic dimension
            phase_rad = (avg_z % (2 * math.pi)) if avg_z >= 0 else ((avg_z % (2 * math.pi)))

            lattice.insert_bundle(
                x=nx,
                y=ny,
                phase_rad=phase_rad,
                tongue="KO",
                authority="public",
                intent_vector=[0, 0, 0],
                intent_label=f"leaf-lod{self.lod_level}",
                payload={
                    "lod_level": self.lod_level,
                    "point_count": len(self.points),
                    "z_mean": avg_z,
                    "variance": self._compute_variance(),
                },
            )

    # -------------------------------------------------------------------
    # Signed octree extrusion (refined from stub)
    # -------------------------------------------------------------------

    def to_signed_octree_direct(self, octree) -> None:
        """Extrude 2.5D quadtree into signed 3D octants.

        Maps 2D quadrants to 3D octants with sign-based partitioning.
        z-height determines sign_z, enabling mirror operations across XY-plane.
        """
        center_x = self.boundary.x + self.boundary.width / 2
        center_y = self.boundary.y + self.boundary.height / 2

        b = self.boundary
        for p in self.points:
            # Normalize to [-1, 1]
            nx = 2.0 * (p.x - b.x) / b.width - 1.0 if b.width > 0 else 0.0
            ny = 2.0 * (p.y - b.y) / b.height - 1.0 if b.height > 0 else 0.0
            nx = max(-0.99, min(0.99, nx * 0.95))
            ny = max(-0.99, min(0.99, ny * 0.95))
            nz = max(-0.99, min(0.99, (p.z / max(abs(p.z), 1.0)) * 0.95))

            octree.insert(
                x=nx,
                y=ny,
                z=nz,
                tongue="KO",
                authority="public",
                intent_vector=[0, 0, 0],
                intent_label=f"grok-pt-lod{self.lod_level}",
                payload={"source": "AdaptiveQuadTree25D", "lod": self.lod_level},
            )

        if self.divided:
            for child in (self.northwest, self.northeast, self.southwest, self.southeast):
                if child:
                    child.to_signed_octree_direct(octree)

    # -------------------------------------------------------------------
    # Bridge to HYDRA Quadtree25D
    # -------------------------------------------------------------------

    def to_hydra_quadtree(
        self,
        max_depth: int = _DEFAULT_MAX_DEPTH,
        max_points: int = _DEFAULT_MAX_POINTS_PER_LEAF,
        variance_threshold: float = _DEFAULT_VARIANCE_THRESHOLD,
    ) -> Quadtree25D:
        """Convert this classic quadtree into a HYDRA Quadtree25D.

        Maps AABB coordinates to [-1, 1] range for octree/lattice compatibility.
        """
        b = self.boundary
        qt = Quadtree25D(
            bounds=(-1, -1, 1, 1),
            max_depth=max_depth,
            max_points=max_points,
            variance_threshold=variance_threshold,
        )
        all_pts = self.all_points()
        if not all_pts:
            return qt

        # Normalize (x, y) from AABB space to [-1, 1]
        for p in all_pts:
            nx = 2.0 * (p.x - b.x) / b.width - 1.0 if b.width > 0 else 0.0
            ny = 2.0 * (p.y - b.y) / b.height - 1.0 if b.height > 0 else 0.0
            nx = max(-0.999, min(0.999, nx))
            ny = max(-0.999, min(0.999, ny))
            qt.insert(QuadPoint(x=nx, y=ny, z=p.z))

        return qt

    # -------------------------------------------------------------------
    # Bridge to SignedOctree
    # -------------------------------------------------------------------

    def project_to_octree(self, max_depth: int = 6, chladni_mode: Tuple[int, int] = (3, 2)):
        """Bridge to SignedOctree via HYDRA Quadtree25D."""
        return self.to_hydra_quadtree().project_to_octree(max_depth=max_depth, chladni_mode=chladni_mode)

    # -------------------------------------------------------------------
    # Bridge to HyperbolicLattice25D
    # -------------------------------------------------------------------

    def project_to_lattice(self, cell_size: float = 0.25, max_depth: int = 6):
        """Bridge to HyperbolicLattice25D via HYDRA Quadtree25D."""
        return self.to_hydra_quadtree().project_to_lattice(cell_size=cell_size, max_depth=max_depth)


if __name__ == "__main__":
    demo()
