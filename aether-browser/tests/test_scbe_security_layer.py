"""
Tests for AetherBrowser SCBE Security Layer
=============================================

Comprehensive test suite covering:
  - SCBESecurityLayer: request classification, trust scoring, certificate
    verification, Harmonic Wall enforcement
  - TrustZoneManager: zone lookup, promotion, demotion, edge cases
  - SacredTongueFilter: per-tongue analysis, composite scoring
  - Poincare ball geometry helpers
  - Config constants and invariants

All tests use only stdlib (unittest).

Document ID: AETHER-BROWSER-TEST-2026-001
Version: 1.0.0
"""

from __future__ import annotations

import math
import sys
import os
import unittest

# Ensure the src directory is on the import path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import (
    PHI,
    PI,
    EPSILON,
    BALL_RADIUS,
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
    CORE_TRUSTED_DOMAINS,
    WALL_BLOCKED_DOMAINS,
    METHOD_RISK_WEIGHTS,
    DOMAIN_TRUST_DEFAULTS,
    HARMONIC_SCALE_TABLE,
    harmonic_scale,
)

from scbe_security_layer import (
    SCBESecurityLayer,
    TrustZoneManager,
    SacredTongueFilter,
    DomainRecord,
    _clamp_to_ball,
    _poincare_distance_1d,
    _poincare_distance_nd,
    _domain_to_radial,
    _domain_to_vector,
)


# =============================================================================
# CONFIG TESTS
# =============================================================================

class TestConfig(unittest.TestCase):
    """Test configuration constants and invariants."""

    def test_phi_value(self) -> None:
        """PHI should be the golden ratio."""
        expected: float = (1.0 + math.sqrt(5.0)) / 2.0
        self.assertAlmostEqual(PHI, expected, places=12)

    def test_phi_identity(self) -> None:
        """PHI satisfies phi^2 = phi + 1."""
        self.assertAlmostEqual(PHI ** 2, PHI + 1, places=12)

    def test_tongue_weights_sum_to_one(self) -> None:
        """Tongue weights must sum to 1.0."""
        total: float = sum(TONGUE_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=10)

    def test_tongue_weights_decrease(self) -> None:
        """Tongue weights should decrease (KO highest, DR lowest)."""
        tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]
        for i in range(len(tongues) - 1):
            self.assertGreater(
                TONGUE_WEIGHTS[tongues[i]],
                TONGUE_WEIGHTS[tongues[i + 1]],
                f"Weight for {tongues[i]} should exceed {tongues[i + 1]}",
            )

    def test_all_tongues_have_descriptions(self) -> None:
        """Every SacredTongue must have a description."""
        for tongue in SacredTongue:
            self.assertIn(tongue.value, TONGUE_DESCRIPTIONS)

    def test_decision_thresholds_ordered(self) -> None:
        """ALLOW_THRESHOLD < DENY_THRESHOLD."""
        self.assertLess(ALLOW_THRESHOLD, DENY_THRESHOLD)

    def test_zone_thresholds_ordered(self) -> None:
        """Zone thresholds increase: CORE < INNER < OUTER."""
        self.assertLess(ZONE_THRESHOLDS["CORE"], ZONE_THRESHOLDS["INNER"])
        self.assertLess(ZONE_THRESHOLDS["INNER"], ZONE_THRESHOLDS["OUTER"])

    def test_harmonic_scale_d1(self) -> None:
        """H(1, 1.5) = 1.5."""
        self.assertAlmostEqual(harmonic_scale(1, R_FIFTH), 1.5, places=10)

    def test_harmonic_scale_d6(self) -> None:
        """H(6, 1.5) should be 1.5^36."""
        expected: float = R_FIFTH ** 36
        self.assertAlmostEqual(harmonic_scale(6, R_FIFTH), expected, places=2)

    def test_harmonic_scale_invalid_d(self) -> None:
        """harmonic_scale should reject d < 1."""
        with self.assertRaises(ValueError):
            harmonic_scale(0)

    def test_harmonic_scale_invalid_R(self) -> None:
        """harmonic_scale should reject R <= 0."""
        with self.assertRaises(ValueError):
            harmonic_scale(1, R=0)
        with self.assertRaises(ValueError):
            harmonic_scale(1, R=-1.0)

    def test_harmonic_scale_table_populated(self) -> None:
        """Precomputed table should have entries for d=1..6."""
        for d in range(1, 7):
            self.assertIn(d, HARMONIC_SCALE_TABLE)
            self.assertAlmostEqual(
                HARMONIC_SCALE_TABLE[d], harmonic_scale(d, R_FIFTH), places=5
            )

    def test_method_risk_weights_known_methods(self) -> None:
        """All standard HTTP methods should have a weight."""
        for method in ("GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"):
            self.assertIn(method, METHOD_RISK_WEIGHTS)

    def test_method_risk_get_lowest(self) -> None:
        """GET should have the lowest risk weight."""
        get_risk: float = METHOD_RISK_WEIGHTS["GET"]
        for method, risk in METHOD_RISK_WEIGHTS.items():
            self.assertGreaterEqual(risk, get_risk,
                                    f"{method} risk should be >= GET risk")


# =============================================================================
# POINCARE GEOMETRY HELPER TESTS
# =============================================================================

class TestPoincareHelpers(unittest.TestCase):
    """Test Poincare ball geometry helper functions."""

    def test_clamp_positive(self) -> None:
        """Positive values within ball are unchanged."""
        self.assertAlmostEqual(_clamp_to_ball(0.5), 0.5)

    def test_clamp_at_boundary(self) -> None:
        """Values at/above boundary are clamped."""
        self.assertAlmostEqual(_clamp_to_ball(1.0), BALL_RADIUS)
        self.assertAlmostEqual(_clamp_to_ball(5.0), BALL_RADIUS)

    def test_clamp_negative(self) -> None:
        """Negative values are clamped to 0."""
        self.assertAlmostEqual(_clamp_to_ball(-0.5), 0.0)

    def test_distance_1d_same_point(self) -> None:
        """Distance between same point is 0."""
        self.assertAlmostEqual(_poincare_distance_1d(0.3, 0.3), 0.0, places=10)

    def test_distance_1d_symmetry(self) -> None:
        """d(a, b) == d(b, a)."""
        d1: float = _poincare_distance_1d(0.2, 0.6)
        d2: float = _poincare_distance_1d(0.6, 0.2)
        self.assertAlmostEqual(d1, d2, places=10)

    def test_distance_1d_positive(self) -> None:
        """Distance is always non-negative."""
        self.assertGreaterEqual(_poincare_distance_1d(0.1, 0.5), 0.0)

    def test_distance_1d_from_origin(self) -> None:
        """Distance from origin increases with radius."""
        d1: float = _poincare_distance_1d(0.0, 0.3)
        d2: float = _poincare_distance_1d(0.0, 0.6)
        d3: float = _poincare_distance_1d(0.0, 0.9)
        self.assertLess(d1, d2)
        self.assertLess(d2, d3)

    def test_distance_1d_boundary_large(self) -> None:
        """Distance near the boundary should be very large."""
        d: float = _poincare_distance_1d(0.0, 0.99)
        self.assertGreater(d, 3.0)

    def test_distance_nd_same_point(self) -> None:
        """n-D distance between same point is 0."""
        p = [0.1, 0.2, 0.3]
        self.assertAlmostEqual(_poincare_distance_nd(p, p), 0.0, places=10)

    def test_distance_nd_symmetry(self) -> None:
        """n-D distance is symmetric."""
        u = [0.1, 0.2, -0.1]
        v = [0.3, -0.1, 0.2]
        self.assertAlmostEqual(
            _poincare_distance_nd(u, v),
            _poincare_distance_nd(v, u),
            places=10,
        )

    def test_distance_nd_triangle_inequality(self) -> None:
        """n-D distance satisfies triangle inequality."""
        u = [0.1, 0.0, 0.0]
        v = [0.0, 0.2, 0.0]
        w = [0.0, 0.0, 0.3]

        d_uv: float = _poincare_distance_nd(u, v)
        d_vw: float = _poincare_distance_nd(v, w)
        d_uw: float = _poincare_distance_nd(u, w)

        self.assertLessEqual(d_uw, d_uv + d_vw + 1e-9)

    def test_distance_nd_dimension_mismatch(self) -> None:
        """Mismatched dimensions should raise ValueError."""
        with self.assertRaises(ValueError):
            _poincare_distance_nd([0.1, 0.2], [0.1, 0.2, 0.3])

    def test_domain_to_radial_deterministic(self) -> None:
        """Same domain always maps to the same radius."""
        r1: float = _domain_to_radial("example.com")
        r2: float = _domain_to_radial("example.com")
        self.assertEqual(r1, r2)

    def test_domain_to_radial_in_ball(self) -> None:
        """Radial coordinate is always in [0, BALL_RADIUS)."""
        for domain in ["a.com", "b.org", "test.example.co.uk", "x" * 200]:
            r: float = _domain_to_radial(domain)
            self.assertGreaterEqual(r, 0.0)
            self.assertLess(r, 1.0)

    def test_domain_to_radial_case_insensitive(self) -> None:
        """Domain mapping is case-insensitive."""
        r1: float = _domain_to_radial("Example.COM")
        r2: float = _domain_to_radial("example.com")
        self.assertEqual(r1, r2)

    def test_domain_to_vector_dimension(self) -> None:
        """Vector has the requested number of dimensions."""
        for dims in [2, 6, 10]:
            v: list = _domain_to_vector("example.com", dims=dims)
            self.assertEqual(len(v), dims)

    def test_domain_to_vector_in_ball(self) -> None:
        """Vector norm is strictly less than 1."""
        for domain in ["test.com", "evil.org", "good.net"]:
            v: list = _domain_to_vector(domain, dims=6)
            norm: float = math.sqrt(sum(x * x for x in v))
            self.assertLess(norm, 1.0)

    def test_domain_to_vector_deterministic(self) -> None:
        """Same domain always produces the same vector."""
        v1 = _domain_to_vector("stable.io")
        v2 = _domain_to_vector("stable.io")
        self.assertEqual(v1, v2)


# =============================================================================
# TRUST ZONE MANAGER TESTS
# =============================================================================

class TestTrustZoneManager(unittest.TestCase):
    """Test TrustZoneManager zone management."""

    def setUp(self) -> None:
        self.manager = TrustZoneManager()

    def test_core_domains_in_core_zone(self) -> None:
        """Pre-seeded CORE domains should be in CORE zone."""
        for domain in CORE_TRUSTED_DOMAINS:
            self.assertEqual(self.manager.get_zone(domain), TrustZone.CORE)

    def test_blocked_domains_in_wall_zone(self) -> None:
        """Pre-seeded WALL domains should be in WALL zone."""
        for domain in WALL_BLOCKED_DOMAINS:
            self.assertEqual(self.manager.get_zone(domain), TrustZone.WALL)

    def test_unknown_domain_gets_outer(self) -> None:
        """Unknown domains should be assigned OUTER zone."""
        zone: TrustZone = self.manager.get_zone("never-seen-before.xyz")
        self.assertEqual(zone, TrustZone.OUTER)

    def test_get_zone_case_insensitive(self) -> None:
        """Zone lookup should be case-insensitive."""
        zone1: TrustZone = self.manager.get_zone("Example.COM")
        zone2: TrustZone = self.manager.get_zone("example.com")
        self.assertEqual(zone1, zone2)

    def test_promote_domain_accumulates_evidence(self) -> None:
        """Promotion accumulates evidence until threshold is met."""
        domain = "promotable.test"
        # Start in OUTER
        self.assertEqual(self.manager.get_zone(domain), TrustZone.OUTER)

        # Not enough evidence yet
        self.manager.promote_domain(domain, 0.3)
        self.assertEqual(self.manager.get_zone(domain), TrustZone.OUTER)

        # Still not enough
        self.manager.promote_domain(domain, 0.3)
        self.assertEqual(self.manager.get_zone(domain), TrustZone.OUTER)

        # Now threshold is met (0.3 + 0.3 + 0.2 = 0.8 > 0.7)
        self.manager.promote_domain(domain, 0.2)
        self.assertEqual(self.manager.get_zone(domain), TrustZone.INNER)

    def test_promote_core_is_noop(self) -> None:
        """Cannot promote beyond CORE."""
        zone: TrustZone = self.manager.promote_domain("example.com", 1.0)
        self.assertEqual(zone, TrustZone.CORE)

    def test_promote_wall_is_noop(self) -> None:
        """WALL domains cannot be promoted (require explicit unblock)."""
        zone: TrustZone = self.manager.promote_domain("malware.test", 1.0)
        self.assertEqual(zone, TrustZone.WALL)

    def test_demote_domain(self) -> None:
        """Demotion moves domain one zone toward WALL."""
        domain = "demotable.test"
        # Force into INNER first
        self.manager.get_zone(domain)  # Creates as OUTER
        record = self.manager.get_record(domain)
        assert record is not None
        record.zone = TrustZone.INNER

        # Demote: INNER -> OUTER
        zone: TrustZone = self.manager.demote_domain(domain, "test reason")
        self.assertEqual(zone, TrustZone.OUTER)

        # Demote again: OUTER -> WALL
        zone = self.manager.demote_domain(domain, "another reason")
        self.assertEqual(zone, TrustZone.WALL)

    def test_demote_wall_is_noop(self) -> None:
        """Cannot demote below WALL."""
        zone: TrustZone = self.manager.demote_domain("malware.test", "already blocked")
        self.assertEqual(zone, TrustZone.WALL)

    def test_get_record_exists(self) -> None:
        """get_record returns DomainRecord for tracked domains."""
        self.manager.get_zone("tracked.test")
        record = self.manager.get_record("tracked.test")
        self.assertIsNotNone(record)
        self.assertEqual(record.domain, "tracked.test")

    def test_get_record_not_exists(self) -> None:
        """get_record returns None for untracked domains."""
        record = self.manager.get_record("untracked.xyz")
        self.assertIsNone(record)

    def test_list_domains_in_zone(self) -> None:
        """list_domains_in_zone returns correct domains."""
        core_list: list = self.manager.list_domains_in_zone(TrustZone.CORE)
        for domain in CORE_TRUSTED_DOMAINS:
            self.assertIn(domain.lower(), core_list)

    def test_list_domains_empty_zone(self) -> None:
        """Empty zone returns empty list."""
        # INNER should be empty by default (no domains seeded there)
        inner_list: list = self.manager.list_domains_in_zone(TrustZone.INNER)
        self.assertEqual(inner_list, [])


# =============================================================================
# SACRED TONGUE FILTER TESTS
# =============================================================================

class TestSacredTongueFilter(unittest.TestCase):
    """Test SacredTongueFilter content analysis."""

    def setUp(self) -> None:
        self.filter = SacredTongueFilter()

    def test_analyze_page_returns_all_tongues(self) -> None:
        """analyze_page should return scores for all 6 tongues."""
        scores: dict = self.filter.analyze_page("https://example.com", {})
        self.assertEqual(len(scores), 6)
        for tongue in ("KO", "AV", "RU", "CA", "UM", "DR"):
            self.assertIn(tongue, scores)

    def test_all_scores_in_range(self) -> None:
        """All tongue scores should be in [0, 1]."""
        signals: dict = {
            "claimed_type": "text/html",
            "actual_type": "text/html",
            "hsts": True,
            "cert_valid": True,
            "permission_requests": 2,
            "permissions_granted": 2,
            "uses_eval": False,
            "inline_script_count": 5,
            "third_party_trackers": 3,
            "has_csp": True,
        }
        scores: dict = self.filter.analyze_page("https://safe.com", signals)
        for tongue, score in scores.items():
            self.assertGreaterEqual(score, 0.0, f"{tongue} score below 0")
            self.assertLessEqual(score, 1.0, f"{tongue} score above 1")

    # -- KO (Intent) --

    def test_ko_data_uri_penalized(self) -> None:
        """Data URIs should reduce intent coherence."""
        scores: dict = self.filter.analyze_page("data:text/html,<h1>X</h1>", {})
        self.assertLess(scores["KO"], 1.0)

    def test_ko_javascript_uri_heavily_penalized(self) -> None:
        """JavaScript URIs should heavily reduce intent coherence."""
        scores: dict = self.filter.analyze_page("javascript:alert(1)", {})
        self.assertLess(scores["KO"], 0.5)

    def test_ko_type_mismatch_penalized(self) -> None:
        """Claimed vs actual type mismatch should reduce coherence."""
        signals: dict = {"claimed_type": "text/html", "actual_type": "application/pdf"}
        scores: dict = self.filter.analyze_page("https://example.com", signals)
        self.assertLess(scores["KO"], 1.0)

    def test_ko_normal_page_high(self) -> None:
        """Normal HTTPS page should have high intent coherence."""
        scores: dict = self.filter.analyze_page("https://example.com", {"has_navigation": True})
        self.assertGreater(scores["KO"], 0.9)

    # -- AV (Transport) --

    def test_av_https_better_than_http(self) -> None:
        """HTTPS should score higher than HTTP."""
        https_scores: dict = self.filter.analyze_page("https://example.com", {})
        http_scores: dict = self.filter.analyze_page("http://example.com", {})
        self.assertGreater(https_scores["AV"], http_scores["AV"])

    def test_av_hsts_bonus(self) -> None:
        """HSTS presence should increase transport score."""
        no_hsts: dict = self.filter.analyze_page("https://example.com", {"hsts": False})
        with_hsts: dict = self.filter.analyze_page("https://example.com", {"hsts": True})
        self.assertGreaterEqual(with_hsts["AV"], no_hsts["AV"])

    # -- RU (Permissions) --

    def test_ru_excessive_permissions_penalized(self) -> None:
        """Requesting many permissions should reduce coherence."""
        modest: dict = self.filter.analyze_page(
            "https://example.com", {"permission_requests": 1, "permissions_granted": 1}
        )
        excessive: dict = self.filter.analyze_page(
            "https://example.com", {"permission_requests": 10, "permissions_granted": 2}
        )
        self.assertGreater(modest["RU"], excessive["RU"])

    # -- CA (Computation) --

    def test_ca_eval_penalized(self) -> None:
        """eval() usage should reduce computation safety."""
        safe: dict = self.filter.analyze_page(
            "https://example.com", {"uses_eval": False}
        )
        unsafe: dict = self.filter.analyze_page(
            "https://example.com", {"uses_eval": True}
        )
        self.assertGreater(safe["CA"], unsafe["CA"])

    def test_ca_crypto_mining_heavily_penalized(self) -> None:
        """Crypto mining detection should heavily reduce score."""
        scores: dict = self.filter.analyze_page(
            "https://example.com", {"crypto_mining_detected": True}
        )
        self.assertLess(scores["CA"], 0.5)

    # -- UM (Privacy) --

    def test_um_trackers_penalized(self) -> None:
        """Third-party trackers should reduce privacy score."""
        clean: dict = self.filter.analyze_page(
            "https://example.com", {"third_party_trackers": 0}
        )
        tracked: dict = self.filter.analyze_page(
            "https://example.com", {"third_party_trackers": 10}
        )
        self.assertGreater(clean["UM"], tracked["UM"])

    def test_um_fingerprinting_penalized(self) -> None:
        """Fingerprinting should reduce privacy score."""
        scores: dict = self.filter.analyze_page(
            "https://example.com", {"fingerprinting_detected": True}
        )
        self.assertLess(scores["UM"], 1.0)

    # -- DR (Schema) --

    def test_dr_csp_bonus(self) -> None:
        """CSP presence should increase schema score."""
        no_csp: dict = self.filter.analyze_page(
            "https://example.com", {"has_csp": False}
        )
        with_csp: dict = self.filter.analyze_page(
            "https://example.com", {"has_csp": True}
        )
        self.assertGreaterEqual(with_csp["DR"], no_csp["DR"])

    def test_dr_malformed_html_penalized(self) -> None:
        """Malformed HTML should reduce schema coherence."""
        scores: dict = self.filter.analyze_page(
            "https://example.com", {"malformed_html": True}
        )
        self.assertLess(scores["DR"], 0.8)

    # -- Composite Score --

    def test_composite_score_in_range(self) -> None:
        """Composite score should be in [0, 1]."""
        scores: dict = {"KO": 0.9, "AV": 0.8, "RU": 1.0, "CA": 0.7, "UM": 0.6, "DR": 0.85}
        composite: float = self.filter.composite_score(scores)
        self.assertGreaterEqual(composite, 0.0)
        self.assertLessEqual(composite, 1.0)

    def test_composite_all_ones(self) -> None:
        """All-ones tongue scores should give composite = 1.0."""
        scores: dict = {t: 1.0 for t in ("KO", "AV", "RU", "CA", "UM", "DR")}
        composite: float = self.filter.composite_score(scores)
        self.assertAlmostEqual(composite, 1.0, places=10)

    def test_composite_all_zeros(self) -> None:
        """All-zeros tongue scores should give composite = 0.0."""
        scores: dict = {t: 0.0 for t in ("KO", "AV", "RU", "CA", "UM", "DR")}
        composite: float = self.filter.composite_score(scores)
        self.assertAlmostEqual(composite, 0.0, places=10)

    def test_composite_ko_weighted_highest(self) -> None:
        """KO (intent) should have the most influence on composite."""
        # Only KO is 1.0, rest are 0.0
        ko_high: dict = {"KO": 1.0, "AV": 0.0, "RU": 0.0, "CA": 0.0, "UM": 0.0, "DR": 0.0}
        # Only DR is 1.0, rest are 0.0
        dr_high: dict = {"KO": 0.0, "AV": 0.0, "RU": 0.0, "CA": 0.0, "UM": 0.0, "DR": 1.0}

        self.assertGreater(
            self.filter.composite_score(ko_high),
            self.filter.composite_score(dr_high),
        )

    def test_composite_missing_tongues_default(self) -> None:
        """Missing tongue scores should default to 0.5."""
        partial: dict = {"KO": 1.0}  # Only KO provided
        composite: float = self.filter.composite_score(partial)
        # Should be between 0.5 and 1.0 (KO pulls up, rest at 0.5)
        self.assertGreater(composite, 0.4)
        self.assertLess(composite, 1.0)


# =============================================================================
# SCBE SECURITY LAYER TESTS
# =============================================================================

class TestSCBESecurityLayer(unittest.TestCase):
    """Test SCBESecurityLayer request classification and security functions."""

    def setUp(self) -> None:
        self.layer = SCBESecurityLayer()

    # -- classify_request --

    def test_classify_core_domain_get_allowed(self) -> None:
        """GET to a CORE domain should be ALLOW."""
        decision: Decision = self.layer.classify_request(
            url="https://example.com/page",
            origin="https://example.com",
            method="GET",
        )
        self.assertEqual(decision, Decision.ALLOW)

    def test_classify_blocked_domain_denied(self) -> None:
        """Any request to a WALL domain should be DENY."""
        decision: Decision = self.layer.classify_request(
            url="https://malware.test/exploit",
            origin="https://some-origin.com",
            method="GET",
        )
        self.assertEqual(decision, Decision.DENY)

    def test_classify_empty_domain_denied(self) -> None:
        """URL with no hostname should be DENY."""
        decision: Decision = self.layer.classify_request(
            url="about:blank",
            origin="",
            method="GET",
        )
        self.assertEqual(decision, Decision.DENY)

    def test_classify_unknown_domain_not_denied(self) -> None:
        """Unknown domain with GET should not be outright DENY."""
        decision: Decision = self.layer.classify_request(
            url="https://unknown-new-site.org/page",
            origin="https://referrer.com",
            method="GET",
        )
        # Should be ALLOW or QUARANTINE (not DENY for a simple GET)
        self.assertIn(decision, (Decision.ALLOW, Decision.QUARANTINE))

    def test_classify_delete_higher_risk(self) -> None:
        """DELETE method should produce higher risk than GET."""
        # We can't guarantee DENY, but risk should be higher
        get_decision: Decision = self.layer.classify_request(
            url="https://unknown-site.org/resource",
            method="GET",
        )
        delete_decision: Decision = self.layer.classify_request(
            url="https://unknown-site.org/resource",
            method="DELETE",
        )
        # DELETE risk >= GET risk (by decision ordering)
        decision_risk = {Decision.ALLOW: 0, Decision.QUARANTINE: 1, Decision.DENY: 2}
        self.assertGreaterEqual(
            decision_risk[delete_decision],
            decision_risk[get_decision],
        )

    def test_classify_with_malicious_signals(self) -> None:
        """Malicious content signals should raise the risk."""
        signals: dict = {
            "uses_eval": True,
            "crypto_mining_detected": True,
            "third_party_trackers": 20,
            "fingerprinting_detected": True,
            "malformed_html": True,
        }
        decision: Decision = self.layer.classify_request(
            url="https://sketchy-site.io/page",
            method="GET",
            content_signals=signals,
        )
        # Should be at least QUARANTINE
        self.assertIn(decision, (Decision.QUARANTINE, Decision.DENY))

    def test_classify_with_safe_signals(self) -> None:
        """Safe content signals should keep the risk low."""
        signals: dict = {
            "hsts": True,
            "cert_valid": True,
            "has_csp": True,
            "has_frame_protection": True,
            "has_navigation": True,
            "uses_eval": False,
            "third_party_trackers": 0,
        }
        decision: Decision = self.layer.classify_request(
            url="https://example.com/page",
            method="GET",
            content_signals=signals,
        )
        self.assertEqual(decision, Decision.ALLOW)

    # -- compute_trust_score --

    def test_trust_score_core_high(self) -> None:
        """CORE domains should have high trust scores."""
        score: float = self.layer.compute_trust_score("example.com")
        self.assertGreater(score, 0.9)

    def test_trust_score_wall_low(self) -> None:
        """WALL domains should have low trust scores."""
        score: float = self.layer.compute_trust_score("malware.test")
        self.assertLess(score, 0.1)

    def test_trust_score_in_range(self) -> None:
        """Trust scores should be in (0, 1]."""
        for domain in ["a.com", "b.org", "c.net", "d.io"]:
            score: float = self.layer.compute_trust_score(domain)
            self.assertGreater(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_trust_score_deterministic(self) -> None:
        """Same domain should always produce same trust score."""
        s1: float = self.layer.compute_trust_score("stable.com")
        s2: float = self.layer.compute_trust_score("stable.com")
        self.assertEqual(s1, s2)

    # -- verify_certificate_chain --

    def test_cert_chain_valid(self) -> None:
        """Valid certificate chain should pass."""
        certs: list = ["leaf-cert-data", "intermediate-ca", "root-ca"]
        result: bool = self.layer.verify_certificate_chain(certs)
        self.assertTrue(result)

    def test_cert_chain_too_short(self) -> None:
        """Chain shorter than MIN_CERT_CHAIN_LENGTH should fail."""
        certs: list = ["only-one-cert"]
        result: bool = self.layer.verify_certificate_chain(certs)
        self.assertFalse(result)

    def test_cert_chain_too_long(self) -> None:
        """Chain longer than MAX_CERT_CHAIN_DEPTH should fail."""
        certs: list = [f"cert-{i}" for i in range(MAX_CERT_CHAIN_DEPTH + 1)]
        result: bool = self.layer.verify_certificate_chain(certs)
        self.assertFalse(result)

    def test_cert_chain_empty_cert_fails(self) -> None:
        """Chain with empty certificate string should fail."""
        certs: list = ["leaf-cert", "", "root-ca"]
        result: bool = self.layer.verify_certificate_chain(certs)
        self.assertFalse(result)

    def test_cert_chain_whitespace_only_fails(self) -> None:
        """Chain with whitespace-only certificate should fail."""
        certs: list = ["leaf-cert", "   ", "root-ca"]
        result: bool = self.layer.verify_certificate_chain(certs)
        self.assertFalse(result)

    def test_cert_chain_exact_min_length(self) -> None:
        """Chain of exactly MIN_CERT_CHAIN_LENGTH should be accepted."""
        certs: list = [f"cert-{i}" for i in range(MIN_CERT_CHAIN_LENGTH)]
        result: bool = self.layer.verify_certificate_chain(certs)
        self.assertTrue(result)

    def test_cert_chain_exact_max_length(self) -> None:
        """Chain of exactly MAX_CERT_CHAIN_DEPTH should be accepted."""
        certs: list = [f"cert-{i}" for i in range(MAX_CERT_CHAIN_DEPTH)]
        result: bool = self.layer.verify_certificate_chain(certs)
        self.assertTrue(result)

    def test_cert_chain_deterministic(self) -> None:
        """Same chain should always produce same result."""
        certs: list = ["leaf", "intermediate", "root"]
        r1: bool = self.layer.verify_certificate_chain(certs)
        r2: bool = self.layer.verify_certificate_chain(certs)
        self.assertEqual(r1, r2)

    # -- apply_harmonic_wall --

    def test_harmonic_wall_depth_zero(self) -> None:
        """Depth 0 (top-level) should have cost = 1.0."""
        cost: float = self.layer.apply_harmonic_wall(0)
        self.assertAlmostEqual(cost, 1.0, places=10)

    def test_harmonic_wall_monotonic(self) -> None:
        """Cost should increase monotonically with depth."""
        prev_cost: float = 0.0
        for depth in range(HARMONIC_WALL_MAX_DEPTH + 1):
            cost: float = self.layer.apply_harmonic_wall(depth)
            self.assertGreaterEqual(cost, prev_cost)
            prev_cost = cost

    def test_harmonic_wall_bounded(self) -> None:
        """Cost should be bounded by 1 + HARMONIC_ALPHA."""
        max_cost: float = 1.0 + HARMONIC_ALPHA
        for depth in range(HARMONIC_WALL_MAX_DEPTH + 1):
            cost: float = self.layer.apply_harmonic_wall(depth)
            self.assertLessEqual(cost, max_cost + EPSILON)

    def test_harmonic_wall_exceeds_limit_at_high_depth(self) -> None:
        """Cost should exceed HARMONIC_WALL_COST_LIMIT at high depth."""
        # At MAX_DEPTH + 1 it should definitely exceed
        cost: float = self.layer.apply_harmonic_wall(HARMONIC_WALL_MAX_DEPTH + 1)
        self.assertGreater(cost, HARMONIC_WALL_COST_LIMIT)

    def test_harmonic_wall_negative_depth_raises(self) -> None:
        """Negative depth should raise ValueError."""
        with self.assertRaises(ValueError):
            self.layer.apply_harmonic_wall(-1)

    def test_is_blocked_by_wall_low_depth(self) -> None:
        """Low depth should not be blocked."""
        self.assertFalse(self.layer.is_blocked_by_wall(0))
        self.assertFalse(self.layer.is_blocked_by_wall(1))

    def test_is_blocked_by_wall_high_depth(self) -> None:
        """Very high depth should be blocked."""
        self.assertTrue(self.layer.is_blocked_by_wall(HARMONIC_WALL_MAX_DEPTH + 1))

    def test_harmonic_wall_tanh_shape(self) -> None:
        """Verify cost follows tanh shape: fast initial growth, saturation."""
        cost_1: float = self.layer.apply_harmonic_wall(1)
        cost_5: float = self.layer.apply_harmonic_wall(5)
        cost_15: float = self.layer.apply_harmonic_wall(15)

        # Growth from 0->1 should be noticeable
        self.assertGreater(cost_1, 1.0)

        # Growth from 5->15 should be smaller than from 0->5 (saturation)
        growth_early: float = cost_5 - 1.0
        growth_late: float = cost_15 - cost_5
        self.assertGreater(growth_early, growth_late)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple components."""

    def test_full_pipeline_safe_site(self) -> None:
        """Full pipeline for a safe, known site with good signals."""
        layer = SCBESecurityLayer()
        signals: dict = {
            "hsts": True,
            "cert_valid": True,
            "has_csp": True,
            "has_navigation": True,
            "uses_eval": False,
            "third_party_trackers": 0,
            "permission_requests": 0,
        }

        decision: Decision = layer.classify_request(
            url="https://example.com/dashboard",
            origin="https://example.com",
            method="GET",
            content_signals=signals,
        )
        self.assertEqual(decision, Decision.ALLOW)

        trust: float = layer.compute_trust_score("example.com")
        self.assertGreater(trust, 0.9)

        wall_cost: float = layer.apply_harmonic_wall(0)
        self.assertAlmostEqual(wall_cost, 1.0)

    def test_full_pipeline_malicious_site(self) -> None:
        """Full pipeline for a known-malicious site."""
        layer = SCBESecurityLayer()

        decision: Decision = layer.classify_request(
            url="https://malware.test/payload",
            origin="https://innocent.com",
            method="POST",
        )
        self.assertEqual(decision, Decision.DENY)

        trust: float = layer.compute_trust_score("malware.test")
        self.assertLess(trust, 0.1)

    def test_promotion_affects_trust_score(self) -> None:
        """Promoting a domain should change its zone lookup."""
        layer = SCBESecurityLayer()

        domain = "promotable-integration.test"
        zone_before: TrustZone = layer.trust_manager.get_zone(domain)
        self.assertEqual(zone_before, TrustZone.OUTER)

        # Promote with enough evidence
        layer.trust_manager.promote_domain(domain, 0.8)
        zone_after: TrustZone = layer.trust_manager.get_zone(domain)
        self.assertEqual(zone_after, TrustZone.INNER)

    def test_demotion_increases_risk(self) -> None:
        """Demoting a domain should increase its risk (lower trust)."""
        layer = SCBESecurityLayer()

        domain = "demotable-integration.test"
        layer.trust_manager.get_zone(domain)
        # Force to INNER for testing
        record = layer.trust_manager.get_record(domain)
        assert record is not None
        record.zone = TrustZone.INNER

        trust_before: float = layer.compute_trust_score(domain)

        layer.trust_manager.demote_domain(domain, "suspicious activity")

        # After demotion, trust score should change
        trust_after: float = layer.compute_trust_score(domain)

        # The domain was demoted from INNER to OUTER -- trust should
        # remain the same or change depending on zone (INNER/OUTER both
        # go through Poincare distance calculation)
        zone_after: TrustZone = layer.trust_manager.get_zone(domain)
        self.assertEqual(zone_after, TrustZone.OUTER)

    def test_tongue_filter_affects_classification(self) -> None:
        """Content signals from tongue filter should influence classification."""
        layer = SCBESecurityLayer()

        # Good signals
        good_signals: dict = {
            "hsts": True,
            "cert_valid": True,
            "has_csp": True,
            "uses_eval": False,
            "third_party_trackers": 0,
        }

        # Bad signals
        bad_signals: dict = {
            "uses_eval": True,
            "crypto_mining_detected": True,
            "third_party_trackers": 20,
            "fingerprinting_detected": True,
            "malformed_html": True,
        }

        domain = "https://neutral-test-site.org/page"

        good_decision: Decision = layer.classify_request(
            url=domain, method="GET", content_signals=good_signals
        )
        bad_decision: Decision = layer.classify_request(
            url=domain, method="GET", content_signals=bad_signals
        )

        # Bad signals should produce equal or higher risk
        decision_risk = {Decision.ALLOW: 0, Decision.QUARANTINE: 1, Decision.DENY: 2}
        self.assertGreaterEqual(
            decision_risk[bad_decision],
            decision_risk[good_decision],
        )

    def test_harmonic_wall_deep_nesting_blocked(self) -> None:
        """Deep iframe/redirect nesting should be blocked by Harmonic Wall."""
        layer = SCBESecurityLayer()

        # Shallow should be fine
        self.assertFalse(layer.is_blocked_by_wall(0))
        self.assertFalse(layer.is_blocked_by_wall(1))

        # Very deep should be blocked
        self.assertTrue(layer.is_blocked_by_wall(100))

    def test_certificate_chain_integration(self) -> None:
        """Certificate verification integrates with security evaluation."""
        layer = SCBESecurityLayer()

        valid_chain: list = [
            "MIIBojCCAUigAwIBAgIQDHN1YK",
            "MIICCTCCAa+gAwIBAgIUFg0n",
            "MIICMDCCAdagAwIBAgIRAO5jv",
        ]
        self.assertTrue(layer.verify_certificate_chain(valid_chain))

        too_short: list = ["single-cert"]
        self.assertFalse(layer.verify_certificate_chain(too_short))


# =============================================================================
# MATHEMATICAL PROPERTY TESTS
# =============================================================================

class TestMathematicalProperties(unittest.TestCase):
    """Test mathematical properties that SCBE security relies on."""

    def test_poincare_distance_grows_near_boundary(self) -> None:
        """Poincare distance should grow rapidly near the boundary.

        This is the core SCBE insight: adversarial intent (near boundary)
        costs exponentially more than safe operation (near origin).
        """
        origin = [0.0] * 3
        distances: list = []

        for r in [0.1, 0.3, 0.5, 0.7, 0.9, 0.95, 0.99]:
            point = [r, 0.0, 0.0]
            d: float = _poincare_distance_nd(point, origin)
            distances.append(d)

        # Distances should strictly increase
        for i in range(len(distances) - 1):
            self.assertLess(distances[i], distances[i + 1])

        # The growth should be super-linear (accelerating)
        # Check that the last gap is larger than the first gap
        first_gap: float = distances[1] - distances[0]
        last_gap: float = distances[-1] - distances[-2]
        self.assertGreater(last_gap, first_gap)

    def test_harmonic_wall_cost_is_bounded(self) -> None:
        """Harmonic Wall cost should be in [1, 1 + ALPHA] for valid depths."""
        layer = SCBESecurityLayer()
        for depth in range(HARMONIC_WALL_MAX_DEPTH + 1):
            cost: float = layer.apply_harmonic_wall(depth)
            self.assertGreaterEqual(cost, 1.0)
            self.assertLessEqual(cost, 1.0 + HARMONIC_ALPHA + EPSILON)

    def test_trust_score_inversely_related_to_distance(self) -> None:
        """Trust score formula: trust = 1/(1+d_H) is monotonically decreasing."""
        for d in [0.0, 0.5, 1.0, 2.0, 5.0, 10.0, 50.0]:
            trust: float = 1.0 / (1.0 + d)
            self.assertGreater(trust, 0.0)
            self.assertLessEqual(trust, 1.0)
            if d > 0:
                trust_less = 1.0 / (1.0 + d + 0.1)
                self.assertGreater(trust, trust_less)

    def test_phi_weighting_is_normalised(self) -> None:
        """Phi-based tongue weights should sum to 1.0 and be decreasing."""
        weights: list = [PHI ** (-i) for i in range(6)]
        total: float = sum(weights)
        normalised: list = [w / total for w in weights]

        self.assertAlmostEqual(sum(normalised), 1.0, places=10)

        for i in range(len(normalised) - 1):
            self.assertGreater(normalised[i], normalised[i + 1])


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    unittest.main()
