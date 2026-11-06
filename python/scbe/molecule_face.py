"""Real-molecule and spectrum records for the atomic tokenizer and STISA.

The linguistic map from a word to an element stays in atomic_tokenization.
This module reads a SMILES string, or a precursor m/z plus an adduct, into one
record other systems can call. Exact mass is RDKit's monoisotopic mass.
Identity strips stereo, canonicalizes the tautomer, then keeps the InChIKey.
Average molar mass is not used. A measured precursor bias stays off unless
the caller passes it.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

# Same eight positions as src/tokenizer/code_weight_packets.FIELD_DEFINITIONS.
# On a molecule row the numbers are the real element, tongue_id is 0 because
# the row is not a tongue opcode, and reserved holds that element's atom count.
STISA_SLOTS = (
    "Z_proxy",
    "group_proxy",
    "period_proxy",
    "valence_proxy",
    "chi_proxy",
    "band_flag",
    "tongue_id",
    "reserved",
)

# name, ion SMILES, sign of the ion mass, charge of the observed ion.
# Delta is sign * ExactMolWt(ion). Charge magnitude is 1 for every row.
# [M-H]- uses the proton mass with a minus sign. Multimers are absent on
# purpose: an unknown name raises KeyError instead of a silent wrong mass.
_ADDUCT_IONS = (
    ("[M+H]+", "[H+]", 1, 1),
    ("[M+Na]+", "[Na+]", 1, 1),
    ("[M+K]+", "[K+]", 1, 1),
    ("[M+NH4]+", "[NH4+]", 1, 1),
    ("[M-H]-", "[H+]", -1, -1),
    ("[M+Cl]-", "[Cl-]", 1, -1),
    ("[M+CH2O2-H]-", "[O-]C=O", 1, -1),
)

BOUNDARY = (
    "Monoisotopic RDKit exact mass and adduct arithmetic. "
    "Average molar mass stays in chemistry_dimensions. "
    "A caller that ranks structures from peaks uses this record as input."
)

MOLECULE_SCHEMA = "scbe-stisa-molecule-v1"
SPECTRUM_SCHEMA = "scbe-stisa-spectrum-v1"


def _rdkit() -> dict[str, Any]:
    cached = getattr(_rdkit, "value", None)
    if cached is not None:
        return cached
    import rdkit
    from rdkit import Chem, RDLogger
    from rdkit.Chem import Descriptors, rdMolDescriptors
    from rdkit.Chem.MolStandardize import rdMolStandardize

    RDLogger.DisableLog("rdApp.*")
    cached = {
        "Chem": Chem,
        "Descriptors": Descriptors,
        "rdMolDescriptors": rdMolDescriptors,
        "enumerator": rdMolStandardize.TautomerEnumerator(),
        "version": rdkit.__version__,
    }
    _rdkit.value = cached
    return cached


def _exact_mass(smiles: str) -> float:
    chem = _rdkit()["Chem"]
    descriptors = _rdkit()["Descriptors"]
    molecule = chem.MolFromSmiles(smiles)
    if molecule is None:
        raise RuntimeError(f"RDKit could not parse adduct ion {smiles!r}")
    return float(descriptors.ExactMolWt(molecule))


def _adduct_table() -> dict[str, dict[str, float | int]]:
    cached = getattr(_adduct_table, "value", None)
    if cached is not None:
        return cached
    table: dict[str, dict[str, float | int]] = {}
    for name, ion, sign, charge in _ADDUCT_IONS:
        table[name] = {
            "delta": int(sign) * _exact_mass(ion),
            "charge": int(charge),
        }
    _adduct_table.value = table
    return table


def known_adducts() -> tuple[str, ...]:
    """Adduct names this reader can turn into a neutral mass."""
    return tuple(name for name, _ion, _sign, _charge in _ADDUCT_IONS)


def adduct_delta(adduct: str) -> float:
    """Monoisotopic mass added to the neutral to produce the measured ion."""
    try:
        row = _adduct_table()[adduct]
    except KeyError as exc:
        known = ", ".join(known_adducts())
        raise KeyError(f"unknown adduct {adduct!r}; known adducts: {known}") from exc
    return float(row["delta"])


def correct_bias(mass: float, measured_bias_ppm: float = 0.0) -> float:
    """Undo a relative bias on a mass that came from a measured precursor.

    Zero leaves the mass unchanged. A positive bias means the measurement
    reads high. Dividing removes that fraction. Nothing here applies a
    default instrument offset.
    """
    ppm = float(measured_bias_ppm)
    if ppm == 0.0:
        return float(mass)
    return float(mass) / (1.0 + ppm * 1e-6)


def neutral_mass(precursor_mz: float, adduct: str, measured_bias_ppm: float = 0.0) -> float:
    """Neutral monoisotopic mass implied by one precursor peak."""
    return correct_bias(float(precursor_mz) - adduct_delta(adduct), measured_bias_ppm)


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise TypeError(f"{name} must be a number")
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _float_list(values: Sequence[Any], name: str) -> list[float]:
    try:
        sequence = list(values)
    except TypeError as exc:
        raise TypeError(f"{name} must be a sequence of numbers") from exc
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} must be a sequence of numbers")
    return [_finite(item, name) for item in sequence]


def _optional_floats(values: Any, name: str) -> list[float] | None:
    if values is None:
        return None
    if isinstance(values, (int, float)) and not isinstance(values, bool):
        return [_finite(values, name)]
    return _float_list(values, name)


def _parse_smiles(smiles: str):
    if not isinstance(smiles, str):
        raise TypeError("smiles must be a string")
    text = smiles.strip()
    if not text:
        raise ValueError("smiles is empty")
    chem = _rdkit()["Chem"]
    molecule = chem.MolFromSmiles(text)
    if molecule is None:
        raise ValueError(f"RDKit could not parse SMILES: {text}")
    return text, molecule


def _identity(molecule) -> tuple[str, str, str]:
    chem = _rdkit()["Chem"]
    enumerator = _rdkit()["enumerator"]
    copied = chem.Mol(molecule)
    chem.RemoveStereochemistry(copied)
    try:
        canonical = enumerator.Canonicalize(copied)
    except (ValueError, RuntimeError, TypeError) as exc:
        raise ValueError(f"could not canonicalize SMILES: {exc}") from exc
    if canonical is None:
        raise ValueError("could not canonicalize SMILES")
    inchikey = chem.MolToInchiKey(canonical)
    if not inchikey or len(inchikey) < 14:
        raise ValueError("could not build an InChIKey")
    identity_smiles = chem.MolToSmiles(canonical, canonical=True)
    return inchikey, inchikey[:14], identity_smiles


def _atom_rows(molecule) -> tuple[list[dict[str, Any]], dict[str, int], str]:
    from python.scbe.atomic_tokenization import PERIODIC_TABLE, element_to_trit_vector

    chem = _rdkit()["Chem"]
    filled = chem.AddHs(molecule)
    counts: dict[str, int] = {}
    atomic_numbers: dict[str, int] = {}
    for atom in filled.GetAtoms():
        symbol = atom.GetSymbol()
        counts[symbol] = counts.get(symbol, 0) + 1
        atomic_numbers[symbol] = int(atom.GetAtomicNum())

    rows: list[dict[str, Any]] = []
    for symbol in sorted(counts, key=lambda item: (atomic_numbers[item], item)):
        count = counts[symbol]
        atomic_number = atomic_numbers[symbol]
        element = PERIODIC_TABLE.get(symbol)
        if element is None:
            vector: list[float | None] = [float(atomic_number), None, None, None, None, None, 0.0, float(count)]
            rows.append(
                {
                    "symbol": symbol,
                    "count": count,
                    "Z": atomic_number,
                    "group": None,
                    "period": None,
                    "valence": None,
                    "chi": None,
                    "witness_stable": None,
                    "table": "rdkit-only",
                    "feature_vector": vector,
                    "trit": None,
                }
            )
            continue
        band = 0.0 if element.witness_stable else 1.0
        trit = {tongue: int(value) for tongue, value in element_to_trit_vector(element).as_dict().items()}
        rows.append(
            {
                "symbol": symbol,
                "count": count,
                "Z": int(element.Z),
                "group": int(element.group),
                "period": int(element.period),
                "valence": int(element.valence),
                "chi": float(element.electronegativity),
                "witness_stable": bool(element.witness_stable),
                "table": "periodic",
                "feature_vector": [
                    float(element.Z),
                    float(element.group),
                    float(element.period),
                    float(element.valence),
                    float(element.electronegativity),
                    band,
                    0.0,
                    float(count),
                ],
                "trit": trit,
            }
        )
    composition = {symbol: counts[symbol] for symbol in sorted(counts)}
    formula = _rdkit()["rdMolDescriptors"].CalcMolFormula(molecule)
    return rows, composition, formula


def read_molecule(smiles: str) -> dict[str, Any]:
    """Read one SMILES string as a real molecule.

    The linguistic classifier is not consulted. Hydrogen is included in
    ``composition`` and omitted from ``heavy_atom_composition``. An element
    missing from the local periodic table keeps its atomic number and leaves
    group, period, valence, and electronegativity empty.
    """
    text, molecule = _parse_smiles(smiles)
    descriptors = _rdkit()["Descriptors"]
    inchikey, inchikey14, identity_smiles = _identity(molecule)
    atoms, composition, formula = _atom_rows(molecule)
    heavy = {symbol: count for symbol, count in composition.items() if symbol != "H"}
    formal_charge = int(sum(atom.GetFormalCharge() for atom in molecule.GetAtoms()))
    return {
        "schema_version": MOLECULE_SCHEMA,
        "role": "molecule",
        "smiles": text,
        "identity_smiles": identity_smiles,
        "inchikey": inchikey,
        "inchikey14": inchikey14,
        "formula": formula,
        "exact_mass": float(descriptors.ExactMolWt(molecule)),
        "mass_basis": "exact_mol_wt",
        "formal_charge": formal_charge,
        "composition": composition,
        "heavy_atom_composition": heavy,
        "atoms": atoms,
        "field_definitions": [{"name": name} for name in STISA_SLOTS],
        "rdkit_version": _rdkit()["version"],
        "boundary": BOUNDARY,
    }


def read_spectrum(
    precursor_mz: float,
    adduct: str,
    *,
    smiles: str | None = None,
    measured_bias_ppm: float = 0.0,
    ms2_mzs: Sequence[float] | None = None,
    ms2_intensities: Sequence[float] | None = None,
    collision_energy_ev: float | Sequence[float] | None = None,
    ionization_mode: str | None = None,
    spectrum_id: str | None = None,
    instrument_type: str | None = None,
) -> dict[str, Any]:
    """Read one precursor peak as a spectrum record.

    ``measured_bias_ppm`` defaults to 0, and the neutral mass is then
    precursor_mz minus the adduct delta. Peak arrays must be the same length
    when both are given. A molecule is attached only when ``smiles`` is given.
    """
    precursor = _finite(precursor_mz, "precursor_mz")
    bias = _finite(measured_bias_ppm, "measured_bias_ppm")
    if (ms2_mzs is None) != (ms2_intensities is None):
        raise ValueError("ms2_mzs and ms2_intensities must be given together")
    peaks = _float_list(ms2_mzs, "ms2_mzs") if ms2_mzs is not None else None
    intensities = _float_list(ms2_intensities, "ms2_intensities") if ms2_intensities is not None else None
    if peaks is not None and intensities is not None and len(peaks) != len(intensities):
        raise ValueError("ms2_mzs and ms2_intensities must have the same length")
    try:
        row = _adduct_table()[adduct]
    except KeyError as exc:
        known = ", ".join(known_adducts())
        raise KeyError(f"unknown adduct {adduct!r}; known adducts: {known}") from exc
    molecule = None if smiles is None else read_molecule(smiles)
    return {
        "schema_version": SPECTRUM_SCHEMA,
        "role": "spectrum",
        "spectrum_id": spectrum_id,
        "adduct": adduct,
        "adduct_delta": float(row["delta"]),
        "charge": int(row["charge"]),
        "precursor_mz": precursor,
        "measured_bias_ppm": bias,
        "neutral_mass": correct_bias(precursor - float(row["delta"]), bias),
        "ionization_mode": ionization_mode,
        "instrument_type": instrument_type,
        "collision_energy_ev": _optional_floats(collision_energy_ev, "collision_energy_ev"),
        "ms2_mzs": peaks,
        "ms2_intensities": intensities,
        "num_peaks": None if peaks is None else len(peaks),
        "molecule": molecule,
        "field_definitions": [{"name": name} for name in STISA_SLOTS],
        "rdkit_version": _rdkit()["version"],
        "boundary": BOUNDARY,
    }
