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


def test_charge_violation_names_charge_not_nullity():
    """The use-case-audit gap: charge violations used to say 'nullity=0'."""
    with pytest.raises(BalanceError, match="charge is not conserved"):
        balance(["Fe^2+"], ["Fe^3+"])


def test_one_sided_element_is_named():
    with pytest.raises(BalanceError, match=r"N \(only in products\)"):
        balance(["H2", "O2"], ["H2O", "N2"])
    with pytest.raises(BalanceError, match=r"O \(only in products\)"):
        balance(["H2"], ["H2O"])


def test_underdetermined_reaction_says_so():
    # C + O2 -> CO + CO2 mixes two independent oxidations (nullity 2).
    with pytest.raises(BalanceError, match="underdetermined: it mixes 2 independent reactions"):
        balance(["C", "O2"], ["CO", "CO2"])


def test_is_conserved_deltas_keys_are_deterministically_ordered():
    # determinism guard: deltas is built over a set-union whose iteration order is PYTHONHASHSEED-dependent.
    # sorted() makes the element keys reproducible, so a direct caller that reads/serializes deltas order-
    # sensitively (a log, a repr, list(deltas)) is hashseed-independent.
    ok, deltas = is_conserved([(1, "C6H12O6"), (1, "O2")], [(1, "CO2"), (1, "H2O")])
    assert not ok  # unbalanced as written -> non-empty deltas across several elements
    element_keys = [k for k in deltas if k != "charge"]
    assert element_keys == sorted(element_keys)  # sorted order, not the (hashseed-varying) set-union order


def test_reaction_packet_hash_is_stable_independent_of_dict_order():
    # the receipt path's determinism is independent of any dict insertion order: canonical_json sorts keys
    # before hashing, so the packet content hash is reproducible (what replay / Merkle-anchoring relies on).
    from python.scbe.reaction_state import sha256_value

    pkt = balance_reaction_packet(["C6H12O6", "O2"], ["CO2", "H2O"])
    d = pkt.unsigned_dict()
    reordered = {k: d[k] for k in reversed(list(d))}  # same content, opposite key order
    assert sha256_value(d) == sha256_value(reordered)  # canonicalized -> identical hash
