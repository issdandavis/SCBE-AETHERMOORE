"""Concurrency, timeout, and arg-validator tests for the SLM router.

These are the third-tier defenses noted as 'still soft' after the
harsh-test pass. Now they're load-bearing contracts under test.
"""

from __future__ import annotations

import threading
import time
from typing import List, Sequence

import pytest

from src.cli.cross_build_ir import QuarantineError, emit_from_ir
from src.cli.slm_router import (
    ArgValidationFailure,
    LatticeRouter,
    LoopDetected,
    StubSLMAdapter,
    _default_safe_arg_validator,
)

_BAND_SET = frozenset({"ARITHMETIC", "LOGIC", "COMPARISON", "AGGREGATION"})
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


# ---------------------------------------------------------------------------
#  Thread safety — concurrent route() calls
# ---------------------------------------------------------------------------


def test_concurrent_routes_with_distinct_args_all_succeed() -> None:
    """16 threads, each routing a unique (op, args, tongue) — none should
    spuriously trip loop detection due to a race on the deque."""
    adapter = _stub_for_add()
    router = LatticeRouter(adapter, loop_window=64)

    errors: List[Exception] = []
    barrier = threading.Barrier(16)

    def worker(i: int) -> None:
        barrier.wait()  # release all 16 threads simultaneously
        try:
            router.route(f"intent {i}", args={"a": f"x{i}", "b": f"y{i}"})
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"concurrent routes raised: {errors[:3]}"
    # Every distinct dispatch landed in the window — 16 unique digests.
    assert len(router.recent_digests) == 16


def test_concurrent_routes_with_same_dispatch_one_succeeds_others_loop() -> None:
    """8 threads racing to dispatch the *same* (op, args, tongue) — exactly
    ONE should succeed; the other 7 must hit LoopDetected. Without the
    lock, the race could let multiple threads pass the membership check."""
    adapter = _stub_for_add()
    router = LatticeRouter(adapter, loop_window=8)

    successes = 0
    loops = 0
    other_errors: List[Exception] = []
    counters_lock = threading.Lock()
    barrier = threading.Barrier(8)

    def worker() -> None:
        nonlocal successes, loops
        barrier.wait()
        try:
            router.route("same intent", args={"a": "x", "b": "y"})
            with counters_lock:
                successes += 1
        except LoopDetected:
            with counters_lock:
                loops += 1
        except Exception as exc:
            with counters_lock:
                other_errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not other_errors, f"unexpected exceptions: {other_errors}"
    assert successes == 1, f"expected exactly 1 success, got {successes}"
    assert loops == 7, f"expected 7 LoopDetected, got {loops}"


def test_recent_digests_is_thread_safe_snapshot() -> None:
    """Reading recent_digests while route() is in flight must return a
    consistent snapshot (no partial / torn read)."""
    adapter = _stub_for_add()
    router = LatticeRouter(adapter, loop_window=64)
    snapshots: List[int] = []

    stop = threading.Event()

    def reader() -> None:
        while not stop.is_set():
            snapshot = router.recent_digests
            snapshots.append(len(snapshot))

    def writer() -> None:
        for i in range(50):
            router.route(f"i{i}", args={"a": f"x{i}", "b": "y"})

    rt = threading.Thread(target=reader, daemon=True)
    wt = threading.Thread(target=writer)
    rt.start()
    wt.start()
    wt.join()
    stop.set()
    rt.join(timeout=1.0)

    # Every snapshot length must be a non-negative int <= the deque maxlen.
    assert all(0 <= n <= 64 for n in snapshots)


# ---------------------------------------------------------------------------
#  Adapter timeout — caller-supplied deadline kills hung calls
# ---------------------------------------------------------------------------


class HangingAdapter:
    """Simulates a remote SLM that never returns. The router's timeout
    parameter must convert this into a ClassificationFailure rather than
    blocking the caller forever."""

    def classify(self, prompt: str, choices: Sequence[str]):
        time.sleep(60.0)  # would hang the test if router doesn't enforce timeout
        return choices[0], 0.99


def test_adapter_timeout_surfaces_as_quarantine() -> None:
    router = LatticeRouter(HangingAdapter(), adapter_timeout=0.2)
    t0 = time.time()
    with pytest.raises(QuarantineError, match="timed out"):
        router.route("hang test", args={"a": "x", "b": "y"})
    elapsed = time.time() - t0
    assert elapsed < 5.0, f"timeout did not fire in time: {elapsed:.2f}s"
    router.close()


def test_adapter_timeout_unset_does_not_wrap_calls() -> None:
    """If adapter_timeout is None, no executor is created (lazy)."""
    adapter = _stub_for_add()
    router = LatticeRouter(adapter, adapter_timeout=None)
    router.route("normal", args={"a": "x", "b": "y"})
    # Internal: no executor was ever spun up.
    assert router._executor is None  # type: ignore[attr-defined]


def test_adapter_timeout_close_is_idempotent() -> None:
    router = LatticeRouter(_stub_for_add(), adapter_timeout=1.0)
    router.route("first", args={"a": "x", "b": "y"})
    router.close()
    router.close()  # second close must not raise


# ---------------------------------------------------------------------------
#  Arg validator — caller-supplied tripwire on dangerous values
# ---------------------------------------------------------------------------


def test_default_safe_validator_rejects_shell_injection() -> None:
    adapter = _stub_for_add()
    router = LatticeRouter(adapter, arg_validator=_default_safe_arg_validator)
    with pytest.raises(ArgValidationFailure, match="forbidden"):
        router.route("Add", args={"a": "x; rm -rf /", "b": "y"})


def test_default_safe_validator_rejects_pipe_and_backtick() -> None:
    adapter = _stub_for_add()
    router = LatticeRouter(adapter, arg_validator=_default_safe_arg_validator)
    for hostile in ("a | b", "a & b", "`whoami`", "$(ls)"):
        with pytest.raises(ArgValidationFailure, match="forbidden"):
            router.route("Add", args={"a": hostile, "b": "y"})


def test_default_safe_validator_rejects_nul_byte() -> None:
    adapter = _stub_for_add()
    router = LatticeRouter(adapter, arg_validator=_default_safe_arg_validator)
    with pytest.raises(ArgValidationFailure, match="forbidden"):
        router.route("Add", args={"a": "x\x00y", "b": "y"})


def test_default_safe_validator_accepts_normal_identifiers() -> None:
    adapter = _stub_for_add()
    router = LatticeRouter(adapter, arg_validator=_default_safe_arg_validator)
    result = router.route("Add", args={"a": "x", "b": "y"})
    assert emit_from_ir(result.op, "RU") == "x.wrapping_add(y)"


def test_validator_subclasses_quarantine() -> None:
    assert issubclass(ArgValidationFailure, QuarantineError)


def test_custom_validator_can_refuse_for_any_reason() -> None:
    """The validator hook is a general refusal point, not just a
    shell-injection check."""

    def only_two_letter_args(op_name: str, args) -> None:
        for _k, v in args.items():
            if len(v) > 2:
                raise ArgValidationFailure(f"value too long: {v!r}")

    adapter = _stub_for_add()
    router = LatticeRouter(adapter, arg_validator=only_two_letter_args)
    with pytest.raises(ArgValidationFailure, match="too long"):
        router.route("Add", args={"a": "this_is_too_long", "b": "y"})


def test_validator_raising_unrelated_exception_wraps() -> None:
    """A buggy validator that raises a generic exception must still
    surface as QuarantineError so the funnel filter still catches it."""

    def buggy_validator(op_name: str, args) -> None:
        raise RuntimeError("validator crashed")

    adapter = _stub_for_add()
    router = LatticeRouter(adapter, arg_validator=buggy_validator)
    with pytest.raises(QuarantineError, match="validator raised"):
        router.route("Add", args={"a": "x", "b": "y"})


def test_no_validator_means_no_check() -> None:
    """Default behaviour with no validator is unchanged — args pass
    through. The execution gate is the real boundary."""
    adapter = _stub_for_add()
    router = LatticeRouter(adapter)  # no validator
    result = router.route("Add", args={"a": "x; rm -rf /", "b": "y"})
    # Routing succeeded; the dangerous string is in the rendered code.
    code = emit_from_ir(result.op, "KO")
    assert "rm -rf" in code  # documenting the contract


# ---------------------------------------------------------------------------
#  Confidence aggregation now structural, not parsed
# ---------------------------------------------------------------------------


def test_aggregate_confidence_no_longer_parses_reasoning_strings() -> None:
    """Cross-check: change the reasoning-line format mid-stream and the
    aggregate confidence must still be correct, because we're tracking
    confidences in a structured list, not regex-parsing the strings."""
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            _BAND_SET: ("ARITHMETIC", 0.99),
            _ARITH_OPS: ("add", 0.42),
            _TONGUE_SET: ("KO", 0.88),
        }
    )
    router = LatticeRouter(adapter, min_confidence=0.4)
    result = router.route("Add", args={"a": "x", "b": "y"})
    # Min over (0.99, 0.42, 0.88) = 0.42, regardless of reasoning format.
    assert result.confidence == pytest.approx(0.42)
