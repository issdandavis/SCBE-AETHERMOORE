"""Tests for hydra/voxel_storage.py — 6D Voxel Storage with Chladni addressing."""
import math
import sys
import os

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hydra.voxel_storage import (
    Voxel,
    VoxelGrid,
    chladni_address,
    chladni_amplitude,
    compute_authority_hash,
    generate_chladni_grid,
    intent_similarity,
    normalize_intent,
    verify_authority,
)


# ── Chladni Addressing ──────────────────────────────────────────

class TestChladniAmplitude:
    def test_symmetric_modes(self):
        """A(x,y) with n=m should give zero everywhere (cos(n)-cos(n) = 0)."""
        for x in [0.0, 0.3, 0.5, 0.8, 1.0]:
            for y in [0.0, 0.3, 0.5, 0.8, 1.0]:
                assert abs(chladni_amplitude(x, y, n=3, m=3)) < 1e-10

    def test_antisymmetric(self):
        """A(x,y) = -A(y,x) for n != m."""
        a = chladni_amplitude(0.3, 0.7, n=3, m=2)
        b = chladni_amplitude(0.7, 0.3, n=3, m=2)
        assert abs(a + b) < 1e-10

    def test_bounded(self):
        """Amplitude should be in [-2, 2]."""
        for x in np.linspace(0, 1, 20):
            for y in np.linspace(0, 1, 20):
                a = chladni_amplitude(x, y, n=3, m=2)
                assert -2.0 - 1e-10 <= a <= 2.0 + 1e-10

    def test_center_value(self):
        """Known value at center (0.5, 0.5)."""
        a = chladni_amplitude(0.5, 0.5, n=3, m=2)
        expected = (math.cos(1.5 * math.pi) * math.cos(math.pi)
                    - math.cos(math.pi) * math.cos(1.5 * math.pi))
        assert abs(a - expected) < 1e-10


class TestChladniAddress:
    def test_range(self):
        """Address should be in [0, 1]."""
        for x in np.linspace(0, 1, 20):
            for y in np.linspace(0, 1, 20):
                ca = chladni_address(x, y)
                assert 0.0 - 1e-10 <= ca <= 1.0 + 1e-10

    def test_symmetric_mode_midpoint(self):
        """When n=m, amplitude is 0, address should be 0.5."""
        ca = chladni_address(0.3, 0.7, mode_n=3, mode_m=3)
        assert abs(ca - 0.5) < 1e-10

    def test_antisymmetric_pair(self):
        """Address(x,y) + Address(y,x) should equal 1.0 for n!=m."""
        ca1 = chladni_address(0.3, 0.7, mode_n=3, mode_m=2)
        ca2 = chladni_address(0.7, 0.3, mode_n=3, mode_m=2)
        assert abs(ca1 + ca2 - 1.0) < 1e-10


class TestChladniGrid:
    def test_shape(self):
        grid = generate_chladni_grid(resolution=8)
        assert grid.shape == (8, 8)

    def test_resolution_one(self):
        grid = generate_chladni_grid(resolution=1)
        assert grid.shape == (1, 1)

    def test_symmetry(self):
        """Grid should be antisymmetric: g[i,j] = -g[j,i] for n!=m."""
        grid = generate_chladni_grid(resolution=8, mode_n=3, mode_m=2)
        for i in range(8):
            for j in range(8):
                assert abs(grid[i, j] + grid[j, i]) < 1e-10


# ── Authority Hash ───────────────────────────────────────────────

class TestAuthorityHash:
    def test_deterministic(self):
        h1 = compute_authority_hash("agent.claude", "payload", 1000.0)
        h2 = compute_authority_hash("agent.claude", "payload", 1000.0)
        assert h1 == h2

    def test_different_agents(self):
        h1 = compute_authority_hash("agent.claude", "p", 1.0)
        h2 = compute_authority_hash("agent.gpt", "p", 1.0)
        assert h1 != h2

    def test_length(self):
        h = compute_authority_hash("agent", "data", 0.0)
        assert len(h) == 32

    def test_verify_valid(self):
        ts = 12345.0
        h = compute_authority_hash("agent.claude", "test", ts)
        assert verify_authority(h, "agent.claude", "test", ts)

    def test_verify_invalid(self):
        assert not verify_authority("badbadbad", "agent.claude", "test", 0.0)


# ── Intent Vector ────────────────────────────────────────────────

class TestIntentVector:
    def test_normalize_unit(self):
        v = normalize_intent([3.0, 4.0, 0.0])
        assert abs(np.linalg.norm(v) - 1.0) < 1e-10

    def test_normalize_zero(self):
        v = normalize_intent([0.0, 0.0, 0.0])
        assert np.linalg.norm(v) == 0.0

    def test_similarity_identical(self):
        a = normalize_intent([1.0, 0.0, 0.0])
        assert abs(intent_similarity(a, a) - 1.0) < 1e-10

    def test_similarity_orthogonal(self):
        a = normalize_intent([1.0, 0.0, 0.0])
        b = normalize_intent([0.0, 1.0, 0.0])
        assert abs(intent_similarity(a, b)) < 1e-10

    def test_similarity_opposite(self):
        a = normalize_intent([1.0, 0.0, 0.0])
        b = normalize_intent([-1.0, 0.0, 0.0])
        assert abs(intent_similarity(a, b) + 1.0) < 1e-10

    def test_similarity_zero_vector(self):
        a = normalize_intent([1.0, 0.0, 0.0])
        b = np.zeros(3)
        assert intent_similarity(a, b) == 0.0


# ── Voxel Dataclass ──────────────────────────────────────────────

class TestVoxel:
    def test_color_channel(self):
        v = Voxel(voxel_id="test", x=0, y=0, z=0, wavelength_nm=540.0, tongue="RU")
        ch = v.color_channel
        assert ch.wavelength_nm == 540.0
        assert ch.tongue == "RU"

    def test_position_6d_shape(self):
        v = Voxel(voxel_id="test", x=0.1, y=0.2, z=0.3, wavelength_nm=500.0)
        assert v.position_6d.shape == (6,)

    def test_distance_to_self_zero(self):
        v = Voxel(voxel_id="a", x=0.5, y=0.5, z=0.0, wavelength_nm=550.0,
                  authority_hash="abc", intent_vector=normalize_intent([1, 0, 0]))
        assert v.distance_to(v) == 0.0

    def test_distance_symmetry(self):
        a = Voxel(voxel_id="a", x=0.1, y=0.2, z=0.0, wavelength_nm=400.0)
        b = Voxel(voxel_id="b", x=0.8, y=0.6, z=0.1, wavelength_nm=700.0)
        assert abs(a.distance_to(b) - b.distance_to(a)) < 1e-10

    def test_spectral_distance_weighted(self):
        """Voxels at same spatial position but different wavelengths should have nonzero distance."""
        a = Voxel(voxel_id="a", x=0.5, y=0.5, z=0.0, wavelength_nm=400.0)
        b = Voxel(voxel_id="b", x=0.5, y=0.5, z=0.0, wavelength_nm=700.0)
        d = a.distance_to(b)
        assert d > 0


# ── VoxelGrid ────────────────────────────────────────────────────

class TestVoxelGrid:
    def test_store_returns_voxel(self):
        grid = VoxelGrid(resolution=4)
        v = grid.store(x=0.5, y=0.5, z=0.0, wavelength_nm=550.0, authority="claude")
        assert isinstance(v, Voxel)
        assert v.voxel_id in grid.voxels

    def test_store_custom_id(self):
        grid = VoxelGrid(resolution=4)
        v = grid.store(x=0.5, y=0.5, voxel_id="custom-1")
        assert v.voxel_id == "custom-1"

    def test_store_sets_chladni_address(self):
        grid = VoxelGrid(resolution=4)
        v = grid.store(x=0.3, y=0.7)
        assert 0.0 <= v.chladni_address <= 1.0

    def test_store_computes_authority_hash(self):
        grid = VoxelGrid(resolution=4)
        v = grid.store(x=0.5, y=0.5, authority="agent.claude")
        assert len(v.authority_hash) == 32

    def test_store_normalizes_intent(self):
        grid = VoxelGrid(resolution=4)
        v = grid.store(x=0.5, y=0.5, intent_vector=[3.0, 4.0, 0.0])
        assert abs(np.linalg.norm(v.intent_vector) - 1.0) < 1e-10


class TestVoxelGridUpdate:
    def test_update_increments_version(self):
        grid = VoxelGrid(resolution=4)
        v = grid.store(x=0.5, y=0.5, voxel_id="u1")
        assert v.version == 1
        grid.update("u1", z=0.5)
        assert grid.voxels["u1"].version == 2

    def test_update_nonexistent_returns_none(self):
        grid = VoxelGrid(resolution=4)
        assert grid.update("does-not-exist", z=1.0) is None

    def test_update_changes_value(self):
        grid = VoxelGrid(resolution=4)
        grid.store(x=0.5, y=0.5, voxel_id="u2", wavelength_nm=400.0)
        grid.update("u2", wavelength_nm=700.0)
        assert grid.voxels["u2"].wavelength_nm == 700.0

    def test_update_normalizes_intent(self):
        grid = VoxelGrid(resolution=4)
        grid.store(x=0.5, y=0.5, voxel_id="u3")
        grid.update("u3", intent_vector=[3.0, 4.0, 0.0])
        v = grid.voxels["u3"]
        assert abs(np.linalg.norm(v.intent_vector) - 1.0) < 1e-10

    def test_update_adds_temporal_event(self):
        grid = VoxelGrid(resolution=4)
        grid.store(x=0.5, y=0.5, voxel_id="u4")
        initial_events = len(grid._temporal_index)
        grid.update("u4", z=1.0)
        assert len(grid._temporal_index) == initial_events + 1


class TestVoxelGridQueries:
    @pytest.fixture()
    def populated_grid(self):
        grid = VoxelGrid(resolution=8)
        grid.store(x=0.1, y=0.1, wavelength_nm=400.0, authority="claude",
                   intent_vector=[1, 0, 0], intent_label="arch", voxel_id="v1")
        grid.store(x=0.5, y=0.5, wavelength_nm=540.0, authority="gpt",
                   intent_vector=[0, 1, 0], intent_label="draft", voxel_id="v2")
        grid.store(x=0.9, y=0.9, wavelength_nm=700.0, authority="claude",
                   intent_vector=[0, 0, 1], intent_label="research", voxel_id="v3")
        grid.store(x=0.3, y=0.7, wavelength_nm=410.0, authority="gemini",
                   intent_vector=[0.9, 0.1, 0], intent_label="review", voxel_id="v4")
        return grid

    def test_query_by_intent_ranking(self, populated_grid):
        results = populated_grid.query_by_intent([1, 0, 0], top_k=2)
        assert len(results) == 2
        # First result should be "arch" (exact match)
        assert results[0][0].intent_label == "arch"
        assert results[0][1] > 0.99

    def test_query_by_intent_min_similarity(self, populated_grid):
        results = populated_grid.query_by_intent([1, 0, 0], top_k=10, min_similarity=0.9)
        labels = [v.intent_label for v, _ in results]
        assert "arch" in labels
        assert "draft" not in labels  # orthogonal

    def test_query_by_wavelength(self, populated_grid):
        results = populated_grid.query_by_wavelength(400.0, tolerance_nm=15.0)
        ids = [v.voxel_id for v in results]
        assert "v1" in ids
        assert "v4" in ids
        assert "v2" not in ids

    def test_query_by_authority(self, populated_grid):
        results = populated_grid.query_by_authority("claude")
        assert len(results) == 2
        ids = {v.voxel_id for v in results}
        assert ids == {"v1", "v3"}

    def test_query_by_chladni_antinode(self, populated_grid):
        antinodes = populated_grid.query_by_chladni_zone("antinode", threshold=0.1)
        for v in antinodes:
            assert abs(v.chladni_address - 0.5) > 0.1

    def test_query_by_chladni_nodal(self, populated_grid):
        nodals = populated_grid.query_by_chladni_zone("nodal", threshold=0.1)
        for v in nodals:
            assert abs(v.chladni_address - 0.5) <= 0.1

    def test_time_slice_all(self, populated_grid):
        results = populated_grid.time_slice(t_start=0)
        assert len(results) == 4

    def test_time_slice_empty_window(self, populated_grid):
        results = populated_grid.time_slice(t_start=0, t_end=1)
        assert len(results) == 0  # all voxels created after epoch 1

    def test_nearest_neighbors(self, populated_grid):
        ref = populated_grid.voxels["v1"]
        neighbors = populated_grid.nearest_neighbors(ref, k=2)
        assert len(neighbors) == 2
        # Distances should be sorted ascending
        assert neighbors[0][1] <= neighbors[1][1]

    def test_nearest_neighbors_excludes_self(self, populated_grid):
        ref = populated_grid.voxels["v1"]
        neighbors = populated_grid.nearest_neighbors(ref, k=10)
        ids = [v.voxel_id for v, _ in neighbors]
        assert "v1" not in ids


class TestVoxelGridStats:
    def test_empty_stats(self):
        grid = VoxelGrid(resolution=4)
        s = grid.stats()
        assert s["count"] == 0

    def test_populated_stats(self):
        grid = VoxelGrid(resolution=4)
        grid.store(x=0.1, y=0.1, authority="claude", wavelength_nm=400.0, voxel_id="s1")
        grid.store(x=0.5, y=0.5, authority="gpt", wavelength_nm=600.0, voxel_id="s2")
        s = grid.stats()
        assert s["count"] == 2
        assert s["unique_agents"] == 2
        assert s["wavelength_range"] == (400.0, 600.0)
        assert s["chladni_mode"] == (3, 2)
        assert s["temporal_events"] == 2

    def test_stats_after_update(self):
        grid = VoxelGrid(resolution=4)
        grid.store(x=0.5, y=0.5, voxel_id="su1")
        grid.update("su1", z=1.0)
        s = grid.stats()
        assert s["versions_total"] == 2
        assert s["temporal_events"] == 2  # store + update
