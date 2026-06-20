"""First-class chemistry dimensional analysis.

This is the cheap, honest chemistry action: parse a formula, count atoms, and
derive the subatomic ledger (protons, neutrons, electrons, charge, mass number).
It is useful for formula checks, reaction accounting, and AI tool use because the
result is deterministic and easy to verify. It is not a molecular dynamics,
toxicity, synthesis, thermodynamics, or bioactivity engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping

from .reaction_balance import parse_formula


class ChemistryDimensionError(ValueError):
    """Raised when dimensional chemistry cannot account for a formula."""


@dataclass(frozen=True)
class ElementDimension:
    symbol: str
    atomic_number: int
    mass_number: int
    atomic_weight: float

    @property
    def common_neutrons(self) -> int:
        return self.mass_number - self.atomic_number


# Common biology/materials elements plus the early periodic table. Mass numbers
# are the most common stable isotope (or longest-lived/common teaching isotope
# where appropriate); atomic weights are standard average weights for molar-mass
# estimates. Keep this small and auditable instead of pretending to be NIST.
ELEMENTS: Mapping[str, ElementDimension] = {
    "H": ElementDimension("H", 1, 1, 1.008),
    "He": ElementDimension("He", 2, 4, 4.0026),
    "Li": ElementDimension("Li", 3, 7, 6.94),
    "Be": ElementDimension("Be", 4, 9, 9.0122),
    "B": ElementDimension("B", 5, 11, 10.81),
    "C": ElementDimension("C", 6, 12, 12.011),
    "N": ElementDimension("N", 7, 14, 14.007),
    "O": ElementDimension("O", 8, 16, 15.999),
    "F": ElementDimension("F", 9, 19, 18.998),
    "Ne": ElementDimension("Ne", 10, 20, 20.180),
    "Na": ElementDimension("Na", 11, 23, 22.990),
    "Mg": ElementDimension("Mg", 12, 24, 24.305),
    "Al": ElementDimension("Al", 13, 27, 26.982),
    "Si": ElementDimension("Si", 14, 28, 28.085),
    "P": ElementDimension("P", 15, 31, 30.974),
    "S": ElementDimension("S", 16, 32, 32.06),
    "Cl": ElementDimension("Cl", 17, 35, 35.45),
    "Ar": ElementDimension("Ar", 18, 40, 39.948),
    "K": ElementDimension("K", 19, 39, 39.098),
    "Ca": ElementDimension("Ca", 20, 40, 40.078),
    "Fe": ElementDimension("Fe", 26, 56, 55.845),
    "Co": ElementDimension("Co", 27, 59, 58.933),
    "Cu": ElementDimension("Cu", 29, 63, 63.546),
    "Zn": ElementDimension("Zn", 30, 64, 65.38),
    "Se": ElementDimension("Se", 34, 80, 78.971),
    "Br": ElementDimension("Br", 35, 79, 79.904),
    "I": ElementDimension("I", 53, 127, 126.904),
}

CLAIM_BOUNDARY = [
    "formula-level dimensional accounting only",
    "neutron counts use common isotope mass numbers, not isotope-resolved samples",
    "molar mass is an average-weight estimate",
    "not a thermodynamics, kinetics, synthesis, toxicity, or bioactivity claim",
]


def element_dimension(symbol: str) -> ElementDimension:
    """Return the dimensional row for an element symbol."""

    try:
        return ELEMENTS[symbol]
    except KeyError as exc:
        raise ChemistryDimensionError(
            f"element {symbol!r} is not in the local chemistry dimension table"
        ) from exc


def analyze_formula(formula: str) -> dict:
    """Analyze a chemical formula into atom/subatomic dimensional totals."""

    counts, charge = parse_formula(formula)
    atoms: Dict[str, dict] = {}
    totals = {
        "atoms": 0,
        "protons": 0,
        "neutrons_common_isotope": 0,
        "electrons": 0,
        "mass_number_common_isotope": 0,
        "molar_mass_g_mol": 0.0,
        "charge": int(charge),
    }
    for symbol in sorted(counts):
        count = int(counts[symbol])
        dim = element_dimension(symbol)
        protons = dim.atomic_number * count
        neutrons = dim.common_neutrons * count
        mass_number = dim.mass_number * count
        molar_mass = dim.atomic_weight * count
        atoms[symbol] = {
            "count": count,
            "atomic_number": dim.atomic_number,
            "mass_number_common_isotope": dim.mass_number,
            "protons": protons,
            "neutrons_common_isotope": neutrons,
            "electrons_neutral": protons,
            "molar_mass_g_mol": round(molar_mass, 6),
        }
        totals["atoms"] += count
        totals["protons"] += protons
        totals["neutrons_common_isotope"] += neutrons
        totals["mass_number_common_isotope"] += mass_number
        totals["molar_mass_g_mol"] += molar_mass
    totals["electrons"] = totals["protons"] - charge
    totals["molar_mass_g_mol"] = round(totals["molar_mass_g_mol"], 6)
    return {
        "schema_version": "scbe_chemistry_dimensions_v1",
        "formula": formula,
        "atoms": atoms,
        "totals": totals,
        "claim_boundary": list(CLAIM_BOUNDARY),
    }


def analyze_many(formulas: list[str]) -> dict:
    """Analyze several formulas and return a combined ledger."""

    rows = [analyze_formula(formula) for formula in formulas]
    combined = {
        "atoms": 0,
        "protons": 0,
        "neutrons_common_isotope": 0,
        "electrons": 0,
        "mass_number_common_isotope": 0,
        "molar_mass_g_mol": 0.0,
        "charge": 0,
    }
    for row in rows:
        for key in combined:
            combined[key] += row["totals"][key]
    combined["molar_mass_g_mol"] = round(combined["molar_mass_g_mol"], 6)
    return {
        "schema_version": "scbe_chemistry_dimensions_batch_v1",
        "formulas": formulas,
        "rows": rows,
        "combined_totals": combined,
        "claim_boundary": list(CLAIM_BOUNDARY),
    }
