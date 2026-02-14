"""
Tests for Tri-Manifold Lattice (Python Reference)
==================================================

Covers:
- Harmonic scaling H(d, R) = R^(d²) properties
- Triadic distance (weighted Euclidean norm)
- TemporalWindow sliding average
- TriManifoldLattice integration
- Temporal resonance and anomaly detection
- Duality: H(d, R) * H(d, 1/R) = 1

@module tests/test_tri_manifold_lattice
@layer Layer 5, Layer 11, Layer 12, Layer 14
"""

import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from symphonic_cipher.scbe_aethermoore.ai_brain.tri_manifold_lattice import (
    HARMONIC_R,
    TemporalWindow,
    TriManifoldLattice,
    TriadicWeights,
    harmonic_scale,
    harmonic_scale_inverse,
    harmonic_scale_table,
    triadic_distance,
    triadic_partial,
)
from symphonic_cipher.scbe_aethermoore.ai_brain.unified_state import (
    BRAIN_DIMENSIONS,
    PHI,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def safe_vector(scale: float = 0.1):
    """Create a safe 21D vector near Poincaré center."""
    return [math.sin(i * 0.7) * scale for i in range(BRAIN_DIMENSIONS)]


def drift_vector(step: int, max_scale: float = 0.5):
    """Create a 21D vector that progressively drifts from center."""
    scale = min(max_scale, step * 0.02)
    return [math.sin(i * 0.7 + step * 0.3) * scale for i in range(BRAIN_DIMENSIONS)]


ORIGIN = [0.0] * BRAIN_DIMENSIONS


# ---------------------------------------------------------------------------
# Harmonic Scaling Law
# ---------------------------------------------------------------------------


class TestHarmonicScale:
    """H(d, R) = R^(d²) properties."""

    def test_h1(self):
        assert harmonic_scale(1, 1.5) == pytest.approx(1.5)

    def test_h2(self):
        assert harmonic_scale(2, 1.5) == pytest.approx(1.5**4, rel=1e-6)

    def test_h3(self):
        assert harmonic_scale(3, 1.5) == pytest.approx(1.5**9, rel=1e-4)

    def test_h6_over_two_million(self):
        h6 = harmonic_scale(6, 1.5)
        assert h6 > 2_000_000
        assert h6 < 2_500_000

    def test_super_exponential_growth(self):
        prev_ratio = 0
        for d in range(1, 6):
            ratio = harmonic_scale(d + 1, 1.5) / harmonic_scale(d, 1.5)
            assert ratio > prev_ratio
            prev_ratio = ratio

    def test_h0_is_one(self):
        assert harmonic_scale(0, 1.5) == 1.0
        assert harmonic_scale(0, 42) == 1.0

    def test_r_one_always_one(self):
        for d in range(7):
            assert harmonic_scale(d, 1.0) == 1.0

    def test_negative_d_returns_one(self):
        assert harmonic_scale(-1, 1.5) == 1.0

    def test_zero_r_returns_zero(self):
        assert harmonic_scale(3, 0) == 0.0

    def test_duality(self):
        for d in range(1, 7):
            product = harmonic_scale(d, 1.5) * harmonic_scale_inverse(d, 1.5)
            assert product == pytest.approx(1.0, abs=1e-8)

    def test_monotonic_increasing_for_r_gt_1(self):
        prev = 0
        for d in range(7):
            h = harmonic_scale(d, 1.5)
            assert h >= prev
            prev = h

    def test_monotonic_decreasing_for_r_lt_1(self):
        prev = float("inf")
        for d in range(7):
            h = harmonic_scale(d, 0.5)
            assert h <= prev
            prev = h

    def test_table(self):
        table = harmonic_scale_table(3, 1.5)
        assert len(table) == 3
        assert table[0]["d"] == 1
        assert table[0]["scale"] == pytest.approx(1.5)

    def test_golden_ratio_scaling(self):
        h = harmonic_scale(3, PHI)
        assert h == pytest.approx(PHI**9, rel=1e-4)
        assert h > 50

    def test_perfect_fourth(self):
        R = 4 / 3
        h3 = harmonic_scale(3, R)
        h6 = harmonic_scale(6, R)
        assert h6 / h3 > 1000


# ---------------------------------------------------------------------------
# Triadic Distance
# ---------------------------------------------------------------------------


class TestTriadicDistance:
    """Weighted Euclidean norm of 3 manifold distances."""

    def test_zero_all(self):
        assert triadic_distance(0, 0, 0) == 0.0

    def test_positive_definite(self):
        assert triadic_distance(1, 0, 0) > 0
        assert triadic_distance(0, 1, 0) > 0
        assert triadic_distance(0, 0, 1) > 0

    def test_immediate_weight_dominates(self):
        w = TriadicWeights(0.5, 0.3, 0.2)
        d_imm = triadic_distance(1, 0, 0, w)
        d_mem = triadic_distance(0, 1, 0, w)
        d_gov = triadic_distance(0, 0, 1, w)
        assert d_imm > d_mem > d_gov

    def test_monotonic(self):
        w = TriadicWeights(0.5, 0.3, 0.2)
        for x in range(6):
            d1 = triadic_distance(x, 2, 1, w)
            d2 = triadic_distance(x + 1, 2, 1, w)
            assert d2 >= d1

    def test_non_negative_random(self):
        import random

        random.seed(42)
        for _ in range(100):
            d1 = random.random() * 10
            d2 = random.random() * 10
            dg = random.random() * 10
            assert triadic_distance(d1, d2, dg) >= 0

    def test_partial_non_negative(self):
        w = TriadicWeights(0.5, 0.3, 0.2)
        d_tri = triadic_distance(3, 4, 5, w)
        assert triadic_partial(3, w.immediate, d_tri) >= 0
        assert triadic_partial(4, w.memory, d_tri) >= 0
        assert triadic_partial(5, w.governance, d_tri) >= 0

    def test_partial_zero_when_dtri_zero(self):
        assert triadic_partial(0, 0.5, 0) == 0.0


# ---------------------------------------------------------------------------
# TemporalWindow
# ---------------------------------------------------------------------------


class TestTemporalWindow:
    """Sliding window for distance averaging."""

    def test_starts_empty(self):
        w = TemporalWindow(5)
        assert w.filled() == 0
        assert w.average() == 0.0
        assert not w.is_warmed_up()

    def test_accumulates(self):
        w = TemporalWindow(5)
        w.push(1)
        w.push(2)
        w.push(3)
        assert w.filled() == 3
        assert w.average() == pytest.approx(2.0)

    def test_warmup(self):
        w = TemporalWindow(5)
        for i in range(1, 6):
            w.push(i)
        assert w.is_warmed_up()
        assert w.average() == pytest.approx(3.0)

    def test_sliding(self):
        w = TemporalWindow(5)
        for i in range(1, 6):
            w.push(i)
        w.push(6)  # drops 1
        assert w.average() == pytest.approx(4.0)

    def test_latest(self):
        w = TemporalWindow(5)
        w.push(10)
        w.push(20)
        assert w.latest() == 20

    def test_variance_constant(self):
        w = TemporalWindow(5)
        for _ in range(5):
            w.push(7)
        assert w.variance() == pytest.approx(0.0, abs=1e-10)

    def test_reset(self):
        w = TemporalWindow(5)
        for i in range(5):
            w.push(i)
        w.reset()
        assert w.filled() == 0
        assert w.average() == 0.0

    def test_size_one(self):
        w = TemporalWindow(1)
        w.push(5)
        assert w.average() == 5
        w.push(10)
        assert w.average() == 10
        assert w.is_warmed_up()

    def test_rejects_size_zero(self):
        with pytest.raises(ValueError):
            TemporalWindow(0)


# ---------------------------------------------------------------------------
# TriManifoldLattice
# ---------------------------------------------------------------------------


class TestTriManifoldLattice:
    """Full lattice integration."""

    def test_starts_empty(self):
        lat = TriManifoldLattice()
        assert lat.tick == 0
        assert lat.current_triadic_distance() == 0.0

    def test_ingest_produces_node(self):
        lat = TriManifoldLattice()
        node = lat.ingest(safe_vector(0.1))
        assert node.tick == 1
        assert len(node.raw_state) == BRAIN_DIMENSIONS
        assert len(node.embedded) == BRAIN_DIMENSIONS
        assert node.hyperbolic_dist >= 0
        assert node.triadic_distance >= 0
        assert node.embedded_norm < 1.0

    def test_origin_near_zero(self):
        lat = TriManifoldLattice()
        node = lat.ingest(ORIGIN)
        assert node.hyperbolic_dist < 0.01
        assert node.triadic_distance < 0.01

    def test_drift_increases_distance(self):
        lat = TriManifoldLattice()
        distances = []
        for i in range(20):
            node = lat.ingest(drift_vector(i, 0.8))
            distances.append(node.triadic_distance)
        first_half = sum(distances[:10]) / 10
        second_half = sum(distances[10:]) / 10
        assert second_half > first_half

    def test_harmonic_cost_scaling(self):
        lat = TriManifoldLattice(harmonic_dimensions=6)
        node = lat.ingest(safe_vector(0.3))
        h6 = 1.5**36
        assert node.harmonic_cost == pytest.approx(node.triadic_distance * h6, rel=1e-2)

    def test_weights_normalized(self):
        lat = TriManifoldLattice(weights=TriadicWeights(5, 3, 2))
        w = lat.weights
        assert w.immediate + w.memory + w.governance == pytest.approx(1.0)

    def test_temporal_resonance_empty(self):
        lat = TriManifoldLattice()
        assert lat.temporal_resonance() == 1.0

    def test_temporal_resonance_constant(self):
        lat = TriManifoldLattice()
        for _ in range(50):
            lat.ingest(safe_vector(0.15))
        assert lat.temporal_resonance() > 0.95

    def test_temporal_resonance_drops_on_shift(self):
        lat = TriManifoldLattice(
            window_immediate=3, window_memory=10, window_governance=30
        )
        for _ in range(50):
            lat.ingest(ORIGIN)
        steady = lat.temporal_resonance()
        for _ in range(3):
            lat.ingest(safe_vector(0.8))
        shifted = lat.temporal_resonance()
        assert shifted < steady

    def test_temporal_anomaly_empty(self):
        lat = TriManifoldLattice()
        assert lat.temporal_anomaly() == 0.0

    def test_drift_velocity_zero_initially(self):
        lat = TriManifoldLattice()
        assert lat.drift_velocity() == 0.0
        lat.ingest(ORIGIN)
        assert lat.drift_velocity() == 0.0

    def test_drift_acceleration_zero_initially(self):
        lat = TriManifoldLattice()
        assert lat.drift_acceleration() == 0.0

    def test_snapshot(self):
        lat = TriManifoldLattice()
        lat.ingest(safe_vector(0.2))
        lat.ingest(safe_vector(0.3))
        snap = lat.snapshot()
        assert snap.tick == 2
        assert snap.node_count == 2

    def test_duality_verification(self):
        lat = TriManifoldLattice()
        for d in range(7):
            _, _, product = lat.verify_duality(d)
            assert product == pytest.approx(1.0, abs=1e-6)

    def test_reset(self):
        lat = TriManifoldLattice()
        for _ in range(5):
            lat.ingest(safe_vector())
        lat.reset()
        assert lat.tick == 0
        assert lat.current_triadic_distance() == 0.0

    def test_manifold_convergence(self):
        """All three manifolds converge for constant input."""
        lat = TriManifoldLattice()
        for _ in range(200):
            lat.ingest(safe_vector(0.2))
        snap = lat.snapshot()
        d = snap.manifold_distances
        assert abs(d["immediate"] - d["memory"]) < 0.01
        assert abs(d["memory"] - d["governance"]) < 0.01

    def test_embedded_norm_strictly_below_one(self):
        lat = TriManifoldLattice()
        import random

        random.seed(42)
        for _ in range(50):
            v = [(random.random() - 0.5) * 20 for _ in range(BRAIN_DIMENSIONS)]
            node = lat.ingest(v)
            assert node.embedded_norm < 1.0
