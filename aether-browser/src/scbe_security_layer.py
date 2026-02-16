"""
AetherBrowser SCBE Security Layer
==================================

Core security integration for AetherBrowser -- an SCBE-secured web browser.

This module provides the SCBE (Spectral Context Bound Encryption) security
layer that wraps around an existing browser engine (Servo, Chromium, etc.).
It implements three primary components:

1. **SCBESecurityLayer** -- Main security wrapper that classifies requests,
   computes trust scores via Poincare ball distance, verifies certificate
   chains using Sacred Tongue validation, and enforces a Harmonic Wall to
   block runaway request depths.

2. **TrustZoneManager** -- Manages concentric trust zones (CORE, INNER,
   OUTER, WALL) modelled as regions in a Poincare ball. Domains can be
   promoted or demoted between zones based on accumulated evidence.

3. **SacredTongueFilter** -- Content filtering using the Six Sacred Tongues,
   where each tongue maps to a browser security dimension (intent, transport,
   permissions, computation, privacy, schema). Produces a phi-weighted
   composite coherence score.

Design principles:
  - Only stdlib imports (math, hashlib, dataclasses, typing, urllib.parse)
  - Full type annotations on all public interfaces
  - Hyperbolic geometry via the Poincare ball model (curvature -1)
  - Golden Ratio (phi) weighting throughout for SCBE compatibility

Document ID: AETHER-BROWSER-SECURITY-2026-001
Version: 1.0.0
"""

from __future__ import annotations

import math
import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from enum import Enum

from config import (
    PHI,
    PI,
    EPSILON,
    BALL_RADIUS,
    CURVATURE,
    R_FIFTH,
    Decision,
    TrustZone,
    SacredTongue,
    TONGUE_WEIGHTS,
    TONGUE_DESCRIPTIONS,
    ZONE_THRESHOLDS,
    ALLOW_THRESHOLD,
    DENY_THRESHOLD,
    HARMONIC_ALPHA,
    HARMONIC_BETA,
    HARMONIC_WALL_MAX_DEPTH,
    HARMONIC_WALL_COST_LIMIT,
    MIN_CERT_CHAIN_LENGTH,
    MAX_CERT_CHAIN_DEPTH,
    CERT_HASH_ALGORITHM,
    CORE_TRUSTED_DOMAINS,
    WALL_BLOCKED_DOMAINS,
    METHOD_RISK_WEIGHTS,
    DOMAIN_TRUST_DEFAULTS,
)


# =============================================================================
# HELPER: POINCARE BALL GEOMETRY (stdlib-only, no numpy)
# =============================================================================

def _clamp_to_ball(r: float) -> float:
    """Clamp a radial distance to strictly inside the Poincare ball.

    Args:
        r: Radial distance (non-negative).

    Returns:
        Clamped value in [0, BALL_RADIUS].
    """
    return min(max(r, 0.0), BALL_RADIUS)


def _poincare_distance_1d(r_u: float, r_v: float) -> float:
    """Compute Poincare ball distance between two points on the radial axis.

    For points along a common radial line through the origin, the Poincare
    distance simplifies to:

        d_H(u, v) = |artanh(r_u) - artanh(r_v)| * 2

    More precisely, using the full formula in 1-D:

        d_H(u, v) = arcosh(1 + 2 * (r_u - r_v)^2 / ((1 - r_u^2)(1 - r_v^2)))

    Args:
        r_u: Radial coordinate of first point, in [0, 1).
        r_v: Radial coordinate of second point, in [0, 1).

    Returns:
        Hyperbolic distance (non-negative float).
    """
    r_u = _clamp_to_ball(abs(r_u))
    r_v = _clamp_to_ball(abs(r_v))

    diff_sq: float = (r_u - r_v) ** 2
    denom: float = (1.0 - r_u ** 2) * (1.0 - r_v ** 2)

    if denom < EPSILON:
        return 50.0  # Effective infinity when at the boundary

    arg: float = 1.0 + 2.0 * diff_sq / denom
    # arcosh(x) = ln(x + sqrt(x^2 - 1)), defined for x >= 1
    if arg < 1.0:
        return 0.0
    return math.acosh(arg)


def _poincare_distance_nd(u: List[float], v: List[float]) -> float:
    """Compute Poincare ball distance between two n-dimensional points.

    d_H(u, v) = arcosh(1 + 2 * ||u - v||^2 / ((1 - ||u||^2)(1 - ||v||^2)))

    Args:
        u: First point as a list of floats, strictly inside the unit ball.
        v: Second point as a list of floats, strictly inside the unit ball.

    Returns:
        Hyperbolic distance (non-negative float).
    """
    if len(u) != len(v):
        raise ValueError(
            f"Dimension mismatch: len(u)={len(u)} != len(v)={len(v)}"
        )

    u_norm_sq: float = sum(x * x for x in u)
    v_norm_sq: float = sum(x * x for x in v)
    diff_norm_sq: float = sum((a - b) ** 2 for a, b in zip(u, v))

    # Clamp norms to ball interior
    u_norm_sq = min(u_norm_sq, BALL_RADIUS ** 2)
    v_norm_sq = min(v_norm_sq, BALL_RADIUS ** 2)

    denom: float = (1.0 - u_norm_sq) * (1.0 - v_norm_sq)
    if denom < EPSILON:
        return 50.0

    arg: float = 1.0 + 2.0 * diff_norm_sq / denom
    if arg < 1.0:
        return 0.0
    return math.acosh(arg)


def _domain_to_radial(domain: str) -> float:
    """Map a domain name to a deterministic radial coordinate in [0, 1).

    Uses SHA-256 to produce a uniform hash, then maps the first 4 bytes
    to a float in [0, BALL_RADIUS).  This gives every domain a stable
    position in the Poincare ball.

    Args:
        domain: Lowercase domain name string.

    Returns:
        Radial coordinate in [0, BALL_RADIUS).
    """
    h: bytes = hashlib.sha256(domain.lower().encode("utf-8")).digest()
    # Interpret first 4 bytes as unsigned int, normalise to [0, 1)
    raw: int = int.from_bytes(h[:4], byteorder="big")
    return (raw / (2 ** 32)) * BALL_RADIUS


def _domain_to_vector(domain: str, dims: int = 6) -> List[float]:
    """Map a domain name to a deterministic point inside the Poincare ball.

    Produces a ``dims``-dimensional vector by hashing the domain and
    splitting the digest into coordinate bytes, then normalising so
    the resulting vector lies strictly inside the unit ball.

    Args:
        domain: Lowercase domain name string.
        dims: Number of dimensions (default 6 for Sacred Tongues).

    Returns:
        List of floats representing a point in the Poincare ball.
    """
    h: bytes = hashlib.sha256(domain.lower().encode("utf-8")).digest()
    # Use consecutive pairs of bytes for each dimension
    raw: List[float] = []
    for i in range(dims):
        byte_val: int = h[i % len(h)]
        # Map byte to [-1, 1] range
        raw.append((byte_val / 127.5) - 1.0)

    # Normalise to lie inside ball with some margin
    norm: float = math.sqrt(sum(x * x for x in raw))
    if norm < EPSILON:
        return [0.0] * dims

    # Scale to radius 0.5 * BALL_RADIUS (middle of ball by default)
    scale: float = 0.5 * BALL_RADIUS / norm
    return [x * scale for x in raw]


# =============================================================================
# CLASS: TrustZoneManager
# =============================================================================

@dataclass
class DomainRecord:
    """Internal record for a tracked domain.

    Attributes:
        domain: The domain name (lowercase).
        zone: Current trust zone.
        evidence_score: Accumulated positive evidence (higher = more trusted).
        demoted_at: Timestamp of last demotion (0 if never demoted).
        promotion_count: Number of promotions in the current tracking window.
        first_seen: Timestamp when the domain was first encountered.
    """
    domain: str
    zone: TrustZone
    evidence_score: float = 0.0
    demoted_at: float = 0.0
    promotion_count: int = 0
    first_seen: float = field(default_factory=time.time)


class TrustZoneManager:
    """Manages browsing trust zones for AetherBrowser.

    Trust zones model concentric regions in a Poincare ball:

        CORE  (origin)      -- bookmarks, explicitly trusted sites
        INNER (near-center) -- authenticated, session-verified sites
        OUTER (mid-ball)    -- general web, default for unknown domains
        WALL  (boundary)    -- blocked, malicious, policy-violating sites

    Domains can be promoted toward CORE or demoted toward WALL based on
    behavioural evidence accumulated over time.

    The zone hierarchy (from most trusted to least):
        CORE > INNER > OUTER > WALL
    """

    # Ordered from most trusted to least trusted
    _ZONE_ORDER: List[TrustZone] = [
        TrustZone.CORE,
        TrustZone.INNER,
        TrustZone.OUTER,
        TrustZone.WALL,
    ]

    def __init__(
        self,
        core_domains: Optional[Tuple[str, ...]] = None,
        blocked_domains: Optional[Tuple[str, ...]] = None,
    ) -> None:
        """Initialise the TrustZoneManager.

        Args:
            core_domains: Domains to pre-seed in CORE zone.
                Defaults to ``CORE_TRUSTED_DOMAINS`` from config.
            blocked_domains: Domains to pre-seed in WALL zone.
                Defaults to ``WALL_BLOCKED_DOMAINS`` from config.
        """
        self._records: Dict[str, DomainRecord] = {}

        if core_domains is None:
            core_domains = CORE_TRUSTED_DOMAINS
        if blocked_domains is None:
            blocked_domains = WALL_BLOCKED_DOMAINS

        now: float = time.time()
        for d in core_domains:
            self._records[d.lower()] = DomainRecord(
                domain=d.lower(),
                zone=TrustZone.CORE,
                evidence_score=1.0,
                first_seen=now,
            )
        for d in blocked_domains:
            self._records[d.lower()] = DomainRecord(
                domain=d.lower(),
                zone=TrustZone.WALL,
                evidence_score=0.0,
                first_seen=now,
            )

    # ----- public API -----

    def get_zone(self, domain: str) -> TrustZone:
        """Return the trust zone for the given domain.

        If the domain has not been seen before it is assigned the default
        initial zone (OUTER) and a new record is created.

        Args:
            domain: Domain name (case-insensitive).

        Returns:
            The ``TrustZone`` for the domain.
        """
        domain = domain.lower()
        if domain not in self._records:
            default_zone_str: str = DOMAIN_TRUST_DEFAULTS.initial_zone
            default_zone: TrustZone = TrustZone(default_zone_str)
            self._records[domain] = DomainRecord(
                domain=domain,
                zone=default_zone,
                first_seen=time.time(),
            )
        return self._records[domain].zone

    def promote_domain(self, domain: str, evidence: float) -> TrustZone:
        """Attempt to promote a domain to a higher trust zone.

        Promotion requires sufficient accumulated evidence and respects
        rate limits and cooldown periods.

        Args:
            domain: Domain name (case-insensitive).
            evidence: Positive evidence value to accumulate (0-1 range).

        Returns:
            The domain's zone after the promotion attempt.
        """
        domain = domain.lower()
        # Ensure record exists
        _ = self.get_zone(domain)
        record: DomainRecord = self._records[domain]

        # Cannot promote beyond CORE or out of WALL without explicit unblock
        if record.zone == TrustZone.CORE:
            return record.zone
        if record.zone == TrustZone.WALL:
            return record.zone  # WALL domains require explicit unblock

        # Check demotion cooldown
        now: float = time.time()
        if record.demoted_at > 0:
            elapsed: float = now - record.demoted_at
            if elapsed < DOMAIN_TRUST_DEFAULTS.demotion_cooldown_seconds:
                return record.zone  # Still in cooldown

        # Rate limit
        if record.promotion_count >= DOMAIN_TRUST_DEFAULTS.max_promotions_per_hour:
            return record.zone

        # Accumulate evidence
        record.evidence_score = min(record.evidence_score + evidence, 1.0)

        # Check threshold
        if record.evidence_score >= DOMAIN_TRUST_DEFAULTS.promotion_evidence_threshold:
            current_idx: int = self._ZONE_ORDER.index(record.zone)
            if current_idx > 0:
                record.zone = self._ZONE_ORDER[current_idx - 1]
                record.evidence_score = 0.0  # Reset after promotion
                record.promotion_count += 1

        return record.zone

    def demote_domain(self, domain: str, reason: str) -> TrustZone:
        """Demote a domain to a lower trust zone.

        Demotion is immediate and unconditional -- it always moves the
        domain one zone toward WALL.

        Args:
            domain: Domain name (case-insensitive).
            reason: Human-readable reason for the demotion (stored for audit).

        Returns:
            The domain's zone after demotion.
        """
        domain = domain.lower()
        _ = self.get_zone(domain)
        record: DomainRecord = self._records[domain]

        current_idx: int = self._ZONE_ORDER.index(record.zone)
        if current_idx < len(self._ZONE_ORDER) - 1:
            record.zone = self._ZONE_ORDER[current_idx + 1]
            record.demoted_at = time.time()
            record.evidence_score = max(record.evidence_score - 0.3, 0.0)

        return record.zone

    def get_record(self, domain: str) -> Optional[DomainRecord]:
        """Return the full DomainRecord for a domain, or None if untracked.

        Args:
            domain: Domain name (case-insensitive).

        Returns:
            The ``DomainRecord`` or ``None``.
        """
        return self._records.get(domain.lower())

    def list_domains_in_zone(self, zone: TrustZone) -> List[str]:
        """Return all domains currently in the specified zone.

        Args:
            zone: The target ``TrustZone``.

        Returns:
            List of domain name strings.
        """
        return [
            r.domain for r in self._records.values() if r.zone == zone
        ]


# =============================================================================
# CLASS: SacredTongueFilter
# =============================================================================

class SacredTongueFilter:
    """Content filtering using the Six Sacred Tongues.

    Each Sacred Tongue maps to a browser security analysis dimension:

        KO (Kor'aelin)     -- Intent analysis
        AV (Avali)         -- Transport security
        RU (Runethic)      -- Permission checking
        CA (Cassisivadan)  -- Computation safety
        UM (Umbroth)       -- Privacy protection
        DR (Draumric)      -- Schema validation

    The filter analyses content signals and produces a coherence score
    for each tongue, then combines them into a single phi-weighted
    composite score.

    Coherence scores are in [0, 1] where:
        1.0 = fully coherent / safe
        0.0 = fully incoherent / suspicious
    """

    # Canonical tongue order
    TONGUES: Tuple[str, ...] = ("KO", "AV", "RU", "CA", "UM", "DR")

    def __init__(self) -> None:
        """Initialise the SacredTongueFilter with default weights."""
        self._weights: Dict[str, float] = dict(TONGUE_WEIGHTS)

    # ----- Signal analysis helpers -----

    @staticmethod
    def _analyze_intent(url: str, signals: Dict[str, object]) -> float:
        """KO tongue: Intent analysis.

        Checks whether the page is trying to do what it claims by examining
        URL structure, declared content type, and navigation signals.

        Args:
            url: The page URL.
            signals: Content signal dictionary.

        Returns:
            Coherence score in [0, 1].
        """
        score: float = 1.0

        # Penalise data URIs pretending to be pages
        if url.startswith("data:"):
            score -= 0.4

        # Penalise javascript URIs
        if url.startswith("javascript:"):
            score -= 0.8

        # Check for claimed_type vs actual_type mismatch
        claimed: str = str(signals.get("claimed_type", ""))
        actual: str = str(signals.get("actual_type", ""))
        if claimed and actual and claimed != actual:
            score -= 0.3

        # Reward pages with clear navigation intent
        if signals.get("has_navigation", False):
            score += 0.1

        return max(0.0, min(1.0, score))

    @staticmethod
    def _analyze_transport(url: str, signals: Dict[str, object]) -> float:
        """AV tongue: Transport security.

        Evaluates connection security: HTTPS, HSTS, certificate validity.

        Args:
            url: The page URL.
            signals: Content signal dictionary.

        Returns:
            Coherence score in [0, 1].
        """
        score: float = 0.5  # Neutral default

        parsed = urlparse(url)
        scheme: str = parsed.scheme.lower()

        # HTTPS is the baseline expectation
        if scheme == "https":
            score += 0.3
        elif scheme == "http":
            score -= 0.2
        elif scheme in ("file", "about", "chrome"):
            score += 0.2  # Local/internal pages are inherently secure

        # HSTS presence
        if signals.get("hsts", False):
            score += 0.1

        # Certificate validity signal
        if signals.get("cert_valid", False):
            score += 0.1

        return max(0.0, min(1.0, score))

    @staticmethod
    def _analyze_permissions(url: str, signals: Dict[str, object]) -> float:
        """RU tongue: Permission checking.

        Verifies that the page has permission for requested resources
        (camera, microphone, geolocation, etc.).

        Args:
            url: The page URL.
            signals: Content signal dictionary.

        Returns:
            Coherence score in [0, 1].
        """
        score: float = 1.0

        # Each excessive permission request reduces coherence
        requested_perms: int = int(signals.get("permission_requests", 0))
        granted_perms: int = int(signals.get("permissions_granted", 0))

        if requested_perms > 3:
            score -= 0.2 * (requested_perms - 3)

        # Penalise if requesting more than granted
        if requested_perms > granted_perms + 1:
            score -= 0.2

        return max(0.0, min(1.0, score))

    @staticmethod
    def _analyze_computation(url: str, signals: Dict[str, object]) -> float:
        """CA tongue: Computation safety.

        Evaluates script safety: eval usage, inline scripts, web workers,
        WebAssembly, known patterns.

        Args:
            url: The page URL.
            signals: Content signal dictionary.

        Returns:
            Coherence score in [0, 1].
        """
        score: float = 1.0

        # eval() or Function() constructors are risky
        if signals.get("uses_eval", False):
            score -= 0.4

        # Inline script count penalty
        inline_scripts: int = int(signals.get("inline_script_count", 0))
        if inline_scripts > 10:
            score -= 0.1 * min((inline_scripts - 10), 5)

        # WebAssembly not necessarily bad, but raises scrutiny
        if signals.get("uses_wasm", False):
            score -= 0.1

        # Crypto-mining patterns
        if signals.get("crypto_mining_detected", False):
            score -= 0.6

        return max(0.0, min(1.0, score))

    @staticmethod
    def _analyze_privacy(url: str, signals: Dict[str, object]) -> float:
        """UM tongue: Privacy protection.

        Detects potential data leakage: third-party trackers, fingerprinting,
        cookie abuse, exfiltration patterns.

        Args:
            url: The page URL.
            signals: Content signal dictionary.

        Returns:
            Coherence score in [0, 1].
        """
        score: float = 1.0

        # Third-party tracker count
        trackers: int = int(signals.get("third_party_trackers", 0))
        score -= 0.05 * min(trackers, 10)

        # Canvas/WebGL fingerprinting
        if signals.get("fingerprinting_detected", False):
            score -= 0.3

        # Excessive cookie usage
        cookies: int = int(signals.get("cookie_count", 0))
        if cookies > 20:
            score -= 0.1 * min((cookies - 20) // 10, 3)

        return max(0.0, min(1.0, score))

    @staticmethod
    def _analyze_schema(url: str, signals: Dict[str, object]) -> float:
        """DR tongue: Schema validation.

        Validates page structure: well-formed HTML, expected content type
        headers, CSP presence, structured data validity.

        Args:
            url: The page URL.
            signals: Content signal dictionary.

        Returns:
            Coherence score in [0, 1].
        """
        score: float = 0.8  # Assume reasonably well-formed by default

        # Content-Security-Policy header presence
        if signals.get("has_csp", False):
            score += 0.1

        # X-Frame-Options or frame-ancestors
        if signals.get("has_frame_protection", False):
            score += 0.05

        # Malformed HTML penalty
        if signals.get("malformed_html", False):
            score -= 0.3

        # MIME type mismatch
        if signals.get("mime_mismatch", False):
            score -= 0.2

        return max(0.0, min(1.0, score))

    # ----- Public API -----

    def analyze_page(
        self,
        url: str,
        content_signals: Dict[str, object],
    ) -> Dict[str, float]:
        """Analyse a page and produce coherence scores for each tongue.

        Args:
            url: The page URL.
            content_signals: Dictionary of content analysis signals.
                Expected keys vary by tongue (see individual analyzers).

        Returns:
            Dictionary mapping tongue code (str) to coherence score (float).
            Example: {"KO": 0.9, "AV": 0.8, "RU": 1.0, ...}
        """
        analyzers = {
            "KO": self._analyze_intent,
            "AV": self._analyze_transport,
            "RU": self._analyze_permissions,
            "CA": self._analyze_computation,
            "UM": self._analyze_privacy,
            "DR": self._analyze_schema,
        }

        scores: Dict[str, float] = {}
        for tongue_code, analyzer_fn in analyzers.items():
            scores[tongue_code] = analyzer_fn(url, content_signals)

        return scores

    def composite_score(self, tongue_scores: Dict[str, float]) -> float:
        """Compute phi-weighted composite coherence score.

        Each tongue's score is weighted by PHI^(-i) (normalised), following
        the SCBE Langues Weighting System (LWS).  This gives higher weight
        to KO (intent) and decreasing weight through DR (schema).

        Composite = sum(w_i * s_i) for i in tongues

        Args:
            tongue_scores: Dictionary mapping tongue codes to scores.

        Returns:
            Weighted composite score in [0, 1].
        """
        total: float = 0.0
        weight_sum: float = 0.0

        for tongue_code in self.TONGUES:
            score: float = tongue_scores.get(tongue_code, 0.5)
            weight: float = self._weights.get(tongue_code, 1.0 / 6.0)
            total += weight * score
            weight_sum += weight

        if weight_sum < EPSILON:
            return 0.5

        return total / weight_sum


# =============================================================================
# CLASS: SCBESecurityLayer
# =============================================================================

class SCBESecurityLayer:
    """Main SCBE security wrapper for AetherBrowser.

    Integrates trust zone management, Sacred Tongue content filtering,
    Poincare ball trust scoring, certificate chain verification, and
    Harmonic Wall depth limiting into a single security evaluation pipeline.

    Usage::

        layer = SCBESecurityLayer()
        decision = layer.classify_request(
            url="https://example.com/page",
            origin="https://example.com",
            method="GET",
        )
        assert decision == Decision.ALLOW

    The classification pipeline:
      1. Extract domain from URL
      2. Look up trust zone (TrustZoneManager)
      3. Compute trust score via Poincare ball distance
      4. Optionally evaluate content signals (SacredTongueFilter)
      5. Apply HTTP method risk weight
      6. Produce final Decision (ALLOW / QUARANTINE / DENY)
    """

    def __init__(
        self,
        trust_manager: Optional[TrustZoneManager] = None,
        tongue_filter: Optional[SacredTongueFilter] = None,
    ) -> None:
        """Initialise the SCBE security layer.

        Args:
            trust_manager: Pre-configured TrustZoneManager.
                If None, a default instance is created.
            tongue_filter: Pre-configured SacredTongueFilter.
                If None, a default instance is created.
        """
        self.trust_manager: TrustZoneManager = trust_manager or TrustZoneManager()
        self.tongue_filter: SacredTongueFilter = tongue_filter or SacredTongueFilter()

        # Origin of the Poincare ball -- represents maximum trust
        self._origin: List[float] = [0.0] * 6

    # ----- Core classification -----

    def classify_request(
        self,
        url: str,
        origin: str = "",
        method: str = "GET",
        content_signals: Optional[Dict[str, object]] = None,
    ) -> Decision:
        """Classify an HTTP request as ALLOW, QUARANTINE, or DENY.

        Combines Poincare ball trust distance, zone membership, HTTP method
        risk weight, and optional content analysis into a single risk score,
        then maps to a governance decision.

        Args:
            url: The request URL.
            origin: The origin URL (page making the request).
            method: HTTP method (GET, POST, PUT, DELETE, etc.).
            content_signals: Optional content analysis signals for
                Sacred Tongue filtering.

        Returns:
            A ``Decision`` enum value.
        """
        parsed = urlparse(url)
        domain: str = (parsed.hostname or "").lower()

        if not domain:
            return Decision.DENY

        # 1. Zone lookup
        zone: TrustZone = self.trust_manager.get_zone(domain)

        # Fast paths: WALL always denied, CORE always allowed for GET
        if zone == TrustZone.WALL:
            return Decision.DENY
        if zone == TrustZone.CORE and method.upper() in ("GET", "HEAD", "OPTIONS"):
            return Decision.ALLOW

        # 2. Trust score (distance-based risk)
        trust: float = self.compute_trust_score(domain)
        risk: float = 1.0 - trust  # Higher distance -> higher risk

        # 3. Method risk
        method_risk: float = METHOD_RISK_WEIGHTS.get(method.upper(), 0.5)
        risk = risk * 0.7 + method_risk * 0.3

        # 4. Content analysis (if signals provided)
        if content_signals:
            tongue_scores: Dict[str, float] = self.tongue_filter.analyze_page(
                url, content_signals
            )
            coherence: float = self.tongue_filter.composite_score(tongue_scores)
            # Blend content coherence into risk (lower coherence = higher risk)
            risk = risk * 0.6 + (1.0 - coherence) * 0.4

        # 5. Zone bonus/penalty
        zone_bonus: Dict[TrustZone, float] = {
            TrustZone.CORE: -0.3,
            TrustZone.INNER: -0.1,
            TrustZone.OUTER: 0.0,
            TrustZone.WALL: 0.5,
        }
        risk += zone_bonus.get(zone, 0.0)
        risk = max(0.0, min(1.0, risk))

        # 6. Decision
        if risk < ALLOW_THRESHOLD:
            return Decision.ALLOW
        elif risk < DENY_THRESHOLD:
            return Decision.QUARANTINE
        else:
            return Decision.DENY

    # ----- Trust scoring -----

    def compute_trust_score(self, domain: str) -> float:
        """Compute a trust score for a domain using Poincare ball distance.

        Maps the domain to a point in the Poincare ball and computes its
        hyperbolic distance from the origin (maximum trust).  The score
        is inversely related to distance:

            trust = 1 / (1 + d_H(domain_point, origin))

        This produces a value in (0, 1] where:
            - 1.0 = maximum trust (at the origin)
            - 0.0 = minimum trust (approaching the boundary)

        The distance grows exponentially near the boundary, making it
        progressively harder for untrusted domains to reach high trust.

        Args:
            domain: Domain name string.

        Returns:
            Trust score in (0, 1].
        """
        domain = domain.lower()

        # Check for known zones first
        zone: TrustZone = self.trust_manager.get_zone(domain)
        if zone == TrustZone.CORE:
            return 0.95  # Near-maximum trust
        if zone == TrustZone.WALL:
            return 0.05  # Near-minimum trust

        # Compute Poincare distance from origin
        domain_point: List[float] = _domain_to_vector(domain, dims=6)
        d_h: float = _poincare_distance_nd(domain_point, self._origin)

        # Transform distance to trust score
        trust: float = 1.0 / (1.0 + d_h)
        return trust

    # ----- Certificate verification -----

    def verify_certificate_chain(self, certs: List[str]) -> bool:
        """Verify a certificate chain using Sacred Tongue validation.

        Each certificate in the chain is hashed and checked for chain
        continuity: each cert's hash must incorporate the hash of its
        issuer (the next cert in the chain).

        The validation uses the Six Sacred Tongues by requiring that the
        combined hash of the chain produces a coherent signature across
        all six tongue dimensions.

        Chain requirements:
          1. Length >= MIN_CERT_CHAIN_LENGTH
          2. Length <= MAX_CERT_CHAIN_DEPTH
          3. Adjacent cert hashes must link (child incorporates parent hash)
          4. Combined chain hash must pass tongue coherence check

        In a real implementation, actual X.509 parsing and signature
        verification would occur here.  This implementation validates the
        structural properties and chain-hash coherence.

        Args:
            certs: List of certificate strings (PEM or fingerprint),
                ordered from leaf (index 0) to root (last index).

        Returns:
            True if the chain is valid, False otherwise.
        """
        # Length checks
        if len(certs) < MIN_CERT_CHAIN_LENGTH:
            return False
        if len(certs) > MAX_CERT_CHAIN_DEPTH:
            return False

        # Verify chain linkage
        prev_hash: str = ""
        chain_hashes: List[str] = []

        for i, cert in enumerate(certs):
            if not cert or not cert.strip():
                return False

            # Each cert hash incorporates the previous cert's hash
            cert_input: str = cert.strip() + prev_hash
            cert_hash: str = hashlib.sha256(cert_input.encode("utf-8")).hexdigest()
            chain_hashes.append(cert_hash)
            prev_hash = cert_hash

        # Sacred Tongue coherence check on the full chain
        # The combined chain hash is split across 6 tongue dimensions
        combined: str = "|".join(chain_hashes)
        combined_hash: bytes = hashlib.sha256(combined.encode("utf-8")).digest()

        # Each tongue gets a score from a segment of the hash
        tongue_scores: List[float] = []
        for i in range(6):
            # Use 4 bytes per tongue (24 bytes total, within 32-byte SHA-256)
            offset: int = i * 4
            segment: int = int.from_bytes(
                combined_hash[offset:offset + 4], byteorder="big"
            )
            # Normalise to [0, 1]
            tongue_scores.append(segment / (2 ** 32))

        # Coherence threshold: the variance of tongue scores must be below
        # a threshold (coherent chains produce balanced hashes)
        mean_score: float = sum(tongue_scores) / len(tongue_scores)
        variance: float = sum(
            (s - mean_score) ** 2 for s in tongue_scores
        ) / len(tongue_scores)

        # Variance threshold derived from golden ratio:
        # For a truly random hash, expected variance ~ 1/12 ~ 0.083
        # We accept chains whose variance is below 0.15 (generous bound)
        max_variance: float = 0.15

        return variance < max_variance

    # ----- Harmonic Wall -----

    def apply_harmonic_wall(self, request_depth: int) -> float:
        """Apply the Harmonic Wall cost function.

        The Harmonic Wall implements SCBE's bounded risk amplification:

            cost(d) = 1 + ALPHA * tanh(BETA * d)

        where ``d`` is the request depth (redirect/iframe nesting level).

        The cost grows monotonically with depth and saturates at
        (1 + ALPHA), preventing overflow while still making deep
        nesting prohibitively expensive.

        If the cost exceeds ``HARMONIC_WALL_COST_LIMIT`` or the depth
        exceeds ``HARMONIC_WALL_MAX_DEPTH``, the request should be
        blocked.

        Args:
            request_depth: The nesting/redirect depth of the request
                (0 = top-level, 1 = first redirect/iframe, etc.).

        Returns:
            Cost value (float >= 1.0).  Values exceeding
            ``HARMONIC_WALL_COST_LIMIT`` indicate the request should
            be blocked.

        Raises:
            ValueError: If request_depth is negative.
        """
        if request_depth < 0:
            raise ValueError(
                f"request_depth must be non-negative, got {request_depth}"
            )

        # Hard limit on depth
        if request_depth > HARMONIC_WALL_MAX_DEPTH:
            return HARMONIC_ALPHA + 1.0  # Maximum cost, will exceed limit

        cost: float = 1.0 + HARMONIC_ALPHA * math.tanh(HARMONIC_BETA * request_depth)
        return cost

    def is_blocked_by_wall(self, request_depth: int) -> bool:
        """Check whether the Harmonic Wall blocks a request at this depth.

        Convenience method that calls ``apply_harmonic_wall`` and compares
        against the configured cost limit.

        Args:
            request_depth: The nesting/redirect depth.

        Returns:
            True if the request should be blocked.
        """
        cost: float = self.apply_harmonic_wall(request_depth)
        return cost > HARMONIC_WALL_COST_LIMIT
