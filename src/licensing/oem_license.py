"""
OEM License Gate — Support-Free Black Box License Validation
============================================================

Runtime license validation for OEM/white-label distribution of
SCBE-AETHERMOORE. Supports three distribution models:

  1. OEM License: Vendored inside another product. Licensee handles
     all support. SCBE operates as a "black box" module.
  2. Source-Available "As-Is": Sold without warranty or support.
     Buyer hosts on air-gapped servers (Digital Sovereignty).
  3. Usage-Based License: Per-decision metering with royalty billing.

License validation uses HMAC-SHA256 over a canonical claim set.
No network call required (air-gap compatible).

@module licensing/oem_license
@layer Layer 13 (Governance)
@version 1.0.0
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

# ── License Tiers ────────────────────────────────────────────────────────────


class LicenseTier(Enum):
    """Commercial license tiers (from CUSTOMER_LICENSE_AGREEMENT.md)."""

    HOMEBREW = "homebrew"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    OEM = "oem"  # White-label / black-box
    SOURCE_AVAILABLE = "source_available"  # As-is, no support


class LicenseModel(Enum):
    """Monetization model."""

    PERPETUAL = "perpetual"  # One-time purchase
    SUBSCRIPTION = "subscription"  # Monthly/annual recurring
    USAGE_BASED = "usage_based"  # Per-1k decisions
    ROYALTY = "royalty"  # Percentage of licensee revenue
    HYBRID = "hybrid"  # Platform floor + per-decision


# ── License Claims ───────────────────────────────────────────────────────────


@dataclass
class LicenseClaims:
    """Canonical claim set embedded in a license key.

    Fields match the Order Form terms from CUSTOMER_LICENSE_AGREEMENT.md.
    """

    licensee: str  # Organization name
    tier: str  # LicenseTier value
    model: str  # LicenseModel value
    issued_at: float  # Unix timestamp
    expires_at: float  # Unix timestamp (0 = perpetual)
    max_authorized_users: int = 1  # Per Order Form
    max_deployment_instances: int = 1  # Per Order Form
    max_swarm_agents: int = 3  # Per Order Form
    max_decisions_per_month: int = 0  # 0 = unlimited
    modules: List[str] = field(default_factory=lambda: ["core"])
    patent_grant: bool = True  # US Patent 63/961,403
    support_level: str = "none"  # none, community, email, dedicated
    white_label: bool = False  # OEM white-label rights
    air_gap_approved: bool = False  # Source-available deployment
    custom_terms: Dict[str, Any] = field(default_factory=dict)

    def canonical_json(self) -> str:
        """Deterministic JSON for HMAC signing."""
        d = asdict(self)
        return json.dumps(d, sort_keys=True, separators=(",", ":"))


# ── License Key ──────────────────────────────────────────────────────────────


@dataclass
class LicenseKey:
    """A signed license key containing claims + HMAC signature."""

    claims: LicenseClaims
    signature: str  # hex-encoded HMAC-SHA256

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claims": asdict(self.claims),
            "signature": self.signature,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LicenseKey":
        claims = LicenseClaims(**d["claims"])
        return cls(claims=claims, signature=d["signature"])

    @classmethod
    def from_json(cls, s: str) -> "LicenseKey":
        return cls.from_dict(json.loads(s))


# ── License Generator ────────────────────────────────────────────────────────


def generate_license_key(
    claims: LicenseClaims,
    signing_secret: str,
) -> LicenseKey:
    """Generate a signed license key.

    Uses HMAC-SHA256 over the canonical JSON of claims.
    No network call — works offline / air-gapped.

    Args:
        claims: License claims to embed.
        signing_secret: Secret key for HMAC signing.

    Returns:
        LicenseKey with claims and signature.
    """
    canonical = claims.canonical_json()
    sig = hmac.new(
        signing_secret.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return LicenseKey(claims=claims, signature=sig)


# ── License Validator ────────────────────────────────────────────────────────


@dataclass
class ValidationResult:
    """Result of license validation."""

    valid: bool
    tier: str
    model: str
    reason: str
    remaining_decisions: Optional[int] = None
    expires_in_days: Optional[float] = None
    modules: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def validate_license_key(
    key: LicenseKey,
    signing_secret: str,
    current_decisions_this_month: int = 0,
) -> ValidationResult:
    """Validate a license key at runtime.

    Checks:
      1. HMAC signature integrity
      2. Expiration (if not perpetual)
      3. Decision quota (if usage-based)
      4. Tier-specific constraints

    Args:
        key: The license key to validate.
        signing_secret: Secret for HMAC verification.
        current_decisions_this_month: Current usage count.

    Returns:
        ValidationResult with pass/fail and diagnostics.
    """
    claims = key.claims
    warnings: List[str] = []

    # 1. Signature check
    canonical = claims.canonical_json()
    expected_sig = hmac.new(
        signing_secret.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(key.signature, expected_sig):
        return ValidationResult(
            valid=False,
            tier=claims.tier,
            model=claims.model,
            reason="INVALID_SIGNATURE",
            modules=[],
        )

    # 2. Expiration check
    now = time.time()
    expires_in_days = None
    if claims.expires_at > 0:
        if now > claims.expires_at:
            return ValidationResult(
                valid=False,
                tier=claims.tier,
                model=claims.model,
                reason="LICENSE_EXPIRED",
                modules=claims.modules,
            )
        expires_in_days = (claims.expires_at - now) / 86400
        if expires_in_days < 30:
            warnings.append(f"License expires in {expires_in_days:.0f} days")

    # 3. Decision quota check
    remaining = None
    if claims.max_decisions_per_month > 0:
        remaining = claims.max_decisions_per_month - current_decisions_this_month
        if remaining <= 0:
            return ValidationResult(
                valid=False,
                tier=claims.tier,
                model=claims.model,
                reason="DECISION_QUOTA_EXCEEDED",
                remaining_decisions=0,
                modules=claims.modules,
            )
        if remaining < claims.max_decisions_per_month * 0.1:
            warnings.append(f"Only {remaining} decisions remaining this month")

    return ValidationResult(
        valid=True,
        tier=claims.tier,
        model=claims.model,
        reason="VALID",
        remaining_decisions=remaining,
        expires_in_days=round(expires_in_days, 1) if expires_in_days else None,
        modules=claims.modules,
        warnings=warnings,
    )


# ── Tier Presets ─────────────────────────────────────────────────────────────

TIER_DEFAULTS = {
    LicenseTier.HOMEBREW: {
        "max_authorized_users": 1,
        "max_deployment_instances": 1,
        "max_swarm_agents": 3,
        "max_decisions_per_month": 10_000,
        "support_level": "community",
        "white_label": False,
        "air_gap_approved": False,
        "modules": ["core", "harmonic", "crypto"],
    },
    LicenseTier.PROFESSIONAL: {
        "max_authorized_users": 10,
        "max_deployment_instances": 5,
        "max_swarm_agents": 12,
        "max_decisions_per_month": 100_000,
        "support_level": "email",
        "white_label": False,
        "air_gap_approved": False,
        "modules": ["core", "harmonic", "crypto", "symphonic", "governance", "spectral"],
    },
    LicenseTier.ENTERPRISE: {
        "max_authorized_users": 0,  # unlimited
        "max_deployment_instances": 0,
        "max_swarm_agents": 0,
        "max_decisions_per_month": 0,
        "support_level": "dedicated",
        "white_label": False,
        "air_gap_approved": True,
        "modules": [
            "core",
            "harmonic",
            "crypto",
            "symphonic",
            "governance",
            "spectral",
            "fleet",
            "training",
            "ai_brain",
        ],
    },
    LicenseTier.OEM: {
        "max_authorized_users": 0,
        "max_deployment_instances": 0,
        "max_swarm_agents": 0,
        "max_decisions_per_month": 0,
        "support_level": "none",
        "white_label": True,
        "air_gap_approved": True,
        "modules": [
            "core",
            "harmonic",
            "crypto",
            "symphonic",
            "governance",
            "spectral",
            "fleet",
            "training",
            "ai_brain",
            "gateway",
        ],
    },
    LicenseTier.SOURCE_AVAILABLE: {
        "max_authorized_users": 0,
        "max_deployment_instances": 0,
        "max_swarm_agents": 0,
        "max_decisions_per_month": 0,
        "support_level": "none",
        "white_label": False,
        "air_gap_approved": True,
        "modules": [
            "core",
            "harmonic",
            "crypto",
            "symphonic",
            "governance",
            "spectral",
            "fleet",
            "training",
            "ai_brain",
        ],
    },
}


def create_tier_license(
    tier: LicenseTier,
    licensee: str,
    model: LicenseModel = LicenseModel.SUBSCRIPTION,
    duration_days: int = 365,
    signing_secret: str = "",
    **overrides: Any,
) -> LicenseKey:
    """Create a license key with tier-appropriate defaults.

    Args:
        tier: License tier.
        licensee: Organization name.
        model: Monetization model.
        duration_days: License duration (0 = perpetual).
        signing_secret: HMAC signing secret.
        **overrides: Override any default claim field.

    Returns:
        Signed LicenseKey.
    """
    defaults = TIER_DEFAULTS[tier].copy()
    defaults.update(overrides)

    now = time.time()
    claims = LicenseClaims(
        licensee=licensee,
        tier=tier.value,
        model=model.value,
        issued_at=now,
        expires_at=now + (duration_days * 86400) if duration_days > 0 else 0.0,
        **defaults,
    )

    return generate_license_key(claims, signing_secret)
