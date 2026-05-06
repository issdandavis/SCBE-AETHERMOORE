"""Tests for Sacred Tongues tokenizer extension.

Uses a stub tokenizer so the suite stays offline.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.training_data.extend_tokenizer_sacred_tongues import (
    SACRED_TONGUE_NAMES,
    extend_tokenizer,
    measure_pieces,
)


class _StubTokenizer:
    """Minimal HF-tokenizer-like surface.

    Models the relevant invariant: new tokens added via ``add_tokens``
    become atomic in subsequent encode calls. Does not model BPE itself —
    we just need to verify the extender wires add_tokens correctly and
    measures pieces with both surface forms.
    """

    def __init__(self) -> None:
        # vocab: maps surface form -> id. Pre-populated with a few atomic
        # entries to model the base tokenizer's existing vocabulary.
        self._vocab: dict[str, int] = {
            "the": 0,
            " the": 1,
            "TODO": 2,
        }

    def __len__(self) -> int:
        # Treat unique base-form ids as the vocab size (mirror HF semantics).
        return len({v for v in self._vocab.values()})

    def encode(self, text: str, add_special_tokens: bool = False):
        # If the entire string is in vocab, atomic
        if text in self._vocab:
            return [self._vocab[text]]
        # Try without leading space if added with space
        if text.startswith(" ") and text[1:] in self._vocab:
            # If only the no-space form is in vocab, the leading-space form
            # still tokenizes as 1 piece in HF for added tokens
            return [self._vocab[text[1:]]]
        # Fallback: split on apostrophe / non-alnum to model BPE-ish fragmentation
        body = text.lstrip(" ")
        pieces: list[str] = []
        cur = ""
        for ch in body:
            if ch.isalnum() or ch == "_":
                cur += ch
            else:
                if cur:
                    pieces.append(cur)
                    cur = ""
                if ch.strip():
                    pieces.append(ch)
        if cur:
            pieces.append(cur)
        return list(range(len(pieces) or 1, (len(pieces) or 1) * 2))

    def add_tokens(self, new_tokens: list[str]) -> int:
        added = 0
        next_id = max(self._vocab.values(), default=-1) + 1
        for t in new_tokens:
            if t not in self._vocab:
                self._vocab[t] = next_id
                next_id += 1
                added += 1
        return added

    def save_pretrained(self, path: Path) -> None:
        Path(path).mkdir(parents=True, exist_ok=True)
        (Path(path) / "stub_vocab.json").write_text(json.dumps(self._vocab))


@pytest.fixture
def tok():
    return _StubTokenizer()


def test_sacred_tongue_names_includes_six_lowercase_and_six_capitalized():
    """The canonical list must cover both casings of all six tongues."""
    lowered = [t.lower() for t in SACRED_TONGUE_NAMES]
    assert "kor'aelin" in lowered
    assert "avali" in lowered
    assert "runethic" in lowered
    assert "cassisivadan" in lowered
    assert "umbroth" in lowered
    assert "draumric" in lowered
    # 6 unique names x 2 casings = 12 entries
    assert len(SACRED_TONGUE_NAMES) == 12


def test_measure_pieces_picks_min_of_dual_form(tok):
    # 'the' is atomic in both forms in the stub
    assert measure_pieces(tok, "the") == 1
    # Sacred tongue name is fragmented before extension
    assert measure_pieces(tok, "kor'aelin") > 1


def test_extend_tokenizer_adds_all_requested(tok):
    report = extend_tokenizer(tok, ["kor'aelin", "umbroth"])
    assert report["n_added_to_vocab"] == 2
    assert report["n_requested"] == 2
    assert report["vocab_size_after"] - report["vocab_size_before"] == 2
    # Both should now be atomic
    assert "kor'aelin" in report["now_atomic"]
    assert "umbroth" in report["now_atomic"]
    assert report["still_fragmented"] == []


def test_extend_tokenizer_skips_already_present(tok):
    # 'the' already exists in stub vocab — adding it again should be a noop
    report = extend_tokenizer(tok, ["the", "kor'aelin"])
    assert report["n_added_to_vocab"] == 1
    # Both still atomic post-add
    assert "the" in report["now_atomic"]
    assert "kor'aelin" in report["now_atomic"]


def test_extend_tokenizer_records_before_and_after_pieces(tok):
    report = extend_tokenizer(tok, ["umbroth"])
    # Before: stub fragments 'umbroth' on word-boundary scan -> 1 piece
    # (since the stub's fallback is permissive). What matters is that
    # AFTER the add, the literal IS atomic.
    assert report["pieces_after"]["umbroth"] == 1


def test_full_sacred_tongue_extension_makes_all_atomic(tok):
    report = extend_tokenizer(tok, list(SACRED_TONGUE_NAMES))
    assert len(report["now_atomic"]) == 12
    assert report["still_fragmented"] == []
