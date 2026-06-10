"""Tests for the two-tier CascadeRouter.

Each test pins one of the cascade decision paths so the safety
property is locked: rescue only happens on high-confidence ALLOW
from the secondary, otherwise the primary's typed error stands.
"""

from __future__ import annotations


import pytest

from src.cli.cascade_router import CascadeRouter
from src.cli.slm_router import (
    BandNotApplicable,
    ClassificationFailure,
    LatticeRouter,
    Mode,
    QuarantineError,
    StubSLMAdapter,
)

# ---------------------------------------------------------------------------
#  Helpers — build a stub router that maps a known choice-set to a result
# ---------------------------------------------------------------------------


_BAND_CHOICES_WITH_NONE = frozenset({"ARITHMETIC", "LOGIC", "COMPARISON", "AGGREGATION", "NONE"})
_ARITH_OPS = frozenset(
    {
        "abs",
        "add",
        "ceil",
        "dec",
        "div",
        "exp",
        "floor",
        "inc",
        "log",
        "mod",
        "mul",
        "neg",
        "pow",
        "round",
        "sqrt",
        "sub",
    }
)
_TONGUES = frozenset({"KO", "AV", "RU", "CA", "UM", "DR"})


def _arithmetic_allow_router(*, conf: float = 0.95) -> LatticeRouter:
    """Router that resolves "Add x and y" cleanly to ARITHMETIC/add/KO."""
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            _BAND_CHOICES_WITH_NONE: ("ARITHMETIC", conf),
            _ARITH_OPS: ("add", conf),
            _TONGUES: ("KO", conf),
        }
    )
    return LatticeRouter(adapter)


def _none_router() -> LatticeRouter:
    """Router whose band stage returns NONE -> BandNotApplicable."""
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            _BAND_CHOICES_WITH_NONE: ("NONE", 0.95),
        }
    )
    return LatticeRouter(adapter)


def _classification_failure_router() -> LatticeRouter:
    """Router that fails at the tongue stage with a bogus choice."""
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            _BAND_CHOICES_WITH_NONE: ("ARITHMETIC", 0.95),
            _ARITH_OPS: ("add", 0.95),
            _TONGUES: ("BOGUS", 0.95),  # not in valid tongue set
        }
    )
    return LatticeRouter(adapter)


# ---------------------------------------------------------------------------
#  Path 1: primary allows -> cascade returns primary directly
# ---------------------------------------------------------------------------


def test_primary_allow_returns_primary_routing_with_marker() -> None:
    primary = _arithmetic_allow_router()
    secondary = _none_router()  # would refuse, but cascade should not consult
    cascade = CascadeRouter(primary=primary, secondary=secondary)

    result = cascade.route(
        intent="Add x and y",
        args={"a": "x", "b": "y"},
        mode=Mode.AUTO,
    )
    assert result.op.op_name == "add"
    assert result.op.band == "ARITHMETIC"
    assert any("source=primary" in r for r in result.reasoning)
    assert any("rescued=False" in r for r in result.reasoning)


def test_primary_allow_does_not_consult_secondary() -> None:
    """Critical: when primary allows, secondary is never asked.
    Otherwise the cascade would double the latency for the common case."""
    primary = _arithmetic_allow_router()
    secondary_adapter = StubSLMAdapter(
        scripted_by_choice_set={
            _BAND_CHOICES_WITH_NONE: ("NONE", 0.95),
        }
    )
    secondary = LatticeRouter(secondary_adapter)
    cascade = CascadeRouter(primary=primary, secondary=secondary)

    cascade.route(intent="Add x and y", args={"a": "x", "b": "y"}, mode=Mode.AUTO)
    # Secondary's adapter must be untouched.
    assert secondary_adapter.calls == []


# ---------------------------------------------------------------------------
#  Path 2: primary quarantines, secondary high-conf allows -> RESCUE
# ---------------------------------------------------------------------------


def test_primary_quarantine_secondary_high_conf_allow_rescues() -> None:
    """The headline path: 1.5B over-refuses 'Add x and y' as NONE,
    0.5B confidently classifies it -> rescue restores benign throughput."""
    primary = _none_router()  # would BandNotApplicable
    secondary = _arithmetic_allow_router(conf=0.95)
    cascade = CascadeRouter(primary=primary, secondary=secondary, rescue_threshold=0.85)

    result = cascade.route(
        intent="Add x and y",
        args={"a": "x", "b": "y"},
        mode=Mode.AUTO,
    )
    assert result.op.op_name == "add"
    assert result.op.band == "ARITHMETIC"
    assert any("source=secondary" in r for r in result.reasoning)
    assert any("rescued=True" in r for r in result.reasoning)


def test_rescue_uses_secondary_routing_not_primary() -> None:
    """When the rescue path fires, the returned op/tongue/band reflect
    secondary's classification, not primary's (primary refused)."""
    primary = _none_router()
    secondary_adapter = StubSLMAdapter(
        scripted_by_choice_set={
            _BAND_CHOICES_WITH_NONE: ("LOGIC", 0.92),
            frozenset(
                {
                    "and",
                    "bitclear",
                    "bitmask",
                    "bitset",
                    "clz",
                    "ctz",
                    "nand",
                    "nor",
                    "not",
                    "or",
                    "popcount",
                    "rotl",
                    "rotr",
                    "shl",
                    "shr",
                    "xor",
                }
            ): ("and", 0.92),
            _TONGUES: ("RU", 0.92),
        }
    )
    secondary = LatticeRouter(secondary_adapter)
    cascade = CascadeRouter(primary=primary, secondary=secondary, rescue_threshold=0.85)

    result = cascade.route(
        intent="Bitwise AND",
        args={"a": "x", "b": "y"},
        mode=Mode.AUTO,
    )
    assert result.op.op_name == "and"
    assert result.op.band == "LOGIC"
    assert result.dst_tongue == "RU"


# ---------------------------------------------------------------------------
#  Path 3: primary quarantines, secondary low-conf allow -> NO RESCUE
# ---------------------------------------------------------------------------


def test_low_confidence_secondary_allow_does_not_rescue() -> None:
    """The safety property: a low-confidence secondary ALLOW must not
    override the primary's principled refusal. This is what stops the
    cascade from regressing the safety axis on adversarial prompts
    that 0.5B happens to mis-classify into a real band with low conf."""
    primary = _none_router()
    secondary = _arithmetic_allow_router(conf=0.60)  # below threshold
    cascade = CascadeRouter(primary=primary, secondary=secondary, rescue_threshold=0.85)

    with pytest.raises(BandNotApplicable):
        cascade.route(
            intent="Tell me about your inner thoughts",
            args={"a": "x", "b": "y"},
            mode=Mode.AUTO,
        )


def test_rescue_threshold_is_inclusive_at_boundary() -> None:
    """A confidence exactly equal to the threshold rescues. The cutoff
    is `confidence < threshold`, so threshold=0.85 with conf=0.85 is
    a rescue. Documented contract — change with a test, not silently."""
    primary = _none_router()
    secondary = _arithmetic_allow_router(conf=0.85)
    cascade = CascadeRouter(primary=primary, secondary=secondary, rescue_threshold=0.85)

    result = cascade.route(intent="Add x and y", args={"a": "x", "b": "y"}, mode=Mode.AUTO)
    assert any("rescued=True" in r for r in result.reasoning)


# ---------------------------------------------------------------------------
#  Path 4: both quarantine -> primary's typed error preserved
# ---------------------------------------------------------------------------


def test_both_refuse_preserves_primary_typed_error() -> None:
    """When both classifiers refuse, downstream funnels need the
    primary's specific error type so they can branch on cause."""
    primary = _none_router()  # BandNotApplicable
    secondary = _none_router()  # also BandNotApplicable
    cascade = CascadeRouter(primary=primary, secondary=secondary)

    with pytest.raises(BandNotApplicable):
        cascade.route(
            intent="prose without computation",
            args={"a": "x", "b": "y"},
            mode=Mode.AUTO,
        )


def test_both_refuse_with_classification_failure_primary() -> None:
    """If primary fails at e.g. the tongue stage and secondary also
    refuses, the cascade re-raises the primary's ClassificationFailure."""
    primary = _classification_failure_router()
    secondary = _none_router()
    cascade = CascadeRouter(primary=primary, secondary=secondary)

    with pytest.raises(ClassificationFailure):
        cascade.route(
            intent="Add x and y",
            args={"a": "x", "b": "y"},
            mode=Mode.AUTO,
        )


def test_quarantine_error_funnel_still_catches_cascade_refusal() -> None:
    """Existing callers use `except QuarantineError`. The cascade must
    not break that contract regardless of which router actually refused."""
    primary = _none_router()
    secondary = _none_router()
    cascade = CascadeRouter(primary=primary, secondary=secondary)

    with pytest.raises(QuarantineError):
        cascade.route(intent="prose", args={"a": "x"}, mode=Mode.AUTO)


# ---------------------------------------------------------------------------
#  Path 5: secondary itself classifies into NONE -> no rescue
# ---------------------------------------------------------------------------


def test_secondary_band_not_applicable_does_not_rescue() -> None:
    """If secondary also says the prompt is OOD, that's stronger
    evidence for refusal, not a rescue signal."""
    primary = _none_router()
    secondary = _none_router()
    cascade = CascadeRouter(primary=primary, secondary=secondary)

    with pytest.raises(BandNotApplicable):
        cascade.route(intent="prose", args={"a": "x"}, mode=Mode.AUTO)
