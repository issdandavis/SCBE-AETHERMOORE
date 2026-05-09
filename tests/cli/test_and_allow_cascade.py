"""Tests for AndAllowCascadeRouter.

The AND-of-allow contract:
  - ALLOW iff BOTH classifiers ALLOW
  - QUARANTINE if EITHER refuses
  - Primary refusal short-circuits (secondary not called)
  - On disagreement (primary ALLOW, secondary refuse), re-raise
    secondary's typed error -- it's the new information

Motivated by Petri Result G: different classifiers have different
blind spots. AND-of-allow composes the catches.
"""

from __future__ import annotations

import pytest

from src.cli.cascade_router import AndAllowCascadeRouter
from src.cli.slm_router import (
    BandNotApplicable,
    ClassificationFailure,
    LatticeRouter,
    Mode,
    QuarantineError,
    StubSLMAdapter,
)

# ---------------------------------------------------------------------------
#  Helpers — same shape as the cascade-router test fixtures
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
_LOGIC_OPS = frozenset(
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
)
_TONGUES = frozenset({"KO", "AV", "RU", "CA", "UM", "DR"})


def _arithmetic_allow_router(*, conf: float = 0.95) -> LatticeRouter:
    return LatticeRouter(
        StubSLMAdapter(
            scripted_by_choice_set={
                _BAND_CHOICES_WITH_NONE: ("ARITHMETIC", conf),
                _ARITH_OPS: ("add", conf),
                _TONGUES: ("KO", conf),
            }
        )
    )


def _logic_allow_router(*, conf: float = 0.95, op: str = "and", tongue: str = "RU") -> LatticeRouter:
    return LatticeRouter(
        StubSLMAdapter(
            scripted_by_choice_set={
                _BAND_CHOICES_WITH_NONE: ("LOGIC", conf),
                _LOGIC_OPS: (op, conf),
                _TONGUES: (tongue, conf),
            }
        )
    )


def _none_router() -> LatticeRouter:
    return LatticeRouter(
        StubSLMAdapter(
            scripted_by_choice_set={
                _BAND_CHOICES_WITH_NONE: ("NONE", 0.95),
            }
        )
    )


def _bogus_tongue_router() -> LatticeRouter:
    """ALLOWs band+op but fails at tongue stage with bogus choice."""
    return LatticeRouter(
        StubSLMAdapter(
            scripted_by_choice_set={
                _BAND_CHOICES_WITH_NONE: ("ARITHMETIC", 0.95),
                _ARITH_OPS: ("add", 0.95),
                _TONGUES: ("BOGUS", 0.95),
            }
        )
    )


# ---------------------------------------------------------------------------
#  Path 1: both ALLOW -> ALLOW with primary's routing
# ---------------------------------------------------------------------------


def test_both_allow_returns_primary_routing() -> None:
    primary = _arithmetic_allow_router()
    secondary = _arithmetic_allow_router()
    cascade = AndAllowCascadeRouter(primary=primary, secondary=secondary)

    result = cascade.route(intent="Add x and y", args={"a": "x", "b": "y"}, mode=Mode.AUTO)
    assert result.op.op_name == "add"
    assert result.op.band == "ARITHMETIC"
    assert result.dst_tongue == "KO"
    assert any("and_allow: both_agreed=True" in r for r in result.reasoning)


def test_both_allow_uses_primary_band_even_when_secondary_disagrees() -> None:
    """Both allow but classify differently. Primary's choice is the
    action surface; secondary's choice surfaces in the reasoning trail
    for diagnostic visibility but does NOT override the routing."""
    primary = _arithmetic_allow_router()
    secondary = _logic_allow_router()  # would route to LOGIC/and/RU
    cascade = AndAllowCascadeRouter(primary=primary, secondary=secondary)

    result = cascade.route(intent="ambiguous prompt", args={"a": "x", "b": "y"}, mode=Mode.AUTO)
    assert result.op.band == "ARITHMETIC"  # primary's choice
    assert result.op.op_name == "add"
    assert any("secondary_band=LOGIC" in r for r in result.reasoning)
    assert any("secondary_op=and" in r for r in result.reasoning)


# ---------------------------------------------------------------------------
#  Path 2: primary refuses -> short-circuit, secondary not called
# ---------------------------------------------------------------------------


def test_primary_refusal_short_circuits_does_not_call_secondary() -> None:
    """The latency property: when primary refuses, we already have
    QUARANTINE under the AND-of-allow contract. No need to call
    secondary; doing so would waste capacity for no information gain."""
    primary = _none_router()
    secondary_adapter = StubSLMAdapter(
        scripted_by_choice_set={
            _BAND_CHOICES_WITH_NONE: ("ARITHMETIC", 0.95),
            _ARITH_OPS: ("add", 0.95),
            _TONGUES: ("KO", 0.95),
        }
    )
    secondary = LatticeRouter(secondary_adapter)
    cascade = AndAllowCascadeRouter(primary=primary, secondary=secondary)

    with pytest.raises(BandNotApplicable):
        cascade.route(intent="prose", args={"a": "x"}, mode=Mode.AUTO)
    assert secondary_adapter.calls == [], "secondary must not be consulted"


def test_primary_refusal_preserves_primary_typed_error() -> None:
    primary = _bogus_tongue_router()  # primary fails ClassificationFailure
    secondary = _arithmetic_allow_router()  # would allow
    cascade = AndAllowCascadeRouter(primary=primary, secondary=secondary)

    with pytest.raises(ClassificationFailure):
        cascade.route(intent="Add x and y", args={"a": "x", "b": "y"}, mode=Mode.AUTO)


# ---------------------------------------------------------------------------
#  Path 3: primary ALLOWs, secondary refuses -> secondary's error wins
# ---------------------------------------------------------------------------


def test_secondary_refusal_after_primary_allow_raises_secondary_error() -> None:
    """When the classifiers disagree, secondary's error is the more
    informative signal -- it's the new information, primary already
    said allowable. The funnel should see secondary's typed reason."""
    primary = _arithmetic_allow_router()
    secondary = _none_router()  # BandNotApplicable
    cascade = AndAllowCascadeRouter(primary=primary, secondary=secondary)

    with pytest.raises(BandNotApplicable):
        cascade.route(intent="Add x and y", args={"a": "x", "b": "y"}, mode=Mode.AUTO)


def test_secondary_classification_failure_after_primary_allow() -> None:
    primary = _arithmetic_allow_router()
    secondary = _bogus_tongue_router()  # ClassificationFailure on tongue stage
    cascade = AndAllowCascadeRouter(primary=primary, secondary=secondary)

    with pytest.raises(ClassificationFailure):
        cascade.route(intent="Add x and y", args={"a": "x", "b": "y"}, mode=Mode.AUTO)


# ---------------------------------------------------------------------------
#  Funnel compatibility -- existing QuarantineError catches still work
# ---------------------------------------------------------------------------


def test_quarantine_error_funnel_catches_either_classifier_refusal() -> None:
    """Callers using `except QuarantineError` to handle gate refusal
    must not have to know which classifier actually refused."""
    # Case A: primary refuses
    primary_a = _none_router()
    secondary_a = _arithmetic_allow_router()
    cascade_a = AndAllowCascadeRouter(primary=primary_a, secondary=secondary_a)
    with pytest.raises(QuarantineError):
        cascade_a.route(intent="prose", args={"a": "x"}, mode=Mode.AUTO)

    # Case B: secondary refuses
    primary_b = _arithmetic_allow_router()
    secondary_b = _none_router()
    cascade_b = AndAllowCascadeRouter(primary=primary_b, secondary=secondary_b)
    with pytest.raises(QuarantineError):
        cascade_b.route(intent="ambiguous", args={"a": "x", "b": "y"}, mode=Mode.AUTO)


# ---------------------------------------------------------------------------
#  Diagnostic marker -- the reasoning trail must surface secondary's choice
# ---------------------------------------------------------------------------


def test_and_allow_marker_records_secondary_confidence() -> None:
    primary = _arithmetic_allow_router(conf=0.95)
    secondary = _arithmetic_allow_router(conf=0.72)
    cascade = AndAllowCascadeRouter(primary=primary, secondary=secondary)

    result = cascade.route(intent="Add x and y", args={"a": "x", "b": "y"}, mode=Mode.AUTO)
    # The marker captures secondary's confidence at 2 decimal places.
    assert any("secondary_conf=0.72" in r for r in result.reasoning)
