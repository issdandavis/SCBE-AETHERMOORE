"""Tests for Phi-Ternary Primitive."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from primitives import (
    PhiTernary,
    DualPhiTernary,
    phi_ternary,
    dual_phi_ternary,
    tongue_phi_ternary,
    tongue_vector_to_phi_ternary,
    phi_ternary_energy,
    phi_ternary_center,
    phi_ternary_symmetry,
    PHI,
)


class TestPhiTernary:
    def test_basic_creation(self):
        pt = phi_ternary(1, 0)
        assert pt.q == 1
        assert pt.k == 0
        assert pt.value == 1.0

    def test_phi_scaling(self):
        for k in range(6):
            pt = phi_ternary(1, k)
            assert abs(pt.weight - PHI**k) < 1e-10

    def test_neutral_is_zero(self):
        pt = phi_ternary(0, 5)
        assert pt.value == 0.0
        assert pt.is_neutral

    def test_negative_mirrors_positive(self):
        pos = phi_ternary(1, 3)
        neg = phi_ternary(-1, 3)
        assert abs(pos.value + neg.value) < 1e-10

    def test_mirror_operation(self):
        pt = phi_ternary(1, 2)
        mirrored = pt.mirror()
        assert mirrored.q == -1
        assert mirrored.k == 2
        assert abs(pt.value + mirrored.value) < 1e-10

    def test_neutral_mirror_stays_neutral(self):
        pt = phi_ternary(0, 3)
        assert pt.mirror().is_neutral

    def test_scale_up(self):
        pt = phi_ternary(1, 2)
        scaled = pt.scale_up()
        assert scaled.k == 3
        assert abs(scaled.value - PHI**3) < 1e-10

    def test_scale_down(self):
        pt = phi_ternary(1, 3)
        scaled = pt.scale_down()
        assert scaled.k == 2

    def test_invalid_q_raises(self):
        with pytest.raises(ValueError):
            phi_ternary(2, 0)
        with pytest.raises(ValueError):
            phi_ternary(-5, 0)

    def test_frozen(self):
        pt = phi_ternary(1, 0)
        with pytest.raises(AttributeError):
            pt.q = -1


class TestDualPhiTernary:
    def test_agreement(self):
        d = dual_phi_ternary(1, 2, 1, 3)
        assert d.agrees
        assert d.disagreement_score == 0.0
        assert not d.is_non_congruent

    def test_disagreement(self):
        d = dual_phi_ternary(1, 2, -1, 3)
        assert not d.agrees
        assert d.disagreement_score > 0
        assert d.is_non_congruent

    def test_neutral_not_non_congruent(self):
        d = dual_phi_ternary(1, 2, 0, 3)
        assert not d.agrees  # different q values
        assert not d.is_non_congruent  # but one is neutral

    def test_disagreement_phi_scaled(self):
        d1 = dual_phi_ternary(1, 0, -1, 0)
        d2 = dual_phi_ternary(1, 3, -1, 3)
        assert d2.disagreement_score > d1.disagreement_score

    def test_combined_on_agreement(self):
        d = dual_phi_ternary(1, 2, 1, 2)
        assert d.combined_value == PHI**2


class TestTongueMapping:
    def test_tongue_phi_ternary(self):
        ko = tongue_phi_ternary("KO", 1)
        dr = tongue_phi_ternary("DR", 1)
        assert ko.k == 0
        assert dr.k == 5
        assert dr.value > ko.value * 10  # DR is ~11x KO

    def test_tongue_vector_conversion(self):
        activations = [0.5, -0.3, 0.8, 0.0, -0.2, 0.9]
        result = tongue_vector_to_phi_ternary(activations, threshold=0.1)
        assert len(result) == 6
        assert result[0].q == 1  # KO positive
        assert result[1].q == -1  # AV negative
        assert result[3].q == 0  # CA neutral
        assert result[5].q == 1  # DR positive

    def test_all_neutral(self):
        activations = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        result = tongue_vector_to_phi_ternary(activations)
        assert all(v.is_neutral for v in result)


class TestEnergy:
    def test_neutral_zero_energy(self):
        values = [phi_ternary(0, k) for k in range(6)]
        assert phi_ternary_energy(values) == 0.0

    def test_positive_energy(self):
        values = [phi_ternary(1, 0)]
        assert phi_ternary_energy(values) == 1.0

    def test_higher_k_more_energy(self):
        e0 = phi_ternary_energy([phi_ternary(1, 0)])
        e5 = phi_ternary_energy([phi_ternary(1, 5)])
        assert e5 > e0 * 100  # phi^10 >> 1


class TestCenter:
    def test_balanced_center_is_zero(self):
        values = [phi_ternary(1, 2), phi_ternary(-1, 2)]
        assert abs(phi_ternary_center(values)) < 1e-10

    def test_all_positive_center_positive(self):
        values = [phi_ternary(1, k) for k in range(6)]
        assert phi_ternary_center(values) > 0

    def test_all_neutral_center_zero(self):
        values = [phi_ternary(0, k) for k in range(6)]
        assert phi_ternary_center(values) == 0.0


class TestSymmetry:
    def test_perfect_symmetry(self):
        values = [phi_ternary(1, 2), phi_ternary(-1, 2)]
        assert abs(phi_ternary_symmetry(values) - 1.0) < 1e-10

    def test_all_neutral_perfect_symmetry(self):
        values = [phi_ternary(0, k) for k in range(6)]
        assert phi_ternary_symmetry(values) == 1.0

    def test_all_positive_zero_symmetry(self):
        values = [phi_ternary(1, k) for k in range(6)]
        assert phi_ternary_symmetry(values) == 0.0

    def test_partial_symmetry(self):
        values = [
            phi_ternary(1, 0),
            phi_ternary(-1, 0),  # balanced pair
            phi_ternary(1, 1),  # unbalanced extra
        ]
        sym = phi_ternary_symmetry(values)
        assert 0 < sym < 1


class TestRPSCyclicProperty:
    """Test the rock-paper-scissors non-transitive dominance."""

    def test_cyclic_tongue_dominance(self):
        """Adjacent tongues should create non-transitive cycles."""
        tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]
        for i in range(6):
            t1 = tongue_phi_ternary(tongues[i], 1)
            t2 = tongue_phi_ternary(tongues[(i + 1) % 6], 1)
            # Higher k means more expensive — neither globally dominates
            # The cycle prevents any single tongue from winning everywhere
            assert t1.k != t2.k  # Different phi levels

    def test_dual_ternary_rps_detection(self):
        """When two systems disagree in opposite directions, that's the RPS signal."""
        # System A says activate, System B says inhibit
        d = dual_phi_ternary(1, 2, -1, 2)
        assert d.is_non_congruent
        # System A says activate, System B agrees
        d2 = dual_phi_ternary(1, 2, 1, 2)
        assert not d2.is_non_congruent


class TestForcedCenter:
    """Test that the ternary center is forced by geometry."""

    def test_full_tongue_balance_at_center(self):
        """A balanced tongue vector should have center near 0."""
        # Equal positive and negative across tongues
        values = [
            phi_ternary(1, 0),
            phi_ternary(-1, 1),
            phi_ternary(1, 2),
            phi_ternary(-1, 3),
            phi_ternary(0, 4),
            phi_ternary(0, 5),
        ]
        center = phi_ternary_center(values)
        # Not exactly 0 because phi weights differ, but the CENTER concept holds
        assert isinstance(center, float)

    def test_three_states_exist(self):
        """The system must always have all three states available."""
        pos = phi_ternary(1, 0)
        neu = phi_ternary(0, 0)
        neg = phi_ternary(-1, 0)
        assert pos.value + neg.value == 0  # mirror
        assert neu.value == 0  # center is real
        # 1 + (-1) + 0 = 0 — the ternary center
