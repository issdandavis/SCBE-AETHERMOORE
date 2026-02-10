"""
Tests for Dual Ternary Encoding with Full Negative State Flux
==============================================================

Covers:
- Full 9-state space enumeration and energy model
- Phase classification (constructive, destructive, neutral, negative_resonance)
- Encoding continuous values to dual ternary
- Spectral analysis (DFT, cross-correlation, 9-fold symmetry)
- Fractal dimension estimation (log(9)/log(3) base)
- Phase anomaly detection (Shannon entropy)
- DualTernarySystem lifecycle
- Tensor product representation
- Security anomaly detection (biased vs balanced sequences)

@module tests/test_dual_ternary_full_flux
"""

import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from symphonic_cipher.scbe_aethermoore.ai_brain.dual_ternary import (
    DualTernaryState,
    DualTernaryConfig,
    DualTernarySystem,
    FULL_STATE_SPACE,
    compute_state_energy,
    state_index,
    state_from_index,
    transition,
    encode_to_dual_ternary,
    encode_sequence,
    compute_spectrum,
    estimate_fractal_dimension,
)

PHI = (1 + math.sqrt(5)) / 2


# ---------------------------------------------------------------------------
# Full 9-State Space
# ---------------------------------------------------------------------------

class TestFullStateSpace:
    """Verify the complete 9-state dual ternary space."""

    def test_exactly_9_states(self):
        assert len(FULL_STATE_SPACE) == 9

    def test_all_combinations_present(self):
        pairs = {(s.primary, s.mirror) for s in FULL_STATE_SPACE}
        expected = {(p, m) for p in [-1, 0, 1] for m in [-1, 0, 1]}
        assert pairs == expected

    def test_state_index_bijection(self):
        indices = [state_index(s) for s in FULL_STATE_SPACE]
        assert sorted(indices) == list(range(9))

    def test_state_from_index_roundtrip(self):
        for i in range(9):
            s = state_from_index(i)
            assert state_index(s) == i

    def test_index_clamping(self):
        s_neg = state_from_index(-5)
        assert state_index(s_neg) == 0
        s_big = state_from_index(100)
        assert state_index(s_big) == 8


# ---------------------------------------------------------------------------
# State Energy Model
# ---------------------------------------------------------------------------

class TestStateEnergy:
    """Verify energy E(p,m) = p^2 + m^2 + p*m."""

    def test_ground_state_energy(self):
        e = compute_state_energy(DualTernaryState(0, 0))
        assert e.energy == 0
        assert e.phase == "neutral"

    def test_constructive_energy(self):
        e = compute_state_energy(DualTernaryState(1, 1))
        assert e.energy == 3
        assert e.phase == "constructive"

    def test_negative_resonance_energy(self):
        e = compute_state_energy(DualTernaryState(-1, -1))
        assert e.energy == 3
        assert e.phase == "negative_resonance"

    def test_destructive_energy(self):
        e1 = compute_state_energy(DualTernaryState(1, -1))
        assert e1.energy == 1
        assert e1.phase == "destructive"
        e2 = compute_state_energy(DualTernaryState(-1, 1))
        assert e2.energy == 1
        assert e2.phase == "destructive"

    def test_half_active_states(self):
        for p, m in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            e = compute_state_energy(DualTernaryState(p, m))
            assert e.energy == 1
            assert e.phase == "neutral"

    def test_energy_symmetry(self):
        """E(p,m) should equal E(-p,-m) — sign inversion preserves energy."""
        for s in FULL_STATE_SPACE:
            e1 = compute_state_energy(s)
            e2 = compute_state_energy(DualTernaryState(-s.primary, -s.mirror))
            assert e1.energy == e2.energy

    def test_all_energies_non_negative(self):
        for s in FULL_STATE_SPACE:
            e = compute_state_energy(s)
            assert e.energy >= 0


# ---------------------------------------------------------------------------
# Transitions
# ---------------------------------------------------------------------------

class TestTransitions:
    """State transitions stay within {-1, 0, 1}."""

    def test_identity_transition(self):
        s = DualTernaryState(1, -1)
        t = transition(s, 0, 0)
        assert t.primary == 1 and t.mirror == -1

    def test_clip_positive(self):
        s = DualTernaryState(1, 1)
        t = transition(s, 5, 5)
        assert t.primary == 1 and t.mirror == 1

    def test_clip_negative(self):
        s = DualTernaryState(-1, -1)
        t = transition(s, -5, -5)
        assert t.primary == -1 and t.mirror == -1

    def test_basic_step(self):
        s = DualTernaryState(0, 0)
        t = transition(s, 1, -1)
        assert t.primary == 1 and t.mirror == -1


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------

class TestEncoding:
    """Continuous -> dual ternary encoding."""

    def test_above_threshold(self):
        s = encode_to_dual_ternary(0.5, -0.5, threshold=0.33)
        assert s.primary == 1 and s.mirror == -1

    def test_below_threshold(self):
        s = encode_to_dual_ternary(0.1, -0.1, threshold=0.33)
        assert s.primary == 0 and s.mirror == 0

    def test_sequence_pairs(self):
        vals = [0.5, -0.5, 0.1, 0.8]
        seq = encode_sequence(vals, threshold=0.33)
        assert len(seq) == 2
        assert seq[0].primary == 1 and seq[0].mirror == -1
        assert seq[1].primary == 0 and seq[1].mirror == 1

    def test_sequence_odd_length(self):
        vals = [0.5, -0.5, 0.8]
        seq = encode_sequence(vals, threshold=0.33)
        assert len(seq) == 2
        assert seq[1].mirror == 0  # second element paired with 0

    def test_21d_encoding(self):
        """21D brain state -> 11 dual ternary states."""
        state = [0.5] * 21
        seq = encode_sequence(state, threshold=0.33)
        assert len(seq) == 11  # ceil(21/2)


# ---------------------------------------------------------------------------
# Spectral Analysis
# ---------------------------------------------------------------------------

class TestSpectralAnalysis:
    """DFT and phase anomaly detection."""

    def test_short_sequence_empty(self):
        sp = compute_spectrum([DualTernaryState(0, 0)] * 3)
        assert sp.primary_magnitudes == []
        assert sp.coherence == 0

    def test_uniform_low_phase_anomaly(self):
        """All 9 states equally represented -> low anomaly."""
        seq = FULL_STATE_SPACE * 10  # 90 elements, balanced
        sp = compute_spectrum(seq)
        assert sp.phase_anomaly < 0.15

    def test_biased_high_phase_anomaly(self):
        """All same state -> maximum anomaly."""
        seq = [DualTernaryState(1, 1)] * 50
        sp = compute_spectrum(seq)
        assert sp.phase_anomaly > 0.95

    def test_ninefold_energy_balanced(self):
        """Balanced distribution -> low ninefold energy."""
        seq = FULL_STATE_SPACE * 10
        sp = compute_spectrum(seq)
        assert sp.ninefold_energy < 0.1

    def test_ninefold_energy_biased(self):
        """All one state -> high ninefold energy."""
        seq = [DualTernaryState(1, 1)] * 50
        sp = compute_spectrum(seq)
        assert sp.ninefold_energy > 0.5

    def test_coherence_bounded(self):
        seq = FULL_STATE_SPACE * 5
        sp = compute_spectrum(seq)
        assert 0 <= sp.coherence <= 1

    def test_dft_lengths_power_of_2(self):
        seq = [DualTernaryState(1, 0)] * 10
        sp = compute_spectrum(seq)
        assert len(sp.primary_magnitudes) == 16  # next pow2 of 10


# ---------------------------------------------------------------------------
# Fractal Dimension
# ---------------------------------------------------------------------------

class TestFractalDimension:
    """Fractal dimension estimation: D = log(9)/log(3) + correction."""

    def test_base_dimension_is_2(self):
        seq = FULL_STATE_SPACE * 5
        fd = estimate_fractal_dimension(seq)
        assert abs(fd.base_dimension - 2.0) < 1e-10

    def test_short_sequence_default(self):
        fd = estimate_fractal_dimension([DualTernaryState(0, 0)] * 2)
        assert fd.hausdorff_dimension == fd.base_dimension

    def test_hausdorff_geq_base(self):
        """For balanced sequences, hausdorff >= base."""
        seq = FULL_STATE_SPACE * 20
        fd = estimate_fractal_dimension(seq)
        assert fd.hausdorff_dimension >= fd.base_dimension - 0.01

    def test_symmetry_breaking_zero_for_symmetric(self):
        """If primary and mirror distributions are identical, breaking ~ 0."""
        seq = [DualTernaryState(1, 1), DualTernaryState(-1, -1), DualTernaryState(0, 0)] * 20
        fd = estimate_fractal_dimension(seq)
        assert fd.symmetry_breaking < 0.05

    def test_symmetry_breaking_nonzero_for_asymmetric(self):
        """If primary is always +1 but mirror varies, breaking > 0."""
        seq = [DualTernaryState(1, -1), DualTernaryState(1, 0), DualTernaryState(1, 1)] * 20
        fd = estimate_fractal_dimension(seq)
        assert fd.symmetry_breaking > 0.1


# ---------------------------------------------------------------------------
# DualTernarySystem
# ---------------------------------------------------------------------------

class TestDualTernarySystem:
    """Full system lifecycle."""

    def test_encode_increments_step(self):
        sys = DualTernarySystem()
        sys.encode([0.5] * 21)
        sys.encode([0.5] * 21)
        assert sys.step == 2

    def test_history_grows(self):
        sys = DualTernarySystem()
        sys.encode([0.5] * 21)
        assert sys.history_length == 11

    def test_history_caps_at_1024(self):
        sys = DualTernarySystem()
        for _ in range(200):
            sys.encode([0.5] * 21)
        assert sys.history_length <= 1024

    def test_full_analysis_structure(self):
        sys = DualTernarySystem()
        for _ in range(5):
            sys.encode([0.5] * 21)
        result = sys.full_analysis()
        assert "spectrum" in result
        assert "fractal" in result
        assert "threat_score" in result
        assert 0 <= result["threat_score"] <= 1

    def test_reset_clears_state(self):
        sys = DualTernarySystem()
        sys.encode([0.5] * 21)
        sys.reset()
        assert sys.step == 0
        assert sys.history_length == 0

    def test_biased_input_high_threat(self):
        """All positive values -> biased encoding -> higher threat."""
        sys = DualTernarySystem()
        for _ in range(10):
            sys.encode([1.0] * 21)
        result = sys.full_analysis()
        assert result["phase_anomaly_detected"]
        assert result["threat_score"] > 0.3


# ---------------------------------------------------------------------------
# Tensor Product
# ---------------------------------------------------------------------------

class TestTensorProduct:
    """3x3 tensor product representation."""

    def test_single_state_tensor(self):
        t = DualTernarySystem.to_tensor_product(DualTernaryState(1, -1))
        assert t[2][0] == 1  # primary=1 -> row 2, mirror=-1 -> col 0
        total = sum(sum(row) for row in t)
        assert total == 1

    def test_histogram_sums_to_length(self):
        seq = FULL_STATE_SPACE * 3
        hist = DualTernarySystem.tensor_histogram(seq)
        total = sum(sum(row) for row in hist)
        assert total == 27

    def test_histogram_balanced(self):
        seq = FULL_STATE_SPACE * 10
        hist = DualTernarySystem.tensor_histogram(seq)
        for row in hist:
            for val in row:
                assert val == 10


# ---------------------------------------------------------------------------
# Security: Anomaly Detection
# ---------------------------------------------------------------------------

class TestAnomalyDetection:
    """Detect attack patterns via spectral analysis."""

    def test_normal_traffic_low_anomaly(self):
        """Balanced state distribution -> low anomaly."""
        sys = DualTernarySystem()
        # Encode diverse values
        import random
        rng = random.Random(42)
        for _ in range(20):
            vals = [rng.gauss(0, 0.5) for _ in range(21)]
            sys.encode(vals)
        result = sys.full_analysis()
        assert result["threat_score"] < 0.7

    def test_attack_traffic_high_anomaly(self):
        """All max-positive -> highly biased -> high anomaly."""
        sys = DualTernarySystem()
        for _ in range(20):
            sys.encode([5.0] * 21)
        result = sys.full_analysis()
        assert result["phase_anomaly_detected"]
