"""Bijective Tamper Signal — encoding-level tamper detection for L13.

Builds on the bijective compiler substrate (705/705 KO=Python, 335/335 AV=TS):

    parse(decode(encode(src))) ≡ parse(src)   — holds for legitimate code

When code DIVERGES under tokenize-decode, that divergence is a FINGERPRINT
of encoding-level tampering or unicode trickery. This module turns that
fingerprint into a tamper signal in [0, 1] for the L13 risk decision gate.

What this gate catches well:
    * NFD/NFC normalization shifts (combining marks rearranged to hide payload)
    * Zero-width-joiner (ZWJ) and zero-width-space (ZWSP) injections in
      identifiers that the BPE tokenizer normalizes away
    * Subword-boundary tricks where the tokenizer cannot round-trip
    * Outright corrupt bytes that don't parse after tokenize/decode

What this gate does NOT catch (out of scope, needs sibling gates):
    * Homoglyph identifiers (Cyrillic а vs Latin a — both are valid,
      single-codepoint identifiers; AST sees them as different but each
      independently round-trips fine)
    * Logically-equivalent but structurally-different programs
    * Run-time behavior (this is a STATIC encoding-level signal)

Tamper score scale:
    0.00 - 0.10   → kind="none"        — bytes and AST both stable
    0.10 - 0.40   → kind="nfc"         — bytes shift via NFC, AST stable
                                          (recoverable, log-only)
    0.40 - 0.80   → kind="structural"  — AST shifts after decode
                                          (semantic shift, quarantine)
    0.80 - 1.00   → kind="syntax"      — decoded source does not parse
                                          (catastrophic, deny)

Plus a side channel:
    kind="input_invalid" — input source itself does not parse. Not a
    tamper signal per se; route to syntax-error handling.

L13 integration sketch (not wired here to keep the change additive):

    from src.governance.bijective_tamper import evaluate_code
    from src.governance.runtime_gate import Decision

    def l13_with_tamper_signal(src, language, base_decision):
        result = evaluate_code(src, language)
        if result.kind == "syntax":
            return Decision.DENY
        if result.kind == "structural":
            return max(base_decision, Decision.QUARANTINE)
        # nfc / none — pass through, annotate
        return base_decision.with_annotation(result.fingerprint, result.score)

The fingerprint is a SHA-256 of the canonical AST. Two semantically-equal
programs hash the same — useful for replay detection, dedup, whitelisting.
"""

from __future__ import annotations

import ast
import hashlib
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# --------------------------------------------------------------------------- #
#  Public types
# --------------------------------------------------------------------------- #

DivergenceKind = str  # Literal: "none" | "nfc" | "structural" | "syntax" | "input_invalid"


@dataclass
class TamperResult:
    """Outcome of a single bijective-tamper evaluation."""

    score: float  # 0.0 = clean, 1.0 = catastrophic
    kind: DivergenceKind
    semantic_fingerprint: Optional[str]  # SHA-256 of canonical AST, hex
    bytes_diverge: bool
    nfc_recovers_bytes: bool
    ast_diverge: bool
    decoded_parses: bool
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "kind": self.kind,
            "semantic_fingerprint": self.semantic_fingerprint,
            "bytes_diverge": self.bytes_diverge,
            "nfc_recovers_bytes": self.nfc_recovers_bytes,
            "ast_diverge": self.ast_diverge,
            "decoded_parses": self.decoded_parses,
            "detail": self.detail,
        }


# --------------------------------------------------------------------------- #
#  Per-language AST canonicalization
# --------------------------------------------------------------------------- #


def _ast_canonical_python(src: str) -> str:
    """Canonical AST dump for Python. Raises SyntaxError on bad input."""
    tree = ast.parse(src)
    return ast.dump(tree, annotate_fields=True, include_attributes=False, indent=2)


_AST_CANONICAL = {
    "python": _ast_canonical_python,
}


# --------------------------------------------------------------------------- #
#  Tokenizer access (lazy / injectable)
# --------------------------------------------------------------------------- #

_DEFAULT_TOKENIZER_DIR = (
    Path(__file__).resolve().parents[2] / "artifacts" / "extended_tokenizer" / "qwen25-coder-7b-sacred-tongues"
)
_TOKENIZER_CACHE: dict[str, object] = {}


def _load_tokenizer(tokenizer_dir: Optional[Path] = None):
    key = str(tokenizer_dir or _DEFAULT_TOKENIZER_DIR)
    if key in _TOKENIZER_CACHE:
        return _TOKENIZER_CACHE[key]
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(key, use_fast=True)
    _TOKENIZER_CACHE[key] = tok
    return tok


def _decode_through_tokenizer(src: str, tokenizer) -> str:
    encoded = tokenizer.encode(src, add_special_tokens=False)
    ids = encoded.ids if hasattr(encoded, "ids") else encoded
    try:
        return tokenizer.decode(ids, skip_special_tokens=False)
    except TypeError:
        return tokenizer.decode(ids)


# --------------------------------------------------------------------------- #
#  Public evaluate_code
# --------------------------------------------------------------------------- #


def evaluate_code(
    src: str,
    language: str = "python",
    tokenizer=None,
    tokenizer_dir: Optional[Path] = None,
) -> TamperResult:
    """Compute the bijective tamper signal for a source string.

    Args:
        src: Source code to evaluate.
        language: Currently only "python" is implemented. Future: "typescript",
                  "rust", etc. — see docs/specs/COMPILER_GATES_BY_LANGUAGE_TODO.md.
        tokenizer: Optional pre-loaded HF tokenizer. If None, the canonical
                   Qwen+atomic-tongue tokenizer is loaded (cached).
        tokenizer_dir: Optional override for the tokenizer artifacts path.

    Returns:
        TamperResult with score, divergence kind, and semantic fingerprint.
    """
    if language not in _AST_CANONICAL:
        return TamperResult(
            score=1.0,
            kind="input_invalid",
            semantic_fingerprint=None,
            bytes_diverge=False,
            nfc_recovers_bytes=False,
            ast_diverge=False,
            decoded_parses=False,
            detail={"error": f"unsupported language: {language}"},
        )

    canonicalize = _AST_CANONICAL[language]

    # Step 1: input must parse
    try:
        src_canonical = canonicalize(src)
    except SyntaxError as e:
        return TamperResult(
            score=1.0,
            kind="input_invalid",
            semantic_fingerprint=None,
            bytes_diverge=False,
            nfc_recovers_bytes=False,
            ast_diverge=False,
            decoded_parses=False,
            detail={"error": f"input does not parse: {e}"},
        )

    src_fingerprint = hashlib.sha256(src_canonical.encode("utf-8")).hexdigest()

    # Step 2: tokenize-decode round trip
    if tokenizer is None:
        tokenizer = _load_tokenizer(tokenizer_dir)
    decoded = _decode_through_tokenizer(src, tokenizer)

    bytes_diverge = decoded != src
    nfc_recovers = bytes_diverge and unicodedata.normalize("NFC", src) == decoded

    # Step 3: does decoded source parse?
    try:
        decoded_canonical = canonicalize(decoded)
    except SyntaxError as e:
        return TamperResult(
            score=1.0,
            kind="syntax",
            semantic_fingerprint=src_fingerprint,
            bytes_diverge=bytes_diverge,
            nfc_recovers_bytes=nfc_recovers,
            ast_diverge=True,
            decoded_parses=False,
            detail={"error": f"decoded source does not parse: {e}"},
        )

    ast_diverge = src_canonical != decoded_canonical

    # Step 4: classify.
    # Decision order matters: NFC-recoverable cases are documented expected
    # divergence and classify as "nfc" even when the AST shifts (string literal
    # values are codepoint-sensitive, so NFD↔NFC literals change AST values).
    if not bytes_diverge:
        return TamperResult(
            score=0.0,
            kind="none",
            semantic_fingerprint=src_fingerprint,
            bytes_diverge=False,
            nfc_recovers_bytes=False,
            ast_diverge=False,
            decoded_parses=True,
        )

    if nfc_recovers:
        # Documented expected normalization. Score reflects whether AST also
        # shifted (slightly higher when literals were affected).
        score = 0.25 if ast_diverge else 0.20
        note = (
            "bytes diverged via NFC normalization; literal contents shifted (AST changed)"
            if ast_diverge
            else "bytes diverged via NFC normalization; AST stable"
        )
        return TamperResult(
            score=score,
            kind="nfc",
            semantic_fingerprint=src_fingerprint,
            bytes_diverge=True,
            nfc_recovers_bytes=True,
            ast_diverge=ast_diverge,
            decoded_parses=True,
            detail={"note": note},
        )

    if not ast_diverge:
        # Bytes diverge via something other than NFC, but AST stable.
        return TamperResult(
            score=0.30,
            kind="nfc",
            semantic_fingerprint=src_fingerprint,
            bytes_diverge=True,
            nfc_recovers_bytes=False,
            ast_diverge=False,
            decoded_parses=True,
            detail={"note": "bytes diverged via non-NFC normalization; AST stable"},
        )

    # Bytes AND AST diverge AND NFC does not recover — semantic-level shift.
    return TamperResult(
        score=0.60,
        kind="structural",
        semantic_fingerprint=src_fingerprint,
        bytes_diverge=True,
        nfc_recovers_bytes=False,
        ast_diverge=True,
        decoded_parses=True,
        detail={
            "note": "AST canonical changed after tokenize-decode (not NFC-recoverable)",
            "src_fingerprint": src_fingerprint,
            "decoded_fingerprint": hashlib.sha256(decoded_canonical.encode("utf-8")).hexdigest(),
        },
    )


# --------------------------------------------------------------------------- #
#  Convenience: L13 mapping
# --------------------------------------------------------------------------- #

L13_MAPPING_RECOMMENDATION = {
    "none": "ALLOW",
    "nfc": "ALLOW",  # log only; could be QUARANTINE in stricter modes
    "structural": "QUARANTINE",
    "syntax": "DENY",
    "input_invalid": "DENY",  # cannot reason about syntactically-invalid input
}


def recommended_l13_action(result: TamperResult) -> str:
    """Map a TamperResult to the recommended L13 action string.

    Conservative default; production wiring should compose with other signals
    (harmonic wall score, swarm consensus, etc.).
    """
    return L13_MAPPING_RECOMMENDATION.get(result.kind, "QUARANTINE")
