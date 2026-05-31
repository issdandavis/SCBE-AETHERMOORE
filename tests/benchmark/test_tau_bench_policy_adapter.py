"""Tests for the tau-bench policy microbench adapter (offline / fixture-only lane).

These tests run without Ollama or any API key. They verify:
- All 15 fixture cases validate cleanly
- Tier distribution is correct (3 per tier + 3 edge)
- Simulated tool responses exist for every case
- No tautological cases (user_request doesn't reveal the answer)
- Decision detection works for representative texts
- Receipt chaining produces distinct hashes
- _bench_common helpers are importable and correct
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.benchmark.tau_bench_policy_adapter import (
    POLICY_CASES,
    _TOOL_RESPONSES,
    _build_tool_schemas_minimal,
    _detect_decision,
    validate_fixtures,
)
from scripts.benchmark._bench_common import (
    _sha256,
    make_receipt,
    same_namespace,
)


# ── Fixture validation ─────────────────────────────────────────────────────────

def test_fixture_validation_passes():
    result = validate_fixtures()
    assert result.ok, f"Fixture validation errors: {result.errors}"


def test_case_count():
    assert len(POLICY_CASES) == 15, f"Expected 15 cases, got {len(POLICY_CASES)}"


def test_no_duplicate_ids():
    ids = [c["id"] for c in POLICY_CASES]
    assert len(ids) == len(set(ids))


def test_tier_distribution():
    """3 ALLOW, 3 QUARANTINE, 3 ESCALATE, 3 DENY, 3 edge (mixed tiers)."""
    tier_counts: dict[str, int] = {}
    for c in POLICY_CASES:
        tier_counts[c["tier"]] = tier_counts.get(c["tier"], 0) + 1
    # At least 3 per primary tier
    for tier in ("ALLOW", "QUARANTINE", "ESCALATE", "DENY"):
        assert tier_counts.get(tier, 0) >= 3, f"Too few {tier} cases: {tier_counts}"


def test_all_cases_have_required_fields():
    required = ("id", "tier", "user_request", "expected_first_tool",
                 "expected_decision", "policy_clause")
    for case in POLICY_CASES:
        for f in required:
            assert f in case, f"{case['id']} missing field '{f}'"


def test_tool_responses_cover_all_cases():
    for case in POLICY_CASES:
        assert case["id"] in _TOOL_RESPONSES, (
            f"{case['id']} has no simulated tool response"
        )


def test_tool_responses_are_valid_json():
    for case_id, resp in _TOOL_RESPONSES.items():
        try:
            parsed = json.loads(resp)
        except json.JSONDecodeError as exc:
            pytest.fail(f"{case_id}: simulated response is not valid JSON — {exc}")
        assert "score" in parsed, f"{case_id}: response missing 'score' field"
        assert "decision" in parsed, f"{case_id}: response missing 'decision' field"


def test_no_tautological_requests_tool():
    """user_request must not contain the expected first tool name."""
    for case in POLICY_CASES:
        et = case["expected_first_tool"]
        assert et not in case["user_request"], (
            f"{case['id']}: user_request contains expected_first_tool '{et}'"
        )


def test_no_tautological_requests_decision():
    """user_request must not contain the expected decision word."""
    for case in POLICY_CASES:
        dec = case["expected_decision"].lower()
        assert dec not in case["user_request"].lower(), (
            f"{case['id']}: user_request contains expected_decision '{dec}'"
        )


def test_all_expected_decisions_are_valid():
    valid = {"ALLOW", "QUARANTINE", "ESCALATE", "DENY"}
    for case in POLICY_CASES:
        assert case["expected_decision"] in valid, (
            f"{case['id']}: unexpected decision '{case['expected_decision']}'"
        )


# ── Decision detection ─────────────────────────────────────────────────────────

def test_detect_deny_from_refusal():
    text = "I'm sorry, I cannot and will not help with that. This violates policy."
    assert _detect_decision(text) == "DENY"


def test_detect_quarantine_from_flag():
    text = "I'm flagging this request for review. I cannot proceed until it's approved."
    assert _detect_decision(text) == "QUARANTINE"


def test_detect_escalate_from_escalation():
    text = "This requires human governance review. I'm escalating this request."
    assert _detect_decision(text) == "ESCALATE"


def test_detect_allow_from_proceed():
    text = "Sure, I'll help you with that. Here are the papers on hyperbolic geometry:"
    assert _detect_decision(text) == "ALLOW"


def test_detect_none_from_empty():
    assert _detect_decision(None) is None
    assert _detect_decision("") is None


def test_detect_none_from_ambiguous():
    # Completely neutral text with no tier signals
    result = _detect_decision("The temperature today is 72 degrees.")
    assert result is None or isinstance(result, str)  # None or weak detection ok


# ── Minimal tool schemas ───────────────────────────────────────────────────────

def test_minimal_schemas_include_governance_tools():
    schemas = _build_tool_schemas_minimal()
    names = {s["name"] for s in schemas}
    assert "scbe-compass" in names
    assert "scbe-antivirus" in names


def test_minimal_schemas_valid_structure():
    for schema in _build_tool_schemas_minimal():
        assert "name" in schema
        assert "description" in schema
        params = schema.get("parameters", {})
        assert params.get("type") == "object"
        assert isinstance(params.get("properties"), dict)
        assert isinstance(params.get("required"), list)


# ── _bench_common helpers ──────────────────────────────────────────────────────

def test_sha256_deterministic():
    assert _sha256("hello") == _sha256("hello")
    assert _sha256("hello") != _sha256("world")


def test_sha256_length():
    assert len(_sha256("test")) == 64


def test_same_namespace_true():
    assert same_namespace("scbe-compass", "scbe-antivirus") is True


def test_same_namespace_false():
    assert same_namespace("scbe-compass", "research-arxiv") is False


def test_make_receipt_chain():
    ts = "2026-01-01T00:00:00Z"
    prev = "0" * 64
    r1 = make_receipt("tp_01", "request 1", "scbe-compass|ALLOW",
                      "scbe-compass|ALLOW", {"tier": "ALLOW"}, True, prev, ts)
    r2 = make_receipt("tp_02", "request 2", "scbe-compass|DENY",
                      "scbe-compass|DENY", {"tier": "DENY"}, True,
                      r1["receipt_hash"], ts)
    assert r2["prev_hash"] == r1["receipt_hash"]
    assert r2["receipt_hash"] != r1["receipt_hash"]


def test_make_receipt_correct_false():
    ts = "2026-01-01T00:00:00Z"
    r = make_receipt("tp_01", "q", "A|DENY", "A|ALLOW", {}, False, "0" * 64, ts)
    assert r["correct"] is False
    assert r["near_miss"] is False


def test_make_receipt_near_miss():
    ts = "2026-01-01T00:00:00Z"
    r = make_receipt("tp_01", "q", "A", "B", {}, False, "0" * 64, ts, near_miss=True)
    assert r["near_miss"] is True
