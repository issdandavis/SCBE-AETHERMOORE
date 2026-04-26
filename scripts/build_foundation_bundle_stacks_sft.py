#!/usr/bin/env python3
"""Build SCBE foundation-bundle stack SFT records.

This lane teaches one action packet across synchronized surfaces:
dense semantic, mathematical, statistical, resonance, chemical, coding,
binary/hex transport, Sacred Tongues lane naming, and a seventh binding lane
for known/unknown system-state handling.
"""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SFT_ROOT = REPO_ROOT / "training-data" / "sft"

TRAIN_OUT = SFT_ROOT / "foundation_bundle_stacks_train.sft.jsonl"
EVAL_OUT = SFT_ROOT / "foundation_bundle_stacks_holdout.sft.jsonl"
MANIFEST_OUT = SFT_ROOT / "foundation_bundle_stacks_manifest.json"

SYSTEM = (
    "You are an SCBE foundation-bundle instructor. Express the same action "
    "packet through dense semantic, mathematical, statistical, resonance, "
    "chemical, and coding surfaces. Preserve bijective transport fields and "
    "state when the seventh binding lane is handling known or unknown system "
    "state. Keep outputs structured and auditable."
)

TONGUES = [
    ("KO", "Kor'aelin", "intent"),
    ("AV", "Avali", "context"),
    ("RU", "Runethic", "relation"),
    ("CA", "Cassisivadan", "implementation"),
    ("UM", "Umbroth", "veil"),
    ("DR", "Draumric", "structure"),
    ("SE", "Seventh Binding Tongue", "known_unknown_binding"),
]

STACKS = [
    {
        "id": "dense_semantic",
        "tongue": "KO",
        "purpose": "preserve meaning and user intent without letting analogy override facts",
        "math_form": "meaning = fact + gated_context + bounded_analogy",
        "stat_form": "semantic_confidence >= 0.80 and contradiction_rate <= 0.05",
        "resonance_form": "intent phase remains coherent across restatement",
        "chemical_form": "stable mixture: fact solvent + context solute; analogy is catalyst only",
        "coding_form": "assert packet['source'] in {'fact','context','bounded_analogy'}",
    },
    {
        "id": "mathematical",
        "tongue": "DR",
        "purpose": "preserve exact transformations, invariants, and reversible mappings",
        "math_form": "f^-1(f(x)) = x",
        "stat_form": "round_trip_error == 0",
        "resonance_form": "phase returns to origin after inverse transform",
        "chemical_form": "balanced equation: inputs and outputs conserve count",
        "coding_form": "assert decode(encode(x)) == x",
    },
    {
        "id": "statistical",
        "tongue": "AV",
        "purpose": "measure uncertainty, drift, recall, precision, and failure pressure",
        "math_form": "risk = P(failure | context, time, access)",
        "stat_form": "track precision, recall, f1, false_negative_rate, calibration_error",
        "resonance_form": "noise rises when uncertainty bands widen",
        "chemical_form": "unstable reaction when variance exceeds containment",
        "coding_form": "assert metrics['recall'] >= floor['recall']",
    },
    {
        "id": "resonance",
        "tongue": "RU",
        "purpose": "track phase alignment, rhythm, recurrence, and harmonic stability",
        "math_form": "coherence = cos(delta_phase)",
        "stat_form": "mean_phase_error <= 0.10 over the active window",
        "resonance_form": "matching overtones reinforce; destructive interference quarantines",
        "chemical_form": "stable lattice when local bonds reinforce global structure",
        "coding_form": "assert abs(packet['phase_error']) <= packet['phase_floor']",
    },
    {
        "id": "chemical",
        "tongue": "UM",
        "purpose": "teach conservation, stability, containment, and reaction class",
        "math_form": "reactants_count == products_count",
        "stat_form": "stability_score >= 0.75 or route == 'QUARANTINE'",
        "resonance_form": "reaction heat is pressure that must remain bounded",
        "chemical_form": "classify synthesis, decomposition, displacement, redox, or neutralization",
        "coding_form": "assert is_balanced(reaction) and route_by_stability(reaction)",
    },
    {
        "id": "coding",
        "tongue": "CA",
        "purpose": "turn decisions into executable, tested, reversible actions",
        "math_form": "program_state(t+1) = apply(action, program_state(t))",
        "stat_form": "executable_accuracy >= 0.85 and regression_guard == 'PASS'",
        "resonance_form": "code path stays aligned with receipt path",
        "chemical_form": "safe build when dependencies react without conflict",
        "coding_form": "run_tests(); assert receipt['exit_code'] == 0",
    },
]

ACTIONS = [
    {
        "id": "validate_input",
        "verb": "validate",
        "english": "Check the input before action and separate fact, context, analogy, and unknown state.",
        "route": "ALLOW",
    },
    {
        "id": "transform_state",
        "verb": "transform",
        "english": "Apply a reversible transformation and keep the inverse path available.",
        "route": "ALLOW",
    },
    {
        "id": "test_receipt",
        "verb": "test",
        "english": "Run the behavior and record a receipt instead of trusting training loss.",
        "route": "ALLOW",
    },
    {
        "id": "quarantine_drift",
        "verb": "quarantine",
        "english": "If meaning, safety, or execution drifts, isolate it before merge or dispatch.",
        "route": "QUARANTINE",
    },
    {
        "id": "merge_evidence",
        "verb": "merge",
        "english": "Combine only adapters or records that preserve their original measured capability.",
        "route": "ESCALATE",
    },
    {
        "id": "route_agent",
        "verb": "route",
        "english": "Send the task to the narrowest qualified model, tool, or human lane.",
        "route": "ALLOW",
    },
]


def encode_transport(text: str) -> dict[str, str]:
    raw = text.encode("utf-8")
    return {
        "utf8_len": str(len(raw)),
        "hex": raw.hex(".").upper(),
        "binary": " ".join(format(byte, "08b") for byte in raw),
    }


def make_packet(stack: dict, action: dict) -> dict:
    tongue = next(row for row in TONGUES if row[0] == stack["tongue"])
    action_text = f"{stack['id']}::{action['id']}::{action['route']}"
    transport = encode_transport(action_text)
    return {
        "packet_id": action_text,
        "stack": stack["id"],
        "tongue": {
            "abbr": tongue[0],
            "full_name": tongue[1],
            "duty": tongue[2],
        },
        "action": {
            "id": action["id"],
            "verb": action["verb"],
            "route": action["route"],
            "english": action["english"],
        },
        "surfaces": {
            "dense_semantic": stack["purpose"],
            "mathematical": stack["math_form"],
            "statistical": stack["stat_form"],
            "resonance": stack["resonance_form"],
            "chemical": stack["chemical_form"],
            "coding": stack["coding_form"],
        },
        "transport": {
            "source_text": action_text,
            "utf8_len": int(transport["utf8_len"]),
            "hex": transport["hex"],
            "binary": transport["binary"],
            "round_trip_rule": "utf8(binary(source_text)) == utf8(hex(source_text)) == source_text",
        },
        "bijective_checks": [
            "stack_id maps to exactly one stack role",
            "tongue abbreviation maps to exactly one full tongue name",
            "source_text round-trips through binary and hex without loss",
            "action route is preserved across every surface",
        ],
    }


def make_record(stack: dict, action: dict, *, holdout: bool) -> dict:
    prompt = (
        "Build a foundation-bundle action packet.\n"
        f"Stack: {stack['id']}\n"
        f"Action: {action['id']}\n"
        f"Route: {action['route']}\n"
        "Include semantic, mathematical, statistical, resonance, chemical, coding, "
        "binary, hex, and tongue-binding fields."
    )
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": json.dumps(make_packet(stack, action), indent=2, ensure_ascii=True)},
        ],
        "meta": {
            "program": "foundation_bundle_stacks",
            "split": "holdout" if holdout else "train",
            "stack": stack["id"],
            "action": action["id"],
            "tongue": stack["tongue"],
            "route": action["route"],
            "surfaces": [
                "dense_semantic",
                "mathematical",
                "statistical",
                "resonance",
                "chemical",
                "coding",
                "binary",
                "hex",
                "tongue_binding",
            ],
        },
    }


def binding_records() -> list[dict]:
    rows: list[dict] = []
    for idx, action in enumerate(ACTIONS):
        group_text = f"foundation_bundle::{action['id']}::SE"
        transport = encode_transport(group_text)
        payload = {
            "packet_id": group_text,
            "tongue": {
                "abbr": "SE",
                "full_name": "Seventh Binding Tongue",
                "duty": "bind known and unknown system states without pretending unknowns are facts",
            },
            "known_state": {
                "stacks": [stack["id"] for stack in STACKS],
                "action": action["id"],
                "route": action["route"],
            },
            "unknown_state": {
                "rule": "mark as unknown, preserve provenance, and route through test or quarantine before merge",
                "forbidden_move": "do not convert unknown state into a factual claim",
            },
            "group_bijection": {
                "individual_to_group": "each stack packet keeps its own identity inside the bundle",
                "group_to_individual": "the bundle can be decomposed back into stack packets",
                "self_relation": "each packet round-trips with itself before it can bind to the group",
            },
            "transport": {
                "source_text": group_text,
                "utf8_len": int(transport["utf8_len"]),
                "hex": transport["hex"],
                "binary": transport["binary"],
            },
        }
        rows.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {
                        "role": "user",
                        "content": f"Bind the known and unknown states for action {action['id']} across all foundation stacks.",
                    },
                    {"role": "assistant", "content": json.dumps(payload, indent=2, ensure_ascii=True)},
                ],
                "meta": {
                    "program": "foundation_bundle_stacks",
                    "split": "holdout" if idx in {1, 4} else "train",
                    "stack": "foundation_bundle",
                    "action": action["id"],
                    "tongue": "SE",
                    "route": action["route"],
                    "surfaces": ["known_state", "unknown_state", "group_bijection", "binary", "hex"],
                },
            }
        )
    return rows


def build_records() -> list[dict]:
    rows: list[dict] = []
    for stack_index, stack in enumerate(STACKS):
        for action_index, action in enumerate(ACTIONS):
            holdout = (stack_index + action_index) % 5 == 0
            rows.append(make_record(stack, action, holdout=holdout))
    rows.extend(binding_records())
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def main() -> int:
    rows = build_records()
    train_rows = [row for row in rows if row["meta"]["split"] == "train"]
    holdout_rows = [row for row in rows if row["meta"]["split"] == "holdout"]

    write_jsonl(TRAIN_OUT, train_rows)
    write_jsonl(EVAL_OUT, holdout_rows)

    manifest = {
        "schema_version": "foundation_bundle_stacks_manifest_v1",
        "outputs": {
            "train": str(TRAIN_OUT.relative_to(REPO_ROOT)),
            "eval": str(EVAL_OUT.relative_to(REPO_ROOT)),
        },
        "counts": {
            "train": len(train_rows),
            "holdout": len(holdout_rows),
            "total": len(rows),
        },
        "stacks": [stack["id"] for stack in STACKS],
        "actions": [action["id"] for action in ACTIONS],
        "tongues": [{"abbr": abbr, "full_name": name, "duty": duty} for abbr, name, duty in TONGUES],
        "invariants": [
            "binary and hex decode to the same source_text",
            "stack identity survives group binding",
            "known state and unknown state remain explicitly separated",
            "route labels are preserved across all surfaces",
        ],
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")

    print(json.dumps({"train": len(train_rows), "holdout": len(holdout_rows), "manifest": str(MANIFEST_OUT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
