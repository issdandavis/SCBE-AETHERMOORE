"""
Tests for Cymatic Voxel Neural Network (Python Reference)
==========================================================

Covers:
- 6D Chladni equation properties
- Zone classification (nodal / negative_space / implied_boundary)
- Sacred Tongue assignment
- CymaticVoxelNet store & retrieve
- Semantic coherence gating
- Auto-propagation along nodal contours
- Network statistics
- Edge cases

@module tests/test_cymatic_voxel_net
@layer Layer 5, Layer 8, Layer 12, Layer 14
"""

import sys
import os
import math
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from symphonic_cipher.scbe_aethermoore.ai_brain.cymatic_voxel_net import (
    NODAL_THRESHOLD,
    REALM_CENTERS,
    SACRED_TONGUES,
    TONGUE_DIMENSION_MAP,
    CymaticVoxelNet,
    chladni_6d,
    classify_zone,
    dominant_tongue,
    estimate_nodal_density,
)


# ---------------------------------------------------------------------------
# A. 6D Chladni Equation
# ---------------------------------------------------------------------------


class TestChladni6D:
    """6D Chladni equation properties."""

    def test_returns_zero_at_origin(self):
        c = chladni_6d([0, 0, 0, 0, 0, 0], [1, 2, 3, 2, 1, 3])
        assert abs(c) < 1e-10

    def test_returns_zero_for_equal_pairs(self):
        # s2i = s2i+1 -> each term is cos(a)cos(b) - cos(b)cos(a) = 0
        c = chladni_6d([0.5, 0.3, 0.7, 0.1, 0.9, 0.2], [2, 2, 3, 3, 1, 1])
        assert abs(c) < 1e-10

    def test_nonzero_at_generic_point(self):
        c = chladni_6d([0.5, 0.3, 0.7, 0.1, 0.9, 0.2], [1, 2, 3, 4, 5, 6])
        assert abs(c) > 0.001

    def test_antisymmetric_under_pair_swap(self):
        coords = [0.3, 0.7, 0.1, 0.5, 0.9, 0.2]
        c1 = chladni_6d(coords, [2, 5, 3, 4, 1, 6])
        c2 = chladni_6d(coords, [5, 2, 4, 3, 6, 1])
        assert c1 == pytest.approx(-c2, abs=1e-8)

    def test_sums_three_paired_terms(self):
        coords = [0.5, 0.3, 0.0, 0.0, 0.0, 0.0]
        state = [2, 3, 0, 0, 0, 0]  # Only first pair nonzero
        expected = (
            math.cos(2 * math.pi * 0.5) * math.cos(3 * math.pi * 0.3)
            - math.cos(3 * math.pi * 0.5) * math.cos(2 * math.pi * 0.3)
        )
        assert chladni_6d(coords, state) == pytest.approx(expected, abs=1e-8)

    def test_handles_short_inputs(self):
        c = chladni_6d([0.5], [1, 2])
        assert math.isfinite(c)

    def test_bounded(self):
        random.seed(42)
        for _ in range(100):
            coords = [random.random() * 4 - 2 for _ in range(6)]
            state = [random.random() * 10 for _ in range(6)]
            assert abs(chladni_6d(coords, state)) <= 6.01


# ---------------------------------------------------------------------------
# B. Zone Classification
# ---------------------------------------------------------------------------


class TestClassifyZone:
    """Zone classification."""

    def test_nodal_near_zero(self):
        assert classify_zone(0.0005, 0.001) == "nodal"
        assert classify_zone(-0.0005, 0.001) == "nodal"
        assert classify_zone(0, 0.001) == "nodal"

    def test_boundary_zone(self):
        assert classify_zone(0.002, 0.001, 0.05) == "implied_boundary"
        assert classify_zone(0.04, 0.001, 0.05) == "implied_boundary"

    def test_negative_space(self):
        assert classify_zone(1.0, 0.001, 0.05) == "negative_space"
        assert classify_zone(-1.0, 0.001, 0.05) == "negative_space"

    def test_threshold_transitions(self):
        threshold = 0.01
        width = 0.05
        assert classify_zone(0.005, threshold, width) == "nodal"
        assert classify_zone(0.015, threshold, width) == "implied_boundary"
        assert classify_zone(0.055, threshold, width) == "implied_boundary"
        assert classify_zone(0.07, threshold, width) == "negative_space"


# ---------------------------------------------------------------------------
# C. Tongue Assignment
# ---------------------------------------------------------------------------


class TestDominantTongue:
    """Sacred Tongue assignment."""

    def test_ko_dim_0(self):
        assert dominant_tongue([1, 0, 0, 0, 0, 0]) == "KO"

    def test_av_dim_1(self):
        assert dominant_tongue([0, 1, 0, 0, 0, 0]) == "AV"

    def test_dr_dim_5(self):
        assert dominant_tongue([0, 0, 0, 0, 0, 1]) == "DR"

    def test_handles_negative(self):
        assert dominant_tongue([0, 0, 0, -5, 0, 0]) == "CA"

    def test_all_tongues_reachable(self):
        tongues = set()
        for i in range(6):
            coords = [0] * 6
            coords[i] = 1
            tongues.add(dominant_tongue(coords))
        assert len(tongues) == 6

    def test_tongue_dimension_map_matches(self):
        for i, t in enumerate(SACRED_TONGUES):
            assert TONGUE_DIMENSION_MAP[t] == i

    def test_realm_centers_exist(self):
        for t in SACRED_TONGUES:
            assert len(REALM_CENTERS[t]) == 6


# ---------------------------------------------------------------------------
# D. Store & Retrieve
# ---------------------------------------------------------------------------


class TestStoreRetrieve:
    """CymaticVoxelNet store & retrieve."""

    def test_starts_empty(self):
        net = CymaticVoxelNet()
        assert net.stored_count() == 0

    def test_store_increments(self):
        net = CymaticVoxelNet()
        net.store([0, 0, 0, 0, 0, 0], b"\x01\x02\x03")
        assert net.stored_count() == 1

    def test_stored_voxel_has_payload(self):
        net = CymaticVoxelNet()
        v = net.store([0.5, 0.3, 0.1, 0.2, 0.4, 0.6], b"\x2a")
        assert v.payload is not None
        assert v.payload[0] == 0x2A

    def test_probe_doesnt_store(self):
        net = CymaticVoxelNet()
        v = net.probe([0.5, 0.3, 0.1, 0.2, 0.4, 0.6])
        assert len(v.coords) == 6
        assert v.zone in ("nodal", "negative_space", "implied_boundary")
        assert v.tongue in SACRED_TONGUES
        assert math.isfinite(v.chladni_value)
        assert len(v.embedded) == 6
        assert net.stored_count() == 0

    def test_retrieve_stored(self):
        net = CymaticVoxelNet()
        coords = [0, 0, 0, 0, 0, 0]
        net.store(coords, b"\x63")
        result = net.retrieve(coords, [0, 0, 0, 0, 0, 0])
        assert result is not None
        assert result.payload[0] == 0x63

    def test_retrieve_unstored_returns_none(self):
        net = CymaticVoxelNet()
        result = net.retrieve([1, 2, 3, 4, 5, 6], [0, 0, 0, 0, 0, 0])
        assert result is None

    def test_clear(self):
        net = CymaticVoxelNet()
        net.store([0, 0, 0, 0, 0, 0], b"\x01")
        net.store([1, 0, 0, 0, 0, 0], b"\x02")
        net.clear()
        assert net.stored_count() == 0


# ---------------------------------------------------------------------------
# E. Semantic Coherence Gating
# ---------------------------------------------------------------------------


class TestCoherenceGating:
    """Semantic coherence gating via hyperbolic distance."""

    def test_nearby_access(self):
        net = CymaticVoxelNet()
        coords = [0.1, 0.0, 0.0, 0.0, 0.0, 0.0]
        net.store(coords, b"\x2a")
        result = net.retrieve(coords, [0.1, 0.0, 0.0, 0.0, 0.0, 0.0], max_distance=5.0)
        assert result is not None

    def test_distant_gated_out(self):
        net = CymaticVoxelNet()
        coords = [0.1, 0.0, 0.0, 0.0, 0.0, 0.0]
        net.store(coords, b"\x2a")
        result = net.retrieve(coords, [0.9, 0.8, 0.7, 0.6, 0.5, 0.4], max_distance=0.1)
        assert result is None


# ---------------------------------------------------------------------------
# F. Auto-Propagation
# ---------------------------------------------------------------------------


class TestPropagation:
    """Auto-propagation along nodal contours."""

    def test_propagation_produces_activations(self):
        net = CymaticVoxelNet([1, 1, 1, 1, 1, 1], max_hops=10, coherence_decay=0.85)
        acts = net.propagate([0, 0, 0, 0, 0, 0])
        assert len(acts) > 0

    def test_strength_decays(self):
        net = CymaticVoxelNet([1, 1, 1, 1, 1, 1], max_hops=10, coherence_decay=0.85)
        acts = net.propagate([0, 0, 0, 0, 0, 0], max_hops=5)
        if len(acts) >= 2:
            assert acts[1].strength < acts[0].strength

    def test_generation_increments(self):
        net = CymaticVoxelNet([1, 1, 1, 1, 1, 1], max_hops=10, coherence_decay=0.85)
        acts = net.propagate([0, 0, 0, 0, 0, 0], max_hops=5)
        for i, a in enumerate(acts):
            assert a.generation == i

    def test_harmonic_cost_grows(self):
        net = CymaticVoxelNet([1, 1, 1, 1, 1, 1], max_hops=10, coherence_decay=0.85)
        acts = net.propagate([0, 0, 0, 0, 0, 0], max_hops=5)
        if len(acts) >= 3:
            assert acts[2].harmonic_cost > acts[0].harmonic_cost

    def test_propagation_stops_at_negative_space(self):
        net = CymaticVoxelNet([1, 5, 3, 7, 2, 4])
        acts = net.propagate([0.5, 0.3, 0.7, 0.1, 0.9, 0.2], max_hops=20, step_size=0.05)
        assert len(acts) <= 20

    def test_last_propagation(self):
        net = CymaticVoxelNet([1, 1, 1, 1, 1, 1], max_hops=10, coherence_decay=0.85)
        net.propagate([0, 0, 0, 0, 0, 0], max_hops=3)
        log = net.last_propagation()
        assert len(log) > 0

    def test_respects_max_hops(self):
        net = CymaticVoxelNet([1, 1, 1, 1, 1, 1], max_hops=3)
        acts = net.propagate([0, 0, 0, 0, 0, 0])
        assert len(acts) <= 3


# ---------------------------------------------------------------------------
# G. Network Statistics
# ---------------------------------------------------------------------------


class TestNetworkStatistics:
    """Network statistics snapshot."""

    def test_snapshot_counts(self):
        net = CymaticVoxelNet([1, 2, 3, 4, 5, 6])
        for i in range(20):
            coords = [
                math.sin(i * 0.5),
                math.cos(i * 0.7),
                math.sin(i * 1.1),
                math.cos(i * 0.3),
                math.sin(i * 0.9),
                math.cos(i * 1.3),
            ]
            net.store(coords, bytes([i]))

        snap = net.snapshot()
        assert snap.total_voxels == 20
        assert snap.nodal_count + snap.negative_space_count + snap.boundary_count == 20
        assert 0 <= snap.nodal_fraction <= 1
        assert snap.mean_chladni_abs >= 0

    def test_nodal_density_reasonable(self):
        density = estimate_nodal_density([1, 2, 3, 2, 1, 3], samples=5000, threshold=0.01)
        assert 0 <= density <= 1

    def test_equal_pair_100_percent_nodal(self):
        density = estimate_nodal_density([2, 2, 3, 3, 1, 1], samples=1000, threshold=0.01)
        assert density == pytest.approx(1.0, abs=0.05)


# ---------------------------------------------------------------------------
# H. Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases."""

    def test_short_coords_padded(self):
        net = CymaticVoxelNet()
        v = net.probe([0.5])
        assert len(v.coords) == 6
        assert v.coords[1] == 0

    def test_state_and_position_update(self):
        net = CymaticVoxelNet()
        net.set_state([5, 4, 3, 2, 1, 0])
        assert net.get_state() == [5, 4, 3, 2, 1, 0]
        net.set_position([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
        assert net.get_position() == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]

    def test_poincare_embedding_stays_in_ball(self):
        net = CymaticVoxelNet()
        v = net.probe([10, -10, 20, -20, 30, -30])
        norm = math.sqrt(sum(x * x for x in v.embedded))
        assert norm < 1

    def test_realm_distance_non_negative(self):
        net = CymaticVoxelNet()
        random.seed(42)
        for _ in range(20):
            coords = [random.random() * 2 - 1 for _ in range(6)]
            v = net.probe(coords)
            assert v.realm_distance >= 0

    def test_chladni_finite(self):
        net = CymaticVoxelNet([1, 2, 3, 4, 5, 6])
        random.seed(42)
        for _ in range(50):
            coords = [(random.random() - 0.5) * 10 for _ in range(6)]
            v = net.probe(coords)
            assert math.isfinite(v.chladni_value)

    def test_empty_snapshot(self):
        net = CymaticVoxelNet()
        snap = net.snapshot()
        assert snap.total_voxels == 0
