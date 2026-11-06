"""AI Chemistry Set math catalog.

One JSON receipt per operation so another system can call balance, exact mass,
average molar mass, adduct neutral mass, or identity without guessing which
chem verb owns the number. The linguistic word-to-element map is not used.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Sequence

SCHEMA = "aethermoore_ai_chemistry_set_v1"
PRODUCT = "AI Chemistry Set"
BOUNDARY = (
    "Educational formula and structure math with a receipt. "
    "Exact mass, average molar mass, and atom conservation stay labeled. "
    "This catalog does not rank spectra and does not give a synthesis procedure."
)

OPERATIONS = (
    {
        "name": "ops",
        "mass_basis": "catalog",
        "inputs": [],
        "returns": "the operation list",
    },
    {
        "name": "balance",
        "mass_basis": "element_conservation",
        "inputs": ["equation"],
        "returns": "smallest positive integer coefficients and the balanced equation",
    },
    {
        "name": "exact",
        "mass_basis": "exact_mol_wt",
        "inputs": ["smiles"],
        "returns": "monoisotopic mass, formula, composition, and InChIKey14",
    },
    {
        "name": "average",
        "mass_basis": "average_molar_mass",
        "inputs": ["formula"],
        "returns": "atom counts and average molar mass",
    },
    {
        "name": "adduct",
        "mass_basis": "exact_mol_wt",
        "inputs": ["precursor_mz", "adduct"],
        "returns": "neutral monoisotopic mass for one known single-charge adduct",
    },
    {
        "name": "same",
        "mass_basis": "inchikey14",
        "inputs": ["smiles", "other"],
        "returns": "whether two drawings share an InChIKey first block",
    },
)


def _receipt_id(operation: str, inputs: dict[str, Any]) -> str:
    blob = json.dumps({"operation": operation, "inputs": inputs}, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
    return f"chemset_{digest}"


def _envelope(
    operation: str,
    inputs: dict[str, Any],
    result: dict[str, Any],
    mass_basis: str,
    assumptions: list[str],
    *,
    ok: bool = True,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "schema_version": SCHEMA,
        "receipt_id": _receipt_id(operation, inputs),
        "product": PRODUCT,
        "operation": operation,
        "inputs": inputs,
        "result": result,
        "assumptions": assumptions,
        "mass_basis": mass_basis,
        "error": error,
        "boundary": BOUNDARY,
    }


def _split_equation(equation: str) -> tuple[list[str], list[str]]:
    match = re.match(r"(.+?)(?:->|=>|=)(.+)", str(equation or "").strip())
    if not match:
        raise ValueError("equation needs a reactant side and a product side")

    def side(value: str) -> list[str]:
        parts = []
        for part in value.split("+"):
            token = re.sub(r"^\d+\s*", "", part.strip())
            if token:
                parts.append(token)
        return parts

    reactants = side(match.group(1))
    products = side(match.group(2))
    if not reactants or not products:
        raise ValueError("equation needs at least one reactant and one product")
    return reactants, products


def _format_equation(coeffs: Sequence[int], reactants: Sequence[str], products: Sequence[str]) -> str:
    def side(values: Sequence[int], formulas: Sequence[str]) -> str:
        return " + ".join(formula if coeff == 1 else f"{coeff}{formula}" for coeff, formula in zip(values, formulas))

    count = len(reactants)
    return f"{side(coeffs[:count], reactants)} -> {side(coeffs[count:], products)}"


def _mass_closure(coeffs: Sequence[int], reactants: Sequence[str], products: Sequence[str]) -> dict[str, Any]:
    from python.scbe.chemistry_dimensions import analyze_formula

    def total(formulas: Sequence[str], values: Sequence[int]) -> float:
        mass = 0.0
        for coeff, formula in zip(values, formulas):
            mass += coeff * float(analyze_formula(formula)["totals"]["molar_mass_g_mol"])
        return mass

    count = len(reactants)
    left = total(reactants, coeffs[:count])
    right = total(products, coeffs[count:])
    scale = max(abs(left), abs(right), 1e-12)
    return {
        "mass_basis": "average_molar_mass",
        "reactant_g_mol": round(left, 6),
        "product_g_mol": round(right, 6),
        "relative_error": abs(left - right) / scale,
    }


def balance_equation(
    *,
    equation: str | None = None,
    reactants: Sequence[str] | None = None,
    products: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Balance one equation and return a Chemistry Set receipt."""
    from python.scbe.reaction_balance import (
        BalanceError,
        _request_text_problems,
        balance,
        is_conserved,
        screen_species_hazards,
    )

    if equation:
        parsed_reactants, parsed_products = _split_equation(equation)
    else:
        parsed_reactants = [str(item).strip() for item in (reactants or []) if str(item).strip()]
        parsed_products = [str(item).strip() for item in (products or []) if str(item).strip()]
    inputs = {"reactants": parsed_reactants, "products": parsed_products}
    if equation:
        inputs["equation"] = equation
    if not parsed_reactants or not parsed_products:
        raise ValueError("balance needs reactants and products")
    denied = _request_text_problems(parsed_reactants, parsed_products)
    if denied:
        return _envelope(
            "balance",
            inputs,
            {"hazard_notes": denied},
            "element_conservation",
            ["The request text matched the chemistry deny screen."],
            ok=False,
            error="; ".join(denied),
        )
    try:
        coeffs = [int(value) for value in balance(parsed_reactants, parsed_products)]
    except BalanceError as exc:
        return _envelope(
            "balance",
            inputs,
            {"hazard_notes": screen_species_hazards(parsed_reactants, parsed_products)},
            "element_conservation",
            ["No unique positive integer balance for the species as written."],
            ok=False,
            error=str(exc),
        )
    conserved, deltas = is_conserved(
        list(zip(coeffs[: len(parsed_reactants)], parsed_reactants)),
        list(zip(coeffs[len(parsed_reactants) :], parsed_products)),
    )
    balanced = _format_equation(coeffs, parsed_reactants, parsed_products)
    closure = _mass_closure(coeffs, parsed_reactants, parsed_products)
    return _envelope(
        "balance",
        inputs,
        {
            "reactants": parsed_reactants,
            "products": parsed_products,
            "coefficients": coeffs,
            "balanced_equation": balanced,
            "conserved": bool(conserved),
            "deltas": deltas,
            "mass_closure": closure,
            "math": "exact rational nullspace over the element conservation matrix",
            "hazard_notes": screen_species_hazards(parsed_reactants, parsed_products)
            or ["Educational/math mode. No procedural synthesis requested."],
        },
        "element_conservation",
        [
            "Coefficients are the smallest positive integers that conserve atoms and charge.",
            "The mass closure uses average elemental weights, not the monoisotopic mass.",
        ],
    )


def exact_molecule(smiles: str) -> dict[str, Any]:
    from python.scbe.molecule_face import read_molecule

    molecule = read_molecule(smiles)
    return _envelope(
        "exact",
        {"smiles": smiles},
        {
            "smiles": molecule["smiles"],
            "formula": molecule["formula"],
            "exact_mass": molecule["exact_mass"],
            "composition": molecule["composition"],
            "heavy_atom_composition": molecule["heavy_atom_composition"],
            "inchikey": molecule["inchikey"],
            "inchikey14": molecule["inchikey14"],
            "formal_charge": molecule["formal_charge"],
        },
        "exact_mol_wt",
        ["Exact mass is RDKit ExactMolWt of the supplied SMILES."],
    )


def average_formula(formula: str) -> dict[str, Any]:
    from python.scbe.chemistry_dimensions import analyze_formula

    row = analyze_formula(formula)
    composition = {symbol: int(atom["count"]) for symbol, atom in row["atoms"].items()}
    return _envelope(
        "average",
        {"formula": formula},
        {
            "formula": row["formula"],
            "composition": composition,
            "molar_mass_g_mol": row["totals"]["molar_mass_g_mol"],
            "charge": row["totals"]["charge"],
            "atoms": row["atoms"],
        },
        "average_molar_mass",
        ["Molar mass is the average-weight ledger in chemistry_dimensions, not a monoisotopic mass."],
    )


def adduct_mass(precursor_mz: float, adduct: str, measured_bias_ppm: float = 0.0) -> dict[str, Any]:
    from python.scbe.molecule_face import neutral_mass, read_spectrum

    spectrum = read_spectrum(precursor_mz, adduct, measured_bias_ppm=measured_bias_ppm)
    return _envelope(
        "adduct",
        {"precursor_mz": precursor_mz, "adduct": adduct, "measured_bias_ppm": measured_bias_ppm},
        {
            "neutral_mass": neutral_mass(precursor_mz, adduct, measured_bias_ppm),
            "adduct_delta": spectrum["adduct_delta"],
            "charge": spectrum["charge"],
            "measured_bias_ppm": spectrum["measured_bias_ppm"],
        },
        "exact_mol_wt",
        ["Neutral mass is precursor_mz minus the RDKit ion mass. Bias stays 0 unless the caller sets it."],
    )


def same_molecule(smiles: str, other: str) -> dict[str, Any]:
    left = exact_molecule(smiles)
    right = exact_molecule(other)
    same = left["result"]["inchikey14"] == right["result"]["inchikey14"]
    return _envelope(
        "same",
        {"smiles": smiles, "other": other},
        {
            "same": same,
            "left_inchikey14": left["result"]["inchikey14"],
            "right_inchikey14": right["result"]["inchikey14"],
            "left_formula": left["result"]["formula"],
            "right_formula": right["result"]["formula"],
        },
        "inchikey14",
        ["Identity removes stereo, canonicalizes the tautomer, then compares the first InChIKey block."],
    )


def list_operations() -> dict[str, Any]:
    return _envelope(
        "ops",
        {},
        {"operations": [dict(row) for row in OPERATIONS if row["name"] != "ops"]},
        "catalog",
        ["Each operation names its mass basis. Call that operation for the number."],
    )


def run(operation: str, **inputs: Any) -> dict[str, Any]:
    """Run one catalog operation and return its receipt."""
    name = str(operation or "ops").strip().lower()
    if name in {"", "ops", "help"}:
        return list_operations()
    if name == "balance":
        return balance_equation(
            equation=inputs.get("equation"),
            reactants=inputs.get("reactants"),
            products=inputs.get("products"),
        )
    if name == "exact":
        return exact_molecule(str(inputs.get("smiles") or ""))
    if name == "average":
        return average_formula(str(inputs.get("formula") or ""))
    if name == "adduct":
        return adduct_mass(
            float(inputs["precursor_mz"]),
            str(inputs["adduct"]),
            float(inputs.get("measured_bias_ppm") or 0.0),
        )
    if name == "same":
        return same_molecule(str(inputs.get("smiles") or ""), str(inputs.get("other") or ""))
    known = ", ".join(row["name"] for row in OPERATIONS)
    raise KeyError(f"unknown chemistry set operation {operation!r}; known operations: {known}")
