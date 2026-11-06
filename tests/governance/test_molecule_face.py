"""Real-molecule and spectrum doors on the atomic tokenizer and STISA."""

import subprocess
import sys
from pathlib import Path

import pytest

from python.scbe.atomic_tokenization import map_token_to_element, read_molecule, read_spectrum
from python.scbe.molecule_face import STISA_SLOTS, adduct_delta
from src.tokenizer.code_weight_packets import (
    FIELD_DEFINITIONS,
    resolve_element,
    stisa_molecule,
    stisa_spectrum,
)

ROOT = Path(__file__).resolve().parents[2]
GLUCOSE_STEREO = "OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O"
GLUCOSE_FLAT = "OCC1OC(O)C(O)C(O)C1O"
STEREO_DRAWN = "C=C(C)[C@@H]1CCC2CCC(=O)C=C2C1"
STEREO_FLAT = "C=C(C)C1CCC2CCC(=O)C=C2C1"


def test_glucose_drawings_share_the_inchikey_block():
    stereo = read_molecule(GLUCOSE_STEREO)
    flat = read_molecule(GLUCOSE_FLAT)

    assert stereo["inchikey14"] == flat["inchikey14"] == "WQZGKKKJIJFFOK"
    assert len(stereo["inchikey"]) == 27
    assert stereo["role"] == "molecule"
    assert "semantic_class" not in stereo
    assert all("semantic_class" not in row for row in stereo["atoms"])


def test_stereo_strip_keeps_one_identity():
    assert read_molecule(STEREO_DRAWN)["inchikey14"] == read_molecule(STEREO_FLAT)["inchikey14"]


def test_ethanol_exact_mass_and_heavy_composition():
    record = read_molecule("CCO")

    assert abs(record["exact_mass"] - 46.041865) < 5e-4
    assert abs(record["exact_mass"] - 46.041865) < abs(record["exact_mass"] - 46.06844)
    assert record["heavy_atom_composition"] == {"C": 2, "O": 1}
    assert "H" in record["formula"]
    assert record["composition"]["H"] == 6
    assert record["mass_basis"] == "exact_mol_wt"
    assert "Fe" not in record["composition"]


def test_linguistic_word_still_maps_to_sodium():
    assert map_token_to_element("run").symbol == "Na"


def test_stisa_molecule_uses_real_atoms():
    record = stisa_molecule("CCO")
    carbon = next(row for row in record["atoms"] if row["symbol"] == "C")

    assert record["schema_version"] == "scbe-stisa-molecule-v1"
    assert record["role"] == "molecule"
    assert record["schema_version"] != "scbe-stisa-chemical-composition-v1"
    assert len(carbon["feature_vector"]) == 8
    assert carbon["feature_vector"][0] == 6
    assert carbon["Z"] == 6
    assert carbon["feature_vector"][6] == 0.0
    assert carbon["feature_vector"][7] == 2
    assert carbon["table"] == "periodic"
    assert set(carbon["trit"]) == {"KO", "AV", "RU", "CA", "UM", "DR"}
    assert record["composition"]["C"] == 2
    assert "Fe" not in record["composition"]
    assert [item["name"] for item in record["field_definitions"]] == list(STISA_SLOTS)
    assert [item["name"] for item in FIELD_DEFINITIONS] == list(STISA_SLOTS)
    assert record["inchikey14"] == read_molecule("CCO")["inchikey14"]

    linguistic = resolve_element("return")
    assert linguistic["symbol"] == "C"
    assert linguistic["feat"][6] == 1.0
    assert linguistic["feat"][7] == 0.0
    assert resolve_element("widget")["symbol"] == "Fe"


def test_element_outside_the_local_table_stays_unfilled():
    record = read_molecule("C[Se]C")
    selenium = next(row for row in record["atoms"] if row["symbol"] == "Se")

    assert selenium["Z"] == 34
    assert selenium["table"] == "rdkit-only"
    assert selenium["chi"] is None
    assert selenium["group"] is None
    assert selenium["trit"] is None
    assert selenium["feature_vector"][0] == 34
    assert "Fe" not in record["composition"]
    assert "Se" in record["composition"]


def test_proton_mass_is_the_ion_not_the_atom():
    proton = adduct_delta("[M+H]+")

    assert abs(proton - 1.007276) < 1e-5
    assert abs(proton - 1.007825) > 1e-4


def test_ethanol_proton_adduct_round_trips():
    molecule = read_molecule("CCO")
    precursor = molecule["exact_mass"] + adduct_delta("[M+H]+")
    spectrum = read_spectrum(precursor, "[M+H]+", smiles="CCO", collision_energy_ev=[20, 40])

    assert spectrum["neutral_mass"] == pytest.approx(molecule["exact_mass"], abs=1e-9)
    assert spectrum["molecule"]["inchikey14"] == molecule["inchikey14"]
    assert spectrum["charge"] == 1
    ppm = (spectrum["neutral_mass"] - molecule["exact_mass"]) / molecule["exact_mass"] * 1e6
    assert abs(ppm) < 1e-6
    biased = read_spectrum(precursor, "[M+H]+", measured_bias_ppm=10)
    assert biased["neutral_mass"] == pytest.approx(spectrum["neutral_mass"] / 1.00001, rel=1e-12)
    assert biased["molecule"] is None


def test_unknown_adduct_names_the_known_set():
    with pytest.raises(KeyError, match=r"unknown adduct '\[2M\+H\]\+'"):
        read_spectrum(100.0, "[2M+H]+")


def test_spectrum_without_smiles_has_neutral_mass_and_no_molecule():
    proton = adduct_delta("[M+H]+")
    spectrum = stisa_spectrum(100.0, "[M+H]+", ms2_mzs=[50.0, 80.0], ms2_intensities=[0.2, 1.0])

    assert spectrum["role"] == "spectrum"
    assert spectrum["schema_version"] == "scbe-stisa-spectrum-v1"
    assert spectrum["molecule"] is None
    assert spectrum["neutral_mass"] == pytest.approx(100.0 - proton, abs=1e-9)
    assert spectrum["num_peaks"] == 2


def test_peak_arrays_must_match():
    with pytest.raises(ValueError, match="same length"):
        read_spectrum(100.0, "[M+H]+", ms2_mzs=[1.0, 2.0], ms2_intensities=[1.0])


def test_importing_the_readers_does_not_import_rdkit():
    script = r"""
import importlib.util
import sys
from pathlib import Path

root = Path(sys.argv[1])

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

atomic = load("atomic_lazy_check", root / "python" / "scbe" / "atomic_tokenization.py")
packets = load("stisa_lazy_check", root / "src" / "tokenizer" / "code_weight_packets.py")
assert "rdkit" not in sys.modules
assert callable(atomic.read_molecule)
assert callable(atomic.read_spectrum)
assert callable(packets.stisa_molecule)
assert callable(packets.stisa_spectrum)
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(ROOT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
