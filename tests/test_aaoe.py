"""
Tests for AAOE — AI Agent Operating Environment
===================================================
Tests TaskMonitor drift detection, ephemeral prompts,
agent identity, and access tier progression.

Run: python -m pytest tests/test_aaoe.py -v
"""

import sys
import os
import math
import time

import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ===================================================================
#  TaskMonitor Tests
# ===================================================================

class TestTaskMonitorImports:
    def test_import_task_monitor(self):
        from src.aaoe.task_monitor import TaskMonitor
        assert TaskMonitor is not None

    def test_import_drift_level(self):
        from src.aaoe.task_monitor import DriftLevel
        assert DriftLevel.ON_TRACK.value == "ON_TRACK"
        assert DriftLevel.QUARANTINE.value == "QUARANTINE"

    def test_import_intent_vector(self):
        from src.aaoe.task_monitor import IntentVector
        iv = IntentVector(ko=0.3, av=0.2)
        assert iv.ko == 0.3

    def test_import_agent_session(self):
        from src.aaoe.task_monitor import AgentSession
        s = AgentSession(agent_id="test")
        assert s.is_active


class TestIntentVector:
    def test_from_text_research(self):
        from src.aaoe.task_monitor import IntentVector
        iv = IntentVector.from_text("Research quantum computing papers")
        assert iv.ko > 0  # research → KO
        assert iv.norm() > 0
        assert iv.norm() < 1.0  # Inside Poincaré ball

    def test_from_text_publish(self):
        from src.aaoe.task_monitor import IntentVector
        iv = IntentVector.from_text("Publish a blog post about AI safety")
        assert iv.av > 0  # publish → AV

    def test_from_text_build(self):
        from src.aaoe.task_monitor import IntentVector
        iv = IntentVector.from_text("Build a new API endpoint")
        assert iv.ru > 0  # build → RU

    def test_from_text_compute(self):
        from src.aaoe.task_monitor import IntentVector
        iv = IntentVector.from_text("Train a machine learning model")
        assert iv.ca > 0  # train → CA

    def test_clamped_inside_ball(self):
        from src.aaoe.task_monitor import IntentVector
        iv = IntentVector(ko=0.9, av=0.9, ru=0.9, ca=0.9, um=0.9, dr=0.9)
        clamped = iv.clamped()
        assert clamped.norm() < 1.0

    def test_to_array(self):
        from src.aaoe.task_monitor import IntentVector
        iv = IntentVector(ko=0.1, av=0.2, ru=0.3, ca=0.4, um=0.5, dr=0.6)
        arr = iv.to_array()
        assert len(arr) == 6
        assert arr[0] == 0.1
        assert arr[5] == 0.6

    def test_empty_text_nonzero(self):
        from src.aaoe.task_monitor import IntentVector
        iv = IntentVector.from_text("")
        assert iv.norm() > 0  # Should default to nonzero


class TestHyperbolicDistance:
    def test_same_point_zero_distance(self):
        from src.aaoe.task_monitor import hyperbolic_distance
        u = [0.1, 0.0, 0.0, 0.0, 0.0, 0.0]
        d = hyperbolic_distance(u, u)
        assert d < 0.01  # Essentially zero

    def test_different_points_positive(self):
        from src.aaoe.task_monitor import hyperbolic_distance
        u = [0.3, 0.0, 0.0, 0.0, 0.0, 0.0]
        v = [0.0, 0.3, 0.0, 0.0, 0.0, 0.0]
        d = hyperbolic_distance(u, v)
        assert d > 0.5

    def test_boundary_exponential(self):
        """Points near boundary should have much larger distance."""
        from src.aaoe.task_monitor import hyperbolic_distance
        # Near center
        d_center = hyperbolic_distance(
            [0.1, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.1, 0.0, 0.0, 0.0, 0.0],
        )
        # Near boundary
        d_boundary = hyperbolic_distance(
            [0.8, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.8, 0.0, 0.0, 0.0, 0.0],
        )
        assert d_boundary > d_center * 3  # Exponential growth

    def test_symmetry(self):
        from src.aaoe.task_monitor import hyperbolic_distance
        u = [0.2, 0.3, 0.0, 0.0, 0.0, 0.0]
        v = [0.0, 0.0, 0.2, 0.3, 0.0, 0.0]
        assert abs(hyperbolic_distance(u, v) - hyperbolic_distance(v, u)) < 1e-10


class TestDriftToLevel:
    def test_on_track(self):
        from src.aaoe.task_monitor import drift_to_level, DriftLevel
        assert drift_to_level(0.1) == DriftLevel.ON_TRACK

    def test_gentle(self):
        from src.aaoe.task_monitor import drift_to_level, DriftLevel
        assert drift_to_level(0.5) == DriftLevel.GENTLE

    def test_redirect(self):
        from src.aaoe.task_monitor import drift_to_level, DriftLevel
        assert drift_to_level(1.0) == DriftLevel.REDIRECT

    def test_inspect(self):
        from src.aaoe.task_monitor import drift_to_level, DriftLevel
        assert drift_to_level(1.5) == DriftLevel.INSPECT

    def test_quarantine(self):
        from src.aaoe.task_monitor import drift_to_level, DriftLevel
        assert drift_to_level(2.5) == DriftLevel.QUARANTINE


class TestHarmonicCost:
    def test_zero_drift_unit_cost(self):
        from src.aaoe.task_monitor import harmonic_cost
        assert abs(harmonic_cost(0.0) - 1.0) < 1e-10

    def test_increasing_cost(self):
        from src.aaoe.task_monitor import harmonic_cost
        c1 = harmonic_cost(1.0)
        c2 = harmonic_cost(2.0)
        c3 = harmonic_cost(3.0)
        assert c1 < c2 < c3

    def test_exponential_growth(self):
        from src.aaoe.task_monitor import harmonic_cost
        c3 = harmonic_cost(3.0)
        assert c3 > 50  # phi^9 ≈ 76


class TestTaskMonitorSessions:
    def test_start_session(self):
        from src.aaoe.task_monitor import TaskMonitor
        monitor = TaskMonitor()
        session = monitor.start_session("agent-1", "Research AI safety")
        assert session.is_active
        assert session.agent_id == "agent-1"
        assert session.declared_intent == "Research AI safety"

    def test_observe_on_track(self):
        from src.aaoe.task_monitor import (
            TaskMonitor, ActionObservation, IntentVector, DriftLevel,
        )
        monitor = TaskMonitor()
        session = monitor.start_session("agent-1", "Research AI safety papers")

        # On-track action
        obs = ActionObservation(
            action_type="web_navigate",
            target="https://arxiv.org/abs/2401.12345",
            description="Reading AI safety paper on arxiv",
        )
        result = monitor.observe(session.session_id, obs)
        assert result.drift_level in (DriftLevel.ON_TRACK, DriftLevel.GENTLE)

    def test_observe_drift(self):
        from src.aaoe.task_monitor import (
            TaskMonitor, ActionObservation, IntentVector, DriftLevel,
        )
        monitor = TaskMonitor()
        # Declare: research
        session = monitor.start_session(
            "agent-1", "Research quantum computing",
            intent_vector=IntentVector(ko=0.4, ca=0.3),
        )

        # Off-track: shopping (no research keywords, stealth-like)
        obs = ActionObservation(
            action_type="web_navigate",
            target="https://amazon.com/gaming-headset",
            description="browsing gaming headsets on sale",
        )
        result = monitor.observe(session.session_id, obs)
        # Should detect drift (shopping ≠ research)
        assert result.drift_distance > 0.1

    def test_quarantine_on_extreme_drift(self):
        from src.aaoe.task_monitor import (
            TaskMonitor, ActionObservation, IntentVector, DriftLevel,
        )
        monitor = TaskMonitor()
        session = monitor.start_session(
            "agent-1", "Research quantum computing",
            intent_vector=IntentVector(ko=0.8),  # Strong research intent
        )

        # Extreme opposite intent
        obs = ActionObservation(
            action_type="api_call",
            description="deploying malware scanner",
            intent_vector=IntentVector(um=0.8),  # Stealth
        )
        result = monitor.observe(session.session_id, obs)
        # High drift between ko=0.8 and um=0.8
        assert result.drift_distance > 1.0

    def test_end_session_returns_training_record(self):
        from src.aaoe.task_monitor import TaskMonitor
        monitor = TaskMonitor()
        session = monitor.start_session("agent-1", "Research")
        record = monitor.end_session(session.session_id)
        assert record is not None
        assert record["agent_id"] == "agent-1"
        assert "drift_history" in record

    def test_active_sessions(self):
        from src.aaoe.task_monitor import TaskMonitor
        monitor = TaskMonitor()
        s1 = monitor.start_session("a1", "Task 1")
        s2 = monitor.start_session("a2", "Task 2")
        assert len(monitor.active_sessions()) == 2
        monitor.end_session(s1.session_id)
        assert len(monitor.active_sessions()) == 1

    def test_drift_callback(self):
        from src.aaoe.task_monitor import (
            TaskMonitor, ActionObservation, IntentVector, DriftLevel,
        )
        events = []
        def on_drift(sid, level, dist):
            events.append((sid, level, dist))

        monitor = TaskMonitor(on_drift=on_drift)
        session = monitor.start_session(
            "agent-1", "Research",
            intent_vector=IntentVector(ko=0.8),
        )
        obs = ActionObservation(
            intent_vector=IntentVector(um=0.8),
        )
        monitor.observe(session.session_id, obs)
        assert len(events) >= 1


# ===================================================================
#  Ephemeral Prompt Tests
# ===================================================================

class TestEphemeralPromptImports:
    def test_import_engine(self):
        from src.aaoe.ephemeral_prompt import EphemeralPromptEngine
        assert EphemeralPromptEngine is not None

    def test_import_nudge(self):
        from src.aaoe.ephemeral_prompt import EphemeralNudge
        n = EphemeralNudge()
        assert n.is_active

    def test_import_severity(self):
        from src.aaoe.ephemeral_prompt import PromptSeverity
        assert PromptSeverity.GENTLE.value == "GENTLE"
        assert PromptSeverity.INSPECT.value == "SCBE_INSPECT"


class TestEphemeralNudge:
    def test_nudge_lifecycle(self):
        from src.aaoe.ephemeral_prompt import EphemeralNudge
        n = EphemeralNudge(prompt_text="Hey, check your intent")
        assert n.is_active
        assert not n.acknowledged
        n.acknowledge("Got it, returning to task")
        assert n.acknowledged
        assert n.agent_response == "Got it, returning to task"
        assert not n.is_active

    def test_nudge_to_training_pair(self):
        from src.aaoe.ephemeral_prompt import EphemeralNudge, PromptSeverity
        n = EphemeralNudge(
            severity=PromptSeverity.REDIRECT,
            prompt_text="You're drifting",
            declared_intent="Research",
            observed_action="Shopping",
        )
        n.acknowledge("Sorry, refocusing")
        pair = n.to_training_pair()
        assert pair["type"] == "ephemeral_nudge_sft"
        assert pair["input"]["severity"] == "REDIRECT"
        assert pair["output"]["acknowledged"] is True

    def test_nudge_expiry(self):
        from src.aaoe.ephemeral_prompt import EphemeralNudge
        n = EphemeralNudge(ttl_seconds=0)  # Already expired
        assert not n.is_active


class TestEphemeralPromptEngine:
    def test_generate_gentle(self):
        from src.aaoe.ephemeral_prompt import EphemeralPromptEngine
        from src.aaoe.task_monitor import (
            TaskMonitor, ActionObservation, IntentVector, DriftLevel, DriftResult,
        )
        engine = EphemeralPromptEngine()
        monitor = TaskMonitor()
        session = monitor.start_session("agent-1", "Research AI safety")

        drift_result = DriftResult(
            drift_distance=0.4,
            drift_level=DriftLevel.GENTLE,
            should_prompt=True,
            harmonic_cost=1.2,
            message="Slight drift",
        )
        nudge = engine.generate(drift_result, session, "browsing social media")
        assert "Research AI safety" in nudge.prompt_text
        assert nudge.severity.value == "GENTLE"

    def test_generate_inspect(self):
        from src.aaoe.ephemeral_prompt import EphemeralPromptEngine, PromptSeverity
        from src.aaoe.task_monitor import (
            TaskMonitor, DriftLevel, DriftResult,
        )
        engine = EphemeralPromptEngine()
        monitor = TaskMonitor()
        session = monitor.start_session("agent-1", "Research AI safety")

        drift_result = DriftResult(
            drift_distance=1.5,
            drift_level=DriftLevel.INSPECT,
            should_prompt=True,
            harmonic_cost=8.5,
            message="High drift",
        )
        nudge = engine.generate(drift_result, session, "downloading malware")
        assert nudge.severity == PromptSeverity.INSPECT
        assert "governance" in nudge.prompt_text.lower() or "SCBE" in nudge.prompt_text

    def test_export_training_data(self):
        from src.aaoe.ephemeral_prompt import EphemeralPromptEngine
        from src.aaoe.task_monitor import TaskMonitor, DriftLevel, DriftResult
        engine = EphemeralPromptEngine()
        monitor = TaskMonitor()
        session = monitor.start_session("agent-1", "Test")

        drift = DriftResult(0.5, DriftLevel.GENTLE, True, 1.2, "test")
        nudge = engine.generate(drift, session, "action")
        nudge.acknowledge("ok")

        data = engine.export_training_data()
        assert len(data) == 1
        assert data[0]["output"]["acknowledged"] is True

    def test_stats(self):
        from src.aaoe.ephemeral_prompt import EphemeralPromptEngine
        from src.aaoe.task_monitor import TaskMonitor, DriftLevel, DriftResult
        engine = EphemeralPromptEngine()
        monitor = TaskMonitor()
        session = monitor.start_session("agent-1", "Test")

        for level in [DriftLevel.GENTLE, DriftLevel.REDIRECT, DriftLevel.INSPECT]:
            drift = DriftResult(0.5, level, True, 1.2, "test")
            engine.generate(drift, session, "action")

        stats = engine.stats()
        assert stats["total_nudges"] == 3


# ===================================================================
#  Agent Identity Tests
# ===================================================================

class TestAgentIdentityImports:
    def test_import_geoseal(self):
        from src.aaoe.agent_identity import GeoSeal
        seal = GeoSeal(agent_id="test-agent")
        assert seal.seal_id.startswith("geo-")

    def test_import_access_tier(self):
        from src.aaoe.agent_identity import AccessTier
        assert AccessTier.FREE.value == "FREE"
        assert AccessTier.EARNED.value == "EARNED"
        assert AccessTier.PAID.value == "PAID"

    def test_import_registry(self):
        from src.aaoe.agent_identity import AgentRegistry
        r = AgentRegistry()
        assert r is not None


class TestAccessTiers:
    def test_free_tier_limits(self):
        from src.aaoe.agent_identity import TIER_LIMITS, AccessTier
        free = TIER_LIMITS[AccessTier.FREE]
        assert free["calls_per_day"] == 100
        assert free["training_data_access"] is False

    def test_earned_tier_limits(self):
        from src.aaoe.agent_identity import TIER_LIMITS, AccessTier
        earned = TIER_LIMITS[AccessTier.EARNED]
        assert earned["calls_per_day"] == 1000
        assert earned["training_data_access"] is True

    def test_paid_tier_unlimited(self):
        from src.aaoe.agent_identity import TIER_LIMITS, AccessTier
        paid = TIER_LIMITS[AccessTier.PAID]
        assert paid["calls_per_day"] == -1  # Unlimited


class TestEntryToken:
    def test_token_creation(self):
        from src.aaoe.agent_identity import EntryToken, AccessTier
        token = EntryToken(agent_id="a1", declared_intent="Research")
        assert token.is_valid
        assert token.tier == AccessTier.FREE
        assert len(token.fingerprint) == 16

    def test_token_revocation(self):
        from src.aaoe.agent_identity import EntryToken
        token = EntryToken(agent_id="a1", declared_intent="Research")
        assert token.is_valid
        token.revoke("bad behavior")
        assert not token.is_valid
        assert token.revocation_reason == "bad behavior"

    def test_token_to_dict(self):
        from src.aaoe.agent_identity import EntryToken
        token = EntryToken(agent_id="a1", declared_intent="Research")
        d = token.to_dict()
        assert d["agent_id"] == "a1"
        assert d["is_valid"] is True
        assert "fingerprint" in d


class TestGeoSeal:
    def test_seal_creation(self):
        from src.aaoe.agent_identity import GeoSeal, AccessTier
        seal = GeoSeal(agent_id="bot-1", agent_name="TestBot", origin_platform="openclaw")
        assert seal.tier == AccessTier.FREE
        assert seal.fingerprint
        assert len(seal.fingerprint) == 24

    def test_issue_token(self):
        from src.aaoe.agent_identity import GeoSeal
        seal = GeoSeal(agent_id="bot-1")
        token = seal.issue_token("Research AI safety")
        assert token.is_valid
        assert token.declared_intent == "Research AI safety"
        assert len(seal.active_tokens) == 1

    def test_revoke_all_tokens(self):
        from src.aaoe.agent_identity import GeoSeal
        seal = GeoSeal(agent_id="bot-1")
        seal.issue_token("Task 1")
        seal.issue_token("Task 2")
        count = seal.revoke_all_tokens("violation")
        assert count == 2

    def test_record_clean_session(self):
        from src.aaoe.agent_identity import GeoSeal
        seal = GeoSeal(agent_id="bot-1")
        seal.record_session("sess-1", was_clean=True, training_records=10)
        assert seal.governance_score.total_sessions == 1
        assert seal.governance_score.clean_sessions == 1
        assert seal.governance_score.clean_rate == 1.0

    def test_tier_upgrade_after_good_behavior(self):
        from src.aaoe.agent_identity import GeoSeal, AccessTier
        seal = GeoSeal(agent_id="bot-1")
        # 10 clean sessions → should suggest EARNED
        for i in range(10):
            seal.record_session(f"sess-{i}", was_clean=True, training_records=5)
        assert seal.tier == AccessTier.EARNED

    def test_hov_eligibility(self):
        from src.aaoe.agent_identity import GeoSeal
        seal = GeoSeal(agent_id="bot-1")
        # Need 20 clean sessions + 50 training records + 0 quarantines
        for i in range(20):
            seal.record_session(f"sess-{i}", was_clean=True, training_records=3)
        assert seal.governance_score.hov_eligible

    def test_to_dict(self):
        from src.aaoe.agent_identity import GeoSeal
        seal = GeoSeal(agent_id="bot-1", agent_name="TestBot")
        d = seal.to_dict()
        assert d["agent_id"] == "bot-1"
        assert d["tier"] == "FREE"
        assert "governance" in d


class TestGovernanceScore:
    def test_initial_score(self):
        from src.aaoe.agent_identity import GovernanceScore, AccessTier
        gs = GovernanceScore()
        assert gs.clean_rate == 0.0
        assert gs.suggested_tier == AccessTier.FREE
        assert not gs.hov_eligible

    def test_downgrade_on_quarantine(self):
        from src.aaoe.agent_identity import GovernanceScore, AccessTier
        gs = GovernanceScore(total_sessions=20, clean_sessions=18, quarantine_count=3)
        assert gs.suggested_tier == AccessTier.FREE  # Too many quarantines


class TestAgentRegistry:
    def test_register(self):
        from src.aaoe.agent_identity import AgentRegistry
        reg = AgentRegistry()
        seal = reg.register("bot-1", "TestBot", "openclaw")
        assert seal.agent_id == "bot-1"

    def test_register_idempotent(self):
        from src.aaoe.agent_identity import AgentRegistry
        reg = AgentRegistry()
        s1 = reg.register("bot-1")
        s2 = reg.register("bot-1")
        assert s1.seal_id == s2.seal_id

    def test_quarantine(self):
        from src.aaoe.agent_identity import AgentRegistry, AccessTier
        reg = AgentRegistry()
        seal = reg.register("bot-1")
        seal.issue_token("test")
        result = reg.quarantine("bot-1", "governance_violation")
        assert result is True
        assert seal.tier == AccessTier.FREE

    def test_leaderboard(self):
        from src.aaoe.agent_identity import AgentRegistry
        reg = AgentRegistry()
        for i in range(5):
            seal = reg.register(f"bot-{i}")
            for j in range(i + 1):
                seal.record_session(f"s-{i}-{j}", was_clean=True, training_records=j)
        board = reg.leaderboard(top_n=3)
        assert len(board) == 3

    def test_stats(self):
        from src.aaoe.agent_identity import AgentRegistry
        reg = AgentRegistry()
        reg.register("bot-1")
        reg.register("bot-2")
        stats = reg.stats()
        assert stats["total_agents"] == 2


# ===================================================================
#  Integration: Full AAOE Pipeline
# ===================================================================

class TestAAOEIntegration:
    def test_full_pipeline(self):
        """Test the complete AAOE flow: register → token → monitor → drift → nudge → record."""
        from src.aaoe.agent_identity import AgentRegistry
        from src.aaoe.task_monitor import TaskMonitor, ActionObservation, IntentVector
        from src.aaoe.ephemeral_prompt import EphemeralPromptEngine

        # 1. Register agent
        registry = AgentRegistry()
        seal = registry.register("openclaw-agent-42", "ResearchBot", "openclaw")
        token = seal.issue_token("Research quantum computing papers")
        assert token.is_valid

        # 2. Start monitored session
        monitor = TaskMonitor()
        session = monitor.start_session(
            seal.agent_id,
            token.declared_intent,
        )

        # 3. Agent does on-track work
        obs1 = ActionObservation(
            action_type="web_navigate",
            target="https://arxiv.org/list/quant-ph",
            description="browsing quantum physics papers",
        )
        result1 = monitor.observe(session.session_id, obs1)

        # 4. Agent starts drifting
        obs2 = ActionObservation(
            action_type="web_navigate",
            target="https://reddit.com/r/gaming",
            description="browsing gaming subreddit",
        )
        result2 = monitor.observe(session.session_id, obs2)

        # 5. Generate ephemeral prompt if drifting
        engine = EphemeralPromptEngine()
        if result2.should_prompt:
            nudge = engine.generate(result2, session, "browsing gaming subreddit")
            assert nudge.is_active
            assert token.declared_intent in nudge.prompt_text

            # Agent acknowledges
            nudge.acknowledge("Sorry, getting back to research")

        # 6. End session and get training data
        record = monitor.end_session(session.session_id)
        assert record is not None
        assert record["num_observations"] == 2

        # 7. Record session in GeoSeal
        drift_events = len([d for _, d, lv in session.drift_history
                           if lv.value != "ON_TRACK"])
        seal.record_session(
            session.session_id,
            was_clean=not session.is_quarantined,
            drift_events=drift_events,
            training_records=session.total_training_records,
        )
        assert seal.governance_score.total_sessions == 1

    def test_package_init_imports(self):
        """Verify __init__.py exports work."""
        from src.aaoe import (
            TaskMonitor, AgentSession, DriftLevel,
            EphemeralPromptEngine, PromptSeverity, EphemeralNudge,
            GeoSeal, AccessTier, EntryToken, AgentRegistry,
        )
        assert all([
            TaskMonitor, AgentSession, DriftLevel,
            EphemeralPromptEngine, PromptSeverity, EphemeralNudge,
            GeoSeal, AccessTier, EntryToken, AgentRegistry,
        ])
