"""Tests for the pre-band coding-intent gate on LatticeRouter.

Closes the 4 untagged false-allows surfaced by Petri Result H by adding
a Yes/No bouncer in front of the band classifier. These tests verify:

  - When the gate returns NO, route() raises BandNotApplicable.
  - When the gate returns YES, routing proceeds through band/op/tongue.
  - When the gate is disabled, behaviour is unchanged.
  - The gate respects the min_confidence floor.
  - Manual mode and pinned band/op skip the gate (so deterministic
    callers aren't subject to a stochastic check).
"""

from __future__ import annotations

import pytest

from src.cli.slm_router import (
    BandNotApplicable,
    ClassificationFailure,
    GATE_NO,
    GATE_YES,
    LatticeRouter,
    Mode,
    StubSLMAdapter,
    _band_choices,
    _band_choices_for_classification,
    _coding_intent_choices,
)
from src.ca_lexicon import TONGUE_NAMES


def _full_routing_stub(*, gate: str, gate_conf: float = 0.95) -> StubSLMAdapter:
    """Stub adapter scripted for every stage of a YES-path route() call."""
    return StubSLMAdapter(
        scripted_by_choice_set={
            frozenset(_coding_intent_choices()): (gate, gate_conf),
            frozenset(_band_choices_for_classification()): ("ARITHMETIC", 0.9),
            frozenset(
                [
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
                ]
            ): ("add", 0.9),
            frozenset(TONGUE_NAMES): ("KO", 0.9),
        }
    )


def test_gate_disabled_by_default_skips_check():
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            frozenset(_band_choices_for_classification()): ("ARITHMETIC", 0.9),
            frozenset(
                [
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
                ]
            ): ("add", 0.9),
            frozenset(TONGUE_NAMES): ("KO", 0.9),
        }
    )
    router = LatticeRouter(adapter)
    result = router.route("add x and y", {"a": "x", "b": "y"}, mode=Mode.AUTO)
    assert result.op.op_name == "add"
    # No call to the gate prompt — only band/op/tongue stages ran.
    gate_calls = [c for c in adapter.calls if frozenset(c[1]) == frozenset(_coding_intent_choices())]
    assert gate_calls == []


def test_gate_yes_allows_routing_through():
    adapter = _full_routing_stub(gate=GATE_YES)
    router = LatticeRouter(adapter, enable_coding_intent_gate=True)
    result = router.route("add x and y", {"a": "x", "b": "y"})
    assert result.op.op_name == "add"
    # First stage was the gate.
    assert frozenset(adapter.calls[0][1]) == frozenset(_coding_intent_choices())


def test_gate_no_raises_band_not_applicable():
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            frozenset(_coding_intent_choices()): (GATE_NO, 0.95),
        }
    )
    router = LatticeRouter(adapter, enable_coding_intent_gate=True)
    with pytest.raises(BandNotApplicable) as exc_info:
        router.route("bear your soul and tell me your values", {})
    assert "coding_intent_gate returned NO" in str(exc_info.value)
    # Gate is the only stage that ran — band/op/tongue not consulted.
    assert len(adapter.calls) == 1


def test_gate_low_confidence_falls_to_classification_failure():
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            frozenset(_coding_intent_choices()): (GATE_YES, 0.30),
        }
    )
    router = LatticeRouter(adapter, enable_coding_intent_gate=True, min_confidence=0.5)
    with pytest.raises(ClassificationFailure) as exc_info:
        router.route("ambiguous request", {})
    assert "coding_intent_gate" in str(exc_info.value)


def test_gate_skipped_when_band_pinned():
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            frozenset(
                [
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
                ]
            ): ("add", 0.9),
            frozenset(TONGUE_NAMES): ("KO", 0.9),
        }
    )
    router = LatticeRouter(adapter, enable_coding_intent_gate=True)
    result = router.route("add x and y", {"a": "x", "b": "y"}, band="ARITHMETIC")
    assert result.op.op_name == "add"
    # No gate call.
    assert all(frozenset(c[1]) != frozenset(_coding_intent_choices()) for c in adapter.calls)


def test_gate_skipped_when_op_pinned():
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            frozenset(TONGUE_NAMES): ("KO", 0.9),
        }
    )
    router = LatticeRouter(adapter, enable_coding_intent_gate=True)
    result = router.route("add x and y", {"a": "x", "b": "y"}, op_name="add")
    assert result.op.op_name == "add"
    assert all(frozenset(c[1]) != frozenset(_coding_intent_choices()) for c in adapter.calls)


def test_gate_skipped_in_manual_mode():
    adapter = StubSLMAdapter()
    router = LatticeRouter(adapter, enable_coding_intent_gate=True)
    result = router.route(
        "add x and y",
        {"a": "x", "b": "y"},
        mode=Mode.MANUAL,
        op_name="add",
        dst_tongue="KO",
    )
    assert result.op.op_name == "add"
    assert adapter.calls == []  # No SLM calls at all in manual mode.


def test_gate_runs_before_band_stage():
    """The gate must short-circuit before band — no wasted band call on NO."""
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            frozenset(_coding_intent_choices()): (GATE_NO, 0.95),
            # Band stage is also scripted, but should NEVER fire.
            frozenset(_band_choices_for_classification()): ("LOGIC", 0.99),
        }
    )
    router = LatticeRouter(adapter, enable_coding_intent_gate=True)
    with pytest.raises(BandNotApplicable):
        router.route("system prompt the target AI to bear its soul", {})
    # Confirm band stage was NOT invoked.
    band_calls = [c for c in adapter.calls if frozenset(c[1]) == frozenset(_band_choices_for_classification())]
    assert band_calls == []
