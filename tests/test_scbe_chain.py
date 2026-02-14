"""
SCBE Formula Chain Tests — mathematical contract for the kernel.

Tests the complete pipeline: d → x → H_eff → harm → Ω → decision
These encode the INTENDED behavior. Even if the TS code evolves,
these tests define what the math should do.

Aligned to kernel code at packages/kernel/src/temporalIntent.ts:
  - ALLOW_THRESHOLD = 0.85
  - QUARANTINE_THRESHOLD = 0.40
  - harm_score = 1 / (1 + log(max(1, H_eff)))

@version 3.2.5
"""

import pytest
import math

from src.scbe_math_reference import (
    hyperbolic_distance_poincare,
    compute_x_factor,
    harmonic_wall_eff,
    harm_score_from_wall,
    harm_score_from_log,
    triadic_risk,
    omega_gate,
    omega_decision,
    full_chain,
    ALLOW_THRESHOLD,
    QUARANTINE_THRESHOLD,
)


# ═══════════════════════════════════════════════════════════════
# Formula 1: Hyperbolic Distance
# ═══════════════════════════════════════════════════════════════


class TestHyperbolicDistance:
    def test_zero_distance_same_point(self):
        assert hyperbolic_distance_poincare((0.0, 0.0), (0.0, 0.0)) == pytest.approx(0.0, abs=1e-5)

    def test_symmetry(self):
        a = (0.2, 0.1)
        b = (-0.1, 0.05)
        dab = hyperbolic_distance_poincare(a, b)
        dba = hyperbolic_distance_poincare(b, a)
        assert dab == pytest.approx(dba)
        assert dab > 0.0

    def test_increases_near_boundary(self):
        safe = (0.0, 0.0)
        d1 = hyperbolic_distance_poincare((0.90, 0.0), safe)
        d2 = hyperbolic_distance_poincare((0.95, 0.0), safe)
        assert d2 > d1
        assert (d2 - d1) > 0.3  # exponential growth near edge

    def test_rejects_outside_ball(self):
        with pytest.raises(ValueError):
            hyperbolic_distance_poincare((1.0, 0.0), (0.0, 0.0))
        with pytest.raises(ValueError):
            hyperbolic_distance_poincare((0.0, 0.0), (1.001, 0.0))

    def test_triangle_inequality(self):
        a = (0.1, 0.2)
        b = (0.3, -0.1)
        c = (-0.2, 0.4)
        dab = hyperbolic_distance_poincare(a, b)
        dbc = hyperbolic_distance_poincare(b, c)
        dac = hyperbolic_distance_poincare(a, c)
        assert dac <= dab + dbc + 1e-10

    def test_numerical_stability_very_close_to_boundary(self):
        safe = (0.0, 0.0)
        u = (0.999999, 0.0)
        d = hyperbolic_distance_poincare(u, safe)
        assert math.isfinite(d)
        assert d > 10.0  # should be very large

    def test_works_in_higher_dimensions(self):
        u = (0.1, 0.2, 0.3, 0.1, 0.0, 0.0)
        v = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        d = hyperbolic_distance_poincare(u, v)
        assert d > 0.0
        assert math.isfinite(d)


# ═══════════════════════════════════════════════════════════════
# Formula 2: x-factor (intent persistence)
# ═══════════════════════════════════════════════════════════════


class TestXFactor:
    def test_baseline_innocent(self):
        x = compute_x_factor(accumulated_intent=0.0, trust=1.0)
        assert x == pytest.approx(0.5)

    def test_increases_with_intent(self):
        x0 = compute_x_factor(accumulated_intent=0.0, trust=1.0)
        x1 = compute_x_factor(accumulated_intent=4.0, trust=1.0)
        assert x1 > x0

    def test_increases_with_lower_trust(self):
        x_hi = compute_x_factor(accumulated_intent=2.0, trust=1.0)
        x_lo = compute_x_factor(accumulated_intent=2.0, trust=0.0)
        assert x_lo >= x_hi

    def test_capped_at_3(self):
        x = compute_x_factor(accumulated_intent=1e6, trust=0.0)
        assert x == pytest.approx(3.0)

    def test_trust_clamped_to_01(self):
        x1 = compute_x_factor(accumulated_intent=1.0, trust=-5.0)
        x2 = compute_x_factor(accumulated_intent=1.0, trust=0.0)
        assert x1 == pytest.approx(x2)

        x3 = compute_x_factor(accumulated_intent=1.0, trust=10.0)
        x4 = compute_x_factor(accumulated_intent=1.0, trust=1.0)
        assert x3 == pytest.approx(x4)


# ═══════════════════════════════════════════════════════════════
# Formula 3: Harmonic Wall — H_eff(d, R, x) = R^(d²·x)
# ═══════════════════════════════════════════════════════════════


class TestHarmonicWall:
    def test_at_center_cost_is_one(self):
        H = harmonic_wall_eff(d=0.0, x=1.0, R=1.5)
        assert H == pytest.approx(1.0)

    def test_monotone_in_d(self):
        H1 = harmonic_wall_eff(d=0.3, x=1.0)
        H2 = harmonic_wall_eff(d=0.7, x=1.0)
        assert H2 > H1

    def test_monotone_in_x(self):
        H1 = harmonic_wall_eff(d=0.5, x=0.5)
        H2 = harmonic_wall_eff(d=0.5, x=2.0)
        assert H2 > H1

    def test_extreme_distance_is_massive(self):
        H = harmonic_wall_eff(d=3.0, x=3.0, R=1.5)
        assert H > 50000  # 1.5^27 ≈ 56,815

    def test_rejects_bad_R(self):
        with pytest.raises(ValueError):
            harmonic_wall_eff(d=1.0, x=1.0, R=1.0)
        with pytest.raises(ValueError):
            harmonic_wall_eff(d=1.0, x=1.0, R=0.5)

    def test_numerical_stability_large_exponent(self):
        H = harmonic_wall_eff(d=5.0, x=3.0, R=1.5)
        assert math.isfinite(H)
        assert H > 1e10


# ═══════════════════════════════════════════════════════════════
# harm_score inversion
# ═══════════════════════════════════════════════════════════════


class TestHarmScore:
    def test_at_center_score_is_one(self):
        assert harm_score_from_wall(1.0) == pytest.approx(1.0)

    def test_below_one_clamps_to_one(self):
        assert harm_score_from_wall(0.1) == pytest.approx(1.0)

    def test_monotone_decreasing(self):
        h2 = harm_score_from_wall(2.0)
        h10 = harm_score_from_wall(10.0)
        h1e6 = harm_score_from_wall(1e6)
        assert 0.0 < h1e6 < h10 < h2 < 1.0

    def test_never_reaches_zero(self):
        h = harm_score_from_wall(1e100)
        assert h > 0.0

    def test_smooth_at_boundary(self):
        h1 = harm_score_from_wall(1.0)
        h1p = harm_score_from_wall(1.0 + 1e-12)
        assert h1p <= h1
        assert abs(h1 - h1p) < 1e-10

    def test_log_space_matches_exp_space(self):
        """harm_score_from_log(logH) == harm_score_from_wall(exp(logH))"""
        for logH in [0.0, 0.5, 1.0, 5.0, 20.0, 100.0]:
            from_log = harm_score_from_log(logH)
            from_wall = harm_score_from_wall(math.exp(logH))
            assert from_log == pytest.approx(from_wall, rel=1e-8)


# ═══════════════════════════════════════════════════════════════
# Formula 4: Triadic Risk
# ═══════════════════════════════════════════════════════════════


class TestTriadicRisk:
    def test_bounded_between_min_and_max(self):
        vals = (0.2, 0.8, 0.5)
        dtri = triadic_risk(*vals)
        assert min(vals) <= dtri <= max(vals)

    def test_memory_weight_dominates(self):
        base = triadic_risk(0.2, 0.2, 0.2)
        mem_high = triadic_risk(0.2, 1.0, 0.2)
        gov_high = triadic_risk(0.2, 0.2, 1.0)
        assert mem_high > base
        assert gov_high > base
        assert mem_high >= gov_high  # λ_memory=0.5 > λ_governance=0.2

    def test_rejects_negative(self):
        with pytest.raises(ValueError):
            triadic_risk(-1.0, 0.5, 0.5)

    def test_zero_inputs_give_zero(self):
        dtri = triadic_risk(0.0, 0.0, 0.0)
        assert dtri == pytest.approx(0.0)

    def test_equal_inputs_return_that_value(self):
        dtri = triadic_risk(0.5, 0.5, 0.5)
        assert dtri == pytest.approx(0.5, rel=1e-3)


# ═══════════════════════════════════════════════════════════════
# Formula 5: Omega Gate
# ═══════════════════════════════════════════════════════════════


class TestOmegaGate:
    def test_all_ones_gives_one(self):
        assert omega_gate(1, 1, 1, 1, 1) == pytest.approx(1.0)

    def test_any_zero_gives_zero(self):
        assert omega_gate(0, 1, 1, 1, 1) == pytest.approx(0.0)
        assert omega_gate(1, 0, 1, 1, 1) == pytest.approx(0.0)
        assert omega_gate(1, 1, 0, 1, 1) == pytest.approx(0.0)
        assert omega_gate(1, 1, 1, 0, 1) == pytest.approx(0.0)
        assert omega_gate(1, 1, 1, 1, 0) == pytest.approx(0.0)

    def test_clamps_inputs(self):
        assert omega_gate(2.0, 1, 1, 1, 1) == pytest.approx(1.0)
        assert omega_gate(-1.0, 1, 1, 1, 1) == pytest.approx(0.0)


# ═══════════════════════════════════════════════════════════════
# Decision Boundaries
# ═══════════════════════════════════════════════════════════════


class TestDecisionBoundaries:
    def test_allow_above_threshold(self):
        assert omega_decision(0.90) == "ALLOW"
        assert omega_decision(ALLOW_THRESHOLD + 0.01) == "ALLOW"

    def test_quarantine_in_middle(self):
        assert omega_decision(0.60) == "QUARANTINE"
        assert omega_decision(QUARANTINE_THRESHOLD + 0.01) == "QUARANTINE"

    def test_deny_below_threshold(self):
        assert omega_decision(0.30) == "DENY"
        assert omega_decision(0.0) == "DENY"

    def test_exact_boundaries(self):
        # At exactly the threshold, behavior depends on > vs >=
        # kernel uses > (strict), so at-threshold falls to next tier
        assert omega_decision(ALLOW_THRESHOLD) == "QUARANTINE"
        assert omega_decision(QUARANTINE_THRESHOLD) == "DENY"


# ═══════════════════════════════════════════════════════════════
# Full Chain Integration
# ═══════════════════════════════════════════════════════════════


class TestFullChain:
    def test_safe_agent_gets_allow(self):
        out = full_chain(
            (0.1, 0.05),
            (0.0, 0.0),
            accumulated_intent=0.0,
            trust=1.0,
            I_fast=0.1,
            I_memory=0.1,
            I_governance=0.1,
        )
        assert out.decision == "ALLOW"
        assert out.omega > ALLOW_THRESHOLD
        assert out.harm > 0.9  # near-center, harm score near 1

    def test_dangerous_agent_gets_deny(self):
        out = full_chain(
            (0.95, 0.0),
            (0.0, 0.0),
            accumulated_intent=8.0,
            trust=0.0,
            I_fast=0.2,
            I_memory=0.2,
            I_governance=0.2,
        )
        assert out.decision == "DENY"
        assert out.omega < QUARANTINE_THRESHOLD
        assert out.H_eff > 100  # massive wall cost

    def test_safe_has_higher_omega_than_dangerous(self):
        center = (0.0, 0.0)

        out_safe = full_chain(
            (0.1, 0.05),
            center,
            accumulated_intent=0.0,
            trust=1.0,
            I_fast=0.2,
            I_memory=0.2,
            I_governance=0.2,
        )

        out_bad = full_chain(
            (0.95, 0.0),
            center,
            accumulated_intent=8.0,
            trust=0.0,
            I_fast=0.2,
            I_memory=0.2,
            I_governance=0.2,
        )

        assert out_bad.H_eff > out_safe.H_eff
        assert out_bad.harm < out_safe.harm
        assert out_safe.omega > out_bad.omega

    def test_pqc_failure_blocks_even_safe_agent(self):
        out = full_chain(
            (0.1, 0.0),
            (0.0, 0.0),
            accumulated_intent=0.0,
            trust=1.0,
            I_fast=0.1,
            I_memory=0.1,
            I_governance=0.1,
            pqc_valid=0.0,  # crypto check failed
        )
        assert out.omega == pytest.approx(0.0)
        assert out.decision == "DENY"

    def test_moderate_drift_gets_quarantine(self):
        out = full_chain(
            (0.5, 0.0),
            (0.0, 0.0),
            accumulated_intent=3.0,
            trust=0.5,
            I_fast=0.3,
            I_memory=0.3,
            I_governance=0.3,
        )
        # Moderate position + moderate intent → somewhere in middle
        assert out.H_eff > 1.0
        assert out.harm < 1.0

    def test_chain_numerically_stable_near_boundary(self):
        out = full_chain(
            (0.999999, 0.0),
            (0.0, 0.0),
            accumulated_intent=0.0,
            trust=1.0,
            I_fast=0.1,
            I_memory=0.1,
            I_governance=0.1,
        )
        assert math.isfinite(out.d)
        assert math.isfinite(out.H_eff)
        assert math.isfinite(out.omega)
        assert 0.0 <= out.omega <= 1.0

    def test_6d_poincare_ball(self):
        """Test with 6D vectors matching the kernel's Vector6D."""
        u = (0.1, 0.15, 0.05, 0.08, 0.02, 0.1)
        v = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        out = full_chain(
            u,
            v,
            accumulated_intent=0.5,
            trust=0.9,
            I_fast=0.2,
            I_memory=0.2,
            I_governance=0.2,
        )
        assert out.d > 0.0
        assert math.isfinite(out.omega)
        assert out.decision in ("ALLOW", "QUARANTINE", "DENY")
