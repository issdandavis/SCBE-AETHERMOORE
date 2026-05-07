#!/usr/bin/env python3
"""Build targeted SFT rows from chemistry v6 raw gate misses.

The v6 scaffolded-marker run passed the deterministic wrapper gate 5/5 but
raw model output passed 0/5. The raw misses were mostly exact-anchor failures
and near-miss corruptions:

- `carboxyllic acid` instead of `carboxylic acid`
- `NA_clathrine` instead of `NaCl`
- `queue_drill_guard` instead of `queue_drain_guard`
- missing `SCBE fusion`, `oxygen`, `alcohol`, `not a molecule`

This shard teaches exact anchor preservation without copying the frozen eval
prompts verbatim. It is meant for a future raw-only diagnostic or v7-style
repair experiment, not for claiming that v6 succeeded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "training-data" / "sft"
TRAIN_NAME = "chemistry_raw_anchor_repair_v1_train.sft.jsonl"
EVAL_NAME = "chemistry_raw_anchor_repair_v1_eval.sft.jsonl"
MANIFEST_NAME = "chemistry_raw_anchor_repair_v1_manifest.json"

SYSTEM = (
    "You are an SCBE-AETHERMOORE chemistry raw-anchor repair specialist. "
    "Preserve exact chemistry and lane-boundary anchors. When a near-miss token "
    "is shown, correct it explicitly and then give the concise verification path. "
    "Do not invent alternate spellings or substitute similar-looking identifiers."
)


CASES: list[dict[str, Any]] = [
    {
        "case_id": "aspirin_carboxylic_anchor",
        "split": "train",
        "bad": "carboxyllic acid",
        "good": "carboxylic acid",
        "prompts": [
            "Repair this raw aspirin verification anchor: the model wrote carboxyllic acid. Correct the anchor and verify the functional groups.",
            "A chemistry gate requires the exact phrase carboxylic acid. The raw answer wrote carboxyllic acid. Produce the corrected aspirin route.",
            "For aspirin, preserve aromatic ring, ester, carboxylic acid, valence, governance, and PASS exactly.",
        ],
        "answer": (
            "ANCHOR_REPAIR=carboxyllic acid -> carboxylic acid\n"
            "REQUIRED_MARKERS=aspirin | aromatic | ester | carboxylic acid | valid | valence | governance | PASS\n"
            "Aspirin contains an aromatic ring, an ester, and a carboxylic acid. "
            "The exact anchor is carboxylic acid. Valence is valid and the governance verdict is PASS."
        ),
    },
    {
        "case_id": "nacl_symbol_anchor",
        "split": "train",
        "bad": "NA_clathrine",
        "good": "NaCl",
        "prompts": [
            "Repair this raw ionic-boundary miss: the model wrote NA_clathrine. Correct it and verify the sodium chloride boundary.",
            "A chemistry gate requires NaCl exactly. The raw answer wrote NA_clathrine. Produce the corrected boundary response.",
            "Preserve NaCl, ionic, sodium, chloride, not organic, valid, and governance exactly.",
        ],
        "answer": (
            "ANCHOR_REPAIR=NA_clathrine -> NaCl\n"
            "REQUIRED_MARKERS=NaCl | ionic | sodium | chloride | not organic | valid | governance\n"
            "NaCl is sodium chloride. It is ionic chemistry, not organic chemistry. "
            "The exact anchor is NaCl, and the conservative governance verdict is valid boundary handling."
        ),
    },
    {
        "case_id": "queue_drain_guard_boundary_anchor",
        "split": "train",
        "bad": "queue_drill_guard",
        "good": "queue_drain_guard",
        "prompts": [
            "Repair this lane-boundary miss: the raw answer wrote queue_drill_guard. Correct the code token and state the chemistry boundary.",
            "A gate requires queue_drain_guard and not a molecule exactly. The raw answer changed the identifier. Produce the corrected boundary response.",
            "Preserve queue_drain_guard, not a molecule, avoid, real atoms, structural, and atomic tokenizer exactly.",
        ],
        "answer": (
            "ANCHOR_REPAIR=queue_drill_guard -> queue_drain_guard\n"
            "REQUIRED_MARKERS=material chemistry | structural | atomic tokenizer | queue_drain_guard | not a molecule | avoid | real atoms\n"
            "queue_drain_guard is a code token, not a molecule. The chemistry agent must avoid claiming "
            "real atoms, RDKit validation, or a chemical formula for this identifier."
        ),
    },
    {
        "case_id": "ethanol_missing_functional_group",
        "split": "train",
        "bad": "missing oxygen/alcohol/SCBE fusion",
        "good": "oxygen | alcohol | SCBE fusion",
        "prompts": [
            "Repair an ethanol route that forgot oxygen, alcohol, and SCBE fusion. Include every required anchor.",
            "For CCO, preserve carbon, oxygen, valence, alcohol, RDKit, SCBE fusion, and PASS exactly.",
            "The raw ethanol answer named CCO but omitted the functional group and fusion marker. Produce the corrected concise route.",
        ],
        "answer": (
            "ANCHOR_REPAIR=missing oxygen/alcohol/SCBE fusion -> oxygen | alcohol | SCBE fusion\n"
            "REQUIRED_MARKERS=CCO | carbon | oxygen | valence | alcohol | RDKit | SCBE fusion | PASS\n"
            "CCO is ethanol. It contains carbon and oxygen, satisfies valence, has an alcohol group, "
            "is RDKit-valid, has finite SCBE fusion, and receives governance verdict PASS."
        ),
    },
    {
        "case_id": "pentavalent_exact_smiles_anchor",
        "split": "train",
        "bad": "mutated C(C)(C)(C)(C)C",
        "good": "C(C)(C)(C)(C)C",
        "prompts": [
            "Repair a pentavalent-carbon rejection where the raw answer mutated the proposed SMILES. Preserve the exact string and deny it.",
            "The gate requires C(C)(C)(C)(C)C exactly. Produce the invalid valence route with DENY.",
            "Preserve carbon, valence, pentavalent, invalid, RDKit, and DENY for the exact C(C)(C)(C)(C)C proposal.",
        ],
        "answer": (
            "ANCHOR_REPAIR=mutated C(C)(C)(C)(C)C -> C(C)(C)(C)(C)C\n"
            "REQUIRED_MARKERS=C(C)(C)(C)(C)C | carbon | valence | pentavalent | invalid | RDKit | DENY\n"
            "C(C)(C)(C)(C)C creates a pentavalent carbon claim. Carbon valence exceeds 4, "
            "the material chemistry route is invalid, and the governance verdict is DENY."
        ),
    },
]

EVAL_CASES: list[dict[str, Any]] = [
    {
        "case_id": "eval_carboxylate_spelling_boundary",
        "split": "eval",
        "bad": "carboxalate acid",
        "good": "carboxylic acid",
        "prompts": [
            "Correct carboxalate acid to the exact aspirin functional-group anchor and give the concise route."
        ],
        "answer": (
            "ANCHOR_REPAIR=carboxalate acid -> carboxylic acid\n"
            "REQUIRED_MARKERS=aspirin | aromatic | ester | carboxylic acid | valid | valence | governance | PASS\n"
            "The exact functional-group anchor is carboxylic acid."
        ),
    },
    {
        "case_id": "eval_identifier_boundary",
        "split": "eval",
        "bad": "queue_drainage_guard",
        "good": "queue_drain_guard",
        "prompts": [
            "Correct queue_drainage_guard to the exact code identifier and state why it is not material chemistry."
        ],
        "answer": (
            "ANCHOR_REPAIR=queue_drainage_guard -> queue_drain_guard\n"
            "REQUIRED_MARKERS=structural | atomic tokenizer | queue_drain_guard | not a molecule | avoid | real atoms\n"
            "queue_drain_guard is a code identifier, not a molecule."
        ),
    },
]


def _sha(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _record(case: dict[str, Any], prompt: str, repeat_index: int) -> dict[str, Any]:
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": case["answer"]},
        ],
        "metadata": {
            "track": "chemistry_raw_anchor_repair_v1",
            "case_id": case["case_id"],
            "split": case["split"],
            "repeat_index": repeat_index,
            "bad_anchor": case["bad"],
            "good_anchor": case["good"],
            "source_hf_job": "69fc98b3317220dbbd1a5d52",
            "source_review": "docs/ops/TRAINING_RUN_REVIEW_CHEMISTRY_V6_2026-05-07.md",
        },
    }
    payload["id"] = f"chemistry_raw_anchor_repair_v1_{case['split']}_{case['case_id']}_{repeat_index}_{_sha(payload)[:16]}"
    return payload


def build_records(repeats: int = 6) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train: list[dict[str, Any]] = []
    for case in CASES:
        for prompt in case["prompts"]:
            for repeat_index in range(repeats):
                train.append(_record(case, prompt, repeat_index))
    eval_rows = [_record(case, prompt, 0) for case in EVAL_CASES for prompt in case["prompts"]]
    return train, eval_rows


def write_outputs(out_dir: Path, *, repeats: int = 6) -> dict[str, Any]:
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
        "schema_version": "chemistry_raw_anchor_repair_manifest_v1",
        "track": "chemistry_raw_anchor_repair_v1",
        "train_file": str(train_path.relative_to(REPO_ROOT)),
        "eval_file": str(eval_path.relative_to(REPO_ROOT)),
        "train_records": len(train),
        "eval_records": len(eval_rows),
        "repeats": repeats,
        "source_hf_job": "69fc98b3317220dbbd1a5d52",
        "source_raw_pass_rate": 0.0,
        "source_scaffolded_pass_rate": 1.0,
        "repair_pairs": [{"bad": case["bad"], "good": case["good"]} for case in CASES + EVAL_CASES],
        "files": {
            TRAIN_NAME: _sha(train),
            EVAL_NAME: _sha(eval_rows),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
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
    parser.add_argument("--repeats", type=int, default=6)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = write_outputs(args.out_dir, repeats=args.repeats)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        print(
            "chemistry raw anchor repair SFT: "
            f"train={result['train_records']} eval={result['eval_records']} "
            f"train_path={result['train_path']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
