"""Tests for the Tier 1 SLM router.

The stub adapter scripts answers per choice-set, so we can drive the
router through every stage deterministically without a running Ollama
server. Three things under test:

  * the three-stage classification pipeline (band -> op -> tongue);
  * confidence-floor and out-of-set rejection;
  * loop detection over the recent-action window.
"""

from __future__ import annotations

from typing import Dict

import pytest

from src.cli.cross_build_ir import LatticeOp, QuarantineError, emit_from_ir
from src.cli.slm_router import (
    ClassificationFailure,
    LatticeRouter,
    LoopDetected,
    RoutingResult,
    StubSLMAdapter,
)

# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------


def _stub_for_add_to_python(confidence: float = 0.95) -> StubSLMAdapter:
    """Wire a stub that routes any 'add' intent to (ARITHMETIC, add, KO)."""
    return StubSLMAdapter(
        scripted_by_choice_set={
            frozenset({"ARITHMETIC", "LOGIC", "COMPARISON", "AGGREGATION", "NONE"}): (
                "ARITHMETIC",
                confidence,
            ),
            # 16 ARITHMETIC ops in Tier 1 (none excluded from arithmetic band).
            frozenset(
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
            ): ("add", confidence),
            frozenset({"KO", "AV", "RU", "CA", "UM", "DR"}): ("KO", confidence),
        }
    )


# ---------------------------------------------------------------------------
#  Happy path: three-stage classification produces a valid LatticeOp
# ---------------------------------------------------------------------------


def test_router_resolves_intent_to_lattice_op() -> None:
    adapter = _stub_for_add_to_python()
    router = LatticeRouter(adapter)
    result = router.route("Add x and y", args={"a": "x", "b": "y"})
    assert isinstance(result, RoutingResult)
    assert result.op.op_name == "add"
    assert result.op.args == {"a": "x", "b": "y"}
    assert result.dst_tongue == "KO"
    assert result.confidence == pytest.approx(0.95)


def test_router_emits_correct_code_when_combined_with_ir() -> None:
    """Smoke: the router output is a real LatticeOp the IR can emit."""
    adapter = _stub_for_add_to_python()
    router = LatticeRouter(adapter)
    result = router.route("Add x and y", args={"a": "x", "b": "y"})
    code = emit_from_ir(result.op, result.dst_tongue)
    assert code == "(x + y)"


def test_router_records_three_stage_reasoning() -> None:
    adapter = _stub_for_add_to_python()
    router = LatticeRouter(adapter)
    result = router.route("Add x and y", args={"a": "x", "b": "y"})
    assert len(result.reasoning) == 3
    assert any("band=ARITHMETIC" in line for line in result.reasoning)
    assert any("op=add" in line for line in result.reasoning)
    assert any("tongue=KO" in line for line in result.reasoning)


def test_router_skips_tongue_classification_when_caller_supplies_it() -> None:
    """If dst_tongue is given, the router should make exactly 2 SLM calls
    (band + op), not 3."""
    adapter = _stub_for_add_to_python()
    router = LatticeRouter(adapter)
    result = router.route("Add x and y", args={"a": "x", "b": "y"}, dst_tongue="RU")
    assert result.dst_tongue == "RU"
    # 2 SLM calls, not 3.
    assert len(adapter.calls) == 2


def test_router_caller_supplied_tongue_validated() -> None:
    adapter = _stub_for_add_to_python()
    router = LatticeRouter(adapter)
    with pytest.raises(ClassificationFailure, match="dst_tongue"):
        router.route("Add", args={"a": "x", "b": "y"}, dst_tongue="ZZ")


# ---------------------------------------------------------------------------
#  Confidence floor
# ---------------------------------------------------------------------------


def test_router_rejects_below_floor_confidence() -> None:
    adapter = _stub_for_add_to_python(confidence=0.30)
    router = LatticeRouter(adapter, min_confidence=0.5)
    with pytest.raises(ClassificationFailure, match="confidence"):
        router.route("Add x and y", args={"a": "x", "b": "y"})


def test_router_accepts_at_or_above_floor() -> None:
    """Boundary: confidence == floor should pass (>= contract)."""
    adapter = _stub_for_add_to_python(confidence=0.5)
    router = LatticeRouter(adapter, min_confidence=0.5)
    result = router.route("Add x and y", args={"a": "x", "b": "y"})
    assert result.confidence == pytest.approx(0.5)


def test_router_aggregate_confidence_is_minimum_across_stages() -> None:
    """If band is high-conf but op is low-conf, the aggregate must report
    the weakest link, not the average."""
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            frozenset({"ARITHMETIC", "LOGIC", "COMPARISON", "AGGREGATION", "NONE"}): (
                "ARITHMETIC",
                0.99,
            ),
            frozenset(
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
            ): ("add", 0.55),
            frozenset({"KO", "AV", "RU", "CA", "UM", "DR"}): ("KO", 0.95),
        }
    )
    router = LatticeRouter(adapter, min_confidence=0.5)
    result = router.route("Add x and y", args={"a": "x", "b": "y"})
    assert result.confidence == pytest.approx(0.55)


# ---------------------------------------------------------------------------
#  Out-of-set safety
# ---------------------------------------------------------------------------


def test_router_rejects_out_of_set_choice() -> None:
    """If the SLM returns a value outside the supplied choices, the router
    must refuse rather than dispatch a fabricated op."""
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            frozenset({"ARITHMETIC", "LOGIC", "COMPARISON", "AGGREGATION", "NONE"}): (
                "TRANSCENDENT",
                0.99,
            ),
        }
    )
    router = LatticeRouter(adapter)
    with pytest.raises(ClassificationFailure, match="not in choices"):
        router.route("Anything", args={})


# ---------------------------------------------------------------------------
#  Missing-args validation (confused-deputy guard)
# ---------------------------------------------------------------------------


def test_router_rejects_op_with_missing_args() -> None:
    """Even with high confidence, the router must refuse if the resolved
    op needs args the caller didn't supply."""
    adapter = _stub_for_add_to_python()
    router = LatticeRouter(adapter)
    with pytest.raises(ClassificationFailure, match="missing"):
        router.route("Add x and y", args={"a": "x"})  # missing 'b'


# ---------------------------------------------------------------------------
#  Loop detection
# ---------------------------------------------------------------------------


def test_router_detects_immediate_repeat() -> None:
    adapter = _stub_for_add_to_python()
    router = LatticeRouter(adapter, loop_window=5)
    router.route("Add", args={"a": "x", "b": "y"})
    with pytest.raises(LoopDetected, match="recent window"):
        router.route("Add again", args={"a": "x", "b": "y"})


def test_router_loop_window_only_holds_recent_actions() -> None:
    """An older identical action falls off the window and a repeat is
    permitted again."""
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            frozenset({"ARITHMETIC", "LOGIC", "COMPARISON", "AGGREGATION", "NONE"}): (
                "ARITHMETIC",
                0.95,
            ),
            frozenset(
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
            ): ("add", 0.95),
            frozenset({"KO", "AV", "RU", "CA", "UM", "DR"}): ("KO", 0.95),
        }
    )
    router = LatticeRouter(adapter, loop_window=2)
    # Action 1: add(x, y)
    router.route("first", args={"a": "x", "b": "y"})
    # Push two unrelated actions. We use distinct args so they have
    # distinct digests, while the (op, tongue) stay scripted as add/KO.
    router.route("second", args={"a": "p", "b": "q"})
    router.route("third", args={"a": "r", "b": "s"})
    # Now action 1's digest has been evicted from the window of 2.
    # Re-routing it should succeed.
    result = router.route("first again", args={"a": "x", "b": "y"})
    assert result.op.args == {"a": "x", "b": "y"}


def test_router_does_not_flag_same_op_to_different_tongue_as_loop() -> None:
    """Same op + same args + DIFFERENT dst tongue is a different action."""
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            frozenset({"ARITHMETIC", "LOGIC", "COMPARISON", "AGGREGATION", "NONE"}): (
                "ARITHMETIC",
                0.95,
            ),
            frozenset(
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
            ): ("add", 0.95),
        }
    )
    router = LatticeRouter(adapter)
    router.route("Add", args={"a": "x", "b": "y"}, dst_tongue="KO")
    # Same op + args, different tongue — not a loop.
    result = router.route("Add", args={"a": "x", "b": "y"}, dst_tongue="RU")
    assert result.dst_tongue == "RU"


def test_router_reset_history_clears_loop_state() -> None:
    adapter = _stub_for_add_to_python()
    router = LatticeRouter(adapter)
    router.route("Add", args={"a": "x", "b": "y"})
    router.reset_history()
    # Re-routing the same dispatch must succeed after reset.
    result = router.route("Add", args={"a": "x", "b": "y"})
    assert result.op.op_name == "add"


def test_router_recent_digests_exposes_state() -> None:
    adapter = _stub_for_add_to_python()
    router = LatticeRouter(adapter)
    router.route("Add", args={"a": "x", "b": "y"})
    digests = router.recent_digests
    assert len(digests) == 1
    assert all(len(d) == 64 for d in digests)  # SHA-256 hex


# ---------------------------------------------------------------------------
#  Cross-tier integration: router output -> emit_from_ir
# ---------------------------------------------------------------------------


def test_router_output_round_trips_through_all_six_tongues() -> None:
    """End-to-end: router picks add+KO+args, then emit_from_ir to all 6
    tongues produces valid lexicon code in every tongue."""
    adapter = _stub_for_add_to_python()
    router = LatticeRouter(adapter)
    result = router.route("Add", args={"a": "x", "b": "y"})
    expected = {
        "KO": "(x + y)",
        "AV": "(x + y)",
        "RU": "x.wrapping_add(y)",
        "CA": "(x + y)",
        "UM": "(x + y)",
        "DR": "(x + y)",
    }
    for tongue, want in expected.items():
        assert emit_from_ir(result.op, tongue) == want


# ---------------------------------------------------------------------------
#  Subclass relationship — funnel filter can catch all router refusals
# ---------------------------------------------------------------------------


def test_classification_failure_subclasses_quarantine() -> None:
    assert issubclass(ClassificationFailure, QuarantineError)


def test_loop_detected_subclasses_quarantine() -> None:
    assert issubclass(LoopDetected, QuarantineError)
