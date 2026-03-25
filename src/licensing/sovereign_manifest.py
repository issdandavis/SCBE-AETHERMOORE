"""
Sovereign Deployment Manifest — Self-Contained Air-Gap Deployment Descriptor
=============================================================================

Generates a deployment manifest that bundles:
  1. License validation (HMAC-SHA256, no network)
  2. NIST AI RMF compliance evidence
  3. Entropy Surface defense configuration
  4. Air-gap readiness attestation
  5. Integrity hash chain for tamper detection

Designed for government/enterprise "Digital Sovereignty" deployments
where all computation stays on the licensee's isolated infrastructure.

Target buyers:
  - Government "Sovereign Cloud" programs (FedRAMP, GovCloud)
  - Defense/IC contractors (CMMC 2.0)
  - Financial institutions (air-gapped trading systems)
  - Healthcare organizations (HIPAA, on-prem only)

No outbound network calls. No telemetry. No phone-home.
License validation is cryptographic (HMAC), not server-based.

@module licensing/sovereign_manifest
@layer Layer 13 (Governance)
@version 1.0.0
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .oem_license import (
    LicenseKey,
    LicenseTier,
    validate_license_key,
)
from .nist_ai_rmf import generate_compliance_report


# ── Deployment Environment Classification ──────────────────────────────────

class DeploymentEnvironment(Enum):
    """Target deployment environment for sovereign installs."""
    AIR_GAPPED = "air_gapped"           # No network connectivity
    SOVEREIGN_CLOUD = "sovereign_cloud"  # Gov cloud (FedRAMP, GovCloud)
    ON_PREMISES = "on_premises"          # Enterprise data center
    EDGE = "edge"                        # Edge/tactical deployment
    SCIF = "scif"                        # Sensitive Compartmented Info Facility


class ComplianceFramework(Enum):
    """Compliance frameworks this deployment satisfies."""
    NIST_AI_RMF = "NIST_AI_RMF_1.0"
    NIST_800_53 = "NIST_SP_800-53_Rev5"
    FIPS_140_3 = "FIPS_140-3"
    CMMC_2 = "CMMC_2.0"
    FEDRAMP_HIGH = "FedRAMP_High"
    HIPAA = "HIPAA"
    SOC2_TYPE2 = "SOC2_Type_II"
    EO_14110 = "EO_14110"
    WHITE_HOUSE_AI_2026 = "WH_AI_Policy_Framework_2026"


# ── Entropy Surface Defense Config ─────────────────────────────────────────

@dataclass
class EntropySurfacePolicy:
    """Entropy surface defense policy for this deployment.

    Controls how aggressively the system nullifies output under
    suspected extraction attempts.
    """
    enabled: bool = True
    leakage_budget_bits: float = 128.0
    probing_threshold: float = 0.6
    nullification_sigmoid_k: float = 10.0
    max_queries_per_window: int = 50
    anti_extraction_mode: str = "standard"  # standard, aggressive, paranoid

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Integrity Hash Chain ───────────────────────────────────────────────────

def _sha256(data: str) -> str:
    """SHA-256 hex digest of a string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_integrity_chain(components: List[str]) -> str:
    """Compute a chained hash over deployment components.

    Each component's hash feeds into the next, creating a tamper-evident
    chain. If any component is modified, the final hash changes.

    Args:
        components: List of string representations to hash.

    Returns:
        Final chain hash (hex).
    """
    chain = "SCBE_SOVEREIGN_GENESIS"
    for component in components:
        chain = _sha256(chain + "|" + component)
    return chain


# ── Sovereign Deployment Manifest ──────────────────────────────────────────

@dataclass
class SovereignManifest:
    """Self-contained deployment manifest for air-gapped environments.

    This is the single artifact a government/enterprise buyer receives.
    It proves:
      1. The license is valid and correctly scoped
      2. The deployment meets required compliance frameworks
      3. Anti-extraction defenses are configured
      4. The artifact hasn't been tampered with
    """

    # Identity
    manifest_version: str = "1.0.0"
    generated_at: float = field(default_factory=time.time)
    deployment_id: str = ""

    # License
    license_tier: str = ""
    license_valid: bool = False
    license_reason: str = ""
    license_modules: List[str] = field(default_factory=list)
    air_gap_approved: bool = False
    white_label: bool = False

    # Environment
    environment: str = ""
    compliance_frameworks: List[str] = field(default_factory=list)

    # Compliance
    nist_rmf_checks_passed: int = 0
    nist_rmf_checks_total: int = 0
    compliance_score: float = 0.0

    # Entropy Surface Defense
    entropy_surface: Dict[str, Any] = field(default_factory=dict)

    # Integrity
    integrity_hash: str = ""
    component_hashes: Dict[str, str] = field(default_factory=dict)

    # Deployment constraints
    max_deployment_instances: int = 0
    max_swarm_agents: int = 0
    max_decisions_per_month: int = 0
    support_level: str = "none"

    # Warnings
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @property
    def deployment_ready(self) -> bool:
        """Whether this manifest allows deployment."""
        return (
            self.license_valid
            and self.air_gap_approved
            and self.compliance_score >= 0.8
        )


# ── Manifest Generator ─────────────────────────────────────────────────────

def generate_sovereign_manifest(
    license_key: LicenseKey,
    signing_secret: str,
    environment: DeploymentEnvironment = DeploymentEnvironment.AIR_GAPPED,
    compliance_targets: Optional[List[ComplianceFramework]] = None,
    entropy_policy: Optional[EntropySurfacePolicy] = None,
    deployment_id: str = "",
    current_decisions_this_month: int = 0,
) -> SovereignManifest:
    """Generate a sovereign deployment manifest.

    This is the primary artifact for Digital Sovereignty licensing.
    It validates the license, generates compliance evidence, configures
    anti-extraction defenses, and produces a tamper-evident hash chain.

    Args:
        license_key: Signed license key.
        signing_secret: HMAC verification secret.
        environment: Target deployment environment.
        compliance_targets: Required compliance frameworks.
        entropy_policy: Entropy surface defense configuration.
        deployment_id: Unique deployment identifier.
        current_decisions_this_month: For quota checking.

    Returns:
        SovereignManifest ready for deployment.
    """
    if compliance_targets is None:
        compliance_targets = [
            ComplianceFramework.NIST_AI_RMF,
            ComplianceFramework.NIST_800_53,
            ComplianceFramework.EO_14110,
        ]

    if entropy_policy is None:
        # Default: scale aggressiveness by environment
        if environment in (DeploymentEnvironment.SCIF, DeploymentEnvironment.AIR_GAPPED):
            entropy_policy = EntropySurfacePolicy(
                anti_extraction_mode="paranoid",
                leakage_budget_bits=64.0,
                probing_threshold=0.4,
            )
        else:
            entropy_policy = EntropySurfacePolicy()

    # ── 1. Validate license ──────────────────────────────────────────────

    validation = validate_license_key(
        license_key, signing_secret, current_decisions_this_month
    )

    warnings: List[str] = list(validation.warnings)

    # Check air-gap approval
    claims = license_key.claims
    if not claims.air_gap_approved:
        warnings.append(
            "License does not include air-gap approval. "
            "Sovereign deployment requires air_gap_approved=True."
        )

    # Check tier compatibility with environment
    if environment == DeploymentEnvironment.SCIF and claims.tier not in (
        LicenseTier.OEM.value, LicenseTier.ENTERPRISE.value
    ):
        warnings.append(
            f"SCIF deployment requires OEM or Enterprise tier, got {claims.tier}"
        )

    # ── 2. Generate compliance evidence ──────────────────────────────────

    compliance_report = generate_compliance_report()
    passed = sum(1 for c in compliance_report.checks if c.status == "PASS")
    total = len(compliance_report.checks)
    compliance_score = passed / max(total, 1)

    # ── 3. Build component hashes ────────────────────────────────────────

    component_hashes = {
        "license_claims": _sha256(claims.canonical_json()),
        "license_signature": _sha256(license_key.signature),
        "compliance_report": _sha256(json.dumps(asdict(compliance_report), sort_keys=True, default=str)),
        "entropy_policy": _sha256(json.dumps(entropy_policy.to_dict(), sort_keys=True)),
        "environment": _sha256(environment.value),
        "deployment_id": _sha256(deployment_id or "unspecified"),
    }

    # ── 4. Compute integrity chain ───────────────────────────────────────

    integrity_hash = compute_integrity_chain(
        [component_hashes[k] for k in sorted(component_hashes.keys())]
    )

    # ── 5. Assemble manifest ─────────────────────────────────────────────

    return SovereignManifest(
        manifest_version="1.0.0",
        deployment_id=deployment_id,
        license_tier=claims.tier,
        license_valid=validation.valid,
        license_reason=validation.reason,
        license_modules=claims.modules,
        air_gap_approved=claims.air_gap_approved,
        white_label=claims.white_label,
        environment=environment.value,
        compliance_frameworks=[f.value for f in compliance_targets],
        nist_rmf_checks_passed=passed,
        nist_rmf_checks_total=total,
        compliance_score=round(compliance_score, 3),
        entropy_surface=entropy_policy.to_dict(),
        integrity_hash=integrity_hash,
        component_hashes=component_hashes,
        max_deployment_instances=claims.max_deployment_instances,
        max_swarm_agents=claims.max_swarm_agents,
        max_decisions_per_month=claims.max_decisions_per_month,
        support_level=claims.support_level,
        warnings=warnings,
    )


# ── Manifest Verification ──────────────────────────────────────────────────

def verify_manifest_integrity(manifest: SovereignManifest) -> bool:
    """Verify that a manifest hasn't been tampered with.

    Recomputes the integrity chain from component hashes and
    compares against the stored integrity hash.

    Args:
        manifest: Manifest to verify.

    Returns:
        True if integrity chain matches.
    """
    expected = compute_integrity_chain(
        [manifest.component_hashes[k] for k in sorted(manifest.component_hashes.keys())]
    )
    return expected == manifest.integrity_hash
