"""
Tests for src/governance/chemical_bonds.py
==========================================

Covers:
- Constants (TONGUES, BOND_PAIRS, BOND_NAMES)
- BondState dataclass
- TongueMolecule: bonds, total_energy, stability, broken_count, broken_bonds
- Fuzzy membership functions (safe, cautious, suspicious, hostile)
- Dominant class classification
- MoleculeReport
- batch_analyze
- Edge cases: extreme values, uniform coords, zero coords
"""

import sys
import math
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from governance.chemical_bonds import (
    TONGUES,
    BOND_PAIRS,
    BOND_NAMES,
    BondState,
    MoleculeReport,
    TongueMolecule,
    batch_analyze,
)

# ============================================================
# Constants
# ============================================================


@pytest.mark.unit
class TestConstants:
    def test_tongues_count(self):
        assert len(TONGUES) == 6

    def test_tongues_order(self):
        assert TONGUES == ("KO", "AV", "RU", "CA", "UM", "DR")

    def test_bond_pairs_count(self):
        assert len(BOND_PAIRS) == 3

    def test_bond_pairs_are_perpendicular(self):
        """KO-RU, CA-UM, AV-DR are the 3 perpendicular pairs."""
        assert ("KO", "RU") in BOND_PAIRS
        assert ("CA", "UM") in BOND_PAIRS
        assert ("AV", "DR") in BOND_PAIRS

    def test_bond_names_match_pairs(self):
        assert len(BOND_NAMES) == len(BOND_PAIRS)
        assert BOND_NAMES[0] == "sigma_KO_RU"
        assert BOND_NAMES[1] == "pi_CA_UM"
        assert BOND_NAMES[2] == "delta_AV_DR"


# ============================================================
# TongueMolecule construction
# ============================================================


@pytest.mark.unit
class TestTongueMoleculeConstruction:
    def test_requires_6_coords(self):
        with pytest.raises(ValueError, match="Expected 6"):
            TongueMolecule([0.5, 0.5])

    def test_requires_exactly_6(self):
        with pytest.raises(ValueError):
            TongueMolecule([0.5] * 7)

    def test_accepts_6_coords(self):
        mol = TongueMolecule([0.5] * 6)
        assert mol.coords == [0.5] * 6

    def test_default_reference(self):
        mol = TongueMolecule([0.5] * 6)
        assert mol.reference == [0.5] * 6

    def test_custom_reference(self):
        mol = TongueMolecule([0.5] * 6, reference=[0.3] * 6)
        assert mol.reference == [0.3] * 6


# ============================================================
# Bond computation
# ============================================================


@pytest.mark.unit
class TestBonds:
    def test_three_bonds(self):
        mol = TongueMolecule([0.5] * 6)
        assert len(mol.bonds) == 3

    def test_bond_names(self):
        mol = TongueMolecule([0.5] * 6)
        names = [b.name for b in mol.bonds]
        assert names == BOND_NAMES

    def test_bond_state_has_fields(self):
        mol = TongueMolecule([0.5] * 6)
        bond = mol.bonds[0]
        assert isinstance(bond, BondState)
        assert hasattr(bond, "z")
        assert hasattr(bond, "energy")
        assert hasattr(bond, "angle_deg")
        assert hasattr(bond, "dissociation")
        assert hasattr(bond, "broken")

    def test_uniform_coords_no_broken_bonds(self):
        """At reference coords (all 0.5), no bonds should be broken."""
        mol = TongueMolecule([0.5] * 6)
        assert mol.broken_count == 0

    def test_bond_z_complex(self):
        mol = TongueMolecule([0.9, 0.1, 0.7, 0.4, 0.9, 0.2])
        for bond in mol.bonds:
            assert isinstance(bond.z, complex)

    def test_bond_energy_nonnegative(self):
        mol = TongueMolecule([0.9, 0.1, 0.7, 0.4, 0.9, 0.2])
        for bond in mol.bonds:
            assert bond.energy >= 0.0

    def test_sigma_bond_complex_value(self):
        """sigma KO-RU: real = (KO+RU)/2, imag = KO-RU."""
        coords = [0.9, 0.0, 0.3, 0.0, 0.0, 0.0]
        mol = TongueMolecule(coords)
        sigma = mol.bonds[0]
        expected_real = (0.9 + 0.3) / 2.0
        expected_imag = 0.9 - 0.3
        assert abs(sigma.z.real - expected_real) < 1e-10
        assert abs(sigma.z.imag - expected_imag) < 1e-10

    def test_broken_bond_threshold(self):
        """Bond breaks when shift from reference > 0.3."""
        # Reference is [0.5]*6. Set KO far from reference.
        mol = TongueMolecule([1.0, 0.5, 0.5, 0.5, 0.5, 0.5])
        sigma = mol.bonds[0]  # KO-RU bond
        # KO shifted by 0.5 from ref, RU unchanged
        # z_ref = (0.5+0.5)/2 + j*(0.5-0.5) = 0.5+0j
        # z = (1.0+0.5)/2 + j*(1.0-0.5) = 0.75+0.5j
        # shift = |0.75+0.5j - 0.5+0j| = |0.25+0.5j| ≈ 0.559 > 0.3
        assert sigma.broken is True

    def test_not_broken_when_close_to_reference(self):
        mol = TongueMolecule([0.55, 0.5, 0.55, 0.5, 0.5, 0.5])
        assert mol.broken_count == 0


# ============================================================
# Energy, stability, broken
# ============================================================


@pytest.mark.unit
class TestEnergyStability:
    def test_total_energy_nonnegative(self):
        mol = TongueMolecule([0.9, 0.1, 0.7, 0.4, 0.9, 0.2])
        assert mol.total_energy >= 0.0

    def test_total_energy_is_sum_of_bonds(self):
        mol = TongueMolecule([0.9, 0.1, 0.7, 0.4, 0.9, 0.2])
        expected = sum(b.energy for b in mol.bonds)
        assert abs(mol.total_energy - expected) < 1e-10

    def test_stability_bounded_0_1(self):
        mol = TongueMolecule([0.9, 0.1, 0.7, 0.4, 0.9, 0.2])
        assert 0.0 <= mol.stability <= 1.0

    def test_uniform_coords_high_stability(self):
        mol = TongueMolecule([0.5] * 6)
        # All bonds should have similar angles
        assert mol.stability > 0.5

    def test_broken_bonds_list(self):
        mol = TongueMolecule([1.0, 0.5, 0.0, 0.5, 0.5, 0.5])
        broken = mol.broken_bonds
        assert isinstance(broken, list)
        for name in broken:
            assert name in BOND_NAMES

    def test_zero_coords_energy(self):
        mol = TongueMolecule([0.0] * 6)
        assert mol.total_energy == 0.0


# ============================================================
# Fuzzy membership
# ============================================================


@pytest.mark.unit
class TestFuzzyMembership:
    def test_fuzzy_safe_high_for_low_energy(self):
        # Energy near 0.3 should give high safe membership
        mol = TongueMolecule([0.0] * 6)  # zero energy
        # fuzzy_safe peaks at energy=0.3
        # zero energy: _fuzzy(0, 0.3, 0.15) = exp(-0.09/0.045) = exp(-2) ≈ 0.135
        assert mol.fuzzy_safe > 0.0

    def test_fuzzy_values_nonnegative(self):
        mol = TongueMolecule([0.5] * 6)
        assert mol.fuzzy_safe >= 0.0
        assert mol.fuzzy_cautious >= 0.0
        assert mol.fuzzy_suspicious >= 0.0
        assert mol.fuzzy_hostile >= 0.0

    def test_fuzzy_gaussian_shape(self):
        """Fuzzy function is Gaussian: value at center should be 1.0."""
        mol = TongueMolecule([0.5] * 6)
        # _fuzzy(value, center, width) = exp(-(value-center)^2 / (2*width^2))
        # At center: exp(0) = 1.0
        assert TongueMolecule._fuzzy(0.3, 0.3, 0.15) == 1.0
        assert TongueMolecule._fuzzy(0.6, 0.6, 0.15) == 1.0

    def test_fuzzy_decays_away_from_center(self):
        v1 = TongueMolecule._fuzzy(0.3, 0.3, 0.15)
        v2 = TongueMolecule._fuzzy(0.5, 0.3, 0.15)
        assert v2 < v1


# ============================================================
# Dominant class
# ============================================================


@pytest.mark.unit
class TestDominantClass:
    def test_returns_string(self):
        mol = TongueMolecule([0.5] * 6)
        assert mol.dominant_class in ("SAFE", "CAUTIOUS", "SUSPICIOUS", "HOSTILE")

    def test_zero_energy_leans_safe(self):
        mol = TongueMolecule([0.0] * 6)
        # Energy=0, closest peak is SAFE at 0.3
        assert mol.dominant_class == "SAFE"

    def test_high_energy_leans_hostile(self):
        # All coords at 1.0, energy = sum of |z|^2 for 3 bonds
        # Each bond: real=(1+1)/2=1, imag=1-1=0, |z|^2=1.0
        # total_energy = 3.0, closest to hostile peak at 1.3
        mol = TongueMolecule([1.0] * 6)
        # With total_energy=3.0 and hostile center at 1.3, width 0.20:
        # _fuzzy(3.0, 1.3, 0.2) = exp(-(1.7)^2/0.08) very small
        # Actually all fuzzy values will be very small for energy=3.0
        # but hostile should be least-small
        assert mol.dominant_class in ("SUSPICIOUS", "HOSTILE")


# ============================================================
# MoleculeReport
# ============================================================


@pytest.mark.unit
class TestMoleculeReport:
    def test_report_returns_dataclass(self):
        mol = TongueMolecule([0.5] * 6)
        report = mol.report()
        assert isinstance(report, MoleculeReport)

    def test_report_bonds_count(self):
        mol = TongueMolecule([0.5] * 6)
        report = mol.report()
        assert len(report.bonds) == 3

    def test_report_fuzzy_sums_to_one(self):
        mol = TongueMolecule([0.5] * 6)
        report = mol.report()
        total = report.fuzzy_safe + report.fuzzy_cautious + report.fuzzy_suspicious + report.fuzzy_hostile
        assert abs(total - 1.0) < 1e-10

    def test_report_cached(self):
        mol = TongueMolecule([0.5] * 6)
        r1 = mol.report()
        r2 = mol.report()
        assert r1 is r2

    def test_report_stability(self):
        mol = TongueMolecule([0.5] * 6)
        report = mol.report()
        assert 0.0 <= report.stability <= 1.0

    def test_report_dominant_class(self):
        mol = TongueMolecule([0.5] * 6)
        report = mol.report()
        assert report.dominant_class in ("SAFE", "CAUTIOUS", "SUSPICIOUS", "HOSTILE")


# ============================================================
# batch_analyze
# ============================================================


@pytest.mark.integration
class TestBatchAnalyze:
    def test_returns_list(self):
        coords_list = [[0.5] * 6, [0.9, 0.1, 0.9, 0.1, 0.9, 0.1]]
        results = batch_analyze(coords_list)
        assert isinstance(results, list)
        assert len(results) == 2

    def test_each_is_report(self):
        results = batch_analyze([[0.5] * 6])
        assert isinstance(results[0], MoleculeReport)

    def test_custom_reference(self):
        results = batch_analyze([[0.5] * 6], reference=[0.3] * 6)
        assert len(results) == 1

    def test_empty_list(self):
        results = batch_analyze([])
        assert results == []

    def test_batch_preserves_order(self):
        coords_list = [
            [0.0] * 6,  # low energy -> SAFE
            [0.5] * 6,  # mid energy
        ]
        results = batch_analyze(coords_list)
        assert results[0].total_energy < results[1].total_energy


# ============================================================
# Edge cases
# ============================================================


@pytest.mark.unit
class TestEdgeCases:
    def test_all_zero_coords(self):
        mol = TongueMolecule([0.0] * 6)
        assert mol.total_energy == 0.0
        assert mol.broken_count >= 0  # may or may not be broken
        report = mol.report()
        assert isinstance(report, MoleculeReport)

    def test_all_one_coords(self):
        mol = TongueMolecule([1.0] * 6)
        assert mol.total_energy > 0
        report = mol.report()
        assert isinstance(report, MoleculeReport)

    def test_negative_coords(self):
        mol = TongueMolecule([-0.5, -0.3, -0.1, -0.2, -0.4, -0.6])
        # Should not crash
        assert mol.total_energy >= 0.0
        report = mol.report()
        assert isinstance(report, MoleculeReport)

    def test_large_coords(self):
        mol = TongueMolecule([100.0] * 6)
        assert mol.total_energy > 0
        assert math.isfinite(mol.stability)

    def test_asymmetric_coords(self):
        mol = TongueMolecule([1.0, 0.0, 1.0, 0.0, 1.0, 0.0])
        assert mol.broken_count > 0  # significant deviation from reference
        broken = mol.broken_bonds
        assert len(broken) > 0

    def test_bond_angle_range(self):
        mol = TongueMolecule([0.9, 0.1, 0.7, 0.4, 0.9, 0.2])
        for bond in mol.bonds:
            assert -180.0 <= bond.angle_deg <= 180.0
