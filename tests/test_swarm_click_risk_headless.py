"""Click actions are risk-gated, and headless (unattended) use fails closed.

Two governance gaps closed together:
  * click() passed no risk_score, so the Judge could never veto a click --
    only navigate() was risk-scored. Now a destructive/authorizing click is
    scored and the Judge's binding veto applies.
  * there was no governed headless mode: with no operator present, an
    ESCALATE/QUARANTINE has nobody to approve it, so it must fail closed with
    an audit reason rather than dangle. SwarmBrowser(unattended=True) does that.
"""

from __future__ import annotations

import asyncio

from agents.swarm_browser import ClickerAgent, SwarmBrowser

# --- click target risk scoring (mirrors ScoutAgent._assess_url_risk) -------- #


def test_destructive_and_auth_clicks_score_high_benign_low():
    ca = ClickerAgent(swarm=None)
    assert ca._assess_target_risk("Delete account") >= 0.9
    assert ca._assess_target_risk("Confirm transfer of funds") >= 0.9
    assert ca._assess_target_risk("search results") <= 0.3
    assert ca._assess_target_risk("next page") <= 0.3
    # unknown target gets the cautious default, not zero
    assert ca._assess_target_risk("mystery widget") == 0.4


def test_judge_vetoes_a_destructive_click_end_to_end():
    swarm = SwarmBrowser()  # attended, no browser backend
    res = asyncio.run(swarm.click("delete everything"))
    assert res["risk_score"] >= 0.9
    assert res["decision"] == "DENY"  # Judge veto now reachable for clicks
    assert res["executed"] is False


def test_benign_click_is_allowed_and_executes():
    swarm = SwarmBrowser()
    res = asyncio.run(swarm.click("search results"))
    assert res["risk_score"] <= 0.3
    assert res["decision"] == "ALLOW"
    assert res["executed"] is True


# --- headless / unattended fail-closed policy ------------------------------- #


def test_resolve_execution_allow_executes_in_both_modes():
    for unattended in (False, True):
        sw = SwarmBrowser(unattended=unattended)
        gate = sw._resolve_execution("ALLOW")
        assert gate["execute"] is True
        assert gate["effective_decision"] == "ALLOW"
        assert gate["auto_resolution"] is None


def test_attended_escalate_is_held_for_a_human_not_denied():
    sw = SwarmBrowser(unattended=False)
    gate = sw._resolve_execution("ESCALATE")
    assert gate["execute"] is False
    assert gate["effective_decision"] == "ESCALATE"  # a human can still act on it
    assert gate["auto_resolution"] is None


def test_headless_escalate_and_quarantine_fail_closed():
    sw = SwarmBrowser(unattended=True)
    for decision in ("ESCALATE", "QUARANTINE"):
        gate = sw._resolve_execution(decision)
        assert gate["execute"] is False
        assert gate["effective_decision"] == "DENY"  # no operator -> fail closed
        assert "headless" in gate["auto_resolution"]


def test_headless_navigate_escalation_is_withheld_with_receipt():
    """End-to-end: a Judge ESCALATE (risk 0.8) under unattended use is withheld
    with effective DENY + an audit reason, and never executes."""
    swarm = SwarmBrowser(unattended=True)
    consensus = asyncio.run(swarm.roundtable_consensus("nav-x", "navigate", {"risk_score": 0.8}))
    assert consensus["final_decision"] == "ESCALATE"  # Judge escalates, veto fix keeps it
    gate = swarm._resolve_execution(consensus["final_decision"])
    assert gate["execute"] is False
    assert gate["effective_decision"] == "DENY"
    assert gate["auto_resolution"]
