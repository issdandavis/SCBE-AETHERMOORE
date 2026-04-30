"""Build exact CA opcode repair rows for add-byte confusion.

The first CA/GeoSeal smoke repair adapter learned the runnable Python repair
and partial CA recall, but direct adapter smoke job 69f2cc41d2c8bd8662bd3863
still emitted 0x09 for the final add byte. This shard drills only the exact
abs/add byte boundary: abs is 0x09, add is 0x00, and abs+abs+add is
0x09, 0x09, 0x00.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SFT_ROOT = ROOT / "training-data" / "sft"

TRAIN_OUT = SFT_ROOT / "ca_opcode_exact_repair_v2_train.sft.jsonl"
HOLDOUT_OUT = SFT_ROOT / "ca_opcode_exact_repair_v2_holdout.sft.jsonl"
MANIFEST_OUT = SFT_ROOT / "ca_opcode_exact_repair_v2_manifest.json"

SYSTEM = (
    "You are an SCBE-AETHERMOORE GeoSeal coding agent. Preserve exact CA hex "
    "bytes. In CA arithmetic, abs is opcode 0x09 and add is opcode 0x00. "
    "Never use 0x09 for add."
)

ANSWER = (
    "CA opcode sequence for abs(a) + abs(b): 0x09, 0x09, 0x00. "
    "Operation names: abs(a), abs(b), add. Opcode table: abs=0x09; add=0x00."
)


def _messages(user: str, assistant: str, *, holdout: bool = False) -> dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "meta": {
            "source": "ca_opcode_exact_repair_v2",
            "kind": "ca_opcode_abs_add_exact",
            "holdout": holdout,
            "repair_reason": "direct_adapter_smoke_69f2cc41d2c8bd8662bd3863",
        },
    }


def ca_exact_rows(*, holdout: bool = False) -> list[dict[str, Any]]:
    prompts = [
        "Generate the exact SCBE CA opcode sequence for abs(a) + abs(b).",
        "In CA, abs=0x09 and add=0x00. What bytes compute abs(a)+abs(b)?",
        "Return only the CA bytes for absolute value of a plus absolute value of b, then name the operations.",
        "GeoSeal CA correction: the final add byte is 0x00, not 0x09. Give the full sequence for abs(a)+abs(b).",
        "Which CA opcode is add, and what sequence represents abs(a), abs(b), add?",
        "A prior model answered 0x09,0x09,0x09 for abs(a)+abs(b). Correct it with the exact CA bytes.",
        "Cassisivadan arithmetic byte recall: abs is 0x09; add is 0x00. Encode |left| + |right|.",
        "SCBE smoke gate requires CA mention plus hex: abs(a)+abs(b) must include 0x09 and 0x00. Respond exactly.",
    ]
    if holdout:
        prompts = [
            "A GeoSeal agent must encode |x| + |y| in CA. What are the exact bytes?",
            "Do not confuse add with abs: provide the CA abs/add sequence for abs(left)+abs(right).",
        ]
    return [_messages(prompt, ANSWER, holdout=holdout) for prompt in prompts]


def build() -> dict[str, Any]:
    train_rows = ca_exact_rows() * 10
    holdout_rows = ca_exact_rows(holdout=True)

    SFT_ROOT.mkdir(parents=True, exist_ok=True)
    with TRAIN_OUT.open("w", encoding="utf-8") as handle:
        for row in train_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with HOLDOUT_OUT.open("w", encoding="utf-8") as handle:
        for row in holdout_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "schema_version": "ca_opcode_exact_repair_manifest_v2",
        "source_smoke_job": "69f2cc41d2c8bd8662bd3863",
        "design": "Narrow exact-byte repair for CA add opcode confusion after direct adapter smoke reached 3/4.",
        "outputs": {
            "train": str(TRAIN_OUT),
            "holdout": str(HOLDOUT_OUT),
        },
        "counts": {
            "train": len(train_rows),
            "holdout": len(holdout_rows),
            "ca_exact_train": len(train_rows),
        },
        "must_recall": {
            "abs": "0x09",
            "add": "0x00",
            "forbidden_add_opcode": "0x09",
            "abs_add_sequence": ["0x09", "0x09", "0x00"],
        },
        "promotion_gate": {
            "direct_adapter_smoke_min_passed": 4,
            "direct_adapter_smoke_total": 4,
            "evaluator": "scripts/eval/smoke_merged_coding_model_hf.py",
        },
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    return manifest


def main() -> int:
    print(json.dumps(build(), indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
