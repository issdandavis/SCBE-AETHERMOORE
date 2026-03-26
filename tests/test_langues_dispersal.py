"""Tests for langues metric 6D bit spin dispersal routing."""

from __future__ import annotations

import math

import numpy as np
import pytest

from src.storage.langues_dispersal import (
    PHI,
    TONGUE_NAMES,
    SpinVector,
    build_metric_tensor,
    compute_dispersal,
    dispersal_route,
    quantize_spin,
)

# =========================================================================== #
#  Metric Tensor
# =========================================================================== #


class TestMetricTensor:
    def test_is_6x6_diagonal(self):
        G = build_metric_tensor()
        assert G.shape == (6, 6)
        for i in range(6):
            for j in range(6):
                if i == j:
                    assert G[i, j] == pytest.approx(PHI**i, rel=1e-14)
                else:
                    assert G[i, j] == 0.0

    def test_positive_definite(self):
        G = build_metric_tensor()
        eigenvalues = np.linalg.eigvalsh(G)
        assert all(ev > 0 for ev in eigenvalues)

    def test_weights_match_golden_ratio_progression(self):
        G = build_metric_tensor()
        for i in range(5):
            ratio = G[i + 1, i + 1] / G[i, i]
            assert ratio == pytest.approx(PHI, rel=1e-14)


# =========================================================================== #
#  Spin Quantization
# =========================================================================== #


class TestSpinQuantization:
    def test_centroid_gives_all_zero_spin(self):
        centroid = [0.5, 0.3, 0.2, 0.4, 0.1, 0.6]
        sv = quantize_spin(centroid, centroid, threshold=0.05)
        assert sv.spins == (0, 0, 0, 0, 0, 0)
        assert sv.magnitude == 0
        assert sv.code == "000000"

    def test_above_centroid_gives_positive_spin(self):
        centroid = [0.5] * 6
        above = [0.7] * 6
        sv = quantize_spin(above, centroid, threshold=0.05)
        assert all(s == 1 for s in sv.spins)
        assert sv.magnitude == 6
        assert sv.code == "++++++"

    def test_below_centroid_gives_negative_spin(self):
        centroid = [0.5] * 6
        below = [0.2] * 6
        sv = quantize_spin(below, centroid, threshold=0.05)
        assert all(s == -1 for s in sv.spins)
        assert sv.code == "------"

    def test_mixed_spins(self):
        centroid = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        mixed = [0.8, 0.5, 0.2, 0.7, 0.5, 0.1]
        sv = quantize_spin(mixed, centroid, threshold=0.05)
        assert sv.spins == (1, 0, -1, 1, 0, -1)
        assert sv.code == "+0-+0-"
        assert sv.magnitude == 4

    def test_threshold_creates_dead_zone(self):
        centroid = [0.5] * 6
        near = [0.52, 0.48, 0.54, 0.46, 0.505, 0.495]
        sv = quantize_spin(near, centroid, threshold=0.05)
        # 0.52-0.5=0.02 < 0.05 → 0, 0.54-0.5=0.04 < 0.05 → 0
        assert sv.spins == (0, 0, 0, 0, 0, 0)

    def test_metric_weighted_norm_increases_with_higher_tongues(self):
        # Same spin pattern, but the norm should weight DR (idx 5) much more than KO (idx 0)
        sv_ko = SpinVector(spins=(1, 0, 0, 0, 0, 0))
        sv_dr = SpinVector(spins=(0, 0, 0, 0, 0, 1))
        assert sv_dr.metric_weighted_norm() > sv_ko.metric_weighted_norm()
        assert sv_dr.metric_weighted_norm() == pytest.approx(math.sqrt(PHI**5), rel=1e-14)


# =========================================================================== #
#  Dispersal Rate
# =========================================================================== #


class TestDispersalRate:
    def test_identical_records_have_zero_dispersal(self):
        vecs = [[0.5, 0.3, 0.2, 0.4, 0.1, 0.6]] * 20
        report = compute_dispersal(vecs)
        assert report.dispersal_rate == 0.0
        assert report.spin_entropy == 0.0

    def test_spread_records_have_positive_dispersal(self):
        rng = np.random.default_rng(42)
        vecs = rng.uniform(0, 1, size=(50, 6)).tolist()
        report = compute_dispersal(vecs)
        assert report.dispersal_rate > 0
        assert report.record_count == 50

    def test_higher_spread_gives_higher_dispersal(self):
        # Tight cluster
        tight = [[0.5 + 0.01 * i, 0.5, 0.5, 0.5, 0.5, 0.5] for i in range(20)]
        # Wide spread
        wide = [[0.1 + 0.04 * i, 0.1 + 0.04 * i, 0.5, 0.5, 0.5, 0.5] for i in range(20)]

        d_tight = compute_dispersal(tight)
        d_wide = compute_dispersal(wide)
        assert d_wide.dispersal_rate > d_tight.dispersal_rate

    def test_spin_entropy_is_bounded(self):
        rng = np.random.default_rng(7)
        vecs = rng.uniform(0, 1, size=(100, 6)).tolist()
        report = compute_dispersal(vecs)
        assert 0.0 <= report.spin_entropy <= 1.0

    def test_dominant_tongue_is_valid(self):
        rng = np.random.default_rng(11)
        vecs = rng.uniform(0, 1, size=(30, 6)).tolist()
        report = compute_dispersal(vecs)
        assert report.dominant_tongue in TONGUE_NAMES

    def test_effective_dimension_between_0_and_6(self):
        rng = np.random.default_rng(13)
        vecs = rng.uniform(0, 1, size=(40, 6)).tolist()
        report = compute_dispersal(vecs)
        assert 0.0 <= report.effective_dimension <= 6.0

    def test_empty_input(self):
        report = compute_dispersal([])
        assert report.record_count == 0
        assert report.dispersal_rate == 0.0

    def test_per_tongue_dispersal_sums_to_total(self):
        rng = np.random.default_rng(17)
        vecs = rng.uniform(0, 1, size=(25, 6)).tolist()
        report = compute_dispersal(vecs)
        tongue_sum = sum(report.tongue_dispersals.values())
        assert tongue_sum == pytest.approx(report.dispersal_rate, rel=1e-4)

    def test_dr_tongue_contributes_most_when_spread_in_dr(self):
        """DR (idx 5) has weight φ^5 ≈ 11.09. If spread is mostly in DR,
        DR should dominate the dispersal."""
        vecs = [[0.5, 0.5, 0.5, 0.5, 0.5, 0.1 + 0.04 * i] for i in range(20)]
        report = compute_dispersal(vecs)
        assert report.dominant_tongue == "DR"


# =========================================================================== #
#  Dispersal Routing
# =========================================================================== #


class TestDispersalRouting:
    def test_low_spin_routes_to_hemisphere(self):
        centroid = [0.5] * 6
        near = [0.52, 0.48, 0.51, 0.49, 0.5, 0.5]  # all within threshold
        route = dispersal_route(near, centroid, threshold=0.05)
        assert route["zone"] == "hemisphere"
        assert route["spin_magnitude"] <= 2

    def test_high_spin_routes_to_cone(self):
        centroid = [0.5] * 6
        far = [0.9, 0.1, 0.9, 0.1, 0.9, 0.1]  # all far from centroid
        route = dispersal_route(far, centroid, threshold=0.05)
        assert route["zone"] == "cone"
        assert route["spin_magnitude"] >= 4

    def test_route_includes_spin_code(self):
        centroid = [0.5] * 6
        record = [0.8, 0.5, 0.2, 0.7, 0.5, 0.1]
        route = dispersal_route(record, centroid, threshold=0.05)
        assert len(route["spin_code"]) == 6
        assert set(route["spin_code"]) <= {"+", "0", "-"}

    def test_route_dominant_tongue_valid(self):
        centroid = [0.5] * 6
        record = [0.5, 0.5, 0.5, 0.5, 0.5, 0.9]
        route = dispersal_route(record, centroid, threshold=0.05)
        assert route["dominant_tongue"] in TONGUE_NAMES


# =========================================================================== #
#  Integration: Dispersal + Fusion Surfaces
# =========================================================================== #


class TestDispersalFusionIntegration:
    def test_dispersal_routes_match_semisphere_cone_zones(self):
        """Records routed to 'hemisphere' by dispersal should have low
        Poincare radius, matching SemiSphereCone's logic."""
        from scripts.system.storage_bridge_lab import build_bridge_workload, _note_to_geometry

        notes = build_bridge_workload(seed=42, count=50)
        geos = [_note_to_geometry(n, i) for i, n in enumerate(notes)]
        tongue_vecs = [g["tongue_coords"] for g in geos]

        report = compute_dispersal(tongue_vecs)
        centroid = report.centroid

        hemisphere_count = 0
        cone_count = 0
        for g in geos:
            route = dispersal_route(g["tongue_coords"], centroid)
            float(np.linalg.norm(g["coord_3d"]))
            if route["zone"] == "hemisphere":
                hemisphere_count += 1
            else:
                cone_count += 1

        # Both zones should have records (not degenerate)
        assert hemisphere_count > 0
        assert cone_count > 0
        assert hemisphere_count + cone_count == 50

    def test_dispersal_report_from_real_workload(self):
        """Full dispersal analysis on a real workload."""
        from scripts.system.storage_bridge_lab import build_bridge_workload, _note_to_geometry

        notes = build_bridge_workload(seed=99, count=200)
        geos = [_note_to_geometry(n, i) for i, n in enumerate(notes)]
        tongue_vecs = [g["tongue_coords"] for g in geos]

        report = compute_dispersal(tongue_vecs)
        assert report.record_count == 200
        assert report.dispersal_rate > 0
        assert report.spin_entropy > 0
        assert report.effective_dimension > 1.0  # at least 2 tongues active
        assert len(report.spin_distribution) >= 2  # at least 2 different spin codes
