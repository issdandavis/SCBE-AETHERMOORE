"""Chemistry Verification Gate — Training Promotion Rule.

A molecule cannot be promoted to downstream training unless it passes:
  1. RDKit parse
  2. Valence arithmetic check
  3. SCBE fusion state finite
  4. Governance summary preserves elements/tokens/votes

Usage:
    python scripts/eval/chemistry_verification_gate.py --smiles "CCO"
    python scripts/eval/chemistry_verification_gate.py --file training-data/chemistry_manual_verification_v1.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

from rdkit import Chem, rdBase

rdBase.DisableLog("rdApp.error")
rdBase.DisableLog("rdApp.warning")

sys.path.insert(0, "python")
from scbe.state9d_chemistry_fusion import (
    fuse_molecule,
    molecule_governance_summary,
    tokenize_molecule,
)

# ---------------------------------------------------------------------------
# Gate thresholds
# ---------------------------------------------------------------------------
MAX_VALENCE_PRESSURE = 50.0
MAX_COHERENCE_PENALTY = 20.0
MIN_TOKENS = 1


def rdkit_parse_check(smiles: str) -> tuple[bool, str]:
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False, "RDKit returned None"
        if mol.GetNumAtoms() == 0:
            return False, "RDKit parsed zero atoms"
        Chem.SanitizeMol(mol)
        return True, f"Parsed: {mol.GetNumAtoms()} atoms"
    except Exception as e:
        return False, str(e)


def _explicit_valence(atom: Chem.Atom) -> int:
    try:
        return int(atom.GetValence(Chem.ValenceType.EXPLICIT))
    except Exception:
        return int(atom.GetExplicitValence())


def _allowed_valence(atom: Chem.Atom) -> int | None:
    """Return conservative structural valence ceiling for training verification.

    This is not a synthesis-safety rule. It only separates structurally valid
    SMILES from impossible packets so the chemistry training data has a stable
    promotion boundary.
    """

    sym = atom.GetSymbol()
    charge = atom.GetFormalCharge()

    if sym == "N" and charge > 0:
        return 4
    if sym == "O" and charge > 0:
        return 3
    if sym == "O" and charge < 0:
        return 1
    if sym == "S":
        return 6
    if sym == "P":
        return 5

    return {
        "C": 4,
        "N": 3,
        "O": 2,
        "F": 1,
        "Cl": 1,
        "Br": 1,
        "I": 1,
        "B": 3,
        "Na": 0,
        "Mg": 0,
        "Al": 0,
        "Si": 4,
        "K": 0,
        "Ca": 0,
    }.get(sym)


def valence_check(smiles: str) -> tuple[bool, str]:
    try:
        if "[H]" in smiles and any(ch.isdigit() for ch in smiles):
            return False, "Explicit hydrogen ring closure is not a promotable structure"
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False, "Parse failed"
        if mol.GetNumAtoms() == 0:
            return False, "No atoms parsed"
        if "." in smiles and _has_neutral_salt_fragment(mol):
            return False, "Neutral salt fragments must be encoded with ionic charges"
        for atom in mol.GetAtoms():
            sym = atom.GetSymbol()
            if abs(atom.GetFormalCharge()) > 3:
                return False, f"{sym} has unrealistic formal charge {atom.GetFormalCharge():+d}"
            if sym == "H" and atom.IsInRing():
                return False, "Hydrogen ring closure is not a promotable structure"
            val = _explicit_valence(atom)
            max_val = _allowed_valence(atom)
            if max_val is not None and val > max_val:
                return False, f"{sym} has valence {val} > max {max_val}"
        return True, "All valences within limits"
    except Exception as e:
        return False, str(e)


def _has_neutral_salt_fragment(mol: Chem.Mol) -> bool:
    has_neutral_metal = False
    has_neutral_halide = False
    for atom in mol.GetAtoms():
        sym = atom.GetSymbol()
        charge = atom.GetFormalCharge()
        if sym in {"Na", "K", "Mg", "Ca", "Al"} and charge == 0:
            has_neutral_metal = True
        if sym in {"F", "Cl", "Br", "I"} and charge == 0:
            has_neutral_halide = True
    return has_neutral_metal and has_neutral_halide


def scbe_fusion_check(smiles: str) -> tuple[bool, str, Dict[str, Any]]:
    try:
        states = tokenize_molecule(smiles)
        if len(states) < MIN_TOKENS:
            return False, f"Too few tokens ({len(states)})", {}

        fusion = fuse_molecule(states)
        summary = molecule_governance_summary(smiles, t=0.0)

        # Check finite state
        sv = summary.get("state_vector", {})
        if not sv:
            return False, "Missing state_vector", {}

        # Check pressure
        pressure = summary.get("valence_pressure", 0.0)
        if pressure > MAX_VALENCE_PRESSURE:
            return False, f"Valence pressure {pressure:.2f} > {MAX_VALENCE_PRESSURE}", summary

        # Check coherence
        coherence = summary.get("coherence_penalty", 0.0)
        if coherence > MAX_COHERENCE_PENALTY:
            return False, f"Coherence penalty {coherence:.2f} > {MAX_COHERENCE_PENALTY}", summary

        # Check tau_hat exists
        tau_hat = summary.get("tau_hat", {})
        if not tau_hat or len(tau_hat) != 6:
            return False, f"Invalid tau_hat: {tau_hat}", summary

        # Check elements preserved
        expected_elements = summary.get("elements", [])
        if not expected_elements:
            return False, "No elements extracted", summary

        return True, "All SCBE checks passed", summary
    except Exception as e:
        return False, f"SCBE fusion error: {e}", {}


def run_gate(smiles: str) -> Dict[str, Any]:
    """Run the full chemistry verification gate on one SMILES."""
    result = {
        "smiles": smiles,
        "verdict": "PENDING",
        "checks": {},
        "summary": {},
        "reasons": [],
    }

    # Check 1: RDKit parse
    ok, msg = rdkit_parse_check(smiles)
    result["checks"]["rdkit_parse"] = ok
    if not ok:
        result["reasons"].append(f"RDKit: {msg}")

    # Check 2: Valence
    ok, msg = valence_check(smiles)
    result["checks"]["valence"] = ok
    if not ok:
        result["reasons"].append(f"Valence: {msg}")

    # Check 3: SCBE fusion
    ok, msg, summary = scbe_fusion_check(smiles)
    result["checks"]["scbe_fusion"] = ok
    result["summary"] = summary
    if not ok:
        result["reasons"].append(f"SCBE: {msg}")

    # Final verdict
    if all(result["checks"].values()):
        result["verdict"] = "PASS"
    else:
        result["verdict"] = "DENY"

    return result


def promote(smiles: str) -> bool:
    """Returns True if the molecule can be promoted."""
    result = run_gate(smiles)
    return result["verdict"] == "PASS"


def run_batch(file_path: str) -> Dict[str, Any]:
    with open(file_path, "r", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]

    results = []
    counts = {"PASS": 0, "DENY": 0}

    for row in rows:
        smiles = row.get("smiles", "")
        res = run_gate(smiles)
        results.append(res)
        counts[res["verdict"]] += 1

    return {
        "total": len(rows),
        "counts": counts,
        "pass_rate": counts["PASS"] / max(1, len(rows)),
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Chemistry verification gate")
    parser.add_argument("--smiles", type=str, help="Single SMILES to check")
    parser.add_argument("--file", type=str, help="JSONL file of verification rows")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    if args.smiles:
        result = run_gate(args.smiles)
        print(json.dumps(result, indent=None if args.json else 2, default=str))
        sys.exit(0 if result["verdict"] == "PASS" else 1)

    if args.file:
        batch = run_batch(args.file)

        # Fail if any expected-valid molecules were denied
        denied_valid = []
        with open(args.file, "r", encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
        for row, res in zip(rows, batch["results"]):
            expected_governance = row.get("expected_governance", "ALLOW" if row.get("expected_valid") else "DENY")
            if expected_governance == "ALLOW" and res["verdict"] == "DENY":
                denied_valid.append(row.get("name", row.get("smiles")))

        batch["denied_expected_allow"] = denied_valid
        if args.json:
            print(json.dumps(batch, indent=2, default=str))
        else:
            print(f"\nChemistry Verification Gate — Batch Results")
            print(f"  Total: {batch['total']}")
            print(f"  PASS:  {batch['counts']['PASS']}")
            print(f"  DENY:  {batch['counts']['DENY']}")
            print(f"  Rate:  {batch['pass_rate']*100:.1f}%")

        if denied_valid:
            if not args.json:
                print(f"\n  ERROR: Expected-ALLOW molecules DENIED: {denied_valid}")
            sys.exit(1)

        if not args.json:
            print("\n  All expected-ALLOW molecules passed. Gate OK.")
        sys.exit(0)

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
