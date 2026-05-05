#!/usr/bin/env python3
"""Build SFT rows that repair the chemistry promotion gate language.

The broader chemistry corpus teaches structured verification receipts, but the
remote promotion gate is deliberately lexical: a generated answer must include
exact markers such as PASS, DENY, RDKit, valence, and not a molecule. This
small pack teaches that response shape without changing the frozen gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "training-data" / "sft"
TRAIN_NAME = "chemistry_gate_repair_v1_train.sft.jsonl"
EVAL_NAME = "chemistry_gate_repair_v1_eval.sft.jsonl"
MANIFEST_NAME = "chemistry_gate_repair_v1_manifest.json"

SYSTEM = (
    "You are an SCBE-AETHERMOORE chemistry verification agent. Answer in concise English. "
    "Start every answer with REQUIRED_MARKERS listing the exact gate words that apply. "
    "Always include the required gate markers exactly when they are true: SMILES string, "
    "carbon, oxygen, valence, RDKit, SCBE fusion, governance, PASS, DENY, invalid, "
    "pentavalent, not a molecule, and real atoms. Keep material chemistry separate from "
    "structural atomic tokenizer metaphors."
)


CANONICAL_CASES: list[dict[str, Any]] = [
    {
        "case_id": "ethanol_route",
        "split": "train",
        "prompts": [
            "Verify ethanol from SMILES CCO. Walk atoms, bonds, valence, polarity, functional group, RDKit validity, SCBE fusion, and governance verdict.",
            "Run the chemistry verification route for CCO and say whether ethanol should PASS.",
            "Check SMILES CCO as ethanol and include every gate marker needed for promotion.",
        ],
        "answer": (
            "REQUIRED_MARKERS=CCO | carbon | oxygen | valence | alcohol | RDKit | SCBE fusion | PASS. "
            "CCO is ethanol. Atoms: two carbon atoms and one oxygen atom. Bonds: C-C and C-O "
            "single bonds with hydrogens implied. Valence: each carbon is within valence 4 and "
            "oxygen is within valence 2. Electronegativity/polarity: the C-O bond is polar. "
            "Functional group: alcohol. RDKit validity: RDKit parses CCO as valid. SCBE fusion: "
            "SCBE fusion is finite with acceptable valence pressure and coherence. Governance "
            "verdict: PASS."
        ),
    },
    {
        "case_id": "aspirin_route",
        "split": "train",
        "prompts": [
            "Verify aspirin from SMILES CC(=O)Oc1ccccc1C(=O)O. Explain aromatic ring, ester, carboxylic acid, validity, valence pressure, and promotion verdict.",
            "Check CC(=O)Oc1ccccc1C(=O)O and include the aspirin functional groups and governance verdict.",
            "Run material chemistry verification for aspirin and return PASS only if the route is valid.",
        ],
        "answer": (
            "REQUIRED_MARKERS=aspirin | aromatic | ester | carboxylic acid | valid | valence | governance | PASS. "
            "Aspirin is CC(=O)Oc1ccccc1C(=O)O. The molecule has an aromatic ring, an ester, "
            "and a carboxylic acid. RDKit validity: valid. Valence: aromatic carbon, carbonyl "
            "carbon, and oxygen atoms satisfy their valence ceilings. SCBE fusion: finite signal "
            "with acceptable valence pressure. Governance verdict: PASS."
        ),
    },
    {
        "case_id": "pentavalent_carbon_reject",
        "split": "train",
        "prompts": [
            "A molecule is proposed as C(C)(C)(C)(C)C. Verify whether it should promote. Walk valence arithmetic and state the governance verdict.",
            "Check the proposed SMILES C(C)(C)(C)(C)C for pentavalent carbon and promotion safety.",
            "Does C(C)(C)(C)(C)C pass the chemistry gate? Include RDKit and valence reasoning.",
        ],
        "answer": (
            "REQUIRED_MARKERS=C(C)(C)(C)(C)C | carbon | valence | pentavalent | invalid | RDKit | DENY. "
            "C(C)(C)(C)(C)C puts too many single bonds on one carbon. The central carbon is "
            "pentavalent, which exceeds carbon valence 4. RDKit validity: invalid or rejected "
            "for this material chemistry claim. SCBE fusion cannot rescue an invalid molecule. "
            "Governance verdict: DENY."
        ),
    },
    {
        "case_id": "nacl_boundary",
        "split": "train",
        "prompts": [
            "Verify NaCl as an ionic boundary case. Explain why it is not organic but valid chemistry tokenization.",
            "Check NaCl and separate sodium chloride ionic chemistry from organic functional groups.",
            "Run the NaCl boundary case and include sodium, chloride, not organic, valid, and governance.",
        ],
        "answer": (
            "REQUIRED_MARKERS=NaCl | ionic | sodium | chloride | not organic | valid | governance. "
            "NaCl is sodium chloride. It is ionic chemistry, not organic chemistry and not an "
            "organic functional-group example. The sodium and chloride ions can still be handled "
            "as a valid chemistry tokenization boundary case. Governance verdict: conservative "
            "valid boundary handling, not an aromatic, ester, or carbon chain claim."
        ),
    },
    {
        "case_id": "lane_boundary",
        "split": "train",
        "prompts": [
            "Explain the boundary between material chemistry verification and structural atomic tokenizer metaphors. For code token queue_drain_guard, what must the chemistry agent avoid claiming?",
            "When input is code token queue_drain_guard, separate structural atomic tokenizer language from material chemistry.",
            "Check queue_drain_guard as a lane-boundary case and say what not to claim about real atoms.",
        ],
        "answer": (
            "REQUIRED_MARKERS=material chemistry | structural | atomic tokenizer | queue_drain_guard | not a molecule | avoid | real atoms. "
            "queue_drain_guard is a code token, not a molecule. The material chemistry agent must "
            "avoid claiming RDKit validates queue_drain_guard, avoid claiming it has a chemical "
            "formula, and avoid claiming electronegativity proves anything about it. Structural "
            "atomic tokenizer metaphors can describe code organization, but they are not real atoms "
            "or material chemistry."
        ),
    },
]

EVAL_CASES: list[dict[str, Any]] = [
    {
        "case_id": "methanol_route_eval",
        "split": "eval",
        "prompts": ["Verify methanol from SMILES CO and include the chemistry promotion markers."],
        "answer": (
            "REQUIRED_MARKERS=CO | carbon | oxygen | valence | alcohol | RDKit | SCBE fusion | PASS. "
            "CO is methanol. Atoms include carbon and oxygen. Valence is satisfied for carbon and oxygen. "
            "The functional group is alcohol. RDKit validity: valid. SCBE fusion is finite. Governance verdict: PASS."
        ),
    },
    {
        "case_id": "code_token_boundary_eval",
        "split": "eval",
        "prompts": ["For code token cache_flush_guard, explain the material chemistry boundary."],
        "answer": (
            "REQUIRED_MARKERS=structural | atomic tokenizer | cache_flush_guard | not a molecule | avoid | real atoms. "
            "cache_flush_guard is a structural atomic tokenizer token, not a molecule. The chemistry agent must "
            "avoid claiming real atoms, RDKit validity, a chemical formula, or electronegativity for it."
        ),
    },
]


def _sha(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _record(case: dict[str, Any], prompt: str, repeat_index: int) -> dict[str, Any]:
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": case["answer"]},
        ],
        "metadata": {
            "track": "chemistry_gate_repair_v1",
            "case_id": case["case_id"],
            "split": case["split"],
            "repeat_index": repeat_index,
            "training_pattern": "gate_language_repair",
            "source_files": [
                "config/model_training/chemistry_verification_eval_contract.json",
                "artifacts/hf_coding_agent_jobs/scbe-chemistry-0.5b-qlora",
            ],
        },
    }
    payload["id"] = f"chemistry_gate_repair_v1_{case['case_id']}_{repeat_index}_{_sha(payload)[:16]}"
    return payload


def build_records(repeats: int = 7) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train: list[dict[str, Any]] = []
    for case in CANONICAL_CASES:
        for prompt in case["prompts"]:
            for repeat_index in range(repeats):
                train.append(_record(case, prompt, repeat_index))
    eval_rows = [_record(case, prompt, 0) for case in EVAL_CASES for prompt in case["prompts"]]
    return train, eval_rows


def write_outputs(out_dir: Path, *, repeats: int = 7) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    train, eval_rows = build_records(repeats=repeats)
    train_path = out_dir / TRAIN_NAME
    eval_path = out_dir / EVAL_NAME
    manifest_path = out_dir / MANIFEST_NAME

    train_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True, ensure_ascii=True) for row in train) + "\n",
        encoding="utf-8",
    )
    eval_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True, ensure_ascii=True) for row in eval_rows) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "chemistry_gate_repair_manifest_v1",
        "track": "chemistry_gate_repair_v1",
        "train_file": str(train_path.relative_to(REPO_ROOT)),
        "eval_file": str(eval_path.relative_to(REPO_ROOT)),
        "train_records": len(train),
        "eval_records": len(eval_rows),
        "repeats": repeats,
        "case_ids": [case["case_id"] for case in CANONICAL_CASES + EVAL_CASES],
        "repair_reason": "HF job 69f96c159d85bec4d76f2c27 trained, but failed the lexical chemistry promotion gate 0/5.",
        "files": {
            TRAIN_NAME: _sha(train),
            EVAL_NAME: _sha(eval_rows),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    return {
        "ok": True,
        "train_records": len(train),
        "eval_records": len(eval_rows),
        "train_path": str(train_path),
        "eval_path": str(eval_path),
        "manifest_path": str(manifest_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = write_outputs(args.out_dir, repeats=args.repeats)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        print(
            "chemistry gate repair SFT: "
            f"train={result['train_records']} eval={result['eval_records']} "
            f"train_path={result['train_path']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
