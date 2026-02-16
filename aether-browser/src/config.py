"""
AetherBrowser SCBE Security Configuration
==========================================

Default constants and configuration for the SCBE (Spectral Context Bound
Encryption) security layer integrated into AetherBrowser.

All values derive from the SCBE-AETHERMOORE framework:
  - Golden Ratio (phi) weighting for trust and coherence metrics
  - Poincare ball model for hyperbolic trust geometry
  - Harmonic ratios from music theory for scaling constants
  - Six Sacred Tongues for multi-dimensional content analysis

Document ID: AETHER-BROWSER-CONFIG-2026-001
Version: 1.0.0
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from enum import Enum


# =============================================================================
# UNIVERSAL MATHEMATICAL CONSTANTS
# =============================================================================

PI: float = math.pi                            # 3.141592653589793
E: float = math.e                              # 2.718281828459045
PHI: float = (1.0 + math.sqrt(5.0)) / 2.0     # 1.618033988749895 (Golden Ratio)
SQRT2: float = math.sqrt(2.0)                  # 1.4142135623730951
SQRT5: float = math.sqrt(5.0)                  # 2.23606797749979


# =============================================================================
# HARMONIC RATIO CONSTANTS (Music Theory Derived)
# =============================================================================

R_FIFTH: float = 1.5           # 3:2 - Perfect Fifth (Primary harmonic ratio)
R_FOURTH: float = 4.0 / 3.0   # 4:3 - Perfect Fourth
R_THIRD: float = 1.25          # 5:4 - Major Third
R_SIXTH: float = 1.6           # 8:5 - Minor Sixth
R_OCTAVE: float = 2.0          # 2:1 - Octave


# =============================================================================
# AETHERMOORE DERIVED CONSTANTS
# =============================================================================

PHI_AETHER: float = PHI ** (1.0 / R_FIFTH)    # phi^(2/3) ~ 1.3782
LAMBDA_ISAAC: float = R_FIFTH * (PHI ** 2)     # R5 * phi^2 ~ 3.9271
OMEGA_SPIRAL: float = (2.0 * PI) / (PHI ** 3)  # 2pi / phi^3 ~ 1.4833
ALPHA_ABH: float = PHI + R_FIFTH               # phi + 1.5 ~ 3.1180


# =============================================================================
# POINCARE BALL GEOMETRY
# =============================================================================

BALL_RADIUS: float = 0.999       # Clamp boundary for Poincare ball (strictly < 1)
CURVATURE: float = -1.0          # Constant negative curvature
EPSILON: float = 1e-9            # Numerical safety epsilon


# =============================================================================
# TRUST ZONE CONFIGURATION
# =============================================================================

class TrustZone(Enum):
    """Trust zones for domain classification in AetherBrowser.

    Zones form concentric regions in the Poincare ball:
      - CORE: origin region (r < 0.2), bookmarks and known-safe sites
      - INNER: near-center (r < 0.5), authenticated / previously-trusted sites
      - OUTER: mid-ball (r < 0.8), general web browsing
      - WALL: boundary region (r >= 0.8), blocked or highly suspicious
    """
    CORE = "CORE"
    INNER = "INNER"
    OUTER = "OUTER"
    WALL = "WALL"


# Poincare ball radius thresholds for each zone boundary
ZONE_THRESHOLDS: Dict[str, float] = {
    "CORE": 0.2,    # r < 0.2  -> CORE
    "INNER": 0.5,   # r < 0.5  -> INNER
    "OUTER": 0.8,   # r < 0.8  -> OUTER
    # r >= 0.8 -> WALL
}


# =============================================================================
# GOVERNANCE DECISION TYPES
# =============================================================================

class Decision(Enum):
    """Security decisions from the SCBE classification pipeline.

    Mirrors the SCBE-AETHERMOORE L13 risk decision tiers:
      ALLOW:      Safe operation, low risk
      QUARANTINE: Suspicious, needs review / sandboxed execution
      DENY:       Adversarial or policy-violating, blocked outright
    """
    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    DENY = "DENY"


# Risk score thresholds for governance decisions
ALLOW_THRESHOLD: float = 0.3    # risk < 0.3 -> ALLOW
DENY_THRESHOLD: float = 0.7     # risk >= 0.7 -> DENY
# 0.3 <= risk < 0.7 -> QUARANTINE


# =============================================================================
# SIX SACRED TONGUES - BROWSER CONTENT ANALYSIS MAPPING
# =============================================================================

class SacredTongue(Enum):
    """The Six Sacred Tongues mapped to browser content analysis categories.

    Each tongue corresponds to a cryptographic section in SS1 format and is
    repurposed here as a content analysis dimension for web page evaluation.
    """
    KO = "KO"   # Kor'aelin  - Intent analysis (nonce/flow)
    AV = "AV"   # Avali      - Transport security (aad/header)
    RU = "RU"   # Runethic   - Permission checking (salt/binding)
    CA = "CA"   # Cassisivadan - Computation safety (ciphertext/bitcraft)
    UM = "UM"   # Umbroth    - Privacy protection (redaction/veil)
    DR = "DR"   # Draumric   - Schema validation (tag/structure)


# Tongue descriptions for browser security context
TONGUE_DESCRIPTIONS: Dict[str, str] = {
    "KO": "Intent analysis: Is the page doing what it claims?",
    "AV": "Transport security: Is the connection secure and authentic?",
    "RU": "Permission checking: Does the page have permission for requested resources?",
    "CA": "Computation safety: Is the page running safe scripts?",
    "UM": "Privacy protection: Is the page leaking user data?",
    "DR": "Schema validation: Does the page structure match expectations?",
}

# Golden-ratio-derived weights for phi-weighted composite scoring
# Weight for tongue i = PHI^(-i) / sum(PHI^(-j) for j in 0..5)
_raw_tongue_weights: List[float] = [PHI ** (-i) for i in range(6)]
_tongue_weight_sum: float = sum(_raw_tongue_weights)
TONGUE_WEIGHTS: Dict[str, float] = {
    tongue.value: _raw_tongue_weights[i] / _tongue_weight_sum
    for i, tongue in enumerate(SacredTongue)
}


# =============================================================================
# HARMONIC WALL CONFIGURATION
# =============================================================================

HARMONIC_ALPHA: float = 10.0    # Maximum additional risk multiplier
HARMONIC_BETA: float = 0.5      # Growth rate (saturation speed control)
HARMONIC_WALL_MAX_DEPTH: int = 20  # Maximum redirect/iframe depth before hard block
HARMONIC_WALL_COST_LIMIT: float = 8.0  # Cost threshold for blocking (depth ~2 triggers)


# =============================================================================
# CERTIFICATE VERIFICATION
# =============================================================================

# Minimum number of certificates in a valid chain (leaf + at least one CA)
MIN_CERT_CHAIN_LENGTH: int = 2

# Maximum chain depth before rejection
MAX_CERT_CHAIN_DEPTH: int = 10

# Hash algorithm for certificate fingerprinting
CERT_HASH_ALGORITHM: str = "sha256"


# =============================================================================
# DOMAIN TRUST DEFAULTS
# =============================================================================

@dataclass(frozen=True)
class DomainTrustDefaults:
    """Default trust parameters for domain classification.

    Attributes:
        initial_zone: Zone assigned to never-before-seen domains.
        promotion_evidence_threshold: Minimum evidence score to promote a domain.
        demotion_cooldown_seconds: Seconds before a demoted domain can be re-promoted.
        max_promotions_per_hour: Rate limit on zone promotions (prevents gaming).
    """
    initial_zone: str = "OUTER"
    promotion_evidence_threshold: float = 0.7
    demotion_cooldown_seconds: int = 3600
    max_promotions_per_hour: int = 5


DOMAIN_TRUST_DEFAULTS: DomainTrustDefaults = DomainTrustDefaults()


# =============================================================================
# KNOWN TRUSTED DOMAINS (CORE zone by default)
# =============================================================================

CORE_TRUSTED_DOMAINS: Tuple[str, ...] = (
    "example.com",
    "localhost",
    "127.0.0.1",
)


# =============================================================================
# BLOCKED DOMAINS (WALL zone, always denied)
# =============================================================================

WALL_BLOCKED_DOMAINS: Tuple[str, ...] = (
    "malware.test",
    "phishing.test",
    "blocked.test",
)


# =============================================================================
# HTTP METHOD RISK WEIGHTS
# =============================================================================

METHOD_RISK_WEIGHTS: Dict[str, float] = {
    "GET": 0.0,       # Read-only, lowest risk
    "HEAD": 0.0,      # Metadata only
    "OPTIONS": 0.0,   # CORS preflight
    "POST": 0.3,      # Data submission
    "PUT": 0.4,       # Resource replacement
    "PATCH": 0.3,     # Partial update
    "DELETE": 0.5,    # Destructive
}


# =============================================================================
# PRECOMPUTED REFERENCE VALUES
# =============================================================================

def harmonic_scale(d: int, R: float = R_FIFTH) -> float:
    """Compute the Harmonic Scaling value H(d, R) = R^(d^2).

    This is the core AETHERMOORE super-exponential growth formula.

    Args:
        d: Dimension count (positive integer, typically 1-6).
        R: Harmonic ratio (positive real, default 1.5).

    Returns:
        The harmonic scaling multiplier.

    Raises:
        ValueError: If d < 1 or R <= 0.
    """
    if d < 1:
        raise ValueError(f"Dimension d must be >= 1, got {d}")
    if R <= 0:
        raise ValueError(f"Harmonic ratio R must be > 0, got {R}")
    return R ** (d * d)


# Precomputed harmonic scale table for d=1..6 with R=1.5
HARMONIC_SCALE_TABLE: Dict[int, float] = {
    d: harmonic_scale(d, R_FIFTH) for d in range(1, 7)
}
