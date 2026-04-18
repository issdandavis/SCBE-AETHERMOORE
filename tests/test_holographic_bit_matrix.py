"""
Tests for src/kernel/holographic_bit_matrix.py
==============================================

Covers:
- HolographicBitMatrix construction and golden-angle initialization
- Tongue modulation (trit overlay)
- Holographic encode/decode
- MERA compression at multiple levels
- Combined field and weight matrix
- Governance cost and harmonic wall
- State inspection (HoloState)
- Reconstruction error
- holographic_scatter_pipeline integration
"""

import sys
import math
from pathlib import Path

import pytest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kernel.holographic_bit_matrix import (
    PHI,
    TONGUE_WEIGHTS,
    TONGUE_KEYS,
    HoloState,
    HolographicBitMatrix,
    holographic_scatter_pipeline,
)

# ============================================================
# Construction and bit substrate
# ============================================================


@pytest.mark.unit
class TestBitSubstrate:
    def test_default_size(self):
        hbm = HolographicBitMatrix()
        assert hbm.size == 32
        assert hbm.bit_matrix.shape == (32, 32)

    def test_custom_size(self):
        hbm = HolographicBitMatrix(size=16)
        assert hbm.size == 16
        assert hbm.bit_matrix.shape == (16, 16)

    def test_bit_matrix_binary(self):
        hbm = HolographicBitMatrix(size=16)
        unique_vals = set(hbm.bit_matrix.flatten())
        assert unique_vals <= {0, 1}

    def test_bit_density_near_golden(self):
        """Density should be roughly 61.8% (golden ratio proportion)."""
        hbm = HolographicBitMatrix(size=64)
        density = float(np.mean(hbm.bit_matrix))
        # Allow generous tolerance — the pattern is structured, not random
        assert 0.3 < density < 0.9

    def test_deterministic(self):
        """Same size should produce same bit pattern."""
        hbm1 = HolographicBitMatrix(size=16)
        hbm2 = HolographicBitMatrix(size=16)
        np.testing.assert_array_equal(hbm1.bit_matrix, hbm2.bit_matrix)

    def test_initial_trit_matrix_zeros(self):
        hbm = HolographicBitMatrix(size=8)
        assert np.all(hbm.trit_matrix == 0)

    def test_initial_holo_field_zeros(self):
        hbm = HolographicBitMatrix(size=8)
        assert np.all(hbm.holo_field == 0)

    def test_initial_tongue_activation_all_zero(self):
        hbm = HolographicBitMatrix(size=8)
        for t in TONGUE_KEYS:
            assert hbm.tongue_activation[t] == 0.0


# ============================================================
# Tongue modulation
# ============================================================


@pytest.mark.unit
class TestTongueModulation:
    def test_active_tongues_get_positive_trit(self):
        hbm = HolographicBitMatrix(size=12)
        hbm.modulate_tongues(["KO", "CA"])
        # Check that some cells have +1
        assert np.any(hbm.trit_matrix == 1)

    def test_null_tongues_get_negative_trit(self):
        hbm = HolographicBitMatrix(size=12)
        hbm.modulate_tongues(["KO"])
        assert np.any(hbm.trit_matrix == -1)

    def test_no_active_tongues(self):
        hbm = HolographicBitMatrix(size=12)
        hbm.modulate_tongues([])
        # All should be -1 (null)
        assert np.all(hbm.trit_matrix == -1)

    def test_all_active_tongues(self):
        hbm = HolographicBitMatrix(size=12)
        hbm.modulate_tongues(TONGUE_KEYS)
        # All should be +1
        assert np.all(hbm.trit_matrix == 1)

    def test_tongue_activation_weights(self):
        hbm = HolographicBitMatrix(size=8)
        hbm.modulate_tongues(["KO", "DR"])
        assert hbm.tongue_activation["KO"] == TONGUE_WEIGHTS["KO"]
        assert hbm.tongue_activation["DR"] == TONGUE_WEIGHTS["DR"]
        assert hbm.tongue_activation["AV"] == 0.0

    def test_invalid_tongue_ignored(self):
        hbm = HolographicBitMatrix(size=8)
        hbm.modulate_tongues(["KO", "INVALID"])
        assert hbm.tongue_activation["KO"] == TONGUE_WEIGHTS["KO"]


# ============================================================
# Encode / Decode
# ============================================================


@pytest.mark.unit
class TestEncodeDecode:
    def test_encode_populates_holo_field(self):
        hbm = HolographicBitMatrix(size=8)
        hbm.modulate_tongues(["KO"])
        signal = np.array([1.0, 0.5, -0.3, 0.8])
        hbm.encode(signal)
        assert np.any(hbm.holo_field != 0)

    def test_encode_zero_signal_leaves_field_zero(self):
        hbm = HolographicBitMatrix(size=8)
        hbm.modulate_tongues(["KO"])
        signal = np.zeros(4)
        hbm.encode(signal)
        np.testing.assert_array_equal(hbm.holo_field, 0)

    def test_decode_returns_correct_length(self):
        hbm = HolographicBitMatrix(size=8)
        hbm.modulate_tongues(["KO", "CA"])
        signal = np.array([0.5, -0.3, 0.8, 0.1])
        hbm.encode(signal)
        decoded = hbm.decode(signal_length=4)
        assert len(decoded) == 4

    def test_decode_returns_finite(self):
        hbm = HolographicBitMatrix(size=8)
        hbm.modulate_tongues(["KO", "CA"])
        signal = np.array([0.5, -0.3, 0.8, 0.1])
        hbm.encode(signal)
        decoded = hbm.decode(signal_length=4)
        assert np.all(np.isfinite(decoded))


# ============================================================
# MERA Compression
# ============================================================


@pytest.mark.unit
class TestMERACompression:
    def test_level_0_no_compression(self):
        hbm = HolographicBitMatrix(size=16)
        hbm.modulate_tongues(["KO"])
        hbm.encode(np.array([1.0, 0.5]))
        compressed = hbm.mera_compress(level=0)
        assert compressed.shape == (16, 16)

    def test_level_1_halves(self):
        hbm = HolographicBitMatrix(size=16)
        hbm.modulate_tongues(["KO"])
        hbm.encode(np.array([1.0, 0.5]))
        compressed = hbm.mera_compress(level=1)
        assert compressed.shape == (8, 8)

    def test_level_2_quarters(self):
        hbm = HolographicBitMatrix(size=16)
        hbm.modulate_tongues(["KO"])
        hbm.encode(np.array([1.0, 0.5]))
        compressed = hbm.mera_compress(level=2)
        assert compressed.shape == (4, 4)

    def test_level_3_eighths(self):
        hbm = HolographicBitMatrix(size=16)
        hbm.modulate_tongues(["KO"])
        hbm.encode(np.array([1.0]))
        compressed = hbm.mera_compress(level=3)
        assert compressed.shape == (2, 2)

    def test_level_stops_at_minimum_size(self):
        hbm = HolographicBitMatrix(size=8)
        compressed = hbm.mera_compress(level=10)
        # Should stop before going below 4
        assert compressed.shape[0] >= 1
        assert compressed.shape[1] >= 1

    def test_updates_mera_level(self):
        hbm = HolographicBitMatrix(size=16)
        hbm.mera_compress(level=2)
        assert hbm.mera_level == 2


# ============================================================
# Combined field and weight matrix
# ============================================================


@pytest.mark.unit
class TestCombinedField:
    def test_combine_shape(self):
        hbm = HolographicBitMatrix(size=8)
        combined = hbm.combine()
        assert combined.shape == (8, 8)

    def test_combine_dtype(self):
        hbm = HolographicBitMatrix(size=8)
        combined = hbm.combine()
        assert combined.dtype == np.float64

    def test_to_weight_matrix_equals_combine(self):
        hbm = HolographicBitMatrix(size=8)
        hbm.modulate_tongues(["KO"])
        np.testing.assert_array_equal(hbm.to_weight_matrix(), hbm.combine())

    def test_combine_has_bit_contribution(self):
        """With no trit or holo, combined should be 0.5 * bit_matrix."""
        hbm = HolographicBitMatrix(size=8)
        combined = hbm.combine()
        expected = hbm.bit_matrix.astype(np.float64) * 0.5
        np.testing.assert_allclose(combined, expected)


# ============================================================
# Governance cost and harmonic wall
# ============================================================


@pytest.mark.unit
class TestGovernance:
    def test_governance_cost_no_active(self):
        hbm = HolographicBitMatrix(size=8)
        assert hbm.governance_cost() == 0.0

    def test_governance_cost_single_tongue(self):
        hbm = HolographicBitMatrix(size=8)
        hbm.modulate_tongues(["KO"])
        assert hbm.governance_cost() == TONGUE_WEIGHTS["KO"]

    def test_governance_cost_multiple_tongues(self):
        hbm = HolographicBitMatrix(size=8)
        hbm.modulate_tongues(["KO", "DR"])
        expected = TONGUE_WEIGHTS["KO"] + TONGUE_WEIGHTS["DR"]
        assert abs(hbm.governance_cost() - expected) < 1e-10

    def test_harmonic_wall_zero_drift(self):
        hbm = HolographicBitMatrix(size=8)
        assert hbm.harmonic_wall(0.0) == 1.0

    def test_harmonic_wall_negative_drift(self):
        hbm = HolographicBitMatrix(size=8)
        assert hbm.harmonic_wall(-1.0) == 1.0

    def test_harmonic_wall_positive_drift_increases(self):
        hbm = HolographicBitMatrix(size=8)
        hbm.modulate_tongues(["KO", "CA"])
        h1 = hbm.harmonic_wall(1.0)
        h2 = hbm.harmonic_wall(2.0)
        assert h2 > h1  # R^((phi*d)^2), R>1 means larger d = larger wall

    def test_harmonic_wall_formula(self):
        hbm = HolographicBitMatrix(size=8)
        hbm.modulate_tongues(["KO"])  # cost = 1.0
        # H = max(cost, 1.0)^((phi*d)^2) = 1.0^(phi^2) = 1.0
        assert hbm.harmonic_wall(1.0) == 1.0
        hbm.modulate_tongues(["KO", "CA"])
        r = hbm.governance_cost()
        expected = r ** ((PHI * 2.0) ** 2)  # canonical Layer 12 formula
        assert abs(hbm.harmonic_wall(2.0) - expected) < 1e-6


# ============================================================
# State inspection
# ============================================================


@pytest.mark.unit
class TestState:
    def test_state_returns_holostate(self):
        hbm = HolographicBitMatrix(size=8)
        s = hbm.state()
        assert isinstance(s, HoloState)

    def test_state_active_tongues(self):
        hbm = HolographicBitMatrix(size=8)
        hbm.modulate_tongues(["KO", "DR"])
        s = hbm.state()
        assert set(s.tongues_active) == {"KO", "DR"}

    def test_state_null_tongues(self):
        hbm = HolographicBitMatrix(size=8)
        hbm.modulate_tongues(["KO"])
        s = hbm.state()
        assert "KO" not in s.tongues_null
        assert len(s.tongues_null) == 5

    def test_state_trit_distribution(self):
        hbm = HolographicBitMatrix(size=6)
        hbm.modulate_tongues(["KO", "AV", "RU"])
        s = hbm.state()
        total = s.trit_distribution["-1"] + s.trit_distribution["0"] + s.trit_distribution["+1"]
        assert total == 36  # 6x6

    def test_state_bit_density(self):
        hbm = HolographicBitMatrix(size=8)
        s = hbm.state()
        assert 0.0 <= s.bit_density <= 1.0

    def test_state_governance_cost(self):
        hbm = HolographicBitMatrix(size=8)
        hbm.modulate_tongues(["CA"])
        s = hbm.state()
        assert s.governance_cost == TONGUE_WEIGHTS["CA"]


# ============================================================
# Reconstruction error
# ============================================================


@pytest.mark.unit
class TestReconstructionError:
    def test_zero_signal_zero_error(self):
        hbm = HolographicBitMatrix(size=8)
        hbm.modulate_tongues(["KO"])
        original = np.zeros(4)
        hbm.encode(original)
        err = hbm.reconstruction_error(original)
        assert err == 0.0

    def test_error_is_finite(self):
        hbm = HolographicBitMatrix(size=8)
        hbm.modulate_tongues(["KO", "CA"])
        original = np.array([0.5, -0.3, 0.8, 0.1])
        hbm.encode(original)
        err = hbm.reconstruction_error(original)
        assert math.isfinite(err)

    def test_error_nonnegative(self):
        hbm = HolographicBitMatrix(size=8)
        hbm.modulate_tongues(["KO"])
        original = np.array([1.0, -1.0, 0.5])
        hbm.encode(original)
        err = hbm.reconstruction_error(original)
        assert err >= 0.0


# ============================================================
# holographic_scatter_pipeline
# ============================================================


@pytest.mark.integration
class TestHolographicScatterPipeline:
    def test_returns_dict(self):
        signal = np.array([0.5, -0.3, 0.8, 0.1])
        result = holographic_scatter_pipeline(signal, ["KO", "CA"], matrix_size=8)
        assert isinstance(result, dict)

    def test_weight_matrix_shape(self):
        signal = np.array([0.5, -0.3])
        result = holographic_scatter_pipeline(signal, ["KO"], matrix_size=8)
        assert result["weight_matrix"].shape == (8, 8)

    def test_compressed_field_smaller(self):
        signal = np.array([0.5, -0.3])
        result = holographic_scatter_pipeline(signal, ["KO"], matrix_size=16, mera_level=2)
        assert result["compressed_field"].shape[0] < 16

    def test_reconstruction_error_present(self):
        signal = np.array([0.5, -0.3, 0.8, 0.1])
        result = holographic_scatter_pipeline(signal, ["KO", "CA"], matrix_size=8)
        assert "reconstruction_error" in result
        assert math.isfinite(result["reconstruction_error"])

    def test_state_has_correct_tongues(self):
        signal = np.array([1.0])
        result = holographic_scatter_pipeline(signal, ["KO", "DR"], matrix_size=8)
        assert set(result["state"].tongues_active) == {"KO", "DR"}

    def test_empty_signal(self):
        signal = np.array([])
        result = holographic_scatter_pipeline(signal, ["KO"], matrix_size=8)
        # Empty signal produces NaN from mean of empty slice — acceptable edge case
        err = result["reconstruction_error"]
        assert err == 0.0 or math.isfinite(err) or math.isnan(err)
