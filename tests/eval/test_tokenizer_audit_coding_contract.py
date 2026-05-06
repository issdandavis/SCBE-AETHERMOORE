"""Tests for the coding-contract tokenizer audit.

Uses a stub tokenizer so the suite doesn't need HF network access.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.eval.tokenizer_audit_coding_contract import (
    _classify,
    _tokenize_dual,
    audit_contract,
    render_markdown_report,
)


class _StubTokenizer:
    """Minimal stand-in for AutoTokenizer for unit tests.

    Splits on word boundaries and uses a small known atomic vocabulary
    so we can predict piece counts deterministically. Mirrors the
    AutoTokenizer surface methods the audit uses: ``encode`` and
    ``convert_ids_to_tokens``.
    """

    name_or_path = "stub/test-tokenizer"

    # tokens that exist in the vocab as single pieces (no leading space form)
    _atomic = {"items", "seen", "return", "TODO", "RDKit", "molecule"}
    # tokens that have a leading-space-only single piece
    _atomic_space = {"items", "return", "TODO"}

    def encode(self, text: str, add_special_tokens: bool = False):
        leading_space = text.startswith(" ")
        body = text.lstrip(" ")
        if leading_space and body in self._atomic_space:
            return [hash((" ", body)) % 50000]
        if not leading_space and body in self._atomic:
            return [hash(body) % 50000]
        # fallback: split on non-word boundaries; assign synthetic ids
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
        if leading_space and pieces:
            pieces[0] = "_" + pieces[0]
        return [(hash(p) % 50000) + 1 for p in pieces]

    def convert_ids_to_tokens(self, ids):
        # Provide synthetic but stable token strings so the audit can
        # surface them in reports.
        return [f"id{i}" for i in ids]


@pytest.fixture
def tok():
    return _StubTokenizer()


def test_tokenize_dual_finds_atomic_in_either_form(tok):
    audit = _tokenize_dual(tok, "items")
    assert audit["atomic"] is True
    assert audit["min_pieces"] == 1
    assert audit["literal"] == "items"


def test_tokenize_dual_flags_fragmented(tok):
    audit = _tokenize_dual(tok, "def inventory_unique")
    assert audit["atomic"] is False
    assert audit["min_pieces"] >= 2


def test_classify_buckets():
    assert _classify({"min_pieces": 1}) == "atomic"
    assert _classify({"min_pieces": 2}) == "bigram"
    assert _classify({"min_pieces": 3}) == "fragmented"
    assert _classify({"min_pieces": 7}) == "fragmented"


def test_audit_contract_writes_summary(tmp_path: Path, tok):
    contract = {
        "contract_id": "test_contract",
        "prompts": [
            {
                "id": "p1",
                "required": ["items", "def inventory_unique"],
                "forbidden": ["TODO", "def count_vowels"],
            },
            {
                "id": "p2",
                "required": ["items", "return"],
                "forbidden": ["TODO"],
            },
        ],
    }
    cpath = tmp_path / "c.json"
    cpath.write_text(json.dumps(contract))
    audit = audit_contract(cpath, tok)

    # required summary: items appears in 2 prompts, dedup to unique-3
    assert audit["required"]["summary"]["n_unique"] == 3
    # 'items' and 'return' are atomic; 'def inventory_unique' is fragmented
    assert audit["required"]["summary"]["n_atomic"] >= 2
    # forbidden: TODO appears in both prompts but unique=2
    assert audit["forbidden"]["summary"]["n_unique"] == 2

    # in_prompts cross-reference holds
    assert audit["required"]["details"]["items"]["in_prompts"] == ["p1", "p2"]
    assert audit["forbidden"]["details"]["TODO"]["in_prompts"] == ["p1", "p2"]


def test_render_markdown_report_includes_fragmented_section(tmp_path: Path, tok):
    # kor'aelin splits on the apostrophe -> ["kor", "'", "aelin"] = 3 pieces
    contract = {
        "contract_id": "test_contract",
        "prompts": [
            {
                "id": "p1",
                "required": ["kor'aelin"],
                "forbidden": ["TODO"],
            }
        ],
    }
    cpath = tmp_path / "c.json"
    cpath.write_text(json.dumps(contract))
    audit = audit_contract(cpath, tok)
    md = render_markdown_report(audit)
    assert "Tokenizer Audit" in md
    assert "test_contract" in md
    # Fragmented section should surface kor'aelin
    assert "kor'aelin" in md
    # Report includes the implications block when fragmented tokens exist
    assert "fragmented" in md.lower()
