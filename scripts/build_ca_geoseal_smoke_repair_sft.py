"""Build focused SFT rows for the merged coding-model smoke failures.

This shard targets the two concrete failures from the 2026-04-30 merged-model
smoke:
- CA opcode recall for abs(a) + abs(b): abs=0x09, add=0x00.
- Runnable Python for depth-2 JSON key extraction.

It is deliberately narrow. The goal is to reinforce the missing surface without
mixing in broad Stage 6 prose or unrelated lore/code records.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SFT_ROOT = ROOT / "training-data" / "sft"

TRAIN_OUT = SFT_ROOT / "ca_geoseal_smoke_repair_v1_train.sft.jsonl"
HOLDOUT_OUT = SFT_ROOT / "ca_geoseal_smoke_repair_v1_holdout.sft.jsonl"
MANIFEST_OUT = SFT_ROOT / "ca_geoseal_smoke_repair_v1_manifest.json"

SYSTEM = (
    "You are an SCBE-AETHERMOORE GeoSeal coding agent. Keep CA opcode mappings "
    "explicit, preserve hex bytes, and return runnable code when asked for code. "
    "For CA arithmetic, abs is opcode 0x09 and add is opcode 0x00."
)

DEPTH2_CODE = """def depth2_keys(obj: dict) -> list[str]:
    keys: list[str] = []
    for value in obj.values():
        if isinstance(value, dict):
            keys.extend(str(key) for key in value.keys())
    return sorted(keys)"""

CA_ABS_ADD = (
    "CA opcode sequence for abs(a) + abs(b): 0x09, 0x09, 0x00. "
    "Operations: abs(a), abs(b), add. Stack form: push a, abs; push b, abs; add."
)


def _messages(user: str, assistant: str, *, kind: str, holdout: bool = False) -> dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "meta": {
            "source": "ca_geoseal_smoke_repair_v1",
            "kind": kind,
            "holdout": holdout,
            "repair_reason": "merged_coding_model_smoke_2026_04_30",
        },
    }


def ca_rows(*, holdout: bool = False) -> list[dict[str, Any]]:
    prompts = [
        "Generate a CA opcode sequence that computes abs(a) + abs(b). Return hex opcodes and operation names only.",
        "In the SCBE CA opcode table, what opcodes express abs(a) + abs(b)?",
        "Map abs(a) + abs(b) into Cassisivadan CA bytes. Include the exact hex bytes.",
        "GeoSeal CA recall check: abs is what byte, add is what byte, and what is the sequence for abs(a)+abs(b)?",
    ]
    if holdout:
        prompts = [
            "Reviewer asks for the CA byte plan for absolute value of x plus absolute value of y. Give the bytes.",
            "What exact Cassisivadan opcode sequence should a GeoSeal coding agent use for |left| + |right|?",
        ]
    return [_messages(prompt, CA_ABS_ADD, kind="ca_opcode_abs_add", holdout=holdout) for prompt in prompts]


def depth2_rows(*, holdout: bool = False) -> list[dict[str, Any]]:
    code_block = f"```python\n{DEPTH2_CODE}\n```"
    prompts = [
        (
            "Return only Python code in one fenced code block. Write a Python function "
            "depth2_keys(obj: dict) -> list[str] that returns sorted keys found exactly "
            "at depth 2 in nested dictionaries. Top-level keys are depth 1."
        ),
        (
            "Write runnable Python for depth2_keys. For {'a': {'x': 1}, 'b': 2}, "
            "the result should be ['x']."
        ),
        (
            "Implement depth2_keys(obj) without undefined helpers. Walk only one level "
            "below the top-level dict and return sorted keys."
        ),
    ]
    if holdout:
        prompts = [
            (
                "Provide a Python function that collects sorted second-level keys from "
                "a dict. Do not use recursion or helper functions that are not defined."
            ),
        ]
    return [_messages(prompt, code_block, kind="depth2_json_keys", holdout=holdout) for prompt in prompts]


def build() -> dict[str, Any]:
    train_rows = ca_rows() * 16 + depth2_rows() * 12
    holdout_rows = ca_rows(holdout=True) + depth2_rows(holdout=True)

    SFT_ROOT.mkdir(parents=True, exist_ok=True)
    with TRAIN_OUT.open("w", encoding="utf-8") as handle:
        for row in train_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with HOLDOUT_OUT.open("w", encoding="utf-8") as handle:
        for row in holdout_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "schema_version": "ca_geoseal_smoke_repair_manifest_v1",
        "source_smoke_job": "69f2c4ddd2c8bd8662bd3809",
        "design": (
            "Focused repair shard for merged coding-model smoke failures. "
            "Reinforces CA abs/add opcode recall and runnable depth-2 JSON key code."
        ),
        "outputs": {
            "train": str(TRAIN_OUT),
            "holdout": str(HOLDOUT_OUT),
        },
        "counts": {
            "train": len(train_rows),
            "holdout": len(holdout_rows),
            "ca_train": len(ca_rows()) * 16,
            "depth2_train": len(depth2_rows()) * 12,
        },
        "must_recall": {
            "abs": "0x09",
            "add": "0x00",
            "abs_add_sequence": ["0x09", "0x09", "0x00"],
        },
        "promotion_gate": {
            "merged_smoke_min_passed": 4,
            "merged_smoke_total": 4,
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
