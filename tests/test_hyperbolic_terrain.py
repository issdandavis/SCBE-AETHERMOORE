"""Tests for hydra/hyperbolic_terrain.py — Poincare disk terrain mapping."""
from __future__ import annotations

import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import numpy as np

from hydra.hyperbolic_terrain import (
    PoincarePoint,
    poincare_distance,
    poincare_distance_with_elevation,
    mobius_translate,
    mobius_gyration,
    geodesic_path,
    geodesic_length,
    geodesic_midpoint,
    euclidean_to_poincare,
    poincare_to_euclidean,
    eccentricity_terrain,
    hyperbolic_voronoi_cell,
    HyperbolicTerrain,
    HYPERBOLIC_TERRAIN_INTEROP,
)


# ---------------------------------------------------------------------------
# PoincarePoint
# ---------------------------------------------------------------------------

class TestPoincarePoint:
    def test_inside_disk(self):
        p = PoincarePoint(0.3, 0.4)
        assert p.radius < 1.0

    def test_clamp_outside_disk(self):
        p = PoincarePoint(2.0, 3.0)
        assert p.radius <= 0.999 + 1e-6

    def test_auto_id(self):
        p = PoincarePoint(0.1, 0.2, z=5.0)
        assert p.point_id.startswith("hp_")

    def test_conformal_factor_center(self):
        p = PoincarePoint(0.0, 0.0)
        assert abs(p.conformal_factor - 2.0) < 1e-10

    def test_conformal_factor_grows_near_boundary(self):
        center = PoincarePoint(0.0, 0.0)
        edge = PoincarePoint(0.99, 0.0)
        assert edge.conformal_factor > center.conformal_factor * 10

    def test_tongue_weight(self):
        p = PoincarePoint(0, 0, tongue="DR")
        assert p.tongue_weight > 10.0

    def test_to_klein(self):
        p = PoincarePoint(0.0, 0.0)
        k = p.to_klein()
        assert k == (0.0, 0.0)

    def test_to_half_plane_center(self):
        p = PoincarePoint(0.0, 0.0)
        u, v = p.to_half_plane()
        assert abs(u) < 1e-10
        assert v > 0


# ---------------------------------------------------------------------------
# Poincare distance
# ---------------------------------------------------------------------------

class TestPoincareDistance:
    def test_zero_distance(self):
        p = PoincarePoint(0.3, 0.4)
        assert poincare_distance(p, p) == 0.0

    def test_symmetric(self):
        a = PoincarePoint(0.1, 0.2)
        b = PoincarePoint(-0.3, 0.4)
        assert abs(poincare_distance(a, b) - poincare_distance(b, a)) < 1e-10

    def test_triangle_inequality(self):
        a = PoincarePoint(0.1, 0.0)
        b = PoincarePoint(0.0, 0.3)
        c = PoincarePoint(-0.2, -0.1)
        ab = poincare_distance(a, b)
        bc = poincare_distance(b, c)
        ac = poincare_distance(a, c)
        assert ac <= ab + bc + 1e-10

    def test_distance_grows_near_boundary(self):
        center = PoincarePoint(0.0, 0.0)
        near = PoincarePoint(0.1, 0.0)
        far = PoincarePoint(0.9, 0.0)
        d_near = poincare_distance(center, near)
        d_far = poincare_distance(center, far)
        assert d_far > d_near * 5  # exponential growth

    def test_with_elevation(self):
        a = PoincarePoint(0.1, 0.1, z=0.0)
        b = PoincarePoint(0.1, 0.1, z=10.0)
        d_flat = poincare_distance(a, b)
        d_elev = poincare_distance_with_elevation(a, b, z_weight=0.5)
        assert d_elev > d_flat


# ---------------------------------------------------------------------------
# Mobius transformations
# ---------------------------------------------------------------------------

class TestMobiusTranslate:
    def test_origin_to_origin(self):
        p = PoincarePoint(0.3, 0.4)
        result = mobius_translate(p, p)
        assert abs(result.x) < 1e-10
        assert abs(result.y) < 1e-10

    def test_identity_at_origin(self):
        p = PoincarePoint(0.3, 0.4)
        origin = PoincarePoint(0.0, 0.0)
        result = mobius_translate(p, origin)
        assert abs(result.x - p.x) < 1e-10
        assert abs(result.y - p.y) < 1e-10

    def test_preserves_disk(self):
        p = PoincarePoint(0.5, 0.5)
        center = PoincarePoint(0.3, -0.2)
        result = mobius_translate(p, center)
        assert result.radius < 1.0

    def test_isometry(self):
        """Mobius translation preserves hyperbolic distances."""
        a = PoincarePoint(0.1, 0.2)
        b = PoincarePoint(-0.3, 0.1)
        center = PoincarePoint(0.2, -0.1)

        d_before = poincare_distance(a, b)
        a_t = mobius_translate(a, center)
        b_t = mobius_translate(b, center)
        d_after = poincare_distance(a_t, b_t)
        assert abs(d_before - d_after) < 1e-6


# ---------------------------------------------------------------------------
# Geodesic paths
# ---------------------------------------------------------------------------

class TestGeodesicPath:
    def test_path_endpoints(self):
        a = PoincarePoint(0.1, 0.2)
        b = PoincarePoint(-0.3, 0.4)
        path = geodesic_path(a, b, num_segments=10)
        assert len(path) == 11
        assert abs(path[0].x - a.x) < 0.05
        assert abs(path[-1].x - b.x) < 0.05

    def test_path_stays_in_disk(self):
        a = PoincarePoint(0.8, 0.0)
        b = PoincarePoint(0.0, 0.8)
        path = geodesic_path(a, b, num_segments=32)
        for p in path:
            assert p.radius < 1.0

    def test_geodesic_length_equals_distance(self):
        a = PoincarePoint(0.1, 0.0)
        b = PoincarePoint(0.5, 0.0)
        assert abs(geodesic_length(a, b) - poincare_distance(a, b)) < 1e-10

    def test_midpoint(self):
        a = PoincarePoint(0.0, 0.0)
        b = PoincarePoint(0.6, 0.0)
        mid = geodesic_midpoint(a, b)
        d_am = poincare_distance(a, mid)
        d_mb = poincare_distance(mid, b)
        assert abs(d_am - d_mb) < 0.15  # approximate midpoint

    def test_elevation_interpolation(self):
        a = PoincarePoint(0.0, 0.0, z=0.0)
        b = PoincarePoint(0.5, 0.0, z=10.0)
        path = geodesic_path(a, b, num_segments=10)
        assert path[0].z == 0.0
        assert path[-1].z == 10.0
        assert 4.0 < path[5].z < 6.0  # midpoint elevation ~5


# ---------------------------------------------------------------------------
# Euclidean <-> Poincare mapping
# ---------------------------------------------------------------------------

class TestConformalMapping:
    def test_center_maps_to_center(self):
        p = euclidean_to_poincare(0.0, 0.0, bounds=(-1, -1, 1, 1))
        assert abs(p.x) < 1e-10
        assert abs(p.y) < 1e-10

    def test_stays_in_disk(self):
        for x in [-1, -0.5, 0, 0.5, 1]:
            for y in [-1, -0.5, 0, 0.5, 1]:
                p = euclidean_to_poincare(x, y, bounds=(-1, -1, 1, 1))
                assert p.radius < 1.0

    def test_higher_curvature_more_compression(self):
        p_low = euclidean_to_poincare(0.5, 0.5, curvature=0.5)
        p_high = euclidean_to_poincare(0.5, 0.5, curvature=2.0)
        assert p_high.radius > p_low.radius  # more curvature pushes toward boundary

    def test_roundtrip(self):
        x, y, z = 0.3, -0.2, 5.0
        bounds = (-2, -2, 2, 2)
        p = euclidean_to_poincare(x, y, z, bounds, curvature=1.0)
        x2, y2, z2 = poincare_to_euclidean(p, bounds, curvature=1.0)
        assert abs(x - x2) < 0.01
        assert abs(y - y2) < 0.01
        assert abs(z - z2) < 0.01


# ---------------------------------------------------------------------------
# Eccentricity terrain
# ---------------------------------------------------------------------------

class TestEccentricityTerrain:
    def test_returns_features(self):
        points = [
            PoincarePoint(0.1 * i, 0.1 * j, z=float(i + j))
            for i in range(-3, 4) for j in range(-3, 4)
        ]
        features = eccentricity_terrain(points, k_neighbors=4)
        assert len(features) > 0

    def test_feature_types(self):
        points = [
            PoincarePoint(0.05 * i, 0.05 * j, z=float(i * j * 0.1))
            for i in range(-5, 6) for j in range(-5, 6)
        ]
        features = eccentricity_terrain(points, k_neighbors=4)
        types = {f.feature_type for f in features}
        assert len(types) >= 2  # at least 2 different feature types

    def test_isolated_point_is_peak_or_ridge(self):
        cluster = [PoincarePoint(0.01 * i, 0.01 * j, z=0.0) for i in range(5) for j in range(5)]
        isolated = [PoincarePoint(0.8, 0.0, z=5.0)]
        features = eccentricity_terrain(cluster + isolated, k_neighbors=3)
        iso_feat = [f for f in features if f.point.point_id == isolated[0].point_id]
        assert len(iso_feat) == 1
        assert iso_feat[0].feature_type in ("peak", "ridge")


# ---------------------------------------------------------------------------
# HyperbolicTerrain
# ---------------------------------------------------------------------------

class TestHyperbolicTerrain:
    def test_add_point(self):
        t = HyperbolicTerrain()
        p = t.add_point(PoincarePoint(0.1, 0.2, z=3.0))
        assert t.stats()["point_count"] == 1

    def test_add_euclidean(self):
        t = HyperbolicTerrain()
        p = t.add_euclidean_point(0.5, 0.3, z=10.0, bounds=(-1, -1, 1, 1))
        assert p.radius < 1.0
        assert t.stats()["point_count"] == 1

    def test_add_elevation_grid(self):
        t = HyperbolicTerrain()
        dem = np.ones((8, 8)) * 5.0
        count = t.add_elevation_grid(dem)
        assert count == 64
        assert t.stats()["point_count"] == 64

    def test_nearest_points(self):
        t = HyperbolicTerrain()
        t.add_point(PoincarePoint(0.0, 0.0))
        t.add_point(PoincarePoint(0.5, 0.0))
        t.add_point(PoincarePoint(0.9, 0.0))
        results = t.nearest_points(PoincarePoint(0.0, 0.0), k=2)
        assert len(results) == 2
        assert results[0][1] <= results[1][1]

    def test_semantic_geodesic_cost(self):
        t = HyperbolicTerrain()
        a = PoincarePoint(0.1, 0.0, tongue="DR")  # high weight = easy
        b = PoincarePoint(0.1, 0.0, tongue="KO")  # low weight = hard
        c = PoincarePoint(0.5, 0.0, tongue="DR")
        d = PoincarePoint(0.5, 0.0, tongue="KO")
        cost_easy = t.semantic_geodesic_cost(a, c)
        cost_hard = t.semantic_geodesic_cost(b, d)
        assert cost_hard > cost_easy  # KO has lower weight, higher cost

    def test_conformal_factor_map(self):
        t = HyperbolicTerrain()
        t.add_point(PoincarePoint(0.0, 0.0))
        t.add_point(PoincarePoint(0.9, 0.0))
        cfm = t.conformal_factor_map()
        assert len(cfm) == 2
        assert all("conformal_factor" in c for c in cfm)

    def test_stats(self):
        t = HyperbolicTerrain(curvature=1.5)
        dem = np.random.randn(4, 4)
        t.add_elevation_grid(dem)
        stats = t.stats()
        assert stats["point_count"] == 16
        assert stats["curvature"] == 1.5


# ---------------------------------------------------------------------------
# Bridges
# ---------------------------------------------------------------------------

class TestBridges:
    def _make_terrain(self) -> HyperbolicTerrain:
        t = HyperbolicTerrain()
        dem = np.random.randn(6, 6)
        t.add_elevation_grid(dem)
        return t

    def test_to_quadtree25d(self):
        t = self._make_terrain()
        qt = t.to_quadtree25d(max_depth=4)
        assert qt.stats()["point_count"] == 36

    def test_to_octree(self):
        t = self._make_terrain()
        octree = t.to_octree(max_depth=4)
        assert octree.stats()["count"] == 36

    def test_to_lattice(self):
        t = self._make_terrain()
        lattice = t.to_lattice(cell_size=0.4)
        assert lattice.stats()["bundle_count"] == 36


# ---------------------------------------------------------------------------
# Interop matrix
# ---------------------------------------------------------------------------

class TestInteropMatrix:
    def test_concepts_present(self):
        expected = {
            "poincare_point", "poincare_distance", "mobius_translate",
            "geodesic_path", "conformal_factor", "eccentricity_terrain",
            "euclidean_to_poincare",
        }
        assert expected == set(HYPERBOLIC_TERRAIN_INTEROP.keys())

    def test_python_in_all(self):
        for concept, langs in HYPERBOLIC_TERRAIN_INTEROP.items():
            assert "python" in langs, f"Missing python for {concept}"


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_dem_to_all_bridges(self):
        t = HyperbolicTerrain(curvature=1.0)
        dem = np.array([
            [0, 1, 5, 2],
            [1, 3, 8, 3],
            [2, 6, 4, 1],
            [0, 2, 1, 0],
        ], dtype=float)
        t.add_elevation_grid(dem, bounds=(-1, -1, 1, 1))

        # Features
        features = t.eccentricity_map(k=3)
        assert len(features) == 16

        # All bridges
        qt = t.to_quadtree25d()
        assert qt.stats()["point_count"] == 16
        octree = t.to_octree()
        assert octree.stats()["count"] == 16
        lattice = t.to_lattice()
        assert lattice.stats()["bundle_count"] == 16

        # Geodesic
        pts = list(t._points.values())
        path = t.geodesic_between(pts[0], pts[-1], segments=8)
        assert len(path) == 9
