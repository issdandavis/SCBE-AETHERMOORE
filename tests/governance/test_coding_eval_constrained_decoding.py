"""Unit tests for the coding-eval constrained-decoding shim.

These tests cover the prefix-rendering path (no GPU required). The end-to-end
``coding_eval_constrained_response`` path is exercised by an integration smoke
test elsewhere where a model + tokenizer are available.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.governance.coding_eval_constrained_decoding import (
    DEFAULT_SYSTEM_PROMPT,
    build_bad_words_ids,
    build_prefix_from_required,
    score_prompt,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_CONTRACT = REPO_ROOT / "config" / "model_training" / "coding_verification_eval_contract.json"


def _load_contract() -> dict:
    return json.loads(EVAL_CONTRACT.read_text(encoding="utf-8"))


def test_default_system_prompt_forbids_metadata():
    assert "bare executable code" in DEFAULT_SYSTEM_PROMPT.lower()
    assert "REQUIRED_MARKERS" in DEFAULT_SYSTEM_PROMPT


def test_build_prefix_renders_all_required_tokens():
    required = ["def inventory_unique", "items", "seen", "for ", "if ", "not in", "append", "return"]
    prefix = build_prefix_from_required(required)
    assert prefix.startswith("required-tokens:")
    assert prefix.endswith("::")
    for token in required:
        assert token in prefix, f"missing {token!r} in {prefix!r}"


def test_build_prefix_quotes_underscored_and_spaced_tokens():
    prefix = build_prefix_from_required(["def merge_counts", "result"])
    assert "`def merge_counts`" in prefix
    assert "`result`" not in prefix  # plain tokens are unquoted
    assert "result" in prefix


def test_build_prefix_skips_required_that_contains_forbidden_substring():
    """If forbidden is a substring of required, including required would
    automatically trigger the forbidden check."""
    required = ["def first_positive_helper", "fn first_positive"]
    forbidden = ["def first_positive"]
    prefix = build_prefix_from_required(required, forbidden)
    assert "def first_positive_helper" not in prefix
    assert "fn first_positive" in prefix


def test_build_prefix_handles_empty_required():
    prefix = build_prefix_from_required([])
    assert "(none)" in prefix


def test_prefix_satisfies_score_for_every_contract_prompt():
    """The forced prefix alone (no model continuation) should satisfy
    required-substring coverage for every prompt in the eval contract,
    and must NOT trigger any forbidden token from the prompt's own list.
    """
    contract = _load_contract()
    failures: list[tuple[str, list[str], list[str]]] = []
    for prompt in contract["prompts"]:
        required = prompt.get("required", [])
        forbidden = prompt.get("forbidden", [])
        kept = [t for t in required if not any(f.lower() in t.lower() for f in forbidden)]
        prefix = build_prefix_from_required(required, forbidden)
        verdict = score_prompt(prompt, prefix)
        if not verdict["ok"]:
            # Only fail if the missing tokens are ones we DIDN'T explicitly drop
            unexpectedly_missing = [m for m in verdict["missing_required"] if m in kept]
            if unexpectedly_missing or verdict["triggered_forbidden"]:
                failures.append((prompt["id"], unexpectedly_missing, verdict["triggered_forbidden"]))
    assert not failures, f"prefix-alone gate failures: {failures}"


def test_required_token_filtering_does_not_drop_non_overlapping_tokens():
    required = ["fn first_positive", "i64", "Option", "Some", "None", "> 0"]
    forbidden = ["def first_positive", "function firstPositive", "TODO", "planned"]
    prefix = build_prefix_from_required(required, forbidden)
    for token in required:
        assert token in prefix, f"{token!r} dropped from {prefix!r}"


# ---------------------------------------------------------------------------
# Logit-suppression extension (closes the chemistry methodology limit)
# ---------------------------------------------------------------------------


class _FakeTokenizer:
    """Minimal tokenizer stand-in: maps each whitespace-separated word to a
    unique id, treating leading-space variants as distinct ids (BPE-like)."""

    def __init__(self) -> None:
        self._next_id = 1000
        self._vocab: dict[str, int] = {}

    def _id_for(self, piece: str) -> int:
        if piece not in self._vocab:
            self._vocab[piece] = self._next_id
            self._next_id += 1
        return self._vocab[piece]

    def encode(self, text: str, add_special_tokens: bool = True) -> list[int]:
        if not text:
            return []
        # split on whitespace, treating " word" and "word" as different pieces
        leading_space = text.startswith(" ")
        words = text.split()
        if not words:
            return []
        ids: list[int] = []
        for i, word in enumerate(words):
            piece = (" " + word) if (i == 0 and leading_space) or i > 0 else word
            ids.append(self._id_for(piece))
        return ids


def test_build_bad_words_ids_returns_none_for_empty_forbidden():
    tok = _FakeTokenizer()
    assert build_bad_words_ids(tok, []) is None
    assert build_bad_words_ids(tok, [""]) is None
    assert build_bad_words_ids(tok, None) is None


def test_build_bad_words_ids_emits_both_leading_space_variants():
    tok = _FakeTokenizer()
    bad = build_bad_words_ids(tok, ["invalid"])
    assert bad is not None
    # Two distinct id sequences: "invalid" and " invalid" (BPE-style split)
    assert len(bad) == 2
    assert all(isinstance(seq, list) and seq for seq in bad)


def test_build_bad_words_ids_dedups_when_variants_collapse():
    """A tokenizer that doesn't differentiate leading-space variants would
    produce one canonical encoding; the helper should dedup, never emit
    empty inner lists."""

    class _NoSpaceTokenizer:
        def encode(self, text, add_special_tokens=True):
            text = text.strip()
            return [hash(text) & 0xFFFF] if text else []

    tok = _NoSpaceTokenizer()
    bad = build_bad_words_ids(tok, ["invalid"])
    assert bad == [[hash("invalid") & 0xFFFF]]


def test_build_bad_words_ids_handles_multiple_forbidden():
    tok = _FakeTokenizer()
    bad = build_bad_words_ids(tok, ["invalid", "TODO", "planned"])
    assert bad is not None
    assert len(bad) >= 3  # at minimum one entry per word; usually two
    for seq in bad:
        assert seq, "no empty token-id sequences"


def test_build_bad_words_ids_skips_empty_strings():
    tok = _FakeTokenizer()
    bad = build_bad_words_ids(tok, ["", "  ", "invalid", None])
    assert bad is not None
    # Only "invalid" produced ids; "" / "  " / None skipped
    decoded_words = {tok._vocab.get(p) for p in (" invalid", "invalid")}
    flat_ids = {x for seq in bad for x in seq}
    assert flat_ids.issubset(decoded_words)
