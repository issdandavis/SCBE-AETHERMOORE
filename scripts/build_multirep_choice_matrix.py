#!/usr/bin/env python3
"""Build multi-representation choice records.

Each scenario is represented in English, Python, UTF-8 bytes, binary, and hex.
The records make the mapping explicit so a model can learn that the same
decision object has multiple faithful surfaces.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SYSTEM = (
    "You are an SCBE multi-representation coding instructor. Map the same "
    "decision across English, Python, UTF-8 bytes, binary, and hex. Preserve "
    "meaning exactly and explain how each surface maps back to the same object."
)


DECISIONS = [
    {
        "id": "timeout_rethink_kaggle",
        "english": "If a Kaggle training run times out, do not repeat the same run. Preserve logs, reduce scope, run a capped smoke test, then scale.",
        "python": "decision = {'scenario': 'timeout_rethink_kaggle', 'answer': 'B', 'move': 'RETHINK', 'next': 'capped_smoke_then_scale'}",
        "answer": "B",
        "move": "RETHINK",
    },
    {
        "id": "two_tongue_gcd_receipt",
        "english": "Semantic agreement between KO/Python and RU/Rust is proven by executing both implementations and receiving output 21.",
        "python": "decision = {'scenario': 'two_tongue_gcd_receipt', 'answer': 'B', 'move': 'TEST_RECEIPT', 'expected_output': 21}",
        "answer": "B",
        "move": "TEST_RECEIPT",
    },
    {
        "id": "invention_outside_cave",
        "english": "Invention must come from memory, evidence, rules, and need before it can move toward build.",
        "python": "decision = {'scenario': 'invention_outside_cave', 'answer': 'B', 'move': 'EVIDENCE_BEFORE_BUILD', 'anchors': ['memory', 'evidence', 'rules', 'need']}",
        "answer": "B",
        "move": "EVIDENCE_BEFORE_BUILD",
    },
]


def encode_surfaces(text: str) -> dict[str, object]:
    raw = text.encode("utf-8")
    return {
        "utf8_bytes": list(raw),
        "hex": raw.hex(".").upper(),
        "binary": " ".join(format(byte, "08b") for byte in raw),
    }


def build_response(item: dict) -> str:
    english = item["english"]
    python_code = item["python"]
    english_encoded = encode_surfaces(english)
    python_encoded = encode_surfaces(python_code)
    payload = {
        "scenario": item["id"],
        "answer": item["answer"],
        "move": item["move"],
        "english": english,
        "python": python_code,
        "english_hex": english_encoded["hex"],
        "english_binary": english_encoded["binary"],
        "python_hex": python_encoded["hex"],
        "python_binary": python_encoded["binary"],
        "round_trip_rule": "hex and binary decode to the same UTF-8 strings shown in english and python",
    }
    return json.dumps(payload, indent=2, ensure_ascii=True)


def build_records() -> list[dict]:
    records = []
    for item in DECISIONS:
        prompt = (
            "Map this decision across English, Python, binary, and hex.\n\n"
            f"Scenario: {item['id']}\n"
            f"Answer: {item['answer']}\n"
            f"Move: {item['move']}\n"
        )
        records.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": build_response(item)},
                ],
                "meta": {
                    "source": "multirep_choice_matrix_v1",
                    "scenario_id": item["id"],
                    "answer": item["answer"],
                    "move": item["move"],
                    "surfaces": ["english", "python", "utf8_bytes", "binary", "hex"],
                },
            }
        )
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="training-data/sft/multirep_choice_matrix_v1.sft.jsonl")
    parser.add_argument("--manifest", default="training-data/sft/multirep_choice_matrix_v1_manifest.json")
    args = parser.parse_args()
    output = Path(args.output)
    manifest = Path(args.manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    records = build_records()
    output.write_text("\n".join(json.dumps(row, ensure_ascii=True) for row in records) + "\n", encoding="utf-8")
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "multirep_choice_matrix_v1",
                "record_count": len(records),
                "output": str(output),
                "surfaces": ["english", "python", "utf8_bytes", "binary", "hex"],
            },
            indent=2,
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output), "manifest": str(manifest), "records": len(records)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
