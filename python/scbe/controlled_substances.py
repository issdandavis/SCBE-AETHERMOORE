"""Controlled-substance screen — defensive refusal lane for SMILES/CAS inputs.

Modeled on the published ControlChemCheck safety tool from ChemCrow
(Bran, Cox, Schilter, Baldassari, White, Schwaller; ur-whitelab/chemcrow-public,
MIT license). The screening list (``data/chem_wep_smi.csv``) is vendored
verbatim from that project: CAS numbers and SMILES of chemicals controlled
under international chemical-weapons schedules (OPCW / Australia Group
sources, per the upstream ``source`` column).

DEFENSIVE ONLY: this module flags and refuses. It never synthesizes,
suggests analogues, or expands the list, and screen reports never name the
matched entry — only that a match occurred and how.

Screen levels (honest degradation, recorded in every report):
- ``exact_string`` (stdlib, always on): exact CAS-number and raw-SMILES match.
- ``canonical`` (RDKit): canonical-SMILES equality catches alternate
  renderings of the same molecule.
- ``similarity`` (RDKit): Tanimoto > 0.35 over Morgan fingerprints flags
  close analogues — the published ControlChemCheck threshold.

Two-tier outcome (mirrors the L13 DENY/QUARANTINE split): exact and canonical
matches REFUSE; similarity flags are WITNESSED in the receipt rather than
refused. Measured rationale (scripts/eval/controlled_substance_screen_eval.py):
at the published 0.35 threshold, common solvents flag (acetone 0.45,
acetic acid 0.42), so refusal at that tier would break benign computation
while the witnessed flag preserves the audit trail.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

SCREEN_SCHEMA_VERSION = "scbe_controlled_substance_screen_v1"
SCREEN_LIST_PATH = Path(__file__).resolve().parent / "data" / "chem_wep_smi.csv"
SCREEN_LIST_SOURCE = "chemcrow chem_wep_smi.csv (ur-whitelab/chemcrow-public, MIT)"
# Published ControlChemCheck threshold: Tanimoto similarity above this flags
# the input as a close analogue of a listed chemical.
SIMILARITY_THRESHOLD = 0.35

_CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")
_CAS_TOKEN_RE = re.compile(r"\d{2,7}-\d{2}-\d")
# Match kinds that refuse outright; a "similarity" flag witnesses instead.
EXACT_MATCH_KINDS = ("cas_exact", "smiles_exact", "smiles_canonical")

_LIST_CACHE: Optional[List[Dict[str, str]]] = None
_CAS_SET_CACHE: Optional[frozenset] = None
_RDKIT_CACHE: Optional[Dict[str, Any]] = None


class ControlledSubstanceDenied(ValueError):
    """Raised when an input matches (or closely resembles) a listed chemical."""

    def __init__(self, message: str, report: Dict[str, Any]):
        super().__init__(message)
        self.report = report


def load_screen_list() -> List[Dict[str, str]]:
    """The vendored screening rows ({cas, source, smiles}), cached."""
    global _LIST_CACHE
    if _LIST_CACHE is None:
        with SCREEN_LIST_PATH.open(newline="", encoding="utf-8") as handle:
            _LIST_CACHE = [row for row in csv.DictReader(handle) if row.get("smiles", "").strip()]
    return _LIST_CACHE


def _listed_cas_numbers() -> frozenset:
    """All CAS-shaped tokens in the vendored ``cas`` column, normalized.

    The upstream column wraps some values in parentheses and lists several
    CAS numbers per row, so cells are tokenized rather than compared whole.
    """
    global _CAS_SET_CACHE
    if _CAS_SET_CACHE is None:
        _CAS_SET_CACHE = frozenset(
            token for row in load_screen_list() for token in _CAS_TOKEN_RE.findall(row.get("cas", ""))
        )
    return _CAS_SET_CACHE


def _rdkit_screen_state() -> Optional[Dict[str, Any]]:
    """Canonical-SMILES set + Morgan fingerprints for the list, or None.

    Lazy and never raises: without RDKit the screen degrades (visibly) to the
    exact-string level. List entries RDKit cannot parse stay covered by the
    exact-string lane.
    """
    global _RDKIT_CACHE
    if _RDKIT_CACHE is not None:
        return _RDKIT_CACHE or None
    try:
        from rdkit import Chem, DataStructs, RDLogger
        from rdkit.Chem import rdFingerprintGenerator

        RDLogger.DisableLog("rdApp.*")  # list rows that fail to parse are expected, not news
        generator = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
        canonical: set[str] = set()
        fingerprints = []
        for row in load_screen_list():
            mol = Chem.MolFromSmiles(row["smiles"].strip())
            if mol is None:
                continue
            canonical.add(Chem.MolToSmiles(mol, canonical=True))
            fingerprints.append(generator.GetFingerprint(mol))
        _RDKIT_CACHE = {
            "Chem": Chem,
            "DataStructs": DataStructs,
            "generator": generator,
            "canonical": canonical,
            "fingerprints": fingerprints,
        }
    except Exception:
        _RDKIT_CACHE = {}
    return _RDKIT_CACHE or None


def screen_input(text: str) -> Dict[str, Any]:
    """Screen one SMILES string or CAS number against the vendored list.

    Returns a report that names the screen level that actually ran and the
    match kind — never the matched entry itself.
    """
    candidate = (text or "").strip()
    rows = load_screen_list()
    report: Dict[str, Any] = {
        "schema_version": SCREEN_SCHEMA_VERSION,
        "flagged": False,
        "match_kind": None,
        "max_similarity": None,
        "screen_level": "exact_string",
        "input_parsed": None,
        "list_source": SCREEN_LIST_SOURCE,
        "list_size": len(rows),
    }
    if not candidate:
        return report

    if _CAS_RE.match(candidate):
        if candidate in _listed_cas_numbers():
            report["flagged"] = True
            report["match_kind"] = "cas_exact"
        return report

    if any(candidate == row["smiles"].strip() for row in rows):
        report["flagged"] = True
        report["match_kind"] = "smiles_exact"
        return report

    state = _rdkit_screen_state()
    if state is None:
        return report
    report["screen_level"] = "similarity"
    mol = state["Chem"].MolFromSmiles(candidate)
    report["input_parsed"] = mol is not None
    if mol is None:
        return report
    if state["Chem"].MolToSmiles(mol, canonical=True) in state["canonical"]:
        report["flagged"] = True
        report["match_kind"] = "smiles_canonical"
        return report
    fingerprint = state["generator"].GetFingerprint(mol)
    similarities = [state["DataStructs"].TanimotoSimilarity(fingerprint, fp) for fp in state["fingerprints"]]
    if similarities:
        report["max_similarity"] = round(max(similarities), 4)
        if report["max_similarity"] > SIMILARITY_THRESHOLD:
            report["flagged"] = True
            report["match_kind"] = "similarity"
    return report


def assert_not_controlled(text: str) -> Dict[str, Any]:
    """Refuse exact/canonical matches; return the report otherwise.

    A similarity-only flag does NOT raise — callers must witness it in their
    receipt (see geometry_view) so the flag survives into the audit trail.
    """
    report = screen_input(text)
    if report["match_kind"] in EXACT_MATCH_KINDS:
        raise ControlledSubstanceDenied(
            "input matches a chemical on the controlled-substances screening list "
            f"(match_kind={report['match_kind']}); refusing to compute",
            report,
        )
    return report
