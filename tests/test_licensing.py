"""
Comprehensive tests for the SCBE Licensing & Monetization module.

Covers:
  1. OEM License — Key generation, validation, tiers, expiration, quotas
  2. Usage Meter — Decision tracking, revenue estimation, SLOs, quotas
  3. NIST AI RMF — Compliance report generation, function coverage

@module tests/test_licensing
"""

import json
import sys
import os
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.licensing.oem_license import (
    LicenseTier,
    LicenseModel,
    LicenseClaims,
    LicenseKey,
    generate_license_key,
    validate_license_key,
    create_tier_license,
    TIER_DEFAULTS,
)
from src.licensing.usage_meter import (
    UsageMeter,
    DecisionRecord,
    DEFAULT_RATE_PER_1K_DECISIONS,
    DEFAULT_PLATFORM_FLOOR_MONTHLY,
    DEFAULT_AGENT_BUNDLE_MONTHLY,
    TARGET_FALSE_QUARANTINE_RATE,
)
from src.licensing.nist_ai_rmf import (
    RMFFunction,
    generate_compliance_report,
    TradeWindsProfile,
    SBIRDeliverable,
    generate_policy_framework_report,
    generate_combined_compliance_summary,
)


SIGNING_SECRET = "test-secret-key-do-not-use-in-production"


# ============================================================================
# OEM License Tests
# ============================================================================

class TestLicenseTiers:
    """Verify tier definitions match CUSTOMER_LICENSE_AGREEMENT.md."""

    def test_homebrew_limits(self):
        d = TIER_DEFAULTS[LicenseTier.HOMEBREW]
        assert d["max_authorized_users"] == 1
        assert d["max_deployment_instances"] == 1
        assert d["max_swarm_agents"] == 3
        assert d["support_level"] == "community"
        assert d["white_label"] is False

    def test_professional_limits(self):
        d = TIER_DEFAULTS[LicenseTier.PROFESSIONAL]
        assert d["max_authorized_users"] == 10
        assert d["max_deployment_instances"] == 5
        assert d["max_swarm_agents"] == 12
        assert d["support_level"] == "email"

    def test_enterprise_unlimited(self):
        d = TIER_DEFAULTS[LicenseTier.ENTERPRISE]
        assert d["max_authorized_users"] == 0  # unlimited
        assert d["max_deployment_instances"] == 0
        assert d["max_swarm_agents"] == 0
        assert d["support_level"] == "dedicated"
        assert d["air_gap_approved"] is True

    def test_oem_white_label(self):
        d = TIER_DEFAULTS[LicenseTier.OEM]
        assert d["white_label"] is True
        assert d["support_level"] == "none"
        assert d["air_gap_approved"] is True
        assert "gateway" in d["modules"]

    def test_source_available_no_support(self):
        d = TIER_DEFAULTS[LicenseTier.SOURCE_AVAILABLE]
        assert d["support_level"] == "none"
        assert d["white_label"] is False
        assert d["air_gap_approved"] is True

    def test_all_tiers_have_defaults(self):
        for tier in LicenseTier:
            assert tier in TIER_DEFAULTS


class TestLicenseKeyGeneration:
    """Test key generation and signing."""

    def test_generate_key(self):
        claims = LicenseClaims(
            licensee="TestCorp",
            tier="homebrew",
            model="subscription",
            issued_at=time.time(),
            expires_at=time.time() + 86400 * 365,
        )
        key = generate_license_key(claims, SIGNING_SECRET)
        assert key.signature != ""
        assert len(key.signature) == 64  # SHA-256 hex

    def test_create_tier_license(self):
        key = create_tier_license(
            LicenseTier.PROFESSIONAL,
            "AcmeSecurity",
            signing_secret=SIGNING_SECRET,
        )
        assert key.claims.licensee == "AcmeSecurity"
        assert key.claims.tier == "professional"
        assert key.claims.max_authorized_users == 10

    def test_oem_license_has_gateway(self):
        key = create_tier_license(
            LicenseTier.OEM, "WhiteLabelInc",
            signing_secret=SIGNING_SECRET,
        )
        assert key.claims.white_label is True
        assert "gateway" in key.claims.modules

    def test_perpetual_license(self):
        key = create_tier_license(
            LicenseTier.ENTERPRISE, "GovCorp",
            model=LicenseModel.PERPETUAL,
            duration_days=0,
            signing_secret=SIGNING_SECRET,
        )
        assert key.claims.expires_at == 0.0

    def test_key_serialization_roundtrip(self):
        key = create_tier_license(
            LicenseTier.HOMEBREW, "TestCo",
            signing_secret=SIGNING_SECRET,
        )
        json_str = key.to_json()
        restored = LicenseKey.from_json(json_str)
        assert restored.signature == key.signature
        assert restored.claims.licensee == "TestCo"


class TestLicenseValidation:
    """Test runtime license validation."""

    def test_valid_license(self):
        key = create_tier_license(
            LicenseTier.PROFESSIONAL, "ValidCorp",
            signing_secret=SIGNING_SECRET,
        )
        result = validate_license_key(key, SIGNING_SECRET)
        assert result.valid is True
        assert result.reason == "VALID"
        assert result.tier == "professional"

    def test_invalid_signature(self):
        key = create_tier_license(
            LicenseTier.HOMEBREW, "BadCorp",
            signing_secret=SIGNING_SECRET,
        )
        result = validate_license_key(key, "wrong-secret")
        assert result.valid is False
        assert result.reason == "INVALID_SIGNATURE"

    def test_expired_license(self):
        claims = LicenseClaims(
            licensee="ExpiredCorp",
            tier="homebrew",
            model="subscription",
            issued_at=time.time() - 86400 * 400,
            expires_at=time.time() - 86400,  # expired yesterday
        )
        key = generate_license_key(claims, SIGNING_SECRET)
        result = validate_license_key(key, SIGNING_SECRET)
        assert result.valid is False
        assert result.reason == "LICENSE_EXPIRED"

    def test_quota_exceeded(self):
        key = create_tier_license(
            LicenseTier.HOMEBREW, "QuotaCorp",
            signing_secret=SIGNING_SECRET,
        )
        # Homebrew has 10,000 decisions/month
        result = validate_license_key(key, SIGNING_SECRET, current_decisions_this_month=10_001)
        assert result.valid is False
        assert result.reason == "DECISION_QUOTA_EXCEEDED"

    def test_quota_warning(self):
        key = create_tier_license(
            LicenseTier.HOMEBREW, "NearQuotaCorp",
            signing_secret=SIGNING_SECRET,
        )
        result = validate_license_key(key, SIGNING_SECRET, current_decisions_this_month=9_500)
        assert result.valid is True
        assert len(result.warnings) > 0
        assert "remaining" in result.warnings[0].lower()

    def test_enterprise_unlimited_quota(self):
        key = create_tier_license(
            LicenseTier.ENTERPRISE, "UnlimitedCorp",
            signing_secret=SIGNING_SECRET,
        )
        result = validate_license_key(key, SIGNING_SECRET, current_decisions_this_month=999_999)
        assert result.valid is True
        assert result.remaining_decisions is None  # unlimited

    def test_expiration_warning(self):
        claims = LicenseClaims(
            licensee="SoonCorp",
            tier="professional",
            model="subscription",
            issued_at=time.time(),
            expires_at=time.time() + 86400 * 15,  # 15 days
        )
        key = generate_license_key(claims, SIGNING_SECRET)
        result = validate_license_key(key, SIGNING_SECRET)
        assert result.valid is True
        assert any("expires" in w.lower() for w in result.warnings)

    def test_modules_list_returned(self):
        key = create_tier_license(
            LicenseTier.OEM, "ModularCorp",
            signing_secret=SIGNING_SECRET,
        )
        result = validate_license_key(key, SIGNING_SECRET)
        assert "gateway" in result.modules
        assert "core" in result.modules


# ============================================================================
# Usage Meter Tests
# ============================================================================

class TestUsageMeter:
    """Test per-decision usage metering."""

    @pytest.fixture
    def meter(self):
        return UsageMeter()

    @pytest.fixture
    def sample_record(self):
        return DecisionRecord(
            timestamp=time.time(),
            tenant_id="tenant-001",
            agent_id="agent-a",
            decision="ALLOW",
            latency_ms=45.0,
            risk_score=0.15,
            policy_ids=["POL-001"],
        )

    def test_record_decision(self, meter, sample_record):
        meter.record_decision(sample_record)
        assert meter.total_decisions == 1
        assert meter.billable_decisions == 1

    def test_non_billable_decision(self, meter):
        record = DecisionRecord(
            timestamp=time.time(),
            tenant_id="tenant-001",
            agent_id="agent-a",
            decision="ALLOW",
            latency_ms=30.0,
            risk_score=0.1,
            policy_ids=[],
            billable=False,
        )
        meter.record_decision(record)
        assert meter.total_decisions == 1
        assert meter.billable_decisions == 0

    def test_tenant_tracking(self, meter):
        for i in range(5):
            meter.record_decision(DecisionRecord(
                timestamp=time.time(),
                tenant_id="tenant-001",
                agent_id=f"agent-{i % 3}",
                decision="ALLOW",
                latency_ms=40.0,
                risk_score=0.1,
                policy_ids=[],
            ))
        assert meter.tenant_decisions("tenant-001") == 5
        assert meter.tenant_agents("tenant-001") == 3

    def test_multi_tenant(self, meter):
        for tenant in ["t1", "t2", "t3"]:
            meter.record_decision(DecisionRecord(
                timestamp=time.time(),
                tenant_id=tenant,
                agent_id="agent-a",
                decision="ALLOW",
                latency_ms=50.0,
                risk_score=0.1,
                policy_ids=[],
            ))
        assert meter.unique_tenants == 3

    def test_decision_distribution(self, meter):
        for decision in ["ALLOW", "ALLOW", "QUARANTINE", "DENY"]:
            meter.record_decision(DecisionRecord(
                timestamp=time.time(),
                tenant_id="t1",
                agent_id="a1",
                decision=decision,
                latency_ms=50.0,
                risk_score=0.5,
                policy_ids=[],
            ))
        dist = meter.decision_distribution
        assert dist["ALLOW"] == 2
        assert dist["QUARANTINE"] == 1
        assert dist["DENY"] == 1

    def test_false_quarantine_rate(self, meter):
        for _ in range(98):
            meter.record_decision(DecisionRecord(
                timestamp=time.time(), tenant_id="t1", agent_id="a1",
                decision="ALLOW", latency_ms=50.0, risk_score=0.1, policy_ids=[],
            ))
        meter.record_decision(DecisionRecord(
            timestamp=time.time(), tenant_id="t1", agent_id="a1",
            decision="QUARANTINE", latency_ms=50.0, risk_score=0.5, policy_ids=[],
        ))
        # 1 out of 99 = ~1.01%
        assert meter.false_quarantine_rate < TARGET_FALSE_QUARANTINE_RATE

    def test_p95_latency(self, meter):
        for i in range(100):
            meter.record_decision(DecisionRecord(
                timestamp=time.time(), tenant_id="t1", agent_id="a1",
                decision="ALLOW", latency_ms=float(i), risk_score=0.1, policy_ids=[],
            ))
        p95 = meter.p95_latency_ms
        assert p95 == 95.0  # 95th percentile of 0-99

    def test_revenue_estimation(self, meter):
        for i in range(1000):
            meter.record_decision(DecisionRecord(
                timestamp=time.time(), tenant_id="t1", agent_id="a1",
                decision="ALLOW", latency_ms=50.0, risk_score=0.1, policy_ids=[],
            ))
        rev = meter.estimate_revenue()
        assert rev["decisions_counted"] == 1000
        assert rev["decision_revenue"] == DEFAULT_RATE_PER_1K_DECISIONS
        assert rev["platform_revenue"] == DEFAULT_PLATFORM_FLOOR_MONTHLY
        assert rev["agent_revenue"] == DEFAULT_AGENT_BUNDLE_MONTHLY
        assert rev["total_estimated"] > 0

    def test_per_tenant_revenue(self, meter):
        for i in range(500):
            meter.record_decision(DecisionRecord(
                timestamp=time.time(), tenant_id="t1", agent_id="a1",
                decision="ALLOW", latency_ms=50.0, risk_score=0.1, policy_ids=[],
            ))
        rev = meter.estimate_revenue(tenant_id="t1")
        assert rev["tenants_counted"] == 1

    def test_quota_check(self, meter):
        for i in range(50):
            meter.record_decision(DecisionRecord(
                timestamp=time.time(), tenant_id="t1", agent_id="a1",
                decision="ALLOW", latency_ms=50.0, risk_score=0.1, policy_ids=[],
            ))
        within, remaining = meter.check_quota("t1", 100)
        assert within is True
        assert remaining == 50

    def test_quota_exceeded(self, meter):
        for i in range(101):
            meter.record_decision(DecisionRecord(
                timestamp=time.time(), tenant_id="t1", agent_id="a1",
                decision="ALLOW", latency_ms=50.0, risk_score=0.1, policy_ids=[],
            ))
        within, remaining = meter.check_quota("t1", 100)
        assert within is False
        assert remaining == 0

    def test_unlimited_quota(self, meter):
        within, remaining = meter.check_quota("t1", 0)  # 0 = unlimited
        assert within is True
        assert remaining == -1

    def test_slo_report(self, meter):
        for i in range(100):
            meter.record_decision(DecisionRecord(
                timestamp=time.time(), tenant_id="t1", agent_id="a1",
                decision="ALLOW", latency_ms=50.0, risk_score=0.1, policy_ids=[],
            ))
        slo = meter.slo_report()
        assert slo["p95_latency_pass"] is True
        assert slo["false_quarantine_pass"] is True
        assert slo["total_decisions"] == 100

    def test_export_usage_report(self, meter, sample_record):
        meter.record_decision(sample_record)
        report = meter.export_usage_report()
        assert "generated_at" in report
        assert "revenue_estimate" in report
        assert "slo_compliance" in report

    def test_export_jsonl(self, meter, sample_record):
        meter.record_decision(sample_record)
        jsonl = meter.export_records_jsonl()
        parsed = json.loads(jsonl)
        assert parsed["decision"] == "ALLOW"
        assert parsed["tenant_id"] == "tenant-001"

    def test_reset(self, meter, sample_record):
        meter.record_decision(sample_record)
        assert meter.total_decisions == 1
        meter.reset()
        assert meter.total_decisions == 0


# ============================================================================
# NIST AI RMF Tests
# ============================================================================

class TestNISTAIRMF:
    """Test NIST AI RMF compliance report generation."""

    @pytest.fixture
    def report(self):
        return generate_compliance_report()

    def test_report_generated(self, report):
        assert report.framework == "NIST AI RMF 1.0"
        assert report.system_name == "SCBE-AETHERMOORE"
        assert report.generated_at > 0

    def test_all_checks_pass(self, report):
        assert report.pass_rate == 1.0
        assert report.fail_count == 0

    def test_four_functions_covered(self, report):
        functions = set(c.function for c in report.checks)
        assert functions == {"GOVERN", "MAP", "MEASURE", "MANAGE"}

    def test_govern_checks(self, report):
        govern = report.by_function(RMFFunction.GOVERN)
        assert len(govern) >= 5  # Policies, accountability, risk tolerance, oversight, documentation

    def test_map_checks(self, report):
        mapped = report.by_function(RMFFunction.MAP)
        assert len(mapped) >= 4  # Context, risk categorization, data provenance, architecture

    def test_measure_checks(self, report):
        measured = report.by_function(RMFFunction.MEASURE)
        assert len(measured) >= 5  # Performance, bias, security, crypto, monitoring, audit

    def test_manage_checks(self, report):
        managed = report.by_function(RMFFunction.MANAGE)
        assert len(managed) >= 4  # Prioritization, incident response, risk response, fail-safe

    def test_total_check_count(self, report):
        assert report.total_checks >= 20

    def test_each_check_has_scbe_mapping(self, report):
        for check in report.checks:
            assert check.scbe_mapping != "", f"{check.check_id} missing SCBE mapping"

    def test_each_check_has_evidence(self, report):
        for check in report.checks:
            assert check.evidence != "", f"{check.check_id} missing evidence"

    def test_summary_structure(self, report):
        summary = report.summary()
        assert "framework" in summary
        assert "pass_rate" in summary
        assert "by_function" in summary
        assert summary["by_function"]["GOVERN"]["total"] >= 5

    def test_pqc_mentioned_in_crypto_check(self, report):
        crypto_checks = [c for c in report.checks if "cryptographic" in c.description.lower()]
        assert len(crypto_checks) >= 1
        assert any("ML-KEM" in c.evidence for c in crypto_checks)


class TestTradeWindsProfile:

    def test_default_profile(self):
        profile = TradeWindsProfile(company_name="Davis AI LLC")
        assert profile.technology_name == "SCBE-AETHERMOORE"
        assert profile.trl_level == 6
        assert len(profile.naics_codes) >= 3
        assert len(profile.certifications) >= 4
        assert len(profile.key_differentiators) >= 4

    def test_differentiators_include_hyperbolic(self):
        profile = TradeWindsProfile(company_name="Test")
        assert any("hyperbolic" in d.lower() for d in profile.key_differentiators)

    def test_differentiators_include_pqc(self):
        profile = TradeWindsProfile(company_name="Test")
        assert any("quantum" in d.lower() for d in profile.key_differentiators)

    def test_differentiators_include_air_gap(self):
        profile = TradeWindsProfile(company_name="Test")
        assert any("air-gap" in d.lower() for d in profile.key_differentiators)


class TestSBIRDeliverable:

    def test_default_deliverable(self):
        sbir = SBIRDeliverable()
        assert sbir.protection_period_years == 20
        assert "SBIR DATA RIGHTS" in sbir.marking
        assert len(sbir.technical_data_items) >= 6
        assert len(sbir.computer_software_items) >= 3

    def test_marking_includes_dfars(self):
        sbir = SBIRDeliverable()
        assert "DFARS 252.227-7018" in sbir.marking

    def test_technical_data_includes_pqc(self):
        sbir = SBIRDeliverable()
        assert any("quantum" in item.lower() for item in sbir.technical_data_items)


# ============================================================================
# White House National AI Policy Framework Tests
# ============================================================================

class TestPolicyFrameworkReport:
    """Test alignment to White House National AI Policy Framework (March 2026)."""

    @pytest.fixture
    def report(self):
        return generate_policy_framework_report()

    def test_report_generated(self, report):
        assert report.framework == "White House National AI Policy Framework"
        assert report.framework_date == "2026-03-20"
        assert report.generated_at > 0

    def test_all_five_pillars_covered(self, report):
        pillar_ids = set(p.pillar_id for p in report.pillars)
        assert pillar_ids == {"PILLAR-1", "PILLAR-2", "PILLAR-3", "PILLAR-4", "PILLAR-5"}

    def test_pillar_1_federal_preemption(self, report):
        p1 = report.by_pillar("PILLAR-1")
        assert len(p1) >= 2
        assert all(p.pillar_name == "Federal Preemption" for p in p1)
        # Should address audit/reporting standardization
        assert any("audit" in p.opportunity.lower() for p in p1)

    def test_pillar_2_child_safety(self, report):
        p2 = report.by_pillar("PILLAR-2")
        assert len(p2) >= 2
        assert all(p.pillar_name == "Child Safety & Community Protections" for p in p2)
        # Should reference content governance decisions
        all_evidence = " ".join(p.evidence + " " + p.scbe_capability for p in p2).lower()
        assert "quarantine" in all_evidence or "deny" in all_evidence or "governance" in all_evidence

    def test_pillar_3_intellectual_property(self, report):
        p3 = report.by_pillar("PILLAR-3")
        assert len(p3) >= 2
        assert all(p.pillar_name == "Intellectual Property" for p in p3)
        # Should reference patent and licensing
        assert any("patent" in p.evidence.lower() or "license" in p.evidence.lower() for p in p3)

    def test_pillar_4_innovation_governance(self, report):
        p4 = report.by_pillar("PILLAR-4")
        assert len(p4) >= 2
        assert all(p.pillar_name == "Innovation Governance" for p in p4)

    def test_pillar_5_workforce_development(self, report):
        p5 = report.by_pillar("PILLAR-5")
        assert len(p5) >= 1
        assert all(p.pillar_name == "Workforce Development" for p in p5)

    def test_high_readiness_rate(self, report):
        """Most alignments should be READY (not PLANNED)."""
        assert report.readiness_rate >= 0.8

    def test_each_alignment_has_evidence(self, report):
        for p in report.pillars:
            assert p.evidence != "", f"{p.pillar_id} missing evidence"
            assert p.scbe_capability != "", f"{p.pillar_id} missing SCBE capability"

    def test_summary_structure(self, report):
        summary = report.summary()
        assert "framework" in summary
        assert "readiness_rate" in summary
        assert "risk_areas" in summary
        assert len(summary["risk_areas"]) >= 5

    def test_total_alignment_count(self, report):
        assert report.total_count >= 11


class TestCombinedComplianceSummary:
    """Test the unified compliance evidence package."""

    def test_combined_summary_structure(self):
        summary = generate_combined_compliance_summary()
        assert summary["system"] == "SCBE-AETHERMOORE"
        assert "nist_ai_rmf" in summary
        assert "wh_policy_framework" in summary
        assert "combined_readiness" in summary
        assert "key_differentiators" in summary
        assert "regulatory_timeline" in summary

    def test_combined_readiness_high(self):
        summary = generate_combined_compliance_summary()
        assert summary["combined_readiness"]["overall"] >= 0.9

    def test_key_differentiators_include_preemption(self):
        summary = generate_combined_compliance_summary()
        assert any("preemption" in d.lower() for d in summary["key_differentiators"])

    def test_regulatory_timeline_present(self):
        summary = generate_combined_compliance_summary()
        timeline = summary["regulatory_timeline"]
        assert "current" in timeline
        assert "expected" in timeline
        assert "recommendation" in timeline
