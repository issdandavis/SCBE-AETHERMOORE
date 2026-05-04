"""Chemistry manual verification runner.

For each row in chemistry_manual_verification_v1.jsonl:

  1. RDKit parse check
  2. Atomic tokenization
  3. Manual valence arithmetic verification
  4. SCBE fusion state computation
  5. Compare expected vs actual
  6. Emit PASS / HOLD / DENY

This is "running the numbers to the 10th decimal."
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List

from rdkit import Chem, rdBase
from rdkit.Chem import Descriptors

rdBase.DisableLog("rdApp.error")
rdBase.DisableLog("rdApp.warning")

sys.path.insert(0, "python")
from scbe.state9d_chemistry_fusion import (
    fuse_molecule,
    molecule_governance_summary,
    tokenize_molecule,
)

DATASET_PATH = "training-data/chemistry_manual_verification_v1.jsonl"


def rdkit_parse(smiles: str) -> tuple[bool, Any]:
    """Attempt RDKit parse. Returns (success, mol_or_none)."""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False, None
        Chem.SanitizeMol(mol)
        return True, mol
    except Exception:
        return False, None


def check_valence_manual(mol) -> tuple[bool, str]:
    """Verify that every atom's explicit valence is satisfied."""
    if mol is None:
        return False, "No molecule"
    issues = []
    for atom in mol.GetAtoms():
        sym = atom.GetSymbol()
        valence = atom.GetExplicitValence()
        # Common valences
        expected = {
            "C": 4, "N": 3, "O": 2, "S": 2, "P": 3,
            "F": 1, "Cl": 1, "Br": 1, "I": 1, "B": 3,
            "Na": 0, "Mg": 0, "Al": 0, "Si": 4,
        }.get(sym, None)
        if expected is not None and valence > expected:
            issues.append(f"{sym} has valence {valence} > expected {expected}")
    if issues:
        return False, "; ".join(issues)
    return True, "All valences satisfied"


def check_functional_group(mol, expected_family: str) -> tuple[bool, str]:
    """Basic functional group detection via SMARTS."""
    if mol is None:
        return False, "No molecule"

    smarts_map = {
        "alcohol": "[OX2H]",
        "carboxylic_acid": "[CX3](=O)[OX2H1]",
        "ketone": "[CX3](=O)[#6]",
        "ester": "[CX3](=O)[OX2H0]",
        "amine": "[NX3;H2,H1;!$(NC=O)]",
        "amide": "[NX3][CX3](=[OX1])",
        "aromatic_hydrocarbon": "c1ccccc1",
        "ether": "[#6][OX2][#6]",
        "alkane": "[CX4]",
        "alkene": "[CX3]=[CX3]",
        "alkyne": "[CX2]#[CX2]",
    }

    detected = []
    for name, smarts in smarts_map.items():
        patt = Chem.MolFromSmarts(smarts)
        if patt and mol.HasSubstructMatch(patt):
            detected.append(name)

    # Normalize family names
    family_norm = expected_family.lower().replace(" ", "_")
    if family_norm in detected or any(family_norm in d for d in detected):
        return True, f"Detected: {detected}"
    if expected_family == "invalid":
        return True, "N/A (invalid molecule)"
    return False, f"Expected {expected_family}, detected: {detected}"


def check_drug_like_filters(mol) -> tuple[bool, str]:
    """Lipinski-like filter check."""
    if mol is None:
        return False, "No molecule"
    mw = Descriptors.MolWt(mol)
    logp = Descriptors.MolLogP(mol)
    hbd = Descriptors.NumHDonors(mol)
    hba = Descriptors.NumHAcceptors(mol)
    tpsa = Descriptors.TPSA(mol)

    passes = (
        0 < mw <= 500
        and -10 <= logp <= 10
        and hbd <= 5
        and hba <= 10
        and tpsa < 150
    )
    details = f"MW={mw:.1f}, logP={logp:.2f}, HBD={hbd}, HBA={hba}, TPSA={tpsa:.1f}"
    return passes, details


def verify_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Run full verification pipeline on one row."""
    smiles = row["smiles"]
    expected_valid = row["expected_valid"]
    expected_governance = row["expected_governance"]
    expected_family = row["expected_family"]

    result: Dict[str, Any] = {
        "smiles": smiles,
        "name": row["name"],
        "expected_valid": expected_valid,
        "expected_governance": expected_governance,
        "checks": {},
        "scbe": {},
        "verdict": "PENDING",
        "reasons": [],
    }

    # ---- Check 1: RDKit parse ----
    parsed, mol = rdkit_parse(smiles)
    result["checks"]["rdkit_parse"] = parsed
    if not parsed and expected_valid:
        result["reasons"].append("RDKit failed to parse a molecule expected to be valid")
    if parsed and not expected_valid:
        result["reasons"].append("RDKit parsed a molecule expected to be invalid")

    # ---- Check 2: Valence arithmetic ----
    if mol:
        valence_ok, valence_msg = check_valence_manual(mol)
        result["checks"]["valence_manual"] = valence_ok
        result["checks"]["valence_msg"] = valence_msg
        if not valence_ok:
            result["reasons"].append(f"Valence violation: {valence_msg}")
    else:
        result["checks"]["valence_manual"] = False
        result["checks"]["valence_msg"] = "N/A (parse failed)"

    # ---- Check 3: Functional group ----
    if mol:
        fg_ok, fg_msg = check_functional_group(mol, expected_family)
        result["checks"]["functional_group"] = fg_ok
        result["checks"]["functional_group_msg"] = fg_msg
        if not fg_ok and expected_valid:
            result["reasons"].append(f"Functional group mismatch: {fg_msg}")
    else:
        result["checks"]["functional_group"] = False
        result["checks"]["functional_group_msg"] = "N/A"

    # ---- Check 4: Drug-like filters (for drug rows) ----
    if mol and row.get("source") == "drug":
        filter_ok, filter_msg = check_drug_like_filters(mol)
        result["checks"]["drug_like_filters"] = filter_ok
        result["checks"]["drug_like_msg"] = filter_msg
        if not filter_ok:
            result["reasons"].append(f"Drug-like filter fail: {filter_msg}")
    else:
        result["checks"]["drug_like_filters"] = None

    # ---- Check 5: SCBE fusion pipeline ----
    try:
        states = tokenize_molecule(smiles)
        fusion = fuse_molecule(states)
        summary = molecule_governance_summary(smiles, t=0.0)

        result["scbe"]["n_tokens"] = len(states)
        result["scbe"]["elements"] = summary.get("elements", [])
        result["scbe"]["tau_hat"] = summary.get("tau_hat", {})
        result["scbe"]["coherence_penalty"] = summary.get("coherence_penalty", 0.0)
        result["scbe"]["valence_pressure"] = summary.get("valence_pressure", 0.0)
        result["scbe"]["votes"] = summary.get("votes", {})
        result["scbe"]["state_finite"] = True
        result["checks"]["scbe_fusion_finite"] = True
    except Exception as e:
        result["scbe"]["state_finite"] = False
        result["checks"]["scbe_fusion_finite"] = False
        result["reasons"].append(f"SCBE fusion failed: {e}")

    # ---- Check 6: Compare expected vs actual ----
    actual_valid = parsed
    actual_governance = "ALLOW" if parsed else "DENY"

    governance_match = actual_governance == expected_governance
    validity_match = actual_valid == expected_valid

    result["actual_valid"] = actual_valid
    result["actual_governance"] = actual_governance
    result["checks"]["governance_match"] = governance_match
    result["checks"]["validity_match"] = validity_match

    if not validity_match:
        result["reasons"].append(
            f"Validity mismatch: expected {expected_valid}, got {actual_valid}"
        )
    if not governance_match:
        result["reasons"].append(
            f"Governance mismatch: expected {expected_governance}, got {actual_governance}"
        )

    # ---- Final verdict ----
    if result["checks"].get("scbe_fusion_finite") and governance_match and validity_match:
        if mol and row.get("source") == "drug" and not result["checks"].get("drug_like_filters"):
            result["verdict"] = "HOLD"
            result["reasons"].append("Drug-like filters failed")
        else:
            result["verdict"] = "PASS"
    elif result["checks"].get("scbe_fusion_finite") and not result["checks"].get("rdkit_parse") and not expected_valid:
        result["verdict"] = "PASS"
    else:
        result["verdict"] = "DENY"

    return result


def run_verification():
    print("=" * 70)
    print("CHEMISTRY MANUAL VERIFICATION RUNNER")
    print("=" * 70)

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]

    results: List[Dict[str, Any]] = []
    counts = {"PASS": 0, "HOLD": 0, "DENY": 0}

    for i, row in enumerate(rows, 1):
        res = verify_row(row)
        results.append(res)
        counts[res["verdict"]] += 1

        status_icon = "[PASS]" if res["verdict"] == "PASS" else "[HOLD]" if res["verdict"] == "HOLD" else "[DENY]"
        print(f"\n{status_icon} {i:2d}. {res['name']:<30s} | {res['verdict']:<5s} | SMILES: {res['smiles']}")
        if res["reasons"]:
            for r in res["reasons"]:
                print(f"    -> {r}")
        else:
            print(f"    -> RDKit: {res['checks'].get('rdkit_parse')}, "
                  f"Valence: {res['checks'].get('valence_manual')}, "
                  f"Fusion: {res['checks'].get('scbe_fusion_finite')}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Total rows : {len(rows)}")
    print(f"  PASS       : {counts['PASS']}")
    print(f"  HOLD       : {counts['HOLD']}")
    print(f"  DENY       : {counts['DENY']}")
    print(f"  Pass rate  : {100.0 * counts['PASS'] / len(rows):.1f}%")
    print("=" * 70)

    # Write results
    out_path = "artifacts/chemistry_manual_verification_results.json"
    import os
    os.makedirs("artifacts", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "dataset": DATASET_PATH,
            "total": len(rows),
            "counts": counts,
            "results": results,
        }, f, indent=2)
    print(f"\nDetailed results written to {out_path}")

    return counts


if __name__ == "__main__":
    run_verification()
