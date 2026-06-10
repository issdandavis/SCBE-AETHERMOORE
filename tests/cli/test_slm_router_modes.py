"""Auto / manual / hybrid mode tests for the SLM router.

These tests cover the three operating regimes:

  * AUTO: SLM picks every unsupplied stage. Default behaviour, what the
    earlier suites already covered.
  * MANUAL: SLM is never called. Every stage must be pinned by the
    caller; a missing pin raises ManualModeError.
  * Hybrid: AUTO mode with one or more stages pinned. SLM only fills
    the gaps. This is the workhorse pattern for agentic loops where
    a higher tier already knows the op semantically but wants to
    explore tongue choice.

Plus the contract surface around mode coercion + lexicon-pin validation.
"""

from __future__ import annotations

from typing import Sequence

import pytest

from src.cli.cross_build_ir import emit_from_ir
from src.cli.slm_router import (
    ClassificationFailure,
    LatticeRouter,
    ManualModeError,
    Mode,
    QuarantineError,
    StubSLMAdapter,
)

_BAND_SET = frozenset({"ARITHMETIC", "LOGIC", "COMPARISON", "AGGREGATION", "NONE"})
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
_TONGUE_SET = frozenset({"KO", "AV", "RU", "CA", "UM", "DR"})


def _stub_for_add() -> StubSLMAdapter:
    return StubSLMAdapter(
        scripted_by_choice_set={
            _BAND_SET: ("ARITHMETIC", 0.99),
            _ARITH_OPS: ("add", 0.99),
            _TONGUE_SET: ("KO", 0.99),
        }
    )


class _RecordingAdapter:
    """Adapter that fails the test if it gets called. Use this to prove
    manual mode skips the SLM entirely."""

    def __init__(self) -> None:
        self.call_count = 0

    def classify(self, prompt: str, choices: Sequence[str]):
        self.call_count += 1
        raise AssertionError(f"adapter must not be called; got prompt={prompt[:60]!r}")


# ---------------------------------------------------------------------------
#  Mode coercion — accepts enum, lowercase string, or None default
# ---------------------------------------------------------------------------


def test_mode_coerce_from_enum() -> None:
    assert Mode.coerce(Mode.AUTO) is Mode.AUTO
    assert Mode.coerce(Mode.MANUAL) is Mode.MANUAL


def test_mode_coerce_from_string() -> None:
    assert Mode.coerce("auto") is Mode.AUTO
    assert Mode.coerce("manual") is Mode.MANUAL
    assert Mode.coerce("AUTO") is Mode.AUTO  # case-insensitive
    assert Mode.coerce("Manual") is Mode.MANUAL


def test_mode_coerce_none_defaults_to_auto() -> None:
    assert Mode.coerce(None) is Mode.AUTO


def test_mode_coerce_unknown_raises_quarantine() -> None:
    with pytest.raises(ManualModeError, match="unknown routing mode"):
        Mode.coerce("turbo")


def test_manual_mode_error_subclasses_quarantine() -> None:
    """A single `except QuarantineError` in the funnel must catch
    manual-mode contract violations."""
    assert issubclass(ManualModeError, QuarantineError)


# ---------------------------------------------------------------------------
#  Manual mode — caller pins everything, SLM never called
# ---------------------------------------------------------------------------


def test_manual_mode_with_op_and_tongue_pinned_skips_slm() -> None:
    """Full manual: op_name + dst_tongue pinned, SLM must not be invoked."""
    adapter = _RecordingAdapter()
    router = LatticeRouter(adapter)
    result = router.route(
        intent="anything",
        args={"a": "x", "b": "y"},
        op_name="add",
        dst_tongue="KO",
        mode=Mode.MANUAL,
    )
    assert adapter.call_count == 0
    assert result.op.op_name == "add"
    assert result.dst_tongue == "KO"
    # No confidences from SLM stages -> aggregate confidence defaults to 1.0
    assert result.confidence == pytest.approx(1.0)


def test_manual_mode_string_value_works_too() -> None:
    """Manual mode accessible via string `mode='manual'`, not just the enum."""
    adapter = _RecordingAdapter()
    router = LatticeRouter(adapter)
    result = router.route(
        intent="",
        args={"a": "x", "b": "y"},
        op_name="add",
        dst_tongue="RU",
        mode="manual",
    )
    assert adapter.call_count == 0
    assert emit_from_ir(result.op, result.dst_tongue) == "x.wrapping_add(y)"


def test_manual_mode_missing_op_name_raises() -> None:
    adapter = _RecordingAdapter()
    router = LatticeRouter(adapter)
    with pytest.raises(ManualModeError, match="op_name"):
        router.route(
            intent="",
            args={"a": "x", "b": "y"},
            dst_tongue="KO",
            mode=Mode.MANUAL,
        )


def test_manual_mode_missing_dst_tongue_raises() -> None:
    adapter = _RecordingAdapter()
    router = LatticeRouter(adapter)
    with pytest.raises(ManualModeError, match="dst_tongue"):
        router.route(
            intent="",
            args={"a": "x", "b": "y"},
            op_name="add",
            mode=Mode.MANUAL,
        )


def test_manual_mode_op_not_in_lexicon_raises() -> None:
    adapter = _RecordingAdapter()
    router = LatticeRouter(adapter)
    with pytest.raises(ManualModeError, match="not in the lexicon"):
        router.route(
            intent="",
            args={},
            op_name="transcend",  # not a real lexicon op
            dst_tongue="KO",
            mode=Mode.MANUAL,
        )


def test_manual_mode_count_now_routes_after_lexicon_close() -> None:
    """After the CA-tongue canonicalisation closed the sphere from 57→64,
    every op (including the previously-excluded `count`/`fold`/`mean`/`reduce`/
    `scan`/`stdev`/`variance`) routes in manual mode without quarantining.
    This test used to assert ManualModeError on `count`; the contract flipped
    once the lexicon's CA templates were canonicalised. Adapter is recording
    only — manual mode never invokes the SLM."""
    adapter = _RecordingAdapter()
    router = LatticeRouter(adapter)
    decision = router.route(
        intent="",
        args={"xs": "v"},
        op_name="count",
        dst_tongue="KO",
        mode=Mode.MANUAL,
    )
    assert decision.op.op_name == "count"
    assert decision.op.band == "AGGREGATION"
    assert decision.dst_tongue == "KO"
    assert adapter.call_count == 0, "manual mode must not consult the SLM"


# ---------------------------------------------------------------------------
#  Auto mode — current default behaviour preserved
# ---------------------------------------------------------------------------


def test_auto_mode_is_default_and_calls_slm() -> None:
    adapter = _stub_for_add()
    router = LatticeRouter(adapter)
    result = router.route("Add x and y", args={"a": "x", "b": "y"})
    # 3 SLM calls (band, op, tongue).
    assert len(adapter.calls) == 3
    assert result.op.op_name == "add"


def test_auto_mode_explicit_string_works() -> None:
    adapter = _stub_for_add()
    router = LatticeRouter(adapter)
    result = router.route("Add", args={"a": "x", "b": "y"}, mode="auto")
    assert result.op.op_name == "add"


# ---------------------------------------------------------------------------
#  Hybrid — AUTO mode with one or more stages pinned
# ---------------------------------------------------------------------------


def test_hybrid_pinned_op_skips_band_and_op_stages() -> None:
    """Pinning op_name in AUTO mode should let the SLM only handle
    the tongue stage (1 call), not all three."""
    adapter = _stub_for_add()
    router = LatticeRouter(adapter)
    result = router.route(
        "anything",
        args={"a": "x", "b": "y"},
        op_name="add",
        # dst_tongue not pinned -> SLM picks tongue
    )
    assert len(adapter.calls) == 1, f"expected 1 SLM call, got {len(adapter.calls)}"
    assert result.op.op_name == "add"
    assert result.dst_tongue == "KO"  # picked by SLM stub


def test_hybrid_pinned_band_only_skips_band_stage() -> None:
    """Pinning band but not op should make exactly 2 SLM calls (op + tongue)."""
    adapter = _stub_for_add()
    router = LatticeRouter(adapter)
    result = router.route(
        "Add",
        args={"a": "x", "b": "y"},
        band="ARITHMETIC",
    )
    assert len(adapter.calls) == 2
    assert result.op.op_name == "add"


def test_hybrid_pinned_op_and_tongue_no_slm_calls() -> None:
    """Pinning both op and tongue in AUTO mode is functionally the same
    as MANUAL mode — no SLM calls."""
    adapter = _RecordingAdapter()
    router = LatticeRouter(adapter)
    result = router.route(
        "anything",
        args={"a": "x", "b": "y"},
        op_name="sub",
        dst_tongue="DR",
    )
    assert adapter.call_count == 0
    assert result.op.op_name == "sub"
    assert emit_from_ir(result.op, "DR") == "(x - y)"


def test_hybrid_band_and_op_must_agree() -> None:
    """If caller pins both band and op, they must be consistent."""
    adapter = _RecordingAdapter()
    router = LatticeRouter(adapter)
    with pytest.raises(ManualModeError, match="disagrees"):
        router.route(
            "",
            args={"a": "x", "b": "y"},
            band="LOGIC",  # add is ARITHMETIC, not LOGIC
            op_name="add",
            dst_tongue="KO",
        )


def test_hybrid_band_pin_outside_lexicon_rejected() -> None:
    """Pinning a band that doesn't exist in the lexicon must be refused
    independently of any op pin."""
    adapter = _stub_for_add()
    router = LatticeRouter(adapter)
    with pytest.raises(ManualModeError, match="not in"):
        router.route(
            "",
            args={"a": "x", "b": "y"},
            band="TRANSCENDENT",  # made-up band, no op pin
            dst_tongue="KO",
        )


# ---------------------------------------------------------------------------
#  Reasoning trace shows pin provenance
# ---------------------------------------------------------------------------


def test_pinned_stages_appear_in_reasoning() -> None:
    """The reasoning trace must record which stages were pinned vs
    SLM-decided so audit logs are honest about provenance."""
    adapter = _stub_for_add()
    router = LatticeRouter(adapter)
    result = router.route(
        "anything",
        args={"a": "x", "b": "y"},
        op_name="add",
        dst_tongue="RU",
    )
    pinned_lines = [r for r in result.reasoning if "pinned" in r or "caller-supplied" in r]
    assert len(pinned_lines) == 3  # band-via-op, op, tongue
    assert any("band=pinned-via-op:ARITHMETIC" in r for r in pinned_lines)
    assert any("op=pinned:add" in r for r in pinned_lines)
    assert any("tongue=caller-supplied:RU" in r for r in pinned_lines)


# ---------------------------------------------------------------------------
#  Manual mode still respects loop detection + arg validation
# ---------------------------------------------------------------------------


def test_manual_mode_still_detects_loops() -> None:
    """Manual mode bypasses the SLM but NOT the loop-detection state."""
    from src.cli.slm_router import LoopDetected  # noqa: PLC0415

    adapter = _RecordingAdapter()
    router = LatticeRouter(adapter, loop_window=4)
    router.route("a", args={"a": "x", "b": "y"}, op_name="add", dst_tongue="KO", mode=Mode.MANUAL)
    with pytest.raises(LoopDetected):
        router.route("b", args={"a": "x", "b": "y"}, op_name="add", dst_tongue="KO", mode=Mode.MANUAL)


def test_manual_mode_still_runs_arg_validator() -> None:
    """Arg validator must run even when SLM is bypassed."""
    from src.cli.slm_router import ArgValidationFailure, _default_safe_arg_validator  # noqa: PLC0415

    adapter = _RecordingAdapter()
    router = LatticeRouter(adapter, arg_validator=_default_safe_arg_validator)
    with pytest.raises(ArgValidationFailure):
        router.route(
            "",
            args={"a": "x; rm -rf /", "b": "y"},
            op_name="add",
            dst_tongue="KO",
            mode=Mode.MANUAL,
        )


def test_manual_mode_still_validates_args_present() -> None:
    """Manual mode must still refuse if required args are missing."""
    adapter = _RecordingAdapter()
    router = LatticeRouter(adapter)
    with pytest.raises(ClassificationFailure, match="missing"):
        router.route(
            "",
            args={"a": "x"},  # missing 'b'
            op_name="add",
            dst_tongue="KO",
            mode=Mode.MANUAL,
        )
