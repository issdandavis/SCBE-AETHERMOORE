#!/usr/bin/env python3
"""Build focused DPO rows for exact CA abs/add opcode repair."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = REPO_ROOT / "training-data" / "dpo" / "ca_opcode_final_dpo_v1_train.jsonl"
MANIFEST_PATH = REPO_ROOT / "training-data" / "dpo" / "ca_opcode_final_dpo_v1_manifest.json"

SYSTEM = (
    "You are an SCBE-AETHERMOORE GeoSeal coding agent. For CA arithmetic, abs is opcode 0x09 "
    "and add is opcode 0x00. The sequence for abs(a)+abs(b) is exactly 0x09, 0x09, 0x00. "
    "Always include the add byte."
)

PROMPTS = [
    "In the SCBE CA opcode table, generate a CA opcode sequence for abs(a) + abs(b). Return the relevant hex opcodes and operation names only.",
    "Generate a CA opcode sequence that computes abs(a) + abs(b). Return hex opcodes and operation names only.",
    "CA smoke gate: include the exact contiguous sequence 0x09, 0x09, 0x00 for abs(a)+abs(b).",
    "A model wrote CA: 0x09 and named abs(a), abs(b), add, but forgot the add byte. Correct the CA sequence.",
    "Do not put 0x09 in the add slot. Give abs(a), abs(b), add as CA hex bytes.",
    "GeoSeal CA recall: abs is 0x09, add is 0x00. Encode abs(left)+abs(right).",
    "What exact Cassisivadan opcode sequence should a GeoSeal coding agent use for |left| + |right|?",
    "Return only CA bytes plus operation names for absolute a plus absolute b.",
]

CHOSEN = [
    "CA: 0x09, 0x09, 0x00\nops: abs(a), abs(b), add\nmap: abs=0x09; add=0x00",
    "CA sequence: 0x09, 0x09, 0x00\noperation names: abs(a), abs(b), add",
    "0x09, 0x09, 0x00\nabs(a), abs(b), add",
    "CA: [0x09, 0x09, 0x00]\nabs=0x09; abs=0x09; add=0x00",
]

REJECTED = [
    "CA: 0x09\nOPCODES: abs(a), abs(b), add\nOPERATION_NAMES: abs, abs, add",
    "CA: 0x09\nOP: ABS\nARG1: a\nARG2: b\nCA: 0x09\nOP: ABS\nARG1: abs(a)\nARG2: abs(b)",
    "CA: 0x09, 0x09\nops: abs(a), abs(b), add",
    "CA: 0x09, 0x09, 0x09\nops: abs(a), abs(b), abs",
    "0x09\nabs(a), abs(b), add",
]


def build_rows() -> list[dict]:
    rows: list[dict] = []
    for index, prompt in enumerate(PROMPTS):
        for chosen in CHOSEN:
            for rejected in REJECTED:
                rows.append(
                    {
                        "system": SYSTEM,
                        "prompt": prompt,
                        "chosen": chosen,
                        "rejected": rejected,
                        "meta": {
                            "source": "ca_opcode_final_dpo_v1",
                            "kind": "ca_abs_add_exact_preference",
                            "prompt_index": index,
                            "required_sequence": "0x09, 0x09, 0x00",
                            "repair_reason": "hf_smoke_69f58f929d85bec4d76f02ee_and_69f599bd9d85bec4d76f0364",
                        },
                    }
                )
    return rows


def main() -> int:
    rows = build_rows()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    manifest = {
        "schema_version": "scbe_dpo_dataset_manifest_v1",
        "dataset_id": "ca_opcode_final_dpo_v1",
        "row_count": len(rows),
        "output": str(OUT_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
        "required_sequence": "0x09, 0x09, 0x00",
        "prompts": len(PROMPTS),
        "chosen_variants": len(CHOSEN),
        "rejected_variants": len(REJECTED),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
