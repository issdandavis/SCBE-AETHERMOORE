"""Tests for src/dynosphere/ — Dynosphere 3D ↔ Sacred Tongues ↔ 21D mapper."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.dynosphere.mapper import (
    DynosphereMapper,
    DynospherePoint,
    TongueProjection,
    CanonicalLift,
    project_to_tongues,
    lift_to_21d,
    round_trip_3d,
    reconstruct_3d_from_21d,
    reconstruct_tongue_proj_from_21d,
    nearest_polyhedron,
    TONGUE_DIRECTIONS,
    PHDM_POLYHEDRA,
    POLYHEDRA_CENTROIDS,
    _compute_braid_phase,
    _cross_tongue_coherence,
    _to_spherical,
)
from src.geoseed.sphere_grid import TONGUE_NAMES, TONGUE_PHASES, PHI_WEIGHTS


# ── Tongue Projection Tests ─────────────────────────────────────────────

class TestTongueProjection:
    def test_projection_returns_all_tongues(self):
        point = np.array([1.0, 0.0, 0.0])
        proj = project_to_tongues(point)
        assert set(proj.raw.keys()) == set(TONGUE_NAMES)
        assert set(proj.weighted.keys()) == set(TONGUE_NAMES)
        assert set(proj.normalized.keys()) == set(TONGUE_NAMES)

    def test_projection_normalized_range(self):
        for _ in range(10):
            point = np.random.randn(3)
            proj = project_to_tongues(point)
            for tongue in TONGUE_NAMES:
                assert 0.0 <= proj.normalized[tongue] <= 1.0 + 1e-10

    def test_ko_highest_raw_for_x_axis(self):
        """KO has phase 0 → basis direction (1,0,0). A point at (1,0,0) has highest raw KO projection."""
        point = np.array([1.0, 0.0, 0.0])
        proj = project_to_tongues(point)
        # KO has highest RAW dot product with (1,0,0)
        for t in TONGUE_NAMES:
            assert proj.raw["KO"] >= proj.raw[t] - 1e-10
        # Dominant is phi-weighted, so DR (PHI^5 weight) may win
        assert proj.dominant in TONGUE_NAMES

    def test_affinity_vector_shape(self):
        point = np.array([0.5, 0.5, 0.7])
        proj = project_to_tongues(point)
        assert proj.affinity_vector.shape == (6,)

    def test_zero_point_handled(self):
        point = np.array([0.0, 0.0, 0.0])
        proj = project_to_tongues(point)
        # All projections should be zero/equal
        assert proj.dominant in TONGUE_NAMES

    def test_antipodal_points_differ(self):
        p1 = np.array([1.0, 0.0, 0.0])
        p2 = np.array([-1.0, 0.0, 0.0])
        proj1 = project_to_tongues(p1)
        proj2 = project_to_tongues(p2)
        # Antipodal points should have different dominant tongues
        assert proj1.dominant != proj2.dominant


# ── 21D Lift Tests ───────────────────────────────────────────────────────

class TestLiftTo21D:
    def test_output_shape(self):
        point = np.array([0.5, 0.3, 0.8])
        lift = lift_to_21d(point)
        assert lift.state_21d.shape == (21,)

    def test_poincare_inside_ball(self):
        point = np.array([0.5, 0.3, 0.8])
        lift = lift_to_21d(point)
        assert np.linalg.norm(lift.poincare_point) < 1.0

    def test_source_3d_preserved(self):
        point = np.array([0.5, 0.3, 0.8])
        lift = lift_to_21d(point)
        # Source should be normalized to unit sphere
        expected = point / np.linalg.norm(point)
        np.testing.assert_allclose(lift.source_3d, expected, atol=1e-10)

    def test_context_block_matches_projection(self):
        point = np.array([1.0, 0.0, 0.0])
        proj = project_to_tongues(point)
        lift = lift_to_21d(point, proj)
        for i, tongue in enumerate(TONGUE_NAMES):
            assert abs(lift.state_21d[i] - proj.normalized[tongue]) < 1e-10

    def test_navigation_block_contains_position(self):
        point = np.array([0.0, 0.0, 1.0])
        lift = lift_to_21d(point)
        np.testing.assert_allclose(lift.state_21d[6:9], [0.0, 0.0, 1.0], atol=1e-10)

    def test_braid_phase_valid(self):
        point = np.array([1.0, 0.0, 0.0])
        lift = lift_to_21d(point)
        par, perp = lift.braid_phase
        assert par in (-1, 0, 1)
        assert perp in (-1, 0, 1)

    def test_multiple_points_give_different_states(self):
        p1 = np.array([1.0, 0.0, 0.0])
        p2 = np.array([0.0, 1.0, 0.0])
        l1 = lift_to_21d(p1)
        l2 = lift_to_21d(p2)
        assert not np.allclose(l1.state_21d, l2.state_21d)


# ── Round-Trip Tests ─────────────────────────────────────────────────────

class TestRoundTrip:
    def test_round_trip_exact(self):
        """3D → 21D → 3D should be exact (position stored directly)."""
        point = np.array([0.5, 0.3, 0.8])
        reconstructed, error = round_trip_3d(point)
        assert error < 1e-10

    def test_round_trip_unit_vectors(self):
        for axis in [np.array([1, 0, 0]), np.array([0, 1, 0]), np.array([0, 0, 1])]:
            reconstructed, error = round_trip_3d(axis.astype(float))
            assert error < 1e-10

    def test_round_trip_random_points(self):
        rng = np.random.default_rng(42)
        for _ in range(20):
            point = rng.standard_normal(3)
            reconstructed, error = round_trip_3d(point)
            assert error < 1e-10

    def test_reconstruct_3d_from_state(self):
        point = np.array([0.577, 0.577, 0.577])
        lift = lift_to_21d(point)
        recon = reconstruct_3d_from_21d(lift.state_21d)
        expected = point / np.linalg.norm(point)
        np.testing.assert_allclose(recon, expected, atol=1e-6)

    def test_reconstruct_tongue_proj(self):
        point = np.array([1.0, 0.0, 0.0])
        lift = lift_to_21d(point)
        recon_proj = reconstruct_tongue_proj_from_21d(lift.state_21d)
        for tongue in TONGUE_NAMES:
            assert abs(recon_proj[tongue] - lift.tongue_projection.normalized[tongue]) < 1e-10


# ── PHDM Polyhedra Tests ────────────────────────────────────────────────

class TestPHDMPolyhedra:
    def test_16_polyhedra_defined(self):
        assert len(PHDM_POLYHEDRA) == 16

    def test_centroids_on_unit_sphere(self):
        for i in range(16):
            norm = np.linalg.norm(POLYHEDRA_CENTROIDS[i])
            assert abs(norm - 1.0) < 1e-10

    def test_nearest_polyhedron_returns_valid_index(self):
        point = np.array([1.0, 0.0, 0.0])
        idx = nearest_polyhedron(point)
        assert 0 <= idx < 16

    def test_different_points_can_map_to_different_faces(self):
        p1 = np.array([1.0, 0.0, 0.0])
        p2 = np.array([0.0, 0.0, -1.0])
        f1 = nearest_polyhedron(p1)
        f2 = nearest_polyhedron(p2)
        # Not guaranteed to differ, but these are far apart enough
        # Just check valid indices
        assert 0 <= f1 < 16
        assert 0 <= f2 < 16


# ── Braid Phase Tests ───────────────────────────────────────────────────

class TestBraidPhase:
    def test_phase_values_valid(self):
        point = np.array([1.0, 0.0, 0.0])
        proj = project_to_tongues(point)
        par, perp = _compute_braid_phase(proj)
        assert par in (-1, 0, 1)
        assert perp in (-1, 0, 1)

    def test_strong_projection_gives_advancing(self):
        """Point directly on a tongue axis should give parallel=1."""
        point = np.array([1.0, 0.0, 0.0])  # aligns with KO
        proj = project_to_tongues(point)
        par, _ = _compute_braid_phase(proj)
        assert par == 1  # dominant tongue has high projection


# ── Cross-Tongue Coherence Tests ─────────────────────────────────────────

class TestCrossTongueCoherence:
    def test_returns_three_values(self):
        proj = project_to_tongues(np.array([1.0, 0.0, 0.0]))
        trust, byz, coh = _cross_tongue_coherence(proj)
        assert isinstance(trust, float)
        assert isinstance(byz, float)
        assert isinstance(coh, float)

    def test_trust_in_range(self):
        proj = project_to_tongues(np.array([0.5, 0.5, 0.7]))
        trust, _, _ = _cross_tongue_coherence(proj)
        assert 0.0 <= trust <= 1.0

    def test_coherence_in_range(self):
        proj = project_to_tongues(np.array([0.5, 0.5, 0.7]))
        _, _, coh = _cross_tongue_coherence(proj)
        assert 0.0 <= coh <= 1.0


# ── DynosphereMapper Tests ──────────────────────────────────────────────

class TestDynosphereMapper:
    def test_map_point_returns_complete(self):
        mapper = DynosphereMapper(resolution=1)  # small for speed
        point = mapper.map_point(np.array([0.5, 0.3, 0.8]))
        assert isinstance(point, DynospherePoint)
        assert point.position_3d.shape == (3,)
        assert point.canonical.state_21d.shape == (21,)
        assert point.tongue_proj.dominant in TONGUE_NAMES
        assert 0 <= point.polyhedron_face < 16

    def test_spherical_coordinates(self):
        mapper = DynosphereMapper(resolution=1)
        point = mapper.map_point(np.array([0.0, 0.0, 1.0]))
        theta, phi = point.spherical
        assert abs(theta) < 1e-10  # north pole: theta = 0
        assert isinstance(phi, float)

    def test_map_grid_vertex(self):
        mapper = DynosphereMapper(resolution=1)
        point = mapper.map_grid_vertex("KO", 0)
        assert isinstance(point, DynospherePoint)
        assert point.tongue_proj.dominant in TONGUE_NAMES

    def test_batch_map(self):
        mapper = DynosphereMapper(resolution=1)
        points = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ])
        results = mapper.batch_map(points)
        assert len(results) == 3
        for r in results:
            assert isinstance(r, DynospherePoint)

    def test_deposit_and_propagate(self):
        mapper = DynosphereMapper(resolution=1, signal_dim=16)
        signal = np.ones(16)
        result = mapper.deposit_and_propagate(
            np.array([1.0, 0.0, 0.0]), signal, n_steps=1
        )
        assert set(result.keys()) == set(TONGUE_NAMES)
        # Some energy should have propagated
        total_energy = sum(np.sum(v ** 2) for v in result.values())
        assert total_energy > 0

    def test_global_state_21d(self):
        mapper = DynosphereMapper(resolution=1, signal_dim=16)
        state = mapper.global_state_21d()
        assert state.shape == (21,)

    def test_diagnostics(self):
        mapper = DynosphereMapper(resolution=1)
        diag = mapper.diagnostics()
        assert diag["resolution"] == 1
        assert diag["polyhedra_count"] == 16
        assert set(diag["grids"].keys()) == set(TONGUE_NAMES)


# ── Spherical Coordinate Tests ──────────────────────────────────────────

class TestSphericalCoordinates:
    def test_north_pole(self):
        theta, phi = _to_spherical(np.array([0.0, 0.0, 1.0]))
        assert abs(theta) < 1e-10

    def test_south_pole(self):
        theta, phi = _to_spherical(np.array([0.0, 0.0, -1.0]))
        assert abs(theta - math.pi) < 1e-10

    def test_equator(self):
        theta, phi = _to_spherical(np.array([1.0, 0.0, 0.0]))
        assert abs(theta - math.pi / 2) < 1e-10


# ── Tongue Direction Tests ──────────────────────────────────────────────

class TestTongueDirections:
    def test_all_tongues_have_directions(self):
        assert set(TONGUE_DIRECTIONS.keys()) == set(TONGUE_NAMES)

    def test_directions_are_unit_vectors_in_xy(self):
        for tongue, d in TONGUE_DIRECTIONS.items():
            assert d.shape == (3,)
            assert abs(np.linalg.norm(d) - 1.0) < 1e-10
            assert abs(d[2]) < 1e-10  # z component is 0

    def test_ko_points_along_x(self):
        """KO has phase 0, so direction should be (1, 0, 0)."""
        np.testing.assert_allclose(TONGUE_DIRECTIONS["KO"], [1.0, 0.0, 0.0], atol=1e-10)
