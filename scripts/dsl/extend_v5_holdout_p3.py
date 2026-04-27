#!/usr/bin/env python3
"""P-3 floor patch: extend v5 holdout to >=30 multiline_edit + >=30 dialogue rows.

The kernel's per-category contract gate needs statistical power (>=30 each)
to reject contract collapse on the thin lanes. v5 currently sits at
multiline_edit=8, dialogue=8 (per `v5_tokenizer_audit.json` and direct grep
2026-04-27). This script appends parametric holdout-only rows that match the
existing schema:

  - multiline_edit -> assistant emits `well_select(MULTILINE)\n# expected: ...`
  - dialogue       -> assistant emits `tongue_shift(SRC -> DST)\nseal()\n# expected: ...`

Idempotent: rows are deduped by sha256 over (user, assistant) before append.
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
HOLDOUT = SFT / "bijective_dsl_v5_holdout.sft.jsonl"
MANIFEST = SFT / "bijective_dsl_v5_holdout_manifest.json"

TONGUE_NAMES = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}
TONGUE_RUNTIMES = {
    "KO": ("Python", "py"),
    "AV": ("TypeScript", "ts"),
    "RU": ("Rust", "rs"),
    "CA": ("C", "c"),
    "UM": ("Julia", "jl"),
    "DR": ("Haskell", "hs"),
}

# (algo_id, description, body lines per language)
MULTILINE_ALGOS = [
    ("max_value", "Maximum element of a list",
     {"py": "def max_value(xs):\n    m = xs[0]\n    for x in xs:\n        if x > m:\n            m = x\n    return m",
      "ts": "function maxValue(xs:number[]):number{\n  let m = xs[0];\n  for (const x of xs) if (x > m) m = x;\n  return m;\n}",
      "rs": "fn max_value(xs: &[i64]) -> i64 {\n    let mut m = xs[0];\n    for &x in xs { if x > m { m = x; } }\n    m\n}",
      "c":  "long max_value(long *xs, size_t n){\n  long m = xs[0];\n  for(size_t i=0;i<n;++i) if(xs[i]>m) m=xs[i];\n  return m;\n}",
      "jl": "function max_value(xs)\n  m = xs[1]\n  for x in xs; if x > m; m = x; end; end\n  m\nend",
      "hs": "maxValue :: [Int] -> Int\nmaxValue (x:xs) = foldl max x xs"}),
    ("min_value", "Minimum element of a list", None),
    ("count_evens", "Count even elements", None),
    ("count_odds", "Count odd elements", None),
    ("contains_zero", "Predicate: list contains zero", None),
    ("triple_all", "Triple every element", None),
    ("negate_all", "Negate every element", None),
    ("abs_all", "Absolute value of every element", None),
    ("running_sum", "Running sum (prefix sums)", None),
    ("running_max", "Running maximum", None),
    ("dedupe", "Remove consecutive duplicates", None),
    ("clip_positive", "Clip negatives to zero", None),
    ("scale_by", "Scale every element by k", None),
    ("zip_pairs", "Pair adjacent elements", None),
    ("first_index_of", "First index of target", None),
    ("last_index_of", "Last index of target", None),
    ("fill_default", "Fill empty slots with default", None),
    ("rotate_left", "Rotate list left by one", None),
    ("rotate_right", "Rotate list right by one", None),
    ("interleave", "Interleave two lists", None),
    ("partition_by", "Partition by predicate", None),
    ("take_while", "Take while predicate holds", None),
    ("drop_while", "Drop while predicate holds", None),
    ("flatten_one", "Flatten one level of nesting", None),
]


def _stub_body(algo_id: str, ext: str) -> str:
    # Generic minimal stub — the assistant target only exercises the
    # well_select(MULTILINE) emission, not the full body. Body just needs to
    # be syntactically plausible per language so the prompt looks realistic.
    if ext == "py":
        return f"def {algo_id}(xs):\n    out = []\n    for x in xs:\n        out.append(x)\n    return out"
    if ext == "ts":
        return f"function {algo_id}(xs:number[]):number[]{{\n  const out:number[] = [];\n  for (const x of xs) out.push(x);\n  return out;\n}}"
    if ext == "rs":
        return f"fn {algo_id}(xs: &[i64]) -> Vec<i64> {{\n    let mut out = Vec::new();\n    for &x in xs {{ out.push(x); }}\n    out\n}}"
    if ext == "c":
        return f"void {algo_id}(long *xs, size_t n, long *out){{\n  for(size_t i=0;i<n;++i) out[i]=xs[i];\n}}"
    if ext == "jl":
        return f"function {algo_id}(xs)\n  out = []\n  for x in xs; push!(out, x); end\n  out\nend"
    if ext == "hs":
        return f"{algo_id} :: [Int] -> [Int]\n{algo_id} = id"
    return ""


SLOT_EDIT_PAIRS = [
    (["loop_body", "return"], ["sentinel_check", "return_default"],
     "guard with sentinel before update", "return canonical default for empty input"),
    (["init", "loop_body"], ["init_one", "body_change"],
     "initialize accumulator to 1 (for products)", "transform loop body to apply per-element operation"),
    (["compare", "return"], ["strict_compare", "return_default"],
     "use strict comparison (< instead of <=)", "return canonical default for empty input"),
    (["init", "step"], ["init_zero", "step_increment"],
     "initialize accumulator to 0", "advance counter at each step"),
]

DIALOGUE_SCENES = [
    ("supply-line-handoff", "Supply line operator hands the wagon list off to the foreman."),
    ("watchtower-call", "Watchtower calls the next shift in to take the post."),
    ("river-pilot-query", "River pilot asks the lock keeper for current draft."),
    ("forge-test-pass", "Forge tester confirms the alloy passes the bend test."),
    ("library-claim-check", "Archivist confirms the citation index is valid."),
    ("frontier-greeting", "Outpost greeter welcomes traveler at the gate."),
    ("market-price-quote", "Market caller quotes the day's price for grain."),
    ("camp-fire-watch", "Camp fire watch hands report to the relief watch."),
    ("messenger-relay", "Messenger relays the courier packet receipt."),
    ("harbor-clear", "Harbor master signals clear-to-depart."),
    ("hunters-return", "Hunters report the day's catch back to the cook."),
    ("council-recess", "Council herald announces recess and reconvene time."),
    ("scout-position", "Scout reports current position and bearing."),
    ("trader-confirm", "Trader confirms final tally before signing."),
    ("guildhall-summons", "Guildhall page summons member to the floor."),
    ("granary-count", "Granary keeper confirms grain count for the season."),
    ("herald-announcement", "Herald posts the public announcement."),
    ("docent-tour-end", "Docent ends the tour and dismisses the group."),
    ("smith-order-up", "Smith calls 'order up' on the finished blade."),
    ("ward-relief", "Ward relief checks in for the night shift."),
    ("ferry-cast-off", "Ferry hand signals cast-off to the dock."),
    ("brewer-batch-set", "Brewer confirms the batch is set for the night."),
    ("scribe-fair-copy", "Scribe submits the fair copy for seal."),
    ("falconer-recall", "Falconer signals the recall to the bird."),
    ("camp-quiet-hour", "Camp warden calls quiet hour."),
    ("road-toll-paid", "Toll keeper records that the toll is paid."),
]

DIALOGUE_PAIRS = [
    ("KO", "AV"), ("AV", "RU"), ("RU", "CA"), ("CA", "UM"), ("UM", "DR"), ("DR", "KO"),
    ("KO", "RU"), ("AV", "CA"), ("RU", "UM"), ("CA", "DR"), ("UM", "KO"), ("DR", "AV"),
    ("KO", "CA"), ("AV", "UM"), ("RU", "DR"), ("CA", "KO"), ("UM", "AV"), ("DR", "RU"),
    ("KO", "UM"), ("AV", "DR"), ("RU", "KO"), ("CA", "AV"), ("UM", "RU"), ("DR", "CA"),
    ("KO", "DR"), ("AV", "KO"),
]

DIALECTS = {
    "KO": ("River-Court", "Inland Delta"),
    "AV": ("Sky-Mark", "Open Plateau"),
    "RU": ("Foundry Oathline", "Iron Boundary"),
    "CA": ("Ledger Spiral", "Stone Archive"),
    "UM": ("Veil-Hush", "Dusk Fen"),
    "DR": ("Forge-Keep", "Basalt Span"),
}


def signature(row: dict[str, Any]) -> str:
    user = "\n".join(m.get("content", "") for m in row.get("messages", []) if m.get("role") == "user")
    assistant = "\n".join(m.get("content", "") for m in row.get("messages", []) if m.get("role") == "assistant")
    return hashlib.sha256(f"{user}\n---\n{assistant}".encode("utf-8")).hexdigest()


def make_multiline_row(algo_id: str, desc: str, tongue: str, slot_idx: int, seed: int) -> dict[str, Any]:
    runtime, ext = TONGUE_RUNTIMES[tongue]
    body = _stub_body(algo_id, ext)
    slots, edits, edit_a, edit_b = SLOT_EDIT_PAIRS[slot_idx % len(SLOT_EDIT_PAIRS)]
    user = (
        f"<input>Algorithm: {algo_id} ({desc})\n"
        f"Original ({tongue}, {runtime}):\n```{ext}\n{body}\n```\n"
        f"Multi-slot edit composition (apply in order):\n"
        f"  - slot={slots[0]}: {edit_a}\n"
        f"  - slot={slots[1]}: {edit_b}\n"
        f"Propagate the composed edit bijectively across all six tongues.</input>\n"
        f"<target_tongue>{tongue}</target_tongue>"
    )
    assistant = f"well_select(MULTILINE)\n# expected: ## algorithm: {algo_id}"
    return {
        "messages": [
            {"role": "system", "content": "Emit a DSL program over the 8 SCBE primitives."},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "meta": {
            "task": "multiline_edit",
            "category": "multiline_edit",
            "algorithm": algo_id,
            "edits": list(edits),
            "slots": list(slots),
            "dsl_program_depth": 1,
            "dsl_synthesised_from": "multiline_edit",
            "target_tongue": tongue,
            "split": "holdout",
            "provenance": "v5_holdout_p3_floor_patch",
            "seed": seed,
            "template_family": "HOLDOUT-P3-multiline",
            "holdout_only": True,
        },
    }


def make_dialogue_row(scene_id: str, scene_desc: str, src: str, dst: str, seed: int) -> dict[str, Any]:
    src_runtime, _ = TONGUE_RUNTIMES[src]
    dst_runtime, _ = TONGUE_RUNTIMES[dst]
    src_dialect, src_region = DIALECTS[src]
    dst_dialect, dst_region = DIALECTS[dst]
    user = (
        f"<input>Build a bijective cross-tongue dialogue packet for semantic_id={scene_id}.\n"
        f"scene: {scene_desc}\n"
        f"speaker: {TONGUE_NAMES[src]} ({src}) dialect={src_dialect} region={src_region}\n"
        f"listener: {TONGUE_NAMES[dst]} ({dst}) dialect={dst_dialect} region={dst_region}\n"
        f"Keep the nontechnical meaning aligned across native dialogue, English gloss, "
        f"assigned runtime languages, binary, hex, and Sacred Tongues transport.</input>\n"
        f"<target_tongue>{dst}</target_tongue>"
    )
    if src == dst:
        assistant = "seal()\n# expected: sealed dialogue handoff"
        depth = 1
    else:
        assistant = f"tongue_shift({src} -> {dst})\nseal()\n# expected: sealed dialogue handoff"
        depth = 2
    return {
        "messages": [
            {"role": "system", "content": "Emit a DSL program over the 8 SCBE primitives."},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "meta": {
            "program": "cross_tongue_dialogue_bijective",
            "category": "dialogue",
            "task": "dialogue",
            "split": "holdout",
            "semantic_id": scene_id,
            "speaker_tongue": src,
            "listener_tongue": dst,
            "speaker_runtime_language": src_runtime,
            "listener_runtime_language": dst_runtime,
            "speaker_dialect": src_dialect,
            "listener_dialect": dst_dialect,
            "dsl_program_depth": depth,
            "dsl_synthesised_from": "dialogue",
            "provenance": "v5_holdout_p3_floor_patch",
            "seed": seed,
            "template_family": "HOLDOUT-P3-dialogue",
            "dialogue_contract_normalized": True,
            "holdout_only": True,
        },
    }


def build_new_rows(target_per_lane: int = 30) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    tongues = list(TONGUE_RUNTIMES.keys())
    multiline_rows: list[dict[str, Any]] = []
    base_seed = 41527000
    for i, (algo_id, desc, _) in enumerate(MULTILINE_ALGOS):
        tongue = tongues[i % len(tongues)]
        slot_idx = i % len(SLOT_EDIT_PAIRS)
        multiline_rows.append(make_multiline_row(algo_id, desc, tongue, slot_idx, base_seed + i))
        if len(multiline_rows) >= target_per_lane:
            break

    dialogue_rows: list[dict[str, Any]] = []
    seed_base = 42528000
    n = len(DIALOGUE_PAIRS)
    for i, (scene_id, scene_desc) in enumerate(DIALOGUE_SCENES):
        src, dst = DIALOGUE_PAIRS[i % n]
        dialogue_rows.append(make_dialogue_row(scene_id, scene_desc, src, dst, seed_base + i))
        if len(dialogue_rows) >= target_per_lane:
            break

    return multiline_rows, dialogue_rows


def main() -> int:
    existing_text = HOLDOUT.read_text(encoding="utf-8")
    existing_rows = [json.loads(line) for line in existing_text.splitlines() if line.strip()]
    existing_sigs = {signature(row) for row in existing_rows}

    multiline_new, dialogue_new = build_new_rows(target_per_lane=30)

    cur_multiline = sum(1 for r in existing_rows if (r.get("meta") or {}).get("task") == "multiline_edit")
    cur_dialogue = sum(1 for r in existing_rows if (r.get("meta") or {}).get("category") == "dialogue")

    needed_multi = max(0, 30 - cur_multiline)
    needed_dlg = max(0, 30 - cur_dialogue)

    appended: list[dict[str, Any]] = []
    for row in multiline_new:
        if needed_multi <= 0:
            break
        sig = signature(row)
        if sig in existing_sigs:
            continue
        appended.append(row)
        existing_sigs.add(sig)
        needed_multi -= 1
    for row in dialogue_new:
        if needed_dlg <= 0:
            break
        sig = signature(row)
        if sig in existing_sigs:
            continue
        appended.append(row)
        existing_sigs.add(sig)
        needed_dlg -= 1

    if not appended:
        print("No new rows needed; floors already met.")
        return 0

    new_text_block = "\n".join(json.dumps(row, ensure_ascii=False) for row in appended)
    final_text = existing_text.rstrip("\n") + "\n" + new_text_block + "\n"
    HOLDOUT.write_text(final_text, encoding="utf-8")

    final_rows = [json.loads(line) for line in final_text.splitlines() if line.strip()]
    counts = Counter()
    for row in final_rows:
        meta = row.get("meta") or {}
        cat = meta.get("category") or meta.get("task") or "unknown"
        counts[cat] += 1

    payload = {
        "schema_version": "bijective_dsl_v5_holdout_manifest_v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "p3_floor_patch_appended": len(appended),
        "p3_appended_multiline_edit": sum(
            1 for r in appended if (r.get("meta") or {}).get("task") == "multiline_edit"
        ),
        "p3_appended_dialogue": sum(
            1 for r in appended if (r.get("meta") or {}).get("category") == "dialogue"
        ),
        "output": str(HOLDOUT.relative_to(ROOT).as_posix()),
        "output_records": len(final_rows),
        "by_category": dict(counts),
        "sha256": hashlib.sha256(HOLDOUT.read_bytes()).hexdigest(),
    }
    MANIFEST.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Appended {len(appended)} rows -> {payload['output']} (now {payload['output_records']} total)")
    print(json.dumps(payload["by_category"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
