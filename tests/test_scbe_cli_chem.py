import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCBE = REPO_ROOT / "scbe.py"


def run_scbe(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCBE), *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        timeout=40,
        check=False,
    )


def test_chem_atomize_exposes_atomic_token_states() -> None:
    result = run_scbe("chem", "atomize", "release payload after compare", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "scbe_chem_atomize_v1"
    assert payload["token_count"] == 4
    assert payload["tokens"] == ["release", "payload", "after", "compare"]
    assert {"tau_hat", "reconstruction_votes"} <= set(payload["fusion"])
    assert {"token", "semantic_class", "element", "tau"} <= set(payload["states"][0])
    assert "wet-lab" in payload["claim_boundary"]


def test_chem_bonds_exposes_sacred_tongue_molecule_report() -> None:
    result = run_scbe(
        "chem",
        "bonds",
        "0.1",
        "0.15",
        "0.2",
        "0.12",
        "0.14",
        "0.16",
        "--json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "scbe_chem_bonds_v1"
    assert payload["tongues"] == ["KO", "AV", "RU", "CA", "UM", "DR"]
    assert len(payload["bonds"]) == 3
    assert payload["dominant_class"] in {"SAFE", "CAUTIOUS", "SUSPICIOUS", "HOSTILE"}


def test_chem_convert_uses_rdkit_adapter() -> None:
    result = run_scbe(
        "chem",
        "convert",
        "--smiles",
        "CCO",
        "--to",
        "can",
        "--engine",
        "rdkit",
        "--json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "scbe_chem_convert_v1"
    assert payload["engine"] == "rdkit"
    assert payload["output"] == "CCO"
    assert payload["descriptors"]["mol_wt"] == 46.069


def test_chem_convert_uses_openbabel_adapter() -> None:
    result = run_scbe(
        "chem",
        "convert",
        "--smiles",
        "CCO",
        "--to",
        "can",
        "--engine",
        "openbabel",
        "--json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "scbe_chem_convert_v1"
    assert payload["engine"] == "openbabel"
    assert payload["output"] == "CCO"


def test_chem_orbitals_exposes_geoseed_summary() -> None:
    result = run_scbe("chem", "orbitals", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "geoseed_orbital_v1"
    assert payload["total_m_states"] == 36
    assert payload["golden_ratio_checkpoint"]["exact"] is True
    assert "claim_boundary" in payload


def test_chem_map_semantics_classifies_known_operation() -> None:
    result = run_scbe(
        "chem",
        "map-semantics",
        "--operation",
        "release",
        "--chemical-analogue",
        "dissociation",
        "--json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "scbe_chem_semantic_map_v1"
    assert payload["operation"] == "release"
    assert payload["accepted"] is True
    assert payload["line_type"] == "shared_operation"
