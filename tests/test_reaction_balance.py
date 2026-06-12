"""Regression locks for the exact reaction balancer (python/scbe/reaction_balance.py)."""

from __future__ import annotations

import pytest

from python.scbe.reaction_balance import (
    BalanceError,
    HazardDenied,
    balance,
    balance_reaction_packet,
    format_equation,
    is_conserved,
    parse_formula,
    screen_species_hazards,
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


def test_bleach_acid_reaction_carries_hazard_flags():
    """The use-case-audit gap: NaOCl + HCl -> Cl2 balanced with zero warning."""
    packet = balance_reaction_packet(["NaOCl", "HCl"], ["Cl2", "NaCl", "H2O"])
    hazards = packet.target.metadata["hazards"]
    assert any("Cl2" in flag and "(product)" in flag for flag in hazards)
    assert any("chlorine" in flag for flag in hazards)
    # Hazard is a warning, not a correctness failure: stoichiometry stays exact.
    assert packet.classification == "BIJECTIVE"
    assert packet.target.metadata["coefficients"] == [1, 2, 1, 1, 1]
    assert any(flag in packet.semantic_engravings for flag in hazards)
    assert any("not a safety claim" in line for line in packet.claim_boundary)


def test_benign_reaction_has_empty_hazard_list():
    packet = balance_reaction_packet(["C3H8", "O2"], ["CO2", "H2O"])
    assert packet.target.metadata["hazards"] == []
    assert any("not a safety claim" in line for line in packet.claim_boundary)


def test_hazard_screen_strips_charge_notation():
    flags = screen_species_hazards(["CN^-"], ["HCN"])
    assert len(flags) == 2
    assert "hazard (reactant): CN^- — cyanide — highly toxic" in flags[0]
    assert "hazard (product): HCN" in flags[1]


def test_hazard_screen_is_case_sensitive_about_elements():
    # CO (carbon monoxide) flags; Co (cobalt) must not.
    assert screen_species_hazards(["CO"], []) != []
    assert screen_species_hazards(["Co"], []) == []


def test_forbidden_request_text_is_denied_before_balancing():
    """chem_code's FORBIDDEN_PATTERNS deny the request as a governed refusal,
    not a parse error. Only active in checkouts that carry chem_code."""
    pytest.importorskip("python.scbe.chem_code")
    with pytest.raises(HazardDenied, match="denied unsafe chemistry request"):
        balance_reaction_packet(["sarin"], ["H2O"])
