"""Provider-reported usage must be captured, normalized, and never merged with the estimate.

Before this, `terminal_ai_router.py` recorded only `estimated_cents` and accumulated
`spent_cents_estimate`. The name was honest, but the string "usage" appeared nowhere in the
file: the provider's own token counts were never read, so no receipt could ever be
reconciled against what the provider actually billed.

The design these tests pin (from GitHub Discussion #534):

  * Normalization happens INSIDE the router, because it is the only place that still sees
    the provider payload -- `_safe_body_summary` and `_response_metadata` redact it before
    anything is persisted.
  * Estimate and report are SEPARATE fields. Neither overwrites the other, because a
    disagreement between them is the audit signal for a provider changing billing
    semantics, and that signal only exists if the estimate survives.
  * The provider's raw usage object is kept as evidence, but scalars only. Usage is
    metadata, not content -- and that assumption is enforced, not trusted.
  * Unknown keys are recorded as unmapped rather than dropped, so a provider adding a field
    is visible instead of silent.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "terminal_ai_router", ROOT / "scripts" / "system" / "terminal_ai_router.py"
)
router = importlib.util.module_from_spec(_spec)
sys.modules["terminal_ai_router"] = router
_spec.loader.exec_module(router)


def test_openai_shape_is_normalized():
    u = router._normalize_usage("openai", {"usage": {"prompt_tokens": 12, "completion_tokens": 30, "total_tokens": 42}})
    assert u["reported"] == {"input_tokens": 12, "output_tokens": 30, "total_tokens": 42}
    assert u["normalizer_version"] == router.USAGE_NORMALIZER_VERSION


def test_anthropic_shape_maps_to_the_same_canonical_fields():
    """Different provider vocabulary, identical canonical output -- that is the whole point."""
    u = router._normalize_usage("anthropic", {"usage": {"input_tokens": 12, "output_tokens": 30}})
    assert u["reported"]["input_tokens"] == 12
    assert u["reported"]["output_tokens"] == 30


def test_cache_tokens_are_captured_not_ignored():
    u = router._normalize_usage(
        "anthropic",
        {
            "usage": {
                "input_tokens": 5,
                "output_tokens": 7,
                "cache_read_input_tokens": 900,
                "cache_creation_input_tokens": 100,
            }
        },
    )
    assert u["reported"]["cache_read_tokens"] == 900
    assert u["reported"]["cache_write_tokens"] == 100


def test_unknown_provider_keys_are_reported_as_unmapped():
    """A provider adding a field must be visible, not silently dropped."""
    u = router._normalize_usage("openai", {"usage": {"prompt_tokens": 1, "reasoning_tokens": 500}})
    assert "reasoning_tokens" in u["unmapped_keys"]
    assert u["reported"]["input_tokens"] == 1


def test_usage_cannot_smuggle_text_past_the_redaction_boundary():
    """Usage is metadata by convention; this enforces it rather than trusting the provider.

    If a provider ever echoes the prompt inside `usage`, storing it verbatim would put user
    content into a receipt that is explicitly designed never to hold any.
    """
    u = router._normalize_usage("evil", {"usage": {"prompt_tokens": 3, "echo": "the user's secret prompt"}})
    evidence = u["provider_evidence"]
    assert evidence["echo"] == {"type": "str", "length": len("the user's secret prompt")}
    assert "secret" not in repr(evidence)


def test_missing_usage_is_recorded_as_absent_not_as_zero():
    """Zero tokens and 'the provider told us nothing' are different facts."""
    u = router._normalize_usage("openai", {"choices": []})
    assert u["reported"] is None
    assert u["provider_evidence"] is None


def test_estimate_and_report_never_overwrite_each_other():
    u = router._normalize_usage("openai", {"usage": {"prompt_tokens": 10, "completion_tokens": 20}})
    cost = router._reconcile_usage(4.25, u)
    assert cost["estimated_cents"] == 4.25  # estimate survives the report
    assert cost["reported_tokens"]["input_tokens"] == 10
    assert cost["status"] == "reported"
    assert "reported_cents" not in cost, "must not invent money from tokens without a price table"


def test_estimate_only_is_labelled_honestly():
    cost = router._reconcile_usage(1.0, router._normalize_usage("openai", {}))
    assert cost["status"] == "estimate_only"
    assert cost["reported_available"] is False


def test_ledger_accumulates_tokens_separately_from_the_cents_estimate():
    ledger: dict = {}
    usage = router._normalize_usage("openai", {"usage": {"prompt_tokens": 10, "completion_tokens": 20}})
    for _ in range(3):
        router._record_spend(ledger, "openai", model="m", tier="t", estimated_cents=2.0, response_ok=True, usage=usage)
    row = ledger["providers"]["openai"]
    assert row["spent_cents_estimate"] == pytest.approx(6.0)
    assert row["reported_tokens"] == {"input_tokens": 30, "output_tokens": 60}
    assert row["calls_with_reported_usage"] == 3
    assert ledger["events"][0]["usage"]["reported"]["input_tokens"] == 10


def test_record_spend_still_works_without_usage():
    """Backwards compatible: the parameter is optional and old call sites keep working."""
    ledger: dict = {}
    router._record_spend(ledger, "openai", model="m", tier="t", estimated_cents=1.5, response_ok=False)
    row = ledger["providers"]["openai"]
    assert row["spent_cents_estimate"] == pytest.approx(1.5)
    assert "reported_tokens" not in row
    assert "usage" not in ledger["events"][0]


def test_booleans_are_not_mistaken_for_token_counts():
    """bool is a subclass of int in Python -- `cached: true` must not become 1 token."""
    u = router._normalize_usage("openai", {"usage": {"prompt_tokens": True, "completion_tokens": 5}})
    assert "input_tokens" not in (u["reported"] or {})
    assert u["reported"]["output_tokens"] == 5
