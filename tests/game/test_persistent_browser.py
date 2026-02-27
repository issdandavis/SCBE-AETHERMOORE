"""
@file test_persistent_browser.py
@module tests/game
@layer Layer 12, Layer 13

Tests for the PersistentBrowserLimb governance and configuration.

These tests validate:
  - Governance pipeline (harmonic wall, domain safety, risk decisions)
  - PersistentFinger configuration (userDataDir isolation)
  - Session risk accumulation and decay
  - Audit log recording
  - Limb status reporting

Note: These are unit tests that do NOT require a running browser.
      They test the governance and configuration logic only.
"""

import math
import shutil
import tempfile
from pathlib import Path

import pytest

# Ensure src/ is importable
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.browser.persistent_limb import (
    GovernanceDecision,
    GovernanceResult,
    PersistentBrowserLimb,
    PersistentFinger,
    PersistentFingerStats,
    TONGUE_WEIGHT,
    TONGUES,
    check_domain_safety,
    evaluate_browser_action,
    harmonic_wall,
)

PHI = (1 + math.sqrt(5)) / 2


# ── Harmonic Wall Tests ───────────────────────────────────────────────


class TestHarmonicWall:
    """L12: Harmonic Wall cost function."""

    def test_zero_distance_returns_R(self):
        """At d*=0, cost = R · π^0 = R."""
        assert harmonic_wall(0.0, R=1.0) == pytest.approx(1.0)
        assert harmonic_wall(0.0, R=5.0) == pytest.approx(5.0)

    def test_cost_increases_with_distance(self):
        """Cost grows monotonically with d*."""
        costs = [harmonic_wall(d) for d in [0.0, 0.5, 1.0, 1.5, 2.0]]
        for i in range(len(costs) - 1):
            assert costs[i] < costs[i + 1], f"Cost must increase: {costs}"

    def test_exponential_growth(self):
        """Safe is cheap, danger is exponential."""
        w_safe = harmonic_wall(0.1)
        w_danger = harmonic_wall(2.5)
        ratio = w_danger / w_safe
        assert ratio > 50, f"Expected >50x cost ratio, got {ratio:.1f}x"

    def test_formula_accuracy(self):
        """H(d*, R) = R · π^(φ · d*)."""
        d_star = 1.0
        R = 2.0
        expected = R * (math.pi ** (PHI * d_star))
        assert harmonic_wall(d_star, R) == pytest.approx(expected)

    def test_R_scaling(self):
        """Cost scales linearly with R."""
        d = 1.5
        assert harmonic_wall(d, R=2.0) == pytest.approx(2.0 * harmonic_wall(d, R=1.0))


# ── Domain Safety Tests ───────────────────────────────────────────────


class TestDomainSafety:
    """RU tongue domain checking."""

    def test_trusted_domain_allowed(self):
        decision, risk = check_domain_safety("https://github.com/anthropics")
        assert decision == "ALLOW"
        assert risk == 0.0

    def test_blocked_domain_denied(self):
        decision, risk = check_domain_safety("https://malware.com/payload")
        assert decision == "DENY"
        assert risk == 1.0

    def test_unknown_domain_quarantined(self):
        decision, risk = check_domain_safety("https://random-blog.example.org")
        assert decision == "QUARANTINE"
        assert risk == 0.5

    def test_trusted_domains_list(self):
        """All trusted domains should be ALLOW."""
        trusted = [
            "https://github.com",
            "https://huggingface.co",
            "https://arxiv.org",
            "https://scholar.google.com",
            "https://stackoverflow.com",
            "https://docs.python.org",
            "https://pypi.org",
        ]
        for url in trusted:
            decision, _ = check_domain_safety(url)
            assert decision == "ALLOW", f"{url} should be ALLOW"


# ── Governance Pipeline Tests ─────────────────────────────────────────


class TestGovernancePipeline:
    """L13: Full governance evaluation."""

    def test_trusted_navigate_is_allowed(self):
        result = evaluate_browser_action("KO", "https://github.com", "navigate")
        assert result.decision == GovernanceDecision.ALLOW
        assert result.risk_score < 0.30

    def test_blocked_domain_is_denied(self):
        result = evaluate_browser_action("CA", "https://malware.com", "navigate")
        assert result.decision == GovernanceDecision.DENY
        assert result.risk_score == 1.0
        assert result.harmonic_cost == float("inf")

    def test_unknown_domain_is_quarantined(self):
        result = evaluate_browser_action("AV", "https://unknown-site.example", "navigate")
        assert result.decision in (GovernanceDecision.QUARANTINE, GovernanceDecision.ALLOW)
        assert result.risk_score > 0.0

    def test_js_execution_is_high_risk(self):
        """run_js on unknown domain should be QUARANTINE or ESCALATE."""
        result = evaluate_browser_action("DR", "https://unknown-site.example", "run_js")
        assert result.decision in (GovernanceDecision.QUARANTINE, GovernanceDecision.ESCALATE)
        assert result.risk_score > 0.30

    def test_session_risk_increases_cost(self):
        """Higher session risk → higher composite risk."""
        r1 = evaluate_browser_action("KO", "https://github.com", "navigate", session_risk=0.0)
        r2 = evaluate_browser_action("KO", "https://github.com", "navigate", session_risk=0.8)
        assert r2.risk_score > r1.risk_score

    def test_tongue_weight_affects_risk(self):
        """DR (weight 11.09) carries more risk than KO (weight 1.0)."""
        r_ko = evaluate_browser_action("KO", "https://github.com", "navigate")
        r_dr = evaluate_browser_action("DR", "https://github.com", "navigate")
        assert r_dr.risk_score > r_ko.risk_score

    def test_governance_result_fields(self):
        """GovernanceResult has all required fields."""
        result = evaluate_browser_action("CA", "https://github.com", "navigate")
        assert isinstance(result.decision, GovernanceDecision)
        assert isinstance(result.risk_score, float)
        assert isinstance(result.harmonic_cost, float)
        assert result.tongue == "CA"
        assert result.url == "https://github.com"
        assert result.domain_decision == "ALLOW"
        assert isinstance(result.explanation, str)


# ── PersistentFinger Configuration Tests ──────────────────────────────


class TestPersistentFingerConfig:
    """Test finger setup without launching browsers."""

    def test_all_tongues_have_weights(self):
        for t in TONGUES:
            assert t in TONGUE_WEIGHT
            assert TONGUE_WEIGHT[t] > 0

    def test_phi_scaling(self):
        """Weights scale approximately by golden ratio."""
        weights = [TONGUE_WEIGHT[t] for t in TONGUES]
        for i in range(1, len(weights)):
            ratio = weights[i] / weights[i - 1]
            # Allow ~15% tolerance from PHI
            assert abs(ratio - PHI) < 0.3, f"Weight ratio {ratio} too far from PHI={PHI}"

    def test_finger_weight_property(self):
        finger = PersistentFinger(
            tongue="CA",
            user_data_dir=Path("/tmp/test"),
        )
        assert finger.weight == TONGUE_WEIGHT["CA"]

    def test_finger_starts_inactive(self):
        finger = PersistentFinger(
            tongue="KO",
            user_data_dir=Path("/tmp/test"),
        )
        assert finger.active is False
        assert finger.stats.actions == 0
        assert finger.stats.blocked == 0


# ── PersistentBrowserLimb Configuration Tests ─────────────────────────


class TestPersistentBrowserLimb:
    """Test limb configuration and governance without browsers."""

    def setup_method(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="hydra_test_"))
        self.limb = PersistentBrowserLimb(
            session_id="test-alpha",
            session_root=self.tmp_dir,
            governance_enabled=True,
        )

    def teardown_method(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_creates_all_six_fingers(self):
        assert len(self.limb.fingers) == 6
        for t in TONGUES:
            assert t in self.limb.fingers

    def test_user_data_dirs_are_isolated(self):
        """Each tongue gets its own userDataDir."""
        dirs = {t: f.user_data_dir for t, f in self.limb.fingers.items()}
        # All dirs should be unique
        assert len(set(str(d) for d in dirs.values())) == 6
        # All under session root
        for d in dirs.values():
            assert str(d).startswith(str(self.tmp_dir))

    def test_user_data_dir_structure(self):
        """Dir pattern: {root}/{session_id}/{tongue}."""
        ko_dir = self.limb.fingers["KO"].user_data_dir
        assert ko_dir == self.tmp_dir / "test-alpha" / "ko"

    def test_governance_blocks_malicious_domains(self):
        """Governance gate blocks DENY'd domains."""
        gov = self.limb._gate("CA", "https://malware.com", "navigate")
        assert gov.decision == GovernanceDecision.DENY

    def test_governance_allows_trusted_domains(self):
        gov = self.limb._gate("KO", "https://github.com", "navigate")
        assert gov.decision == GovernanceDecision.ALLOW

    def test_session_risk_accumulates_on_deny(self):
        initial_risk = self.limb._session_risk
        self.limb._gate("CA", "https://malware.com", "navigate")
        assert self.limb._session_risk > initial_risk

    def test_session_risk_decays_on_allow(self):
        self.limb._session_risk = 0.5
        self.limb._gate("KO", "https://github.com", "navigate")
        assert self.limb._session_risk < 0.5

    def test_audit_log_records_entries(self):
        assert len(self.limb._audit_log) == 0
        self.limb._gate("KO", "https://github.com", "navigate")
        assert len(self.limb._audit_log) == 1
        entry = self.limb._audit_log[0]
        assert entry["session_id"] == "test-alpha"
        assert entry["tongue"] == "KO"
        assert entry["decision"] == "ALLOW"
        assert "risk_score" in entry
        assert "harmonic_cost" in entry

    def test_status_report(self):
        status = self.limb.status()
        assert status["session_id"] == "test-alpha"
        assert status["open"] is False
        assert len(status["fingers"]) == 6
        for tongue, info in status["fingers"].items():
            assert "active" in info
            assert "weight" in info
            assert "user_data_dir" in info

    def test_custom_tongue_subset(self):
        """Can create a limb with only specific tongues."""
        limb = PersistentBrowserLimb(
            session_id="subset",
            session_root=self.tmp_dir,
            tongues=["KO", "CA"],
        )
        assert len(limb.fingers) == 2
        assert "KO" in limb.fingers
        assert "CA" in limb.fingers
        assert "AV" not in limb.fingers

    def test_get_finger_rejects_invalid_tongue(self):
        # Finger is not active so this should raise
        with pytest.raises(ValueError, match="Unknown tongue"):
            self.limb._get_finger("XX")

    def test_purge_session_creates_and_deletes(self):
        """purge_session cleans up userDataDir."""
        # Create the dirs first
        ko_dir = self.limb.fingers["KO"].user_data_dir
        ko_dir.mkdir(parents=True, exist_ok=True)
        (ko_dir / "test_cookie.db").write_text("test")
        assert ko_dir.exists()

        self.limb.purge_session("KO")
        assert not ko_dir.exists()

    def test_governance_disabled_skips_checks(self):
        """When governance_enabled=False, gate is not called in navigate."""
        limb = PersistentBrowserLimb(
            session_id="no-gov",
            session_root=self.tmp_dir,
            governance_enabled=False,
        )
        # With governance disabled, audit log stays empty
        assert len(limb._audit_log) == 0


# ── Integration Smoke Tests (no browser needed) ──────────────────────


class TestGovernanceIntegration:
    """End-to-end governance pipeline smoke tests."""

    def test_research_workflow_cost_budget(self):
        """Simulate a research workflow and verify cost stays bounded."""
        limb = PersistentBrowserLimb(
            session_id="cost-test",
            session_root=Path(tempfile.mkdtemp()),
        )

        # Simulate 10 trusted navigations
        total_cost = 0.0
        for _ in range(10):
            gov = limb._gate("CA", "https://arxiv.org/abs/2401.00001", "navigate")
            assert gov.decision == GovernanceDecision.ALLOW
            total_cost += gov.harmonic_cost

        # Trusted domain navigations should be cheap
        avg_cost = total_cost / 10
        assert avg_cost < 5.0, f"Average cost {avg_cost} too high for trusted domain"

    def test_adversarial_escalation(self):
        """Repeated blocks should escalate session risk."""
        limb = PersistentBrowserLimb(
            session_id="escalation-test",
            session_root=Path(tempfile.mkdtemp()),
        )

        # Hit blocked domains repeatedly
        for _ in range(5):
            limb._gate("RU", "https://malware.com", "navigate")

        # Session risk should have accumulated
        assert limb._session_risk > 0.5, f"Session risk {limb._session_risk} too low after 5 denials"

    def test_mixed_workflow_audit_trail(self):
        """Audit trail captures all decisions correctly."""
        limb = PersistentBrowserLimb(
            session_id="audit-test",
            session_root=Path(tempfile.mkdtemp()),
        )

        limb._gate("KO", "https://github.com", "navigate")
        limb._gate("CA", "https://malware.com", "navigate")
        limb._gate("AV", "https://unknown.example", "navigate")

        log = limb.get_audit_log()
        assert len(log) == 3
        assert log[0]["decision"] == "ALLOW"
        assert log[1]["decision"] == "DENY"
        assert log[2]["decision"] in ("QUARANTINE", "ALLOW")
