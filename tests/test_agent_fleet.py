"""
Tests for HYDRA Agent Fleet — Multi-Agent Orchestrator
=======================================================

Tests cover:
- Finger interaction methods (click, type, fill_form, etc.)
- FleetTask creation, dedup, and priority ordering
- FleetAgent execution routing (connector-first, browser-first, both)
- AgentFleet orchestration (spawn, submit, run, shutdown)
- SessionPool rate limiting
- ConnectorBridge dispatch
- Training data generation

Run:
    python -m pytest tests/test_agent_fleet.py -v
    python -m pytest tests/test_agent_fleet.py -v -m "not slow"
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Finger Interaction Tests ──────────────────────────────────────────

class TestFingerInteractions:
    """Test the new Finger interaction methods."""

    def test_browsing_result_structure(self):
        from src.browser.hydra_hand import BrowsingResult, Tongue
        r = BrowsingResult(tongue=Tongue.CA, url="https://example.com")
        assert r.tongue == Tongue.CA
        assert r.url == "https://example.com"
        assert r.metadata == {}
        assert r.elapsed_ms == 0.0

    def test_finger_has_interaction_methods(self):
        from src.browser.hydra_hand import Finger, Tongue
        f = Finger(tongue=Tongue.CA)
        assert hasattr(f, "click")
        assert hasattr(f, "type_text")
        assert hasattr(f, "fill_form")
        assert hasattr(f, "select_option")
        assert hasattr(f, "upload_file")
        assert hasattr(f, "download")
        assert hasattr(f, "wait_for")
        assert hasattr(f, "scroll_to")
        assert hasattr(f, "get_attribute")
        assert hasattr(f, "handle_dialog")
        assert hasattr(f, "get_cookies")
        assert hasattr(f, "set_cookies")
        assert hasattr(f, "current_url")
        assert hasattr(f, "page_title")

    def test_tongue_enum_values(self):
        from src.browser.hydra_hand import Tongue
        assert Tongue.KO.value == "KO"
        assert Tongue.AV.value == "AV"
        assert Tongue.RU.value == "RU"
        assert Tongue.CA.value == "CA"
        assert Tongue.UM.value == "UM"
        assert Tongue.DR.value == "DR"

    def test_proximity_mapping(self):
        from src.browser.hydra_hand import Tongue, Proximity, TONGUE_PROXIMITY
        assert TONGUE_PROXIMITY[Tongue.RU] == Proximity.ROCK   # Urgent
        assert TONGUE_PROXIMITY[Tongue.KO] == Proximity.VOICE  # Command
        assert TONGUE_PROXIMITY[Tongue.AV] == Proximity.OWL    # Background


# ── FleetTask Tests ───────────────────────────────────────────────────

class TestFleetTask:
    """Test task creation, dedup, and serialization."""

    def test_task_creation(self):
        from src.fleet.agent_fleet import FleetTask
        t = FleetTask(
            task_type="github_issue",
            platform="github",
            target="241",
            action="triage",
        )
        assert t.task_id  # Auto-generated
        assert t.platform == "github"
        assert t.action == "triage"
        assert t.created_at > 0

    def test_task_fingerprint_dedup(self):
        from src.fleet.agent_fleet import FleetTask
        t1 = FleetTask(task_type="github_issue", platform="github", target="241", action="triage")
        t2 = FleetTask(task_type="github_issue", platform="github", target="241", action="triage")
        t3 = FleetTask(task_type="github_issue", platform="github", target="242", action="triage")
        assert t1.fingerprint == t2.fingerprint  # Same platform:target:action
        assert t1.fingerprint != t3.fingerprint  # Different target

    def test_task_priority_ordering(self):
        from src.fleet.agent_fleet import FleetTask, TaskPriority
        urgent = FleetTask(task_type="a", platform="github", target="1", action="fix", priority=TaskPriority.URGENT)
        normal = FleetTask(task_type="a", platform="github", target="2", action="fix", priority=TaskPriority.NORMAL)
        bg = FleetTask(task_type="a", platform="github", target="3", action="fix", priority=TaskPriority.BACKGROUND)
        assert urgent.priority.value < normal.priority.value < bg.priority.value

    def test_task_to_dict(self):
        from src.fleet.agent_fleet import FleetTask
        t = FleetTask(task_type="shopify_product", platform="shopify", target="123", action="create")
        d = t.to_dict()
        assert d["platform"] == "shopify"
        assert d["action"] == "create"
        assert "task_id" in d
        assert "status" in d

    def test_task_elapsed_ms(self):
        from src.fleet.agent_fleet import FleetTask
        t = FleetTask(task_type="a", platform="b", target="c", action="d")
        t.started_at = 100.0
        t.completed_at = 100.5
        assert t.elapsed_ms == 500.0

    def test_execution_modes(self):
        from src.fleet.agent_fleet import ExecutionMode
        assert ExecutionMode.CONNECTOR_FIRST == "connector_first"
        assert ExecutionMode.BROWSER_FIRST == "browser_first"
        assert ExecutionMode.BOTH == "both"
        assert ExecutionMode.CONNECTOR_ONLY == "connector_only"
        assert ExecutionMode.BROWSER_ONLY == "browser_only"


# ── Agent Role Config Tests ───────────────────────────────────────────

class TestAgentRoles:
    """Test that roles are properly configured."""

    def test_all_roles_defined(self):
        from src.fleet.agent_fleet import AGENT_ROLES
        assert "issues" in AGENT_ROLES
        assert "builder" in AGENT_ROLES
        assert "ops" in AGENT_ROLES

    def test_roles_have_platforms(self):
        from src.fleet.agent_fleet import AGENT_ROLES
        for role, config in AGENT_ROLES.items():
            assert "platforms" in config
            assert "description" in config
            assert "task_types" in config
            assert len(config["platforms"]) > 0

    def test_builder_includes_creative_platforms(self):
        from src.fleet.agent_fleet import AGENT_ROLES
        builder = AGENT_ROLES["builder"]
        assert "shopify" in builder["platforms"]
        assert "canva" in builder["platforms"]
        assert "adobe" in builder["platforms"]
        assert "gamma" in builder["platforms"]

    def test_issues_includes_project_platforms(self):
        from src.fleet.agent_fleet import AGENT_ROLES
        issues = AGENT_ROLES["issues"]
        assert "github" in issues["platforms"]
        assert "notion" in issues["platforms"]


# ── FleetAgent Tests ──────────────────────────────────────────────────

class TestFleetAgent:
    """Test individual agent behavior."""

    def test_agent_creation(self):
        from src.fleet.agent_fleet import FleetAgent
        agent = FleetAgent(agent_id="test-1", role="issues")
        assert agent.agent_id == "test-1"
        assert agent.role == "issues"
        assert agent.tasks_completed == 0

    def test_agent_status(self):
        from src.fleet.agent_fleet import FleetAgent
        agent = FleetAgent(agent_id="test-2", role="builder")
        status = agent.status()
        assert status["agent_id"] == "test-2"
        assert status["role"] == "builder"
        assert status["running"] is False
        assert "platforms" in status

    def test_sft_pair_generation(self):
        from src.fleet.agent_fleet import FleetAgent, FleetTask, TaskResult
        agent = FleetAgent(agent_id="test-3", role="ops")
        task = FleetTask(task_type="github_issue", platform="github", target="100", action="triage")
        result = TaskResult(success=True, data={"title": "Test"}, source="connector", credits_earned=0.2)
        pair = agent._generate_sft_pair(task, result)
        assert "instruction" in pair
        assert "response" in pair
        assert pair["platform"] == "github"
        assert pair["credits"] == 0.2


# ── AgentFleet Orchestrator Tests ─────────────────────────────────────

class TestAgentFleet:
    """Test fleet orchestration without real browser/connector."""

    def test_fleet_creation(self):
        from src.fleet.agent_fleet import AgentFleet
        fleet = AgentFleet(max_agents=3)
        assert fleet.max_agents == 3
        assert len(fleet.roles) == 3
        assert not fleet._running

    def test_fleet_status(self):
        from src.fleet.agent_fleet import AgentFleet
        fleet = AgentFleet(max_agents=2, roles=["issues", "ops"])
        status = fleet.status()
        assert status["running"] is False
        assert status["queue_size"] == 0

    @pytest.mark.asyncio
    async def test_task_dedup(self):
        from src.fleet.agent_fleet import AgentFleet, FleetTask
        fleet = AgentFleet(max_agents=1, roles=["issues"])

        t1 = FleetTask(task_type="github_issue", platform="github", target="241", action="triage")
        t2 = FleetTask(task_type="github_issue", platform="github", target="241", action="triage")

        await fleet.submit(t1)
        await fleet.submit(t2)

        # Second task should be deduped (skipped)
        assert t2.status.value == "skipped"

    @pytest.mark.asyncio
    async def test_priority_queue_ordering(self):
        from src.fleet.agent_fleet import AgentFleet, FleetTask, TaskPriority
        fleet = AgentFleet(max_agents=1, roles=["issues"])

        bg = FleetTask(task_type="a", platform="github", target="1", action="bg", priority=TaskPriority.BACKGROUND)
        urgent = FleetTask(task_type="a", platform="github", target="2", action="urgent", priority=TaskPriority.URGENT)
        normal = FleetTask(task_type="a", platform="github", target="3", action="norm", priority=TaskPriority.NORMAL)

        await fleet.submit(bg)
        await fleet.submit(urgent)
        await fleet.submit(normal)

        # Queue should serve urgent first
        _, _, first = await fleet._task_queue.get()
        assert first.action == "urgent"


# ── SessionPool Tests ────────────────────────────────────────────────

class TestSessionPool:
    """Test shared session pool and rate limiting."""

    def test_pool_creation(self):
        from src.fleet.session_pool import SessionPool
        pool = SessionPool()
        assert pool is not None

    def test_get_session(self):
        from src.fleet.session_pool import SessionPool
        pool = SessionPool()
        session = pool.get_session("github")
        assert session.platform == "github"

    @pytest.mark.asyncio
    async def test_rate_limiter(self):
        from src.fleet.session_pool import RateLimiter
        limiter = RateLimiter(rate=10.0, burst=5)
        # Should allow burst requests
        for _ in range(5):
            assert await limiter.acquire()

    def test_pool_stats(self):
        from src.fleet.session_pool import SessionPool
        pool = SessionPool()
        stats = pool.stats()
        assert isinstance(stats, dict)


# ── Browser Flow Registry Tests ──────────────────────────────────────

class TestBrowserFlows:
    """Test that browser flows are registered."""

    def test_flows_registered(self):
        from src.fleet.agent_fleet import BROWSER_FLOWS
        assert "github" in BROWSER_FLOWS
        assert "shopify" in BROWSER_FLOWS
        assert "gamma" in BROWSER_FLOWS
        assert "canva" in BROWSER_FLOWS

    def test_github_flows(self):
        from src.fleet.agent_fleet import BROWSER_FLOWS
        gh = BROWSER_FLOWS["github"]
        assert "triage" in gh
        assert "review" in gh
        assert "read" in gh

    def test_shopify_flows(self):
        from src.fleet.agent_fleet import BROWSER_FLOWS
        shop = BROWSER_FLOWS["shopify"]
        assert "check" in shop
        assert "verify" in shop


# ── FleetReport Tests ─────────────────────────────────────────────────

class TestFleetReport:
    """Test report generation."""

    def test_report_creation(self):
        from src.fleet.agent_fleet import FleetReport
        r = FleetReport(total_tasks=10, completed=8, failed=1, skipped=1, total_credits=5.5)
        d = r.to_dict()
        assert d["total_tasks"] == 10
        assert d["completed"] == 8
        assert d["total_credits"] == 5.5

    def test_report_to_dict(self):
        from src.fleet.agent_fleet import FleetReport
        r = FleetReport()
        d = r.to_dict()
        assert "total_tasks" in d
        assert "training_pairs_generated" in d


# ── Domain Safety Tests ──────────────────────────────────────────────

class TestDomainSafety:
    """Test the domain safety check used by browser agents."""

    def test_trusted_domains(self):
        from src.browser.hydra_hand import check_domain_safety
        decision, risk = check_domain_safety("https://github.com/some/repo")
        assert decision == "ALLOW"
        assert risk == 0.0

    def test_blocked_domains(self):
        from src.browser.hydra_hand import check_domain_safety
        decision, risk = check_domain_safety("https://malware.com/bad")
        assert decision == "DENY"
        assert risk == 1.0

    def test_unknown_domains(self):
        from src.browser.hydra_hand import check_domain_safety
        decision, risk = check_domain_safety("https://random-site.com")
        assert decision == "QUARANTINE"
        assert risk == 0.5


# ── Quick Fleet Function Tests ───────────────────────────────────────

class TestQuickFleet:
    """Test the convenience quick_fleet function."""

    def test_quick_fleet_import(self):
        from src.fleet.agent_fleet import quick_fleet
        assert callable(quick_fleet)


# ── Integration Smoke Test ───────────────────────────────────────────

@pytest.mark.slow
class TestIntegrationSmoke:
    """Smoke tests that verify components wire together."""

    @pytest.mark.asyncio
    async def test_fleet_start_shutdown(self):
        """Fleet can start and shutdown without errors."""
        from src.fleet.agent_fleet import AgentFleet
        fleet = AgentFleet(max_agents=1, roles=["ops"])
        # Start will fail gracefully if no browser/connectors
        try:
            await fleet.start()
        except Exception:
            pass  # Expected in test env
        await fleet.shutdown()
