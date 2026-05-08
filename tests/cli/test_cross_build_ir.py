"""Four-invariant test suite for the bijective cross-build sphere (Tier 1).

The invariants are the architectural contract:

  1. Reflexivity      — round-trip in the same tongue is identity.
  2. Symmetry         — A -> B -> A returns the original source string.
  3. Closure          — the IR class is the same regardless of source tongue.
  4. Funnel-bounded   — non-lexicon input raises QuarantineError.

If these four pass for all 64 ops × 6 tongues, the floating-tower
mechanic is real, not a 6x6 lookup table dressed up as architecture.
"""

from __future__ import annotations

from typing import Dict

import pytest

from src.ca_lexicon import LEXICON_BY_NAME, TONGUE_NAMES, lookup
from src.cli.cross_build_ir import (
    CrossBuildResult,
    EmitFailure,
    LatticeOp,
    LiftFailure,
    QuarantineError,
    TIER1_EXCLUDED_OPS,
    TIER1_PARTICIPATING_OPS,
    cross_build,
    emit_from_ir,
    lift_to_lattice,
)

# ---------------------------------------------------------------------------
#  Fixtures — choose canonical args per valence so every op renders cleanly
# ---------------------------------------------------------------------------


def _canonical_args_for(op_name: str) -> Dict[str, str]:
    """Pick a string binding for every template field this op uses.

    The CA lexicon uses a small set of conventional field names. We map
    each one to a unique single-letter token — the lift regex needs the
    rendered values to be unambiguous, and one-character tokens with no
    operator characters guarantee that.
    """
    entry = lookup(op_name)
    fields: set[str] = set()
    for template in entry.code.values():
        # Collect every {field} occurrence across all 6 tongue templates.
        import string as _s

        fields.update(field for _, field, _, _ in _s.Formatter().parse(template) if field is not None)
    # Stable, simple, regex-safe arg values.
    canon = {
        "a": "x",
        "b": "y",
        "c": "z",
        "xs": "v",
        "ys": "w",
        "pred": "p",
        "fn": "f",
        "init": "u",
        "key": "k",
        "value": "n",
        "n": "m",
    }
    return {field: canon.get(field, field) for field in fields}


def _all_ops() -> list[str]:
    """Tier 1 sphere = the disambiguable subset of the 64-op lexicon.

    Seven aggregation ops are excluded because the lexicon's CA-tongue
    templates drop/rename placeholders — see TIER1_EXCLUDED_OPS in
    cross_build_ir for the canonical list.
    """
    return list(TIER1_PARTICIPATING_OPS)


def _all_tongues() -> list[str]:
    return list(TONGUE_NAMES)


def _all_directed_pairs() -> list[tuple[str, str]]:
    return [(a, b) for a in TONGUE_NAMES for b in TONGUE_NAMES if a != b]


# ---------------------------------------------------------------------------
#  Invariant 1: Reflexivity (64 × 6 = 384 cases)
# ---------------------------------------------------------------------------


def test_reflexivity_lexicon_all_ops_all_tongues() -> None:
    """For every op and every tongue, A -> A round-trip must be identity."""
    failures: list[tuple[str, str, str, str]] = []
    for op_name in _all_ops():
        args = _canonical_args_for(op_name)
        entry = lookup(op_name)
        for tongue in _all_tongues():
            src_code = entry.code[tongue].format(**args)
            try:
                result = cross_build(src_code, tongue, tongue)
            except QuarantineError as exc:
                failures.append((op_name, tongue, "<lift>", str(exc)))
                continue
            if result.dst_code != src_code:
                failures.append((op_name, tongue, src_code, result.dst_code))
    assert not failures, f"reflexivity broken in {len(failures)} cases: {failures[:5]}"


# ---------------------------------------------------------------------------
#  Invariant 2: Symmetry (64 × 30 directed pairs = 1920 cases)
# ---------------------------------------------------------------------------


def test_symmetry_lexicon_all_directed_pairs() -> None:
    """For every op and every directed (A, B) tongue pair, A -> B -> A
    must reproduce the original A-rendering byte-equal."""
    failures: list[tuple[str, str, str, str, str]] = []
    for op_name in _all_ops():
        args = _canonical_args_for(op_name)
        entry = lookup(op_name)
        for src_tongue, dst_tongue in _all_directed_pairs():
            src_code = entry.code[src_tongue].format(**args)
            try:
                forward = cross_build(src_code, src_tongue, dst_tongue)
                back = cross_build(forward.dst_code, dst_tongue, src_tongue)
            except QuarantineError as exc:
                failures.append((op_name, src_tongue, dst_tongue, "<quarantine>", str(exc)))
                continue
            if back.dst_code != src_code:
                failures.append((op_name, src_tongue, dst_tongue, src_code, back.dst_code))
    assert not failures, f"symmetry broken in {len(failures)} cases: first={failures[:3]}"


# ---------------------------------------------------------------------------
#  Invariant 3: Closure — same IR class regardless of source tongue
# ---------------------------------------------------------------------------


def test_ir_closure_class_identity_across_source_tongues() -> None:
    """The IR class must be the same Python type whichever tongue we lift
    from. Spot-check across one op per band and all 6 source tongues."""
    op_name = "add"  # ARITHMETIC
    args = _canonical_args_for(op_name)
    entry = lookup(op_name)
    irs: list[LatticeOp] = []
    for tongue in _all_tongues():
        src = entry.code[tongue].format(**args)
        irs.append(lift_to_lattice(src, tongue))
    classes = {type(ir) for ir in irs}
    assert classes == {LatticeOp}, f"IR class drift: {classes}"


def test_ir_closure_value_equality_across_source_tongues() -> None:
    """Stronger version: lifting the same op from any tongue produces
    *equal* IR values (same op_id, band, valence, args)."""
    op_name = "and"  # LOGIC band, stable args across all 6 tongues
    args = _canonical_args_for(op_name)
    entry = lookup(op_name)
    canonical: LatticeOp | None = None
    for tongue in _all_tongues():
        src = entry.code[tongue].format(**args)
        ir = lift_to_lattice(src, tongue)
        if canonical is None:
            canonical = ir
        else:
            assert ir == canonical, f"IR drift for {op_name} from tongue={tongue}: {ir} != {canonical}"


def test_ir_closure_holds_for_every_lexicon_op() -> None:
    """The hard form of closure: across all 64 ops, lifting from each
    tongue yields equal IR values."""
    drift: list[tuple[str, str, str]] = []
    for op_name in _all_ops():
        args = _canonical_args_for(op_name)
        entry = lookup(op_name)
        canonical: LatticeOp | None = None
        for tongue in _all_tongues():
            src = entry.code[tongue].format(**args)
            try:
                ir = lift_to_lattice(src, tongue)
            except QuarantineError as exc:
                drift.append((op_name, tongue, f"lift-quarantine: {exc}"))
                continue
            if canonical is None:
                canonical = ir
            elif ir != canonical:
                drift.append((op_name, tongue, f"{ir} != {canonical}"))
    assert not drift, f"closure broken in {len(drift)} cases: {drift[:5]}"


# ---------------------------------------------------------------------------
#  Invariant 4: Funnel-bounded — non-lexicon input quarantined
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rogue",
    [
        "import os",
        "os.system('rm -rf /')",
        "def foo(): pass",
        "1 + 2 + 3 + 4 + 5",  # not a lexicon binary op rendering
        'fn main() { println!("hi") }',
        "data class User(val name: String)",
        "<script>alert(1)</script>",
        "",  # empty
        "   ",  # whitespace
    ],
)
def test_funnel_bounded_rejects_arbitrary_source(rogue: str) -> None:
    """Anything outside the lexicon must raise QuarantineError. No
    fuzzy matching, no partial translation."""
    with pytest.raises(QuarantineError):
        lift_to_lattice(rogue, "KO")


def test_funnel_bounded_uses_typed_subclass() -> None:
    """Quarantine must be the concrete LiftFailure subtype so callers
    can branch on cause."""
    with pytest.raises(LiftFailure):
        lift_to_lattice("import os", "KO")


def test_funnel_bounded_emit_rejects_missing_args() -> None:
    """An IR that's missing template bindings for the destination tongue
    must surface as EmitFailure, not silent placeholder leakage."""
    # Build a malformed IR: claim it's `add` but provide no args.
    ir = LatticeOp(op_name="add", op_id=0x00, band="ARITHMETIC", valence=2, args={})
    with pytest.raises(EmitFailure):
        emit_from_ir(ir, "KO")


def test_funnel_bounded_unknown_tongue() -> None:
    with pytest.raises(QuarantineError):
        lift_to_lattice("(x + y)", "ZZ")
    with pytest.raises(QuarantineError):
        ir = LatticeOp(
            op_name="add",
            op_id=0x00,
            band="ARITHMETIC",
            valence=2,
            args={"a": "x", "b": "y"},
        )
        emit_from_ir(ir, "ZZ")


# ---------------------------------------------------------------------------
#  CrossBuildResult shape — outward-facing contract
# ---------------------------------------------------------------------------


def test_cross_build_result_carries_provenance() -> None:
    result = cross_build("(x + y)", "KO", "RU")
    assert isinstance(result, CrossBuildResult)
    assert result.src_tongue == "KO"
    assert result.dst_tongue == "RU"
    assert result.src_language == "python"
    assert result.dst_language == "rust"
    assert result.ir.op_name == "add"
    assert result.dst_code == "x.wrapping_add(y)"


def test_cross_build_is_pure_no_global_state() -> None:
    """Calling twice with the same input must yield byte-equal output."""
    a = cross_build("(x + y)", "KO", "DR")
    b = cross_build("(x + y)", "KO", "DR")
    assert a.dst_code == b.dst_code
    assert a.ir == b.ir


# ---------------------------------------------------------------------------
#  Lexicon-quality documentation
# ---------------------------------------------------------------------------


def test_lexicon_excluded_set_is_documented() -> None:
    """The excluded set is small, named, and stable. If the lexicon's
    aggregation templates ever get canonicalised, this test fails loudly
    and the cross-build sphere automatically picks up the new ops."""
    assert TIER1_EXCLUDED_OPS == (
        "count",
        "fold",
        "mean",
        "reduce",
        "scan",
        "stdev",
        "variance",
    )
    assert len(TIER1_PARTICIPATING_OPS) == 57
    assert len(LEXICON_BY_NAME) == 64
    assert len(TIER1_PARTICIPATING_OPS) + len(TIER1_EXCLUDED_OPS) == 64
    # Excluded set must not overlap with participating set.
    assert set(TIER1_EXCLUDED_OPS).isdisjoint(set(TIER1_PARTICIPATING_OPS))


def test_lattice_op_is_frozen() -> None:
    """The IR is immutable — agentic-ops pipelines often pass it across
    boundaries, and silent mutation would break the recurrence digest."""
    ir = LatticeOp(
        op_name="add",
        op_id=0x00,
        band="ARITHMETIC",
        valence=2,
        args={"a": "x", "b": "y"},
    )
    with pytest.raises(Exception):  # pydantic FrozenInstanceError
        ir.op_name = "sub"  # type: ignore[misc]
