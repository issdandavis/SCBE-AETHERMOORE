#!/usr/bin/env python3
"""Build SFT rows for the SCBE chemistry adapter invariants.

This pack is narrower than the manual chemistry dataset. It teaches the model
the implementation-facing rules that protect the training gate:

- invalid SMILES still returns all adapter booleans;
- promotion requires RDKit, valence, fusion, and pressure checks;
- chemistry tokens map to real elements instead of generic ENTITY defaults;
- pressure thresholds can deny otherwise valid molecules.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "training-data" / "sft"
DEFAULT_KAGGLE_DIR = REPO_ROOT / "artifacts" / "kaggle_datasets" / "scbe-coding-agent-stage6-repair-v7"

TRAIN_NAME = "chemistry_adapter_invariants_v1_train.sft.jsonl"
EVAL_NAME = "chemistry_adapter_invariants_v1_eval.sft.jsonl"
MANIFEST_NAME = "chemistry_adapter_invariants_v1_manifest.json"

SYSTEM = (
    "You are an SCBE-AETHERMOORE chemistry adapter agent. Explain and preserve "
    "the implementation invariants for chemistry promotion gates. Keep material "
    "chemistry separate from metaphors, return compact JSON, and never promote a "
    "molecule unless RDKit validity, valence, SCBE fusion, and thresholds agree."
)


CASES = [
    {
        "scenario": "invalid_smiles_error_path_booleans",
        "split": "train",
        "user": "What should the chemistry adapter return for invalid SMILES `NotASmiles`?",
        "answer": {
            "schema_version": "scbe_chemistry_adapter_invariant_answer_v1",
            "invariant": "invalid_smiles_error_path_booleans",
            "smiles": "NotASmiles",
            "expected": {
                "can_promote": False,
                "rdkit_ok": False,
                "valence_ok": False,
                "fusion_ok": False,
                "governance_verdict": "DENY",
            },
            "reasoning": [
                "RDKit parse fails, so promotion is impossible.",
                "The adapter must still populate rdkit_ok, valence_ok, and fusion_ok booleans.",
                "The error path must not construct ChemistryCheckResult with missing required fields.",
            ],
            "gate": "DENY unless the result has all required booleans and can_promote is false.",
        },
    },
    {
        "scenario": "water_full_promotion_path",
        "split": "train",
        "user": "Show the adapter promotion contract for water `O`.",
        "answer": {
            "schema_version": "scbe_chemistry_adapter_invariant_answer_v1",
            "invariant": "valid_molecule_promotion_contract",
            "smiles": "O",
            "expected": {
                "can_promote": True,
                "rdkit_ok": True,
                "valence_ok": True,
                "fusion_ok": True,
                "governance_verdict": "ALLOW",
            },
            "reasoning": [
                "RDKit parses the molecule.",
                "Oxygen valence is satisfied.",
                "SCBE fusion summary is finite.",
                "Pressure and coherence remain under thresholds.",
            ],
            "gate": "ALLOW only when all checks agree.",
        },
    },
    {
        "scenario": "ethanol_elements_are_real",
        "split": "train",
        "user": "In chemistry mode, what elements should `CCO` produce?",
        "answer": {
            "schema_version": "scbe_chemistry_adapter_invariant_answer_v1",
            "invariant": "chemistry_context_real_element_mapping",
            "smiles": "CCO",
            "expected_elements": ["C", "C", "O"],
            "forbidden_elements": ["Fe", "Fe", "Fe"],
            "reasoning": [
                "map_token_to_atomic_state must call map_token_to_element with chemistry or molecular context.",
                "Carbon and oxygen tokens must map to periodic-table C and O.",
                "Generic ENTITY fallback to Fe is only a non-chemistry default and must not dominate this lane.",
            ],
            "gate": "PASS only when chemistry elements preserve C/O identity.",
        },
    },
    {
        "scenario": "pentavalent_carbon_rejected",
        "split": "train",
        "user": "Should `C(C)(C)(C)(C)(C)` be promoted?",
        "answer": {
            "schema_version": "scbe_chemistry_adapter_invariant_answer_v1",
            "invariant": "valence_violation_rejection",
            "smiles": "C(C)(C)(C)(C)(C)",
            "expected": {
                "can_promote": False,
                "rdkit_ok": False,
                "valence_ok": False,
            },
            "reasoning": [
                "A central carbon with five single bonds violates carbon valence.",
                "Invalid material chemistry must not be rescued by symbolic fusion.",
                "The adapter blocks promotion when RDKit or valence rejects the structure.",
            ],
            "gate": "DENY on valence violation.",
        },
    },
    {
        "scenario": "pressure_threshold_denies_valid_molecule",
        "split": "train",
        "user": "What happens if `CCO` is valid but the adapter max_valence_pressure is 0.0?",
        "answer": {
            "schema_version": "scbe_chemistry_adapter_invariant_answer_v1",
            "invariant": "threshold_can_override_validity",
            "smiles": "CCO",
            "expected": {
                "rdkit_ok": True,
                "valence_ok": True,
                "fusion_ok": True,
                "can_promote": False,
            },
            "reasoning": [
                "A molecule can be chemically valid but still exceed the configured promotion threshold.",
                "Threshold denial must record a reason such as valence pressure exceeding the limit.",
                "Promotion requires validity and policy thresholds, not validity alone.",
            ],
            "gate": "HOLD or DENY when pressure exceeds configured threshold.",
        },
    },
    {
        "scenario": "batch_check_preserves_order",
        "split": "train",
        "user": "How should batch checking handle `[O, CCO, NotASmiles]`?",
        "answer": {
            "schema_version": "scbe_chemistry_adapter_invariant_answer_v1",
            "invariant": "batch_check_ordered_results",
            "smiles_batch": ["O", "CCO", "NotASmiles"],
            "expected_can_promote": [True, True, False],
            "reasoning": [
                "Each input receives an independent ChemistryCheckResult.",
                "Output order mirrors input order.",
                "Invalid entries do not poison valid entries in the same batch.",
            ],
            "gate": "PASS when batch results are ordered and independent.",
        },
    },
    {
        "scenario": "score_for_sft_contains_training_fields",
        "split": "eval",
        "user": "What fields must `score_for_sft(\"CCO\")` expose?",
        "answer": {
            "schema_version": "scbe_chemistry_adapter_invariant_answer_v1",
            "invariant": "sft_score_fields",
            "smiles": "CCO",
            "required_fields": [
                "score",
                "can_promote",
                "rdkit_ok",
                "valence_ok",
                "fusion_ok",
                "valence_pressure",
                "coherence_penalty",
                "tau_hat",
                "votes",
            ],
            "reasoning": [
                "SFT and preference ranking need a scalar score plus the boolean evidence fields.",
                "tau_hat and votes preserve SCBE fusion provenance.",
            ],
            "gate": "PASS when scoring exposes both chemistry checks and SCBE fusion evidence.",
        },
    },
    {
        "scenario": "aspirin_adapter_promotion",
        "split": "eval",
        "user": "Should aspirin `CC(=O)Oc1ccccc1C(=O)O` pass the adapter gate?",
        "answer": {
            "schema_version": "scbe_chemistry_adapter_invariant_answer_v1",
            "invariant": "complex_valid_molecule_promotion",
            "smiles": "CC(=O)Oc1ccccc1C(=O)O",
            "expected": {
                "can_promote": True,
                "rdkit_ok": True,
                "valence_ok": True,
                "fusion_ok": True,
            },
            "reasoning": [
                "Aspirin parses as a valid organic molecule.",
                "Carbonyl, ester, acid, and aromatic valences are satisfied.",
                "SCBE fusion must not reject a valid molecule without threshold evidence.",
            ],
            "gate": "ALLOW when parser, valence, fusion, and thresholds agree.",
        },
    },
]


def _sha(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _record(case: dict[str, Any]) -> dict[str, Any]:
    assistant = json.dumps(case["answer"], sort_keys=True, ensure_ascii=True)
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": case["user"]},
            {"role": "assistant", "content": assistant},
        ],
        "metadata": {
            "track": "chemistry_adapter_invariants_v1",
            "scenario": case["scenario"],
            "split": case["split"],
            "training_pattern": "adapter_invariant_to_gate_receipt",
            "source_files": [
                "python/scbe/chemistry_adapter.py",
                "python/scbe/atomic_tokenization.py",
                "tests/test_chemistry_adapter.py",
            ],
        },
    }
    payload["id"] = f"chemistry_adapter_invariants_v1_{case['scenario']}_{_sha(payload)[:16]}"
    return payload


def build_records() -> list[dict[str, Any]]:
    return [_record(case) for case in CASES]


def split_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train = [row for row in records if row["metadata"]["split"] == "train"]
    eval_rows = [row for row in records if row["metadata"]["split"] == "eval"]
    return train, eval_rows


def write_outputs(out_dir: Path, *, copy_kaggle: bool = False, kaggle_dir: Path = DEFAULT_KAGGLE_DIR) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    records = build_records()
    train, eval_rows = split_records(records)

    train_path = out_dir / TRAIN_NAME
    eval_path = out_dir / EVAL_NAME
    manifest_path = out_dir / MANIFEST_NAME

    for path, rows in ((train_path, train), (eval_path, eval_rows)):
        path.write_text(
            "\n".join(json.dumps(row, sort_keys=True, ensure_ascii=True) for row in rows) + "\n",
            encoding="utf-8",
        )

    manifest = {
        "schema_version": "chemistry_adapter_invariants_manifest_v1",
        "track": "chemistry_adapter_invariants_v1",
        "train_file": str(train_path.relative_to(REPO_ROOT)),
        "eval_file": str(eval_path.relative_to(REPO_ROOT)),
        "train_records": len(train),
        "eval_records": len(eval_rows),
        "source_files": [
            "python/scbe/chemistry_adapter.py",
            "python/scbe/atomic_tokenization.py",
            "tests/test_chemistry_adapter.py",
        ],
        "invariants": [case["answer"]["invariant"] for case in CASES],
        "files": {
            TRAIN_NAME: _sha(train),
            EVAL_NAME: _sha(eval_rows),
        },
        "gate": {
            "decision": (
                "PASS only if responses preserve adapter booleans, real chemistry element mapping, "
                "threshold denial, and no promotion without RDKit, valence, fusion, and policy agreement."
            ),
            "blocked": [
                "missing_adapter_booleans",
                "all_elements_as_fe",
                "promotion_without_rdkit",
                "promotion_without_valence",
                "threshold_denial_ignored",
            ],
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")

    copied: list[str] = []
    if copy_kaggle:
        kaggle_dir.mkdir(parents=True, exist_ok=True)
        for path in (train_path, eval_path, manifest_path):
            target = kaggle_dir / path.name
            shutil.copy2(path, target)
            copied.append(str(target.relative_to(REPO_ROOT)))

    return {
        "ok": True,
        "train_records": len(train),
        "eval_records": len(eval_rows),
        "train_path": str(train_path),
        "eval_path": str(eval_path),
        "manifest_path": str(manifest_path),
        "copied_to_kaggle": copied,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--copy-kaggle", action="store_true")
    parser.add_argument("--kaggle-dir", type=Path, default=DEFAULT_KAGGLE_DIR)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = write_outputs(args.out_dir, copy_kaggle=args.copy_kaggle, kaggle_dir=args.kaggle_dir)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        print(
            "chemistry adapter invariants SFT: "
            f"train={result['train_records']} eval={result['eval_records']} "
            f"train_path={result['train_path']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
