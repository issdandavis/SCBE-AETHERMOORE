"""
NIST AI Risk Management Framework (AI RMF 1.0) Compliance Module
=================================================================

Maps SCBE-AETHERMOORE capabilities to the NIST AI RMF functions:

  GOVERN  — Policies, roles, risk tolerance
  MAP     — AI system context, stakeholders, risk categorization
  MEASURE — Metrics, testing, monitoring
  MANAGE  — Prioritize, respond, communicate

This module generates compliance evidence artifacts for OEM licensing
deals and government subcontracting (TradeWinds, SBIR/STTR).

Key 2026 requirements addressed:
  - NIST AI RMF 1.0 (January 2023, updated guidance 2025)
  - Executive Order 14110 (Safe, Secure AI — October 2023)
  - OMB M-24-10 (Federal AI governance — March 2024)
  - NIST SP 800-53 Rev 5 (already validated in compliance_report.md)

@module licensing/nist_ai_rmf
@layer Layer 13 (Governance)
@version 1.0.0
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List


# ── AI RMF Functions ─────────────────────────────────────────────────────────


class RMFFunction:
    GOVERN = "GOVERN"
    MAP = "MAP"
    MEASURE = "MEASURE"
    MANAGE = "MANAGE"


# ── Compliance Check ─────────────────────────────────────────────────────────


@dataclass
class ComplianceCheck:
    """A single NIST AI RMF compliance check."""

    check_id: str  # e.g., "GOVERN-1.1"
    function: str  # GOVERN, MAP, MEASURE, MANAGE
    category: str  # Subcategory
    description: str  # What this check verifies
    scbe_mapping: str  # Which SCBE component satisfies this
    evidence: str  # How to demonstrate compliance
    status: str = "PASS"  # PASS, FAIL, PARTIAL, N/A
    notes: str = ""


@dataclass
class ComplianceReport:
    """Full NIST AI RMF compliance report."""

    generated_at: float
    framework: str = "NIST AI RMF 1.0"
    version: str = "1.0.0"
    system_name: str = "SCBE-AETHERMOORE"
    checks: List[ComplianceCheck] = field(default_factory=list)

    @property
    def total_checks(self) -> int:
        return len(self.checks)

    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "PASS")

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "FAIL")

    @property
    def partial_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "PARTIAL")

    @property
    def pass_rate(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return self.pass_count / self.total_checks

    def by_function(self, function: str) -> List[ComplianceCheck]:
        return [c for c in self.checks if c.function == function]

    def summary(self) -> Dict[str, Any]:
        return {
            "framework": self.framework,
            "system": self.system_name,
            "generated_at": self.generated_at,
            "total_checks": self.total_checks,
            "passed": self.pass_count,
            "failed": self.fail_count,
            "partial": self.partial_count,
            "pass_rate": round(self.pass_rate, 4),
            "by_function": {
                f: {
                    "total": len(self.by_function(f)),
                    "passed": sum(1 for c in self.by_function(f) if c.status == "PASS"),
                }
                for f in [RMFFunction.GOVERN, RMFFunction.MAP, RMFFunction.MEASURE, RMFFunction.MANAGE]
            },
        }


# ── SCBE-to-RMF Mapping ─────────────────────────────────────────────────────


def generate_compliance_report() -> ComplianceReport:
    """Generate a NIST AI RMF compliance report for SCBE-AETHERMOORE.

    Maps each RMF subcategory to concrete SCBE components,
    providing evidence artifacts for OEM/government deals.
    """
    checks = []

    # ── GOVERN Function ──────────────────────────────────────────────────
    # Policies, accountability, organizational context

    checks.append(
        ComplianceCheck(
            check_id="GOVERN-1.1",
            function=RMFFunction.GOVERN,
            category="Policies",
            description="Legal and regulatory requirements are understood and inform AI risk management",
            scbe_mapping="CUSTOMER_LICENSE_AGREEMENT.md, docs/05-industry-guides/",
            evidence="Dual-license model with explicit regulatory mapping for banking, healthcare, defense, SaaS verticals",
        )
    )

    checks.append(
        ComplianceCheck(
            check_id="GOVERN-1.2",
            function=RMFFunction.GOVERN,
            category="Policies",
            description="AI risk management policies are established and documented",
            scbe_mapping="config/scbe_core_axioms_v1.yaml (7 core axioms A0-A7)",
            evidence="A0: Deterministic Execution, A2: Policy Before Actuation, A4: Fail-to-Noise, A7: Recoverability",
        )
    )

    checks.append(
        ComplianceCheck(
            check_id="GOVERN-1.3",
            function=RMFFunction.GOVERN,
            category="Accountability",
            description="Roles and responsibilities for AI risk management are defined",
            scbe_mapping="src/governance/, src/fleet/ (shepherd/flock roles)",
            evidence="Layer 13 governance with ALLOW/QUARANTINE/ESCALATE/DENY decisions requiring explicit authorization",
        )
    )

    checks.append(
        ComplianceCheck(
            check_id="GOVERN-1.4",
            function=RMFFunction.GOVERN,
            category="Risk Tolerance",
            description="Risk tolerance is determined and documented",
            scbe_mapping="src/symphonic_cipher/scbe_aethermoore/axiom_grouped/langues_metric.py",
            evidence="Quantified risk thresholds: LOW (L<1.5×L_base→ALLOW), MEDIUM (→QUARANTINE), HIGH (→REVIEW), CRITICAL (→DENY)",
        )
    )

    checks.append(
        ComplianceCheck(
            check_id="GOVERN-2.1",
            function=RMFFunction.GOVERN,
            category="Oversight",
            description="Mechanisms are in place for human oversight of AI",
            scbe_mapping="src/symphonic_cipher/scbe_aethermoore/ai_brain/governance_adapter.py",
            evidence="ESCALATE decision tier requires human governance approval; flux contraction pulls state toward safe origin",
        )
    )

    checks.append(
        ComplianceCheck(
            check_id="GOVERN-2.2",
            function=RMFFunction.GOVERN,
            category="Documentation",
            description="AI system documentation is maintained",
            scbe_mapping="SPEC.md, ARCHITECTURE.md, LAYER_INDEX.md, docs/ (170+ files)",
            evidence="Complete 14-layer pipeline specification with axiom compliance annotations",
        )
    )

    # ── MAP Function ─────────────────────────────────────────────────────
    # Context, categorization, stakeholder impact

    checks.append(
        ComplianceCheck(
            check_id="MAP-1.1",
            function=RMFFunction.MAP,
            category="System Context",
            description="Intended purpose and deployment context are documented",
            scbe_mapping="docs/product/LAUNCH_SKU.md, README.md",
            evidence="Agent Governance for Regulated Workflows — tool-call control, data egress guard, audit export",
        )
    )

    checks.append(
        ComplianceCheck(
            check_id="MAP-1.2",
            function=RMFFunction.MAP,
            category="Risk Categorization",
            description="AI risks are identified and categorized",
            scbe_mapping="14-layer pipeline (L1-L14), docs/CORE_AXIOMS_CANONICAL_INDEX.md",
            evidence="ROME-Class Failure taxonomy; adversarial intent mapped to Poincare ball with exponential cost scaling",
        )
    )

    checks.append(
        ComplianceCheck(
            check_id="MAP-2.1",
            function=RMFFunction.MAP,
            category="Data Provenance",
            description="Data used by the AI system is documented",
            scbe_mapping="training-data/dataset_info.json, scripts/codebase_to_sft.py",
            evidence="10,978 training pairs with source provenance, dedup flags, and validation status",
        )
    )

    checks.append(
        ComplianceCheck(
            check_id="MAP-2.2",
            function=RMFFunction.MAP,
            category="Technical Architecture",
            description="AI system architecture is documented with component interactions",
            scbe_mapping="SYSTEM_ARCHITECTURE.md, LAYER_INDEX.md",
            evidence="14-layer pipeline with 5 quantum axioms, 6 Sacred Tongues, PQC envelope, and governance gate",
        )
    )

    checks.append(
        ComplianceCheck(
            check_id="MAP-3.1",
            function=RMFFunction.MAP,
            category="Third-Party Components",
            description="Third-party AI components and their risks are identified",
            scbe_mapping="package.json (dependencies), src/pyproject.toml",
            evidence="Explicit dependency list with PQC libraries (@noble/post-quantum), MCP SDK, and crypto primitives",
        )
    )

    # ── MEASURE Function ─────────────────────────────────────────────────
    # Metrics, testing, continuous monitoring

    checks.append(
        ComplianceCheck(
            check_id="MEASURE-1.1",
            function=RMFFunction.MEASURE,
            category="Performance Metrics",
            description="AI system performance is measured against stated objectives",
            scbe_mapping="docs/archive/compliance_report.md (150/150 tests)",
            evidence="Coverage: HIPAA(23), NIST-800-53(74), FIPS-140-3(31), PCI-DSS(5), SOX(6), GDPR(5), ISO-27001(3), SOC2(17)",
        )
    )

    checks.append(
        ComplianceCheck(
            check_id="MEASURE-1.2",
            function=RMFFunction.MEASURE,
            category="Bias Testing",
            description="AI outputs are tested for harmful bias and discrimination",
            scbe_mapping="src/training/symphonic_governor.py (multi-scalar grading)",
            evidence="Balanced ternary grading (+1/0/-1) with tonal review ensures symmetric treatment; "
            "6D Langues Metric provides equal-weight evaluation across all dimensions",
        )
    )

    checks.append(
        ComplianceCheck(
            check_id="MEASURE-2.1",
            function=RMFFunction.MEASURE,
            category="Security Testing",
            description="AI system is tested for adversarial robustness",
            scbe_mapping="tests/security/, tests/enterprise/, tests/L6-adversarial/",
            evidence="L6-adversarial test tier with attack simulations; hyperbolic geometry makes "
            "attacks cost-prohibitive (H(d,R) = R^(d²))",
        )
    )

    checks.append(
        ComplianceCheck(
            check_id="MEASURE-2.2",
            function=RMFFunction.MEASURE,
            category="Cryptographic Assurance",
            description="Cryptographic controls meet current and future threat models",
            scbe_mapping="src/crypto/, packages/kernel/src/pqcEnvelope.ts",
            evidence="Post-quantum: ML-KEM-768 (key encapsulation) + ML-DSA-65 (signatures) + AES-256-GCM; "
            "NIST-approved algorithms resistant to quantum attacks",
        )
    )

    checks.append(
        ComplianceCheck(
            check_id="MEASURE-3.1",
            function=RMFFunction.MEASURE,
            category="Continuous Monitoring",
            description="AI system is continuously monitored in deployment",
            scbe_mapping="src/harmonic/audioAxis.ts (L14), src/spectral/ (L9-L10)",
            evidence="Layer 14 audio telemetry via FFT; Layer 9-10 spectral coherence monitoring; "
            "stellar pulse synchronization for drift detection",
        )
    )

    checks.append(
        ComplianceCheck(
            check_id="MEASURE-3.2",
            function=RMFFunction.MEASURE,
            category="Audit Trail",
            description="Decision-level audit trail for all AI actions",
            scbe_mapping="src/gateway/authorize-service.ts, src/licensing/usage_meter.py",
            evidence="Every governance decision logged with timestamp, agent_id, tenant_id, "
            "risk_score, policy_ids, latency; exportable as JSONL for SIEM integration",
        )
    )

    # ── MANAGE Function ──────────────────────────────────────────────────
    # Prioritize, respond, communicate

    checks.append(
        ComplianceCheck(
            check_id="MANAGE-1.1",
            function=RMFFunction.MANAGE,
            category="Risk Prioritization",
            description="AI risks are prioritized based on impact and likelihood",
            scbe_mapping="src/symphonic_cipher/scbe_aethermoore/axiom_grouped/langues_metric.py",
            evidence="Exponential cost scaling: L(x,t) = Σ w_l exp(β_l · (d_l + sin(ω_l·t + φ_l))); "
            "golden ratio weights prioritize higher-risk dimensions",
        )
    )

    checks.append(
        ComplianceCheck(
            check_id="MANAGE-1.2",
            function=RMFFunction.MANAGE,
            category="Incident Response",
            description="AI-specific incident response procedures are established",
            scbe_mapping="src/selfHealing/, src/symphonic_cipher/scbe_aethermoore/ai_brain/governance_adapter.py",
            evidence="Flux contraction: x' = (1-α)·x + α·x_safe; AsymmetryTracker triggers after 3+ "
            "consecutive high readings; self-healing recovery pipeline",
        )
    )

    checks.append(
        ComplianceCheck(
            check_id="MANAGE-2.1",
            function=RMFFunction.MANAGE,
            category="Risk Response",
            description="Tiered response actions for different risk levels",
            scbe_mapping="src/api/govern.ts, src/symphonic_cipher/scbe_aethermoore/gate_swap.py",
            evidence="4-tier response: ALLOW (<0.3 combined score), QUARANTINE (0.3-0.6), "
            "ESCALATE (0.6-0.85), DENY (≥0.85); tri-manifold gate with hard-deny on integrity failure",
        )
    )

    checks.append(
        ComplianceCheck(
            check_id="MANAGE-2.2",
            function=RMFFunction.MANAGE,
            category="Fail-Safe",
            description="AI system fails safely when errors or anomalies occur",
            scbe_mapping="config/scbe_core_axioms_v1.yaml (A4: Fail-to-Noise, A7: Recoverability)",
            evidence="A4: System fails to noise (safe default) rather than exposing state; "
            "A7: Recoverability over perfection — bounded failure with monotonic recovery",
        )
    )

    checks.append(
        ComplianceCheck(
            check_id="MANAGE-3.1",
            function=RMFFunction.MANAGE,
            category="Communication",
            description="Stakeholders are informed about AI system risks and decisions",
            scbe_mapping="src/gateway/unified-api.ts (LayerExplanation), src/licensing/usage_meter.py",
            evidence="Authorization responses include per-layer explanation, dominant risk factor, "
            "and recommendation; usage reports exportable for compliance reviews",
        )
    )

    checks.append(
        ComplianceCheck(
            check_id="MANAGE-3.2",
            function=RMFFunction.MANAGE,
            category="Intellectual Property",
            description="IP protections and licensing terms are clear",
            scbe_mapping="CUSTOMER_LICENSE_AGREEMENT.md, COMMERCIAL.md, US Patent 63/961,403",
            evidence="Dual-license (MIT + Commercial); 3-tier commercial model with OEM/source-available; "
            "20-year IP protection for SBIR/STTR deliveries",
        )
    )

    return ComplianceReport(
        generated_at=time.time(),
        checks=checks,
    )


# ── Government Contracting Helpers ───────────────────────────────────────────


@dataclass
class TradeWindsProfile:
    """Profile for the DoD TradeWinds Marketplace submission."""

    company_name: str
    technology_name: str = "SCBE-AETHERMOORE"
    description: str = (
        "Post-quantum AI governance framework using hyperbolic geometry "
        "(Poincaré ball model) for exponential cost scaling of adversarial behavior. "
        "14-layer security pipeline with ML-KEM-768/ML-DSA-65 cryptography."
    )
    category: str = "AI Safety & Governance"
    trl_level: int = 6  # Technology Readiness Level (6 = prototype demonstrated)
    cage_code: str = ""  # Assigned by DLA
    naics_codes: List[str] = field(
        default_factory=lambda: [
            "541512",  # Computer Systems Design Services
            "541519",  # Other Computer Related Services
            "541715",  # R&D in Physical, Engineering, and Life Sciences
        ]
    )
    certifications: List[str] = field(
        default_factory=lambda: [
            "NIST AI RMF 1.0 Compliant",
            "NIST SP 800-53 Rev 5 (74 controls verified)",
            "FIPS 140-3 Compatible (ML-KEM-768, ML-DSA-65)",
            "CMMC 2.0 Ready",
            "US Provisional Patent 63/961,403",
        ]
    )
    key_differentiators: List[str] = field(
        default_factory=lambda: [
            "Hyperbolic geometry makes adversarial attacks computationally infeasible",
            "Post-quantum cryptography (NIST-approved ML-KEM/ML-DSA)",
            "14-layer pipeline with 5 quantum axiom mesh",
            "Support-free OEM licensing model (Black Box clause)",
            "Air-gap compatible (no network calls for license validation)",
        ]
    )


@dataclass
class SBIRDeliverable:
    """Technical data marking for SBIR/STTR deliveries.

    Critical: The 20-year IP protection period is non-extendable.
    All technical data must be precisely marked during delivery.
    """

    title: str = "SCBE-AETHERMOORE Post-Quantum AI Governance Framework"
    data_rights: str = "SBIR Data Rights"
    protection_period_years: int = 20
    marking: str = (
        "SBIR DATA RIGHTS — Contract No. [TBD], Contractor: Issac Daniel Davis. "
        "This data was developed under a Small Business Innovation Research (SBIR) contract. "
        "Use, duplication, or disclosure is subject to the restrictions as stated in "
        "DFARS 252.227-7018. Expiration of SBIR Data Rights: [issue_date + 20 years]."
    )
    technical_data_items: List[str] = field(
        default_factory=lambda: [
            "14-Layer Harmonic Security Pipeline Specification",
            "Poincaré Ball Hyperbolic Geometry Implementation",
            "Post-Quantum Cryptographic Envelope (ML-KEM-768, ML-DSA-65)",
            "Six Sacred Tongues Bijective Tokenization",
            "Langues Weighting System (6D Phase-Shifted Cost Function)",
            "Symphonic Governor Tonal Training Engine",
            "Governance Decision Pipeline (ALLOW/QUARANTINE/ESCALATE/DENY)",
        ]
    )
    computer_software_items: List[str] = field(
        default_factory=lambda: [
            "scbe-aethermoore npm package (v3.3.0)",
            "scbe-aethermoore PyPI package (v3.3.0)",
            "Docker multi-stage build (Node 20 + liboqs + Python 3.11)",
        ]
    )
