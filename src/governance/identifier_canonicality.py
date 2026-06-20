"""Identifier-Canonicality Signal — sibling gate to bijective_tamper.

The bijective tamper signal proves that

    parse(decode(encode(src))) ≡ parse(src)

holds for clean code. But it does NOT catch homoglyph identifier attacks
because each homoglyph codepoint is a single valid Unicode character that
round-trips through the tokenizer perfectly. The AST happens to see them
as DIFFERENT identifier strings (Cyrillic `а` vs Latin `a` are distinct
codepoints), but a human reading the source can't tell them apart.

This module catches what bijective_tamper explicitly leaves on the table:

    1. Mixed-script identifiers (Latin + Cyrillic + Greek in one name) —
       almost always a confusable attack, never legitimate.
    2. Identifiers containing only-confusable codepoints (a Cyrillic-only
       version of an ASCII identifier name).
    3. Invisible characters in identifiers (zero-width joiner, zero-width
       space, soft hyphen, byte-order mark in interior position).
    4. Bidirectional control characters (a known supply-chain attack vector
       — the "Trojan Source" class of bugs).

What this gate does NOT catch (out of scope):
    * Single-script non-Latin identifiers (e.g., a fully Cyrillic legitimate
      identifier). These look weird but are not deceptive.
    * Logically-equivalent semantically-different programs.
    * Run-time behavior.

Known false positive (multilingual codebases):
    The `confusable` kind fires when EVERY codepoint in an identifier is in
    the curated ASCII-confusables table. Legitimate non-Latin words whose
    glyphs all happen to be in that table will also classify as `confusable`
    → QUARANTINE. Verified examples: Greek `ορα` ("vision"), Greek `αρα`
    ("so/therefore"). For English-only codebases this is intended; for
    multilingual codebases, leave the env-var off or allowlist via the
    emitted SHA-256 fingerprint. See docs/specs/IDENTIFIER_CANONICALITY_L13.md
    "Known false positive: multilingual codebases" for the operator contract.

Score scale:
    0.00          → kind="clean"           — no canonicality issues
    0.30 - 0.50   → kind="non_ascii"       — non-ASCII single-script ids
                                              (legitimate but log-worthy)
    0.60 - 0.80   → kind="confusable"      → all-confusable codepoints used
                                              to mimic an ASCII name
    0.85 - 0.95   → kind="mixed_script"    → script-mixing attack
    1.00          → kind="invisible"       → invisible chars or BiDi
                                              controls (catastrophic)
    1.00          → kind="input_invalid"   — input did not parse

L13 mapping (recommendation; production may compose with other signals):
    clean         → ALLOW
    non_ascii     → ALLOW (annotate)
    confusable    → QUARANTINE
    mixed_script  → DENY
    invisible     → DENY
    input_invalid → no-op (handled by sibling gates / not a tamper signal)
"""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# --------------------------------------------------------------------------- #
#  Public types
# --------------------------------------------------------------------------- #

CanonicalityKind = str  # "clean" | "non_ascii" | "confusable" | "mixed_script" | "invisible" | "input_invalid"


@dataclass
class IdentifierFinding:
    """One suspicious identifier from the source."""

    name: str
    kind: CanonicalityKind
    scripts: List[str]
    detail: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "scripts": list(self.scripts),
            "detail": self.detail,
        }


@dataclass
class CanonicalityResult:
    """Outcome of a single identifier-canonicality evaluation."""

    score: float  # 0.0 = clean, 1.0 = catastrophic
    kind: CanonicalityKind
    findings: List[IdentifierFinding] = field(default_factory=list)
    identifier_count: int = 0
    fingerprint: Optional[str] = None  # SHA-256 of sorted identifier set
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "kind": self.kind,
            "findings": [f.to_dict() for f in self.findings],
            "identifier_count": self.identifier_count,
            "fingerprint": self.fingerprint,
            "detail": self.detail,
        }


# --------------------------------------------------------------------------- #
#  Confusable / invisible codepoint tables
#
#  This is a curated, deliberately small table covering the highest-confidence
#  ASCII-confusable attack codepoints. A complete TR39 confusables table has
#  ~7,000 entries; for v1 we focus on what actually shows up in real source-code
#  homoglyph attacks, which is dominated by Cyrillic and a handful of Greek.
# --------------------------------------------------------------------------- #

# Map: confusable codepoint -> ASCII codepoint it mimics
_ASCII_CONFUSABLES: Dict[str, str] = {
    # Cyrillic lowercase that looks like Latin
    "а": "a",  # а
    "е": "e",  # е
    "о": "o",  # о
    "р": "p",  # р
    "с": "c",  # с
    "х": "x",  # х
    "у": "y",  # у
    "і": "i",  # і (Ukrainian)
    "ј": "j",  # ј (Serbian)
    "һ": "h",  # һ
    # Cyrillic uppercase that looks like Latin
    "А": "A",  # А
    "В": "B",  # В
    "С": "C",  # С
    "Е": "E",  # Е
    "Н": "H",  # Н
    "К": "K",  # К
    "М": "M",  # М
    "О": "O",  # О
    "Р": "P",  # Р
    "Т": "T",  # Т
    "Х": "X",  # Х
    # Greek that looks like Latin
    "α": "a",  # α
    "ο": "o",  # ο
    "ρ": "p",  # ρ
    "υ": "u",  # υ
    "ν": "v",  # ν (looks like v in some fonts)
    "Α": "A",  # Α
    "Β": "B",  # Β
    "Ε": "E",  # Ε
    "Η": "H",  # Η
    "Ι": "I",  # Ι
    "Κ": "K",  # Κ
    "Μ": "M",  # Μ
    "Ν": "N",  # Ν
    "Ο": "O",  # Ο
    "Ρ": "P",  # Ρ
    "Τ": "T",  # Τ
    "Χ": "X",  # Χ
    "Υ": "Y",  # Υ
    "Ζ": "Z",  # Ζ
    # Mathematical Alphanumeric Symbols (whole homoglyph alphabet block)
    # We don't enumerate all 1,024; reject ALL identifiers containing any
    # codepoint in U+1D400..U+1D7FF range (handled programmatically below).
}

# Invisible / formatting-control codepoints that should NEVER appear inside
# identifiers (they are valid Python identifier characters per PEP 3131 in
# some cases, which is exactly the supply-chain risk).
_INVISIBLE_CODEPOINTS: frozenset = frozenset(
    chr(cp)
    for cp in (
        0x200B,  # zero-width space
        0x200C,  # zero-width non-joiner
        0x200D,  # zero-width joiner
        0x2060,  # word joiner
        0xFEFF,  # zero-width no-break space (BOM)
        0x00AD,  # soft hyphen
        0x180E,  # Mongolian vowel separator
        0x2061,  # function application
        0x2062,  # invisible times
        0x2063,  # invisible separator
        0x2064,  # invisible plus
    )
)

# BiDi control codepoints — the Trojan Source class. NEVER legitimate inside
# identifiers; very rarely legitimate in source at all.
_BIDI_CODEPOINTS: frozenset = frozenset(
    chr(cp)
    for cp in (
        0x202A,  # LRE
        0x202B,  # RLE
        0x202C,  # PDF
        0x202D,  # LRO
        0x202E,  # RLO
        0x2066,  # LRI
        0x2067,  # RLI
        0x2068,  # FSI
        0x2069,  # PDI
    )
)


def _codepoint_script(ch: str) -> str:
    """Return a coarse script bucket for a single codepoint.

    We don't load the full Unicode Script property; a coarse bucket is
    enough for the mixed-script attack which always combines 2 scripts that
    share visual confusability (Latin + Cyrillic, Latin + Greek).
    """
    cp = ord(ch)
    if 0x0041 <= cp <= 0x007A or cp == 0x005F:  # A-Z, a-z, _ (Latin/ASCII)
        return "Latin"
    if 0x0030 <= cp <= 0x0039:
        return "Digit"
    if 0x00C0 <= cp <= 0x024F:
        return "Latin"  # Latin-1 Supplement / Extended-A/B
    if 0x0370 <= cp <= 0x03FF:
        return "Greek"
    if 0x0400 <= cp <= 0x04FF:
        return "Cyrillic"
    if 0x0500 <= cp <= 0x052F:
        return "Cyrillic"
    if 0x0530 <= cp <= 0x058F:
        return "Armenian"
    if 0x0590 <= cp <= 0x05FF:
        return "Hebrew"
    if 0x0600 <= cp <= 0x06FF:
        return "Arabic"
    if 0x3040 <= cp <= 0x309F:
        return "Hiragana"
    if 0x30A0 <= cp <= 0x30FF:
        return "Katakana"
    if 0x4E00 <= cp <= 0x9FFF:
        return "Han"
    if 0xAC00 <= cp <= 0xD7AF:
        return "Hangul"
    if 0x1D400 <= cp <= 0x1D7FF:
        return "Math"  # Math alphanumerics — almost always confusable abuse
    return "Other"


def _scripts_in(name: str) -> List[str]:
    """Distinct (non-Digit, non-_) script buckets present in the identifier."""
    seen: List[str] = []
    for ch in name:
        if ch == "_":
            continue
        s = _codepoint_script(ch)
        if s == "Digit":
            continue
        if s not in seen:
            seen.append(s)
    return seen


def _has_invisible(name: str) -> Optional[str]:
    """Return the first invisible character found, if any."""
    for ch in name:
        if ch in _INVISIBLE_CODEPOINTS or ch in _BIDI_CODEPOINTS:
            return ch
    return None


def _has_source_text_bidi(src: str) -> Optional[str]:
    """Return the first BiDi control or invisible codepoint found in source text.

    Trojan Source attacks commonly place BiDi controls in comments or string
    literals, not only inside identifiers. Zero-width characters inside
    identifiers can also break tokenization, so an AST-stage check would never
    see them. Catch both classes before parsing so the gate does not depend on
    AST identifier extraction.
    """
    for ch in src:
        if ch in _BIDI_CODEPOINTS or ch in _INVISIBLE_CODEPOINTS:
            return ch
    return None


def _is_all_confusable(name: str) -> bool:
    """True if every non-Latin codepoint in the name is in the ASCII confusable
    table AND the name has at least one such codepoint AND, when we replace
    the confusables with their ASCII mimics, the result is a plain ASCII
    identifier-shaped string.

    This is the classic homoglyph attack: `аpi_key` (with Cyrillic а) that
    looks identical to `api_key` (with Latin a) on screen.
    """
    has_any_confusable = False
    rebuilt = []
    for ch in name:
        if ch in _ASCII_CONFUSABLES:
            has_any_confusable = True
            rebuilt.append(_ASCII_CONFUSABLES[ch])
        elif ord(ch) < 128:
            rebuilt.append(ch)
        else:
            # Non-confusable, non-ASCII codepoint present — not a pure
            # ASCII-mimic attack; fall through to mixed-script handling.
            return False
    if not has_any_confusable:
        return False
    candidate = "".join(rebuilt)
    return candidate.isidentifier()


def _classify_identifier(name: str) -> Optional[IdentifierFinding]:
    """Return a finding if the identifier is suspicious, else None."""
    invisible_ch = _has_invisible(name)
    if invisible_ch is not None:
        return IdentifierFinding(
            name=name,
            kind="invisible",
            scripts=_scripts_in(name),
            detail=(f"contains invisible/BiDi codepoint U+{ord(invisible_ch):04X}"),
        )

    # Math-alphanumeric block check — always treat as catastrophic confusable
    if any(0x1D400 <= ord(ch) <= 0x1D7FF for ch in name):
        return IdentifierFinding(
            name=name,
            kind="mixed_script",
            scripts=_scripts_in(name),
            detail="contains Mathematical Alphanumeric Symbol codepoint",
        )

    scripts = _scripts_in(name)

    # Mixed-script: any combination of >1 distinct non-trivial scripts
    if len(scripts) >= 2:
        return IdentifierFinding(
            name=name,
            kind="mixed_script",
            scripts=scripts,
            detail=f"identifier mixes scripts: {scripts}",
        )

    # All-confusable single non-Latin script that mimics an ASCII identifier
    if _is_all_confusable(name):
        return IdentifierFinding(
            name=name,
            kind="confusable",
            scripts=scripts,
            detail=f"identifier uses only ASCII-confusable codepoints from {scripts}",
        )

    # Single non-Latin script (legitimate but worth annotating)
    if scripts and scripts != ["Latin"]:
        return IdentifierFinding(
            name=name,
            kind="non_ascii",
            scripts=scripts,
            detail=f"non-ASCII single-script identifier ({scripts})",
        )

    return None


# --------------------------------------------------------------------------- #
#  AST identifier extraction
# --------------------------------------------------------------------------- #


def _extract_identifiers_python(src: str) -> List[str]:
    """Return all identifier strings used in the AST.

    Walks every node and collects identifier-bearing fields. Order of first
    appearance is preserved; duplicates are kept (so a repeated bad name
    contributes proportionally to score weighting if we ever choose to).
    """
    tree = ast.parse(src)
    names: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.arg):
            names.append(node.arg)
        elif isinstance(node, ast.Attribute):
            names.append(node.attr)
        elif isinstance(node, ast.alias):
            names.append(node.name)
            if node.asname is not None:
                names.append(node.asname)
        elif isinstance(node, ast.keyword):
            if node.arg is not None:
                names.append(node.arg)
        elif isinstance(node, ast.ExceptHandler):
            if node.name is not None:
                names.append(node.name)
        elif isinstance(node, ast.Global):
            names.extend(node.names)
        elif isinstance(node, ast.Nonlocal):
            names.extend(node.names)
    return names


_LANGUAGE_EXTRACTORS = {
    "python": _extract_identifiers_python,
}


# --------------------------------------------------------------------------- #
#  Public evaluate_code
# --------------------------------------------------------------------------- #

# Score table per kind — used to compute the aggregate score (max severity wins).
_KIND_SCORE: Dict[CanonicalityKind, float] = {
    "clean": 0.0,
    "non_ascii": 0.30,
    "confusable": 0.65,
    "mixed_script": 0.90,
    "invisible": 1.00,
    "input_invalid": 1.00,
}


def evaluate_code(src: str, language: str = "python") -> CanonicalityResult:
    """Compute the identifier-canonicality signal for a source string.

    Args:
        src: Source code to evaluate.
        language: Currently only "python" is implemented.

    Returns:
        CanonicalityResult with score, kind, findings, and fingerprint.
    """
    if language not in _LANGUAGE_EXTRACTORS:
        return CanonicalityResult(
            score=1.0,
            kind="input_invalid",
            findings=[],
            identifier_count=0,
            fingerprint=None,
            detail={"error": f"unsupported language: {language}"},
        )

    source_bidi = _has_source_text_bidi(src)
    if source_bidi is not None:
        fingerprint = hashlib.sha256(src.encode("utf-8", errors="replace")).hexdigest()
        return CanonicalityResult(
            score=1.0,
            kind="invisible",
            findings=[
                IdentifierFinding(
                    name="<source>",
                    kind="invisible",
                    scripts=[],
                    detail=f"source text contains invisible/BiDi codepoint U+{ord(source_bidi):04X}",
                )
            ],
            identifier_count=0,
            fingerprint=fingerprint,
            detail={"source_text_bidi": f"U+{ord(source_bidi):04X}"},
        )

    extractor = _LANGUAGE_EXTRACTORS[language]
    try:
        identifiers = extractor(src)
    except SyntaxError as e:
        return CanonicalityResult(
            score=1.0,
            kind="input_invalid",
            findings=[],
            identifier_count=0,
            fingerprint=None,
            detail={"error": f"input does not parse: {e}"},
        )

    fingerprint = hashlib.sha256("\n".join(sorted(set(identifiers))).encode("utf-8")).hexdigest()

    findings: List[IdentifierFinding] = []
    seen: set = set()
    for ident in identifiers:
        if ident in seen:
            continue
        seen.add(ident)
        finding = _classify_identifier(ident)
        if finding is not None:
            findings.append(finding)

    if not findings:
        return CanonicalityResult(
            score=0.0,
            kind="clean",
            findings=[],
            identifier_count=len(seen),
            fingerprint=fingerprint,
        )

    # Aggregate: max-severity kind wins (catastrophic findings dominate).
    max_kind = max(findings, key=lambda f: _KIND_SCORE.get(f.kind, 0.0))
    score = _KIND_SCORE.get(max_kind.kind, 0.5)
    # Slight bump if multiple kinds present (more findings = more severity).
    n_distinct = len({f.kind for f in findings})
    if n_distinct > 1:
        score = min(1.0, score + 0.05)

    return CanonicalityResult(
        score=score,
        kind=max_kind.kind,
        findings=findings,
        identifier_count=len(seen),
        fingerprint=fingerprint,
        detail={"distinct_kinds": n_distinct, "total_findings": len(findings)},
    )


# --------------------------------------------------------------------------- #
#  Convenience: L13 mapping
# --------------------------------------------------------------------------- #

L13_MAPPING_RECOMMENDATION: Dict[CanonicalityKind, str] = {
    "clean": "ALLOW",
    "non_ascii": "ALLOW",  # log-only; could be QUARANTINE in stricter modes
    "confusable": "QUARANTINE",
    "mixed_script": "DENY",
    "invisible": "DENY",
    "input_invalid": "QUARANTINE",  # not a canonicality signal at runtime layer
}


def recommended_l13_action(result: CanonicalityResult) -> str:
    """Map a CanonicalityResult to the recommended L13 action string."""
    return L13_MAPPING_RECOMMENDATION.get(result.kind, "QUARANTINE")
