#!/usr/bin/env python3
"""Validate the SCBE foundation-bundle SFT lane.

This is a corpus gate, not a model-quality score. It verifies that the final
test substrate contains the required primary-to-binary-to-hex coverage across
all foundation stacks and the seventh binding tongue.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SFT_ROOT = REPO_ROOT / "training-data" / "sft"

FILES = [
    SFT_ROOT / "foundation_bundle_stacks_train.sft.jsonl",
    SFT_ROOT / "foundation_bundle_stacks_holdout.sft.jsonl",
]

REQUIRED_STACKS = {
    "dense_semantic",
    "mathematical",
    "statistical",
    "resonance",
    "chemical",
    "coding",
    "foundation_bundle",
}
REQUIRED_ACTIONS = {
    "validate_input",
    "transform_state",
    "test_receipt",
    "quarantine_drift",
    "merge_evidence",
    "route_agent",
}
REQUIRED_TONGUES = {"KO", "AV", "RU", "CA", "UM", "DR", "SE"}
REQUIRED_SURFACES = {
    "dense_semantic",
    "mathematical",
    "statistical",
    "resonance",
    "chemical",
    "coding",
}


def load_rows() -> list[dict]:
    rows: list[dict] = []
    for path in FILES:
        if not path.exists():
            raise FileNotFoundError(path)
        for line_no, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            row = json.loads(line)
            row["_source_file"] = str(path.relative_to(REPO_ROOT))
            row["_line_no"] = line_no
            rows.append(row)
    return rows


def assistant_payload(row: dict) -> dict:
    messages = row.get("messages", [])
    if not messages or messages[-1].get("role") != "assistant":
        raise ValueError(
            f"{row['_source_file']}:{row['_line_no']} missing assistant message"
        )
    return json.loads(messages[-1].get("content", "{}"))


def check_transport(payload: dict, errors: list[str], row: dict) -> None:
    transport = payload.get("transport", {})
    source_text = transport.get("source_text")
    hex_text = transport.get("hex")
    binary_text = transport.get("binary")
    loc = f"{row['_source_file']}:{row['_line_no']}"
    if not source_text or not hex_text or not binary_text:
        errors.append(f"{loc} missing source_text/hex/binary")
        return
    try:
        from_hex = bytes.fromhex(str(hex_text).replace(".", " ")).decode("utf-8")
        from_binary = bytes(int(part, 2) for part in str(binary_text).split()).decode(
            "utf-8"
        )
    except Exception as exc:
        errors.append(f"{loc} transport decode failed: {exc}")
        return
    if from_hex != source_text:
        errors.append(f"{loc} hex round-trip mismatch")
    if from_binary != source_text:
        errors.append(f"{loc} binary round-trip mismatch")


def main() -> int:
    rows = load_rows()
    errors: list[str] = []
    stacks: set[str] = set()
    actions: set[str] = set()
    tongues: set[str] = set()
    split_counts = {"train": 0, "holdout": 0}

    for row in rows:
        meta = row.get("meta", {})
        stacks.add(str(meta.get("stack")))
        actions.add(str(meta.get("action")))
        tongues.add(str(meta.get("tongue")))
        split = str(meta.get("split"))
        if split in split_counts:
            split_counts[split] += 1
        else:
            errors.append(
                f"{row['_source_file']}:{row['_line_no']} invalid split {split}"
            )

        payload = assistant_payload(row)
        check_transport(payload, errors, row)

        if meta.get("stack") != "foundation_bundle":
            surfaces = set(payload.get("surfaces", {}).keys())
            missing_surfaces = REQUIRED_SURFACES - surfaces
            if missing_surfaces:
                errors.append(
                    f"{row['_source_file']}:{row['_line_no']} missing surfaces {sorted(missing_surfaces)}"
                )
        else:
            if (
                "known_state" not in payload
                or "unknown_state" not in payload
                or "group_bijection" not in payload
            ):
                errors.append(
                    f"{row['_source_file']}:{row['_line_no']} missing seventh-binding sections"
                )

    for label, required, actual in (
        ("stacks", REQUIRED_STACKS, stacks),
        ("actions", REQUIRED_ACTIONS, actions),
        ("tongues", REQUIRED_TONGUES, tongues),
    ):
        missing = required - actual
        if missing:
            errors.append(f"missing required {label}: {sorted(missing)}")

    if split_counts["train"] == 0 or split_counts["holdout"] == 0:
        errors.append(f"invalid split counts: {split_counts}")

    report = {
        "gate": "foundation_bundle_stacks_v1",
        "pass": not errors,
        "records": len(rows),
        "split_counts": split_counts,
        "stacks": sorted(stacks),
        "actions": sorted(actions),
        "tongues": sorted(tongues),
        "errors": errors,
    }
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
