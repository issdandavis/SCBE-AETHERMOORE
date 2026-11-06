"""AI Chemistry Set catalog and the crucible black box."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from python.scbe.atomic_tokenization import map_token_to_element
from python.scbe.chemistry_crucible import run_black_box
from python.scbe.chemistry_math_set import run
from python.scbe.chemistry_science_score import THRESHOLD, score_formulas

ROOT = Path(__file__).resolve().parents[2]
GLUCOSE_STEREO = "OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O"
GLUCOSE_FLAT = "OCC1OC(O)C(O)C(O)C1O"


def test_balance_matches_the_chemistry_set_propane_equation():
    receipt = run("balance", equation="C3H8 + O2 -> CO2 + H2O")

    assert receipt["ok"] is True
    assert receipt["schema_version"] == "aethermoore_ai_chemistry_set_v1"
    assert receipt["product"] == "AI Chemistry Set"
    assert receipt["mass_basis"] == "element_conservation"
    assert receipt["result"]["balanced_equation"] == "C3H8 + 5O2 -> 3CO2 + 4H2O"
    assert receipt["result"]["conserved"] is True
    assert receipt["result"]["deltas"] == {}
    assert receipt["result"]["mass_closure"]["relative_error"] <= 1e-6
    assert receipt["receipt_id"].startswith("chemset_")


def test_exact_and_average_keep_their_mass_basis():
    exact = run("exact", smiles="CCO")
    average = run("average", formula="C2H6O")

    assert exact["mass_basis"] == "exact_mol_wt"
    assert abs(exact["result"]["exact_mass"] - 46.041865) < 5e-4
    assert exact["result"]["inchikey14"] == "LFQSCWFLJHTTHZ"
    assert average["mass_basis"] == "average_molar_mass"
    assert average["result"]["molar_mass_g_mol"] == 46.069
    assert exact["result"]["composition"] == average["result"]["composition"] == {"C": 2, "H": 6, "O": 1}


def test_adduct_round_trip_uses_the_ion_mass():
    exact = run("exact", smiles="CCO")
    proton = run("adduct", precursor_mz=0.0, adduct="[M+H]+")
    precursor = exact["result"]["exact_mass"] + proton["result"]["adduct_delta"]
    receipt = run("adduct", precursor_mz=precursor, adduct="[M+H]+")

    assert receipt["mass_basis"] == "exact_mol_wt"
    assert receipt["result"]["neutral_mass"] == pytest.approx(exact["result"]["exact_mass"], abs=1e-9)
    assert abs(proton["result"]["adduct_delta"] - 1.007276) < 1e-5


def test_same_accepts_glucose_drawings_and_rejects_propanol():
    same = run("same", smiles=GLUCOSE_STEREO, other=GLUCOSE_FLAT)
    different = run("same", smiles="CCO", other="CCCO")

    assert same["result"]["same"] is True
    assert same["result"]["left_inchikey14"] == "WQZGKKKJIJFFOK"
    assert different["result"]["same"] is False
    assert different["result"]["left_inchikey14"] != different["result"]["right_inchikey14"]


def test_ops_names_every_mass_basis():
    receipt = run("ops")
    rows = {row["name"]: row["mass_basis"] for row in receipt["result"]["operations"]}

    assert rows == {
        "balance": "element_conservation",
        "exact": "exact_mol_wt",
        "average": "average_molar_mass",
        "adduct": "exact_mol_wt",
        "same": "inchikey14",
    }


def test_word_projector_stays_on_sodium():
    assert map_token_to_element("run").symbol == "Na"


def test_crucible_match_falls_when_agents_bring_different_compounds():
    report = run_black_box()
    by_name = {trial["name"]: trial for trial in report["trials"]}

    assert by_name["ethanol_spellings"]["match_accuracy"] == 1.0
    assert by_name["ethanol_spellings"]["math_accuracy"] == 1.0
    assert by_name["glucose_drawings"]["detail"]["inchikey14"] == "WQZGKKKJIJFFOK"
    assert by_name["ethanol_combustion"]["detail"]["balanced_equation"] == "C2H6O + 3O2 -> 2CO2 + 3H2O"
    assert by_name["ethanol_combustion"]["match_accuracy"] == 1.0
    assert by_name["ethanol_combustion"]["math_accuracy"] == 1.0
    assert by_name["methanol_swap"]["detail"]["balanced_equation"] == "2CH4O + 3O2 -> 2CO2 + 4H2O"
    assert by_name["methanol_swap"]["math_accuracy"] == 1.0
    assert by_name["methanol_swap"]["match_accuracy"] == 0.0
    assert by_name["propanol_is_not_ethanol"]["math_accuracy"] == 1.0
    assert by_name["propanol_is_not_ethanol"]["match_accuracy"] == 0.0
    assert by_name["peroxide_not_water"]["detail"]["balanced_equation"] == "H2 + O2 -> H2O2"
    assert by_name["peroxide_not_water"]["math_accuracy"] == 1.0
    assert by_name["peroxide_not_water"]["match_accuracy"] == 0.0
    assert report["math_accuracy_mean"] == 1.0
    assert report["match_accuracy_mean"] == 0.5
    assert report["accuracy_mean"] == 0.5
    assert all(trial["receipt_ids"] for trial in report["trials"])


def test_cli_balance_and_crucible():
    balance = subprocess.run(
        [
            sys.executable,
            "scbe.py",
            "chem",
            "set",
            "balance",
            "--equation",
            "C3H8 + O2 -> CO2 + H2O",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert balance.returncode == 0, balance.stderr
    assert json.loads(balance.stdout)["result"]["balanced_equation"] == "C3H8 + 5O2 -> 3CO2 + 4H2O"

    crucible = subprocess.run(
        [sys.executable, "scbe.py", "chem", "set", "crucible", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert crucible.returncode == 0, crucible.stderr
    payload = json.loads(crucible.stdout)
    assert payload["match_accuracy_mean"] == 0.5
    assert payload["math_accuracy_mean"] == 1.0


def _points(scored: dict) -> dict[str, int]:
    return {point["name"]: point["point"] for point in scored["points"]}


def test_science_micro_points_reach_their_own_threshold():
    aligned = score_formulas("C2H5OH", "C2H6O")
    charge = score_formulas("H2O+", "H2O")
    missing_valence = score_formulas("Se", "Se")
    outside = score_formulas("Zz", "H2O")

    assert THRESHOLD == 8
    assert aligned["science_score"] == 8
    assert aligned["admitted"] is True
    assert sum(point["point"] for point in aligned["points"]) == aligned["science_score"]
    assert aligned["venn"]["region"] == "intersection"
    assert "math" not in aligned

    charge_points = _points(charge)
    assert charge["science_score"] == 5
    assert charge["admitted"] is False
    assert charge_points["atomic_alignment"] == 1
    assert charge_points["polar_nucleus"] == 0
    assert charge_points["charge_state"] == 0
    assert charge_points["density_medium"] == 1
    assert charge_points["existence_venn"] == 0
    assert charge["candidate"]["protons"] == charge["reference"]["protons"] == 10
    assert charge["candidate"]["electrons"] == 9
    assert charge["reference"]["electrons"] == 10

    assert missing_valence["science_score"] == 7
    assert _points(missing_valence)["valence_and_atom_count"] == 0
    assert missing_valence["admitted"] is False

    assert outside["venn"]["region"] == "nonexistence"
    assert outside["science_score"] == 0
    assert outside["admitted"] is False


def test_crucible_science_stays_separate_from_math():
    report = run_black_box()
    by_name = {trial["name"]: trial for trial in report["trials"]}

    def points(name: str) -> dict[str, int]:
        return {point["name"]: point["point"] for point in by_name[name]["science_points"]}

    assert by_name["ethanol_spellings"]["science_score"] == 8
    assert by_name["glucose_drawings"]["science_score"] == 8
    assert by_name["ethanol_combustion"]["science_score"] == 8
    assert by_name["ethanol_combustion"]["science_admitted"] is True
    assert by_name["methanol_swap"]["math_score"] == 1.0
    assert by_name["methanol_swap"]["science_score"] == 3
    assert by_name["methanol_swap"]["science_admitted"] is False
    assert points("methanol_swap")["atomic_alignment"] == 0
    assert points("methanol_swap")["reaction_effect"] == 1
    assert points("methanol_swap")["polar_nucleus"] == 1
    assert points("methanol_swap")["density_medium"] == 1
    assert by_name["propanol_is_not_ethanol"]["science_score"] == 2
    assert points("propanol_is_not_ethanol")["reaction_effect"] == 0
    assert points("propanol_is_not_ethanol")["polar_nucleus"] == 1
    assert points("propanol_is_not_ethanol")["density_medium"] == 1
    assert by_name["peroxide_not_water"]["science_score"] == 3
    assert points("peroxide_not_water")["reaction_effect"] == 1
    assert report["science_threshold"] == 8
    assert report["science_admitted_count"] == 3
    assert report["accuracy_mean"] == 0.5
    assert report["math_accuracy_mean"] == 1.0
    for trial in report["trials"]:
        assert sum(point["point"] for point in trial["science_points"]) == trial["science_score"]
        assert trial["math_score"] == trial["math_accuracy"]
        assert trial["accuracy"] == trial["match_accuracy"]


def test_cli_science_formula():
    science = subprocess.run(
        [
            sys.executable,
            "scbe.py",
            "chem",
            "set",
            "science",
            "--formula",
            "CH4O",
            "--reference",
            "C2H6O",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert science.returncode == 0, science.stderr
    payload = json.loads(science.stdout)
    assert payload["science_score"] == 2
    assert payload["threshold"] == 8
    assert payload["admitted"] is False
    assert payload["schema_version"] == "aethermoore_chemistry_science_score_v1"
