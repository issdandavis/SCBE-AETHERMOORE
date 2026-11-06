"""Compound receipt: math, word, and code stay three faces."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from python.scbe.chemistry_compound_receipt import cell, compound, measure

ROOT = Path(__file__).resolve().parents[2]


def _node(receipt: dict) -> dict:
    return receipt["hyperatoms"][0]["node"]


def test_aligned_cell_keeps_three_scores_and_the_word():
    receipt = cell(formula="C2H5OH", reference="C2H6O", word="run", code="CCO", board_index=12)

    node = _node(receipt)
    assert receipt["schema_version"] == "aethermoore_chemistry_compound_receipt_v1"
    assert receipt["trit"] == 1
    assert receipt["admitted"] is True
    assert receipt["match_score"] == 1.0
    assert receipt["math_score"] == 1.0
    assert receipt["science_score"] == 8
    assert receipt["science_threshold"] == 8
    assert node["faces"]["word"] == "run"
    assert node["faces"]["code"]["token"] == "CCO"
    assert node["faces"]["math"]["composition"] == {"C": 2, "H": 6, "O": 1}
    assert "total" not in receipt
    assert receipt["receipt_id"].startswith("compound_")
    again = cell(formula="C2H5OH", reference="C2H6O", word="run", code="CCO", board_index=12)
    assert again["receipt_id"] == receipt["receipt_id"]


def test_word_change_changes_the_receipt_without_changing_the_ledger():
    ethanol = cell(formula="C2H6O", reference="C2H6O", word="ethanol", code="CCO", board_index=12)
    other_word = cell(formula="C2H6O", reference="C2H6O", word="alcohol", code="CCO", board_index=12)

    assert ethanol["receipt_id"] != other_word["receipt_id"]
    assert ethanol["science_score"] == other_word["science_score"] == 8
    assert _node(ethanol)["faces"]["math"]["composition"] == _node(other_word)["faces"]["math"]["composition"]


def test_methanol_cell_refuses_while_its_own_ledger_still_exists():
    receipt = cell(formula="CH4O", reference="C2H6O", word="methanol", code="CO", board_index=4)

    assert receipt["trit"] == -1
    assert receipt["admitted"] is False
    assert receipt["match_score"] == 0.0
    assert receipt["math_score"] == 1.0
    assert receipt["science_score"] == 2
    assert "atomic_alignment" in _node(receipt)["science_failed"]
    assert "polar_nucleus" not in _node(receipt)["science_failed"]


def test_charge_sign_refuses_without_losing_the_atom_ledger():
    receipt = cell(formula="H2O+", reference="H2O", word="water-plus", code="[H2O+]", board_index=7)

    node = _node(receipt)
    assert receipt["science_score"] == 5
    assert receipt["match_score"] == 0.0
    assert receipt["math_score"] == 1.0
    assert receipt["trit"] == -1
    assert node["faces"]["math"]["composition"] == {"H": 2, "O": 1}
    assert node["venn"] == "exists_only"


def test_unknown_formula_has_no_math_ledger():
    receipt = cell(formula="Zz", reference="H2O", word="outside", code="Zz", board_index=0)

    assert receipt["math_score"] == 0.0
    assert receipt["match_score"] == 0.0
    assert receipt["science_score"] == 0
    assert receipt["trit"] == -1
    assert _node(receipt)["venn"] == "nonexistence"


def test_open_overlap_stays_open_until_measurement():
    open_receipt = compound(
        "shared-cell",
        [
            {
                "reference": "C2H6O",
                "board_index": 12,
                "measured": False,
                "overlap": [
                    {"formula": "C2H6O", "word": "ethanol", "code": "CCO"},
                    {"formula": "CH4O", "word": "methanol", "code": "CO"},
                ],
            }
        ],
    )

    assert open_receipt["trit"] == 0
    assert open_receipt["admitted"] is False
    assert open_receipt["science_score"] is None
    assert open_receipt["match_score"] is None
    assert open_receipt["math_score"] is None
    assert _node(open_receipt)["candidates"][1]["science_score"] == 2

    measured = measure(open_receipt)
    selected = _node(measured)["selected"]
    assert measured["trit"] == 1
    assert measured["admitted"] is True
    assert measured["science_score"] == 8
    assert measured["match_score"] == 1.0
    assert measured["math_score"] == 1.0
    assert [row["word"] for row in selected] == ["ethanol"]
    assert _node(measured)["candidates"][1]["science_score"] == 2
    assert measured["receipt_id"] != open_receipt["receipt_id"]


def test_two_spellings_can_share_an_admitted_cell():
    receipt = compound(
        "spellings",
        [
            {
                "reference": "C2H6O",
                "board_index": 12,
                "measured": True,
                "overlap": [
                    {"formula": "C2H6O", "word": "ethanol", "code": "CCO"},
                    {"formula": "C2H5OH", "word": "alcohol", "code": "OCC"},
                ],
            }
        ],
    )

    assert receipt["trit"] == 1
    assert receipt["science_score"] == 8
    assert [row["word"] for row in _node(receipt)["selected"]] == ["ethanol", "alcohol"]


def test_refused_overlap_uses_the_weaker_science_score():
    receipt = compound(
        "neither",
        [
            {
                "reference": "C2H6O",
                "board_index": 3,
                "measured": True,
                "overlap": [
                    {"formula": "CH4O", "word": "methanol", "code": "CO"},
                    {"formula": "C3H8O", "word": "propanol", "code": "CCCO"},
                ],
            }
        ],
    )

    assert receipt["trit"] == -1
    assert receipt["admitted"] is False
    assert _node(receipt)["selected"] == []
    assert receipt["science_score"] == 2
    assert receipt["math_score"] == 1.0
    assert receipt["match_score"] == 0.0


def test_chain_is_admitted_only_when_every_joint_is_admitted():
    refused = compound(
        "chain",
        [
            {
                "formula": "C2H6O",
                "reference": "C2H6O",
                "word": "ethanol",
                "code": "CCO",
                "board_index": 1,
            },
            {
                "formula": "CH4O",
                "reference": "C2H6O",
                "word": "methanol",
                "code": "CO",
                "board_index": 2,
                "children": [
                    {
                        "formula": "H2O",
                        "reference": "H2O",
                        "word": "water",
                        "code": "O",
                        "board_index": 3,
                    }
                ],
            },
        ],
    )
    admitted = compound(
        "chain",
        [
            {
                "formula": "C2H6O",
                "reference": "C2H6O",
                "word": "ethanol",
                "code": "CCO",
                "board_index": 1,
            },
            {
                "formula": "H2O",
                "reference": "H2O",
                "word": "water",
                "code": "O",
                "board_index": 2,
            },
        ],
    )

    assert refused["trit"] == -1
    assert refused["admitted"] is False
    assert refused["science_score"] == 2
    assert refused["math_score"] == 1.0
    assert refused["match_score"] == 0.0
    assert admitted["trit"] == 1
    assert admitted["science_score"] == 8
    assert admitted["match_score"] == 1.0
    assert admitted["math_score"] == 1.0


def test_open_joint_keeps_the_chain_open():
    receipt = compound(
        "waiting",
        [
            {
                "formula": "H2O",
                "reference": "H2O",
                "word": "water",
                "code": "O",
                "board_index": 1,
            },
            {
                "reference": "C2H6O",
                "board_index": 2,
                "overlap": [
                    {"formula": "C2H6O", "word": "ethanol", "code": "CCO"},
                    {"formula": "CH4O", "word": "methanol", "code": "CO"},
                ],
            },
        ],
    )

    assert receipt["trit"] == 0
    assert receipt["science_score"] is None
    assert receipt["admitted"] is False


def test_branch_and_board_limits():
    with pytest.raises(ValueError):
        cell(formula="H2O", reference="H2O", word="water", code="O", board_index=256)
    with pytest.raises(ValueError):
        cell(formula="H2O", reference="H2O", word=" ", code="O", board_index=1)
    with pytest.raises(ValueError):
        compound(
            "wide",
            [
                {
                    "formula": "H2O",
                    "reference": "H2O",
                    "word": "water",
                    "code": "O",
                    "board_index": 1,
                    "children": [
                        {
                            "formula": "H2O",
                            "reference": "H2O",
                            "word": "a",
                            "code": "O",
                            "board_index": 2,
                        },
                        {
                            "formula": "H2O",
                            "reference": "H2O",
                            "word": "b",
                            "code": "O",
                            "board_index": 3,
                        },
                        {
                            "formula": "H2O",
                            "reference": "H2O",
                            "word": "c",
                            "code": "O",
                            "board_index": 4,
                        },
                        {
                            "formula": "H2O",
                            "reference": "H2O",
                            "word": "d",
                            "code": "O",
                            "board_index": 5,
                        },
                    ],
                }
            ],
        )


def test_cli_compound_cell():
    completed = subprocess.run(
        [
            sys.executable,
            "scbe.py",
            "chem",
            "set",
            "compound",
            "--formula",
            "C2H6O",
            "--reference",
            "C2H6O",
            "--word",
            "ethanol",
            "--code",
            "CCO",
            "--board",
            "12",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["trit"] == 1
    assert payload["science_score"] == 8
    assert payload["match_score"] == 1.0
    assert payload["math_score"] == 1.0
    assert "total" not in payload
