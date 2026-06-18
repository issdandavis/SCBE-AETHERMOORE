"""Locks for first-class chemistry dimensional analysis."""

from __future__ import annotations

import pytest

from python.scbe.chemistry_dimensions import (
    ChemistryDimensionError,
    analyze_formula,
    analyze_many,
)


def test_glucose_subatomic_ledger_is_dimensionally_accounted():
    row = analyze_formula("C6H12O6")

    assert row["schema_version"] == "scbe_chemistry_dimensions_v1"
    assert row["atoms"]["C"]["count"] == 6
    assert row["atoms"]["H"]["count"] == 12
    assert row["atoms"]["O"]["count"] == 6
    assert row["totals"]["atoms"] == 24
    assert row["totals"]["protons"] == 96
    assert row["totals"]["neutrons_common_isotope"] == 84
    assert row["totals"]["electrons"] == 96
    assert row["totals"]["mass_number_common_isotope"] == 180
    assert row["totals"]["molar_mass_g_mol"] == pytest.approx(180.156)
    assert any("formula-level" in line for line in row["claim_boundary"])


def test_charge_changes_electron_count_not_protons():
    ammonium = analyze_formula("NH4^+")

    assert ammonium["totals"]["charge"] == 1
    assert ammonium["totals"]["protons"] == 11
    assert ammonium["totals"]["electrons"] == 10
    assert ammonium["totals"]["neutrons_common_isotope"] == 7


def test_nested_formula_reuses_reaction_parser():
    row = analyze_formula("Ca(OH)2")

    assert row["atoms"]["Ca"]["count"] == 1
    assert row["atoms"]["O"]["count"] == 2
    assert row["atoms"]["H"]["count"] == 2
    assert row["totals"]["protons"] == 38


def test_batch_analysis_combines_ledgers():
    batch = analyze_many(["H2", "O2"])

    assert batch["combined_totals"]["atoms"] == 4
    assert batch["combined_totals"]["protons"] == 18
    assert batch["combined_totals"]["electrons"] == 18


def test_unknown_element_fails_cleanly():
    with pytest.raises(ChemistryDimensionError, match="not in the local chemistry dimension table"):
        analyze_formula("Uuo")
