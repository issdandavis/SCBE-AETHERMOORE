"""Science score for the chemistry crucible.

Math stays a separate score. These micro-points add up on their own, and the
science gate opens only when the sum reaches the threshold. The points use the
formula ledger already in chemistry_dimensions: atom counts, common-isotope
protons and neutrons, electrons from charge, and average molar mass. They do
not measure a dipole, a solvent density, or a 3D conformer.
"""

from __future__ import annotations

import re
from typing import Any

SCHEMA = "aethermoore_chemistry_science_score_v1"
THRESHOLD = 8

# Mass per atom from the average-weight ledger. These are bands, not g/cm^3.
DENSITY_BANDS = (
    {"name": "rarefied", "low": 0.0, "high": 3.0},
    {"name": "condensed", "low": 3.0, "high": 12.0},
    {"name": "dense", "low": 12.0, "high": None},
)

BOUNDARY = (
    "Science micro-points add to their own threshold. Math is not added into this sum. "
    "Neutron counts are common-isotope mass numbers. "
    "Density bands are mass per atom of that average ledger, not a measured medium. "
    "The existence circle is the dimension table. The reference circle is the compared formula. "
    "The gate sits in their intersection."
)


def _empty_ledger(formula: str, error: str) -> dict[str, Any]:
    return {
        "formula": formula,
        "exists": False,
        "error": error,
        "composition": {},
        "atom_count": 0,
        "valence_sum": None,
        "protons": None,
        "neutrons": None,
        "electrons": None,
        "charge": None,
        "charge_sign": None,
        "molar_mass_g_mol": None,
        "mass_per_atom": None,
        "density_band": None,
    }


def _charge_sign(charge: int) -> int:
    if charge > 0:
        return 1
    if charge < 0:
        return -1
    return 0


def _density_band(mass_per_atom: float) -> str:
    for band in DENSITY_BANDS:
        high = band["high"]
        if high is None or mass_per_atom < float(high):
            if mass_per_atom >= float(band["low"]):
                return str(band["name"])
    return str(DENSITY_BANDS[-1]["name"])


def ledger_from_terms(terms: list[tuple[int, str]]) -> dict[str, Any]:
    """Coefficient-weighted formula ledger. Unknown elements are non-existence."""
    from python.scbe.atomic_tokenization import PERIODIC_TABLE
    from python.scbe.chemistry_dimensions import ChemistryDimensionError, analyze_formula
    from python.scbe.reaction_balance import BalanceError, parse_formula

    composition: dict[str, int] = {}
    protons = neutrons = electrons = charge = 0
    mass = 0.0
    valence_sum = 0
    valence_known = True
    try:
        for coeff, formula in terms:
            if coeff <= 0:
                raise BalanceError(f"coefficient must be positive: {coeff} {formula}")
            row = analyze_formula(formula)
            parsed, parsed_charge = parse_formula(formula)
            for symbol, count in parsed.items():
                composition[symbol] = composition.get(symbol, 0) + coeff * int(count)
                element = PERIODIC_TABLE.get(symbol)
                if element is None:
                    valence_known = False
                else:
                    valence_sum += coeff * int(count) * int(element.valence)
            totals = row["totals"]
            protons += coeff * int(totals["protons"])
            neutrons += coeff * int(totals["neutrons_common_isotope"])
            electrons += coeff * int(totals["electrons"])
            charge += coeff * int(parsed_charge)
            mass += coeff * float(totals["molar_mass_g_mol"])
    except (BalanceError, ChemistryDimensionError, KeyError, ValueError) as exc:
        shown = " + ".join(formula if coeff == 1 else f"{coeff}{formula}" for coeff, formula in terms)
        return _empty_ledger(shown, str(exc))

    atom_count = sum(composition.values())
    mass_per_atom = mass / atom_count if atom_count else None
    shown = " + ".join(formula if coeff == 1 else f"{coeff}{formula}" for coeff, formula in terms)
    return {
        "formula": shown,
        "exists": True,
        "error": None,
        "composition": {symbol: composition[symbol] for symbol in sorted(composition)},
        "atom_count": atom_count,
        "valence_sum": valence_sum if valence_known else None,
        "protons": protons,
        "neutrons": neutrons,
        "electrons": electrons,
        "charge": charge,
        "charge_sign": _charge_sign(charge),
        "molar_mass_g_mol": round(mass, 6),
        "mass_per_atom": None if mass_per_atom is None else round(mass_per_atom, 6),
        "density_band": None if mass_per_atom is None else _density_band(mass_per_atom),
    }


def ledger_from_formula(formula: str) -> dict[str, Any]:
    return ledger_from_terms([(1, formula)])


def _terms(side: str) -> list[tuple[int, str]]:
    terms: list[tuple[int, str]] = []
    for part in side.split("+"):
        token = part.strip()
        if not token:
            continue
        match = re.match(r"^(\d+)?([A-Z\[(].+)$", token)
        if not match:
            raise ValueError(f"cannot read formula term {token!r}")
        coeff = int(match.group(1) or 1)
        terms.append((coeff, match.group(2)))
    if not terms:
        raise ValueError("equation side is empty")
    return terms


def product_terms(equation: str) -> list[tuple[int, str]]:
    parts = re.split(r"->|=>|=", str(equation).strip())
    if len(parts) != 2:
        raise ValueError("equation needs a reactant side and a product side")
    return _terms(parts[1])


def _point(name: str, point: int, note: str) -> dict[str, Any]:
    return {"name": name, "point": int(point), "note": note}


def _mediums(candidate: dict[str, Any], reference: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for band in DENSITY_BANDS:
        rows.append(
            {
                "name": band["name"],
                "low": band["low"],
                "high": band["high"],
                "candidate_inside": candidate.get("density_band") == band["name"],
                "reference_inside": reference.get("density_band") == band["name"],
                "candidate_protons": candidate.get("protons"),
                "candidate_neutrons": candidate.get("neutrons"),
                "candidate_electrons": candidate.get("electrons"),
                "reference_protons": reference.get("protons"),
                "reference_neutrons": reference.get("neutrons"),
                "reference_electrons": reference.get("electrons"),
            }
        )
    return rows


def _venn(candidate: dict[str, Any], reference: dict[str, Any], aligned: bool) -> dict[str, Any]:
    if not candidate.get("exists"):
        region = "nonexistence"
    elif aligned and reference.get("exists"):
        region = "intersection"
    else:
        region = "exists_only"
    return {
        "region": region,
        "candidate_exists": bool(candidate.get("exists")),
        "reference_exists": bool(reference.get("exists")),
        "reference_match": bool(aligned and reference.get("exists") and candidate.get("exists")),
        "existence": "The formula parses and every element is in the dimension table.",
        "nonexistence": "The formula does not parse or an element is outside that table.",
    }


def score_ledgers(
    candidate: dict[str, Any],
    reference: dict[str, Any],
    *,
    candidate_closed: bool | None = None,
    reference_closed: bool | None = None,
) -> dict[str, Any]:
    """Score one candidate ledger against one reference ledger."""
    compositions_equal = (
        candidate.get("exists")
        and reference.get("exists")
        and (candidate.get("composition") == reference.get("composition"))
    )
    charges_equal = compositions_equal and candidate.get("charge") == reference.get("charge")
    if candidate_closed is None and reference_closed is None:
        reaction_point = 1 if compositions_equal else 0
        reaction_note = "Formula pair: the atom delta is the whole effect."
    else:
        reaction_point = 1 if candidate_closed and reference_closed else 0
        reaction_note = "Reaction pair: both processes close. A closed effect can still be the wrong substance."
    valence_point = (
        1
        if compositions_equal
        and candidate.get("valence_sum") is not None
        and candidate.get("atom_count") == reference.get("atom_count")
        and candidate.get("valence_sum") == reference.get("valence_sum")
        else 0
    )
    polar_point = (
        1
        if candidate.get("exists")
        and reference.get("exists")
        and candidate.get("charge_sign") == reference.get("charge_sign")
        else 0
    )
    charge_point = (
        1
        if candidate.get("exists")
        and reference.get("exists")
        and candidate.get("protons") == reference.get("protons")
        and candidate.get("neutrons") == reference.get("neutrons")
        and candidate.get("electrons") == reference.get("electrons")
        else 0
    )
    density_point = (
        1
        if candidate.get("exists")
        and reference.get("exists")
        and candidate.get("density_band") is not None
        and candidate.get("density_band") == reference.get("density_band")
        else 0
    )
    points = [
        _point("atomic_alignment", 1 if compositions_equal else 0, "Element counts match."),
        _point(
            "decomposition_recomposition",
            1 if compositions_equal else 0,
            "Recomposition recovers the reference atom counts.",
        ),
        _point("reaction_effect", reaction_point, reaction_note),
        _point(
            "valence_and_atom_count",
            valence_point,
            "Atom count and the local valence sum match. Valence here is the table value, not a measured bond order.",
        ),
        _point(
            "polar_nucleus",
            polar_point,
            "Charge sign around the nucleus matches. Proton count is scored with the charge ledger.",
        ),
        _point(
            "charge_state",
            charge_point,
            "Protons, common-isotope neutrons, and electrons match.",
        ),
        _point(
            "density_medium",
            density_point,
            "Both sit in the same mass-per-atom band. The proton ledger is not shifted by the band.",
        ),
        _point(
            "existence_venn",
            1 if charges_equal else 0,
            "Point awarded only in the intersection of existence and the reference.",
        ),
    ]
    science_score = sum(point["point"] for point in points)
    failed = [point["name"] for point in points if point["point"] == 0]
    return {
        "schema_version": SCHEMA,
        "science_score": science_score,
        "threshold": THRESHOLD,
        "admitted": science_score >= THRESHOLD,
        "points": points,
        "failed": failed,
        "candidate": candidate,
        "reference": reference,
        "density_mediums": _mediums(candidate, reference),
        "venn": _venn(candidate, reference, charges_equal),
        "boundary": BOUNDARY,
    }


def score_formulas(candidate: str, reference: str) -> dict[str, Any]:
    """Science score for two formulas. Math is not included."""
    return score_ledgers(ledger_from_formula(candidate), ledger_from_formula(reference))


def score_equations(candidate: str, reference: str) -> dict[str, Any]:
    """Science score for two balanced equations, judged on the product side."""
    from python.scbe.reaction_balance import BalanceError, is_conserved

    def closed(equation: str) -> bool:
        parts = re.split(r"->|=>|=", equation.strip())
        if len(parts) != 2:
            return False
        try:
            reactants = _terms(parts[0])
            products = _terms(parts[1])
        except ValueError:
            return False
        try:
            ok, _deltas = is_conserved(reactants, products)
        except BalanceError:
            return False
        return bool(ok)

    try:
        candidate_ledger = ledger_from_terms(product_terms(candidate))
        reference_ledger = ledger_from_terms(product_terms(reference))
    except ValueError as exc:
        empty = _empty_ledger(candidate, str(exc))
        return score_ledgers(empty, empty, candidate_closed=False, reference_closed=False)
    return score_ledgers(
        candidate_ledger,
        reference_ledger,
        candidate_closed=closed(candidate),
        reference_closed=closed(reference),
    )
