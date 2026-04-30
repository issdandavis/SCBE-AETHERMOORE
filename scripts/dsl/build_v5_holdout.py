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
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def category(row: dict[str, Any]) -> str:
    meta = row.get("meta", {}) or {}
    return str(meta.get("task") or meta.get("category") or "unknown")


def signature(row: dict[str, Any]) -> str:
    user = "\n".join(
        m.get("content", "") for m in row.get("messages", []) if m.get("role") == "user"
    )
    assistant = "\n".join(
        m.get("content", "")
        for m in row.get("messages", [])
        if m.get("role") == "assistant"
    )
    return hashlib.sha256(f"{user}\n---\n{assistant}".encode("utf-8")).hexdigest()


def make_record(
    task: str, user: str, assistant: str, meta: dict[str, Any]
) -> dict[str, Any]:
    merged_meta = {
        "task": task,
        "category": task,
        "provenance": "v5_holdout_floor_patch",
        "holdout_only": True,
        **meta,
    }
    return {
        "messages": [
            {
                "role": "system",
                "content": "Emit a DSL program over the 8 SCBE primitives.",
            },
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "meta": merged_meta,
    }


def floor_patch_rows() -> list[dict[str, Any]]:
    specs = [
        (
            "identify",
            "is_even",
            "AV",
            "Identify the algorithm and slot structure: binary lane parity check over n using n % 2.",
            "well_select(IDENTIFIED)\n# expected: algorithm: is_even",
            {"slot": "parity"},
        ),
        (
            "identify",
            "linear_search",
            "CA",
            "Identify the algorithm and slot structure: hexadecimal lane linear scan returning the first matching index.",
            "well_select(IDENTIFIED)\n# expected: algorithm: linear_search",
            {"slot": "scan"},
        ),
        (
            "identify",
            "clamp",
            "RU",
            "Identify the algorithm and slot structure: bounded clamp with lower and upper guards.",
            "well_select(IDENTIFIED)\n# expected: algorithm: clamp",
            {"slot": "guard"},
        ),
        (
            "edit_slot_all",
            "sum_list",
            "UM",
            "Rewrite all slots for sum_list so init, loop, update, and return are explicitly governed.",
            "well_select(EDIT_ALL)\ntongue_shift(KO -> UM)\nseal()\n# expected: all slots patched",
            {"slots": ["init", "loop", "update", "return"]},
        ),
        (
            "edit_slot_all",
            "max_value",
            "AV",
            "Rewrite all slots for max_value so empty input, comparison, update, and return are explicit.",
            "well_select(EDIT_ALL)\ntongue_shift(KO -> AV)\nseal()\n# expected: all slots patched",
            {"slots": ["empty_guard", "compare", "update", "return"]},
        ),
        (
            "edit_slot_all",
            "normalize_name",
            "CA",
            "Rewrite all slots for normalize_name so trim, lower, separator, and return are explicit.",
            "well_select(EDIT_ALL)\ntongue_shift(KO -> CA)\nseal()\n# expected: all slots patched",
            {"slots": ["trim", "lower", "separator", "return"]},
        ),
        (
            "edit_slot_one",
            "sum_list",
            "UM",
            "Algorithm: sum_list. Edit only the init slot in UM so accumulator starts at 1.",
            "well_select(EDIT_INIT)\n# expected: slot init patched for UM",
            {"slot": "init"},
        ),
        (
            "edit_slot_one",
            "is_palindrome",
            "RU",
            "Algorithm: is_palindrome. Edit only the compare slot in RU so the mirrored byte pair must match.",
            "well_select(EDIT_COMPARE)\n# expected: slot compare patched for RU",
            {"slot": "compare"},
        ),
        (
            "edit_slot_one",
            "safe_divide",
            "KO",
            "Algorithm: safe_divide. Edit only the guard slot in KO so division by zero is rejected.",
            "well_select(EDIT_GUARD)\n# expected: slot guard patched for KO",
            {"slot": "guard"},
        ),
        (
            "governance_tag",
            "safe_eval",
            "RU",
            "Add governance tags for safe_eval where untrusted expression input must stay deny-by-default.",
            "well_select(GOVERNED)\nseal()\n# expected: deny_by_default input policy",
            {"policy": "deny_by_default"},
        ),
        (
            "governance_tag",
            "file_write",
            "UM",
            "Add governance tags for file_write where path and overwrite capability must be explicit.",
            "well_select(GOVERNED)\nseal()\n# expected: explicit filesystem capability",
            {"policy": "capability_required"},
        ),
        (
            "governance_tag",
            "network_fetch",
            "AV",
            "Add governance tags for network_fetch where remote host and timeout must be bounded.",
            "well_select(GOVERNED)\nseal()\n# expected: bounded network capability",
            {"policy": "bounded_network"},
        ),
        (
            "align",
            "sort_numbers",
            "CA",
            "Align the sort_numbers operation from KO intent into CA command form without changing behavior.",
            "well_select(ALIGNED)\ntongue_shift(KO -> CA)\nseal()\n# expected: behavior preserved",
            {"src": "KO", "dst": "CA"},
        ),
        (
            "align",
            "parse_json_name",
            "RU",
            "Align the parse_json_name operation from AV intent into RU command form without changing behavior.",
            "well_select(ALIGNED)\ntongue_shift(AV -> RU)\nseal()\n# expected: behavior preserved",
            {"src": "AV", "dst": "RU"},
        ),
        (
            "align",
            "bounded_factorial",
            "UM",
            "Align the bounded_factorial operation from CA intent into UM command form without changing guards.",
            "well_select(ALIGNED)\ntongue_shift(CA -> UM)\nseal()\n# expected: guards preserved",
            {"src": "CA", "dst": "UM"},
        ),
        (
            "translate_all",
            "reverse_string",
            "CA",
            "Translate reverse_string through KO, AV, RU, and CA while preserving the canonical signature.",
            "tongue_shift(KO -> AV)\ntongue_shift(AV -> RU)\ntongue_shift(RU -> CA)\nseal()\n# expected: all target tongues covered",
            {"src": "KO", "dst": "CA"},
        ),
        (
            "translate_all",
            "safe_divide",
            "UM",
            "Translate safe_divide through AV, CA, RU, and UM while preserving the zero guard.",
            "tongue_shift(AV -> CA)\ntongue_shift(CA -> RU)\ntongue_shift(RU -> UM)\nseal()\n# expected: all target tongues covered",
            {"src": "AV", "dst": "UM"},
        ),
        (
            "translate_all",
            "count_words",
            "RU",
            "Translate count_words through CA, KO, UM, and RU while preserving whitespace behavior.",
            "tongue_shift(CA -> KO)\ntongue_shift(KO -> UM)\ntongue_shift(UM -> RU)\nseal()\n# expected: all target tongues covered",
            {"src": "CA", "dst": "RU"},
        ),
        (
            "dialogue",
            "handoff_plan",
            "AV",
            "Create a sealed dialogue handoff from KO planner to AV verifier with task and risk slots.",
            "tongue_shift(KO -> AV)\nseal()\n# expected: sealed dialogue handoff",
            {"src": "KO", "dst": "AV"},
        ),
        (
            "dialogue",
            "review_packet",
            "RU",
            "Create a sealed dialogue handoff from CA coder to RU reviewer with evidence and rollback slots.",
            "tongue_shift(CA -> RU)\nseal()\n# expected: sealed dialogue handoff",
            {"src": "CA", "dst": "RU"},
        ),
        (
            "dialogue",
            "status_packet",
            "UM",
            "Create a sealed dialogue handoff from AV verifier to UM operator with status and next-step slots.",
            "tongue_shift(AV -> UM)\nseal()\n# expected: sealed dialogue handoff",
            {"src": "AV", "dst": "UM"},
        ),
        (
            "multiline_edit",
            "config_patch",
            "KO",
            "Apply a multiline edit to config_patch preserving comments while changing timeout and retry slots.",
            "well_select(MULTILINE_EDIT)\nseal()\n# expected: timeout and retry lines patched",
            {"slots": ["timeout", "retry"]},
        ),
        (
            "multiline_edit",
            "readme_patch",
            "AV",
            "Apply a multiline edit to readme_patch preserving headings while changing install and test blocks.",
            "well_select(MULTILINE_EDIT)\nseal()\n# expected: install and test blocks patched",
            {"slots": ["install", "test"]},
        ),
        (
            "multiline_edit",
            "workflow_patch",
            "RU",
            "Apply a multiline edit to workflow_patch preserving triggers while changing matrix and cache blocks.",
            "well_select(MULTILINE_EDIT)\nseal()\n# expected: matrix and cache blocks patched",
            {"slots": ["matrix", "cache"]},
        ),
        (
            "translate_one",
            "abs_sum",
            "CA",
            "Translate one operation abs_sum from KO into CA while preserving absolute-value semantics.",
            "tongue_shift(KO -> CA)\nseal()\n# expected: single target tongue",
            {"src": "KO", "dst": "CA"},
        ),
        (
            "translate_one",
            "dedupe_list",
            "RU",
            "Translate one operation dedupe_list from AV into RU while preserving stable order.",
            "tongue_shift(AV -> RU)\nseal()\n# expected: single target tongue",
            {"src": "AV", "dst": "RU"},
        ),
        (
            "translate_one",
            "parse_int_safe",
            "UM",
            "Translate one operation parse_int_safe from CA into UM while preserving fallback behavior.",
            "tongue_shift(CA -> UM)\nseal()\n# expected: single target tongue",
            {"src": "CA", "dst": "UM"},
        ),
    ]

    rows: list[dict[str, Any]] = []
    for task, algorithm, tongue, instruction, assistant, meta in specs:
        rows.append(
            make_record(
                task,
                f"<input>{instruction}</input>\n<target_tongue>{tongue}</target_tongue>",
                assistant,
                {"algorithm": algorithm, "tongue": tongue, **meta},
            )
        )
    return rows


def normalize_dialogue_contract(row: dict[str, Any]) -> dict[str, Any]:
    if category(row) != "dialogue":
        return row
    meta = row.get("meta", {}) or {}
    src = meta.get("src") or meta.get("speaker_tongue") or meta.get("tongue") or "KO"
    dst = meta.get("dst") or meta.get("listener_tongue") or meta.get("tongue") or src
    if src == dst:
        program = "seal()\n# expected: sealed dialogue handoff"
    else:
        program = (
            f"tongue_shift({src} -> {dst})\nseal()\n# expected: sealed dialogue handoff"
        )
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

    OUT.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in kept) + "\n",
        encoding="utf-8",
    )
    counts = Counter(category(row) for row in kept)
    payload = {
        "schema_version": "bijective_dsl_v5_holdout_manifest_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_v4_records": len(v4),
        "repair_v3_train_records": len(repair_train),
        "repair_v3_removed": len(v4) - len(cleaned),
        "translate_one_cap": translate_one_cap,
        "floor_patch_records": len(floor_patch_rows()),
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
