"""Tests for the bijective tamper signal (L13 input)."""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.governance.bijective_tamper import (  # noqa: E402
    L13_MAPPING_RECOMMENDATION,
    evaluate_code,
    recommended_l13_action,
)

# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def tokenizer():
    from transformers import AutoTokenizer

    path = REPO_ROOT / "artifacts" / "extended_tokenizer" / "qwen25-coder-7b-sacred-tongues"
    return AutoTokenizer.from_pretrained(str(path), use_fast=True)


# --------------------------------------------------------------------------- #
#  Clean cases — score 0.0, ALLOW
# --------------------------------------------------------------------------- #


def test_clean_ascii_python(tokenizer):
    src = "def f(x):\n    return x + 1\n"
    r = evaluate_code(src, "python", tokenizer=tokenizer)
    assert r.kind == "none"
    assert r.score == 0.0
    assert r.semantic_fingerprint is not None
    assert recommended_l13_action(r) == "ALLOW"


def test_clean_with_unicode_string_literal(tokenizer):
    # Emoji in a string literal — NFC stable, no tampering.
    src = 'msg = "hello 🌍 world"\nprint(msg)\n'
    r = evaluate_code(src, "python", tokenizer=tokenizer)
    assert r.kind == "none"
    assert r.score == 0.0
    assert recommended_l13_action(r) == "ALLOW"


def test_clean_function_with_decorators(tokenizer):
    src = "@staticmethod\n" "def helper(x, y, *, key=None):\n" "    return (x + y, key)\n"
    r = evaluate_code(src, "python", tokenizer=tokenizer)
    assert r.kind == "none"


# --------------------------------------------------------------------------- #
#  NFD-shift case — score ~0.2, ALLOW with annotation
# --------------------------------------------------------------------------- #


def test_nfd_combining_marks_recover_via_nfc(tokenizer):
    """NFD literal in source becomes NFC after tokenize-decode.

    bytes_diverge=True (NFD bytes != NFC bytes after Qwen normalization)
    nfc_recovers_bytes=True (this is the canonical NFC normalization case)
    ast_diverge=True (Python string compare is codepoint-by-codepoint, so
        Constant('a\\u0301') != Constant('\\u00e1'))

    Despite ast_diverge=True, kind="nfc" because nfc_recovers_bytes wins —
    this is documented expected normalization, not adversarial tampering.
    """
    nfd_text = unicodedata.normalize("NFD", 'combining = "áb́ć"')
    src = nfd_text + "\n"
    assert src != unicodedata.normalize("NFC", src), "fixture must actually be NFD"
    r = evaluate_code(src, "python", tokenizer=tokenizer)
    assert r.kind == "nfc", f"expected nfc, got {r.kind} (detail={r.detail})"
    assert 0.10 < r.score < 0.40
    assert r.bytes_diverge is True
    assert r.nfc_recovers_bytes is True
    # AST diverge is EXPECTED here because string literal value changes under NFC
    assert r.ast_diverge is True
    assert recommended_l13_action(r) == "ALLOW"


# --------------------------------------------------------------------------- #
#  Catastrophic case — input does not parse → DENY
# --------------------------------------------------------------------------- #


def test_input_invalid_python_returns_input_invalid(tokenizer):
    src = "def f(:\n    return\n"  # syntax error
    r = evaluate_code(src, "python", tokenizer=tokenizer)
    assert r.kind == "input_invalid"
    assert r.score == 1.0
    assert recommended_l13_action(r) == "DENY"


# --------------------------------------------------------------------------- #
#  Unsupported language → input_invalid
# --------------------------------------------------------------------------- #


def test_unsupported_language_returns_input_invalid(tokenizer):
    r = evaluate_code('fn main() { println!("hi"); }', "rust", tokenizer=tokenizer)
    assert r.kind == "input_invalid"
    assert r.score == 1.0


# --------------------------------------------------------------------------- #
#  Semantic fingerprint stability
# --------------------------------------------------------------------------- #


def test_semantic_fingerprint_equal_for_equivalent_sources(tokenizer):
    """Two byte-different but AST-equivalent sources should hash the same."""
    src_a = "def f(x):\n    return x+1\n"
    src_b = "def f(x):\n    return x + 1\n"  # extra spaces, same AST
    r_a = evaluate_code(src_a, "python", tokenizer=tokenizer)
    r_b = evaluate_code(src_b, "python", tokenizer=tokenizer)
    assert r_a.semantic_fingerprint == r_b.semantic_fingerprint


def test_semantic_fingerprint_differs_for_different_programs(tokenizer):
    src_a = "def f(x):\n    return x + 1\n"
    src_b = "def f(x):\n    return x * 1\n"
    r_a = evaluate_code(src_a, "python", tokenizer=tokenizer)
    r_b = evaluate_code(src_b, "python", tokenizer=tokenizer)
    assert r_a.semantic_fingerprint != r_b.semantic_fingerprint


# --------------------------------------------------------------------------- #
#  L13 mapping coverage
# --------------------------------------------------------------------------- #


def test_l13_mapping_covers_all_kinds():
    expected = {"none", "nfc", "structural", "syntax", "input_invalid"}
    assert set(L13_MAPPING_RECOMMENDATION.keys()) == expected


def test_l13_mapping_actions_are_valid():
    valid = {"ALLOW", "QUARANTINE", "DENY", "REROUTE"}
    for action in L13_MAPPING_RECOMMENDATION.values():
        assert action in valid


# --------------------------------------------------------------------------- #
#  TamperResult.to_dict serialization
# --------------------------------------------------------------------------- #


def test_to_dict_is_json_serializable(tokenizer):
    import json

    r = evaluate_code("x = 1\n", "python", tokenizer=tokenizer)
    serialized = json.dumps(r.to_dict())
    restored = json.loads(serialized)
    assert restored["kind"] == "none"
    assert restored["score"] == 0.0
