"""
Property-based tests for canonical_state.py

Covers:
  1. CanonicalState construction and validation
  2. compute_ds_squared product metric correctness
  3. Boundary amplification (hyperbolic security property)
  4. Torus periodicity
  5. Triangle inequality on each subspace
  6. audit_state_transition hash chain integrity

Uses Hypothesis for property-based testing.
"""

from __future__ import annotations

import math
import sys
import os
import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from src.harmonic.canonical_state import (
    CanonicalState,
    CanonicalStateError,
    build_canonical_state,
    compute_ds_squared,
    safe_origin,
    StateTransitionAuditor,
    audit_state_transition,
    get_auditor,
    STATE21_DIM,
    SCHEMA_VERSION,
    _hyperbolic_distance_sq,
    _torus_distance_sq,
    _compute_energy_harmonic,
)


# ═══════════════════════════════════════════════════════════════
# Hypothesis strategies
# ═══════════════════════════════════════════════════════════════

@st.composite
def _poincare_point(draw, max_norm: float = 0.95):
    """Generate a 6D point inside the Poincare ball via rejection-free scaling."""
    raw = draw(st.lists(
        st.floats(min_value=-1.0, max_value=1.0),
        min_size=6, max_size=6,
    ))
    norm = math.sqrt(sum(x * x for x in raw))
    if norm < 1e-12:
        return [0.0] * 6
    # Scale to random radius within max_norm
    target_r = draw(st.floats(min_value=0.0, max_value=max_norm))
    return [x * target_r / norm for x in raw]


def _phase_angles():
    """Generate 6 phase angles in [0, 2*pi)."""
    return st.lists(
        st.floats(min_value=0.0, max_value=2 * math.pi - 0.01),
        min_size=6, max_size=6,
    )


def _unit_float():
    return st.floats(min_value=0.0, max_value=1.0)


def _canonical_state_strategy():
    """Generate a valid CanonicalState."""
    return st.builds(
        build_canonical_state,
        u=_poincare_point(),
        theta=_phase_angles(),
        flux_participation=st.floats(min_value=0.0, max_value=10.0),
        coherence_spectral=_unit_float(),
        coherence_spin=_unit_float(),
        coherence_triadic=_unit_float(),
        risk_aggregate=_unit_float(),
        entropy_density=st.floats(min_value=0.0, max_value=10.0),
        stabilization=st.floats(min_value=0.0, max_value=10.0),
    )


# ═══════════════════════════════════════════════════════════════
# 1. Construction and Validation
# ═══════════════════════════════════════════════════════════════

class TestConstruction:

    def test_safe_origin_is_valid(self):
        s = safe_origin()
        assert len(s.vec) == STATE21_DIM
        diag = s.validate()
        assert diag["u_norm"] == 0.0
        assert diag["radial_abs_err"] == 0.0

    def test_wrong_dimension_raises(self):
        with pytest.raises(CanonicalStateError, match="21D"):
            CanonicalState(vec=[0.0] * 20)

    def test_outside_ball_raises(self):
        with pytest.raises(CanonicalStateError):
            build_canonical_state(
                u=[0.6, 0.6, 0.6, 0.0, 0.0, 0.0],  # norm ~1.04
                theta=[0.0] * 6,
            )

    def test_coherence_out_of_range_raises(self):
        with pytest.raises(CanonicalStateError, match="coherence_spectral"):
            build_canonical_state(
                u=[0.0] * 6,
                theta=[0.0] * 6,
                coherence_spectral=1.5,
            ).validate()

    def test_schema_version(self):
        s = safe_origin()
        assert s.schema_version == SCHEMA_VERSION

    @given(_canonical_state_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_all_generated_states_validate(self, state):
        """Every state from the strategy must pass validation."""
        diag = state.validate()
        assert diag["u_norm"] < 1.0
        assert diag["radial_abs_err"] < 1e-10
        assert diag["energy_abs_err"] < 1e-6

    def test_hash_deterministic(self):
        s1 = safe_origin()
        s2 = safe_origin()
        assert s1.hash() == s2.hash()

    def test_hash_changes_with_state(self):
        s1 = safe_origin()
        s2 = build_canonical_state(u=[0.1, 0.0, 0.0, 0.0, 0.0, 0.0], theta=[0.0] * 6)
        assert s1.hash() != s2.hash()

    def test_to_dict_has_all_names(self):
        s = safe_origin()
        d = s.to_dict()
        assert len(d) == STATE21_DIM
        assert "u_ko" in d
        assert "energy_harmonic" in d

    def test_derived_cache_consistency(self):
        """radial_norm slot must match computed u_norm."""
        s = build_canonical_state(
            u=[0.3, 0.2, 0.1, 0.0, 0.0, 0.0],
            theta=[0.0] * 6,
        )
        assert abs(s.radial_norm - s.u_norm()) < 1e-12


# ═══════════════════════════════════════════════════════════════
# 2. compute_ds_squared product metric
# ═══════════════════════════════════════════════════════════════

class TestDsSquared:

    def test_zero_distance_same_state(self):
        s = safe_origin()
        result = compute_ds_squared(s, s)
        assert result["ds_squared"] == pytest.approx(0.0, abs=1e-12)
        assert result["hyp_sq"] == pytest.approx(0.0, abs=1e-12)
        assert result["tor_sq"] == pytest.approx(0.0, abs=1e-12)
        assert result["tel_sq"] == pytest.approx(0.0, abs=1e-12)

    @given(_canonical_state_strategy(), _canonical_state_strategy())
    @settings(max_examples=50)
    def test_non_negative(self, a, b):
        """ds² must be >= 0."""
        result = compute_ds_squared(a, b)
        assert result["ds_squared"] >= -1e-12

    @given(_canonical_state_strategy(), _canonical_state_strategy())
    @settings(max_examples=50)
    def test_symmetry(self, a, b):
        """d(a, b) == d(b, a)."""
        r1 = compute_ds_squared(a, b)
        r2 = compute_ds_squared(b, a)
        assert r1["ds_squared"] == pytest.approx(r2["ds_squared"], abs=1e-10)


# ═══════════════════════════════════════════════════════════════
# 3. Boundary amplification (THE security property)
# ═══════════════════════════════════════════════════════════════

class TestBoundaryAmplification:

    def test_near_boundary_amplifies_distance(self):
        """A small shift near ||u||=0.95 must produce MUCH larger ds²
        than the same shift near the origin.

        This is the core security mechanism: adversarial drift toward
        the Poincare boundary costs exponentially more.
        """
        delta = 0.02

        # Near origin: shift from (0,0,...) to (delta,0,...)
        origin_a = build_canonical_state(u=[0.0] * 6, theta=[0.0] * 6)
        origin_b = build_canonical_state(u=[delta, 0.0, 0.0, 0.0, 0.0, 0.0], theta=[0.0] * 6)
        ds2_origin = compute_ds_squared(origin_a, origin_b)

        # Near boundary: shift from (0.95,0,...) to (0.95+delta,0,...)
        boundary_a = build_canonical_state(u=[0.93, 0.0, 0.0, 0.0, 0.0, 0.0], theta=[0.0] * 6)
        boundary_b = build_canonical_state(u=[0.93 + delta, 0.0, 0.0, 0.0, 0.0, 0.0], theta=[0.0] * 6)
        ds2_boundary = compute_ds_squared(boundary_a, boundary_b)

        # The boundary distance must be at least 10x the origin distance
        amplification = ds2_boundary["hyp_sq"] / max(ds2_origin["hyp_sq"], 1e-15)
        assert amplification > 10, (
            f"Boundary amplification = {amplification:.1f}x, expected >10x. "
            f"origin hyp_sq={ds2_origin['hyp_sq']:.6f}, boundary hyp_sq={ds2_boundary['hyp_sq']:.6f}"
        )

    def test_extreme_boundary_amplification(self):
        """At ||u||=0.99, a radial shift should produce massive ds²."""
        u_a = [0.97, 0.0, 0.0, 0.0, 0.0, 0.0]
        u_b = [0.99, 0.0, 0.0, 0.0, 0.0, 0.0]  # 0.02 radial shift near boundary
        d2 = _hyperbolic_distance_sq(u_a, u_b)
        # Compare with same 0.02 shift at origin
        u_c = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        u_d = [0.02, 0.0, 0.0, 0.0, 0.0, 0.0]
        d2_origin = _hyperbolic_distance_sq(u_c, u_d)
        # Boundary must amplify by at least 10x
        assert d2 > 10 * d2_origin, (
            f"Expected boundary >> origin. boundary={d2:.4f}, origin={d2_origin:.4f}"
        )


# ═══════════════════════════════════════════════════════════════
# 4. Torus periodicity
# ═══════════════════════════════════════════════════════════════

class TestTorusPeriodicity:

    def test_wrap_around_zero(self):
        """d(0.01, 2*pi - 0.01) should be ~0.02, not ~6.26."""
        a = [0.01] + [0.0] * 5
        b = [2 * math.pi - 0.01] + [0.0] * 5
        d2 = _torus_distance_sq(a, b)
        assert d2 < 0.01, f"Torus should wrap: d²={d2:.6f}, expected < 0.01"

    def test_opposite_angles_pi(self):
        """d(0, pi) = pi on the circle."""
        a = [0.0] + [0.0] * 5
        b = [math.pi] + [0.0] * 5
        d2 = _torus_distance_sq(a, b)
        assert d2 == pytest.approx(math.pi ** 2, rel=1e-6)

    @given(
        st.floats(min_value=0.0, max_value=2 * math.pi),
        st.floats(min_value=0.0, max_value=2 * math.pi),
    )
    @settings(max_examples=100)
    def test_torus_symmetry(self, a_val, b_val):
        """Torus distance is symmetric."""
        a = [a_val] + [0.0] * 5
        b = [b_val] + [0.0] * 5
        assert _torus_distance_sq(a, b) == pytest.approx(_torus_distance_sq(b, a), abs=1e-12)


# ═══════════════════════════════════════════════════════════════
# 5. Hyperbolic distance properties
# ═══════════════════════════════════════════════════════════════

class TestHyperbolicProperties:

    def test_identity_of_indiscernibles(self):
        u = [0.1, 0.2, 0.0, 0.0, 0.0, 0.0]
        assert _hyperbolic_distance_sq(u, u) == pytest.approx(0.0, abs=1e-12)

    @given(_poincare_point(), _poincare_point())
    @settings(max_examples=50)
    def test_symmetry(self, u, v):
        d_uv = _hyperbolic_distance_sq(u, v)
        d_vu = _hyperbolic_distance_sq(v, u)
        assert d_uv == pytest.approx(d_vu, abs=1e-10)

    @given(_poincare_point(), _poincare_point(), _poincare_point())
    @settings(max_examples=30)
    def test_triangle_inequality(self, u, v, w):
        """d(u,w) <= d(u,v) + d(v,w) (on distances, not squared)."""
        d_uv = math.sqrt(_hyperbolic_distance_sq(u, v))
        d_vw = math.sqrt(_hyperbolic_distance_sq(v, w))
        d_uw = math.sqrt(_hyperbolic_distance_sq(u, w))
        # Allow small numerical tolerance
        assert d_uw <= d_uv + d_vw + 1e-8


# ═══════════════════════════════════════════════════════════════
# 6. Harmonic energy
# ═══════════════════════════════════════════════════════════════

class TestHarmonicEnergy:

    def test_origin_energy_is_one(self):
        """H(6, R) at r=0 → R=1 → 1^36 = 1."""
        assert _compute_energy_harmonic(0.0) == pytest.approx(1.0)

    def test_energy_increases_with_radius(self):
        """Energy must be monotonically increasing with r."""
        e1 = _compute_energy_harmonic(0.1)
        e2 = _compute_energy_harmonic(0.5)
        e3 = _compute_energy_harmonic(0.9)
        assert e1 < e2 < e3

    def test_energy_explodes_near_boundary(self):
        """At r=0.9, R=10, H = 10^36 — astronomically large."""
        e = _compute_energy_harmonic(0.9)
        assert e > 1e30, f"Expected > 1e30, got {e:.2e}"

    def test_outside_ball_raises(self):
        with pytest.raises(CanonicalStateError):
            _compute_energy_harmonic(1.0)


# ═══════════════════════════════════════════════════════════════
# 7. Audit state transition
# ═══════════════════════════════════════════════════════════════

class TestAuditStateTransition:

    def test_audit_records_transition(self):
        auditor = StateTransitionAuditor()
        before = safe_origin()
        after = build_canonical_state(
            u=[0.1, 0.0, 0.0, 0.0, 0.0, 0.0],
            theta=[0.0] * 6,
            risk_aggregate=0.3,
        )
        entry = auditor.audit_state_transition(before, after, "ALLOW", "agent-1")
        assert entry["decision"] == "ALLOW"
        assert entry["agent_id"] == "agent-1"
        assert entry["ds_squared"] > 0
        assert auditor.count == 1

    def test_hash_chain_integrity(self):
        auditor = StateTransitionAuditor()
        s = safe_origin()
        for i in range(5):
            s2 = build_canonical_state(
                u=[0.01 * (i + 1), 0.0, 0.0, 0.0, 0.0, 0.0],
                theta=[0.0] * 6,
            )
            auditor.audit_state_transition(s, s2, "ALLOW", f"agent-{i}")
        assert auditor.verify_chain() is True

    def test_tampered_chain_fails(self):
        auditor = StateTransitionAuditor()
        s = safe_origin()
        s2 = build_canonical_state(u=[0.1, 0.0, 0.0, 0.0, 0.0, 0.0], theta=[0.0] * 6)
        auditor.audit_state_transition(s, s2, "ALLOW", "agent-1")
        auditor.audit_state_transition(s, s2, "DENY", "agent-2")
        # Tamper with an entry
        auditor._entries[0]["decision"] = "HACKED"
        assert auditor.verify_chain() is False

    def test_multiple_decisions_logged(self):
        auditor = StateTransitionAuditor()
        s = safe_origin()
        for decision in ["ALLOW", "WARN", "DENY", "ALLOW", "REVIEW"]:
            s2 = build_canonical_state(u=[0.05, 0.0, 0.0, 0.0, 0.0, 0.0], theta=[0.0] * 6)
            auditor.audit_state_transition(s, s2, decision, "agent-x")
        assert auditor.count == 5
        decisions = [e["decision"] for e in auditor.entries]
        assert decisions == ["ALLOW", "WARN", "DENY", "ALLOW", "REVIEW"]
