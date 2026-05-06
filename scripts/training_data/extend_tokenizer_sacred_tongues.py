#!/usr/bin/env python3
"""Extend a HF tokenizer with atomic vocabulary entries for the six
Sacred Tongues (KO, AV, RU, CA, UM, DR).

Closes Option A from `project_tokenizer_audit_coding_contract_2026_05_06`:
the Sacred Tongue tokens (`kor'aelin`, `umbroth`, etc.) fragment to 3-4
BPE pieces in Qwen2.5-Coder-7B-Instruct, which spreads SFT pressure
across multiple step positions and makes `bad_words_ids` suppression
leaky. Adding them as atomic vocabulary entries collapses each name to
1 piece — the model still has to LEARN the embedding via a subsequent
training round, but the SFT pressure now lands on a single position and
suppression catches the literal in one shot.

What this script does NOT do:

- Train the model. Adding tokens to the tokenizer is independent of
  training; the model's embedding matrix must be resized (via
  ``model.resize_token_embeddings``) at the start of the next SFT round.
- Re-tokenize existing training data. Existing JSONL shards still
  reference the old BPE pieces; the next training run will tokenize
  fresh with the extended tokenizer.
- Modify the original tokenizer. The extended tokenizer is saved to
  ``--output-dir`` (default ``artifacts/extended_tokenizer/``) so the
  base model unchanged.

Usage::

    python scripts/training_data/extend_tokenizer_sacred_tongues.py \\
        --base-model Qwen/Qwen2.5-Coder-7B-Instruct \\
        --output-dir artifacts/extended_tokenizer/qwen25-coder-7b-sacred-tongues
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


# Six Sacred Tongues, both casings. Per memory `feedback_spell_out_tongue_names`,
# the canonical project usage is the full name (Kor'aelin, Avali, Runethic,
# Cassisivadan, Umbroth, Draumric), not the abbreviation. Lowercase forms
# appear in the contracts; capitalized forms appear in narrative/markdown.
SACRED_TONGUE_NAMES: list[str] = [
    "kor'aelin",
    "Kor'aelin",
    "avali",
    "Avali",
    "runethic",
    "Runethic",
    "cassisivadan",
    "Cassisivadan",
    "umbroth",
    "Umbroth",
    "draumric",
    "Draumric",
]


def measure_pieces(tokenizer, token: str) -> int:
    """Return the minimum piece count across leading-space and no-space
    forms (mirroring the audit's tokenization model)."""

    a = len(tokenizer.encode(token, add_special_tokens=False))
    b = len(tokenizer.encode(" " + token, add_special_tokens=False))
    return min(a, b)


def extend_tokenizer(
    tokenizer,
    new_tokens: list[str],
) -> dict[str, Any]:
    """Mutate the tokenizer in place by adding ``new_tokens``. Return a
    structured before/after report.

    The HF ``add_tokens`` method handles the leading-space form internally
    via the tokenizer's normalizer/pre-tokenizer; for the BPE family
    (Qwen2.5) the added token matches both `'foo'` and `' foo'` surfaces.
    """

    before = {t: measure_pieces(tokenizer, t) for t in new_tokens}
    n_before = len(tokenizer)

    n_added = tokenizer.add_tokens(new_tokens)

    n_after = len(tokenizer)
    after = {t: measure_pieces(tokenizer, t) for t in new_tokens}

    return {
        "tokens_requested": new_tokens,
        "n_requested": len(new_tokens),
        "n_added_to_vocab": n_added,
        "vocab_size_before": n_before,
        "vocab_size_after": n_after,
        "pieces_before": before,
        "pieces_after": after,
        "now_atomic": [t for t in new_tokens if after[t] == 1],
        "still_fragmented": [t for t in new_tokens if after[t] > 1],
    }


def save_extended(tokenizer, output_dir: Path, report: dict[str, Any]) -> None:
    """Save the extended tokenizer + the extension report to disk."""

    output_dir.mkdir(parents=True, exist_ok=True)
    tokenizer.save_pretrained(output_dir)
    (output_dir / "sacred_tongues_extension_report.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-model",
        default="Qwen/Qwen2.5-Coder-7B-Instruct",
        help="HF model id whose tokenizer will be extended",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/extended_tokenizer/qwen25-coder-7b-sacred-tongues"),
    )
    parser.add_argument(
        "--also-add",
        nargs="*",
        default=[],
        help="extra atomic tokens to add beyond the Sacred Tongue names",
    )
    args = parser.parse_args()

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)

    new_tokens = list(SACRED_TONGUE_NAMES) + list(args.also_add)
    report = extend_tokenizer(tokenizer, new_tokens)
    save_extended(tokenizer, args.output_dir, report)

    print(f"base model        : {args.base_model}")
    print(f"output dir        : {args.output_dir}")
    print(f"vocab before/after: {report['vocab_size_before']} -> {report['vocab_size_after']}")
    print(f"requested         : {report['n_requested']}")
    print(f"added to vocab    : {report['n_added_to_vocab']}")
    print(f"now atomic        : {len(report['now_atomic'])}/{report['n_requested']}")
    if report["still_fragmented"]:
        print(f"WARNING: still fragmented after add_tokens: {report['still_fragmented']}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
