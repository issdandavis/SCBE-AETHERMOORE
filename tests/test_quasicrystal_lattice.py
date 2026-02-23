"""
Tests for Icosahedral Quasicrystal Lattice Verification System.

Tests:
- Projection matrix orthogonality (icosahedral symmetry)
- Gate mapping and validation
- Phason rekeying invalidation
- Crystalline defect detection (periodic vs aperiodic inputs)
"""

import math
import sys
import os

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from symphonic_cipher.scbe_aethermoore.quasicrystal_lattice import (
    QuasicrystalLattice,
    LatticePoint,
    DefectAnalysis,
    PHI,
)


# =============================================================================
# PROJECTION MATRIX TESTS
# =============================================================================


class TestProjectionMatrices:
    """Test icosahedral projection basis matrices."""

    def test_matrix_shapes(self):
        """M_par and M_perp are 3x6."""
        qc = QuasicrystalLattice()
        assert qc.M_par.shape == (3, 6)
        assert qc.M_perp.shape == (3, 6)

    def test_orthogonality(self):
        """E_parallel and E_perp should be orthogonal subspaces.

        For each of the 6 basis columns, the dot product of the
        parallel and perpendicular projections should be near zero.
        """
        qc = QuasicrystalLattice()
        for i in range(6):
            dot = np.dot(qc.M_par[:, i], qc.M_perp[:, i])
            assert abs(dot) < 1e-10, f"Column {i} not orthogonal: dot={dot}"

    def test_normalisation(self):
        """Columns within each matrix should have consistent norms.

        E_par and E_perp have different norms due to Galois conjugation
        (PHI -> -1/PHI), which is correct for icosahedral QC.
        """
        qc = QuasicrystalLattice()
        # All par columns should have the same norm
        par_norms = [np.linalg.norm(qc.M_par[:, i]) for i in range(6)]
        for n in par_norms:
            assert abs(n - par_norms[0]) < 1e-10

        # All perp columns should have the same norm
        perp_norms = [np.linalg.norm(qc.M_perp[:, i]) for i in range(6)]
        for n in perp_norms:
            assert abs(n - perp_norms[0]) < 1e-10


# =============================================================================
# GATE MAPPING TESTS
# =============================================================================


class TestGateMapping:
    """Test 6D gate → quasicrystal mapping."""

    def test_small_gates_valid(self):
        """Small gate inputs should be valid (within acceptance window)."""
        qc = QuasicrystalLattice()
        # Small integer gates produce perp distances well within radius
        result = qc.map_gates_to_lattice([1, 1, 1, 1, 1, 1])

        assert isinstance(result, LatticePoint)
        assert result.r_physical.shape == (3,)
        assert result.r_perpendicular.shape == (3,)
        assert result.is_valid is True

    def test_large_gates_rejected(self):
        """Large gate values project far from acceptance window."""
        qc = QuasicrystalLattice()
        result = qc.map_gates_to_lattice([1, 2, 3, 5, 8, 13])
        # Large Fibonacci values push the perp projection outside
        assert result.perp_distance > qc.acceptance_radius

    def test_zero_gates(self):
        """All-zero gates should project to origin (always valid)."""
        qc = QuasicrystalLattice()
        result = qc.map_gates_to_lattice([0, 0, 0, 0, 0, 0])

        np.testing.assert_allclose(result.r_physical, [0, 0, 0], atol=1e-12)
        np.testing.assert_allclose(result.r_perpendicular, [0, 0, 0], atol=1e-12)
        assert result.perp_distance == 0.0
        assert result.is_valid is True

    def test_gate_vector_length_check(self):
        """Reject non-6D gate vectors."""
        qc = QuasicrystalLattice()
        with pytest.raises(ValueError, match="6 elements"):
            qc.map_gates_to_lattice([1, 2, 3])

    def test_different_gates_different_projections(self):
        """Different gate inputs produce different projections."""
        qc = QuasicrystalLattice()
        r1 = qc.map_gates_to_lattice([1, 0, 0, 0, 0, 0])
        r2 = qc.map_gates_to_lattice([0, 1, 0, 0, 0, 0])

        assert not np.allclose(r1.r_physical, r2.r_physical)

    def test_linearity(self):
        """Projection should be linear: map(a+b) = map(a) + map(b)."""
        qc = QuasicrystalLattice()
        a = [1, 2, 3, 0, 0, 0]
        b = [0, 0, 0, 5, 8, 13]
        ab = [1, 2, 3, 5, 8, 13]

        ra = qc.map_gates_to_lattice(a)
        rb = qc.map_gates_to_lattice(b)
        rab = qc.map_gates_to_lattice(ab)

        np.testing.assert_allclose(
            rab.r_physical, ra.r_physical + rb.r_physical, atol=1e-10
        )


# =============================================================================
# PHASON REKEYING TESTS
# =============================================================================


class TestPhasonRekey:
    """Test phason strain rekeying mechanism."""

    def test_rekey_changes_strain(self):
        """Rekeying moves the phason strain vector."""
        qc = QuasicrystalLattice()
        assert np.linalg.norm(qc.phason_strain) == 0.0

        new_strain = qc.apply_phason_rekey(b"entropy_seed_1")
        assert np.linalg.norm(new_strain) > 0

    def test_rekey_deterministic(self):
        """Same seed always produces the same phason strain."""
        qc1 = QuasicrystalLattice()
        qc2 = QuasicrystalLattice()

        s1 = qc1.apply_phason_rekey(b"same_seed")
        s2 = qc2.apply_phason_rekey(b"same_seed")

        np.testing.assert_array_equal(s1, s2)

    def test_different_seeds_different_strains(self):
        """Different seeds produce different phason strains."""
        qc = QuasicrystalLattice()

        s1 = qc.apply_phason_rekey(b"seed_alpha")
        s2 = qc.apply_phason_rekey(b"seed_beta")

        assert not np.allclose(s1, s2)

    def test_rekey_invalidates_previously_valid_point(self):
        """A point valid before rekeying should become invalid after."""
        qc = QuasicrystalLattice()

        # Use a small gate vector that is initially valid
        gates = [1, 1, 1, 0, 0, 0]
        before = qc.map_gates_to_lattice(gates)
        assert before.is_valid is True

        # Apply phason shift (2× acceptance_radius magnitude)
        qc.apply_phason_rekey(b"rekey_invalidation_test")

        after = qc.map_gates_to_lattice(gates)
        # The phason shift changes the effective distance
        assert after.perp_distance != before.perp_distance
        # With a 2× radius shift, the small valid point should now be invalid
        assert after.is_valid is False

    def test_physical_space_unchanged_after_rekey(self):
        """Phason shift only affects E_perp, not E_parallel."""
        qc = QuasicrystalLattice()
        gates = [1, 2, 3, 5, 8, 13]

        before = qc.map_gates_to_lattice(gates)
        qc.apply_phason_rekey(b"some_entropy")
        after = qc.map_gates_to_lattice(gates)

        # Physical-space projection is unchanged
        np.testing.assert_array_equal(before.r_physical, after.r_physical)
        # Perpendicular-space RAW projection is unchanged
        np.testing.assert_array_equal(
            before.r_perpendicular, after.r_perpendicular
        )
        # But the distance (from shifted window) changed
        assert before.perp_distance != after.perp_distance


# =============================================================================
# CRYSTALLINE DEFECT DETECTION TESTS
# =============================================================================


class TestDefectDetection:
    """Test FFT-based crystalline defect detection."""

    def test_insufficient_samples(self):
        """Too few samples returns zero score."""
        qc = QuasicrystalLattice()
        result = qc.detect_crystalline_defects([[1, 2, 3, 4, 5, 6]] * 10)

        assert isinstance(result, DefectAnalysis)
        assert result.score == 0.0
        assert result.sample_count == 10

    def test_defect_score_in_range(self):
        """Defect score must be in [0, 1] for any input."""
        qc = QuasicrystalLattice()
        rng = np.random.default_rng(42)
        history = [rng.integers(0, 100, size=6).tolist() for _ in range(64)]

        result = qc.detect_crystalline_defects(history)
        assert 0.0 <= result.score <= 1.0
        assert result.sample_count == 64

    def test_periodic_input_detected(self):
        """Clearly periodic inputs should produce a non-zero defect score."""
        qc = QuasicrystalLattice()

        # Repeating pattern with period 4
        pattern = [
            [10, 20, 30, 40, 50, 60],
            [11, 21, 31, 41, 51, 61],
            [12, 22, 32, 42, 52, 62],
            [13, 23, 33, 43, 53, 63],
        ]
        history = pattern * 8  # 32 samples

        result = qc.detect_crystalline_defects(history)
        assert result.sample_count == 32
        assert result.dominant_power_ratio > 0

    def test_constant_input_no_crash(self):
        """Constant input (all same vector) should not crash."""
        qc = QuasicrystalLattice()
        history = [[5, 5, 5, 5, 5, 5]] * 32

        result = qc.detect_crystalline_defects(history)
        assert 0.0 <= result.score <= 1.0


# =============================================================================
# STATUS / DIAGNOSTICS
# =============================================================================


class TestDiagnostics:
    """Test diagnostic output."""

    def test_get_status(self):
        """Status dict contains expected keys."""
        qc = QuasicrystalLattice()
        status = qc.get_status()

        assert status["lattice_constant"] == 1.0
        assert status["acceptance_radius"] == 1.5
        assert status["phason_norm"] == 0.0
        assert status["projection_shape_par"] == [3, 6]
        assert status["projection_shape_perp"] == [3, 6]
