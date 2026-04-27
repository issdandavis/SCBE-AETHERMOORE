#!/usr/bin/env python3
"""Build boundary-clean bijective DSL v5 holdout.

v4 was burned when v3 contract-repair examples were mined from it. This
builder removes repair-train overlaps, caps the dominant translate_one lane,
and adds deterministic holdout-only rows to restore thin category floors.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SFT = ROOT / "training-data" / "sft"
OUT = SFT / "bijective_dsl_v5_holdout.sft.jsonl"
MANIFEST = SFT / "bijective_dsl_v5_holdout_manifest.json"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def category(row: dict[str, Any]) -> str:
    meta = row.get("meta", {}) or {}
    return str(meta.get("task") or meta.get("category") or "unknown")


def signature(row: dict[str, Any]) -> str:
    user = "\n".join(m.get("content", "") for m in row.get("messages", []) if m.get("role") == "user")
    assistant = "\n".join(m.get("content", "") for m in row.get("messages", []) if m.get("role") == "assistant")
    return hashlib.sha256(f"{user}\n---\n{assistant}".encode("utf-8")).hexdigest()


def make_record(task: str, user: str, assistant: str, meta: dict[str, Any]) -> dict[str, Any]:
    merged_meta = {
        "task": task,
        "category": task,
        "provenance": "v5_holdout_floor_patch",
        "holdout_only": True,
        **meta,
    }
    return {
        "messages": [
            {"role": "system", "content": "Emit a DSL program over the 8 SCBE primitives."},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "meta": merged_meta,
    }


def floor_patch_rows() -> list[dict[str, Any]]:
    return [
        make_record(
            "identify",
            "<input>Identify the algorithm and slot structure: binary lane parity check over n using n % 2.</input>\n<target_tongue>AV</target_tongue>",
            "well_select(IDENTIFIED)\n# expected: algorithm: is_even",
            {"algorithm": "is_even", "tongue": "AV"},
        ),
        make_record(
            "identify",
            "<input>Identify the algorithm and slot structure: hexadecimal lane linear scan returning the first matching index.</input>\n<target_tongue>CA</target_tongue>",
            "well_select(IDENTIFIED)\n# expected: algorithm: linear_search",
            {"algorithm": "linear_search", "tongue": "CA"},
        ),
        make_record(
            "edit_slot_one",
            "<input>Algorithm: sum_list. Edit only the init slot in UM so accumulator starts at 1.</input>\n<target_tongue>UM</target_tongue>",
            "well_select(EDIT_INIT)\n# expected: slot init patched for UM",
            {"algorithm": "sum_list", "slot": "init", "tongue": "UM"},
        ),
        make_record(
            "edit_slot_one",
            "<input>Algorithm: is_palindrome. Edit only the compare slot in RU so the mirrored byte pair must match.</input>\n<target_tongue>RU</target_tongue>",
            "well_select(EDIT_COMPARE)\n# expected: slot compare patched for RU",
            {"algorithm": "is_palindrome", "slot": "compare", "tongue": "RU"},
        ),
    ]


def normalize_dialogue_contract(row: dict[str, Any]) -> dict[str, Any]:
    if category(row) != "dialogue":
        return row
    meta = row.get("meta", {}) or {}
    src = meta.get("src") or meta.get("speaker_tongue") or meta.get("tongue") or "KO"
    dst = meta.get("dst") or meta.get("listener_tongue") or meta.get("tongue") or src
    if src == dst:
        program = "seal()\n# expected: sealed dialogue handoff"
    else:
        program = f"tongue_shift({src} -> {dst})\nseal()\n# expected: sealed dialogue handoff"
    patched = json.loads(json.dumps(row))
    for message in patched.get("messages", []):
        if message.get("role") == "assistant":
            message["content"] = program
            break
    patched["meta"] = {**meta, "dialogue_contract_normalized": True}
    return patched


def build() -> dict[str, Any]:
    v4 = load_jsonl(SFT / "bijective_dsl_v4_holdout.sft.jsonl")
    repair_train = load_jsonl(SFT / "contract_repair_v3_train.sft.jsonl")
    repair_sigs = {signature(row) for row in repair_train}

    cleaned = [row for row in v4 if signature(row) not in repair_sigs]

    kept: list[dict[str, Any]] = []
    translate_one_seen = 0
    translate_one_cap = 7
    for row in cleaned:
        if category(row) == "translate_one":
            translate_one_seen += 1
            if translate_one_seen > translate_one_cap:
                continue
        kept.append(row)

    existing_sigs = {signature(row) for row in kept}
    for row in floor_patch_rows():
        sig = signature(row)
        if sig not in existing_sigs:
            kept.append(row)
            existing_sigs.add(sig)

    kept = [normalize_dialogue_contract(row) for row in kept]

    OUT.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in kept) + "\n", encoding="utf-8")
    counts = Counter(category(row) for row in kept)
    payload = {
        "schema_version": "bijective_dsl_v5_holdout_manifest_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_v4_records": len(v4),
        "repair_v3_train_records": len(repair_train),
        "repair_v3_removed": len(v4) - len(cleaned),
        "translate_one_cap": translate_one_cap,
        "floor_patch_records": 4,
        "output": str(OUT.relative_to(ROOT).as_posix()),
        "output_records": len(kept),
        "by_category": dict(counts),
        "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
    }
    MANIFEST.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    payload = build()
    print(f"Wrote {payload['output']} ({payload['output_records']} records)")
    print(json.dumps(payload["by_category"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
