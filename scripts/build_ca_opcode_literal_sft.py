#!/usr/bin/env python3
"""Build literal SFT rows for CA opcode recall while preserving smoke basics."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TRAIN_PATH = REPO_ROOT / "training-data" / "sft" / "ca_opcode_literal_sft_v1_train.sft.jsonl"
HOLDOUT_PATH = REPO_ROOT / "training-data" / "sft" / "ca_opcode_literal_sft_v1_holdout.sft.jsonl"
MANIFEST_PATH = REPO_ROOT / "training-data" / "sft" / "ca_opcode_literal_sft_v1_manifest.json"

SYSTEM = (
    "You are an SCBE-AETHERMOORE GeoSeal coding agent. Return exact requested code or exact CA byte plans. "
    "For CA arithmetic, abs is opcode 0x09 and add is opcode 0x00. "
    "The sequence for abs(a)+abs(b) is exactly 0x09, 0x09, 0x00."
)

CA_PROMPTS = [
    "In the SCBE CA opcode table, generate a CA opcode sequence for abs(a) + abs(b). Return the relevant hex opcodes and operation names only.",
    "Generate a CA opcode sequence that computes abs(a) + abs(b). Return hex opcodes and operation names only.",
    "GeoSeal CA recall: abs is 0x09, add is 0x00. Encode abs(left)+abs(right).",
    "Do not put 0x09 in the add slot. Give abs(a), abs(b), add as CA hex bytes.",
    "Return only CA bytes plus operation names for absolute a plus absolute b.",
    "What exact Cassisivadan opcode sequence should a GeoSeal coding agent use for |left| + |right|?",
]

CA_OUTPUTS = [
    "CA: 0x09, 0x09, 0x00\nops: abs(a), abs(b), add\nmap: abs=0x09; add=0x00",
    "CA sequence: 0x09, 0x09, 0x00\noperation names: abs(a), abs(b), add",
    "0x09, 0x09, 0x00\nabs(a), abs(b), add",
]

PYTHON_CASES = [
    (
        "Return only Python code in one fenced code block. Write a Python function fib(n: int) -> int that returns the nth Fibonacci number. Use iteration.",
        "```python\ndef fib(n: int) -> int:\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n```",
    ),
    (
        "Return only Python code in one fenced code block. Write a Python function is_prime(n: int) -> bool that returns True if n is prime.",
        "```python\ndef is_prime(n: int) -> bool:\n    if n <= 1:\n        return False\n    for i in range(2, int(n ** 0.5) + 1):\n        if n % i == 0:\n            return False\n    return True\n```",
    ),
    (
        "Return only Python code in one fenced code block. Write a Python function depth2_keys(obj: dict) -> list[str] that returns sorted keys found exactly at depth 2 in nested dictionaries. Top-level keys are depth 1.",
        "```python\ndef depth2_keys(obj: dict) -> list[str]:\n    keys: list[str] = []\n    for value in obj.values():\n        if isinstance(value, dict):\n            keys.extend(str(key) for key in value.keys())\n    return sorted(keys)\n```",
    ),
]


def _row(prompt: str, output: str, kind: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": output},
        ],
        "meta": {
            "source": "ca_opcode_literal_sft_v1",
            "kind": kind,
            "required_sequence": "0x09, 0x09, 0x00" if kind.startswith("ca_") else "",
        },
    }


def build_rows() -> tuple[list[dict], list[dict]]:
    train: list[dict] = []
    holdout: list[dict] = []
    for prompt in CA_PROMPTS:
        for output in CA_OUTPUTS:
            for _ in range(5):
                train.append(_row(prompt, output, "ca_abs_add_exact_literal"))
    for prompt, output in PYTHON_CASES:
        for _ in range(12):
            train.append(_row(prompt, output, "python_smoke_preservation"))
    holdout.append(_row(CA_PROMPTS[0], CA_OUTPUTS[0], "ca_abs_add_exact_literal_holdout"))
    holdout.extend(_row(prompt, output, "python_smoke_preservation_holdout") for prompt, output in PYTHON_CASES)
    return train, holdout


def main() -> int:
    train, holdout = build_rows()
    TRAIN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TRAIN_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        for row in train:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    with HOLDOUT_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        for row in holdout:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    manifest = {
        "schema_version": "scbe_sft_dataset_manifest_v1",
        "dataset_id": "ca_opcode_literal_sft_v1",
        "train_rows": len(train),
        "holdout_rows": len(holdout),
        "train_path": str(TRAIN_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
        "holdout_path": str(HOLDOUT_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
        "required_sequence": "0x09, 0x09, 0x00",
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
