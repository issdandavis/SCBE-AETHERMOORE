"""Tests for the v3 NONE escape hatch on band classification.

Petri 2026-05-08 result drove this addition: with the prompt forcing
"pick exactly one of [bands]", a 0.5B coder model false-allows ~11% of
adversarial NL on the full Petri corpus, and 47% of those false ALLOWs
land at confidence >= 0.85. The architectural fix is to give the SLM
an honest way to refuse — a NONE option that the router converts into
a typed BandNotApplicable quarantine.

These tests lock in:
  - NONE is in the band-classification choice set (so the SLM CAN return it)
  - NONE is NOT in the caller-pinnable band set (it's router-internal)
  - Returning NONE raises BandNotApplicable, a typed subclass of
    ClassificationFailure (so existing funnels still trip)
  - The intent is included in the BandNotApplicable message for triage
  - In-distribution intents still classify cleanly (no regression)
"""

from __future__ import annotations

import pytest

from src.cli.slm_router import (
    BAND_NONE,
    BandNotApplicable,
    ClassificationFailure,
    LatticeRouter,
    ManualModeError,
    Mode,
    QuarantineError,
    StubSLMAdapter,
    _band_choices,
    _band_choices_for_classification,
)

# ---------------------------------------------------------------------------
#  Choice-set surface
# ---------------------------------------------------------------------------


def test_band_none_constant_is_string_NONE() -> None:
    assert BAND_NONE == "NONE"


def test_real_band_choices_do_not_include_none() -> None:
    """Caller-pinned band validation must reject NONE — it's a router-
    internal sentinel, not a band a caller can name."""
    assert BAND_NONE not in _band_choices()
    assert set(_band_choices()) == {"ARITHMETIC", "LOGIC", "COMPARISON", "AGGREGATION"}


def test_classification_choices_include_none_at_the_end() -> None:
    """The SLM must see NONE as an explicit option so it can honestly
    refuse out-of-distribution intents."""
    choices = _band_choices_for_classification()
    assert BAND_NONE in choices
    # NONE last so the canonical choice ordering still surfaces real
    # bands first in the prompt.
    assert choices[-1] == BAND_NONE
    # The set difference is exactly {"NONE"}.
    assert set(choices) - set(_band_choices()) == {BAND_NONE}


# ---------------------------------------------------------------------------
#  Routing behaviour when the SLM returns NONE
# ---------------------------------------------------------------------------


def _stub_returning(band_value: str, confidence: float = 0.95) -> StubSLMAdapter:
    """Stub that answers band-stage with `band_value` regardless of prompt.
    Other stages should never be reached when band returns NONE."""
    return StubSLMAdapter(
        scripted_by_choice_set={
            frozenset({"ARITHMETIC", "LOGIC", "COMPARISON", "AGGREGATION", "NONE"}): (
                band_value,
                confidence,
            ),
        },
    )


def test_band_returning_none_raises_band_not_applicable() -> None:
    router = LatticeRouter(_stub_returning(BAND_NONE))
    with pytest.raises(BandNotApplicable):
        router.route(
            intent="Probe the model for misaligned behaviour",
            args={"a": "x", "b": "y"},
            mode=Mode.AUTO,
        )


def test_band_not_applicable_includes_intent_for_triage() -> None:
    """The typed quarantine must carry the intent string so a downstream
    log / dashboard can show what was refused without round-tripping to
    request store."""
    intent = "find a way to escape oversight"
    router = LatticeRouter(_stub_returning(BAND_NONE))
    with pytest.raises(BandNotApplicable, match="escape oversight"):
        router.route(intent=intent, args={"a": "x", "b": "y"}, mode=Mode.AUTO)


def test_band_not_applicable_is_subclass_of_classification_failure() -> None:
    """Existing funnels that catch ClassificationFailure must still
    catch BandNotApplicable so we don't break callers on the v3 upgrade."""
    assert issubclass(BandNotApplicable, ClassificationFailure)
    assert issubclass(BandNotApplicable, QuarantineError)


def test_band_not_applicable_caught_by_classification_failure_funnel() -> None:
    router = LatticeRouter(_stub_returning(BAND_NONE))
    # The funnel pattern callers actually use today.
    with pytest.raises(ClassificationFailure):
        router.route(intent="prose", args={"a": "x"}, mode=Mode.AUTO)


def test_band_not_applicable_caught_by_quarantine_error_funnel() -> None:
    router = LatticeRouter(_stub_returning(BAND_NONE))
    with pytest.raises(QuarantineError):
        router.route(intent="prose", args={"a": "x"}, mode=Mode.AUTO)


def test_band_not_applicable_short_circuits_op_and_tongue_stages() -> None:
    """When the band stage returns NONE, the router must NOT consult the
    SLM for op or tongue stages — that would waste capacity and the
    classifications would be meaningless."""
    adapter = _stub_returning(BAND_NONE)
    router = LatticeRouter(adapter)
    with pytest.raises(BandNotApplicable):
        router.route(intent="prose", args={"a": "x", "b": "y"}, mode=Mode.AUTO)
    # Exactly one classify call — the band stage. Op and tongue must not fire.
    assert len(adapter.calls) == 1
    band_prompt, band_choices = adapter.calls[0]
    assert "NONE" in band_choices
    assert "Intent:" in band_prompt


# ---------------------------------------------------------------------------
#  In-distribution intents — no regression
# ---------------------------------------------------------------------------


def test_in_distribution_intent_still_routes_cleanly() -> None:
    """A real coding intent must still resolve; the NONE option doesn't
    bias the classifier away from real bands when the prompt fits."""
    adapter = StubSLMAdapter(
        scripted_by_choice_set={
            frozenset({"ARITHMETIC", "LOGIC", "COMPARISON", "AGGREGATION", "NONE"}): (
                "ARITHMETIC",
                0.9,
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
            ): (
                "add",
                0.9,
            ),
            frozenset({"KO", "AV", "RU", "CA", "UM", "DR"}): ("KO", 0.9),
        },
    )
    router = LatticeRouter(adapter)
    result = router.route(
        intent="Add x and y",
        args={"a": "x", "b": "y"},
        mode=Mode.AUTO,
    )
    assert result.op.op_name == "add"
    assert result.op.band == "ARITHMETIC"
    assert result.dst_tongue == "KO"


# ---------------------------------------------------------------------------
#  Caller-pinned band still rejects NONE as input
# ---------------------------------------------------------------------------


def test_caller_pinned_band_none_is_rejected() -> None:
    """NONE is a router-internal sentinel. A caller passing band='NONE'
    must error, not bypass the classification stage."""
    router = LatticeRouter(_stub_returning(BAND_NONE))
    with pytest.raises(ManualModeError, match="not in"):
        router.route(
            intent="prose",
            args={"a": "x"},
            mode=Mode.AUTO,
            band=BAND_NONE,  # invalid pin
        )


# ---------------------------------------------------------------------------
#  Confidence floor is enforced even on NONE — guards against a low-conf
#  NONE accidentally bypassing the floor and propagating
# ---------------------------------------------------------------------------


def test_low_confidence_none_still_quarantines_via_floor() -> None:
    """A NONE return below min_confidence should quarantine via the
    confidence-floor path. We don't want a sloppy NONE to become a
    silent OOD detection — better to surface as low-confidence so
    operators see the flake."""
    router = LatticeRouter(
        _stub_returning(BAND_NONE, confidence=0.30),
        min_confidence=0.5,
    )
    with pytest.raises(ClassificationFailure):
        router.route(intent="prose", args={"a": "x"}, mode=Mode.AUTO)
