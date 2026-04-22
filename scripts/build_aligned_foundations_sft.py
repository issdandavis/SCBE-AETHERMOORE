"""Build aligned multi-representation foundation corpora for SCBE training.

The goal is to teach the same primitive concept in several synchronized forms:
math, English, Sacred Tongue lane naming, and binary transport framing.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SFT_ROOT = REPO_ROOT / "training-data" / "sft"

TRAIN_OUT = SFT_ROOT / "aligned_foundations_train.sft.jsonl"
EVAL_OUT = SFT_ROOT / "aligned_foundations_holdout.sft.jsonl"
MANIFEST_OUT = SFT_ROOT / "aligned_foundations_manifest.json"

SYSTEM = (
    "You are an SCBE aligned-foundations tutor. Teach the same concept in synchronized forms: "
    "mathematics, plain English, Sacred Tongues lane naming, and binary or packet framing. "
    "Keep each answer structured, concise, and invariant-preserving."
)

TONGUES = [
    ("KO", "Kor'aelin", "intent"),
    ("AV", "Avali", "context"),
    ("RU", "Runethic", "relation"),
    ("CA", "Cassisivadan", "implementation"),
    ("UM", "Umbroth", "veil"),
    ("DR", "Draumric", "structure"),
]

LAYERS = [
    ("L10", "spectral coherence", "frequency and mode alignment"),
    ("L11", "triadic temporal accumulation", "time-ordered intent accumulation"),
    ("L12", "harmonic wall", "safety score and bounded traversal"),
    ("L13", "governance risk decision", "ALLOW QUARANTINE ESCALATE DENY routing"),
    ("L14", "audio axis telemetry", "monitoring and outward trace"),
]

RISK_TIERS = [
    ("ALLOW", "safe to proceed inside bounds"),
    ("QUARANTINE", "hold and isolate for closer inspection"),
    ("ESCALATE", "send upward for higher-authority review"),
    ("DENY", "block because the action violates bounds"),
]

CHEMISTRY_CASES = [
    ("2H2 + O2 -> 2H2O", "stable", "synthesis", "atoms conserved and products well-formed"),
    ("HCl + NaOH -> NaCl + H2O", "stable", "neutralization", "acid-base balance closes cleanly"),
    ("2Na + 2H2O -> 2NaOH + H2", "unstable", "displacement", "reactivity is high and release is vigorous"),
    ("2Al + Fe2O3 -> Al2O3 + 2Fe", "unstable", "redox", "thermite-style energy release indicates a high-reactivity lane"),
]


def make_record(user: str, assistant: str, *, category: str, holdout: bool) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "meta": {
            "program": "aligned_foundations",
            "category": category,
            "split": "holdout" if holdout else "train",
        },
    }


def letter_records() -> list[dict]:
    rows: list[dict] = []
    for idx, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ", start=1):
        binary = format(idx, "05b")
        user = f"Align the primitive symbol {letter} across math, English, and binary."
        assistant = (
            f"math: symbol_index({letter}) = {idx}\n"
            f"english: the letter {letter} is primitive symbol {idx}\n"
            f"binary: {idx} -> {binary}\n"
            f"invariant: one symbol, one index, one binary encoding"
        )
        rows.append(make_record(user, assistant, category="alphabet", holdout=idx % 5 == 0))
    return rows


def number_records() -> list[dict]:
    rows: list[dict] = []
    for value in range(16):
        binary = format(value, "04b")
        parity = "even" if value % 2 == 0 else "odd"
        user = f"Teach the number {value} in aligned foundations form."
        assistant = (
            f"math: {value}\n"
            f"english: the quantity is {value} and its parity is {parity}\n"
            f"binary: {binary}\n"
            f"invariant: decimal {value} maps exactly to binary {binary}"
        )
        rows.append(make_record(user, assistant, category="numbers", holdout=value % 4 == 3))
    return rows


def tongue_records() -> list[dict]:
    rows: list[dict] = []
    for idx, (abbr, full_name, duty) in enumerate(TONGUES):
        user = f"State the Sacred Tongue mapping for {abbr} with full name and primary duty."
        assistant = (
            f"abbr: {abbr}\n"
            f"full_name: {full_name}\n"
            f"duty: {duty}\n"
            f"invariant: {abbr} and {full_name} refer to the same communication lane"
        )
        rows.append(make_record(user, assistant, category="tongues", holdout=idx % 3 == 2))
    return rows


def layer_records() -> list[dict]:
    rows: list[dict] = []
    for idx, (code, name, role) in enumerate(LAYERS):
        user = f"Teach {code} in aligned foundations form with number, name, and role."
        assistant = (
            f"layer: {code}\n"
            f"name: {name}\n"
            f"role: {role}\n"
            f"invariant: {code} and {name} identify the same layer function"
        )
        rows.append(make_record(user, assistant, category="layers", holdout=idx == len(LAYERS) - 1))
    return rows


def tier_records() -> list[dict]:
    rows: list[dict] = []
    all_names = ", ".join(name for name, _ in RISK_TIERS)
    for idx, (name, meaning) in enumerate(RISK_TIERS):
        user = f"Explain the risk tier set and define {name}."
        assistant = (
            f"set: {all_names}\n"
            f"focus: {name}\n"
            f"definition: {meaning}\n"
            f"invariant: all four tiers are part of one governance decision box"
        )
        rows.append(make_record(user, assistant, category="risk_tiers", holdout=idx == 2))
    return rows


def chemistry_records() -> list[dict]:
    rows: list[dict] = []
    for idx, (equation, stability, reaction_class, why) in enumerate(CHEMISTRY_CASES):
        user = f"Teach the chemistry packet for {equation} and explain why it is {stability}."
        assistant = (
            f"equation: {equation}\n"
            f"class: {reaction_class}\n"
            f"stability: {stability}\n"
            f"reason: {why}\n"
            f"transfer: stability and instability can be mapped into other governed transformation fields"
        )
        rows.append(make_record(user, assistant, category="chemistry", holdout=idx % 2 == 1))
    return rows


def main() -> int:
    all_rows = (
        letter_records()
        + number_records()
        + tongue_records()
        + layer_records()
        + tier_records()
        + chemistry_records()
    )

    train_rows = [row for row in all_rows if row["meta"]["split"] == "train"]
    holdout_rows = [row for row in all_rows if row["meta"]["split"] == "holdout"]

    SFT_ROOT.mkdir(parents=True, exist_ok=True)
    with TRAIN_OUT.open("w", encoding="utf-8") as handle:
        for row in train_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with EVAL_OUT.open("w", encoding="utf-8") as handle:
        for row in holdout_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "schema_version": "aligned_foundations_manifest_v1",
        "train_file": str(TRAIN_OUT.relative_to(REPO_ROOT)),
        "eval_file": str(EVAL_OUT.relative_to(REPO_ROOT)),
        "counts": {
            "train": len(train_rows),
            "holdout": len(holdout_rows),
            "total": len(all_rows),
        },
        "categories": {
            "alphabet": len(letter_records()),
            "numbers": len(number_records()),
            "tongues": len(tongue_records()),
            "layers": len(layer_records()),
            "risk_tiers": len(tier_records()),
            "chemistry": len(chemistry_records()),
        },
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"[aligned_foundations] wrote {len(train_rows)} train rows -> {TRAIN_OUT}")
    print(f"[aligned_foundations] wrote {len(holdout_rows)} holdout rows -> {EVAL_OUT}")
    print(f"[aligned_foundations] manifest -> {MANIFEST_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
