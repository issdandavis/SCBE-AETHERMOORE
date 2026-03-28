"""Tests for hydra/quadtree25d.py — 2.5D adaptive quadtree with octree/lattice bridge."""

from __future__ import annotations

import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from hydra.quadtree25d import (
    QuadPoint,
    QuadBounds,
    QuadNode,
    Quadtree25D,
    SubdivisionCriterion,
    LODQuery,
    generate_terrain_points,
    sine_hills,
    ridge_terrain,
    flat_with_spikes,
    QUADTREE25D_INTEROP,
)

# ---------------------------------------------------------------------------
# QuadPoint
# ---------------------------------------------------------------------------


class TestQuadPoint:
    def test_auto_id(self):
        p = QuadPoint(0.5, 0.3, z=1.0)
        assert p.point_id.startswith("qp_")
        assert len(p.point_id) > 4

    def test_explicit_id(self):
        p = QuadPoint(0.1, 0.2, z=3.0, point_id="my-point")
        assert p.point_id == "my-point"

    def test_tongue_weight(self):
        p = QuadPoint(0, 0, tongue="DR")
        assert p.tongue_weight > 10.0  # DR ≈ 11.09

    def test_default_tongue(self):
        p = QuadPoint(0, 0)
        assert p.tongue == "KO"
        assert p.tongue_weight == 1.0

    def test_distinct_ids(self):
        p1 = QuadPoint(0.1, 0.2, z=1.0)
        p2 = QuadPoint(0.3, 0.4, z=2.0)
        assert p1.point_id != p2.point_id


# ---------------------------------------------------------------------------
# QuadBounds
# ---------------------------------------------------------------------------


class TestQuadBounds:
    def test_center(self):
        b = QuadBounds(-1, -1, 1, 1)
        assert b.cx == 0.0
        assert b.cy == 0.0

    def test_dimensions(self):
        b = QuadBounds(0, 0, 4, 3)
        assert b.width == 4.0
        assert b.height == 3.0
        assert b.area == 12.0

    def test_contains(self):
        b = QuadBounds(-1, -1, 1, 1)
        assert b.contains(0, 0)
        assert b.contains(-1, -1)
        assert b.contains(1, 1)
        assert not b.contains(1.1, 0)

    def test_intersects(self):
        b1 = QuadBounds(-1, -1, 1, 1)
        b2 = QuadBounds(0, 0, 2, 2)
        assert b1.intersects(b2)
        b3 = QuadBounds(2, 2, 3, 3)
        assert not b1.intersects(b3)

    def test_quadrant_coverage(self):
        b = QuadBounds(0, 0, 4, 4)
        quads = [b.quadrant(i) for i in range(4)]
        # All 4 quads should tile the parent exactly
        total_area = sum(q.area for q in quads)
        assert abs(total_area - b.area) < 1e-10

    def test_quadrant_invalid(self):
        b = QuadBounds(0, 0, 1, 1)
        with pytest.raises(ValueError):
            b.quadrant(4)


# ---------------------------------------------------------------------------
# QuadNode
# ---------------------------------------------------------------------------


class TestQuadNode:
    def test_empty_leaf(self):
        node = QuadNode(QuadBounds(-1, -1, 1, 1))
        assert node.is_leaf
        assert node.point_count == 0
        assert node.z_range == 0.0

    def test_insert_single(self):
        node = QuadNode(QuadBounds(-1, -1, 1, 1))
        node._insert_point(QuadPoint(0, 0, z=5.0))
        assert node.point_count == 1
        assert node.z_min == 5.0
        assert node.z_max == 5.0
        assert node.is_leaf

    def test_density_subdivision(self):
        node = QuadNode(QuadBounds(-1, -1, 1, 1), max_points=2, max_depth=4)
        for i in range(5):
            node._insert_point(QuadPoint(i * 0.1, i * 0.1, z=0.0))
        assert not node.is_leaf
        assert len(node.children) == 4

    def test_variance_subdivision(self):
        node = QuadNode(
            QuadBounds(-1, -1, 1, 1),
            max_points=100,  # high limit so density doesn't trigger
            variance_threshold=1.0,
            max_depth=4,
        )
        # Insert points with very different z values
        node._insert_point(QuadPoint(0.1, 0.1, z=0.0))
        node._insert_point(QuadPoint(0.2, 0.2, z=5.0))  # z_range=5 > threshold=1
        assert not node.is_leaf
        assert node.subdivision_reason == SubdivisionCriterion.VARIANCE

    def test_max_depth_stops_subdivision(self):
        node = QuadNode(
            QuadBounds(-1, -1, 1, 1),
            max_points=1,
            max_depth=0,  # can't subdivide at all
        )
        node._insert_point(QuadPoint(0, 0, z=0))
        node._insert_point(QuadPoint(0.1, 0.1, z=100))
        assert node.is_leaf  # depth=0, can't subdivide

    def test_all_points_recursive(self):
        node = QuadNode(QuadBounds(-1, -1, 1, 1), max_points=2, max_depth=4)
        for i in range(10):
            node._insert_point(QuadPoint(i * 0.1 - 0.5, i * 0.05 - 0.25, z=float(i)))
        assert len(node.all_points()) == 10

    def test_chladni_mode_scales(self):
        QuadNode(QuadBounds(-1, -1, 1, 1), depth=0, chladni_base_mode=(3, 2))
        n3 = QuadNode(QuadBounds(-1, -1, 1, 1), depth=3, chladni_base_mode=(3, 2))
        phi = (1 + math.sqrt(5)) / 2
        assert abs(n3.chladni_mode[0] - 3 * phi**3) < 0.01

    def test_leaf_count(self):
        node = QuadNode(QuadBounds(-1, -1, 1, 1), max_points=2, max_depth=4)
        assert node.leaf_count() == 1  # just root
        for i in range(5):
            node._insert_point(QuadPoint(i * 0.1, i * 0.1))
        assert node.leaf_count() >= 4  # subdivided

    def test_range_query(self):
        node = QuadNode(QuadBounds(-1, -1, 1, 1), max_points=4, max_depth=4)
        for i in range(20):
            x = (i % 5) * 0.3 - 0.6
            y = (i // 5) * 0.3 - 0.6
            node._insert_point(QuadPoint(x, y, z=float(i)))
        region = QuadBounds(-0.4, -0.4, 0.4, 0.4)
        results = node.query_range(region)
        for pt in results:
            assert -0.4 <= pt.x <= 0.4
            assert -0.4 <= pt.y <= 0.4

    def test_range_query_z_filter(self):
        node = QuadNode(QuadBounds(-1, -1, 1, 1))
        node._insert_point(QuadPoint(0, 0, z=1.0))
        node._insert_point(QuadPoint(0.1, 0.1, z=10.0))
        node._insert_point(QuadPoint(0.2, 0.2, z=5.0))
        results = node.query_range(QuadBounds(-1, -1, 1, 1), z_min=4, z_max=8)
        assert len(results) == 1
        assert results[0].z == 5.0


# ---------------------------------------------------------------------------
# Quadtree25D
# ---------------------------------------------------------------------------


class TestQuadtree25D:
    def test_basic_insert(self):
        qt = Quadtree25D()
        pt = qt.insert(QuadPoint(0.5, 0.3, z=2.0))
        assert pt.point_id in qt._point_index
        assert qt.stats()["point_count"] == 1

    def test_out_of_bounds(self):
        qt = Quadtree25D(bounds=(-1, -1, 1, 1))
        with pytest.raises(ValueError):
            qt.insert(QuadPoint(5.0, 0.0))

    def test_batch_insert(self):
        qt = Quadtree25D()
        pts = [QuadPoint(i * 0.05 - 0.5, i * 0.03 - 0.3, z=float(i)) for i in range(20)]
        count = qt.insert_batch(pts)
        assert count == 20

    def test_batch_skips_out_of_bounds(self):
        qt = Quadtree25D(bounds=(0, 0, 1, 1))
        pts = [
            QuadPoint(0.5, 0.5, z=1.0),
            QuadPoint(-5.0, -5.0, z=0.0),  # out of bounds
            QuadPoint(0.3, 0.7, z=2.0),
        ]
        count = qt.insert_batch(pts)
        assert count == 2

    def test_range_query(self):
        qt = Quadtree25D()
        for i in range(50):
            qt.insert(QuadPoint(i * 0.03 - 0.75, i * 0.02 - 0.5, z=float(i % 10)))
        results = qt.range_query(-0.5, -0.3, 0.0, 0.0, z_min=3, z_max=7)
        for pt in results:
            assert -0.5 <= pt.x <= 0.0
            assert -0.3 <= pt.y <= 0.0
            assert 3 <= pt.z <= 7

    def test_range_query_tongue_filter(self):
        qt = Quadtree25D()
        qt.insert(QuadPoint(0.1, 0.1, tongue="KO"))
        qt.insert(QuadPoint(0.2, 0.2, tongue="DR"))
        qt.insert(QuadPoint(0.3, 0.3, tongue="KO"))
        results = qt.range_query(-1, -1, 1, 1, tongue="KO")
        assert len(results) == 2
        assert all(p.tongue == "KO" for p in results)

    def test_nearest(self):
        qt = Quadtree25D()
        qt.insert(QuadPoint(0.0, 0.0, z=0.0))
        qt.insert(QuadPoint(0.5, 0.5, z=5.0))
        qt.insert(QuadPoint(0.9, 0.9, z=9.0))
        results = qt.nearest(0.0, 0.0, k=2)
        assert len(results) == 2
        assert results[0][0].x == 0.0  # closest
        assert results[0][1] <= results[1][1]

    def test_stats_structure(self):
        qt = Quadtree25D()
        pts = generate_terrain_points(sine_hills, resolution=8)
        qt.insert_batch(pts)
        stats = qt.stats()
        assert "point_count" in stats
        assert "leaf_count" in stats
        assert "variance_splits" in stats
        assert "tongue_distribution" in stats
        assert stats["point_count"] == 64

    def test_leaf_heatmap(self):
        qt = Quadtree25D(max_points=4)
        pts = generate_terrain_points(sine_hills, resolution=8)
        qt.insert_batch(pts)
        heatmap = qt.leaf_heatmap()
        assert len(heatmap) > 0
        for cell in heatmap:
            assert "bounds" in cell
            assert "z_mean" in cell
            assert "depth" in cell
            assert "chladni_value" in cell


# ---------------------------------------------------------------------------
# Terrain mesh
# ---------------------------------------------------------------------------


class TestTerrainMesh:
    def test_mesh_generation(self):
        qt = Quadtree25D(max_points=4)
        pts = generate_terrain_points(sine_hills, resolution=8)
        qt.insert_batch(pts)
        mesh = qt.to_terrain_mesh()
        assert mesh.vertex_count > 0
        assert mesh.triangle_count > 0
        # Each leaf produces 2 triangles
        leaf_count = qt.stats()["leaf_count"]
        assert mesh.triangle_count == leaf_count * 2

    def test_mesh_vertices_have_chladni(self):
        qt = Quadtree25D(max_points=4)
        pts = generate_terrain_points(sine_hills, resolution=8)
        qt.insert_batch(pts)
        mesh = qt.to_terrain_mesh()
        # At least some vertices should have nonzero chladni
        has_nonzero = any(v.chladni_amplitude != 0 for v in mesh.vertices)
        assert has_nonzero

    def test_empty_quadtree_mesh(self):
        qt = Quadtree25D()
        mesh = qt.to_terrain_mesh()
        # Empty tree still has 1 leaf (root), so 2 triangles, 4 vertices
        assert mesh.triangle_count == 2
        assert mesh.vertex_count == 4


# ---------------------------------------------------------------------------
# DEM grid
# ---------------------------------------------------------------------------


class TestDEMGrid:
    def test_dem_shape(self):
        qt = Quadtree25D()
        pts = generate_terrain_points(sine_hills, resolution=8)
        qt.insert_batch(pts)
        dem = qt.to_dem_grid(resolution=16)
        assert dem.shape == (16, 16)

    def test_dem_values_in_range(self):
        qt = Quadtree25D()
        pts = generate_terrain_points(flat_with_spikes, resolution=12)
        qt.insert_batch(pts)
        dem = qt.to_dem_grid(resolution=8)
        assert dem.min() >= 0  # flat_with_spikes base is 0.1
        assert dem.max() <= 12  # max spike ~10


# ---------------------------------------------------------------------------
# LOD
# ---------------------------------------------------------------------------


class TestLOD:
    def test_lod_returns_nodes(self):
        qt = Quadtree25D(max_points=4)
        pts = generate_terrain_points(sine_hills, resolution=12)
        qt.insert_batch(pts)
        query = LODQuery(x=0, y=0, z=20, max_screen_error=8.0)
        nodes = qt.lod_nodes(query)
        assert len(nodes) > 0

    def test_closer_view_more_detail(self):
        qt = Quadtree25D(max_points=4, variance_threshold=0.5)
        pts = generate_terrain_points(ridge_terrain, resolution=16)
        qt.insert_batch(pts)
        far = LODQuery(x=0, y=0, z=100, max_screen_error=2.0)
        close = LODQuery(x=0, y=0, z=2, max_screen_error=2.0)
        far_nodes = qt.lod_nodes(far)
        close_nodes = qt.lod_nodes(close)
        # Closer view should select at least as many nodes (more detail)
        assert len(close_nodes) >= len(far_nodes)


# ---------------------------------------------------------------------------
# Octree bridge
# ---------------------------------------------------------------------------


class TestOctreeBridge:
    def test_project_to_octree(self):
        qt = Quadtree25D()
        pts = generate_terrain_points(sine_hills, resolution=6)
        qt.insert_batch(pts)
        octree = qt.project_to_octree(max_depth=4)
        stats = octree.stats()
        assert stats["count"] == 36  # 6x6 grid

    def test_empty_projection(self):
        qt = Quadtree25D()
        octree = qt.project_to_octree()
        assert octree.stats()["count"] == 0


# ---------------------------------------------------------------------------
# Lattice bridge
# ---------------------------------------------------------------------------


class TestLatticeBridge:
    def test_project_to_lattice(self):
        qt = Quadtree25D()
        pts = generate_terrain_points(sine_hills, resolution=6)
        qt.insert_batch(pts)
        lattice = qt.project_to_lattice(cell_size=0.4)
        stats = lattice.stats()
        assert stats["bundle_count"] == 36

    def test_lattice_has_lace_edges(self):
        qt = Quadtree25D()
        pts = generate_terrain_points(sine_hills, resolution=8)
        qt.insert_batch(pts)
        lattice = qt.project_to_lattice(cell_size=0.3)
        stats = lattice.stats()
        assert stats["lace_edges"] > 0


# ---------------------------------------------------------------------------
# Terrain generators
# ---------------------------------------------------------------------------


class TestTerrainGenerators:
    def test_sine_hills_range(self):
        vals = [
            sine_hills(x * 0.1, y * 0.1) for x in range(-10, 10) for y in range(-10, 10)
        ]
        assert min(vals) < 0
        assert max(vals) > 0

    def test_ridge_has_peak(self):
        # Ridge peaks along x=y diagonal
        on_ridge = ridge_terrain(0.0, 0.0)
        off_ridge = ridge_terrain(0.5, -0.5)
        assert on_ridge > off_ridge

    def test_flat_with_spikes_base(self):
        # Far from spikes should be near base level
        val = flat_with_spikes(0.9, 0.9)
        assert val < 1.0

    def test_generate_terrain_count(self):
        pts = generate_terrain_points(sine_hills, resolution=10)
        assert len(pts) == 100

    def test_generate_terrain_auto_tongue(self):
        pts = generate_terrain_points(sine_hills, resolution=4, tongue="auto")
        tongues = {p.tongue for p in pts}
        assert len(tongues) > 1  # multiple tongues assigned


# ---------------------------------------------------------------------------
# Interop matrix
# ---------------------------------------------------------------------------


class TestInteropMatrix:
    def test_all_concepts_present(self):
        expected = {
            "QuadPoint",
            "QuadNode",
            "variance_subdivision",
            "terrain_mesh",
            "lod_select",
            "octree_bridge",
            "lattice_bridge",
        }
        assert expected == set(QUADTREE25D_INTEROP.keys())

    def test_python_in_all(self):
        for concept, langs in QUADTREE25D_INTEROP.items():
            assert "python" in langs, f"Missing python for {concept}"

    def test_multiple_languages(self):
        for concept, langs in QUADTREE25D_INTEROP.items():
            assert len(langs) >= 2, f"Only {len(langs)} language(s) for {concept}"


# ---------------------------------------------------------------------------
# Integration: full pipeline
# ---------------------------------------------------------------------------


class TestFullPipeline:
    def test_terrain_to_octree_to_lattice(self):
        """End-to-end: terrain → quadtree → mesh + octree + lattice."""
        qt = Quadtree25D(max_points=4, variance_threshold=0.5)
        pts = generate_terrain_points(sine_hills, resolution=10)
        qt.insert_batch(pts)

        # Mesh
        mesh = qt.to_terrain_mesh()
        assert mesh.triangle_count > 0

        # Octree
        octree = qt.project_to_octree(max_depth=4)
        assert octree.stats()["count"] == 100

        # Lattice
        lattice = qt.project_to_lattice()
        assert lattice.stats()["bundle_count"] == 100

    def test_mixed_terrain_types(self):
        """Mix different terrain functions in one quadtree."""
        qt = Quadtree25D(max_points=4, variance_threshold=0.3)
        qt.insert_batch(
            generate_terrain_points(sine_hills, bounds=(-1, -1, 0, 0), resolution=8)
        )
        qt.insert_batch(
            generate_terrain_points(ridge_terrain, bounds=(0, 0, 1, 1), resolution=8)
        )
        qt.insert_batch(
            generate_terrain_points(
                flat_with_spikes, bounds=(-1, 0, 0, 1), resolution=8
            )
        )

        stats = qt.stats()
        assert stats["point_count"] == 192  # 64 * 3
        assert stats["variance_splits"] > 0  # terrain should cause splits
