"""
Cassisivadan (CA) Unified Multilingual Lexicon
===============================================
Sacred Tongue of Math & Logic
Patent: US Provisional #63/961,403

Each entry is ONE substrate row linking:
  - SS1 transport token (byte ↔ tongue token bijection)
  - Atomic trit vector [KO, AV, RU, CA, UM, DR]
  - 8-dim feature vector [Z, group, period, valence, chi, band, tongue_id, 0]
  - Code snippets in all 6 target languages:
      KO → Python  (Kor'aelin)
      AV → TypeScript (Avali)
      RU → Rust (Runethic)
      CA → C (Cassisivadan)
      UM → Julia (Umbroth)
      DR → Haskell (Draumric)

The substrate rule: SS1 transport and atomic ops resolve to the SAME row.
The UsageLedger writes to this row from either direction.
The phi-discount cost = base / φ^width applies per-row, not per-layer.

Usage:
    from ca_lexicon import LEXICON, lookup, emit_code
    entry = lookup("div")
    rust_code = emit_code("div", "RU", lhs="x", rhs="y")
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np

# ─── Constants ────────────────────────────────────────────────────────────

PHI = (1 + 5**0.5) / 2
TONGUE_NAMES = ["KO", "AV", "RU", "CA", "UM", "DR"]
LANG_MAP = {
    "KO": "python",
    "AV": "typescript",
    "RU": "rust",
    "CA": "c",
    "UM": "julia",
    "DR": "haskell",
}

EXTENDED_TONGUE_NAMES = ["GO", "ZI"]
EXTENDED_LANG_MAP = {"GO": "go", "ZI": "zig"}
ALL_TONGUE_NAMES = TONGUE_NAMES + EXTENDED_TONGUE_NAMES
ALL_LANG_MAP = {**LANG_MAP, **EXTENDED_LANG_MAP}
TONGUE_PARENT = {"GO": "CA", "ZI": "RU"}


@dataclass(frozen=True)
class LexiconEntry:
    """One substrate row — the atom that both SS1 and the op layer resolve to."""
    op_id: int                              # 0x00–0x3F
    name: str                               # human name
    trit: Tuple[int, ...]                   # (KO, AV, RU, CA, UM, DR)
    feat: Tuple[float, ...]                 # 8-dim atomic feature vector
    code: Dict[str, str]                    # tongue → code template
    band: str                               # ARITHMETIC / LOGIC / COMPARISON / AGGREGATION
    chi: float                              # risk score
    valence: int                            # number of operands
    note: str = ""                          # why chi is what it is


# ─── Band 0: ARITHMETIC (0x00–0x0F) ──────────────────────────────────────

_ARITHMETIC = [
    LexiconEntry(
        op_id=0x00, name="add", band="ARITHMETIC", chi=0.1, valence=2,
        trit=(0, 0, 0, +1, 0, 0),
        feat=(0, 1, 1, 2, 0.1, 2, 3, 0),
        code={
            "KO": "({a} + {b})",
            "AV": "({a} + {b})",
            "RU": "{a}.wrapping_add({b})",
            "CA": "({a} + {b})",
            "UM": "({a} + {b})",
            "DR": "({a} + {b})",
        },
    ),
    LexiconEntry(
        op_id=0x01, name="sub", band="ARITHMETIC", chi=0.1, valence=2,
        trit=(0, 0, 0, +1, 0, 0),
        feat=(1, 1, 1, 2, 0.1, 2, 3, 0),
        code={
            "KO": "({a} - {b})",
            "AV": "({a} - {b})",
            "RU": "{a}.wrapping_sub({b})",
            "CA": "({a} - {b})",
            "UM": "({a} - {b})",
            "DR": "({a} - {b})",
        },
    ),
    LexiconEntry(
        op_id=0x02, name="mul", band="ARITHMETIC", chi=0.2, valence=2,
        trit=(0, 0, 0, +1, 0, 0),
        feat=(2, 1, 1, 2, 0.2, 2, 3, 0),
        code={
            "KO": "({a} * {b})",
            "AV": "({a} * {b})",
            "RU": "{a}.wrapping_mul({b})",
            "CA": "({a} * {b})",
            "UM": "({a} * {b})",
            "DR": "({a} * {b})",
        },
    ),
    LexiconEntry(
        op_id=0x03, name="div", band="ARITHMETIC", chi=0.8, valence=2,
        trit=(0, 0, 0, +1, 0, -1),
        feat=(3, 1, 1, 2, 0.8, 2, 3, 0),
        note="div-by-zero risk → chi=0.8, DR=-1 (lossy)",
        code={
            "KO": "({a} / {b}) if {b} != 0 else float('inf')",
            "AV": "{b} !== 0 ? ({a} / {b}) : Infinity",
            "RU": "{a}.checked_div({b}).unwrap_or(i64::MAX)",
            "CA": "({b} != 0) ? ({a} / {b}) : INT_MAX",
            "UM": "({b} != 0) ? ({a} / {b}) : Inf",
            "DR": "if {b} /= 0 then {a} `div` {b} else maxBound",
        },
    ),
    LexiconEntry(
        op_id=0x04, name="mod", band="ARITHMETIC", chi=0.5, valence=2,
        trit=(0, 0, 0, +1, 0, 0),
        feat=(4, 1, 1, 2, 0.5, 2, 3, 0),
        code={
            "KO": "({a} % {b})",
            "AV": "({a} % {b})",
            "RU": "{a}.rem_euclid({b})",
            "CA": "({a} % {b})",
            "UM": "mod({a}, {b})",
            "DR": "({a} `mod` {b})",
        },
    ),
    LexiconEntry(
        op_id=0x05, name="pow", band="ARITHMETIC", chi=1.2, valence=2,
        trit=(0, 0, 0, +1, 0, +1),
        feat=(5, 1, 2, 2, 1.2, 2, 3, 0),
        note="overflow risk → chi=1.2, DR=+1 (transform)",
        code={
            "KO": "({a} ** {b})",
            "AV": "Math.pow({a}, {b})",
            "RU": "{a}.pow({b} as u32)",
            "CA": "pow({a}, {b})",
            "UM": "({a} ^ {b})",
            "DR": "({a} ^ {b})",
        },
    ),
    LexiconEntry(
        op_id=0x06, name="sqrt", band="ARITHMETIC", chi=0.5, valence=1,
        trit=(0, 0, 0, +1, 0, +1),
        feat=(6, 1, 2, 1, 0.5, 2, 3, 0),
        code={
            "KO": "math.sqrt({a})",
            "AV": "Math.sqrt({a})",
            "RU": "({a} as f64).sqrt()",
            "CA": "sqrt({a})",
            "UM": "sqrt({a})",
            "DR": "sqrt (fromIntegral {a})",
        },
    ),
    LexiconEntry(
        op_id=0x07, name="log", band="ARITHMETIC", chi=0.8, valence=1,
        trit=(0, 0, 0, +1, 0, +1),
        feat=(7, 1, 2, 1, 0.8, 2, 3, 0),
        note="log(0) risk → chi=0.8",
        code={
            "KO": "math.log({a}) if {a} > 0 else float('-inf')",
            "AV": "{a} > 0 ? Math.log({a}) : -Infinity",
            "RU": "({a} as f64).ln()",
            "CA": "log({a})",
            "UM": "log({a})",
            "DR": "log (fromIntegral {a})",
        },
    ),
    LexiconEntry(
        op_id=0x08, name="exp", band="ARITHMETIC", chi=1.5, valence=1,
        trit=(0, 0, 0, +1, 0, +1),
        feat=(8, 1, 2, 1, 1.5, 2, 3, 0),
        note="overflow risk → chi=1.5",
        code={
            "KO": "math.exp({a})",
            "AV": "Math.exp({a})",
            "RU": "({a} as f64).exp()",
            "CA": "exp({a})",
            "UM": "exp({a})",
            "DR": "exp (fromIntegral {a})",
        },
    ),
    LexiconEntry(
        op_id=0x09, name="abs", band="ARITHMETIC", chi=0.0, valence=1,
        trit=(0, 0, 0, +1, 0, 0),
        feat=(9, 1, 1, 1, 0.0, 2, 3, 0),
        code={
            "KO": "abs({a})",
            "AV": "Math.abs({a})",
            "RU": "{a}.abs()",
            "CA": "abs({a})",
            "UM": "abs({a})",
            "DR": "abs {a}",
        },
    ),
    LexiconEntry(
        op_id=0x0A, name="neg", band="ARITHMETIC", chi=0.1, valence=1,
        trit=(0, 0, 0, +1, 0, 0),
        feat=(10, 1, 1, 1, 0.1, 2, 3, 0),
        code={
            "KO": "(-{a})",
            "AV": "(-{a})",
            "RU": "-{a}",
            "CA": "(-{a})",
            "UM": "(-{a})",
            "DR": "(negate {a})",
        },
    ),
    LexiconEntry(
        op_id=0x0B, name="inc", band="ARITHMETIC", chi=0.1, valence=1,
        trit=(0, 0, 0, +1, 0, 0),
        feat=(11, 1, 1, 1, 0.1, 2, 3, 0),
        code={
            "KO": "({a} + 1)",
            "AV": "({a} + 1)",
            "RU": "{a} + 1",
            "CA": "({a} + 1)",
            "UM": "({a} + 1)",
            "DR": "(succ {a})",
        },
    ),
    LexiconEntry(
        op_id=0x0C, name="dec", band="ARITHMETIC", chi=0.1, valence=1,
        trit=(0, 0, 0, +1, 0, 0),
        feat=(12, 1, 1, 1, 0.1, 2, 3, 0),
        code={
            "KO": "({a} - 1)",
            "AV": "({a} - 1)",
            "RU": "{a} - 1",
            "CA": "({a} - 1)",
            "UM": "({a} - 1)",
            "DR": "(pred {a})",
        },
    ),
    LexiconEntry(
        op_id=0x0D, name="floor", band="ARITHMETIC", chi=0.2, valence=1,
        trit=(0, 0, 0, +1, 0, -1),
        feat=(13, 1, 1, 1, 0.2, 2, 3, 0),
        note="DR=-1: lossy transform",
        code={
            "KO": "math.floor({a})",
            "AV": "Math.floor({a})",
            "RU": "({a} as f64).floor() as i64",
            "CA": "(int)floor({a})",
            "UM": "floor(Int, {a})",
            "DR": "floor {a}",
        },
    ),
    LexiconEntry(
        op_id=0x0E, name="ceil", band="ARITHMETIC", chi=0.2, valence=1,
        trit=(0, 0, 0, +1, 0, -1),
        feat=(14, 1, 1, 1, 0.2, 2, 3, 0),
        note="DR=-1: lossy transform",
        code={
            "KO": "math.ceil({a})",
            "AV": "Math.ceil({a})",
            "RU": "({a} as f64).ceil() as i64",
            "CA": "(int)ceil({a})",
            "UM": "ceil(Int, {a})",
            "DR": "ceiling {a}",
        },
    ),
    LexiconEntry(
        op_id=0x0F, name="round", band="ARITHMETIC", chi=0.2, valence=1,
        trit=(0, 0, 0, +1, 0, -1),
        feat=(15, 1, 1, 1, 0.2, 2, 3, 0),
        note="DR=-1: lossy transform",
        code={
            "KO": "round({a})",
            "AV": "Math.round({a})",
            "RU": "({a} as f64).round() as i64",
            "CA": "(int)round({a})",
            "UM": "round(Int, {a})",
            "DR": "round {a}",
        },
    ),
]

# ─── Band 1: LOGIC (0x10–0x1F) ───────────────────────────────────────────

_LOGIC = [
    LexiconEntry(
        op_id=0x10, name="and", band="LOGIC", chi=0.1, valence=2,
        trit=(+1, 0, 0, +1, 0, 0),
        feat=(16, 2, 1, 2, 0.1, 2, 3, 0),
        code={
            "KO": "({a} and {b})",
            "AV": "({a} && {b})",
            "RU": "({a} && {b})",
            "CA": "({a} && {b})",
            "UM": "({a} && {b})",
            "DR": "({a} && {b})",
        },
    ),
    LexiconEntry(
        op_id=0x11, name="or", band="LOGIC", chi=0.1, valence=2,
        trit=(+1, 0, 0, +1, 0, 0),
        feat=(17, 2, 1, 2, 0.1, 2, 3, 0),
        code={
            "KO": "({a} or {b})",
            "AV": "({a} || {b})",
            "RU": "({a} || {b})",
            "CA": "({a} || {b})",
            "UM": "({a} || {b})",
            "DR": "({a} || {b})",
        },
    ),
    LexiconEntry(
        op_id=0x12, name="not", band="LOGIC", chi=0.1, valence=1,
        trit=(+1, 0, 0, +1, 0, 0),
        feat=(18, 2, 1, 1, 0.1, 2, 3, 0),
        code={
            "KO": "(not {a})",
            "AV": "(!{a})",
            "RU": "(!{a})",
            "CA": "(!{a})",
            "UM": "(!{a})",
            "DR": "(not {a})",
        },
    ),
    LexiconEntry(
        op_id=0x13, name="xor", band="LOGIC", chi=0.3, valence=2,
        trit=(0, 0, 0, +1, +1, 0),
        feat=(19, 2, 1, 2, 0.3, 2, 3, 0),
        note="UM=+1: crypto primitive",
        code={
            "KO": "({a} ^ {b})",
            "AV": "({a} ^ {b})",
            "RU": "({a} ^ {b})",
            "CA": "({a} ^ {b})",
            "UM": "xor({a}, {b})",
            "DR": "(xor {a} {b})",
        },
    ),
    LexiconEntry(
        op_id=0x14, name="nand", band="LOGIC", chi=0.2, valence=2,
        trit=(+1, 0, 0, +1, 0, 0),
        feat=(20, 2, 1, 2, 0.2, 2, 3, 0),
        code={
            "KO": "(not ({a} and {b}))",
            "AV": "!({a} && {b})",
            "RU": "!({a} && {b})",
            "CA": "!({a} && {b})",
            "UM": "!({a} && {b})",
            "DR": "(not ({a} && {b}))",
        },
    ),
    LexiconEntry(
        op_id=0x15, name="nor", band="LOGIC", chi=0.2, valence=2,
        trit=(+1, 0, 0, +1, 0, 0),
        feat=(21, 2, 1, 2, 0.2, 2, 3, 0),
        code={
            "KO": "(not ({a} or {b}))",
            "AV": "!({a} || {b})",
            "RU": "!({a} || {b})",
            "CA": "!({a} || {b})",
            "UM": "!({a} || {b})",
            "DR": "(not ({a} || {b}))",
        },
    ),
    LexiconEntry(
        op_id=0x16, name="shl", band="LOGIC", chi=0.6, valence=2,
        trit=(0, 0, 0, +1, +1, 0),
        feat=(22, 2, 1, 2, 0.6, 2, 3, 0),
        note="UM=+1: bit manipulation",
        code={
            "KO": "({a} << {b})",
            "AV": "({a} << {b})",
            "RU": "({a} << {b})",
            "CA": "({a} << {b})",
            "UM": "({a} << {b})",
            "DR": "(shiftL {a} {b})",
        },
    ),
    LexiconEntry(
        op_id=0x17, name="shr", band="LOGIC", chi=0.6, valence=2,
        trit=(0, 0, 0, +1, +1, 0),
        feat=(23, 2, 1, 2, 0.6, 2, 3, 0),
        code={
            "KO": "({a} >> {b})",
            "AV": "({a} >> {b})",
            "RU": "({a} >> {b})",
            "CA": "({a} >> {b})",
            "UM": "({a} >> {b})",
            "DR": "(shiftR {a} {b})",
        },
    ),
    LexiconEntry(
        op_id=0x18, name="rotl", band="LOGIC", chi=0.4, valence=2,
        trit=(0, 0, 0, +1, +1, +1),
        feat=(24, 2, 2, 2, 0.4, 2, 3, 0),
        note="UM+DR: rotation is crypto + transform",
        code={
            "KO": "(({a} << {b}) | ({a} >> (64 - {b}))) & ((1 << 64) - 1)",
            "AV": "({a} << {b}) | ({a} >>> (32 - {b}))",
            "RU": "{a}.rotate_left({b} as u32)",
            "CA": "({a} << {b}) | ({a} >> (sizeof({a})*8 - {b}))",
            "UM": "bitrotate({a}, {b})",
            "DR": "(rotateL {a} {b})",
        },
    ),
    LexiconEntry(
        op_id=0x19, name="rotr", band="LOGIC", chi=0.4, valence=2,
        trit=(0, 0, 0, +1, +1, +1),
        feat=(25, 2, 2, 2, 0.4, 2, 3, 0),
        code={
            "KO": "(({a} >> {b}) | ({a} << (64 - {b}))) & ((1 << 64) - 1)",
            "AV": "({a} >>> {b}) | ({a} << (32 - {b}))",
            "RU": "{a}.rotate_right({b} as u32)",
            "CA": "({a} >> {b}) | ({a} << (sizeof({a})*8 - {b}))",
            "UM": "bitrotate({a}, -{b})",
            "DR": "(rotateR {a} {b})",
        },
    ),
    LexiconEntry(
        op_id=0x1A, name="popcount", band="LOGIC", chi=0.1, valence=1,
        trit=(0, +1, 0, +1, 0, 0),
        feat=(26, 2, 2, 1, 0.1, 2, 3, 0),
        code={
            "KO": "bin({a}).count('1')",
            "AV": "{a}.toString(2).split('').filter(c => c === '1').length",
            "RU": "{a}.count_ones()",
            "CA": "__builtin_popcountll({a})",
            "UM": "count_ones({a})",
            "DR": "(popCount {a})",
        },
    ),
    LexiconEntry(
        op_id=0x1B, name="clz", band="LOGIC", chi=0.1, valence=1,
        trit=(0, +1, 0, +1, 0, 0),
        feat=(27, 2, 2, 1, 0.1, 2, 3, 0),
        code={
            "KO": "({a}.bit_length() and (64 - {a}.bit_length()) or 64)",
            "AV": "Math.clz32({a})",
            "RU": "{a}.leading_zeros()",
            "CA": "__builtin_clzll({a})",
            "UM": "leading_zeros({a})",
            "DR": "(countLeadingZeros {a})",
        },
    ),
    LexiconEntry(
        op_id=0x1C, name="ctz", band="LOGIC", chi=0.1, valence=1,
        trit=(0, +1, 0, +1, 0, 0),
        feat=(28, 2, 2, 1, 0.1, 2, 3, 0),
        code={
            "KO": "(({a} & -{a}).bit_length() - 1) if {a} else 64",
            "AV": "({a} ? 31 - Math.clz32({a} & -{a}) : 32)",
            "RU": "{a}.trailing_zeros()",
            "CA": "__builtin_ctzll({a})",
            "UM": "trailing_zeros({a})",
            "DR": "(countTrailingZeros {a})",
        },
    ),
    LexiconEntry(
        op_id=0x1D, name="bitmask", band="LOGIC", chi=0.7, valence=2,
        trit=(0, 0, +1, +1, +1, 0),
        feat=(29, 2, 2, 2, 0.7, 2, 3, 0),
        note="RU+UM: creates mask scope + security",
        code={
            "KO": "({a} & {b})",
            "AV": "({a} & {b})",
            "RU": "({a} & {b})",
            "CA": "({a} & {b})",
            "UM": "({a} & {b})",
            "DR": "({a} .&. {b})",
        },
    ),
    LexiconEntry(
        op_id=0x1E, name="bitset", band="LOGIC", chi=0.3, valence=2,
        trit=(0, 0, 0, +1, 0, 0),
        feat=(30, 2, 1, 2, 0.3, 2, 3, 0),
        code={
            "KO": "({a} | (1 << {b}))",
            "AV": "({a} | (1 << {b}))",
            "RU": "({a} | (1 << {b}))",
            "CA": "({a} | (1 << {b}))",
            "UM": "({a} | (1 << {b}))",
            "DR": "(setBit {a} {b})",
        },
    ),
    LexiconEntry(
        op_id=0x1F, name="bitclear", band="LOGIC", chi=0.3, valence=1,
        trit=(0, 0, 0, +1, 0, -1),
        feat=(31, 2, 1, 2, 0.3, 2, 3, 0),
        note="DR=-1: destructive",
        code={
            "KO": "({a} & ~(1 << {b}))",
            "AV": "({a} & ~(1 << {b}))",
            "RU": "({a} & !(1 << {b}))",
            "CA": "({a} & ~(1 << {b}))",
            "UM": "({a} & ~(1 << {b}))",
            "DR": "(clearBit {a} {b})",
        },
    ),
]

# ─── Band 2: COMPARISON (0x20–0x2F) ──────────────────────────────────────

_COMPARISON = [
    LexiconEntry(
        op_id=0x20, name="eq", band="COMPARISON", chi=0.0, valence=2,
        trit=(+1, 0, 0, +1, 0, 0),
        feat=(32, 3, 1, 2, 0.0, 1, 3, 0),
        code={
            "KO": "({a} == {b})",
            "AV": "({a} === {b})",
            "RU": "({a} == {b})",
            "CA": "({a} == {b})",
            "UM": "({a} == {b})",
            "DR": "({a} == {b})",
        },
    ),
    LexiconEntry(
        op_id=0x21, name="neq", band="COMPARISON", chi=0.0, valence=2,
        trit=(+1, 0, 0, +1, 0, 0),
        feat=(33, 3, 1, 2, 0.0, 1, 3, 0),
        code={
            "KO": "({a} != {b})",
            "AV": "({a} !== {b})",
            "RU": "({a} != {b})",
            "CA": "({a} != {b})",
            "UM": "({a} != {b})",
            "DR": "({a} /= {b})",
        },
    ),
    LexiconEntry(
        op_id=0x22, name="lt", band="COMPARISON", chi=0.0, valence=2,
        trit=(+1, 0, 0, +1, 0, 0),
        feat=(34, 3, 1, 2, 0.0, 1, 3, 0),
        code={
            "KO": "({a} < {b})",
            "AV": "({a} < {b})",
            "RU": "({a} < {b})",
            "CA": "({a} < {b})",
            "UM": "({a} < {b})",
            "DR": "({a} < {b})",
        },
    ),
    LexiconEntry(
        op_id=0x23, name="lte", band="COMPARISON", chi=0.0, valence=2,
        trit=(+1, 0, 0, +1, 0, 0),
        feat=(35, 3, 1, 2, 0.0, 1, 3, 0),
        code={
            "KO": "({a} <= {b})",
            "AV": "({a} <= {b})",
            "RU": "({a} <= {b})",
            "CA": "({a} <= {b})",
            "UM": "({a} <= {b})",
            "DR": "({a} <= {b})",
        },
    ),
    LexiconEntry(
        op_id=0x24, name="gt", band="COMPARISON", chi=0.0, valence=2,
        trit=(+1, 0, 0, +1, 0, 0),
        feat=(36, 3, 1, 2, 0.0, 1, 3, 0),
        code={
            "KO": "({a} > {b})",
            "AV": "({a} > {b})",
            "RU": "({a} > {b})",
            "CA": "({a} > {b})",
            "UM": "({a} > {b})",
            "DR": "({a} > {b})",
        },
    ),
    LexiconEntry(
        op_id=0x25, name="gte", band="COMPARISON", chi=0.0, valence=2,
        trit=(+1, 0, 0, +1, 0, 0),
        feat=(37, 3, 1, 2, 0.0, 1, 3, 0),
        code={
            "KO": "({a} >= {b})",
            "AV": "({a} >= {b})",
            "RU": "({a} >= {b})",
            "CA": "({a} >= {b})",
            "UM": "({a} >= {b})",
            "DR": "({a} >= {b})",
        },
    ),
    LexiconEntry(
        op_id=0x26, name="cmp", band="COMPARISON", chi=0.0, valence=2,
        trit=(+1, +1, 0, +1, 0, 0),
        feat=(38, 3, 1, 2, 0.0, 1, 3, 0),
        note="AV=+1: produces three-way result",
        code={
            "KO": "(({a} > {b}) - ({a} < {b}))",
            "AV": "({a} < {b} ? -1 : {a} > {b} ? 1 : 0)",
            "RU": "{a}.cmp(&{b})",
            "CA": "({a} > {b}) - ({a} < {b})",
            "UM": "cmp({a}, {b})",
            "DR": "(compare {a} {b})",
        },
    ),
    LexiconEntry(
        op_id=0x27, name="min", band="COMPARISON", chi=0.0, valence=2,
        trit=(0, 0, 0, +1, 0, 0),
        feat=(39, 3, 1, 2, 0.0, 1, 3, 0),
        code={
            "KO": "min({a}, {b})",
            "AV": "Math.min({a}, {b})",
            "RU": "std::cmp::min({a}, {b})",
            "CA": "(({a}) < ({b}) ? ({a}) : ({b}))",
            "UM": "min({a}, {b})",
            "DR": "(min {a} {b})",
        },
    ),
    LexiconEntry(
        op_id=0x28, name="max", band="COMPARISON", chi=0.0, valence=2,
        trit=(0, 0, 0, +1, 0, 0),
        feat=(40, 3, 1, 2, 0.0, 1, 3, 0),
        code={
            "KO": "max({a}, {b})",
            "AV": "Math.max({a}, {b})",
            "RU": "std::cmp::max({a}, {b})",
            "CA": "(({a}) > ({b}) ? ({a}) : ({b}))",
            "UM": "max({a}, {b})",
            "DR": "(max {a} {b})",
        },
    ),
    LexiconEntry(
        op_id=0x29, name="clamp", band="COMPARISON", chi=0.1, valence=3,
        trit=(0, 0, +1, +1, 0, 0),
        feat=(41, 3, 2, 3, 0.1, 1, 3, 0),
        code={
            "KO": "max({lo}, min({hi}, {a}))",
            "AV": "Math.max({lo}, Math.min({hi}, {a}))",
            "RU": "{a}.clamp({lo}, {hi})",
            "CA": "(({a})<({lo})?({lo}):(({a})>({hi})?({hi}):({a})))",
            "UM": "clamp({a}, {lo}, {hi})",
            "DR": "(max {lo} (min {hi} {a}))",
        },
    ),
    LexiconEntry(
        op_id=0x2A, name="within", band="COMPARISON", chi=0.1, valence=3,
        trit=(+1, 0, +1, +1, 0, 0),
        feat=(42, 3, 2, 3, 0.1, 1, 3, 0),
        code={
            "KO": "({lo} <= {a} <= {hi})",
            "AV": "({a} >= {lo} && {a} <= {hi})",
            "RU": "({lo}..={hi}).contains(&{a})",
            "CA": "({a} >= {lo} && {a} <= {hi})",
            "UM": "({lo} <= {a} <= {hi})",
            "DR": "({a} >= {lo} && {a} <= {hi})",
        },
    ),
    LexiconEntry(
        op_id=0x2B, name="isnan", band="COMPARISON", chi=0.5, valence=1,
        trit=(0, +1, 0, +1, +1, 0),
        feat=(43, 3, 1, 1, 0.5, 1, 3, 0),
        note="UM=+1: NaN is a security concern",
        code={
            "KO": "math.isnan({a})",
            "AV": "Number.isNaN({a})",
            "RU": "{a}.is_nan()",
            "CA": "isnan({a})",
            "UM": "isnan({a})",
            "DR": "(isNaN {a})",
        },
    ),
    LexiconEntry(
        op_id=0x2C, name="isinf", band="COMPARISON", chi=0.5, valence=1,
        trit=(0, +1, 0, +1, +1, 0),
        feat=(44, 3, 1, 1, 0.5, 1, 3, 0),
        code={
            "KO": "math.isinf({a})",
            "AV": "!Number.isFinite({a})",
            "RU": "{a}.is_infinite()",
            "CA": "isinf({a})",
            "UM": "isinf({a})",
            "DR": "(isInfinite {a})",
        },
    ),
    LexiconEntry(
        op_id=0x2D, name="isfinite", band="COMPARISON", chi=0.3, valence=1,
        trit=(0, +1, 0, +1, +1, 0),
        feat=(45, 3, 1, 1, 0.3, 1, 3, 0),
        code={
            "KO": "math.isfinite({a})",
            "AV": "Number.isFinite({a})",
            "RU": "{a}.is_finite()",
            "CA": "isfinite({a})",
            "UM": "isfinite({a})",
            "DR": "(not (isNaN {a} || isInfinite {a}))",
        },
    ),
    LexiconEntry(
        op_id=0x2E, name="sign", band="COMPARISON", chi=0.0, valence=1,
        trit=(0, +1, 0, +1, 0, 0),
        feat=(46, 3, 1, 1, 0.0, 1, 3, 0),
        code={
            "KO": "(1 if {a} > 0 else -1 if {a} < 0 else 0)",
            "AV": "Math.sign({a})",
            "RU": "{a}.signum()",
            "CA": "({a} > 0) - ({a} < 0)",
            "UM": "sign({a})",
            "DR": "(signum {a})",
        },
    ),
    LexiconEntry(
        op_id=0x2F, name="classify", band="COMPARISON", chi=0.2, valence=1,
        trit=(0, +1, 0, +1, 0, +1),
        feat=(47, 3, 2, 1, 0.2, 1, 3, 0),
        note="DR=+1: type transform",
        code={
            "KO": "type({a}).__name__",
            "AV": "typeof {a}",
            "RU": "std::mem::discriminant(&{a})",
            "CA": "_Generic(({a}), int: 0, float: 1, double: 2, default: -1)",
            "UM": "typeof({a})",
            "DR": "(typeOf {a})",
        },
    ),
]

# ─── Band 3: AGGREGATION (0x30–0x3F) ─────────────────────────────────────

_AGGREGATION = [
    LexiconEntry(
        op_id=0x30, name="sum", band="AGGREGATION", chi=0.1, valence=1,
        trit=(0, 0, +1, +1, 0, 0),
        feat=(48, 4, 2, 1, 0.1, 3, 3, 0),
        code={
            "KO": "sum({xs})",
            "AV": "{xs}.reduce((a, b) => a + b, 0)",
            "RU": "{xs}.iter().sum::<i64>()",
            "CA": "for(int i=0;i<n;i++) s+={xs}[i];",
            "UM": "sum({xs})",
            "DR": "(sum {xs})",
        },
    ),
    LexiconEntry(
        op_id=0x31, name="product", band="AGGREGATION", chi=0.5, valence=1,
        trit=(0, 0, +1, +1, 0, 0),
        feat=(49, 4, 2, 1, 0.5, 3, 3, 0),
        note="overflow risk",
        code={
            "KO": "math.prod({xs})",
            "AV": "{xs}.reduce((a, b) => a * b, 1)",
            "RU": "{xs}.iter().product::<i64>()",
            "CA": "for(int i=0;i<n;i++) p*={xs}[i];",
            "UM": "prod({xs})",
            "DR": "(product {xs})",
        },
    ),
    LexiconEntry(
        op_id=0x32, name="mean", band="AGGREGATION", chi=0.2, valence=1,
        trit=(0, 0, +1, +1, 0, 0),
        feat=(50, 4, 2, 1, 0.2, 3, 3, 0),
        code={
            "KO": "statistics.mean({xs})",
            "AV": "{xs}.reduce((a, b) => a + b, 0) / {xs}.length",
            "RU": "{xs}.iter().sum::<f64>() / {xs}.len() as f64",
            "CA": "sum/{n}",
            "UM": "mean({xs})",
            "DR": "(sum {xs} / fromIntegral (length {xs}))",
        },
    ),
    LexiconEntry(
        op_id=0x33, name="variance", band="AGGREGATION", chi=0.3, valence=1,
        trit=(0, 0, +1, +1, 0, 0),
        feat=(51, 4, 3, 1, 0.3, 3, 3, 0),
        code={
            "KO": "statistics.variance({xs})",
            "AV": "(() => {{ const m = {xs}.reduce((a,b)=>a+b,0)/{xs}.length; return {xs}.reduce((s,x)=>s+(x-m)**2,0)/{xs}.length; }})()",
            "RU": "{{ let m: f64 = {xs}.iter().sum::<f64>()/{xs}.len() as f64; {xs}.iter().map(|x| (x-m).powi(2)).sum::<f64>()/{xs}.len() as f64 }}",
            "CA": "variance({xs}, {n})",
            "UM": "var({xs})",
            "DR": "(variance {xs})",
        },
    ),
    LexiconEntry(
        op_id=0x34, name="stdev", band="AGGREGATION", chi=0.3, valence=1,
        trit=(0, 0, +1, +1, 0, 0),
        feat=(52, 4, 3, 1, 0.3, 3, 3, 0),
        code={
            "KO": "statistics.stdev({xs})",
            "AV": "Math.sqrt(variance)",
            "RU": "variance.sqrt()",
            "CA": "sqrt(variance({xs}, {n}))",
            "UM": "std({xs})",
            "DR": "(sqrt (variance {xs}))",
        },
    ),
    LexiconEntry(
        op_id=0x35, name="reduce", band="AGGREGATION", chi=0.6, valence=2,
        trit=(+1, 0, +1, +1, 0, +1),
        feat=(53, 4, 3, 2, 0.6, 3, 3, 0),
        note="KO+RU+DR: control + scope + transform",
        code={
            "KO": "functools.reduce({fn}, {xs})",
            "AV": "{xs}.reduce({fn})",
            "RU": "{xs}.iter().fold({init}, {fn})",
            "CA": "for(int i=0;i<n;i++) acc={fn}(acc,{xs}[i]);",
            "UM": "reduce({fn}, {xs}; init={init})",
            "DR": "(foldl {fn} {init} {xs})",
        },
    ),
    LexiconEntry(
        op_id=0x36, name="fold", band="AGGREGATION", chi=0.6, valence=2,
        trit=(+1, 0, +1, +1, 0, +1),
        feat=(54, 4, 3, 2, 0.6, 3, 3, 0),
        code={
            "KO": "functools.reduce({fn}, {xs}, {init})",
            "AV": "{xs}.reduce({fn}, {init})",
            "RU": "{xs}.iter().fold({init}, {fn})",
            "CA": "for(int i=0;i<n;i++) acc={fn}(acc,{xs}[i]);",
            "UM": "foldl({fn}, {init}, {xs})",
            "DR": "(foldl' {fn} {init} {xs})",
        },
    ),
    LexiconEntry(
        op_id=0x37, name="scan", band="AGGREGATION", chi=0.5, valence=2,
        trit=(+1, +1, +1, +1, 0, +1),
        feat=(55, 4, 3, 2, 0.5, 3, 3, 0),
        note="AV=+1: emits intermediates",
        code={
            "KO": "itertools.accumulate({xs}, {fn})",
            "AV": "{xs}.reduce((acc, x) => [...acc, {fn}(acc[acc.length-1], x)], [{init}])",
            "RU": "{xs}.iter().scan({init}, |st, x| {{ *st = {fn}(*st, *x); Some(*st) }})",
            "CA": "for(int i=0;i<n;i++) {{ acc={fn}(acc,{xs}[i]); out[i]=acc; }}",
            "UM": "accumulate({fn}, {xs}; init={init})",
            "DR": "(scanl {fn} {init} {xs})",
        },
    ),
    LexiconEntry(
        op_id=0x38, name="filter", band="AGGREGATION", chi=0.3, valence=2,
        trit=(+1, 0, +1, +1, 0, -1),
        feat=(56, 4, 2, 2, 0.3, 3, 3, 0),
        note="DR=-1: discards elements",
        code={
            "KO": "[x for x in {xs} if {pred}(x)]",
            "AV": "{xs}.filter({pred})",
            "RU": "{xs}.iter().filter(|x| {pred}(x)).collect::<Vec<_>>()",
            "CA": "for(int i=0;i<n;i++) if({pred}({xs}[i])) out[j++]={xs}[i];",
            "UM": "filter({pred}, {xs})",
            "DR": "(filter {pred} {xs})",
        },
    ),
    LexiconEntry(
        op_id=0x39, name="map", band="AGGREGATION", chi=0.2, valence=2,
        trit=(0, 0, +1, +1, 0, +1),
        feat=(57, 4, 2, 2, 0.2, 3, 3, 0),
        code={
            "KO": "[{fn}(x) for x in {xs}]",
            "AV": "{xs}.map({fn})",
            "RU": "{xs}.iter().map({fn}).collect::<Vec<_>>()",
            "CA": "for(int i=0;i<n;i++) out[i]={fn}({xs}[i]);",
            "UM": "map({fn}, {xs})",
            "DR": "(map {fn} {xs})",
        },
    ),
    LexiconEntry(
        op_id=0x3A, name="zip", band="AGGREGATION", chi=0.2, valence=2,
        trit=(0, +1, +1, +1, 0, +1),
        feat=(58, 4, 2, 2, 0.2, 3, 3, 0),
        code={
            "KO": "list(zip({xs}, {ys}))",
            "AV": "{xs}.map((x, i) => [x, {ys}[i]])",
            "RU": "{xs}.iter().zip({ys}.iter()).collect::<Vec<_>>()",
            "CA": "for(int i=0;i<n;i++) out[i]={{.a={xs}[i],.b={ys}[i]}};",
            "UM": "collect(zip({xs}, {ys}))",
            "DR": "(zip {xs} {ys})",
        },
    ),
    LexiconEntry(
        op_id=0x3B, name="unzip", band="AGGREGATION", chi=0.3, valence=1,
        trit=(0, +1, +1, +1, 0, -1),
        feat=(59, 4, 2, 2, 0.3, 3, 3, 0),
        note="DR=-1: splits structure",
        code={
            "KO": "list(zip(*{pairs}))",
            "AV": "[{pairs}.map(p => p[0]), {pairs}.map(p => p[1])]",
            "RU": "{pairs}.iter().cloned().unzip::<Vec<_>, Vec<_>>()",
            "CA": "for(int i=0;i<n;i++) {{ as[i]={pairs}[i].a; bs[i]={pairs}[i].b; }}",
            "UM": "collect.(zip({pairs}...))",
            "DR": "(unzip {pairs})",
        },
    ),
    LexiconEntry(
        op_id=0x3C, name="sort", band="AGGREGATION", chi=0.2, valence=1,
        trit=(0, 0, +1, +1, 0, +1),
        feat=(60, 4, 2, 1, 0.2, 3, 3, 0),
        code={
            "KO": "sorted({xs})",
            "AV": "[...{xs}].sort((a, b) => a - b)",
            "RU": "{{ let mut v = {xs}.to_vec(); v.sort(); v }}",
            "CA": "qsort({xs}, n, sizeof(*{xs}), cmp_int)",
            "UM": "sort({xs})",
            "DR": "(sort {xs})",
        },
    ),
    LexiconEntry(
        op_id=0x3D, name="unique", band="AGGREGATION", chi=0.3, valence=1,
        trit=(0, 0, +1, +1, 0, -1),
        feat=(61, 4, 2, 1, 0.3, 3, 3, 0),
        note="DR=-1: discards duplicates",
        code={
            "KO": "list(dict.fromkeys({xs}))",
            "AV": "[...new Set({xs})]",
            "RU": "{{ let mut v = {xs}.to_vec(); v.sort(); v.dedup(); v }}",
            "CA": "unique({xs}, n)",
            "UM": "unique({xs})",
            "DR": "(nub {xs})",
        },
    ),
    LexiconEntry(
        op_id=0x3E, name="count", band="AGGREGATION", chi=0.0, valence=1,
        trit=(0, +1, +1, +1, 0, 0),
        feat=(62, 4, 2, 1, 0.0, 3, 3, 0),
        code={
            "KO": "len({xs})",
            "AV": "{xs}.length",
            "RU": "{xs}.len()",
            "CA": "n",
            "UM": "length({xs})",
            "DR": "(length {xs})",
        },
    ),
    LexiconEntry(
        op_id=0x3F, name="accum", band="AGGREGATION", chi=0.4, valence=2,
        trit=(0, 0, +1, +1, 0, 0),
        feat=(63, 4, 3, 2, 0.4, 3, 3, 0),
        note="stateful accumulator",
        code={
            "KO": "{acc} += {val}",
            "AV": "{acc} += {val}",
            "RU": "*{acc} += {val}",
            "CA": "{acc} += {val}",
            "UM": "{acc} += {val}",
            "DR": "(modify (+ {val}) {acc})",
        },
    ),
]


# ─── Assembled lexicon ───────────────────────────────────────────────────

LEXICON: Dict[int, LexiconEntry] = {}
LEXICON_BY_NAME: Dict[str, LexiconEntry] = {}

for _band in [_ARITHMETIC, _LOGIC, _COMPARISON, _AGGREGATION]:
    for entry in _band:
        LEXICON[entry.op_id] = entry
        LEXICON_BY_NAME[entry.name] = entry


# ─── API ─────────────────────────────────────────────────────────────────

def lookup(name_or_id) -> LexiconEntry:
    """Look up by name (str) or op_id (int)."""
    if isinstance(name_or_id, int):
        return LEXICON[name_or_id]
    return LEXICON_BY_NAME[name_or_id]


def emit_code(op_name: str, tongue: str, **kwargs) -> str:
    """Emit a code snippet for a given op in a given tongue.

    Usage:
        emit_code("div", "RU", a="x", b="y")
        → "x.checked_div(y).unwrap_or(i64::MAX)"

        emit_code("filter", "KO", xs="data", pred="is_valid")
        → "[x for x in data if is_valid(x)]"
    """
    entry = LEXICON_BY_NAME[op_name]
    template = entry.code[tongue]
    return template.format(**kwargs)


def emit_all_tongues(op_name: str, **kwargs) -> Dict[str, str]:
    """Emit code for all 6 tongues at once. Same substrate, six outputs."""
    return {t: emit_code(op_name, t, **kwargs) for t in TONGUE_NAMES}


def trit_vector(op_name: str) -> np.ndarray:
    """Get the 6-channel trit vector for an op."""
    return np.array(LEXICON_BY_NAME[op_name].trit, dtype=np.int8)


def feature_vector(op_name: str) -> np.ndarray:
    """Get the 8-dim atomic feature vector for an op."""
    return np.array(LEXICON_BY_NAME[op_name].feat, dtype=np.float32)


# ─── Validation + demo ──────────────────────────────────────────────────

def validate():
    errors = []
    if len(LEXICON) != 64:
        errors.append(f"Expected 64 entries, got {len(LEXICON)}")
    ids = sorted(LEXICON.keys())
    if ids != list(range(64)):
        errors.append(f"ID range broken")
    for eid, entry in LEXICON.items():
        if entry.trit[3] != 1:
            errors.append(f"{entry.name}: CA channel must be +1")
        if len(entry.code) != 6:
            errors.append(f"{entry.name}: needs 6 language snippets, got {len(entry.code)}")
        for tongue in TONGUE_NAMES:
            if tongue not in entry.code:
                errors.append(f"{entry.name}: missing {tongue} snippet")
    if errors:
        print(f"FAILED ({len(errors)} errors):")
        for e in errors:
            print(f"  ✗ {e}")
        return False
    print(f"PASSED: 64 ops × 6 languages = 384 code snippets, all present")
    return True


def demo():
    print("=== Unified Lexicon Demo ===\n")
    print("--- div across all 6 tongues ---")
    results = emit_all_tongues("div", a="x", b="y")
    for tongue, code in results.items():
        lang = LANG_MAP[tongue]
        print(f"  {tongue} ({lang:>10}): {code}")

    print("\n--- filter across all 6 tongues ---")
    results = emit_all_tongues("filter", xs="data", pred="is_valid")
    for tongue, code in results.items():
        lang = LANG_MAP[tongue]
        print(f"  {tongue} ({lang:>10}): {code}")

    print(f"\n--- trit vector for 'xor' ---")
    print(f"  {trit_vector('xor')}")
    print(f"  note: {lookup('xor').note}")

    print(f"\n--- feature vector for 'reduce' ---")
    print(f"  {feature_vector('reduce')}")
    print(f"  chi={lookup('reduce').chi}, valence={lookup('reduce').valence}")


# ─── Extended Tongues: Go (CA secondary), Zig (RU secondary) ────────────

_GO_OVERRIDES: Dict[str, str] = {
    "div": "func() int64 {{ if {b} != 0 {{ return {a} / {b} }}; return math.MaxInt64 }}()",
    "pow": "math.Pow(float64({a}), float64({b}))",
    "sqrt": "math.Sqrt(float64({a}))",
    "log": "math.Log(float64({a}))",
    "exp": "math.Exp(float64({a}))",
    "abs": "int64(math.Abs(float64({a})))",
    "ceil": "int64(math.Ceil(float64({a})))",
    "floor": "int64(math.Floor(float64({a})))",
    "round": "int64(math.Round(float64({a})))",
}

_ZI_OVERRIDES: Dict[str, str] = {
    "add": "({a} +% {b})",
    "sub": "({a} -% {b})",
    "mul": "({a} *% {b})",
    "div": "@divTrunc({a}, {b})",
    "mod": "@rem({a}, {b})",
    "pow": "std.math.powi({a}, {b})",
    "sqrt": "@sqrt(@as(f64, {a}))",
    "abs": "if ({a} < 0) -({a}) else {a}",
    "neg": "-({a})",
}


def emit_extended(op_name: str, tongue: str, **kwargs) -> str:
    """Emit code for an extended tongue (GO, ZI) by override or parent passthrough."""
    if tongue not in EXTENDED_TONGUE_NAMES:
        raise ValueError(f"not an extended tongue: {tongue}")
    overrides = _GO_OVERRIDES if tongue == "GO" else _ZI_OVERRIDES
    if op_name in overrides:
        return overrides[op_name].format(**kwargs)
    return emit_code(op_name, TONGUE_PARENT[tongue], **kwargs)


def emit_all_tongues_extended(op_name: str, **kwargs) -> Dict[str, str]:
    """Emit code for all 8 tongues (6 primary + 2 extended)."""
    result = emit_all_tongues(op_name, **kwargs)
    for t in EXTENDED_TONGUE_NAMES:
        result[t] = emit_extended(op_name, t, **kwargs)
    return result


if __name__ == "__main__":
    ok = validate()
    if ok:
        demo()