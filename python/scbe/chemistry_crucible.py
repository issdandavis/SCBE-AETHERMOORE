"""Black-box crucible for the chemistry math set.

Scripted agents each call the catalog with their own compound. The crucible
and the witness then see receipts, not the other agent's private spelling.
Match accuracy is whether those receipts agree on the reference product.
Math accuracy is whether the receipt itself conserves atoms or compares
identity correctly. Science is a separate sum of micro-points. A different
compound can keep math accuracy at 1, miss the science threshold, and drop
the match.
"""

from __future__ import annotations

from typing import Any, Sequence

from python.scbe.chemistry_math_set import run
from python.scbe.chemistry_science_score import THRESHOLD, score_equations, score_formulas

SCHEMA = "aethermoore_chemistry_crucible_v1"
ROLES = ("alchemist", "crucible", "witness")
GLUCOSE_STEREO = "OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O"
GLUCOSE_FLAT = "OCC1OC(O)C(O)C(O)C1O"


def _composition(receipt: dict[str, Any]) -> dict[str, int]:
    result = receipt["result"]
    composition = result.get("composition")
    if composition is None:
        raise KeyError("receipt has no composition")
    return {str(symbol): int(count) for symbol, count in composition.items()}


def _mean(values: Sequence[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def _minimum_formula_science(formulas: Sequence[str]) -> dict[str, Any]:
    """Score every later formula against the first and keep the lowest sum."""
    if len(formulas) < 2:
        return score_formulas(formulas[0], formulas[0])
    reference = formulas[0]
    scored = [score_formulas(candidate, reference) for candidate in formulas[1:]]
    return min(scored, key=lambda row: (int(row["science_score"]), str(row["candidate"]["formula"])))


def _trial(
    name: str,
    *,
    cards: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
    match_accuracy: float,
    math_accuracy: float,
    science: dict[str, Any],
    detail: dict[str, Any],
) -> dict[str, Any]:
    return {
        "name": name,
        "roles": list(ROLES),
        "cards": cards,
        "receipt_ids": [receipt["receipt_id"] for receipt in receipts],
        "match_accuracy": match_accuracy,
        "math_accuracy": math_accuracy,
        "math_score": math_accuracy,
        "accuracy": match_accuracy,
        "science_score": science["science_score"],
        "science_threshold": science["threshold"],
        "science_points": science["points"],
        "science_failed": science["failed"],
        "venn": science["venn"],
        "science_admitted": science["admitted"],
        "detail": detail,
    }


def _card(role: str, agent: str, receipt: dict[str, Any]) -> dict[str, Any]:
    result = receipt["result"]
    return {
        "role": role,
        "agent": agent,
        "operation": receipt["operation"],
        "mass_basis": receipt["mass_basis"],
        "receipt_id": receipt["receipt_id"],
        "formula": result.get("formula") or result.get("balanced_equation"),
        "inchikey14": result.get("inchikey14"),
    }


def _ethanol_spellings() -> dict[str, Any]:
    alchemist = run("exact", smiles="CCO")
    crucible = run("average", formula="C2H5OH")
    witness = run("exact", smiles="OCC")
    compositions = [_composition(alchemist), _composition(crucible), _composition(witness)]
    agreed = compositions[1:] == compositions[:1] * 2
    formulas = [
        alchemist["result"]["formula"],
        crucible["result"]["formula"],
        witness["result"]["formula"],
    ]
    return _trial(
        "ethanol_spellings",
        cards=[
            _card("alchemist", "alchemist", alchemist),
            _card("crucible", "crucible", crucible),
            _card("witness", "witness", witness),
        ],
        receipts=[alchemist, crucible, witness],
        match_accuracy=1.0 if agreed else 0.0,
        math_accuracy=1.0 if agreed else 0.0,
        science=_minimum_formula_science(formulas),
        detail={"compositions": compositions, "agreed": agreed, "formulas": formulas},
    )


def _glucose_drawings() -> dict[str, Any]:
    alchemist = run("exact", smiles=GLUCOSE_STEREO)
    crucible = run("exact", smiles=GLUCOSE_FLAT)
    witness = run("same", smiles=GLUCOSE_STEREO, other=GLUCOSE_FLAT)
    agreed = bool(witness["result"]["same"])
    keys_match = alchemist["result"]["inchikey14"] == crucible["result"]["inchikey14"] == "WQZGKKKJIJFFOK"
    math_ok = agreed and keys_match and witness["result"]["left_inchikey14"] == witness["result"]["right_inchikey14"]
    formulas = [alchemist["result"]["formula"], crucible["result"]["formula"]]
    return _trial(
        "glucose_drawings",
        cards=[
            _card("alchemist", "alchemist", alchemist),
            _card("crucible", "crucible", crucible),
            _card("witness", "witness", witness),
        ],
        receipts=[alchemist, crucible, witness],
        match_accuracy=1.0 if agreed else 0.0,
        math_accuracy=1.0 if math_ok else 0.0,
        science=_minimum_formula_science(formulas),
        detail={"inchikey14": witness["result"]["left_inchikey14"], "same": agreed, "formulas": formulas},
    )


def _reaction_trial(
    name: str,
    reactant_formulas: list[str],
    product_formulas: list[str],
    reference_equation: str,
    math_equation: str,
) -> dict[str, Any]:
    reactant_receipts = [run("average", formula=formula) for formula in reactant_formulas]
    product_receipts = [run("average", formula=formula) for formula in product_formulas]
    crucible = run(
        "balance",
        reactants=[receipt["result"]["formula"] for receipt in reactant_receipts],
        products=[receipt["result"]["formula"] for receipt in product_receipts],
    )
    equation = crucible["result"].get("balanced_equation")
    conserved = bool(crucible["result"].get("conserved"))
    closure = crucible["result"].get("mass_closure") or {}
    closure_ok = conserved and float(closure.get("relative_error", 1.0)) <= 1e-6
    matched = equation == reference_equation
    math_ok = bool(crucible["ok"]) and conserved and closure_ok and equation == math_equation
    science = score_equations(equation or "", reference_equation)
    cards = [_card("alchemist", "alchemist", receipt) for receipt in reactant_receipts]
    cards.append(_card("crucible", "crucible", crucible))
    cards.extend(_card("witness", "witness", receipt) for receipt in product_receipts)
    return _trial(
        name,
        cards=cards,
        receipts=[*reactant_receipts, crucible, *product_receipts],
        match_accuracy=1.0 if matched else 0.0,
        math_accuracy=1.0 if math_ok else 0.0,
        science=science,
        detail={
            "balanced_equation": equation,
            "reference_equation": reference_equation,
            "conserved": conserved,
            "mass_closure": closure,
            "matched_reference": matched,
        },
    )


def _propanol_is_not_ethanol() -> dict[str, Any]:
    alchemist = run("exact", smiles="CCO")
    crucible = run("exact", smiles="CCCO")
    witness = run("same", smiles="CCO", other="CCCO")
    separated = witness["result"]["same"] is False
    keys_differ = alchemist["result"]["inchikey14"] != crucible["result"]["inchikey14"]
    formulas = [alchemist["result"]["formula"], crucible["result"]["formula"]]
    return _trial(
        "propanol_is_not_ethanol",
        cards=[
            _card("alchemist", "alchemist", alchemist),
            _card("crucible", "crucible", crucible),
            _card("witness", "witness", witness),
        ],
        receipts=[alchemist, crucible, witness],
        match_accuracy=0.0 if separated else 1.0,
        math_accuracy=1.0 if separated and keys_differ else 0.0,
        science=_minimum_formula_science(formulas),
        detail={
            "claimed_same_substance": True,
            "receipts_agree": not separated,
            "left_inchikey14": witness["result"]["left_inchikey14"],
            "right_inchikey14": witness["result"]["right_inchikey14"],
            "formulas": formulas,
        },
    )


def run_black_box() -> dict[str, Any]:
    """Run the crucible trials and score match accuracy against math accuracy."""
    trials = [
        _ethanol_spellings(),
        _glucose_drawings(),
        _reaction_trial(
            "ethanol_combustion",
            ["C2H6O", "O2"],
            ["CO2", "H2O"],
            "C2H6O + 3O2 -> 2CO2 + 3H2O",
            "C2H6O + 3O2 -> 2CO2 + 3H2O",
        ),
        _reaction_trial(
            "methanol_swap",
            ["CH4O", "O2"],
            ["CO2", "H2O"],
            "C2H6O + 3O2 -> 2CO2 + 3H2O",
            "2CH4O + 3O2 -> 2CO2 + 4H2O",
        ),
        _propanol_is_not_ethanol(),
        _reaction_trial(
            "peroxide_not_water",
            ["H2", "O2"],
            ["H2O2"],
            "2H2 + O2 -> 2H2O",
            "H2 + O2 -> H2O2",
        ),
    ]
    return {
        "schema_version": SCHEMA,
        "product": "AI Chemistry Set",
        "scene": "crucible",
        "roles": list(ROLES),
        "black_box": "The witness scores chem-set receipts. Agents do not read each other's input strings.",
        "trials": trials,
        "match_accuracy_mean": _mean([trial["match_accuracy"] for trial in trials]),
        "math_accuracy_mean": _mean([trial["math_accuracy"] for trial in trials]),
        "accuracy_mean": _mean([trial["accuracy"] for trial in trials]),
        "accuracy_by_trial": {trial["name"]: trial["accuracy"] for trial in trials},
        "science_threshold": THRESHOLD,
        "science_admitted_count": sum(1 for trial in trials if trial["science_admitted"]),
        "boundary": (
            "Match accuracy asks whether the product agreed with the reference. "
            "Math accuracy asks whether the receipt conserved atoms or compared identity correctly. "
            "Science is a separate sum of eight micro-points and is not added into math."
        ),
    }
