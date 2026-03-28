#!/usr/bin/env python3
"""
Focused formal axiom coverage for the live SCBE reference math surfaces.

This suite complements ``test_theoretical_axioms.py`` instead of replacing it:
- FA1-FA3 are checked against the legacy superexponential wall implementation
  still used by theorem/patent-aligned modules.
- FA4/FA7/FA9/FA10/FA12 are checked against the current reference pipeline.
- The current bounded Layer 12 score is covered explicitly as a regression so
  future work does not accidentally test the wrong formula again.
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

try:
    from scbe_14layer_reference import (
        layer_3_weighted_transform,
        layer_5_hyperbolic_distance,
        layer_6_breathing_transform,
        layer_9_spectral_coherence,
        layer_10_spin_coherence,
        layer_12_harmonic_scaling,
    )
    from symphonic_cipher.qasi_core import harmonic_scaling as legacy_harmonic_scaling

    SCBE_AVAILABLE = True
except ImportError:
    SCBE_AVAILABLE = False


def _ball_point(
    rng: np.random.Generator, dim: int = 6, max_norm: float = 0.75
) -> np.ndarray:
    """Sample a deterministic point well inside the Poincare ball."""
    direction = rng.normal(size=dim)
    direction /= np.linalg.norm(direction) + 1e-12
    radius = rng.uniform(0.05, max_norm)
    return direction * radius


@pytest.mark.skipif(not SCBE_AVAILABLE, reason="SCBE modules not available")
class TestLegacyFormalAxioms123:
    """FA1-FA3 on the legacy H(d,R)=R^(d^2) wall law."""

    def test_axiom1_positivity_of_cost(self):
        distances = np.linspace(0.0, 3.0, 25)
        values = [legacy_harmonic_scaling(float(d), R=1.5)[0] for d in distances]

        assert values[0] == pytest.approx(1.0)
        assert all(value > 0.0 for value in values)
        assert all(value > 1.0 for value in values[1:])

    def test_axiom2_monotonicity_of_deviation(self):
        distances = np.linspace(0.0, 3.0, 25)
        values = [legacy_harmonic_scaling(float(d), R=1.5)[0] for d in distances]

        assert all(left < right for left, right in zip(values, values[1:]))

    def test_axiom3_convexity_of_cost_surface(self):
        distances = np.linspace(0.0, 2.5, 51)
        step = distances[1] - distances[0]
        values = np.array(
            [legacy_harmonic_scaling(float(d), R=1.5)[0] for d in distances]
        )
        second_difference = (values[2:] - 2.0 * values[1:-1] + values[:-2]) / (step**2)

        assert np.all(
            second_difference > 0.0
        ), "Legacy harmonic wall should remain strictly convex"


@pytest.mark.skipif(not SCBE_AVAILABLE, reason="SCBE modules not available")
class TestReferenceFormalAxioms:
    """FA4/FA7/FA9/FA10/FA12 on the live reference pipeline."""

    def test_axiom4_bounded_temporal_breathing(self):
        rng = np.random.default_rng(7)

        for _ in range(24):
            u = _ball_point(rng, dim=8, max_norm=0.7)
            original_norm = np.linalg.norm(u)

            contracted = layer_6_breathing_transform(u, 0.5)
            identity = layer_6_breathing_transform(u, 1.0)
            expanded = layer_6_breathing_transform(u, 2.0)

            contracted_norm = np.linalg.norm(contracted)
            identity_norm = np.linalg.norm(identity)
            expanded_norm = np.linalg.norm(expanded)

            assert contracted_norm < original_norm
            assert identity_norm == pytest.approx(original_norm, rel=1e-9, abs=1e-9)
            assert original_norm < expanded_norm < 1.0

    def test_axiom7_harmonic_resonance_spin_coherence(self):
        aligned = np.zeros(8)
        opposed = np.array([0.0, np.pi] * 4)
        quarter_cycle = np.array([0.0, np.pi / 2.0, np.pi, 3.0 * np.pi / 2.0])

        assert layer_10_spin_coherence(aligned) == pytest.approx(1.0)
        assert layer_10_spin_coherence(opposed) == pytest.approx(0.0, abs=1e-12)
        assert layer_10_spin_coherence(quarter_cycle) == pytest.approx(0.0, abs=1e-12)

        rng = np.random.default_rng(11)
        random_score = layer_10_spin_coherence(rng.uniform(-np.pi, np.pi, 32))
        assert 0.0 <= random_score <= 1.0

    def test_axiom9_hyperbolic_geometry_metric_axioms(self):
        rng = np.random.default_rng(13)

        for _ in range(20):
            u = _ball_point(rng)
            v = _ball_point(rng)
            w = _ball_point(rng)

            d_uu = layer_5_hyperbolic_distance(u, u)
            d_uv = layer_5_hyperbolic_distance(u, v)
            d_vu = layer_5_hyperbolic_distance(v, u)
            d_uw = layer_5_hyperbolic_distance(u, w)
            d_vw = layer_5_hyperbolic_distance(v, w)

            assert d_uu == pytest.approx(0.0, abs=1e-12)
            assert d_uv >= 0.0
            assert d_uv == pytest.approx(d_vu, rel=1e-12, abs=1e-12)
            assert d_uw <= d_uv + d_vw + 1e-9

    def test_axiom10_golden_ratio_weighting_progression(self):
        basis_dimension = 12
        energies = []

        for idx in range(basis_dimension):
            basis = np.zeros(basis_dimension)
            basis[idx] = 1.0
            transformed = layer_3_weighted_transform(basis)
            energies.append(float(np.dot(transformed, transformed)))

        first_half = energies[:6]
        second_half = energies[6:]
        ratios = [right / left for left, right in zip(first_half, first_half[1:])]

        for left, right in zip(first_half, second_half):
            assert left == pytest.approx(right, rel=1e-12, abs=1e-12)

        assert all(value > 0.0 for value in first_half)
        for ratio in ratios:
            assert ratio == pytest.approx(1.618, rel=1e-9, abs=1e-9)

    def test_axiom12_topological_attack_detection_prefers_stable_spectra(self):
        t = np.linspace(0.0, 1.0, 512, endpoint=False)
        low_frequency_signal = np.sin(2.0 * np.pi * 3.0 * t)
        high_frequency_signal = np.array([1.0, -1.0] * 256, dtype=float)

        smooth_score = layer_9_spectral_coherence(low_frequency_signal)
        attack_like_score = layer_9_spectral_coherence(high_frequency_signal)

        assert 0.0 <= smooth_score <= 1.0
        assert 0.0 <= attack_like_score <= 1.0
        assert smooth_score > attack_like_score


@pytest.mark.skipif(not SCBE_AVAILABLE, reason="SCBE modules not available")
class TestReferenceLayer12Regression:
    """Regression coverage for the current bounded reference Layer 12 score."""

    def test_reference_layer12_score_is_bounded_and_monotone_in_distance(self):
        distances = np.linspace(0.0, 3.0, 25)
        values = [layer_12_harmonic_scaling(float(d), 0.0) for d in distances]

        assert values[0] == pytest.approx(1.0)
        assert all(0.0 < value <= 1.0 for value in values)
        assert all(left > right for left, right in zip(values, values[1:]))

    def test_reference_layer12_score_decreases_as_phase_deviation_rises(self):
        phase_deviations = np.linspace(0.0, 1.0, 25)
        values = [
            layer_12_harmonic_scaling(0.5, float(phase)) for phase in phase_deviations
        ]

        assert all(0.0 < value <= 1.0 for value in values)
        assert all(left > right for left, right in zip(values, values[1:]))
