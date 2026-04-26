#!/usr/bin/env python3
"""Build binary-substrate pillar records for SCBE coding training.

Each record preserves one binary fact across synchronized pillars:
standard binary, music theory, atomic theory, and primary coding languages.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SFT_ROOT = REPO_ROOT / "training-data" / "sft"
DEFAULT_OUTPUT = SFT_ROOT / "binary_pillars_v1.sft.jsonl"
DEFAULT_MANIFEST = SFT_ROOT / "binary_pillars_v1_manifest.json"

SYSTEM_PROMPT = (
    "You are an SCBE binary-pillar coding tutor. Treat binary as the trunk. "
    "Align each concept across standard binary, music theory, atomic theory, "
    "and primary code languages without changing the underlying fact."
)

NOTES = ("C", "D", "E", "F", "G", "A", "B")
MODES = ("Ionian", "Dorian", "Phrygian", "Lydian", "Mixolydian", "Aeolian", "Locrian")
ELEMENTS = (
    ("H", 1, "hydrogen"),
    ("He", 2, "helium"),
    ("Li", 3, "lithium"),
    ("Be", 4, "beryllium"),
    ("B", 5, "boron"),
    ("C", 6, "carbon"),
    ("N", 7, "nitrogen"),
    ("O", 8, "oxygen"),
    ("F", 9, "fluorine"),
    ("Ne", 10, "neon"),
    ("Na", 11, "sodium"),
    ("Mg", 12, "magnesium"),
    ("Al", 13, "aluminum"),
    ("Si", 14, "silicon"),
    ("P", 15, "phosphorus"),
    ("S", 16, "sulfur"),
)
LANGUAGES = ("python", "typescript", "c", "rust")


@dataclass(frozen=True)
class PillarRecord:
    record_id: str
    concept: str
    binary: str
    decimal: int
    hex_value: str
    music: dict[str, Any]
    atomic: dict[str, Any]
    code: dict[str, str]
    round_trip: dict[str, Any]


def _bit_count(value: int) -> int:
    return bin(value).count("1")


def byte_to_element_index(value: int) -> int:
    """Prime-stride byte to element index, matching the project mapping style."""

    return ((value * 47) % 118) + 1


def _element_for_nibble(value: int) -> tuple[str, int, str]:
    return ELEMENTS[value % len(ELEMENTS)]


def _music_for_value(value: int) -> dict[str, Any]:
    octave = 2 + (value % 5)
    degree = value % len(NOTES)
    return {
        "note": NOTES[degree],
        "mode": MODES[value % len(MODES)],
        "octave": octave,
        "degree": degree + 1,
        "phase_degrees": (value * 360) // 16,
    }


def _atomic_for_value(value: int) -> dict[str, Any]:
    symbol, atomic_number, name = _element_for_nibble(value)
    return {
        "symbol": symbol,
        "atomic_number": atomic_number,
        "name": name,
        "popcount": _bit_count(value),
        "byte_element_index": byte_to_element_index(value),
    }


def _code_for_value(value: int, width: int) -> dict[str, str]:
    binary = format(value, f"0{width}b")
    return {
        "python": f"value = int('0b{binary}', 2)",
        "typescript": f"const value = 0b{binary};",
        "c": f"unsigned int value = 0b{binary};",
        "rust": f"let value: u8 = 0b{binary};",
    }


def build_nibble_records() -> list[PillarRecord]:
    rows: list[PillarRecord] = []
    for value in range(16):
        binary = format(value, "04b")
        rows.append(
            PillarRecord(
                record_id=f"binary_pillars_v1_nibble_{value:02d}",
                concept=f"nibble_{value}",
                binary=binary,
                decimal=value,
                hex_value=f"0x{value:X}",
                music=_music_for_value(value),
                atomic=_atomic_for_value(value),
                code=_code_for_value(value, 4),
                round_trip={
                    "binary_to_decimal": value,
                    "decimal_to_binary": binary,
                    "hex_to_decimal": int(f"{value:X}", 16),
                },
            )
        )
    return rows


def build_byte_records() -> list[PillarRecord]:
    selected = [
        0,
        1,
        2,
        3,
        7,
        8,
        15,
        16,
        31,
        32,
        47,
        64,
        65,
        90,
        97,
        127,
        128,
        170,
        255,
    ]
    rows: list[PillarRecord] = []
    for value in selected:
        binary = format(value, "08b")
        rows.append(
            PillarRecord(
                record_id=f"binary_pillars_v1_byte_{value:03d}",
                concept=f"byte_{value}",
                binary=binary,
                decimal=value,
                hex_value=f"0x{value:02X}",
                music=_music_for_value(value),
                atomic={
                    **_atomic_for_value(value),
                    "byte_range": "0-255",
                    "ascii": chr(value) if 32 <= value <= 126 else "",
                },
                code=_code_for_value(value, 8),
                round_trip={
                    "binary_to_decimal": value,
                    "decimal_to_binary": binary,
                    "hex_to_decimal": int(f"{value:02X}", 16),
                    "low_nibble": value & 0x0F,
                    "high_nibble": (value >> 4) & 0x0F,
                },
            )
        )
    return rows


def build_logic_records() -> list[PillarRecord]:
    pairs = [(0, 0), (0, 1), (1, 0), (1, 1)]
    rows: list[PillarRecord] = []
    for a, b in pairs:
        value = (a << 1) | b
        binary = f"{a}{b}"
        rows.append(
            PillarRecord(
                record_id=f"binary_pillars_v1_logic_{a}{b}",
                concept=f"logic_pair_{a}{b}",
                binary=binary,
                decimal=value,
                hex_value=f"0x{value:X}",
                music=_music_for_value(value),
                atomic=_atomic_for_value(value),
                code={
                    "python": f"and_bit = {a} & {b}; xor_bit = {a} ^ {b}",
                    "typescript": f"const andBit = {a} & {b}; const xorBit = {a} ^ {b};",
                    "c": f"int and_bit = {a} & {b}; int xor_bit = {a} ^ {b};",
                    "rust": f"let and_bit = {a} & {b}; let xor_bit = {a} ^ {b};",
                },
                round_trip={
                    "binary_to_decimal": value,
                    "decimal_to_binary": binary,
                    "hex_to_decimal": int(f"{value:X}", 16),
                    "and": a & b,
                    "or": a | b,
                    "xor": a ^ b,
                    "nand": 1 - (a & b),
                },
            )
        )
    return rows


def to_sft(record: PillarRecord) -> dict[str, Any]:
    user = (
        f"Teach {record.concept} as synchronized binary pillars. "
        "Preserve the same fact across binary, music, atomic, and code lanes."
    )
    assistant_payload = {
        "concept": record.concept,
        "binary_pillar": {
            "binary": record.binary,
            "decimal": record.decimal,
            "hex": record.hex_value,
        },
        "music_pillar": record.music,
        "atomic_pillar": record.atomic,
        "code_pillar": record.code,
        "round_trip": record.round_trip,
        "invariant": "All pillars describe the same substrate value; do not let analogy override the binary fact.",
    }
    return {
        "id": record.record_id,
        "track": "binary_music_atomic_code_pillars",
        "source_type": "generated_aligned_foundation",
        "quality": "reference",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
            {
                "role": "assistant",
                "content": json.dumps(assistant_payload, ensure_ascii=True, indent=2),
            },
        ],
        "metadata": {
            "concept": record.concept,
            "binary": record.binary,
            "decimal": record.decimal,
            "hex": record.hex_value,
            "pillars": ["binary", "music", "atomic", "code"],
            "languages": list(LANGUAGES),
        },
    }


def build_records() -> list[dict[str, Any]]:
    records = build_nibble_records() + build_byte_records() + build_logic_records()
    return [to_sft(record) for record in records]


def write_dataset(output: Path, manifest: Path) -> dict[str, Any]:
    records = build_records()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")

    payload = {
        "schema_version": "binary_pillars_manifest_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "output_path": str(output.relative_to(REPO_ROOT)),
        "record_count": len(records),
        "pillars": ["binary", "music", "atomic", "code"],
        "languages": list(LANGUAGES),
        "record_groups": {
            "nibbles": 16,
            "bytes": 19,
            "logic_pairs": 4,
        },
        "training_rule": "Binary is the trunk; music and atomic mappings are reference lattices; code is the executable target.",
    }
    manifest.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    manifest = write_dataset(args.output, args.manifest)
    print(
        json.dumps(manifest, indent=2)
        if args.json
        else f"wrote {manifest['record_count']} records"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
