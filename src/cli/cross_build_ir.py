"""Lattice IR for the bijective cross-build sphere — Tier 1 (lexicon-bounded).

The IR is one strict pydantic class. Every successful lift produces an
instance of *this* class regardless of source tongue; every successful
emit consumes the same class regardless of target tongue. That's the
"Closure" invariant in code form — there's no bipartite blob, no
tongue-pair-specific shape, just one shared object.

Tier 1 scope
------------
- Source code must be a rendered lexicon template (e.g. `"(x + y)"` for
  `add`, `"x.wrapping_add(y)"` for `add` in Runethic).
- Anything outside the 64-op CA Unified Multilingual Lexicon raises
  `QuarantineError`. No partial matching, no fuzzy fallback — funnel-bounded.

Tier 2 (deferred): arbitrary AST parsing via tree-sitter populating the
*same* `LatticeOp` schema. The schema is intentionally arity-agnostic so
Tier 2 can land without breaking Tier 1's tests.
"""

from __future__ import annotations

import re
import string
from typing import Dict, List, Mapping, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from src.ca_lexicon import (
    LANG_MAP,
    LEXICON_BY_NAME,
    TONGUE_NAMES,
    LexiconEntry,
)

# ---------------------------------------------------------------------------
#  Errors — all Quarantine-class so the funnel can pattern-match cleanly
# ---------------------------------------------------------------------------


class QuarantineError(Exception):
    """Base class for any lift/emit refusal in the cross-build sphere.

    The funnel filter catches this directly; the gate decides whether
    a quarantined value gets reviewed, dropped, or escalated.
    """


class LiftFailure(QuarantineError):
    """Source string did not match any lexicon op template for `tongue`."""


class EmitFailure(QuarantineError):
    """Target template requires bindings the IR doesn't carry."""


class AmbiguityError(QuarantineError):
    """Source matched more than one op template for the same tongue.

    Deterministic templates should not produce this; if it fires, the
    lexicon has a real collision that needs schema-level disambiguation.
    """


# ---------------------------------------------------------------------------
#  IR — one shared class, source-tongue-agnostic
# ---------------------------------------------------------------------------


class LatticeOp(BaseModel):
    """The center of the bijective sphere.

    Every leg of cross-build (any source -> any target) routes through
    a `LatticeOp`. The args dict carries template variable bindings; the
    op identity is provenance-free in the sense that two lifts of the
    same op from different source tongues produce equal `LatticeOp`s.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    op_name: str = Field(..., description="Lexicon op name, e.g. 'add'")
    op_id: int = Field(..., ge=0, lt=64, description="0x00..0x3F lexicon op id")
    band: str = Field(..., description="ARITHMETIC | LOGIC | COMPARISON | AGGREGATION")
    valence: int = Field(..., ge=0, description="number of operands")
    args: Dict[str, str] = Field(..., description="template-variable bindings")

    @classmethod
    def from_entry(cls, entry: LexiconEntry, args: Mapping[str, str]) -> "LatticeOp":
        return cls(
            op_name=entry.name,
            op_id=entry.op_id,
            band=entry.band,
            valence=entry.valence,
            args=dict(args),
        )


# ---------------------------------------------------------------------------
#  Template tooling — derive a regex that inverts `template.format(**args)`
# ---------------------------------------------------------------------------


_FORMATTER = string.Formatter()


def _parse_template_fragments(template: str) -> List[Tuple[str, Optional[str]]]:
    """Decompose a `str.format` template into (literal, field) chunks.

    Each chunk's literal precedes the field. The final chunk is a
    (literal, None) tail. This is the structure we need for both
    forward render and reverse regex construction.
    """
    fragments: List[Tuple[str, Optional[str]]] = []
    for literal, field, spec, conv in _FORMATTER.parse(template):
        # We do not use format spec or conversion in the lexicon, so refuse
        # them here so a future change shows up as a loud test failure.
        if spec or conv:
            raise ValueError(f"unsupported template feature in {template!r}")
        fragments.append((literal, field))
    return fragments


def _template_field_names(template: str) -> List[str]:
    return [field for _, field in _parse_template_fragments(template) if field]


# Tier 1 scope: arguments are atomic identifiers (variable names, simple
# literals). Nested expressions like `add(add(x, y), z)` belong in Tier 2,
# where a real parser unwraps composition before populating the IR. Pinning
# the placeholder pattern to identifier characters here eliminates a whole
# class of regex ambiguity (e.g. `bitmask` vs `shl` colliding when one's
# arg accidentally absorbs the other's operator).
_TIER1_ARG_PATTERN = r"[A-Za-z_][A-Za-z0-9_]*"


def _template_to_regex(template: str) -> re.Pattern:
    """Build an anchored regex that inverts `template.format(...)`.

    Field names become named capture groups. Repeated names are allowed —
    later occurrences are emitted as backreferences so e.g. `"({a}+{a})"`
    only matches `"(x+x)"`.
    """
    parts: List[str] = ["^"]
    seen_names: Dict[str, int] = {}
    for literal, field in _parse_template_fragments(template):
        if literal:
            parts.append(re.escape(literal))
        if field is None:
            continue
        if field in seen_names:
            seen_names[field] += 1
            parts.append(rf"(?P=__{field}_0)")
        else:
            seen_names[field] = 0
            parts.append(rf"(?P<__{field}_0>{_TIER1_ARG_PATTERN})")
    parts.append("$")
    return re.compile("".join(parts), flags=re.DOTALL)


def _named_groups_to_args(match: re.Match) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for key, value in match.groupdict().items():
        if key.startswith("__") and key.endswith("_0"):
            out[key[2:-2]] = value
    return out


# ---------------------------------------------------------------------------
#  Lift / emit — Tier 1 (lexicon-bounded)
# ---------------------------------------------------------------------------


def _normalise_tongue(tongue: str) -> str:
    t = tongue.upper()
    if t not in TONGUE_NAMES:
        raise QuarantineError(f"unknown tongue: {tongue!r}; valid: {TONGUE_NAMES}")
    return t


def lift_to_lattice(src_code: str, src_tongue: str) -> LatticeOp:
    """Lift a rendered lexicon snippet up into the lattice IR.

    Scans every lexicon op's template for `src_tongue` and finds the
    unique match. Raises `LiftFailure` for no match, `AmbiguityError`
    if two lexicon entries collide for this tongue.
    """
    tongue = _normalise_tongue(src_tongue)
    src = src_code.strip()
    matches: List[Tuple[LexiconEntry, Dict[str, str]]] = []
    for entry in LEXICON_BY_NAME.values():
        template = entry.code.get(tongue)
        if template is None:
            continue
        regex = _template_to_regex(template)
        m = regex.fullmatch(src)
        if not m:
            continue
        matches.append((entry, _named_groups_to_args(m)))

    if not matches:
        raise LiftFailure(f"no lexicon op template matched in tongue={tongue}: {src_code!r}")
    if len(matches) > 1:
        names = sorted(e.name for e, _ in matches)
        raise AmbiguityError(f"source matched multiple lexicon ops in tongue={tongue}: {names}")
    entry, args = matches[0]
    return LatticeOp.from_entry(entry, args)


def emit_from_ir(ir: LatticeOp, dst_tongue: str) -> str:
    """Render a `LatticeOp` into a lexicon snippet for `dst_tongue`.

    Raises `EmitFailure` if the destination template references args
    the IR doesn't carry — that's the contract that prevents partial
    translations from leaking into outputs.
    """
    tongue = _normalise_tongue(dst_tongue)
    entry = LEXICON_BY_NAME.get(ir.op_name)
    if entry is None:
        raise EmitFailure(f"unknown lexicon op in IR: {ir.op_name!r}")
    template = entry.code.get(tongue)
    if template is None:
        raise EmitFailure(f"op {ir.op_name!r} has no template for tongue={tongue}")

    needed = set(_template_field_names(template))
    missing = needed - set(ir.args.keys())
    if missing:
        raise EmitFailure(f"IR missing args for tongue={tongue} template: {sorted(missing)}")
    return template.format(**ir.args)


# ---------------------------------------------------------------------------
#  Cross-build — the public sphere operation
# ---------------------------------------------------------------------------


class CrossBuildResult(BaseModel):
    """The outward-facing return value of a successful cross-build."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    src_code: str
    src_tongue: str
    src_language: str
    dst_code: str
    dst_tongue: str
    dst_language: str
    ir: LatticeOp


def cross_build(src_code: str, src_tongue: str, dst_tongue: str) -> CrossBuildResult:
    """Tongue-A source -> lattice IR -> tongue-B source.

    Both legs must succeed for the result to surface. Any failure on
    either leg surfaces as `QuarantineError` (subtype-typed) so callers
    can route quarantines without string-matching messages.
    """
    src_t = _normalise_tongue(src_tongue)
    dst_t = _normalise_tongue(dst_tongue)
    ir = lift_to_lattice(src_code, src_t)
    dst_code = emit_from_ir(ir, dst_t)
    return CrossBuildResult(
        src_code=src_code,
        src_tongue=src_t,
        src_language=LANG_MAP[src_t],
        dst_code=dst_code,
        dst_tongue=dst_t,
        dst_language=LANG_MAP[dst_t],
        ir=ir,
    )


# ---------------------------------------------------------------------------
#  Tier 1 participating-ops allowlist
# ---------------------------------------------------------------------------
#
# All 64 lexicon ops now participate in the bijective sphere. The seven
# previously-excluded aggregation ops (count, fold, mean, reduce, scan,
# stdev, variance) had CA-tongue templates that dropped/renamed placeholders
# (e.g. `count` was bare `n`, `mean` used `{n}` instead of `{xs}`) and
# reduce/fold shared identical templates in RU + CA causing AmbiguityError.
# The lexicon was canonicalised so every tongue per op shares one
# placeholder set and reduce/fold are syntactically distinct.
TIER1_EXCLUDED_OPS: Tuple[str, ...] = ()


def _participating_ops() -> List[str]:
    return sorted(name for name in LEXICON_BY_NAME if name not in TIER1_EXCLUDED_OPS)


TIER1_PARTICIPATING_OPS: Tuple[str, ...] = tuple(_participating_ops())


__all__ = [
    "AmbiguityError",
    "CrossBuildResult",
    "EmitFailure",
    "LatticeOp",
    "LiftFailure",
    "QuarantineError",
    "TIER1_EXCLUDED_OPS",
    "TIER1_PARTICIPATING_OPS",
    "cross_build",
    "emit_from_ir",
    "lift_to_lattice",
]
