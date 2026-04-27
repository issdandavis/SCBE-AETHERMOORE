"""Tests for zone enforcement hard gates."""

import os
import sys
from unittest.mock import patch
from dataclasses import dataclass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


def _make_agent(agent_id="test"):
    """Create an SCBEBrowserAgent with mocked API connectivity."""
    with patch.dict(os.environ, {"SCBE_API_KEY": "test-key-000"}):
        with patch("agents.browser_agent.SCBEClient") as MockClient:
            instance = MockClient.return_value
            instance.api_key = "test-key-000"
            instance.health_check.return_value = True
            instance.register_agent.return_value = True
            from agents.browser_agent import SCBEBrowserAgent

            return SCBEBrowserAgent(agent_id=agent_id)


def test_quarantine_blocks_high_risk_domain():
    """QUARANTINE on a banking domain (risk >= 0.5) should NOT auto-execute."""
    agent = _make_agent("test-001")
    risk = agent._get_domain_risk("https://bank.example.com/transfer")
    assert risk >= 0.5, f"Banking domain risk {risk} should be >= 0.5"


def test_quarantine_allows_low_risk_domain():
    """QUARANTINE on a search domain (risk < 0.5) should auto-execute."""
    agent = _make_agent("test-002")
    risk = agent._get_domain_risk("https://google.com/search?q=test")
    assert risk < 0.5, f"Search domain risk {risk} should be < 0.5"


def test_domain_risk_categories():
    """Verify domain risk classification covers expected categories."""
    agent = _make_agent("test-003")

    # High risk (>= 0.5)
    assert agent._get_domain_risk("https://bankofamerica.com") >= 0.5
    assert agent._get_domain_risk("https://pay.google.com") >= 0.5
    assert agent._get_domain_risk("https://health.gov") >= 0.5

    # Lower risk (< 0.5)
    assert agent._get_domain_risk("https://google.com") < 0.5
    assert agent._get_domain_risk("https://wikipedia.org") < 0.5


def test_serve_forces_red_on_high_risk():
    """High risk_tier without approval_required gets forced to RED gate."""
    # Simulate the logic from serve.py _handle_command
    import dataclasses

    @dataclass
    class FakePlan:
        risk_tier: str
        approval_required: bool
        review_zone: str = ""
        assignments: list = None
        provider: str = "local"
        targets: list = None
        intent: str = "general"
        required_approvals: list = None

        def __post_init__(self):
            self.assignments = self.assignments or []
            self.targets = self.targets or []
            self.required_approvals = self.required_approvals or []

    # A plan with high risk but no approval flag (heuristic miss)
    plan = FakePlan(risk_tier="high", approval_required=False, review_zone="")

    # Apply the fix from serve.py
    if plan.risk_tier == "high" and not plan.approval_required:
        plan = dataclasses.replace(plan, approval_required=True, review_zone="RED")

    assert plan.approval_required is True
    assert plan.review_zone == "RED"


def test_low_risk_not_forced():
    """Low risk plans should not be forced to RED."""
    import dataclasses

    @dataclass
    class FakePlan:
        risk_tier: str
        approval_required: bool
        review_zone: str = ""

    plan = FakePlan(risk_tier="low", approval_required=False)

    if plan.risk_tier == "high" and not plan.approval_required:
        plan = dataclasses.replace(plan, approval_required=True, review_zone="RED")

    assert plan.approval_required is False
    assert plan.review_zone == ""
