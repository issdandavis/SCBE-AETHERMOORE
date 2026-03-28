"""
Tests for the Sovereign Deployment Manifest.

Covers:
- Manifest generation with valid/invalid licenses
- Air-gap readiness validation
- Compliance score computation
- Integrity hash chain verification
- Environment-specific entropy surface policies
- Deployment readiness checks

@module tests/test_sovereign_manifest
@layer Layer 13 (Governance)
"""

import json
import time

from licensing.oem_license import (
    LicenseClaims,
    LicenseKey,
    LicenseModel,
    LicenseTier,
    create_tier_license,
    generate_license_key,
)
from licensing.sovereign_manifest import (
    ComplianceFramework,
    DeploymentEnvironment,
    EntropySurfacePolicy,
    compute_integrity_chain,
    generate_sovereign_manifest,
    verify_manifest_integrity,
)

SECRET = "test-sovereign-signing-secret-2026"


def _oem_license(duration_days: int = 365, **overrides) -> LicenseKey:
    """Helper: create an OEM-tier license key."""
    return create_tier_license(
        tier=LicenseTier.OEM,
        licensee="TestGov Agency",
        model=LicenseModel.PERPETUAL,
        duration_days=duration_days,
        signing_secret=SECRET,
        **overrides,
    )


def _enterprise_license(**overrides) -> LicenseKey:
    return create_tier_license(
        tier=LicenseTier.ENTERPRISE,
        licensee="DefenseCorp",
        model=LicenseModel.SUBSCRIPTION,
        duration_days=365,
        signing_secret=SECRET,
        **overrides,
    )


def _homebrew_license() -> LicenseKey:
    return create_tier_license(
        tier=LicenseTier.HOMEBREW,
        licensee="IndieHacker",
        model=LicenseModel.SUBSCRIPTION,
        duration_days=90,
        signing_secret=SECRET,
    )


# ═══════════════════════════════════════════════════════════════
# Manifest Generation
# ═══════════════════════════════════════════════════════════════


class TestManifestGeneration:
    def test_oem_air_gapped(self):
        """OEM license should produce a deployment-ready manifest."""
        key = _oem_license()
        manifest = generate_sovereign_manifest(
            key,
            SECRET,
            environment=DeploymentEnvironment.AIR_GAPPED,
            deployment_id="GOV-2026-001",
        )

        assert manifest.license_valid is True
        assert manifest.license_reason == "VALID"
        assert manifest.air_gap_approved is True
        assert manifest.white_label is True
        assert manifest.deployment_ready is True
        assert manifest.deployment_id == "GOV-2026-001"
        assert manifest.support_level == "none"
        assert manifest.manifest_version == "1.0.0"

    def test_enterprise_sovereign_cloud(self):
        """Enterprise license in sovereign cloud."""
        key = _enterprise_license()
        manifest = generate_sovereign_manifest(
            key,
            SECRET,
            environment=DeploymentEnvironment.SOVEREIGN_CLOUD,
        )

        assert manifest.license_valid is True
        assert manifest.air_gap_approved is True
        assert manifest.environment == "sovereign_cloud"

    def test_homebrew_not_air_gap_approved(self):
        """Homebrew license should warn about air-gap."""
        key = _homebrew_license()
        manifest = generate_sovereign_manifest(key, SECRET)

        assert manifest.license_valid is True
        assert manifest.air_gap_approved is False
        assert manifest.deployment_ready is False  # No air-gap approval
        assert any(
            "air-gap" in w.lower() or "air_gap" in w.lower() for w in manifest.warnings
        )

    def test_invalid_signature(self):
        """Tampered license should fail validation."""
        key = _oem_license()
        key = LicenseKey(claims=key.claims, signature="deadbeef" * 8)

        manifest = generate_sovereign_manifest(key, SECRET)

        assert manifest.license_valid is False
        assert manifest.license_reason == "INVALID_SIGNATURE"
        assert manifest.deployment_ready is False

    def test_expired_license(self):
        """Expired license should fail."""
        key = _oem_license(duration_days=0)
        # Manually set expiration to the past
        claims = LicenseClaims(
            licensee="Expired Corp",
            tier=LicenseTier.OEM.value,
            model=LicenseModel.PERPETUAL.value,
            issued_at=time.time() - 86400 * 400,
            expires_at=time.time() - 86400,  # Expired yesterday
            air_gap_approved=True,
            white_label=True,
            modules=["core"],
        )
        key = generate_license_key(claims, SECRET)
        manifest = generate_sovereign_manifest(key, SECRET)

        assert manifest.license_valid is False
        assert manifest.license_reason == "LICENSE_EXPIRED"

    def test_modules_propagated(self):
        """License modules should appear in manifest."""
        key = _oem_license()
        manifest = generate_sovereign_manifest(key, SECRET)

        assert "core" in manifest.license_modules
        assert "harmonic" in manifest.license_modules
        assert "gateway" in manifest.license_modules


# ═══════════════════════════════════════════════════════════════
# Compliance
# ═══════════════════════════════════════════════════════════════


class TestCompliance:
    def test_compliance_score(self):
        """Compliance score should be between 0 and 1."""
        key = _oem_license()
        manifest = generate_sovereign_manifest(key, SECRET)

        assert 0 <= manifest.compliance_score <= 1
        assert manifest.nist_rmf_checks_total > 0
        assert manifest.nist_rmf_checks_passed >= 0

    def test_compliance_frameworks_recorded(self):
        """Target compliance frameworks should be listed."""
        key = _oem_license()
        targets = [ComplianceFramework.NIST_AI_RMF, ComplianceFramework.FEDRAMP_HIGH]
        manifest = generate_sovereign_manifest(
            key,
            SECRET,
            compliance_targets=targets,
        )

        assert ComplianceFramework.NIST_AI_RMF.value in manifest.compliance_frameworks
        assert ComplianceFramework.FEDRAMP_HIGH.value in manifest.compliance_frameworks


# ═══════════════════════════════════════════════════════════════
# Entropy Surface Policy
# ═══════════════════════════════════════════════════════════════


class TestEntropySurface:
    def test_default_policy_for_air_gapped(self):
        """Air-gapped deployments should get paranoid entropy policy."""
        key = _oem_license()
        manifest = generate_sovereign_manifest(
            key,
            SECRET,
            environment=DeploymentEnvironment.AIR_GAPPED,
        )

        assert manifest.entropy_surface["enabled"] is True
        assert manifest.entropy_surface["anti_extraction_mode"] == "paranoid"
        assert manifest.entropy_surface["leakage_budget_bits"] == 64.0

    def test_default_policy_for_sovereign_cloud(self):
        """Sovereign cloud gets standard entropy policy."""
        key = _oem_license()
        manifest = generate_sovereign_manifest(
            key,
            SECRET,
            environment=DeploymentEnvironment.SOVEREIGN_CLOUD,
        )

        assert manifest.entropy_surface["enabled"] is True
        assert manifest.entropy_surface["anti_extraction_mode"] == "standard"
        assert manifest.entropy_surface["leakage_budget_bits"] == 128.0

    def test_scif_gets_paranoid(self):
        """SCIF deployments should get paranoid mode."""
        key = _oem_license()
        manifest = generate_sovereign_manifest(
            key,
            SECRET,
            environment=DeploymentEnvironment.SCIF,
        )

        assert manifest.entropy_surface["anti_extraction_mode"] == "paranoid"

    def test_custom_entropy_policy(self):
        """Custom entropy policy should override defaults."""
        key = _oem_license()
        policy = EntropySurfacePolicy(
            leakage_budget_bits=32.0,
            anti_extraction_mode="aggressive",
        )
        manifest = generate_sovereign_manifest(
            key,
            SECRET,
            entropy_policy=policy,
        )

        assert manifest.entropy_surface["leakage_budget_bits"] == 32.0
        assert manifest.entropy_surface["anti_extraction_mode"] == "aggressive"

    def test_scif_warns_wrong_tier(self):
        """SCIF with homebrew license should warn."""
        key = _homebrew_license()
        manifest = generate_sovereign_manifest(
            key,
            SECRET,
            environment=DeploymentEnvironment.SCIF,
        )

        assert any("SCIF" in w for w in manifest.warnings)


# ═══════════════════════════════════════════════════════════════
# Integrity Hash Chain
# ═══════════════════════════════════════════════════════════════


class TestIntegrity:
    def test_integrity_chain_deterministic(self):
        """Same components should produce same hash."""
        components = ["alpha", "beta", "gamma"]
        h1 = compute_integrity_chain(components)
        h2 = compute_integrity_chain(components)
        assert h1 == h2

    def test_integrity_chain_order_sensitive(self):
        """Different order should produce different hash."""
        h1 = compute_integrity_chain(["alpha", "beta"])
        h2 = compute_integrity_chain(["beta", "alpha"])
        assert h1 != h2

    def test_integrity_chain_tamper_detection(self):
        """Changing any component should change the hash."""
        h1 = compute_integrity_chain(["a", "b", "c"])
        h2 = compute_integrity_chain(["a", "X", "c"])
        assert h1 != h2

    def test_manifest_integrity_valid(self):
        """Fresh manifest should pass integrity check."""
        key = _oem_license()
        manifest = generate_sovereign_manifest(key, SECRET)
        assert verify_manifest_integrity(manifest) is True

    def test_manifest_integrity_tampered(self):
        """Tampered manifest should fail integrity check."""
        key = _oem_license()
        manifest = generate_sovereign_manifest(key, SECRET)

        # Tamper with a component hash
        manifest.component_hashes["license_claims"] = "tampered" * 8

        assert verify_manifest_integrity(manifest) is False


# ═══════════════════════════════════════════════════════════════
# Serialization
# ═══════════════════════════════════════════════════════════════


class TestSerialization:
    def test_to_json_roundtrip(self):
        """Manifest should serialize to valid JSON."""
        key = _oem_license()
        manifest = generate_sovereign_manifest(key, SECRET)
        j = manifest.to_json()

        parsed = json.loads(j)
        assert parsed["license_valid"] is True
        assert parsed["manifest_version"] == "1.0.0"
        assert "integrity_hash" in parsed

    def test_to_dict(self):
        """to_dict should produce a plain dict."""
        key = _oem_license()
        manifest = generate_sovereign_manifest(key, SECRET)
        d = manifest.to_dict()

        assert isinstance(d, dict)
        assert d["license_tier"] == LicenseTier.OEM.value


# ═══════════════════════════════════════════════════════════════
# Deployment Readiness
# ═══════════════════════════════════════════════════════════════


class TestDeploymentReadiness:
    def test_oem_is_ready(self):
        """OEM license should be deployment-ready."""
        key = _oem_license()
        manifest = generate_sovereign_manifest(key, SECRET)
        assert manifest.deployment_ready is True

    def test_invalid_license_not_ready(self):
        """Invalid license should not be deployment-ready."""
        key = _oem_license()
        key = LicenseKey(claims=key.claims, signature="bad")
        manifest = generate_sovereign_manifest(key, SECRET)
        assert manifest.deployment_ready is False

    def test_no_air_gap_not_ready(self):
        """License without air-gap approval should not be ready."""
        key = _homebrew_license()
        manifest = generate_sovereign_manifest(key, SECRET)
        assert manifest.deployment_ready is False
