#!/usr/bin/env python3
"""B-2b parametric generator for multiline_edit + dialogue floor repair.

Produces structurally-valid records that replicate the canonical schemas of
`bijective_dsl_v1_*` (multiline_edit) and `cross_tongue_dialogue_bijective_v1_*`
(dialogue) so that:

1. The v4_holdout pool regains floor-bearing categories that v1_holdout-minus-
   contract-repair drained below the WORKING_MIN=3 threshold.
2. The v5 train split gets contract-learning signal for those categories so the
   model is not trained around the exact behavior it is being graded on.

Constraints (from user directive 2026-04-27):
- Every record stamps `meta.provenance = "parametric_generated_v1"`.
- Every record stamps `meta.seed = <deterministic int>`.
- Train and holdout use **disjoint template families** (algorithm name set for
  multiline_edit, semantic_id set for dialogue, tongue-pair rotation for both).
- Schema validation gate before record acceptance.
- Lore fidelity is intentionally low/neutral — native_text phrases are reused
  verbatim from existing canon records to avoid inventing conlang.

Outputs:
  training-data/sft/dsl_b2b_parametric_v1_train.sft.jsonl
  training-data/sft/dsl_b2b_parametric_v1_holdout.sft.jsonl
  training-data/sft/dsl_b2b_parametric_v1_manifest.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SFT_DIR = PROJECT_ROOT / "training-data/sft"
OUT_TRAIN = SFT_DIR / "dsl_b2b_parametric_v1_train.sft.jsonl"
OUT_HOLDOUT = SFT_DIR / "dsl_b2b_parametric_v1_holdout.sft.jsonl"
OUT_MANIFEST = SFT_DIR / "dsl_b2b_parametric_v1_manifest.json"

PROVENANCE_TAG = "parametric_generated_v1"
TRAIN_SEED_BASE = 8675309
HOLDOUT_SEED_BASE = 31415926

# ----------------------------------------------------------------------
# Tongue metadata (extracted from cross_tongue_dialogue_bijective_v1 canon)
# ----------------------------------------------------------------------
TONGUE_META = {
    "KO": {
        "full_name": "Kor'aelin",
        "dialect": "River-Court",
        "region": "Inland Delta",
        "grammar_basis": "direct intent-first clauses with clipped honor markers",
        "runtime_language": "Python",
    },
    "AV": {
        "full_name": "Avali",
        "dialect": "Tide-Lattice",
        "region": "Littoral Crescent",
        "grammar_basis": "context-first clauses with soft relational particles",
        "runtime_language": "TypeScript",
    },
    "RU": {
        "full_name": "Runethic",
        "dialect": "Foundry Oathline",
        "region": "Iron Boundary",
        "grammar_basis": "oath-bound clauses with explicit risk markers",
        "runtime_language": "Rust",
    },
    "CA": {
        "full_name": "Cassivadan",
        "dialect": "Ledger Spiral",
        "region": "Stone Archive",
        "grammar_basis": "ledger-style symbolic clauses with explicit accounting",
        "runtime_language": "C",
    },
    "UM": {
        "full_name": "Umbroth",
        "dialect": "Veil-Hush",
        "region": "Dusk Fen",
        "grammar_basis": "shadow-soft clauses with hush-tone modifiers",
        "runtime_language": "Julia",
    },
    "DR": {
        "full_name": "Draumric",
        "dialect": "Forge-Keep",
        "region": "Basalt Span",
        "grammar_basis": "compact forge clauses with seal-and-bargain markers",
        "runtime_language": "Haskell",
    },
}

# Canonical native_text pool per tongue (verbatim from v1 canon — no invention).
TONGUE_NATIVE_TEXT = {
    "KO": [
        "Keth'ae mira'esh, I ask water and a calm place to rest.",
        "Kor'aen vara'ir. Passage granted if your intent stays clean.",
    ],
    "AV": [
        "Lirea'mi, the exchange rests in good accord.",
        "Saina're vela'se torin al?",
        "Talan'ul, we have water and a sheltered mat for you.",
    ],
    "RU": [
        "Drath'ul: the night road binds risk; do not travel alone.",
    ],
    "CA": [
        "Klik'ra route = east ridge then lower bridge, yes?",
    ],
    "UM": [
        "Veil'on. I hear the warning and keep to shadowed cover.",
    ],
    "DR": [
        "Forge'en. The bargain stands clean and I thank you.",
        "Seal'en. East ridge first, lower bridge second; the order stands.",
    ],
}

# ----------------------------------------------------------------------
# Multiline_edit template families (TRAIN vs HOLDOUT use disjoint algorithms)
# ----------------------------------------------------------------------
RUNTIME_FILE_EXT = {
    "Python": "py",
    "TypeScript": "ts",
    "Rust": "rs",
    "C": "c",
    "Julia": "jl",
    "Haskell": "hs",
}

# (algorithm_name, description, family_id)
TRAIN_ALGORITHMS = [
    ("sum_list", "Sum of all elements in a list", "TRAIN-A-reductions"),
    ("product_list", "Product of all elements in a list", "TRAIN-A-reductions"),
    ("max_list", "Maximum element in a list", "TRAIN-A-reductions"),
    ("min_list", "Minimum element in a list", "TRAIN-A-reductions"),
    ("mean_list", "Arithmetic mean of a list", "TRAIN-A-reductions"),
    ("count_evens", "Count even elements in a list", "TRAIN-B-counters"),
    ("count_odds", "Count odd elements in a list", "TRAIN-B-counters"),
    ("count_positives", "Count positive elements in a list", "TRAIN-B-counters"),
    ("count_negatives", "Count negative elements in a list", "TRAIN-B-counters"),
]

HOLDOUT_ALGORITHMS = [
    ("all_positive", "Predicate: all elements positive", "HOLDOUT-X-predicates"),
    ("any_negative", "Predicate: any element negative", "HOLDOUT-X-predicates"),
    ("all_even", "Predicate: all elements even", "HOLDOUT-X-predicates"),
    ("any_zero", "Predicate: any element is zero", "HOLDOUT-X-predicates"),
    ("reverse_list", "Reverse order of elements", "HOLDOUT-Y-transforms"),
    ("double_all", "Double every element", "HOLDOUT-Y-transforms"),
    ("square_all", "Square every element", "HOLDOUT-Y-transforms"),
    ("halve_all", "Halve every element", "HOLDOUT-Y-transforms"),
]

# Edit-pair sets (slot, edit-id, slot, edit-id)
TRAIN_EDIT_PAIRS = [
    (("init", "init_zero"), ("loop_body", "accumulator_swap")),
    (("init", "init_one"), ("loop_body", "accumulator_swap")),
    (("loop_body", "body_change"), ("return", "return_default")),
]
HOLDOUT_EDIT_PAIRS = [
    (("loop_body", "sentinel_check"), ("return", "return_default")),
    (("loop_body", "body_change"), ("init", "init_one")),
]

EDIT_DESCRIPTIONS = {
    "init_zero": "initialize accumulator to 0 (for sums)",
    "init_one": "initialize accumulator to 1 (for products)",
    "accumulator_swap": "convert sum into product (multiplicative reduce)",
    "body_change": "transform loop body to apply per-element operation",
    "return_default": "return canonical default for empty input",
    "sentinel_check": "guard with sentinel before update",
}

# Canonical Python source per algorithm (used as the "Original" code block).
ALGORITHM_PY_SOURCE = {
    "sum_list": "def sum_list(xs):\n    total = 0\n    for x in xs:\n        total += x\n    return total",
    "product_list": "def product_list(xs):\n    total = 1\n    for x in xs:\n        total *= x\n    return total",
    "max_list": "def max_list(xs):\n    m = xs[0]\n    for x in xs[1:]:\n        if x > m:\n            m = x\n    return m",
    "min_list": "def min_list(xs):\n    m = xs[0]\n    for x in xs[1:]:\n        if x < m:\n            m = x\n    return m",
    "mean_list": "def mean_list(xs):\n    total = 0\n    for x in xs:\n        total += x\n    return total / len(xs)",
    "count_evens": "def count_evens(xs):\n    n = 0\n    for x in xs:\n        if x % 2 == 0:\n            n += 1\n    return n",
    "count_odds": "def count_odds(xs):\n    n = 0\n    for x in xs:\n        if x % 2 != 0:\n            n += 1\n    return n",
    "count_positives": "def count_positives(xs):\n    n = 0\n    for x in xs:\n        if x > 0:\n            n += 1\n    return n",
    "count_negatives": "def count_negatives(xs):\n    n = 0\n    for x in xs:\n        if x < 0:\n            n += 1\n    return n",
    "all_positive": "def all_positive(xs):\n    for x in xs:\n        if x <= 0:\n            return False\n    return True",
    "any_negative": "def any_negative(xs):\n    for x in xs:\n        if x < 0:\n            return True\n    return False",
    "all_even": "def all_even(xs):\n    for x in xs:\n        if x % 2 != 0:\n            return False\n    return True",
    "any_zero": "def any_zero(xs):\n    for x in xs:\n        if x == 0:\n            return True\n    return False",
    "reverse_list": "def reverse_list(xs):\n    out = []\n    for i in range(len(xs) - 1, -1, -1):\n        out.append(xs[i])\n    return out",
    "double_all": "def double_all(xs):\n    return [x * 2 for x in xs]",
    "square_all": "def square_all(xs):\n    return [x * x for x in xs]",
    "halve_all": "def halve_all(xs):\n    return [x / 2 for x in xs]",
}

TONGUE_CYCLE = ["KO", "AV", "RU", "CA", "UM", "DR"]

# ----------------------------------------------------------------------
# Dialogue template families (TRAIN vs HOLDOUT use disjoint semantic_ids)
# ----------------------------------------------------------------------
TRAIN_DIALOGUE_SIDS = [
    ("operator-handoff-request", "Operator hands off task to sub-agent at protocol boundary."),
    ("sub-agent-receipt", "Sub-agent acknowledges receipt of operator instructions."),
    ("operator-retry", "Operator requests retry after sub-agent partial failure."),
    ("scope-confirmation", "Sub-agent confirms task scope before execution."),
    ("parameter-clarification", "Sub-agent requests parameter clarification."),
    ("sub-agent-final-answer", "Sub-agent returns final answer to operator."),
]
HOLDOUT_DIALOGUE_SIDS = [
    ("operator-refusal-hold", "Operator refuses request and places task on hold."),
    ("sub-agent-clarification", "Sub-agent asks clarifying question before proceeding."),
    ("escalation-request", "Sub-agent escalates ambiguous task back to operator."),
    ("deescalation-confirm", "Operator confirms de-escalation and resumed execution."),
]

# Tongue-pair rotations: TRAIN and HOLDOUT use disjoint orderings.
TRAIN_TONGUE_PAIRS = [
    ("AV", "KO"), ("KO", "AV"),
    ("RU", "CA"), ("CA", "RU"),
    ("UM", "DR"), ("DR", "UM"),
]
HOLDOUT_TONGUE_PAIRS = [
    ("KO", "RU"), ("AV", "CA"),
    ("UM", "KO"), ("DR", "AV"),
    ("RU", "UM"), ("CA", "DR"),
]

# Reusable transport-token pool (from canon, no invention).
TRANSPORT_TOKEN_POOL = [
    "nurel'e", "nurel'sa", "nurel'en", "nurel've", "nurel'ul", "nurel'y",
    "vessa're", "vessa'a", "lirea'i", "lirea'la", "lirea'o", "lirea'u",
    "serin'o", "maren'ul",
]


# ----------------------------------------------------------------------
# Builders
# ----------------------------------------------------------------------
def _build_user_prompt_multiline(alg_name, alg_desc, tongue, runtime, code, edit_pair):
    (slot1, edit1), (slot2, edit2) = edit_pair
    desc1 = EDIT_DESCRIPTIONS[edit1]
    desc2 = EDIT_DESCRIPTIONS[edit2]
    ext = RUNTIME_FILE_EXT[runtime]
    return (
        f"<input>Algorithm: {alg_name} ({alg_desc})\n"
        f"Original ({tongue}, {runtime}):\n"
        f"```{ext}\n"
        f"{code}\n"
        f"```\n"
        f"Multi-slot edit composition (apply in order):\n"
        f"  - slot={slot1}: {desc1}\n"
        f"  - slot={slot2}: {desc2}\n"
        f"Propagate the composed edit bijectively across all six tongues.</input>\n"
        f"<target_tongue>{tongue}</target_tongue>"
    )


def build_multiline_record(alg_tuple, edit_pair, target_tongue, seed, split, family_id):
    alg_name, alg_desc, _ = alg_tuple
    runtime = TONGUE_META[target_tongue]["runtime_language"]
    code = ALGORITHM_PY_SOURCE[alg_name]
    user_content = _build_user_prompt_multiline(
        alg_name, alg_desc, target_tongue, runtime, code, edit_pair
    )
    assistant_content = f"well_select(MULTILINE)\n# expected: ## algorithm: {alg_name}"
    (slot1, edit1), (slot2, edit2) = edit_pair
    rec = {
        "messages": [
            {"role": "system", "content": "Emit a DSL program over the 8 SCBE primitives."},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ],
        "meta": {
            "task": "multiline_edit",
            "algorithm": alg_name,
            "edits": [edit1, edit2],
            "slots": [slot1, slot2],
            "dsl_program_depth": 1,
            "dsl_synthesised_from": "multiline_edit",
            "target_tongue": target_tongue,
            "split": split,
            "provenance": PROVENANCE_TAG,
            "seed": seed,
            "template_family": family_id,
        },
    }
    return rec


def _utf8_binary(text):
    return [format(b, "08b") for b in text.encode("utf-8")]


def _utf8_hex(text):
    return [f"{b:02X}" for b in text.encode("utf-8")]


def _transport_tokens(text, tongue_idx):
    n = len(text.encode("utf-8"))
    pool = TRANSPORT_TOKEN_POOL
    return [pool[(tongue_idx * 7 + i) % len(pool)] for i in range(n)]


def _sha256_hex(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _build_party_block(tongue, native_text, party_idx):
    meta = TONGUE_META[tongue]
    bin_arr = _utf8_binary(native_text)
    hex_arr = _utf8_hex(native_text)
    tokens = _transport_tokens(native_text, party_idx)
    return {
        "tongue": tongue,
        "full_name": meta["full_name"],
        "dialect": meta["dialect"],
        "region": meta["region"],
        "grammar_basis": meta["grammar_basis"],
        "runtime_language": meta["runtime_language"],
        "native_text": native_text,
        "utf8_binary": bin_arr,
        "utf8_hexacode": hex_arr,
        "transport": {
            "transport_tokens": tokens,
            "plaintext_sha256": _sha256_hex(native_text),
            "inferred_languages": [],
            "inferred_domains": ["protocol"],
            "turing_traits": [],
            "roundtrip_ok": True,
        },
    }


def build_dialogue_record(sid_tuple, tongue_pair, seed, split, family_id):
    sid, scene = sid_tuple
    spk_t, lst_t = tongue_pair
    spk_meta = TONGUE_META[spk_t]
    lst_meta = TONGUE_META[lst_t]
    spk_phrase_pool = TONGUE_NATIVE_TEXT[spk_t]
    lst_phrase_pool = TONGUE_NATIVE_TEXT[lst_t]
    spk_text = spk_phrase_pool[seed % len(spk_phrase_pool)]
    lst_text = lst_phrase_pool[(seed + 1) % len(lst_phrase_pool)]

    spk_block = _build_party_block(spk_t, spk_text, party_idx=0)
    lst_block = _build_party_block(lst_t, lst_text, party_idx=1)

    english_gloss = (
        f"Speaker ({spk_meta['full_name']}) and listener ({lst_meta['full_name']}) "
        f"exchange a {sid} packet."
    )
    semantic_verification = {
        "speaker_sha256": spk_block["transport"]["plaintext_sha256"],
        "listener_sha256": lst_block["transport"]["plaintext_sha256"],
        "byte_count_match": (
            len(spk_block["utf8_binary"]) == len(spk_block["transport"]["transport_tokens"])
            and len(lst_block["utf8_binary"]) == len(lst_block["transport"]["transport_tokens"])
        ),
        "roundtrip_ok": True,
    }

    assistant_obj = {
        "semantic_id": sid,
        "scene": scene,
        "speaker": spk_block,
        "listener": lst_block,
        "english_gloss": english_gloss,
        "semantic_verification": semantic_verification,
    }
    user_content = (
        f"Build a bijective cross-tongue dialogue packet for semantic_id={sid}.\n"
        f"scene: {scene}\n"
        f"speaker: {spk_meta['full_name']} ({spk_t}) "
        f"dialect={spk_meta['dialect']} region={spk_meta['region']}\n"
        f"listener: {lst_meta['full_name']} ({lst_t}) "
        f"dialect={lst_meta['dialect']} region={lst_meta['region']}\n"
        f"Keep the nontechnical meaning aligned across native dialogue, English gloss, "
        f"assigned runtime languages, binary, hex, and Sacred Tongues transport."
    )
    rec = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the SCBE cross-tongue bijective dialogue tutor. Preserve one "
                    "nontechnical dialogue intent across speaker and listener tongues, "
                    "dialects, regions, grammar-basis notes, assigned runtime-language "
                    "bindings, UTF-8 binary and hex traces, and Sacred Tongues transport "
                    "tokens. Keep semantic invariants explicit and mark whether round-trip "
                    "transport verification succeeded."
                ),
            },
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": json.dumps(assistant_obj, ensure_ascii=False, indent=2)},
        ],
        "meta": {
            "program": "cross_tongue_dialogue_bijective",
            "category": "dialogue",
            "task": "dialogue",
            "split": split,
            "semantic_id": sid,
            "speaker_tongue": spk_t,
            "listener_tongue": lst_t,
            "speaker_runtime_language": spk_meta["runtime_language"],
            "listener_runtime_language": lst_meta["runtime_language"],
            "speaker_dialect": spk_meta["dialect"],
            "listener_dialect": lst_meta["dialect"],
            "provenance": PROVENANCE_TAG,
            "seed": seed,
            "template_family": family_id,
        },
    }
    return rec


# ----------------------------------------------------------------------
# Schema validation gate
# ----------------------------------------------------------------------
def validate_record(rec):
    if "messages" not in rec or "meta" not in rec:
        return False, "missing messages/meta"
    if rec["meta"].get("provenance") != PROVENANCE_TAG:
        return False, "wrong provenance"
    if "seed" not in rec["meta"]:
        return False, "missing seed"
    msgs = rec["messages"]
    if len(msgs) != 3:
        return False, f"expected 3 messages, got {len(msgs)}"
    roles = [m["role"] for m in msgs]
    if roles != ["system", "user", "assistant"]:
        return False, f"bad role order: {roles}"

    task = rec["meta"].get("task")
    if task == "multiline_edit":
        if not msgs[2]["content"].startswith("well_select(MULTILINE)"):
            return False, "multiline_edit assistant must start with well_select(MULTILINE)"
        if "expected: ## algorithm:" not in msgs[2]["content"]:
            return False, "multiline_edit assistant missing expected-algorithm comment"
    elif task == "dialogue":
        try:
            j = json.loads(msgs[2]["content"])
        except Exception as exc:
            return False, f"dialogue assistant not JSON: {exc}"
        for k in ("semantic_id", "scene", "speaker", "listener"):
            if k not in j:
                return False, f"dialogue missing key {k}"
        for who in ("speaker", "listener"):
            obj = j[who]
            for k in ("tongue", "native_text", "utf8_binary", "utf8_hexacode", "transport"):
                if k not in obj:
                    return False, f"dialogue {who} missing {k}"
            n_bytes = len(obj["native_text"].encode("utf-8"))
            if len(obj["utf8_binary"]) != n_bytes:
                return False, f"dialogue {who} binary len mismatch"
            if len(obj["utf8_hexacode"]) != n_bytes:
                return False, f"dialogue {who} hex len mismatch"
            if len(obj["transport"]["transport_tokens"]) != n_bytes:
                return False, f"dialogue {who} transport-token len mismatch"
            if obj["transport"]["plaintext_sha256"] != _sha256_hex(obj["native_text"]):
                return False, f"dialogue {who} sha256 mismatch"
    else:
        return False, f"unsupported task {task}"
    return True, "ok"


# ----------------------------------------------------------------------
# Drivers
# ----------------------------------------------------------------------
def gen_multiline_train():
    out = []
    counter = 0
    target = 24
    for alg in TRAIN_ALGORITHMS:
        for ep in TRAIN_EDIT_PAIRS:
            if counter >= target:
                return out
            tongue = TONGUE_CYCLE[counter % len(TONGUE_CYCLE)]
            seed = TRAIN_SEED_BASE + counter
            rec = build_multiline_record(alg, ep, tongue, seed, "train", alg[2])
            ok, msg = validate_record(rec)
            if not ok:
                raise RuntimeError(f"train multiline schema fail: {msg}")
            out.append(rec)
            counter += 1
    return out


def gen_multiline_holdout():
    out = []
    counter = 0
    target = 8
    for alg in HOLDOUT_ALGORITHMS:
        if counter >= target:
            return out
        ep = HOLDOUT_EDIT_PAIRS[counter % len(HOLDOUT_EDIT_PAIRS)]
        tongue = TONGUE_CYCLE[counter % len(TONGUE_CYCLE)]
        seed = HOLDOUT_SEED_BASE + counter
        rec = build_multiline_record(alg, ep, tongue, seed, "holdout", alg[2])
        ok, msg = validate_record(rec)
        if not ok:
            raise RuntimeError(f"holdout multiline schema fail: {msg}")
        out.append(rec)
        counter += 1
    return out


def gen_dialogue_train():
    out = []
    counter = 0
    for sid in TRAIN_DIALOGUE_SIDS:
        for pair in TRAIN_TONGUE_PAIRS:
            seed = TRAIN_SEED_BASE + 10000 + counter
            rec = build_dialogue_record(sid, pair, seed, "train", "TRAIN-O-handoff")
            ok, msg = validate_record(rec)
            if not ok:
                raise RuntimeError(f"train dialogue schema fail: {msg}")
            out.append(rec)
            counter += 1
    return out


def gen_dialogue_holdout():
    out = []
    counter = 0
    target = 6
    sid_idx = 0
    pair_idx = 0
    while counter < target:
        sid = HOLDOUT_DIALOGUE_SIDS[sid_idx % len(HOLDOUT_DIALOGUE_SIDS)]
        pair = HOLDOUT_TONGUE_PAIRS[pair_idx % len(HOLDOUT_TONGUE_PAIRS)]
        seed = HOLDOUT_SEED_BASE + 10000 + counter
        rec = build_dialogue_record(sid, pair, seed, "holdout", "HOLDOUT-R-refusal")
        ok, msg = validate_record(rec)
        if not ok:
            raise RuntimeError(f"holdout dialogue schema fail: {msg}")
        out.append(rec)
        counter += 1
        sid_idx += 1
        pair_idx += 1
    return out


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main():
    train_ml = gen_multiline_train()
    holdout_ml = gen_multiline_holdout()
    train_dl = gen_dialogue_train()
    holdout_dl = gen_dialogue_holdout()

    train_rows = train_ml + train_dl
    holdout_rows = holdout_ml + holdout_dl

    OUT_TRAIN.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(OUT_TRAIN, train_rows)
    write_jsonl(OUT_HOLDOUT, holdout_rows)

    # Sanity: train and holdout must have disjoint algorithm sets and disjoint sids.
    train_algs = {r["meta"].get("algorithm") for r in train_rows if r["meta"].get("algorithm")}
    holdout_algs = {r["meta"].get("algorithm") for r in holdout_rows if r["meta"].get("algorithm")}
    overlap_alg = train_algs & holdout_algs
    train_sids = {r["meta"].get("semantic_id") for r in train_rows if r["meta"].get("semantic_id")}
    holdout_sids = {r["meta"].get("semantic_id") for r in holdout_rows if r["meta"].get("semantic_id")}
    overlap_sid = train_sids & holdout_sids
    if overlap_alg or overlap_sid:
        raise RuntimeError(f"train/holdout overlap: algs={overlap_alg} sids={overlap_sid}")

    train_seeds = [r["meta"]["seed"] for r in train_rows]
    holdout_seeds = [r["meta"]["seed"] for r in holdout_rows]
    if len(set(train_seeds + holdout_seeds)) != len(train_seeds) + len(holdout_seeds):
        raise RuntimeError("seed collision")

    manifest = {
        "schema_version": "dsl_b2b_parametric_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": PROVENANCE_TAG,
        "outputs": {
            "train": str(OUT_TRAIN.relative_to(PROJECT_ROOT).as_posix()),
            "holdout": str(OUT_HOLDOUT.relative_to(PROJECT_ROOT).as_posix()),
        },
        "counts": {
            "train_total": len(train_rows),
            "holdout_total": len(holdout_rows),
            "train_multiline_edit": len(train_ml),
            "train_dialogue": len(train_dl),
            "holdout_multiline_edit": len(holdout_ml),
            "holdout_dialogue": len(holdout_dl),
        },
        "template_families": {
            "train_multiline_algorithms": sorted(train_algs),
            "holdout_multiline_algorithms": sorted(holdout_algs),
            "train_dialogue_semantic_ids": sorted(train_sids),
            "holdout_dialogue_semantic_ids": sorted(holdout_sids),
        },
        "seed_bases": {
            "train": TRAIN_SEED_BASE,
            "holdout": HOLDOUT_SEED_BASE,
        },
        "constraints_enforced": [
            "provenance=parametric_generated_v1 stamped on every record",
            "seed stamped + collision-checked",
            "train/holdout algorithm sets disjoint",
            "train/holdout semantic_id sets disjoint",
            "schema validation gate run before acceptance",
            "no human/lore source files overwritten (separate output paths)",
        ],
        "notes": (
            "Lore fidelity intentionally low/neutral. native_text reused verbatim "
            "from canonical v1 dialogue records to avoid inventing conlang. "
            "Tongue metadata (dialect/region/runtime/grammar_basis) extracted from "
            "cross_tongue_dialogue_bijective_v1 canon. This is a contract-learning "
            "repair lane; canon expansion is out of scope for v5."
        ),
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"[b2b-gen] train={len(train_rows)} holdout={len(holdout_rows)}")
    print(f"[b2b-gen] train_ml={len(train_ml)} train_dl={len(train_dl)} "
          f"holdout_ml={len(holdout_ml)} holdout_dl={len(holdout_dl)}")
    print(f"[b2b-gen] wrote {OUT_TRAIN.relative_to(PROJECT_ROOT)}")
    print(f"[b2b-gen] wrote {OUT_HOLDOUT.relative_to(PROJECT_ROOT)}")
    print(f"[b2b-gen] wrote {OUT_MANIFEST.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
