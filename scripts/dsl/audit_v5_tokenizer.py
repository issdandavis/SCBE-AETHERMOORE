#!/usr/bin/env python3
"""v5 tokenizer audit for Qwen/Qwen2.5-Coder-0.5B-Instruct.

Records token IDs for the 9 selector primitives (B-1) in their canonical
emission contexts so the kernel-template `compute_loss` weighted CE can
load them as a fixed list rather than re-tokenizing each step.

Strategy: BPE often merges `(` with the following alphanumerics
(`(ID`, `(AL`, `(SE`, ...). A naive substring matcher misses these.
Instead we extract the payload id span by ORDERED MULTISET DIFFERENCE
between `well_select(SEL)` and `well_select()` (and `well_select(slot_body)`
for EDIT_ prefixes). Whatever is left after removing one instance of each
neutral-context token IS the selector-specific span the kernel must upweight.

Outputs:
  artifacts/dsl_eval_reports/v5_tokenizer_audit.json

Exit codes:
  0  PASS  (every selector has a stable, deterministic payload id chain)
  2  FAIL  (any selector's payload chain differs across emission contexts)
"""
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

from transformers import AutoTokenizer  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = PROJECT_ROOT / "artifacts/dsl_eval_reports/v5_tokenizer_audit.json"

BASE_MODEL = "Qwen/Qwen2.5-Coder-0.5B-Instruct"

SELECTOR_TOKENS = [
    "TRANSLATED",
    "TRANSLATED_ALL",
    "IDENTIFIED",
    "ALIGNED",
    "GOVERNANCE",
    "MULTILINE",
    "SEALED",
]
SELECTOR_PREFIX_TOKENS = ["EDIT_", "EDIT_ALL_"]

CONTEXT_TEMPLATES = [
    ("paren", "well_select({sel})", "well_select()"),
    ("paren_nl", "well_select({sel})\n", "well_select()\n"),
    ("paren_lead_space", " well_select({sel})", " well_select()"),
    ("after_assistant", "assistant\nwell_select({sel})", "assistant\nwell_select()"),
]

PREFIX_CONTEXTS = [
    ("slot_body", "well_select({sel}slot_body)", "well_select(slot_body)"),
    ("slot_head", "well_select({sel}slot_head)", "well_select(slot_head)"),
    ("lead_space_slot_body", " well_select({sel}slot_body)", " well_select(slot_body)"),
]


def _ids(tok, text: str) -> list[int]:
    return tok.encode(text, add_special_tokens=False)


def _ordered_multiset_diff(payload_ctx_ids: list[int], neutral_ctx_ids: list[int]) -> list[int]:
    """Return ids from `payload_ctx_ids` minus one occurrence each of `neutral_ctx_ids`.

    Preserves order. This isolates the BPE token span that is *specific* to
    the payload, even when the selector merged with surrounding punctuation
    (e.g. `(ID`, `(AL`).
    """
    counts = Counter(neutral_ctx_ids)
    out: list[int] = []
    for tid in payload_ctx_ids:
        if counts.get(tid, 0) > 0:
            counts[tid] -= 1
        else:
            out.append(tid)
    return out


# BPE trailing-paren equivalence class for Qwen2.5-Coder.
# `)` (id 8) and `)\n` (id 340) are interchangeable trailing tokens depending
# on whether the close-paren merges with a following newline. Both must end
# up in the upweight union; chain-stability is checked modulo this class.
TRAILING_PAREN_VARIANTS = {8, 340}


def _normalize_chain(chain: tuple[int, ...]) -> tuple[int, ...]:
    """Collapse trailing-paren variants so chain-stability ignores `)` vs `)\\n`."""
    return tuple(0 if tid in TRAILING_PAREN_VARIANTS else tid for tid in chain)


def _audit_target(tok, name: str, payload_text: str, contexts) -> dict:
    per_context: dict[str, dict] = {}
    chains: dict[tuple[int, ...], list[str]] = {}
    normalized_chains: dict[tuple[int, ...], list[str]] = {}
    union_ids: set[int] = set()
    bare_ids = _ids(tok, payload_text)
    for ctx_name, payload_tmpl, neutral_tmpl in contexts:
        payload_ctx = payload_tmpl.format(sel=payload_text)
        neutral_ctx = neutral_tmpl
        payload_ids = _ids(tok, payload_ctx)
        neutral_ids = _ids(tok, neutral_ctx)
        diff = _ordered_multiset_diff(payload_ids, neutral_ids)
        decoded_pieces = [tok.decode([i], skip_special_tokens=False) for i in diff]
        per_context[ctx_name] = {
            "payload_context": payload_ctx,
            "neutral_context": neutral_ctx,
            "payload_ctx_ids": payload_ids,
            "neutral_ctx_ids": neutral_ids,
            "diff_ids": diff,
            "diff_pieces": decoded_pieces,
            "diff_decoded": "".join(decoded_pieces),
        }
        chain = tuple(diff)
        chains.setdefault(chain, []).append(ctx_name)
        normalized_chains.setdefault(_normalize_chain(chain), []).append(ctx_name)
        union_ids.update(diff)

    stable_strict = len(chains) == 1
    stable_modulo_paren = len(normalized_chains) == 1
    canonical = max(chains.items(), key=lambda kv: len(kv[1]))[0] if chains else tuple()

    return {
        "payload_text": payload_text,
        "bare": {
            "ids": bare_ids,
            "n_tokens": len(bare_ids),
            "pieces": [tok.decode([i], skip_special_tokens=False) for i in bare_ids],
        },
        "per_context": per_context,
        "stable_across_contexts": stable_strict,
        "stable_modulo_trailing_paren": stable_modulo_paren,
        "distinct_diff_chains": [list(c) for c in chains.keys()],
        "canonical_diff_ids": list(canonical),
        "canonical_diff_pieces": [tok.decode([i], skip_special_tokens=False) for i in canonical],
        "union_diff_ids": sorted(union_ids),
        "union_diff_pieces": [
            tok.decode([i], skip_special_tokens=False) for i in sorted(union_ids)
        ],
    }


def main() -> int:
    tok = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=False)

    special = {
        "tokenizer_class": tok.__class__.__name__,
        "vocab_size": int(tok.vocab_size),
        "pad_token": tok.pad_token,
        "pad_token_id": tok.pad_token_id,
        "eos_token": tok.eos_token,
        "eos_token_id": tok.eos_token_id,
        "bos_token": tok.bos_token,
        "bos_token_id": tok.bos_token_id,
        "model_max_length": getattr(tok, "model_max_length", None),
    }

    chat_special = {}
    for name in ("<|im_start|>", "<|im_end|>", "<|endoftext|>"):
        ids = _ids(tok, name)
        chat_special[name] = ids[0] if len(ids) == 1 else ids

    failures: list[str] = []

    selector_audit: dict[str, dict] = {}
    paren_variant_only: list[str] = []
    for sel in SELECTOR_TOKENS:
        info = _audit_target(tok, sel, sel, CONTEXT_TEMPLATES)
        selector_audit[sel] = info
        if not info["stable_modulo_trailing_paren"]:
            failures.append(
                f"{sel}: {len(info['distinct_diff_chains'])} distinct diff chains "
                "across contexts (NOT just trailing-paren variant)"
            )
        elif not info["stable_across_contexts"]:
            paren_variant_only.append(sel)
        if not info["canonical_diff_ids"]:
            failures.append(f"{sel}: empty canonical diff (set-diff cancelled the entire selector)")

    prefix_audit: dict[str, dict] = {}
    for pref in SELECTOR_PREFIX_TOKENS:
        info = _audit_target(tok, pref, pref, PREFIX_CONTEXTS)
        prefix_audit[pref] = info
        if not info["stable_modulo_trailing_paren"]:
            failures.append(
                f"{pref}: {len(info['distinct_diff_chains'])} distinct diff chains "
                "across contexts (NOT just trailing-paren variant)"
            )
        elif not info["stable_across_contexts"]:
            paren_variant_only.append(pref)

    # B-1 fast-path: union of all per-context diff ids across all contexts.
    # Using union (not canonical) means trailing-paren variants `)` (8) and
    # `)\n` (340) both end up in the upweight set, so the kernel handles
    # whichever variant the training labels actually carry.
    weighted_ce_ids: set[int] = set()
    for info in selector_audit.values():
        weighted_ce_ids.update(info["union_diff_ids"])
    for info in prefix_audit.values():
        weighted_ce_ids.update(info["union_diff_ids"])

    weighted_ce_table = sorted(
        [
            {"id": tid, "decoded": tok.decode([tid], skip_special_tokens=False)}
            for tid in weighted_ce_ids
        ],
        key=lambda r: r["id"],
    )

    # Sample chat-template fingerprint
    sample_msgs = [
        {"role": "system", "content": "you are a coder."},
        {"role": "user", "content": "translate `def f(): return 1` to Rust."},
        {
            "role": "assistant",
            "content": "well_select(TRANSLATED)\n```rust\nfn f() -> i64 { 1 }\n```",
        },
    ]
    try:
        chat_text = tok.apply_chat_template(
            sample_msgs, tokenize=False, add_generation_prompt=False
        )
    except Exception as e:
        chat_text = f"<error: {e}>"

    payload = {
        "schema_version": "v5_tokenizer_audit_v3",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_model": BASE_MODEL,
        "tokenizer_special": special,
        "chat_special_token_ids": chat_special,
        "trailing_paren_variants": sorted(TRAILING_PAREN_VARIANTS),
        "selector_audit": selector_audit,
        "prefix_audit": prefix_audit,
        "weighted_ce_token_ids": sorted(weighted_ce_ids),
        "weighted_ce_table": weighted_ce_table,
        "chat_template_sample": chat_text[:1500],
        "paren_variant_only_targets": paren_variant_only,
        "verdict": "PASS" if not failures else "FAIL",
        "failures": failures,
        "kernel_template_hint": {
            "config_keys": [
                "selector_token_weight",
                "selector_tokens",
                "selector_prefix_tokens",
            ],
            "load_pattern": (
                "At kernel boot: read this audit JSON, take weighted_ce_token_ids "
                "as the upweight set; in compute_loss, multiply per-token CE by "
                "config['selector_token_weight'] (default 7.0) for any LABEL id "
                "in this set, else 1.0. Mask out -100 labels first; do not weight "
                "the prompt tokens."
            ),
        },
        "notes": (
            "Set-diff payload extraction: well_select(SEL) ids minus one occurrence "
            "each of well_select() ids gives the selector-specific BPE span. "
            "Includes BPE merges like '(ID', '(AL' that are load-bearing for "
            "wrong_well loss. Multi-token chains expected and required for B-1. "
            "Stability is checked modulo the trailing-paren equivalence class "
            "{8: ')', 340: ')\\n'}; both ids end up in the upweight union so the "
            "kernel handles whichever variant training labels carry. Selectors "
            "listed in `paren_variant_only_targets` differ across contexts only "
            "by which trailing-paren BPE merge fires; this is benign."
        ),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"[v5-tok] base_model={BASE_MODEL}")
    print(
        f"[v5-tok] vocab_size={special['vocab_size']} "
        f"pad={special['pad_token_id']} eos={special['eos_token_id']}"
    )
    for sel, info in selector_audit.items():
        chain = info["canonical_diff_ids"]
        pieces = info["canonical_diff_pieces"]
        s_strict = info["stable_across_contexts"]
        s_modulo = info["stable_modulo_trailing_paren"]
        flag = "PASS" if s_modulo else "FAIL"
        kind = "strict" if s_strict else ("paren-variant" if s_modulo else "DIVERGENT")
        print(f"[v5-tok] {sel:>15s}: ids={chain} pieces={pieces} {flag} ({kind})")
    for pref, info in prefix_audit.items():
        chain = info["canonical_diff_ids"]
        pieces = info["canonical_diff_pieces"]
        s_strict = info["stable_across_contexts"]
        s_modulo = info["stable_modulo_trailing_paren"]
        flag = "PASS" if s_modulo else "FAIL"
        kind = "strict" if s_strict else ("paren-variant" if s_modulo else "DIVERGENT")
        print(f"[v5-tok] {pref:>15s}: ids={chain} pieces={pieces} {flag} ({kind})")
    print(f"[v5-tok] weighted_ce_id_count={len(weighted_ce_ids)}")
    print(f"[v5-tok] verdict={'PASS' if not failures else 'FAIL'}")
    if failures:
        for f in failures:
            print(f"[v5-tok] FAIL: {f}")
        return 2
    print(f"[v5-tok] wrote {OUT_PATH.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
