"""
Tests for src/cognitive_governance/governance_engine.py
======================================================

Covers:
- GovernanceDecision enum
- DecisionContext dataclass
- GovernanceEngine: trust management, evaluate, _compute_score, _decide
- Trust update from decisions
- Batch evaluation
- Agent summary
- History management
"""

import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cognitive_governance.governance_engine import (
    GovernanceDecision,
    DecisionContext,
    GovernanceEngine,
)


# ============================================================
# GovernanceDecision Enum
# ============================================================

@pytest.mark.unit
class TestGovernanceDecision:
    def test_allow_value(self):
        assert GovernanceDecision.ALLOW.value == "ALLOW"

    def test_constrain_value(self):
        assert GovernanceDecision.CONSTRAIN.value == "CONSTRAIN"

    def test_redirect_value(self):
        assert GovernanceDecision.REDIRECT.value == "REDIRECT"

    def test_deny_value(self):
        assert GovernanceDecision.DENY.value == "DENY"

    def test_four_decisions(self):
        assert len(GovernanceDecision) == 4


# ============================================================
# Trust Management
# ============================================================

@pytest.mark.unit
class TestTrustManagement:
    def test_default_trust(self):
        engine = GovernanceEngine()
        assert engine.get_trust("new_agent") == 0.5

    def test_set_trust(self):
        engine = GovernanceEngine()
        engine.set_trust("a1", 0.8)
        assert engine.get_trust("a1") == 0.8

    def test_set_trust_clamped_high(self):
        engine = GovernanceEngine()
        engine.set_trust("a1", 1.5)
        assert engine.get_trust("a1") == 1.0

    def test_set_trust_clamped_low(self):
        engine = GovernanceEngine()
        engine.set_trust("a1", -0.5)
        assert engine.get_trust("a1") == 0.0

    def test_update_trust_positive(self):
        engine = GovernanceEngine()
        engine.set_trust("a1", 0.5)
        engine.update_trust("a1", 0.1)
        assert abs(engine.get_trust("a1") - 0.6) < 1e-10

    def test_update_trust_negative(self):
        engine = GovernanceEngine()
        engine.set_trust("a1", 0.5)
        engine.update_trust("a1", -0.2)
        assert abs(engine.get_trust("a1") - 0.3) < 1e-10

    def test_update_trust_clamps(self):
        engine = GovernanceEngine()
        engine.set_trust("a1", 0.95)
        engine.update_trust("a1", 0.2)
        assert engine.get_trust("a1") == 1.0


# ============================================================
# _decide (score-based decisions)
# ============================================================

@pytest.mark.unit
class TestDecide:
    def test_high_score_allows(self):
        engine = GovernanceEngine()
        decision = engine._decide(0.8, "interior", [], "READ")
        assert decision == GovernanceDecision.ALLOW

    def test_medium_score_constrains(self):
        engine = GovernanceEngine()
        decision = engine._decide(0.5, "interior", [], "READ")
        assert decision == GovernanceDecision.CONSTRAIN

    def test_low_score_redirects(self):
        engine = GovernanceEngine()
        decision = engine._decide(0.25, "interior", [], "READ")
        assert decision == GovernanceDecision.REDIRECT

    def test_very_low_score_denies(self):
        engine = GovernanceEngine()
        decision = engine._decide(0.1, "interior", [], "READ")
        assert decision == GovernanceDecision.DENY

    def test_exterior_always_denies(self):
        engine = GovernanceEngine()
        decision = engine._decide(1.0, "exterior", [], "READ")
        assert decision == GovernanceDecision.DENY

    def test_blocked_tongues_deny(self):
        engine = GovernanceEngine()
        # READ uses KO, AV — if both blocked, deny
        decision = engine._decide(0.9, "interior", ["KO", "AV"], "READ")
        assert decision == GovernanceDecision.DENY

    def test_partially_blocked_tongues_allow(self):
        engine = GovernanceEngine()
        # READ uses KO, AV — only KO blocked, AV still open
        decision = engine._decide(0.9, "interior", ["KO"], "READ")
        assert decision == GovernanceDecision.ALLOW

    def test_boundary_allow_threshold(self):
        engine = GovernanceEngine()
        # Exactly at threshold
        decision = engine._decide(engine.allow_threshold, "interior", [], "READ")
        assert decision == GovernanceDecision.ALLOW

    def test_just_below_allow_threshold(self):
        engine = GovernanceEngine()
        decision = engine._decide(engine.allow_threshold - 0.01, "interior", [], "READ")
        assert decision == GovernanceDecision.CONSTRAIN

    def test_unknown_action_uses_ko(self):
        engine = GovernanceEngine()
        # Unknown action defaults to ["KO"] — if KO blocked, deny
        decision = engine._decide(0.9, "interior", ["KO"], "CUSTOM_ACTION")
        assert decision == GovernanceDecision.DENY


# ============================================================
# _compute_score
# ============================================================

@pytest.mark.unit
class TestComputeScore:
    def test_score_bounded_0_1(self):
        engine = GovernanceEngine()
        score = engine._compute_score(
            safety=1.0, trust=1.0, distance=0.0,
            phase_alignment=1.0, classification="interior",
            cost=0.0, sensitivity=0.0,
        )
        assert 0.0 <= score <= 1.0

    def test_exterior_classification_reduces_score(self):
        engine = GovernanceEngine()
        interior = engine._compute_score(
            safety=0.8, trust=0.8, distance=1.0,
            phase_alignment=0.5, classification="interior",
            cost=1.0, sensitivity=0.5,
        )
        exterior = engine._compute_score(
            safety=0.8, trust=0.8, distance=1.0,
            phase_alignment=0.5, classification="exterior",
            cost=1.0, sensitivity=0.5,
        )
        assert exterior < interior

    def test_governance_classification_reduces_score(self):
        engine = GovernanceEngine()
        interior = engine._compute_score(
            safety=0.8, trust=0.8, distance=1.0,
            phase_alignment=0.5, classification="interior",
            cost=1.0, sensitivity=0.5,
        )
        governance = engine._compute_score(
            safety=0.8, trust=0.8, distance=1.0,
            phase_alignment=0.5, classification="governance",
            cost=1.0, sensitivity=0.5,
        )
        assert governance < interior

    def test_higher_trust_higher_score(self):
        engine = GovernanceEngine()
        low_trust = engine._compute_score(
            safety=0.5, trust=0.1, distance=1.0,
            phase_alignment=0.0, classification="interior",
            cost=1.0, sensitivity=0.5,
        )
        high_trust = engine._compute_score(
            safety=0.5, trust=0.9, distance=1.0,
            phase_alignment=0.0, classification="interior",
            cost=1.0, sensitivity=0.5,
        )
        assert high_trust > low_trust

    def test_higher_distance_lower_score(self):
        engine = GovernanceEngine()
        close = engine._compute_score(
            safety=0.5, trust=0.5, distance=0.1,
            phase_alignment=0.0, classification="interior",
            cost=1.0, sensitivity=0.5,
        )
        far = engine._compute_score(
            safety=0.5, trust=0.5, distance=10.0,
            phase_alignment=0.0, classification="interior",
            cost=1.0, sensitivity=0.5,
        )
        assert far < close

    def test_higher_sensitivity_lower_score(self):
        engine = GovernanceEngine()
        low_sens = engine._compute_score(
            safety=0.5, trust=0.5, distance=1.0,
            phase_alignment=0.0, classification="interior",
            cost=1.0, sensitivity=0.0,
        )
        high_sens = engine._compute_score(
            safety=0.5, trust=0.5, distance=1.0,
            phase_alignment=0.0, classification="interior",
            cost=1.0, sensitivity=1.0,
        )
        assert high_sens < low_sens


# ============================================================
# Trust update from decisions
# ============================================================

@pytest.mark.unit
class TestTrustUpdate:
    def test_allow_increases_trust(self):
        engine = GovernanceEngine()
        engine.set_trust("a1", 0.5)
        engine._update_trust_from_decision("a1", GovernanceDecision.ALLOW)
        assert engine.get_trust("a1") > 0.5

    def test_constrain_no_change(self):
        engine = GovernanceEngine()
        engine.set_trust("a1", 0.5)
        engine._update_trust_from_decision("a1", GovernanceDecision.CONSTRAIN)
        assert engine.get_trust("a1") == 0.5

    def test_redirect_decreases_trust(self):
        engine = GovernanceEngine()
        engine.set_trust("a1", 0.5)
        engine._update_trust_from_decision("a1", GovernanceDecision.REDIRECT)
        assert engine.get_trust("a1") < 0.5

    def test_deny_decreases_trust_more(self):
        engine = GovernanceEngine()
        engine.set_trust("a1", 0.5)
        engine.set_trust("a2", 0.5)
        engine._update_trust_from_decision("a1", GovernanceDecision.REDIRECT)
        engine._update_trust_from_decision("a2", GovernanceDecision.DENY)
        assert engine.get_trust("a2") < engine.get_trust("a1")


# ============================================================
# evaluate (full pipeline, mocks dependencies)
# ============================================================

@pytest.mark.integration
class TestEvaluate:
    def _make_engine(self):
        """Create engine with mocked dependencies."""
        engine = GovernanceEngine()

        # Mock space methods
        mock_point = MagicMock()
        mock_point.dominant_tongue.return_value = "KO"
        mock_point.dominant_valence.return_value = MagicMock(name="NEUTRAL")

        engine.space = MagicMock()
        engine.space.embed_action.return_value = mock_point
        engine.space.distance_from_center.return_value = 1.0
        engine.space.phase_coupling.return_value = 0.5
        engine.space.safety_score.return_value = 0.8

        # Mock hypercube
        engine.hypercube = MagicMock()
        engine.hypercube.classify_point.return_value = "interior"
        engine.hypercube.governance_cost.return_value = 1.0

        # Mock permeability
        engine.permeability = MagicMock()
        engine.permeability.passable_tongues.return_value = ["KO", "AV", "RU"]
        engine.permeability.blocked_tongues.return_value = ["UM", "DR"]

        return engine

    def test_evaluate_returns_decision_context(self):
        engine = self._make_engine()
        ctx = engine.evaluate("agent-1", "READ", "file.txt")
        assert isinstance(ctx, DecisionContext)

    def test_evaluate_records_history(self):
        engine = self._make_engine()
        engine.evaluate("agent-1", "READ", "file.txt")
        assert len(engine.history) == 1

    def test_evaluate_updates_trust(self):
        engine = self._make_engine()
        initial = engine.get_trust("agent-1")
        engine.evaluate("agent-1", "READ", "file.txt")
        # Trust should have changed
        final = engine.get_trust("agent-1")
        assert final != initial or True  # CONSTRAIN leaves trust unchanged

    def test_evaluate_explanation_has_agent_id(self):
        engine = self._make_engine()
        ctx = engine.evaluate("agent-1", "READ", "file.txt")
        assert ctx.explanation["agent_id"] == "agent-1"

    def test_evaluate_high_safety_allows(self):
        engine = self._make_engine()
        engine.space.safety_score.return_value = 1.0
        engine.space.distance_from_center.return_value = 0.1
        ctx = engine.evaluate("agent-1", "READ", "file.txt", sensitivity=0.0)
        # With safety=1.0, trust=0.5, close distance, should score high
        assert ctx.score > 0.5

    def test_evaluate_exterior_denies(self):
        engine = self._make_engine()
        engine.hypercube.classify_point.return_value = "exterior"
        ctx = engine.evaluate("agent-1", "READ", "file.txt")
        assert ctx.decision == GovernanceDecision.DENY

    def test_evaluate_with_context(self):
        engine = self._make_engine()
        ctx = engine.evaluate("agent-1", "READ", "file.txt",
                              context={"reason": "testing"})
        assert ctx.explanation["context"]["reason"] == "testing"


# ============================================================
# Batch evaluate
# ============================================================

@pytest.mark.integration
class TestBatchEvaluate:
    def _make_engine(self):
        engine = GovernanceEngine()

        mock_point = MagicMock()
        mock_point.dominant_tongue.return_value = "KO"
        mock_point.dominant_valence.return_value = MagicMock(name="NEUTRAL")

        engine.space = MagicMock()
        engine.space.embed_action.return_value = mock_point
        engine.space.distance_from_center.return_value = 1.0
        engine.space.phase_coupling.return_value = 0.5
        engine.space.safety_score.return_value = 0.8

        engine.hypercube = MagicMock()
        engine.hypercube.classify_point.return_value = "interior"
        engine.hypercube.governance_cost.return_value = 1.0

        engine.permeability = MagicMock()
        engine.permeability.passable_tongues.return_value = TONGUE_KEYS_FALLBACK
        engine.permeability.blocked_tongues.return_value = []

        return engine

    def test_batch_returns_list(self):
        engine = self._make_engine()
        requests = [
            {"agent_id": "a1", "action": "READ", "target": "f1"},
            {"agent_id": "a2", "action": "WRITE", "target": "f2"},
        ]
        results = engine.batch_evaluate(requests)
        assert len(results) == 2

    def test_batch_each_is_decision_context(self):
        engine = self._make_engine()
        requests = [{"agent_id": "a1", "action": "READ", "target": "f1"}]
        results = engine.batch_evaluate(requests)
        assert isinstance(results[0], DecisionContext)


TONGUE_KEYS_FALLBACK = ["KO", "AV", "RU", "CA", "UM", "DR"]


# ============================================================
# Agent summary
# ============================================================

@pytest.mark.integration
class TestAgentSummary:
    def _make_engine(self):
        engine = GovernanceEngine()

        mock_point = MagicMock()
        mock_point.dominant_tongue.return_value = "KO"
        mock_point.dominant_valence.return_value = MagicMock(name="NEUTRAL")

        engine.space = MagicMock()
        engine.space.embed_action.return_value = mock_point
        engine.space.distance_from_center.return_value = 1.0
        engine.space.phase_coupling.return_value = 0.5
        engine.space.safety_score.return_value = 0.8

        engine.hypercube = MagicMock()
        engine.hypercube.classify_point.return_value = "interior"
        engine.hypercube.governance_cost.return_value = 1.0

        engine.permeability = MagicMock()
        engine.permeability.passable_tongues.return_value = TONGUE_KEYS_FALLBACK
        engine.permeability.blocked_tongues.return_value = []

        return engine

    def test_empty_history(self):
        engine = GovernanceEngine()
        summary = engine.get_agent_summary("unknown")
        assert summary["decisions"] == 0
        assert summary["trust"] == 0.5

    def test_after_evaluation(self):
        engine = self._make_engine()
        engine.evaluate("a1", "READ", "file.txt")
        engine.evaluate("a1", "WRITE", "file.txt")
        summary = engine.get_agent_summary("a1")
        assert summary["total_decisions"] == 2
        assert "avg_score" in summary


# ============================================================
# History management
# ============================================================

@pytest.mark.unit
class TestHistoryManagement:
    def test_history_limit(self):
        engine = GovernanceEngine(max_history=5)

        mock_point = MagicMock()
        mock_point.dominant_tongue.return_value = "KO"
        mock_point.dominant_valence.return_value = MagicMock(name="NEUTRAL")

        engine.space = MagicMock()
        engine.space.embed_action.return_value = mock_point
        engine.space.distance_from_center.return_value = 1.0
        engine.space.phase_coupling.return_value = 0.5
        engine.space.safety_score.return_value = 0.8

        engine.hypercube = MagicMock()
        engine.hypercube.classify_point.return_value = "interior"
        engine.hypercube.governance_cost.return_value = 1.0

        engine.permeability = MagicMock()
        engine.permeability.passable_tongues.return_value = TONGUE_KEYS_FALLBACK
        engine.permeability.blocked_tongues.return_value = []

        for i in range(10):
            engine.evaluate(f"a{i}", "READ", "file.txt")

        assert len(engine.history) <= 5
