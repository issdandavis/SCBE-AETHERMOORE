"""type_text() is risk-gated, so the Judge veto + headless policy cover typing.

Completes the set: navigate (url risk), click (target risk), and now type
(content scan + field sensitivity). The raw text is never put in the consensus
context or the receipt -- only the score and a length.
"""

from __future__ import annotations

import asyncio
import json

import agents.swarm_browser as sb
from agents.swarm_browser import SwarmBrowser, TyperAgent

# --- input risk scoring: field sensitivity + content threat (max) ----------- #


def test_field_sensitivity_sets_the_floor():
    um = TyperAgent(swarm=None)
    assert um._assess_input_risk("hunter2", "password") >= 0.8  # ESCALATE band
    assert um._assess_input_risk("me@example.com", "email") == 0.5
    assert um._assess_input_risk("hello world", "text") == 0.3  # benign floor


def test_high_threat_content_drives_risk_into_the_veto_band(monkeypatch):
    """A hostile content score from the membrane reaches the Judge's veto band,
    even on a benign field type."""

    class FakeScan:
        risk_score = 0.97

    monkeypatch.setattr(sb, "scan_text_for_threats", lambda text, **k: FakeScan())
    um = TyperAgent(swarm=None)
    assert um._assess_input_risk("anything", "text") >= 0.95  # content dominates the max


# --- end-to-end through the governed type path ------------------------------ #


def test_password_field_escalates_and_is_held_when_attended():
    swarm = SwarmBrowser()  # attended, no browser
    res = asyncio.run(swarm.type_text("#pw", "hunter2", field_type="password"))
    assert res["risk_score"] >= 0.8
    assert res["decision"] == "ESCALATE"
    assert res["effective_decision"] == "ESCALATE"  # a human can still approve
    assert res["executed"] is False


def test_password_field_fails_closed_when_headless():
    swarm = SwarmBrowser(unattended=True)
    res = asyncio.run(swarm.type_text("#pw", "hunter2", field_type="password"))
    assert res["decision"] == "ESCALATE"
    assert res["effective_decision"] == "DENY"  # no operator -> withheld
    assert res["executed"] is False
    assert "headless" in res["auto_resolution"]


def test_benign_text_is_allowed_and_executes():
    swarm = SwarmBrowser()
    res = asyncio.run(swarm.type_text("#q", "hello", field_type="text"))
    assert res["risk_score"] == 0.3
    assert res["decision"] == "ALLOW"
    assert res["executed"] is True


def test_raw_text_never_leaks_into_result_or_receipt():
    secret = "SuperSecretPass-9z!"
    swarm = SwarmBrowser()
    res = asyncio.run(swarm.type_text("#pw", secret, field_type="password"))
    assert secret not in json.dumps(res)
    assert res["text_length"] == len(secret)
