"""Evaluate the controlled-substance screen: recall, robustness, false positives.

Honest scoping: the original plan was to score against ChemSafetyBench, but its
dataset repository is unavailable (404 as of 2026-06-12). This harness
substitutes three measurable claims against the vendored screening list itself:

1. List recall — every vendored CAS and SMILES entry must be flagged (this is
   true by construction for exact lanes; the harness proves the wiring).
2. Rendering robustness (RDKit) — alternate non-canonical SMILES renderings of
   list entries must still be flagged via the canonical lane.
3. Benign false positives — a panel of common benign compounds; exact-lane
   false positives must be zero, and similarity-lane flags at the published
   0.35 threshold are reported honestly (a known trade-off of that threshold,
   not hidden).

Output is aggregate counts only — entry identities are never printed.

Usage: python scripts/eval/controlled_substance_screen_eval.py [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from python.scbe.controlled_substances import (  # noqa: E402
    SIMILARITY_THRESHOLD,
    _listed_cas_numbers,
    load_screen_list,
    screen_input,
)

BENIGN_PANEL = {
    "water": "O",
    "ethanol": "CCO",
    "acetone": "CC(C)=O",
    "aspirin": "CC(=O)OC1=CC=CC=C1C(=O)O",
    "caffeine": "CN1C=NC2=C1C(=O)N(C)C(=O)N2C",
    "ibuprofen": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",
    "glucose": "C(C1C(C(C(C(O1)O)O)O)O)O",
    "benzene": "C1=CC=CC=C1",
    "toluene": "CC1=CC=CC=C1",
    "acetic acid": "CC(=O)O",
    "citric acid": "C(C(=O)O)C(CC(=O)O)(C(=O)O)O",
    "urea": "C(=O)(N)N",
    "glycine": "C(C(=O)O)N",
    "sucrose": "C(C1C(C(C(C(O1)OC2(C(C(C(O2)CO)O)O)CO)O)O)O)O",
    "paracetamol": "CC(=O)NC1=CC=C(C=C1)O",
    "vitamin c": "C(C(C1C(=C(C(=O)O1)O)O)O)O",
    "lactic acid": "CC(C(=O)O)O",
    "ethylene glycol": "C(CO)O",
}


def evaluate() -> dict:
    rows = load_screen_list()
    cas_numbers = _listed_cas_numbers()
    cas_flagged = sum(1 for cas in cas_numbers if screen_input(cas)["flagged"])
    smiles_flagged = sum(1 for r in rows if screen_input(r["smiles"].strip())["flagged"])

    rendered = caught = 0
    try:
        from rdkit import Chem, RDLogger

        RDLogger.DisableLog("rdApp.*")
        for row in rows:
            mol = Chem.MolFromSmiles(row["smiles"].strip())
            if mol is None or mol.GetNumAtoms() < 2:
                continue
            alternate = Chem.MolToSmiles(mol, canonical=False, rootedAtAtom=mol.GetNumAtoms() - 1)
            if alternate == row["smiles"].strip():
                continue
            rendered += 1
            if screen_input(alternate)["flagged"]:
                caught += 1
        rdkit_available = True
    except Exception:
        rdkit_available = False

    benign_exact_fp = 0
    benign_similarity_fp = []
    for name, smiles in BENIGN_PANEL.items():
        report = screen_input(smiles)
        if report["match_kind"] in ("cas_exact", "smiles_exact", "smiles_canonical"):
            benign_exact_fp += 1
        if report["flagged"] and report["match_kind"] == "similarity":
            benign_similarity_fp.append({"name": name, "max_similarity": report["max_similarity"]})

    return {
        "schema_version": "scbe_controlled_substance_screen_eval_v1",
        "note": "ChemSafetyBench dataset unavailable (404); list-recall + robustness + benign-FP substitute",
        "list_size": len(rows),
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "rdkit_available": rdkit_available,
        "cas_recall": {"flagged": cas_flagged, "total": len(cas_numbers)},
        "smiles_recall": {"flagged": smiles_flagged, "total": len(rows)},
        "rendering_robustness": {"caught": caught, "rendered": rendered},
        "benign_panel_size": len(BENIGN_PANEL),
        "benign_exact_false_positives": benign_exact_fp,
        "benign_similarity_false_positives": benign_similarity_fp,
        "passed": (
            cas_flagged == len(cas_numbers)
            and smiles_flagged == len(rows)
            and benign_exact_fp == 0
            and (not rdkit_available or caught == rendered)
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = evaluate()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"controlled-substance screen eval (list n={result['list_size']})")
        print(f"  CAS recall:        {result['cas_recall']['flagged']}/{result['cas_recall']['total']}")
        print(f"  SMILES recall:     {result['smiles_recall']['flagged']}/{result['smiles_recall']['total']}")
        rr = result["rendering_robustness"]
        level = "similarity" if result["rdkit_available"] else "exact_string (RDKit absent)"
        print(f"  rendering caught:  {rr['caught']}/{rr['rendered']} (screen level: {level})")
        print(f"  benign exact FPs:  {result['benign_exact_false_positives']}/{result['benign_panel_size']}")
        sim_fps = result["benign_similarity_false_positives"]
        print(f"  benign similarity FPs at {result['similarity_threshold']}: {len(sim_fps)}")
        for fp in sim_fps:
            print(f"    {fp['name']}: {fp['max_similarity']}")
        print(f"  PASSED: {result['passed']}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
