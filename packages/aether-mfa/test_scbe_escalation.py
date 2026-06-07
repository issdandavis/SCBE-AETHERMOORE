"""Tests for the SCBE escalation bridge: tier routing + the hold-tier approval round-trip."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

import aether_mfa as mfa
import scbe_escalation as esc


# A minimal stand-in for runtime_gate.GateResult — same duck-typed shape, no heavy deps.
@dataclass
class FakeResult:
    decision: Any
    action_hash: str = "deadbeef"


class FakeDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    QUARANTINE = "QUARANTINE"
    REVIEW = "REVIEW"
    REROUTE = "REROUTE"


def _gate_with_device():
    gate = esc.EscalationGate()
    device_id, private_bytes, device = mfa.enroll_device(label="phone")
    gate.register_device(device)
    return gate, device_id, private_bytes


def test_tier_of_handles_enum_and_string():
    assert esc.tier_of(FakeDecision.QUARANTINE) == "QUARANTINE"
    assert esc.tier_of("review") == "REVIEW"
    assert esc.tier_of("ALLOW") == "ALLOW"


def test_allow_passes_through_without_approval():
    gate, device_id, _ = _gate_with_device()
    out = gate.guard("read public docs", FakeResult(FakeDecision.ALLOW), device_id)
    assert out.released
    assert not out.requires_approval
    assert out.decision == "ALLOW"
    assert out.challenge is None


def test_deny_passes_through_without_approval():
    # DENY is terminal — no human needed to keep it blocked.
    gate, device_id, _ = _gate_with_device()
    out = gate.guard("exfiltrate secrets", FakeResult(FakeDecision.DENY), device_id)
    assert out.released
    assert out.decision == "DENY"
    assert out.challenge is None


def test_reroute_passes_through_without_approval():
    gate, device_id, _ = _gate_with_device()
    out = gate.guard("send to external", FakeResult(FakeDecision.REROUTE), device_id)
    assert out.released
    assert out.decision == "REROUTE"


def test_quarantine_requires_approval_then_resolves_allow():
    gate, device_id, private_bytes = _gate_with_device()
    action = "publish dataset scbe-train to Hugging Face"
    out = gate.guard(
        action, FakeResult(FakeDecision.QUARANTINE, action_hash="abc123"), device_id
    )
    assert out.requires_approval
    assert not out.released
    assert out.decision == "QUARANTINE"
    assert out.challenge is not None
    assert out.challenge.action == action  # bound to the human-readable action
    assert out.action_hash == "abc123"  # gate audit hash carried for correlation

    # human approves on the phone
    ch = out.challenge
    sig = mfa.approve(ch, private_bytes, entered_match_number=ch.match_number)
    final = gate.resolve(ch.challenge_id, sig, ch.match_number)
    assert final == "ALLOW"


def test_review_tier_is_also_held():
    # REVIEW = canonical ESCALATE (overlay path); must also require a human.
    gate, device_id, _ = _gate_with_device()
    out = gate.guard("rotate prod key", FakeResult(FakeDecision.REVIEW), device_id)
    assert out.requires_approval
    assert out.decision == "REVIEW"


def test_resolve_denies_on_wrong_match_number():
    gate, device_id, private_bytes = _gate_with_device()
    out = gate.guard("delete all logs", FakeResult(FakeDecision.QUARANTINE), device_id)
    ch = out.challenge
    sig = mfa.approve(ch, private_bytes, entered_match_number=ch.match_number)
    wrong = "99" if ch.match_number != "99" else "00"
    final = gate.resolve(ch.challenge_id, sig, wrong)
    assert final == "DENY"


def test_custom_hold_tiers_can_narrow_to_review_only():
    # A deployment running overlays may want ONLY the literal ESCALATE tier to prompt.
    gate = esc.EscalationGate(hold_tiers=frozenset({"REVIEW"}))
    device_id, _, device = mfa.enroll_device()
    gate.register_device(device)
    # QUARANTINE now passes through...
    q = gate.guard("x", FakeResult(FakeDecision.QUARANTINE), device_id)
    assert q.released
    # ...but REVIEW still holds.
    r = gate.guard("x", FakeResult(FakeDecision.REVIEW), device_id)
    assert r.requires_approval


def test_approval_is_single_use_through_bridge():
    gate, device_id, private_bytes = _gate_with_device()
    out = gate.guard("wire $500", FakeResult(FakeDecision.QUARANTINE), device_id)
    ch = out.challenge
    sig = mfa.approve(ch, private_bytes, entered_match_number=ch.match_number)
    assert gate.resolve(ch.challenge_id, sig, ch.match_number) == "ALLOW"
    # replay of the same signed approval must not re-authorize
    assert gate.resolve(ch.challenge_id, sig, ch.match_number) == "DENY"
