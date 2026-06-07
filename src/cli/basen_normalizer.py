"""
basen_normalizer.py — multi-base numeric representation layer.

Parses any numeric notation into a canonical Python int, and emits
that int as a literal in any of the six tongue idioms.

This is a *representation* layer, not a compilation layer. Binary,
hex, ternary, octal, and decimal are all notations for the same
integers. The normalizer makes them interchangeable as LatticeOp
argument values.

Supported input notations:
  Binary     0b1010  1010b  1010B  %1010 (BASIC/asm)
  Hex        0xFF  0XFF  FFh  FFH  $FF (asm)  #FF (CSS-style)
  Ternary    0t102  0T102  (base-3; digits 0,1,2)
  Octal      0o17  017  17q  17Q
  Decimal    plain integer or float
  Base-N     explicit: base(value, n) — any base 2..36

Tongue idioms for integer literals:
  KO  (Python)      0b...  0o...  0x...  plain
  AV  (TypeScript)  0b...  0o...  0x...  plain
  RU  (Rust)        0b...  0o...  0x...  plain (with _ separators for readability)
  CA  (C)           0b...  0...   0x...  plain
  UM  (Julia)       0b...  0o...  0x...  plain
  DR  (Haskell)     0b...  0o...  0x...  plain (fromIntegral may be needed)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

TongueCode = Literal["KO", "AV", "RU", "CA", "UM", "DR"]

# Tongue → canonical language name (mirrors LANG_MAP in ca_lexicon)
_TONGUE_LANG: dict[str, str] = {
    "KO": "python",
    "AV": "typescript",
    "RU": "rust",
    "CA": "c",
    "UM": "julia",
    "DR": "haskell",
}

# ── Parser patterns (tried in order — most specific first) ────────────────────

_PATTERNS: list[tuple[str, int]] = [
    # Binary
    (r"^0[bB]([01]+)$", 2),  # 0b1010
    (r"^([01]+)[bB]$", 2),  # 1010b
    (r"^%([01]+)$", 2),  # %1010  (BASIC/assembler)
    # Hex
    (r"^0[xX]([0-9A-Fa-f]+)$", 16),  # 0xFF
    (r"^([0-9A-Fa-f]+)[hH]$", 16),  # FFh
    (r"^\$([0-9A-Fa-f]+)$", 16),  # $FF
    (r"^#([0-9A-Fa-f]+)$", 16),  # #FF  (CSS-style)
    # Ternary
    (r"^0[tT]([012]+)$", 3),  # 0t102
    # Octal
    (r"^0[oO]([0-7]+)$", 8),  # 0o17
    (r"^0([0-7]+)$", 8),  # 017  (C-style — only if leading zero)
    (r"^([0-7]+)[qQ]$", 8),  # 17q
    # Decimal (last — so leading-zero octal matches first)
    (r"^(-?\d+)$", 10),  # plain integer
]


@dataclass(frozen=True)
class ParsedNumeric:
    """Result of parsing a numeric literal."""

    value: int  # canonical Python int
    detected_base: int  # 2, 3, 8, 10, or 16
    source: str  # original input string


def parse_literal(text: str) -> ParsedNumeric:
    """Parse any supported numeric notation into a canonical int.

    Raises ValueError if no pattern matches.
    """
    s = text.strip().replace("_", "")  # allow _ separators everywhere
    for pattern, base in _PATTERNS:
        m = re.fullmatch(pattern, s)
        if m:
            digits = m.group(1)
            value = int(digits, base)
            # re-apply sign for decimal negatives
            if base == 10 and s.startswith("-"):
                value = -value
            return ParsedNumeric(value=value, detected_base=base, source=text)
    raise ValueError(
        f"unrecognised numeric literal: {text!r}\n"
        "supported: 0b... 1010b %1010  0xFF FFh $FF #FF  "
        "0t102  0o17 017 17q  plain decimal"
    )


def parse_base(digits: str, base: int) -> int:
    """Parse a digit string in any base 2..36.

    Useful for extended bases the main parser doesn't cover.
    """
    if not 2 <= base <= 36:
        raise ValueError(f"base must be 2..36, got {base}")
    return int(digits.strip().replace("_", ""), base)


def emit_literal(value: int, base: int, tongue: TongueCode) -> str:
    """Emit an integer as a literal in the given base and tongue idiom.

    Returns a string ready for use as a template argument in a LatticeOp.
    """
    if base == 10:
        return str(value)

    if base == 2:
        raw = bin(value)  # '0b1010'
        if tongue == "RU":
            # Rust convention: group with underscores every 4 bits
            bits = raw[2:]
            padded = bits.zfill(((len(bits) - 1) // 4 + 1) * 4)
            grouped = "_".join(padded[i : i + 4] for i in range(0, len(padded), 4))
            return f"0b{grouped}"
        # All other tongues use the standard 0b prefix
        return raw

    if base == 16:
        raw = hex(value)  # '0xff'
        if tongue == "CA":
            return raw.upper().replace("0X", "0x")  # 0xFF (C canonical)
        if tongue == "DR":
            return raw  # Haskell: 0xff (lowercase is fine)
        return raw  # 0xff

    if base == 8:
        raw = oct(value)  # '0o17'
        if tongue == "CA":
            # C octal: just leading zero
            return "0" + oct(value)[2:]
        return raw  # everyone else: 0o17

    if base == 3:
        # Ternary — no universal literal syntax; emit as a comment-annotated decimal
        digits = _to_base_digits(value, 3)
        return f"{value}  /* 0t{''.join(digits)} */"

    # Generic base-N: emit as decimal with annotation
    digits = _to_base_digits(value, base)
    return f"{value}  /* base{base}:{''.join(digits)} */"


def _to_base_digits(value: int, base: int) -> list[str]:
    """Return digit characters for value in any base 2..36."""
    CHARS = "0123456789abcdefghijklmnopqrstuvwxyz"
    if value == 0:
        return ["0"]
    negative = value < 0
    n = abs(value)
    digits = []
    while n:
        digits.append(CHARS[n % base])
        n //= base
    if negative:
        digits.append("-")
    return list(reversed(digits))


def convert(text: str, target_base: int, tongue: TongueCode = "KO") -> str:
    """One-shot: parse any literal, emit in target_base idiom for tongue."""
    parsed = parse_literal(text)
    return emit_literal(parsed.value, target_base, tongue)


__all__ = [
    "ParsedNumeric",
    "TongueCode",
    "parse_literal",
    "parse_base",
    "emit_literal",
    "convert",
]
