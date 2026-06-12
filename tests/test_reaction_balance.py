"""Regression locks for the exact reaction balancer (python/scbe/reaction_balance.py)."""

from __future__ import annotations

import pytest

from python.scbe.reaction_balance import (
    BalanceError,
    balance,
    balance_reaction_packet,
    format_equation,
    is_conserved,
    parse_formula,
)


def test_parse_formula_handles_groups_and_charge():
    counts, charge = parse_formula("Ca(OH)2")
    assert dict(counts) == {"Ca": 1, "O": 2, "H": 2} and charge == 0
    counts, charge = parse_formula("(NH4)2SO4")
    assert dict(counts) == {"N": 2, "H": 8, "S": 1, "O": 4} and charge == 0
    counts, charge = parse_formula("SO4^2-")
    assert dict(counts) == {"S": 1, "O": 4} and charge == -2
    counts, charge = parse_formula("CuSO4.5H2O")
    assert dict(counts) == {"Cu": 1, "S": 1, "O": 9, "H": 10} and charge == 0


def test_balance_combustion_propane():
    assert balance(["C3H8", "O2"], ["CO2", "H2O"]) == [1, 5, 3, 4]


def test_balance_water_and_rust():
    assert balance(["H2", "O2"], ["H2O"]) == [2, 1, 2]
    assert balance(["Fe", "O2"], ["Fe2O3"]) == [4, 3, 2]


def test_balance_conserves_charge_precipitation():
    coeffs = balance(["Ag^+", "Cl^-"], ["AgCl"])
    ok, deltas = is_conserved(list(zip(coeffs[:2], ["Ag^+", "Cl^-"])), list(zip(coeffs[2:], ["AgCl"])))
    assert ok and deltas == {}


def test_unbalanceable_raises():
    with pytest.raises(BalanceError):
        balance(["H2"], ["O2"])  # no shared element, impossible to conserve


def test_format_equation_drops_unit_coefficients():
    eq = format_equation([1, 5, 3, 4], ["C3H8", "O2"], ["CO2", "H2O"])
    assert eq == "C3H8 + 5 O2 -> 3 CO2 + 4 H2O"


def test_balance_packet_is_bijective_and_hash_verifies():
    packet = balance_reaction_packet(["C3H8", "O2"], ["CO2", "H2O"])
    assert packet.classification == "BIJECTIVE"
    assert packet.verify_hash()
    assert packet.recalculation.identity_ok is True
    assert packet.target.metadata["coefficients"] == [1, 5, 3, 4]
