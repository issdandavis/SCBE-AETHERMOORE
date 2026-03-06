"""
HYDRA Hyperbolic Terrain Mapping — Poincaré Disk Terrain with Geodesic Navigation
===================================================================================

Maps Euclidean terrain data into the Poincaré disk model of hyperbolic space,
enabling exponential LOD compression, geodesic pathfinding, eccentricity-based
feature detection, and conformal visualization.

Integrates with:
  - hydra/quadtree25d.py       (Quadtree25D, terrain mesh, DEM grid)
  - hydra/octree_sphere_grid.py (SignedOctree, HyperbolicLattice25D, Poincaré distance)
  - hydra/color_dimension.py    (Sacred Tongue weights, ColorChannel)

Key concepts from hyperbolic terrain research:
  1. Poincaré disk model       — infinite terrain in a finite circle
  2. Mobius transformations    — isometries of hyperbolic space (translations/rotations)
  3. Geodesics                 — circular arcs orthogonal to disk boundary
  4. Exponential LOD           — distance explodes near boundary ->natural compression
  5. Eccentricity terrain      — identify hills/valleys/plateaus in graph structure
  6. Conformal mapping         — angle-preserving Euclidean <-> hyperbolic transforms
  7. Hyperbolic Voronoi        — territory partitioning under curved metric

Usage:
    from hydra.hyperbolic_terrain import (
        HyperbolicTerrain, PoincarePoint, mobius_translate,
        geodesic_path, eccentricity_terrain,
    )

    terrain = HyperbolicTerrain()
    terrain.add_elevation_grid(dem_array, bounds=(-1, -1, 1, 1))
    path = terrain.geodesic_between(PoincarePoint(0.1, 0.2), PoincarePoint(-0.5, 0.3))
    features = terrain.eccentricity_map()
    mesh = terrain.to_conformal_mesh()
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
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

_BOUNDARY_EPSILON = 1e-6       # keep points strictly inside unit disk
_GEODESIC_SEGMENTS = 64        # segments for geodesic arc approximation
_MAX_POINCARE_RADIUS = 0.999   # clamp radius to avoid boundary singularity


# ---------------------------------------------------------------------------
# Poincaré Disk primitives
# ---------------------------------------------------------------------------

@dataclass
class PoincarePoint:
    """A point in the Poincaré disk model of hyperbolic space.

    Must satisfy x² + y² < 1 (open unit disk).
    z stores elevation/height data for terrain mapping.
    """
    x: float
    y: float
    z: float = 0.0  # elevation in terrain context
    tongue: str = "KO"
    authority: str = "public"
    intent_vector: Optional[List[float]] = None
    point_id: str = ""

    def __post_init__(self):
        # Clamp to open disk
        r2 = self.x * self.x + self.y * self.y
        if r2 >= 1.0:
            scale = _MAX_POINCARE_RADIUS / math.sqrt(r2)
            self.x *= scale
            self.y *= scale
        if not self.point_id:
            digest = hashlib.blake2s(
                f"{self.x:.8f}:{self.y:.8f}:{self.z:.8f}".encode(),
                digest_size=6,
            ).hexdigest()
            self.point_id = f"hp_{digest}"

    @property
    def radius(self) -> float:
        """Distance from disk center (Euclidean)."""
        return math.sqrt(self.x * self.x + self.y * self.y)

    @property
    def angle(self) -> float:
        """Angle in radians from positive x-axis."""
        return math.atan2(self.y, self.x)

    @property
    def conformal_factor(self) -> float:
        """The conformal scaling factor λ = 2/(1-|z|²).

        Points near boundary have enormous conformal factor ->hyperbolic
        distances grow exponentially even though Euclidean distances shrink.
        """
        r2 = self.x * self.x + self.y * self.y
        denom = 1.0 - r2
        if denom <= _BOUNDARY_EPSILON:
            return 2.0 / _BOUNDARY_EPSILON
        return 2.0 / denom

    @property
    def tongue_weight(self) -> float:
        return TONGUE_WEIGHTS.get(self.tongue, 1.0)

    def to_klein(self) -> Tuple[float, float]:
        """Convert to Klein (Beltrami-Klein) model coordinates."""
        r2 = self.x * self.x + self.y * self.y
        denom = 1.0 + r2
        return (2.0 * self.x / denom, 2.0 * self.y / denom)

    def to_half_plane(self) -> Tuple[float, float]:
        """Convert to upper half-plane model (u, v) where v > 0."""
        denom = (1.0 - self.y) ** 2 + self.x ** 2
        if denom < _BOUNDARY_EPSILON:
            return (0.0, 1e6)
        u = 2.0 * self.x / denom
        v = (1.0 - self.x ** 2 - self.y ** 2) / denom
        return (u, max(v, _BOUNDARY_EPSILON))


def poincare_distance(a: PoincarePoint, b: PoincarePoint) -> float:
    """Hyperbolic distance in the Poincaré disk model.

    d(a,b) = acosh(1 + 2||a-b||² / ((1-||a||²)(1-||b||²)))

    This is the canonical formula used throughout SCBE-AETHERMOORE.
    """
    na2 = a.x * a.x + a.y * a.y
    nb2 = b.x * b.x + b.y * b.y
    if na2 >= 1.0 or nb2 >= 1.0:
        return float("inf")

    dx = a.x - b.x
    dy = a.y - b.y
    diff_sq = dx * dx + dy * dy

    denom = (1.0 - na2) * (1.0 - nb2)
    if denom <= 0:
        return float("inf")

    arg = 1.0 + (2.0 * diff_sq) / denom
    return math.acosh(max(1.0, arg))


def poincare_distance_with_elevation(
    a: PoincarePoint,
    b: PoincarePoint,
    z_weight: float = 0.3,
) -> float:
    """Hyperbolic distance with terrain elevation component.

    Combines planar Poincaré distance with vertical displacement.
    z_weight controls how much elevation difference contributes.
    """
    d_h = poincare_distance(a, b)
    d_z = abs(a.z - b.z)
    return d_h + z_weight * d_z


# ---------------------------------------------------------------------------
# Mobius transformations — isometries of the Poincaré disk
# ---------------------------------------------------------------------------

def mobius_translate(point: PoincarePoint, center: PoincarePoint) -> PoincarePoint:
    """Mobius translation: move `point` so that `center` maps to the origin.

    Formula: T_a(z) = (z - a) / (1 - ā·z)
    where a = center, z = point (treated as complex numbers).

    This is an isometry of the Poincaré disk — preserves all distances.
    """
    # Treat as complex: z = x + iy, a = cx + icy
    zx, zy = point.x, point.y
    ax, ay = center.x, center.y

    # Numerator: z - a
    nx = zx - ax
    ny = zy - ay

    # Denominator: 1 - conj(a)*z = 1 - (ax - iay)(zx + izy)
    # = 1 - (ax*zx + ay*zy) - i(ax*zy - ay*zx)
    dx = 1.0 - (ax * zx + ay * zy)
    dy = -(ax * zy - ay * zx)

    # Complex division: (nx + iny) / (dx + idy)
    denom = dx * dx + dy * dy
    if denom < _BOUNDARY_EPSILON:
        return PoincarePoint(0.0, 0.0, point.z, point.tongue, point.authority)

    rx = (nx * dx + ny * dy) / denom
    ry = (ny * dx - nx * dy) / denom

    return PoincarePoint(rx, ry, point.z, point.tongue, point.authority)


def mobius_gyration(a: PoincarePoint, b: PoincarePoint) -> float:
    """Gyration angle from the Mobius addition of a and b.

    Used in gyrovector algebra for hyperbolic operations.
    """
    cross = a.x * b.y - a.y * b.x
    dot = a.x * b.x + a.y * b.y
    na2 = a.x * a.x + a.y * a.y
    nb2 = b.x * b.x + b.y * b.y
    denom = 1.0 + 2 * dot + na2 * nb2
    if abs(denom) < _BOUNDARY_EPSILON:
        return 0.0
    return 2.0 * math.atan2(cross, denom)


# ---------------------------------------------------------------------------
# Geodesic paths — shortest paths on the Poincaré disk
# ---------------------------------------------------------------------------

def geodesic_path(
    a: PoincarePoint,
    b: PoincarePoint,
    num_segments: int = _GEODESIC_SEGMENTS,
) -> List[PoincarePoint]:
    """Compute the geodesic (shortest hyperbolic path) between two points.

    In the Poincaré disk, geodesics are either:
    - Diameters (if both points are collinear with the center)
    - Circular arcs orthogonal to the unit circle boundary

    We parameterize via Mobius interpolation:
    1. Translate so a ->origin
    2. Interpolate along the diameter (which IS a geodesic through origin)
    3. Translate back
    """
    if num_segments < 2:
        return [a, b]

    # Translate b so that a ->origin
    b_translated = mobius_translate(b, a)

    # In the translated frame, the geodesic from origin to b' is a straight line
    # (diameters are geodesics through the center)
    path: List[PoincarePoint] = []
    for i in range(num_segments + 1):
        t = i / num_segments
        # Linear interpolation in translated frame (along diameter)
        px = b_translated.x * t
        py = b_translated.y * t
        # Translate back: apply inverse Mobius (translate by -a = a itself since T_a^(-1) = T_{-a})
        inv_center = PoincarePoint(-a.x, -a.y)
        translated_pt = PoincarePoint(px, py)
        original_pt = mobius_translate(translated_pt, inv_center)

        # Interpolate elevation linearly
        z = a.z * (1 - t) + b.z * t
        path.append(PoincarePoint(
            original_pt.x, original_pt.y, z,
            tongue=a.tongue if t < 0.5 else b.tongue,
            authority=a.authority if t < 0.5 else b.authority,
        ))

    return path


def geodesic_length(a: PoincarePoint, b: PoincarePoint) -> float:
    """Length of the geodesic between two points (= Poincaré distance)."""
    return poincare_distance(a, b)


def geodesic_midpoint(a: PoincarePoint, b: PoincarePoint) -> PoincarePoint:
    """Midpoint of the geodesic between a and b."""
    path = geodesic_path(a, b, num_segments=2)
    return path[1]  # middle point of 3-point path


# ---------------------------------------------------------------------------
# Euclidean <-> Hyperbolic conformal mapping
# ---------------------------------------------------------------------------

def euclidean_to_poincare(
    x: float,
    y: float,
    z: float = 0.0,
    bounds: Tuple[float, float, float, float] = (-1, -1, 1, 1),
    curvature: float = 1.0,
) -> PoincarePoint:
    """Map Euclidean (terrain) coordinates into the Poincaré disk.

    Uses exponential radial compression: points far from center get
    pushed toward the boundary, mimicking hyperbolic distance growth.

    curvature controls how aggressively points compress toward boundary.
    Higher curvature = more compression = more hyperbolic "feel".
    """
    x_min, y_min, x_max, y_max = bounds
    # Normalize to [-1, 1]
    nx = 2.0 * (x - x_min) / (x_max - x_min) - 1.0 if x_max > x_min else 0.0
    ny = 2.0 * (y - y_min) / (y_max - y_min) - 1.0 if y_max > y_min else 0.0

    # Radial compression via tanh (smooth saturation to disk boundary)
    r = math.sqrt(nx * nx + ny * ny)
    if r < _BOUNDARY_EPSILON:
        return PoincarePoint(0.0, 0.0, z)

    r_hyp = math.tanh(r * curvature)
    scale = r_hyp / r
    return PoincarePoint(nx * scale, ny * scale, z)


def poincare_to_euclidean(
    p: PoincarePoint,
    bounds: Tuple[float, float, float, float] = (-1, -1, 1, 1),
    curvature: float = 1.0,
) -> Tuple[float, float, float]:
    """Inverse mapping: Poincaré disk ->Euclidean coordinates."""
    r = p.radius
    if r < _BOUNDARY_EPSILON:
        cx = (bounds[0] + bounds[2]) / 2
        cy = (bounds[1] + bounds[3]) / 2
        return (cx, cy, p.z)

    # Inverse of tanh compression
    r_euc = math.atanh(min(r, _MAX_POINCARE_RADIUS)) / curvature
    scale = r_euc / r

    nx = p.x * scale
    ny = p.y * scale

    x_min, y_min, x_max, y_max = bounds
    x = (nx + 1.0) / 2.0 * (x_max - x_min) + x_min
    y = (ny + 1.0) / 2.0 * (y_max - y_min) + y_min
    return (x, y, p.z)


# ---------------------------------------------------------------------------
# Eccentricity terrain — detect hills, valleys, plateaus
# ---------------------------------------------------------------------------

@dataclass
class TerrainFeature:
    """A detected feature in the eccentricity terrain."""
    point: PoincarePoint
    eccentricity: float
    feature_type: str  # "peak", "valley", "ridge", "plateau", "saddle"
    neighbors: int = 0


def eccentricity_terrain(
    points: List[PoincarePoint],
    k_neighbors: int = 6,
) -> List[TerrainFeature]:
    """Compute eccentricity terrain from a point cloud in hyperbolic space.

    Eccentricity = max distance to any of k nearest neighbors.
    This identifies topological features:
    - High eccentricity = peaks (isolated, far from neighbors)
    - Low eccentricity = valleys/basins (clustered together)
    - Medium eccentricity = ridges/plateaus (moderate spacing)
    """
    if len(points) < 2:
        return []

    features: List[TerrainFeature] = []
    all_ecc: List[float] = []

    for p in points:
        # Compute distances to all other points
        dists = sorted(
            [(poincare_distance(p, q), q) for q in points if q.point_id != p.point_id],
            key=lambda t: t[0],
        )
        k = min(k_neighbors, len(dists))
        if k == 0:
            continue

        neighbor_dists = [d for d, _ in dists[:k]]
        ecc = max(neighbor_dists)
        all_ecc.append(ecc)
        features.append(TerrainFeature(
            point=p,
            eccentricity=ecc,
            feature_type="",  # classified below
            neighbors=k,
        ))

    if not all_ecc:
        return features

    # Classify features by eccentricity percentile
    ecc_sorted = sorted(all_ecc)
    p25 = ecc_sorted[len(ecc_sorted) // 4]
    p75 = ecc_sorted[3 * len(ecc_sorted) // 4]

    for f in features:
        # Compare z-height with neighbors for terrain classification
        if f.eccentricity > p75:
            f.feature_type = "peak" if f.point.z > 0 else "ridge"
        elif f.eccentricity < p25:
            f.feature_type = "valley" if f.point.z < 0 else "plateau"
        else:
            f.feature_type = "saddle"

    return features


# ---------------------------------------------------------------------------
# Hyperbolic Voronoi — territory partitioning
# ---------------------------------------------------------------------------

def hyperbolic_voronoi_cell(
    center: PoincarePoint,
    neighbors: List[PoincarePoint],
    grid_resolution: int = 32,
) -> List[PoincarePoint]:
    """Approximate Voronoi cell boundary for a point in hyperbolic space.

    Returns points on the cell boundary where distance to center
    equals distance to nearest neighbor (bisector locus).
    """
    boundary: List[PoincarePoint] = []
    for angle_idx in range(grid_resolution):
        angle = 2.0 * math.pi * angle_idx / grid_resolution
        # Ray-march from center outward along this angle
        for r_step in range(1, 100):
            r = r_step * 0.01
            if r >= _MAX_POINCARE_RADIUS:
                break
            px = center.x + r * math.cos(angle)
            py = center.y + r * math.sin(angle)
            test = PoincarePoint(px, py)
            if test.radius >= _MAX_POINCARE_RADIUS:
                break

            d_center = poincare_distance(center, test)
            d_nearest = min(poincare_distance(n, test) for n in neighbors)

            if d_nearest <= d_center:
                boundary.append(test)
                break

    return boundary


# ---------------------------------------------------------------------------
# HyperbolicTerrain — main terrain mapper
# ---------------------------------------------------------------------------

class HyperbolicTerrain:
    """Hyperbolic terrain mapper bridging Euclidean heightmaps to Poincaré disk.

    Features:
    - Load DEM/heightmap data and project into hyperbolic space
    - Geodesic pathfinding between terrain points
    - Eccentricity-based feature detection (peaks, valleys, ridges)
    - Natural LOD from conformal factor (boundary = infinite detail compression)
    - Conformal mesh generation for visualization
    - Bridges to Quadtree25D, SignedOctree, HyperbolicLattice25D

    Sacred Tongue integration:
    - Different terrain regions can be tagged with tongue labels
    - Tongue weights influence geodesic cost (semantic terrain difficulty)
    """

    def __init__(
        self,
        curvature: float = 1.0,
        elevation_scale: float = 1.0,
        chladni_mode: Tuple[int, int] = (3, 2),
    ):
        self.curvature = curvature
        self.elevation_scale = elevation_scale
        self.chladni_mode = chladni_mode
        self._points: Dict[str, PoincarePoint] = {}

    def add_point(self, point: PoincarePoint) -> PoincarePoint:
        """Add a point directly in Poincaré coordinates."""
        self._points[point.point_id] = point
        return point

    def add_euclidean_point(
        self,
        x: float, y: float, z: float = 0.0,
        bounds: Tuple[float, float, float, float] = (-1, -1, 1, 1),
        tongue: str = "KO",
        authority: str = "public",
    ) -> PoincarePoint:
        """Map an Euclidean point into the Poincaré disk and add it."""
        p = euclidean_to_poincare(x, y, z * self.elevation_scale, bounds, self.curvature)
        p.tongue = tongue
        p.authority = authority
        self._points[p.point_id] = p
        return p

    def add_elevation_grid(
        self,
        grid: np.ndarray,
        bounds: Tuple[float, float, float, float] = (-1, -1, 1, 1),
        tongue: str = "auto",
    ) -> int:
        """Load a 2D elevation grid (DEM) into the terrain.

        grid: (rows, cols) array of z-values.
        Returns count of points added.
        """
        rows, cols = grid.shape
        x_min, y_min, x_max, y_max = bounds
        dx = (x_max - x_min) / cols
        dy = (y_max - y_min) / rows
        tongues = list(TONGUE_WEIGHTS.keys()) or ["KO"]
        count = 0

        for iy in range(rows):
            for ix in range(cols):
                x = x_min + (ix + 0.5) * dx
                y = y_min + (iy + 0.5) * dy
                z = float(grid[iy, ix])
                t = tongues[(ix + iy) % len(tongues)] if tongue == "auto" else tongue
                self.add_euclidean_point(x, y, z, bounds, tongue=t)
                count += 1

        return count

    def geodesic_between(
        self,
        a: PoincarePoint,
        b: PoincarePoint,
        segments: int = _GEODESIC_SEGMENTS,
    ) -> List[PoincarePoint]:
        """Compute geodesic path between two terrain points."""
        return geodesic_path(a, b, segments)

    def geodesic_route(
        self,
        waypoints: List[PoincarePoint],
        segments_per_leg: int = 32,
    ) -> List[PoincarePoint]:
        """Compute multi-waypoint geodesic route."""
        if len(waypoints) < 2:
            return list(waypoints)

        route: List[PoincarePoint] = []
        for i in range(len(waypoints) - 1):
            leg = geodesic_path(waypoints[i], waypoints[i + 1], segments_per_leg)
            if i > 0:
                leg = leg[1:]  # skip duplicate start point
            route.extend(leg)
        return route

    def semantic_geodesic_cost(
        self,
        a: PoincarePoint,
        b: PoincarePoint,
        z_weight: float = 0.3,
    ) -> float:
        """Geodesic cost with tongue-weighted semantic penalty.

        Higher tongue weight = easier traversal (well-governed territory).
        Lower tongue weight = harder (uncharted semantic space).
        """
        d_h = poincare_distance(a, b)
        d_z = abs(a.z - b.z) * z_weight
        avg_weight = (a.tongue_weight + b.tongue_weight) / 2.0
        semantic_factor = 1.0 / max(avg_weight, 0.1)  # lower weight = higher cost
        return (d_h + d_z) * semantic_factor

    def eccentricity_map(self, k: int = 6) -> List[TerrainFeature]:
        """Compute eccentricity terrain over all loaded points."""
        return eccentricity_terrain(list(self._points.values()), k)

    def nearest_points(
        self,
        query: PoincarePoint,
        k: int = 5,
        z_weight: float = 0.3,
    ) -> List[Tuple[PoincarePoint, float]]:
        """Find k nearest points using terrain-aware hyperbolic distance."""
        scored = [
            (p, poincare_distance_with_elevation(query, p, z_weight))
            for p in self._points.values()
        ]
        scored.sort(key=lambda t: t[1])
        return scored[:k]

    def conformal_factor_map(self) -> List[Dict[str, Any]]:
        """Return conformal scaling factors for all points.

        Points near the disk boundary have enormous conformal factors,
        representing the exponential distance growth of hyperbolic space.
        This naturally provides LOD: boundary regions need infinite detail.
        """
        return [
            {
                "point_id": p.point_id,
                "x": p.x, "y": p.y, "z": p.z,
                "radius": p.radius,
                "conformal_factor": p.conformal_factor,
                "tongue": p.tongue,
                "lod_priority": min(p.conformal_factor / 10.0, 1.0),
            }
            for p in self._points.values()
        ]

    # -------------------------------------------------------------------
    # Bridge to Quadtree25D
    # -------------------------------------------------------------------

    def to_quadtree25d(self, max_depth: int = 8, variance_threshold: float = 0.5):
        """Project hyperbolic terrain into a 2.5D quadtree.

        Points stay in Poincaré coordinates (already in [-1, 1]).
        z-values drive variance-based subdivision.
        """
        from hydra.quadtree25d import Quadtree25D, QuadPoint

        qt = Quadtree25D(
            bounds=(-1, -1, 1, 1),
            max_depth=max_depth,
            variance_threshold=variance_threshold,
        )
        for p in self._points.values():
            try:
                qt.insert(QuadPoint(
                    x=p.x, y=p.y, z=p.z,
                    tongue=p.tongue,
                    authority=p.authority,
                    intent_vector=p.intent_vector,
                    point_id=p.point_id,
                ))
            except ValueError:
                pass
        return qt

    # -------------------------------------------------------------------
    # Bridge to SignedOctree
    # -------------------------------------------------------------------

    def to_octree(self, max_depth: int = 6, chladni_mode: Tuple[int, int] = (3, 2)):
        """Project terrain into SignedOctree.

        x, y from Poincaré disk; z normalized from elevation range.
        """
        from hydra.octree_sphere_grid import SignedOctree

        octree = SignedOctree(max_depth=max_depth, chladni_mode=chladni_mode)
        all_pts = list(self._points.values())
        if not all_pts:
            return octree

        z_vals = [p.z for p in all_pts]
        z_lo, z_hi = min(z_vals), max(z_vals)
        z_span = z_hi - z_lo if z_hi > z_lo else 1.0

        for p in all_pts:
            z_norm = ((p.z - z_lo) / z_span) * 2.0 - 1.0
            z_clamped = max(-0.99, min(0.99, z_norm * 0.98))
            octree.insert(
                x=max(-0.99, min(0.99, p.x)),
                y=max(-0.99, min(0.99, p.y)),
                z=z_clamped,
                tongue=p.tongue,
                authority=p.authority,
                intent_vector=list(p.intent_vector or [0, 0, 0]),
                intent_label=p.point_id,
                payload={"source": "hyperbolic_terrain", "elevation": p.z},
                create_sphere_grid=True,
            )
        return octree

    # -------------------------------------------------------------------
    # Bridge to HyperbolicLattice25D
    # -------------------------------------------------------------------

    def to_lattice(self, cell_size: float = 0.25, max_depth: int = 6, phase_weight: float = 0.35):
        """Project terrain into HyperbolicLattice25D.

        z-elevation maps to cyclic phase angle.
        """
        from hydra.octree_sphere_grid import HyperbolicLattice25D

        lattice = HyperbolicLattice25D(
            cell_size=cell_size,
            max_depth=max_depth,
            phase_weight=phase_weight,
        )
        all_pts = list(self._points.values())
        if not all_pts:
            return lattice

        z_vals = [p.z for p in all_pts]
        z_lo, z_hi = min(z_vals), max(z_vals)
        z_span = z_hi - z_lo if z_hi > z_lo else 1.0

        for p in all_pts:
            z_norm = (p.z - z_lo) / z_span
            phase_rad = z_norm * 2.0 * math.pi
            lattice.insert_bundle(
                x=max(-0.99, min(0.99, p.x)),
                y=max(-0.99, min(0.99, p.y)),
                phase_rad=phase_rad,
                tongue=p.tongue,
                authority=p.authority,
                intent_vector=list(p.intent_vector or [0, 0, 0]),
                intent_label=p.point_id,
                payload={"source": "hyperbolic_terrain", "elevation": p.z},
                bundle_id=p.point_id,
            )
        return lattice

    # -------------------------------------------------------------------
    # Stats
    # -------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        pts = list(self._points.values())
        if not pts:
            return {"point_count": 0}

        radii = [p.radius for p in pts]
        z_vals = [p.z for p in pts]
        conf_factors = [p.conformal_factor for p in pts]
        tongue_dist: Dict[str, int] = {}
        for p in pts:
            tongue_dist[p.tongue] = tongue_dist.get(p.tongue, 0) + 1

        return {
            "point_count": len(pts),
            "radius_range": [min(radii), max(radii)],
            "radius_mean": sum(radii) / len(radii),
            "z_range": [min(z_vals), max(z_vals)],
            "z_mean": sum(z_vals) / len(z_vals),
            "conformal_factor_range": [min(conf_factors), max(conf_factors)],
            "conformal_factor_mean": sum(conf_factors) / len(conf_factors),
            "tongue_distribution": tongue_dist,
            "curvature": self.curvature,
        }


# ---------------------------------------------------------------------------
# INTEROP_MATRIX for hyperbolic terrain
# ---------------------------------------------------------------------------

HYPERBOLIC_TERRAIN_INTEROP = {
    "poincare_point": {
        "python": "PoincarePoint(x, y, z, tongue, authority)",
        "typescript": "interface PoincarePoint { x: number; y: number; z: number; tongue: string; }",
        "rust": "struct PoincarePoint { x: f64, y: f64, z: f64, tongue: String }",
        "glsl": "struct PoincarePoint { vec2 pos; float z; float tongue_weight; };",
        "wasm": "PoincarePoint via wasm-bindgen { x: f64, y: f64, z: f64 }",
        "go": "type PoincarePoint struct { X, Y, Z float64; Tongue string }",
    },
    "poincare_distance": {
        "python": "math.acosh(1 + 2*diff_sq / ((1-na2)*(1-nb2)))",
        "typescript": "Math.acosh(1 + 2*diffSq / ((1-na2)*(1-nb2)))",
        "rust": "((1.0 + 2.0*esq / ((1.0-na2)*(1.0-nb2)))).acosh()",
        "glsl": "acosh(1.0 + 2.0*dot(d,d) / ((1.0-dot(a,a))*(1.0-dot(b,b))))",
        "go": "math.Acosh(1 + 2*diffSq / ((1-na2)*(1-nb2)))",
    },
    "mobius_translate": {
        "python": "T_a(z) = (z - a) / (1 - conj(a)*z) via complex arithmetic",
        "typescript": "mobiusTranslate(z: Complex, a: Complex): Complex",
        "rust": "fn mobius_translate(z: Complex64, a: Complex64) -> Complex64",
        "glsl": "vec2 mobius(vec2 z, vec2 a) { /* complex division */ }",
    },
    "geodesic_path": {
        "python": "geodesic_path(a, b, segments) ->List[PoincarePoint]",
        "typescript": "geodesicPath(a: PoincarePoint, b: PoincarePoint, n: number): PoincarePoint[]",
        "rust": "fn geodesic_path(a: &PoincarePoint, b: &PoincarePoint, n: usize) -> Vec<PoincarePoint>",
        "glsl": "// GPU: interpolate along Mobius-translated diameter",
    },
    "conformal_factor": {
        "python": "lambda_p = 2.0 / (1.0 - |z|^2) — grows to infinity at boundary",
        "typescript": "const lambda = 2 / (1 - normSq);",
        "rust": "let lambda = 2.0 / (1.0 - r2);",
        "glsl": "float lambda = 2.0 / (1.0 - dot(p, p));",
    },
    "eccentricity_terrain": {
        "python": "eccentricity_terrain(points, k) ->List[TerrainFeature]",
        "typescript": "eccentricityTerrain(points: PoincarePoint[], k: number): TerrainFeature[]",
        "rust": "fn eccentricity_terrain(points: &[PoincarePoint], k: usize) -> Vec<TerrainFeature>",
    },
    "euclidean_to_poincare": {
        "python": "tanh(r * curvature) radial compression ->smooth disk mapping",
        "typescript": "Math.tanh(r * curvature) for radial compression",
        "rust": "(r * curvature).tanh() for disk mapping",
        "glsl": "tanh(length(uv) * curvature) * normalize(uv)",
    },
}


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo() -> Dict[str, Any]:
    """Full demo: synthetic terrain ->hyperbolic mapping ->features ->bridges."""
    print("=== HYDRA Hyperbolic Terrain Mapping Demo ===\n")

    terrain = HyperbolicTerrain(curvature=1.2, elevation_scale=0.5)

    # 1. Generate synthetic DEM
    resolution = 16
    dem = np.zeros((resolution, resolution))
    for iy in range(resolution):
        for ix in range(resolution):
            x = (ix / resolution) * 2 - 1
            y = (iy / resolution) * 2 - 1
            dem[iy, ix] = (
                3.0 * math.sin(x * 2.5) * math.cos(y * 2.5)
                + 1.5 * math.sin(x * 5.0 + 1.0)
            )

    count = terrain.add_elevation_grid(dem, bounds=(-1, -1, 1, 1), tongue="auto")
    print(f"[1] Loaded DEM ({resolution}x{resolution}): {count} points")

    # 2. Stats
    stats = terrain.stats()
    print(f"[2] Stats: radius=[{stats['radius_range'][0]:.3f}, {stats['radius_range'][1]:.3f}], "
          f"z=[{stats['z_range'][0]:.2f}, {stats['z_range'][1]:.2f}]")
    print(f"    Conformal factor: [{stats['conformal_factor_range'][0]:.2f}, "
          f"{stats['conformal_factor_range'][1]:.2f}]")

    # 3. Geodesic path
    pts = list(terrain._points.values())
    if len(pts) >= 2:
        path = terrain.geodesic_between(pts[0], pts[-1], segments=16)
        path_length = geodesic_length(pts[0], pts[-1])
        print(f"[3] Geodesic path: {len(path)} waypoints, length={path_length:.4f}")

    # 4. Eccentricity map
    features = terrain.eccentricity_map(k=4)
    feature_types = {}
    for f in features:
        feature_types[f.feature_type] = feature_types.get(f.feature_type, 0) + 1
    print(f"[4] Eccentricity terrain: {len(features)} features -> {feature_types}")

    # 5. Conformal factor map
    conf_map = terrain.conformal_factor_map()
    high_priority = sum(1 for c in conf_map if c["lod_priority"] > 0.5)
    print(f"[5] Conformal LOD: {high_priority}/{len(conf_map)} high-priority points")

    # 6. Nearest query
    center = PoincarePoint(0.0, 0.0)
    nearest = terrain.nearest_points(center, k=5)
    print(f"[6] 5 nearest to center: distances=[{', '.join(f'{d:.3f}' for _, d in nearest)}]")

    # 7. Mobius translation
    translated = mobius_translate(pts[0], PoincarePoint(0.3, 0.2))
    print(f"[7] Mobius translate ({pts[0].x:.3f},{pts[0].y:.3f}) by (0.3,0.2) ->"
          f"({translated.x:.3f},{translated.y:.3f})")

    # 8. Bridge to Quadtree25D
    qt = terrain.to_quadtree25d(max_depth=6, variance_threshold=0.5)
    qt_stats = qt.stats()
    print(f"\n[8] Quadtree25D bridge: {qt_stats['point_count']} points, "
          f"{qt_stats['leaf_count']} leaves, {qt_stats['variance_splits']} variance splits")

    # 9. Bridge to SignedOctree
    octree = terrain.to_octree(max_depth=4)
    oct_stats = octree.stats()
    print(f"[9] Octree bridge: {oct_stats['count']} voxels")

    # 10. Bridge to Lattice
    lattice = terrain.to_lattice(cell_size=0.3)
    lat_stats = lattice.stats()
    print(f"[10] Lattice bridge: {lat_stats['bundle_count']} bundles, "
          f"{lat_stats['overlap_cells']} overlaps, {lat_stats['lace_edges']} lace edges")

    # 11. Semantic geodesic cost
    if len(pts) >= 2:
        cost = terrain.semantic_geodesic_cost(pts[0], pts[-1])
        print(f"\n[11] Semantic geodesic cost (tongue-weighted): {cost:.4f}")

    # 12. Model conversions
    if pts:
        klein = pts[0].to_klein()
        half = pts[0].to_half_plane()
        print(f"[12] Model conversions: Klein=({klein[0]:.3f},{klein[1]:.3f}), "
              f"HalfPlane=({half[0]:.3f},{half[1]:.3f})")

    print(f"\n[13] Interop matrix: {len(HYPERBOLIC_TERRAIN_INTEROP)} concepts "
          f"across {len(set(l for c in HYPERBOLIC_TERRAIN_INTEROP.values() for l in c))} languages")

    print("\n=== Demo complete ===")
    return {
        "point_count": stats["point_count"],
        "features": feature_types,
        "quadtree_leaves": qt_stats["leaf_count"],
        "octree_voxels": oct_stats["count"],
        "lattice_bundles": lat_stats["bundle_count"],
        "interop_concepts": len(HYPERBOLIC_TERRAIN_INTEROP),
    }


if __name__ == "__main__":
    demo()
