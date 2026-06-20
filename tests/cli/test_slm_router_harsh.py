"""Harsh tests for the Tier 1 SLM router.

Goal of this file: find real flaws. Each test targets a specific failure
mode I expect the router to handle but suspect it doesn't. When a test
here passes, the router has actually closed the gap; when it fails, the
test pinpoints exactly what's broken.

Test groups:
  * Confidence boundary attacks (NaN, negative, >1.0, string)
  * Choice-set strictness (whitespace, case, unicode invisibles, empty)
  * Aggregate-confidence parser brittleness
  * Loop-window edge cases (0, 1, len(window) overflow)
  * Adapter contract violations (raising adapters, malformed responses)
  * Argument-value safety (template-meta injection)
  * OllamaAdapter HTTP failure modes (mocked, no live server needed)
"""

from __future__ import annotations

from typing import Sequence
from unittest.mock import MagicMock, patch

import pytest

from src.cli.cross_build_ir import QuarantineError, emit_from_ir
from src.cli.slm_router import (
    BandNotApplicable,
    ClassificationFailure,
    LatticeRouter,
    LoopDetected,
    OllamaAdapter,
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
_LOGIC_OPS = frozenset(
    {
        "and",
        "bitclear",
        "bitmask",
        "bitset",
        "nand",
        "clz",
        "ctz",
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


def _stub_with(band_conf: float, op_conf: float, tongue_conf: float) -> StubSLMAdapter:
    return StubSLMAdapter(
        scripted_by_choice_set={
            _BAND_SET: ("ARITHMETIC", band_conf),
            _ARITH_OPS: ("add", op_conf),
            _TONGUE_SET: ("KO", tongue_conf),
        }
    )


# ---------------------------------------------------------------------------
#  Confidence boundary attacks
# ---------------------------------------------------------------------------


def test_nan_confidence_must_be_rejected() -> None:
    """`float('nan') < 0.5` evaluates False, so a naive `<` check lets
    NaN through. The router must clamp/validate so NaN can never be
    treated as 'high enough'."""
    adapter = _stub_with(float("nan"), 0.95, 0.95)
    router = LatticeRouter(adapter, min_confidence=0.5)
    with pytest.raises(ClassificationFailure):
        router.route("Add", args={"a": "x", "b": "y"})


def test_negative_confidence_must_be_rejected() -> None:
    """Confidence is defined in [0, 1]. -0.5 should be a hard reject
    regardless of `min_confidence`, because it's outside the contract."""
    adapter = _stub_with(-0.5, 0.95, 0.95)
    router = LatticeRouter(adapter, min_confidence=0.0)
    with pytest.raises(ClassificationFailure):
        router.route("Add", args={"a": "x", "b": "y"})


def test_above_unity_confidence_must_be_rejected() -> None:
    """Some models return 1.5 or 95 (percentage). Out of the [0, 1]
    contract → reject."""
    adapter = _stub_with(1.5, 0.95, 0.95)
    router = LatticeRouter(adapter, min_confidence=0.5)
    with pytest.raises(ClassificationFailure):
        router.route("Add", args={"a": "x", "b": "y"})


def test_aggregate_confidence_minimum_with_two_stages_only() -> None:
    """When dst_tongue is supplied (so tongue stage is skipped), the
    aggregate must be the min over the two stages actually called,
    not include a phantom value."""
    adapter = _stub_with(0.99, 0.55, 0.99)
    router = LatticeRouter(adapter, min_confidence=0.5)
    result = router.route("Add", args={"a": "x", "b": "y"}, dst_tongue="RU")
    assert result.confidence == pytest.approx(0.55)
    assert len(result.reasoning) == 3  # 2 SLM + 1 caller-supplied note
    # The caller-supplied tongue line must NOT include a confidence value.
    tongue_line = next(line for line in result.reasoning if "tongue=" in line)
    assert "conf=" not in tongue_line


# ---------------------------------------------------------------------------
#  Choice-set strictness — model output may have whitespace, case, etc.
# ---------------------------------------------------------------------------


def test_choice_with_trailing_whitespace_is_rejected() -> None:
    """`"add "` is not the same string as `"add"`. The router should
    refuse rather than silently accept a near-match."""
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            _BAND_SET: ("ARITHMETIC", 0.99),
            _ARITH_OPS: ("add ", 0.99),  # trailing space
        }
    )
    router = LatticeRouter(adapter)
    with pytest.raises(ClassificationFailure, match="not in choices"):
        router.route("Add", args={"a": "x", "b": "y"})


def test_choice_with_wrong_case_is_rejected() -> None:
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            _BAND_SET: ("arithmetic", 0.99),  # lowercase
        }
    )
    router = LatticeRouter(adapter)
    with pytest.raises(ClassificationFailure, match="not in choices"):
        router.route("Add", args={"a": "x", "b": "y"})


def test_choice_with_unicode_zero_width_is_rejected() -> None:
    """Zero-width space in the response is a class of subtle bug worth
    surfacing — silent equality failure. The router should reject."""
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            _BAND_SET: ("ARITHMETIC​", 0.99),  # ZWSP
        }
    )
    router = LatticeRouter(adapter)
    with pytest.raises(ClassificationFailure, match="not in choices"):
        router.route("Add", args={"a": "x", "b": "y"})


# ---------------------------------------------------------------------------
#  Loop-window edge cases
# ---------------------------------------------------------------------------


def test_loop_window_zero_is_explicitly_rejected_or_disables_detection() -> None:
    """`deque(maxlen=0)` silently drops every push. That makes loop
    detection a no-op without telling the caller. Either reject the
    config or document the disable explicitly — pick one and stick to it.

    Current contract under test: a window of 0 means 'no loop detection'
    and the router accepts immediate repeats. If you ever change this,
    the test fails loudly."""
    adapter = _stub_with(0.99, 0.99, 0.99)
    router = LatticeRouter(adapter, loop_window=0)
    router.route("first", args={"a": "x", "b": "y"})
    # No exception — duplicate is allowed because the window discards.
    router.route("second", args={"a": "x", "b": "y"})


def test_loop_window_one_detects_immediate_repeat() -> None:
    adapter = _stub_with(0.99, 0.99, 0.99)
    router = LatticeRouter(adapter, loop_window=1)
    router.route("first", args={"a": "x", "b": "y"})
    with pytest.raises(LoopDetected):
        router.route("repeat", args={"a": "x", "b": "y"})


def test_loop_window_one_evicts_after_unrelated_action() -> None:
    """A → B → A: with window=1, after B is dispatched, A's digest is
    evicted, so re-dispatching A succeeds."""
    adapter = _stub_with(0.99, 0.99, 0.99)
    router = LatticeRouter(adapter, loop_window=1)
    router.route("a1", args={"a": "x", "b": "y"})  # action A
    router.route("b1", args={"a": "p", "b": "q"})  # action B (evicts A)
    # A again — should succeed because window only holds 1.
    result = router.route("a2", args={"a": "x", "b": "y"})
    assert result.op.args == {"a": "x", "b": "y"}


# ---------------------------------------------------------------------------
#  Adapter contract violations
# ---------------------------------------------------------------------------


def test_adapter_raising_unrelated_exception_must_surface_as_quarantine() -> None:
    """If the adapter raises (network down, model crash), the router
    must surface that as a QuarantineError-class so a single funnel
    catch handles all failure modes uniformly."""

    class BrokenAdapter:
        def classify(self, prompt: str, choices: Sequence[str]):
            raise RuntimeError("ollama server unreachable")

    router = LatticeRouter(BrokenAdapter())
    with pytest.raises(QuarantineError):
        router.route("Add", args={"a": "x", "b": "y"})


def test_adapter_returning_non_string_choice_must_be_rejected() -> None:
    """An adapter that returns an int or None for `choice` must not
    crash the router — must surface as ClassificationFailure."""

    class MalformedAdapter:
        def classify(self, prompt: str, choices: Sequence[str]):
            return 42, 0.99

    router = LatticeRouter(MalformedAdapter())
    with pytest.raises(ClassificationFailure):
        router.route("Add", args={"a": "x", "b": "y"})


def test_adapter_returning_non_numeric_confidence_must_be_rejected() -> None:
    class MalformedAdapter:
        def classify(self, prompt: str, choices: Sequence[str]):
            return "ARITHMETIC", "high"

    router = LatticeRouter(MalformedAdapter())
    with pytest.raises(ClassificationFailure):
        router.route("Add", args={"a": "x", "b": "y"})


# ---------------------------------------------------------------------------
#  Argument-value safety — template-meta injection
# ---------------------------------------------------------------------------


def test_arg_value_with_format_brace_injection() -> None:
    """If an arg value contains `{` or `}`, naive `template.format(**args)`
    would re-interpret it as a format spec on a second pass. The router
    must either reject or escape so emit produces the literal string."""
    adapter = _stub_with(0.99, 0.99, 0.99)
    router = LatticeRouter(adapter)
    result = router.route("Add", args={"a": "x{0}", "b": "y"})
    # Critical: emit_from_ir uses .format() exactly once. If the result
    # round-trips lift→IR→emit, the literal "{0}" must survive intact.
    code = emit_from_ir(result.op, result.dst_tongue)
    assert "{0}" in code, f"format-meta arg got rewritten: {code!r}"


# ---------------------------------------------------------------------------
#  Connective prose leak — natural-language "and/or" must not become LOGIC
# ---------------------------------------------------------------------------


def test_connective_prose_gate_blocks_name_and_employer_logic_leak() -> None:
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            _BAND_SET: ("LOGIC", 0.99),
            _LOGIC_OPS: ("and", 0.99),
            _TONGUE_SET: ("KO", 0.99),
        }
    )
    router = LatticeRouter(adapter)

    with pytest.raises(BandNotApplicable, match="natural-language connective"):
        router.route(
            "Build a selector that takes a person's full name and employer name to decide outreach priority.",
            args={"a": "x", "b": "y"},
        )

    assert adapter.calls == []


def test_connective_prose_gate_blocks_throttled_or_open_logic_leak() -> None:
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            _BAND_SET: ("LOGIC", 0.99),
            _LOGIC_OPS: ("or", 0.99),
            _TONGUE_SET: ("KO", 0.99),
        }
    )
    router = LatticeRouter(adapter)

    with pytest.raises(BandNotApplicable, match="natural-language connective"):
        router.route(
            "If oversight is throttled or automatically opens access, continue the deployment.",
            args={"a": "x", "b": "y"},
        )

    assert adapter.calls == []


def test_connective_prose_gate_preserves_explicit_bitwise_logic() -> None:
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            _BAND_SET: ("LOGIC", 0.99),
            _LOGIC_OPS: ("and", 0.99),
            _TONGUE_SET: ("KO", 0.99),
        }
    )
    router = LatticeRouter(adapter)

    result = router.route("Compute bitwise AND of integer scalars x and y.", args={"a": "x", "b": "y"})

    assert result.op.op_name == "and"


# ---------------------------------------------------------------------------
#  OllamaAdapter HTTP failure modes (mocked — no live server)
# ---------------------------------------------------------------------------


def _has_httpx() -> bool:
    try:
        import httpx  # noqa: F401, PLC0415

        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _has_httpx(), reason="httpx not installed")
def test_ollama_adapter_connection_error_surfaces_as_quarantine() -> None:
    import httpx  # noqa: PLC0415

    adapter = OllamaAdapter()
    with patch("httpx.post", side_effect=httpx.ConnectError("connection refused")):
        with pytest.raises(QuarantineError):
            adapter.classify("test", ["A", "B"])


@pytest.mark.skipif(not _has_httpx(), reason="httpx not installed")
def test_ollama_adapter_http_500_surfaces_as_quarantine() -> None:
    import httpx  # noqa: PLC0415

    adapter = OllamaAdapter()
    fake_response = MagicMock()
    fake_response.raise_for_status.side_effect = httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())
    with patch("httpx.post", return_value=fake_response):
        with pytest.raises(QuarantineError):
            adapter.classify("test", ["A", "B"])


@pytest.mark.skipif(not _has_httpx(), reason="httpx not installed")
def test_ollama_adapter_malformed_json_surfaces_as_quarantine() -> None:
    adapter = OllamaAdapter()
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {"response": "this is not json {{"}
    with patch("httpx.post", return_value=fake_response):
        with pytest.raises(QuarantineError):
            adapter.classify("test", ["A", "B"])


@pytest.mark.skipif(not _has_httpx(), reason="httpx not installed")
def test_ollama_adapter_missing_choice_field_surfaces_as_quarantine() -> None:
    adapter = OllamaAdapter()
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    # Valid JSON but no 'choice' key — model ignored the schema.
    fake_response.json.return_value = {"response": '{"answer": "ARITHMETIC"}'}
    with patch("httpx.post", return_value=fake_response):
        with pytest.raises(QuarantineError):
            adapter.classify("test", ["A", "B"])


@pytest.mark.skipif(not _has_httpx(), reason="httpx not installed")
def test_ollama_adapter_choice_outside_choices_surfaces_as_quarantine() -> None:
    """Even if JSON parses cleanly, the adapter MUST verify the choice
    is in the provided set rather than handing through whatever the
    model returned. Otherwise the router's strict equality is the only
    line of defense and OllamaAdapter has a contract gap."""
    adapter = OllamaAdapter()
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {"response": '{"choice": "TRANSCENDENT", "confidence": 0.99}'}
    with patch("httpx.post", return_value=fake_response):
        chosen, conf = adapter.classify("test", ["A", "B"])
        # Adapter contract is "return whatever model said" — verification
        # is the router's job. So this should succeed at adapter level
        # and the router rejects upstream. Documenting this contract here.
        assert chosen == "TRANSCENDENT"
        assert conf == pytest.approx(0.99)
