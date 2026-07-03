"""Particle chemistry companion for the canonical Machine Crystal p/n/e cube.

This ports the two non-duplicate pieces into Codex's canonical geometry lane:

1. full-balancer wiring:
   exact atom+charge balancing from ``reaction_balance`` is projected into the
   p/n/e ledger, so balanced reactions produce proton/neutron/electron receipts.

2. valence rung:
   formulas are annotated with a compact valence profile from the existing
   periodic-token table. This is a routing/gating feature, not a chemical
   stability proof.

Honesty boundary:
    Exact stoichiometry and formula-level p/n/e accounting are real. Valence
    rungs are heuristic annotations. This is not thermodynamics, kinetics,
    synthesis advice, toxicity, or a complete chemistry engine.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Sequence

from .atomic_tokenization import PERIODIC_TABLE
from .chemistry_dimensions import analyze_formula
from .reaction_balance import BalanceError, balance, format_equation, is_conserved, parse_formula


class ParticleChemError(ValueError):
    """Invalid particle-chemistry balance or valence request."""


VALENCE_RUNG_NAMES = {
    0: "inert",
    1: "monovalent",
    2: "divalent",
    3: "trivalent",
    4: "tetravalent",
}


@dataclass(frozen=True, slots=True)
class CoefficientedFormula:
    coefficient: int
    formula: str

    def packet(self) -> dict:
        return {"coefficient": self.coefficient, "formula": self.formula}


def valence_rung(value: int) -> str:
    value = int(value)
    return VALENCE_RUNG_NAMES.get(value, "polyvalent")


def formula_valence_profile(formula: str) -> dict:
    """Return deterministic valence annotations for a formula."""

    counts, charge = parse_formula(formula)
    entries = []
    total_slots = 0
    max_valence = 0
    missing = []
    for symbol in sorted(counts):
        element = PERIODIC_TABLE.get(symbol)
        if element is None:
            missing.append(symbol)
            continue
        count = int(counts[symbol])
        contribution = count * int(element.valence)
        total_slots += contribution
        max_valence = max(max_valence, int(element.valence))
        entries.append(
            {
                "symbol": symbol,
                "count": count,
                "valence": int(element.valence),
                "rung": valence_rung(int(element.valence)),
                "group": int(element.group),
                "period": int(element.period),
                "slot_contribution": contribution,
            }
        )
    known = not missing
    return {
        "formula": formula,
        "charge": int(charge),
        "entries": entries,
        "missing_elements": missing,
        "known_elements": known,
        "total_valence_slots": total_slots,
        "total_valence_slots_even": (total_slots % 2 == 0),
        "max_valence": max_valence,
        "max_valence_rung": valence_rung(max_valence),
        "claim_boundary": "valence rung is a routing heuristic, not a stability proof",
    }


def _scale_totals(totals: dict, coeff: int) -> dict:
    return {
        "atoms": int(totals["atoms"]) * coeff,
        "protons": int(totals["protons"]) * coeff,
        "neutrons_common_isotope": int(totals["neutrons_common_isotope"]) * coeff,
        "electrons": int(totals["electrons"]) * coeff,
        "mass_number_common_isotope": int(totals["mass_number_common_isotope"]) * coeff,
        "molar_mass_g_mol": round(float(totals["molar_mass_g_mol"]) * coeff, 6),
        "charge": int(totals["charge"]) * coeff,
    }


def _side_particle_totals(coefficiented: Sequence[CoefficientedFormula]) -> dict:
    combined = {
        "atoms": 0,
        "protons": 0,
        "neutrons_common_isotope": 0,
        "electrons": 0,
        "mass_number_common_isotope": 0,
        "molar_mass_g_mol": 0.0,
        "charge": 0,
    }
    rows = []
    for item in coefficiented:
        analysis = analyze_formula(item.formula)
        scaled = _scale_totals(analysis["totals"], item.coefficient)
        rows.append({"coefficient": item.coefficient, "formula": item.formula, "scaled_totals": scaled})
        for key in combined:
            combined[key] += scaled[key]
    combined["molar_mass_g_mol"] = round(combined["molar_mass_g_mol"], 6)
    return {"rows": rows, "combined": combined}


def balance_on_pne_cube(reactants: Sequence[str], products: Sequence[str]) -> dict:
    """Balance formulas and project the result into a p/n/e conservation receipt."""

    coeffs = balance(reactants, products)
    nr = len(reactants)
    left = [CoefficientedFormula(c, f) for c, f in zip(coeffs[:nr], reactants)]
    right = [CoefficientedFormula(c, f) for c, f in zip(coeffs[nr:], products)]
    conserved, deltas = is_conserved(
        [(item.coefficient, item.formula) for item in left],
        [(item.coefficient, item.formula) for item in right],
    )
    left_totals = _side_particle_totals(left)
    right_totals = _side_particle_totals(right)
    particle_keys = ("protons", "neutrons_common_isotope", "electrons", "charge", "mass_number_common_isotope")
    particle_checks = {
        key: left_totals["combined"][key] == right_totals["combined"][key]
        for key in particle_keys
    }
    valence_profiles = [formula_valence_profile(formula) for formula in [*reactants, *products]]
    return {
        "reactants": list(reactants),
        "products": list(products),
        "coefficients": list(coeffs),
        "equation": format_equation(coeffs, reactants, products),
        "atom_charge_conserved": conserved,
        "deltas": deltas,
        "left_particle_totals": left_totals,
        "right_particle_totals": right_totals,
        "particle_checks": particle_checks,
        "valence_profiles": valence_profiles,
        "accepted": conserved and all(particle_checks.values()) and all(v["known_elements"] for v in valence_profiles),
    }


def particle_chem_receipt() -> dict:
    """Run deterministic balancer+valence checks."""

    balanced_cases = [
        {
            "name": "water_synthesis",
            "reactants": ["H2", "O2"],
            "products": ["H2O"],
            "expected_coefficients": [2, 1, 2],
        },
        {
            "name": "methane_combustion",
            "reactants": ["CH4", "O2"],
            "products": ["CO2", "H2O"],
            "expected_coefficients": [1, 2, 1, 2],
        },
        {
            "name": "ionic_salt_pair",
            "reactants": ["Na+", "Cl-"],
            "products": ["NaCl"],
            "expected_coefficients": [1, 1, 1],
        },
    ]

    balanced_results = []
    for case in balanced_cases:
        result = balance_on_pne_cube(case["reactants"], case["products"])
        result["name"] = case["name"]
        result["expected_coefficients"] = case["expected_coefficients"]
        result["coefficients_match_expected"] = result["coefficients"] == case["expected_coefficients"]
        balanced_results.append(result)

    invalid_cases = []
    for case in [{"name": "oxygen_from_nowhere", "reactants": ["H2"], "products": ["H2O"]}]:
        try:
            result = balance_on_pne_cube(case["reactants"], case["products"])
            invalid_cases.append({**case, "rejected": False, "unexpected_result": result})
        except BalanceError as exc:
            invalid_cases.append({**case, "rejected": True, "error": str(exc)})

    valence_samples = {
        formula: formula_valence_profile(formula)
        for formula in ["H2O", "CO2", "CH4", "NaCl", "O2"]
    }

    checks = {
        "balanced_cases_accept": all(item["accepted"] for item in balanced_results),
        "coefficients_match_expected": all(item["coefficients_match_expected"] for item in balanced_results),
        "particle_ledgers_balance": all(all(item["particle_checks"].values()) for item in balanced_results),
        "valence_profiles_known": all(profile["known_elements"] for profile in valence_samples.values()),
        "valence_even_for_samples": all(profile["total_valence_slots_even"] for profile in valence_samples.values()),
        "invalid_case_rejected": all(item["rejected"] for item in invalid_cases),
    }

    return {
        "schema": "scbe_machine_crystal_particle_chem_v1",
        "claim": "Exact reaction balancing can feed the canonical p/n/e cube, while valence rungs annotate formulas as a bounded routing feature.",
        "balanced_results": balanced_results,
        "invalid_cases": invalid_cases,
        "valence_samples": valence_samples,
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "honest_boundary": "Exact stoichiometry and formula p/n/e ledgers only; valence rungs are heuristic annotations, not stability or feasibility claims.",
    }


def main() -> int:
    receipt = particle_chem_receipt()
    out_dir = Path("artifacts/machine_crystal")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "particle_chem.json"
    out_path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["verdict"] == "PASS" else 1


__all__ = [
    "ParticleChemError",
    "balance_on_pne_cube",
    "formula_valence_profile",
    "particle_chem_receipt",
    "valence_rung",
]


if __name__ == "__main__":
    raise SystemExit(main())
