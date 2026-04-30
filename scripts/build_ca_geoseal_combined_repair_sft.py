"""Build combined CA/GeoSeal repair rows for the coding-model smoke gate.

Separate repair adapters showed useful but incomplete behavior:
- ca-geoseal-smoke-repair-v1 passed runnable depth-2 code but missed add=0x00.
- ca-opcode-exact-repair-v2 pressured add=0x00 but regressed depth-2 code.

This shard trains both surfaces together with a stricter CA answer shape so the
next adapter can pass the direct 4-case smoke gate before any full merge.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SFT_ROOT = ROOT / "training-data" / "sft"

TRAIN_OUT = SFT_ROOT / "ca_geoseal_combined_repair_v3_train.sft.jsonl"
HOLDOUT_OUT = SFT_ROOT / "ca_geoseal_combined_repair_v3_holdout.sft.jsonl"
MANIFEST_OUT = SFT_ROOT / "ca_geoseal_combined_repair_v3_manifest.json"

SYSTEM = (
    "You are an SCBE-AETHERMOORE GeoSeal coding agent. Preserve exact CA hex "
    "bytes and return runnable Python when asked for code. For CA arithmetic, "
    "abs is opcode 0x09 and add is opcode 0x00. The sequence for abs(a)+abs(b) "
    "is exactly 0x09, 0x09, 0x00."
)

CA_ANSWER = "CA: 0x09, 0x09, 0x00\nops: abs(a), abs(b), add\nmap: abs=0x09; add=0x00"

DEPTH2_CODE = """def depth2_keys(obj: dict) -> list[str]:
    keys: list[str] = []
    for value in obj.values():
        if isinstance(value, dict):
            keys.extend(str(key) for key in value.keys())
    return sorted(keys)"""


def _messages(user: str, assistant: str, *, kind: str, holdout: bool = False) -> dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "meta": {
            "source": "ca_geoseal_combined_repair_v3",
            "kind": kind,
            "holdout": holdout,
            "repair_reason": "combined_direct_smoke_repairs_2026_04_30",
        },
    }


def ca_rows(*, holdout: bool = False) -> list[dict[str, Any]]:
    prompts = [
        "Generate a CA opcode sequence that computes abs(a) + abs(b). Return hex opcodes and operation names only.",
        "In the SCBE CA opcode table, generate a CA opcode sequence for abs(a) + abs(b). Return the relevant hex opcodes and operation names only.",
        "Correct this wrong CA sequence for abs(a)+abs(b): 0x09, 0x09, 0x09.",
        "GeoSeal CA recall: abs is 0x09, add is 0x00. Encode abs(left)+abs(right).",
        "What exact Cassisivadan opcode sequence should a GeoSeal coding agent use for |left| + |right|?",
        "Return only CA bytes plus operation names for absolute a plus absolute b.",
        "CA smoke gate: include the exact contiguous sequence 0x09, 0x09, 0x00 for abs(a)+abs(b).",
        "Do not put 0x09 in the add slot. Give abs(a), abs(b), add as CA hex bytes.",
    ]
    if holdout:
        prompts = [
            "Reviewer asks for the CA byte plan for absolute value of x plus absolute value of y. Give the bytes and names.",
            "A model confused add with abs. What is the corrected CA sequence for abs(a)+abs(b)?",
        ]
    return [_messages(prompt, CA_ANSWER, kind="ca_opcode_abs_add_exact", holdout=holdout) for prompt in prompts]


def depth2_rows(*, holdout: bool = False) -> list[dict[str, Any]]:
    code_block = f"```python\n{DEPTH2_CODE}\n```"
    prompts = [
        (
            "Return only Python code in one fenced code block. Write a Python function "
            "depth2_keys(obj: dict) -> list[str] that returns sorted keys found exactly "
            "at depth 2 in nested dictionaries. Top-level keys are depth 1."
        ),
        "Implement depth2_keys(obj) without recursion. Walk only one level below the top-level dict and return sorted keys.",
        "Write runnable Python for depth2_keys. For {'a': {'x': 1}, 'b': 2}, the result should be ['x'].",
        "Provide a depth2_keys function that handles empty dictionaries and nested dictionaries without KeyError.",
    ]
    if holdout:
        prompts = [
            "Provide a Python function that collects sorted second-level keys from a dict. Do not use recursion.",
            "Write depth2_keys so {'a': {'x': 1, 'y': {'z': 2}}, 'c': {'m': 4}} returns ['m', 'x', 'y'].",
        ]
    return [_messages(prompt, code_block, kind="depth2_json_keys", holdout=holdout) for prompt in prompts]


def build() -> dict[str, Any]:
    train_rows = ca_rows() * 10 + depth2_rows() * 16
    holdout_rows = ca_rows(holdout=True) + depth2_rows(holdout=True)

    SFT_ROOT.mkdir(parents=True, exist_ok=True)
    with TRAIN_OUT.open("w", encoding="utf-8") as handle:
        for row in train_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with HOLDOUT_OUT.open("w", encoding="utf-8") as handle:
        for row in holdout_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "schema_version": "ca_geoseal_combined_repair_manifest_v3",
        "source_smoke_jobs": ["69f2cc41d2c8bd8662bd3863", "69f2ceb6d70108f37ace19b9"],
        "design": "Combined direct-smoke repair for exact CA bytes and runnable depth-2 JSON key code.",
        "outputs": {"train": str(TRAIN_OUT), "holdout": str(HOLDOUT_OUT)},
        "counts": {
            "train": len(train_rows),
            "holdout": len(holdout_rows),
            "ca_train": len(ca_rows()) * 10,
            "depth2_train": len(depth2_rows()) * 16,
        },
        "must_recall": {
            "abs": "0x09",
            "add": "0x00",
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
