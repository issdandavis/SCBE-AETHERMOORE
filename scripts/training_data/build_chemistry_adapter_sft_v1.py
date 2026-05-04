"""Build chemistry_adapter_verification_v1 SFT dataset.

Captures machine-verified adapter outputs for training:
  SMILES → ChemistryAdapter.check() → structured verdict with computed tau_hat,
  votes, valence_pressure, coherence_penalty, and elements.

This complements the hand-written chemistry_manual_verification_v1 dataset
by providing ground-truth computed values from the live SCBE pipeline.

Output:
  training-data/sft/chemistry_adapter_verification_v1_train.sft.jsonl
  training-data/sft/chemistry_adapter_verification_v1_eval.sft.jsonl
  training-data/sft/chemistry_adapter_verification_v1_manifest.json
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from python.scbe.chemistry_adapter import ChemistryAdapter

SFT_TRAIN_PATH = "training-data/sft/chemistry_adapter_verification_v1_train.sft.jsonl"
SFT_EVAL_PATH = "training-data/sft/chemistry_adapter_verification_v1_eval.sft.jsonl"
SFT_MANIFEST_PATH = "training-data/sft/chemistry_adapter_verification_v1_manifest.json"

# Test cases: expanded to ~50 rows across 12 categories
TEST_CASES = [
    # -------- BASIC (difficulty 1) --------
    ("O", "water", True, 1, ["simple", "inorganic", "polar"]),
    ("C", "methane", True, 1, ["simple", "alkane", "nonpolar"]),
    ("N", "ammonia", True, 1, ["simple", "inorganic", "basic"]),
    ("CCO", "ethanol", True, 1, ["alcohol", "organic"]),
    ("CC", "ethane", True, 1, ["alkane", "organic"]),
    ("C=C", "ethene", True, 1, ["alkene", "organic"]),

    # -------- FUNCTIONAL GROUPS (difficulty 2) --------
    ("CC(=O)O", "acetic_acid", True, 2, ["carboxylic_acid", "organic"]),
    ("CC=O", "acetaldehyde", True, 2, ["aldehyde", "organic"]),
    ("CC(=O)OC", "methyl_acetate", True, 2, ["ester", "organic"]),
    ("CCN", "ethylamine", True, 2, ["amine", "basic"]),
    ("CC#N", "acetonitrile", True, 2, ["nitrile", "organic"]),
    ("CC(C)=O", "acetone", True, 2, ["ketone", "organic"]),

    # -------- AROMATIC / DRUG (difficulty 2) --------
    ("CC(=O)Oc1ccccc1C(=O)O", "aspirin", True, 2, ["drug", "ester", "aromatic"]),
    ("c1ccccc1", "benzene", True, 2, ["aromatic", "hydrocarbon"]),
    ("c1ccc(O)cc1", "phenol", True, 2, ["aromatic", "alcohol"]),
    ("CC(C)Cc1ccc(C(C)C(=O)O)cc1", "ibuprofen", True, 2, ["drug", "nsaid", "aromatic"]),
    ("CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "caffeine", True, 2, ["drug", "alkaloid", "purine"]),

    # -------- RINGS (difficulty 2-3) --------
    ("C1CC1", "cyclopropane", True, 2, ["cycloalkane", "ring_strain"]),
    ("C1CCC1", "cyclobutane", True, 2, ["cycloalkane"]),
    ("C1CCCCC1", "cyclohexane", True, 2, ["cycloalkane"]),
    ("C1=CC=CC=C1", "benzene_kekule", True, 2, ["aromatic", "hydrocarbon"]),

    # -------- ISOTOPES (difficulty 2) --------
    ("[2H]O[2H]", "heavy_water", True, 2, ["isotope", "inorganic"]),
    ("[13CH4]", "carbon_13_methane", True, 2, ["isotope", "alkane"]),
    ("[2H]C([2H])([2H])O", "deuterated_methanol", True, 2, ["isotope", "alcohol"]),

    # -------- CHARGED / IONIC (difficulty 2) --------
    ("[Na+]", "sodium_cation", True, 2, ["ionic", "charged"]),
    ("[Na+].[Cl-]", "sodium_chloride", True, 2, ["ionic", "salt"]),
    ("CC(=O)[O-].[Na+]", "sodium_acetate", True, 2, ["ionic", "salt", "organic"]),
    ("[NH4+]", "ammonium", True, 2, ["ionic", "charged", "basic"]),
    ("[NH4+].[Cl-]", "ammonium_chloride", True, 2, ["ionic", "salt"]),
    ("[N-]=[N+]=[N-]", "azide", True, 2, ["ionic", "charged", "explosive"]),
    ("C=[N+]=[N-]", "diazomethane", True, 2, ["charged", "reactive"]),

    # -------- ORGANOMETALLICS (difficulty 3) --------
    ("c1ccc([Fe]c2ccccc2)cc1", "ferrocene", True, 3, ["organometallic", "metal"]),
    ("C[Hg]C", "dimethylmercury", True, 3, ["organometallic", "toxic", "metal"]),
    ("C[Pb](C)(C)C", "tetramethyllead", True, 3, ["organometallic", "toxic", "metal"]),

    # -------- NATURAL PRODUCTS / COMPLEX (difficulty 3) --------
    ("C(C1C(C(C(C(O1)O)O)O)O)O", "glucose", True, 3, ["sugar", "natural_product", "carbohydrate"]),
    ("CN1CC[C@]23c4c5ccc(O)c4O[C@H]2[C@@H](O)C=C[C@H]3[C@H]1C5", "morphine", True, 3, ["drug", "alkaloid", "natural_product", "stereochemistry"]),
    ("CC(C)CCC(C)C1CCC2C3CC=C4CC(O)CCC4(C)C3CCC12C", "cholesterol", True, 3, ["steroid", "natural_product", "lipid"]),

    # -------- PEPTIDE (difficulty 3) --------
    ("NCC(=O)NC(C)C(=O)O", "glycylalanine", True, 3, ["peptide", "dipeptide", "amino_acid"]),

    # -------- INORGANIC / ACIDS (difficulty 2) --------
    ("OS(=O)(=O)O", "sulfuric_acid", True, 2, ["inorganic", "acid", "strong_acid"]),
    ("O=[N+]([O-])O", "nitric_acid", True, 2, ["inorganic", "acid", "strong_acid"]),
    ("[Si](Cl)(Cl)(Cl)Cl", "silicon_tetrachloride", True, 2, ["inorganic", "silicon", "halide"]),
    ("[Ti](Cl)(Cl)(Cl)Cl", "titanium_tetrachloride", True, 2, ["inorganic", "titanium", "halide"]),
    ("O=C=O", "carbon_dioxide", True, 2, ["inorganic", "oxide", "gas"]),

    # -------- INVALID / BOUNDARY (difficulty 1-3) --------
    ("C(C)(C)(C)(C)(C)", "pentavalent_carbon", False, 3, ["invalid", "valence_violation"]),
    ("C1=C=C1", "cyclopropatriene", False, 3, ["invalid", "impossible_ring", "valence_violation"]),
    ("NotASmiles", "nonsense", False, 1, ["invalid", "parse_failure"]),
    ("", "empty_string", False, 1, ["invalid", "empty"]),

    # -------- STRESS TEST (difficulty 3) --------
    ("CC(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C", "highly_branched", True, 3, ["stress_test", "branched"]),
    ("CCCCCCCCCCCCCCCCCC(=O)O", "stearic_acid", True, 3, ["fatty_acid", "lipid", "long_chain"]),
    ("C1CC2CCC3C4CCC5CCCCC5C4CCC3C2C1", "perhydropyrene", True, 3, ["polycyclic", "hydrocarbon"]),
]

SYSTEM_PROMPT = (
    "You are an SCBE-AETHERMOORE chemistry verification agent. "
    "Given a SMILES string, run the full adapter pipeline: "
    "RDKit parse → valence check → SCBE fusion → governance verdict. "
    "Report the computed tau_hat per tongue, reconstruction votes, "
    "valence_pressure, coherence_penalty, detected elements, and final verdict."
)


def _make_id(smiles: str, name: str) -> str:
    h = hashlib.sha256(f"{name}:{smiles}".encode()).hexdigest()[:16]
    return f"chemistry_adapter_verification_v1_{name}_{h}"


def build_rows():
    adapter = ChemistryAdapter()
    rows = []
    for smiles, name, expected_valid, difficulty, tags in TEST_CASES:
        result = adapter.check(smiles)
        score = adapter.score_for_sft(smiles)

        user_msg = f"Verify SMILES `{smiles}` ({name}). Return adapter-computed verdict and metrics."

        assistant_content = {
            "schema_version": "scbe_chemistry_adapter_verification_answer_v1",
            "smiles": smiles,
            "name": name,
            "expected_valid": expected_valid,
            "computed": {
                "can_promote": result.can_promote,
                "rdkit_ok": result.rdkit_ok,
                "valence_ok": result.valence_ok,
                "fusion_ok": result.fusion_ok,
                "valence_pressure": round(result.valence_pressure, 4),
                "coherence_penalty": round(result.coherence_penalty, 4),
                "governance_verdict": result.governance_verdict,
                "elements": score.get("elements", []),
                "tau_hat": score.get("tau_hat", {}),
                "votes": {k: round(v, 4) for k, v in (score.get("votes") or {}).items()},
                "sft_score": round(score.get("score", 0.0), 4),
            },
            "verdict": {
                "promotion": "PASS" if result.can_promote else "DENY",
                "reasons": result.reasons,
            },
        }

        row = {
            "id": _make_id(smiles, name),
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": json.dumps(assistant_content, separators=(",", ":"))},
            ],
            "metadata": {
                "track": "chemistry_adapter_verification_v1",
                "source": "adapter_test_cases",
                "difficulty": difficulty,
                "expected_valid": expected_valid,
                "expected_governance": result.governance_verdict,
                "tags": tags,
                "training_pattern": "adapter_computed_verdict",
            },
        }
        rows.append(row)
    return rows


def split_and_write(rows, eval_fraction=0.2):
    # Deterministic split: first N% as eval
    n_eval = max(1, int(len(rows) * eval_fraction))
    train_rows = rows[n_eval:]
    eval_rows = rows[:n_eval]

    os.makedirs(os.path.dirname(SFT_TRAIN_PATH), exist_ok=True)
    with open(SFT_TRAIN_PATH, "w", encoding="utf-8") as f:
        for row in train_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with open(SFT_EVAL_PATH, "w", encoding="utf-8") as f:
        for row in eval_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "dataset": "chemistry_adapter_verification_v1",
        "version": "1.0.0",
        "format": "sft",
        "n_train": len(train_rows),
        "n_eval": len(eval_rows),
        "n_total": len(rows),
        "train_path": SFT_TRAIN_PATH,
        "eval_path": SFT_EVAL_PATH,
        "description": (
            "Machine-verified chemistry adapter outputs for SFT training. "
            "Each row contains live-computed tau_hat, votes, valence_pressure, "
            "coherence_penalty, and governance verdict from the SCBE pipeline."
        ),
        "sources": [r["metadata"]["source"] for r in rows],
        "difficulty_distribution": {
            "1": sum(1 for r in rows if r["metadata"]["difficulty"] == 1),
            "2": sum(1 for r in rows if r["metadata"]["difficulty"] == 2),
            "3": sum(1 for r in rows if r["metadata"]["difficulty"] == 3),
        },
        "governance_distribution": {
            "ALLOW": sum(1 for r in rows if r["metadata"]["expected_governance"] == "ALLOW"),
            "DENY": sum(1 for r in rows if r["metadata"]["expected_governance"] == "DENY"),
            "UNKNOWN": sum(1 for r in rows if r["metadata"]["expected_governance"] == "UNKNOWN"),
        },
    }
    with open(SFT_MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def main():
    rows = build_rows()
    manifest = split_and_write(rows)
    print(f"Wrote {manifest['n_train']} train + {manifest['n_eval']} eval rows")
    print(f"Manifest: {SFT_MANIFEST_PATH}")
    print(f"Train: {SFT_TRAIN_PATH}")
    print(f"Eval: {SFT_EVAL_PATH}")


if __name__ == "__main__":
    main()
