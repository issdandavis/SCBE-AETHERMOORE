"""Controlled-substance screen locks (defensive refusal lane).

Tests draw flagged inputs from the vendored screening CSV at runtime — list
contents are never embedded in test code, and assertions never name entries.
"""

from __future__ import annotations

import pytest

from python.scbe.controlled_substances import (
    SIMILARITY_THRESHOLD,
    ControlledSubstanceDenied,
    _listed_cas_numbers,
    assert_not_controlled,
    load_screen_list,
    screen_input,
)

BENIGN_SMILES = ["O", "CCO", "CC(=O)OC1=CC=CC=C1C(=O)O", "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O", "C1=CC=CC=C1"]


def test_screen_list_loads_and_is_nontrivial():
    rows = load_screen_list()
    assert len(rows) > 100
    assert all(row["smiles"].strip() for row in rows)


def test_exact_string_lanes_flag_list_entries():
    """CAS-exact and SMILES-exact lanes are stdlib and always on."""
    rows = load_screen_list()
    a_cas = next(iter(_listed_cas_numbers()))
    cas_report = screen_input(a_cas)
    assert cas_report["flagged"] is True and cas_report["match_kind"] == "cas_exact"
    smiles_report = screen_input(rows[0]["smiles"].strip())
    assert smiles_report["flagged"] is True
    assert smiles_report["match_kind"] in ("smiles_exact", "smiles_canonical")


def test_benign_inputs_are_clear():
    for smiles in BENIGN_SMILES:
        report = screen_input(smiles)
        assert report["flagged"] is False, smiles
        assert report["match_kind"] is None
    # Unknown CAS numbers are clear too.
    assert screen_input("50-78-2")["flagged"] is False  # aspirin CAS
    assert screen_input("")["flagged"] is False


def test_report_never_names_the_matched_entry():
    rows = load_screen_list()
    report = screen_input(rows[0]["smiles"].strip())
    serialized = str(report)
    assert rows[0]["smiles"].strip() not in serialized
    assert rows[0]["cas"].strip() not in serialized


def test_canonical_lane_catches_alternate_renderings():
    Chem = pytest.importorskip("rdkit.Chem")
    rows = load_screen_list()
    caught = 0
    rendered = 0
    for row in rows[:10]:
        mol = Chem.MolFromSmiles(row["smiles"].strip())
        if mol is None or mol.GetNumAtoms() < 2:
            continue
        alternate = Chem.MolToSmiles(mol, canonical=False, rootedAtAtom=mol.GetNumAtoms() - 1)
        if alternate == row["smiles"].strip():
            continue
        rendered += 1
        report = screen_input(alternate)
        if report["flagged"] and report["match_kind"] in ("smiles_exact", "smiles_canonical"):
            caught += 1
    assert rendered > 0 and caught == rendered


def test_similarity_lane_reports_and_threshold_is_published_value():
    pytest.importorskip("rdkit")
    assert SIMILARITY_THRESHOLD == 0.35
    report = screen_input("CC(=O)OC1=CC=CC=C1C(=O)O")  # aspirin: clear, but similarity measured
    assert report["screen_level"] == "similarity"
    assert report["input_parsed"] is True
    assert report["max_similarity"] is not None
    assert report["max_similarity"] <= SIMILARITY_THRESHOLD


def test_assert_not_controlled_raises_with_report():
    rows = load_screen_list()
    with pytest.raises(ControlledSubstanceDenied) as excinfo:
        assert_not_controlled(rows[0]["smiles"].strip())
    assert excinfo.value.report["flagged"] is True
    clear = assert_not_controlled("CCO")
    assert clear["flagged"] is False


def test_geometry_packet_refuses_flagged_and_witnesses_clear_screen():
    pytest.importorskip("rdkit")
    from python.scbe.geometry_view import geometry_view_packet

    rows = load_screen_list()
    with pytest.raises(ControlledSubstanceDenied):
        geometry_view_packet(rows[0]["smiles"].strip())
    packet = geometry_view_packet("CCO")
    witness = [line for line in packet.claim_boundary if line.startswith("controlled-substance screen: clear")]
    assert len(witness) == 1
