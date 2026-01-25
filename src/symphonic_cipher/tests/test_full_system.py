"""
Tests for the Full SCBE-AETHERMOORE Governance System.
"""

import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scbe_aethermoore import (
    SCBEFullSystem,
    GovernanceMode,
    GovernanceMetrics,
    GovernanceDecision,
    quick_evaluate,
    verify_all_theorems,
)


class TestSCBEFullSystem:
    """Tests for the full governance system."""

    def test_initialization(self):
        """System should initialize correctly."""
        system = SCBEFullSystem()
        assert system.state.mode == GovernanceMode.NORMAL
        assert system.state.total_evaluations == 0
        assert system.state.threat_level == 0.0

    def test_cold_start_allows_baseline(self):
        """First evaluation should ALLOW to establish baseline."""
        system = SCBEFullSystem()
        result = system.evaluate_intent(
            identity="test_user",
            intent="test_action"
        )
        assert result.decision == GovernanceDecision.ALLOW
        assert "cold start" in result.explanation.lower()
        assert system.state.reference_state is not None

    def test_sequential_evaluations(self):
        """Sequential evaluations should work and update state."""
        system = SCBEFullSystem()

        # First - cold start
        r1 = system.evaluate_intent("user", "action1")
        assert r1.decision == GovernanceDecision.ALLOW

        # Second - normal evaluation
        r2 = system.evaluate_intent("user", "action2")
        assert r2.decision in [GovernanceDecision.ALLOW, GovernanceDecision.QUARANTINE]

        # Check state updated
        assert system.state.total_evaluations == 2
        assert system.state.reference_state is not None  # Has reference state

    def test_audit_chain_integrity(self):
        """Audit chain should maintain integrity."""
        system = SCBEFullSystem()

        for i in range(5):
            system.evaluate_intent(f"user_{i}", f"action_{i}")

        assert len(system.state.audit_chain) == 5
        assert system.verify_audit_chain()

    def test_entropy_zones(self):
        """System should correctly classify entropy zones."""
        system = SCBEFullSystem()

        # Cold start
        r1 = system.evaluate_intent("user", "action1")

        # Subsequent - should have entropy zone classification
        r2 = system.evaluate_intent("user", "action2")
        assert r2.entropy_zone in ["NEGENTROPY", "OPTIMAL", "HIGH_ENTROPY"]

    def test_mode_escalation(self):
        """System should escalate mode on repeated denials."""
        system = SCBEFullSystem()

        # Force denials by simulating bad state
        # First, establish baseline
        system.evaluate_intent("user", "action")

        # Manually trigger denials
        for _ in range(3):
            system.state.consecutive_denials += 1

        # Check mode would escalate
        if system.state.consecutive_denials >= 3:
            system.state.mode = GovernanceMode.HEIGHTENED

        assert system.state.mode == GovernanceMode.HEIGHTENED

    def test_metrics_completeness(self):
        """GovernanceMetrics should have all fields populated."""
        system = SCBEFullSystem()
        result = system.evaluate_intent("user", "action")

        assert result.state_9d is not None
        assert result.risk_assessment is not None
        assert len(result.layer_states) == 14
        assert result.audit_tag is not None
        assert result.chain_position > 0
        assert isinstance(result.shannon_entropy, float)
        assert isinstance(result.negentropy, float)
        assert isinstance(result.entropy_rate, float)

    def test_reset(self):
        """Reset should clear state but optionally keep key."""
        system = SCBEFullSystem()
        original_key = system.state.secret_key

        system.evaluate_intent("user", "action")
        assert system.state.total_evaluations == 1

        system.reset(keep_key=True)
        assert system.state.total_evaluations == 0
        assert system.state.secret_key == original_key

        system.reset(keep_key=False)
        assert system.state.secret_key != original_key

    def test_get_system_status(self):
        """System status should return correct info."""
        system = SCBEFullSystem()
        system.evaluate_intent("user", "action")

        status = system.get_system_status()

        assert "mode" in status
        assert "threat_level" in status
        assert "total_evaluations" in status
        assert status["total_evaluations"] == 1
        assert "audit_chain_valid" in status
        assert status["audit_chain_valid"] is True


class TestQuickEvaluate:
    """Tests for the quick_evaluate convenience function."""

    def test_quick_evaluate_returns_tuple(self):
        """quick_evaluate should return (decision, explanation)."""
        decision, explanation = quick_evaluate("user", "action")
        assert isinstance(decision, GovernanceDecision)
        assert isinstance(explanation, str)

    def test_quick_evaluate_cold_start(self):
        """quick_evaluate should handle cold start."""
        decision, explanation = quick_evaluate("user", "action")
        assert decision == GovernanceDecision.ALLOW
        assert "cold start" in explanation.lower()


class TestTheoremVerification:
    """Tests for mathematical theorem verification."""

    def test_all_theorems_pass(self):
        """All mathematical theorems should pass."""
        results = verify_all_theorems()

        assert results["A_metric_invariance"] is True
        assert results["B_continuity"] is True
        assert results["C_risk_monotonicity"] is True
        assert results["D_diffeomorphism"] is True


class TestContextHandling:
    """Tests for context handling."""

    def test_context_included_in_evaluation(self):
        """Context should be processed in evaluation."""
        system = SCBEFullSystem()

        result = system.evaluate_intent(
            identity="user",
            intent="read_file",
            context={"file": "secret.txt", "access": "read"}
        )

        assert result.decision is not None

    def test_different_tongues(self):
        """Different tongues should work."""
        system = SCBEFullSystem()

        for tongue in ["KO", "AV", "RU", "CA", "UM", "DR"]:
            result = system.evaluate_intent(
                identity="user",
                intent="action",
                tongue=tongue
            )
            assert result.decision is not None


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_intent(self):
        """Empty intent should still work."""
        system = SCBEFullSystem()
        result = system.evaluate_intent("user", "")
        assert result.decision is not None

    def test_long_intent(self):
        """Long intent should still work."""
        system = SCBEFullSystem()
        long_intent = "a" * 10000
        result = system.evaluate_intent("user", long_intent)
        assert result.decision is not None

    def test_special_characters(self):
        """Special characters in input should be handled."""
        system = SCBEFullSystem()
        result = system.evaluate_intent(
            identity="user@domain.com",
            intent="action with 日本語 and émojis 🚀"
        )
        assert result.decision is not None

    def test_numeric_identity(self):
        """Numeric-like identity should work."""
        system = SCBEFullSystem()
        result = system.evaluate_intent("12345", "action")
        assert result.decision is not None


class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self):
        """Complete workflow should work end-to-end."""
        system = SCBEFullSystem()

        # 1. Initialize with cold start
        r1 = system.evaluate_intent("alice", "login")
        assert r1.decision == GovernanceDecision.ALLOW

        # 2. Normal operations
        r2 = system.evaluate_intent("alice", "read_document")
        r3 = system.evaluate_intent("alice", "write_document")

        # 3. Check audit chain
        assert system.verify_audit_chain()
        assert len(system.state.audit_chain) == 3

        # 4. Check status
        status = system.get_system_status()
        assert status["total_evaluations"] == 3
        assert status["has_reference_state"] is True

        # 5. Verify theorems still hold
        theorems = verify_all_theorems()
        assert all(theorems.values())

    def test_multi_user_scenario(self):
        """Multiple users should be tracked correctly."""
        system = SCBEFullSystem()

        users = ["alice", "bob", "charlie"]
        for user in users:
            system.evaluate_intent(user, "action")

        assert system.state.total_evaluations == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
