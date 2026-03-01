"""
L12 Harmonic Ternary Surface — Machine-Enforced Golden Vectors
==============================================================

This test suite locks the ternary decision surface. If any of these
tests fail, the harmonic scaling formulas or trit thresholds have
changed, which means:
  - Customer integrations may break
  - Signed governance receipts may become invalid
  - Patent claims may be undermined

Update these tests ONLY with a schema_version bump and migration plan.

Canonical reference: docs/L12_HARMONIC_SCALING_CANON.md
Source of truth: src/symphonic_cipher/scbe_aethermoore/governance/
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.symphonic_cipher.scbe_aethermoore.governance.harmonic_scaling import (
    PHI,
    H_score,
    H_wall,
    H_exp,
    harmonic_cost,
    security_bits,
)
from src.symphonic_cipher.scbe_aethermoore.governance.harmonic_trits import (
    TritVector,
    h_trit,
    ternary_vector,
    trit_decision,
    trit_label,
    ALLOW,
    QUARANTINE,
    ESCALATE,
    DENY,
)


# ── H_score Golden Vectors ──────────────────────────────────────────────


class TestHScoreGoldenVectors:
    """H_score(d*, pd) = 1 / (1 + d* + 2*pd) — exact values."""

    def test_origin(self):
        assert H_score(0.0, 0.0) == 1.0

    def test_d1_pd0(self):
        assert H_score(1.0, 0.0) == 0.5

    def test_d2_pd0(self):
        assert abs(H_score(2.0, 0.0) - 1.0 / 3.0) < 1e-10

    def test_d0_pd05(self):
        assert H_score(0.0, 0.5) == 0.5

    def test_d1_pd05(self):
        assert abs(H_score(1.0, 0.5) - 1.0 / 3.0) < 1e-10

    def test_d5_pd1(self):
        assert H_score(5.0, 1.0) == 0.125

    def test_monotonic_decreasing_in_d(self):
        prev = H_score(0.0)
        for d in [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]:
            cur = H_score(d)
            assert cur < prev, f"H_score should decrease: {prev} -> {cur} at d={d}"
            prev = cur

    def test_monotonic_decreasing_in_pd(self):
        prev = H_score(1.0, 0.0)
        for pd in [0.1, 0.2, 0.5, 0.8, 1.0]:
            cur = H_score(1.0, pd)
            assert cur < prev, f"H_score should decrease in pd: {prev} -> {cur}"
            prev = cur

    def test_always_positive(self):
        for d in [0, 0.01, 1, 10, 100, 1000]:
            for pd in [0, 0.5, 1.0]:
                assert H_score(d, pd) > 0

    def test_bounded_above_by_1(self):
        for d in [0, 0.01, 1, 10, 100]:
            assert H_score(d) <= 1.0

    def test_never_zero(self):
        """H_score approaches but never reaches zero."""
        assert H_score(1e10) > 0
        assert H_score(1e10, 1.0) > 0


# ── H_wall Golden Vectors ───────────────────────────────────────────────


class TestHWallGoldenVectors:
    """H_wall(d*, α, β) = 1 + α·tanh(β·d*) — exact values."""

    def test_origin(self):
        assert H_wall(0.0) == 1.0

    def test_d05(self):
        expected = 1.0 + math.tanh(0.5)
        assert abs(H_wall(0.5) - expected) < 1e-10

    def test_d1(self):
        expected = 1.0 + math.tanh(1.0)
        assert abs(H_wall(1.0) - expected) < 1e-10

    def test_d2(self):
        expected = 1.0 + math.tanh(2.0)
        assert abs(H_wall(2.0) - expected) < 1e-10

    def test_saturation_at_100(self):
        """At d*=100, tanh → 1, so H_wall → 2.0."""
        assert abs(H_wall(100.0) - 2.0) < 1e-6

    def test_monotonic_increasing(self):
        prev = H_wall(0.0)
        for d in [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]:
            cur = H_wall(d)
            assert cur > prev, f"H_wall should increase: {prev} -> {cur}"
            prev = cur

    def test_bounded_below_by_1(self):
        for d in [0, 0.01, 1, 10]:
            assert H_wall(d) >= 1.0

    def test_bounded_above_by_1_plus_alpha(self):
        """Default alpha=1 → max is 2.0."""
        for d in [0, 0.01, 1, 10, 100]:
            assert H_wall(d) <= 2.0 + 1e-10

    def test_custom_alpha(self):
        """alpha=2 → H_wall in [1, 3]."""
        assert H_wall(0.0, alpha=2.0) == 1.0
        assert abs(H_wall(100.0, alpha=2.0) - 3.0) < 1e-6

    def test_custom_beta(self):
        """Higher beta → steeper transition."""
        slow = H_wall(0.5, beta=0.5)
        fast = H_wall(0.5, beta=2.0)
        assert fast > slow  # steeper beta → higher at same d*


# ── H_exp Golden Vectors ────────────────────────────────────────────────


class TestHExpGoldenVectors:
    """H_exp(d*, R) = R^(d*²) — exact values."""

    def test_origin(self):
        assert H_exp(0.0) == 1.0

    def test_d1_phi(self):
        """H_exp(1, PHI) = PHI^1 = PHI."""
        assert abs(H_exp(1.0) - PHI) < 1e-10

    def test_d2_phi(self):
        """H_exp(2, PHI) = PHI^4."""
        assert abs(H_exp(2.0) - PHI**4) < 1e-6

    def test_d3_phi(self):
        """H_exp(3, PHI) = PHI^9."""
        assert abs(H_exp(3.0) - PHI**9) < 1e-3

    def test_matches_braid_harmonic_cost(self):
        """H_exp with R=PHI must match hamiltonian_braid.harmonic_cost()."""
        for d in [0, 0.5, 1.0, 2.0, 3.0]:
            assert abs(H_exp(d) - harmonic_cost(d)) < 1e-10

    def test_clamped_no_overflow(self):
        """Large d* must not overflow — exponent clamped at 50."""
        result = H_exp(100.0)
        assert math.isfinite(result)

    def test_asymptotic_dominance_over_wall(self):
        """H_exp grows faster than H_wall at large distances.

        At small d*, H_wall can exceed H_exp (e.g., at d*=1:
        H_wall=1.76, H_exp=1.62). But H_exp overtakes at d*≈1.5
        and then dominates forever.
        """
        # At d*=2, H_exp > H_wall
        assert H_exp(2.0) > H_wall(2.0)
        # At d*=3, gap is enormous
        assert H_exp(3.0) > 10 * H_wall(3.0)


# ── Ternary Trit Decomposition ──────────────────────────────────────────


class TestTernaryVectorComputation:
    """Ternary decomposition: three trits from three formulas."""

    def test_safe_all_positive(self):
        """d*=0.1, pd=0 → all three in safe region → (+1, +1, +1)."""
        tv = ternary_vector(0.1, 0.0)
        assert tv.t_score == 1
        assert tv.t_wall == 1
        assert tv.t_exp == 1

    def test_hostile_all_negative(self):
        """d*=5, pd=0.5 → all three in hostile region → (-1, -1, -1)."""
        tv = ternary_vector(5.0, 0.5)
        assert tv.t_score == -1
        assert tv.t_wall == -1
        assert tv.t_exp == -1

    def test_transition_zone(self):
        """d*=1.0, pd=0 → H_score=0.5 (transition), H_wall=1.76 (transition)."""
        tv = ternary_vector(1.0, 0.0)
        assert tv.t_score == 0   # 0.5 is between 0.33 and 0.67
        assert tv.t_wall == 0    # 1.76 is between 1.5 and 1.9

    def test_phase_incoherent_disagreement(self):
        """Low d* + high pd → H_score drops but H_wall/H_exp stay safe.

        This is the SIGNATURE of a subtle attacker: geometrically
        close to safe behavior but phase-chaotic.
        """
        tv = ternary_vector(0.1, 0.8)
        # H_score = 1/(1 + 0.1 + 1.6) = 0.37 → trit = 0 (transition)
        # H_wall  = 1 + tanh(0.1) = 1.10 → trit = +1 (safe)
        # H_exp   = PHI^0.01 ≈ 1.005 → trit = +1 (safe)
        assert tv.t_wall == 1
        assert tv.t_exp == 1
        assert tv.t_score <= 0  # pulled down by pd
        assert tv.phase_incoherent

    def test_extreme_phase_incoherent(self):
        """d*=0.0, pd=1.0 → extreme phase deviation at zero distance."""
        tv = ternary_vector(0.0, 1.0)
        # H_score = 1/(1 + 0 + 2.0) = 0.333... → trit = 0 (transition, at boundary)
        # H_wall  = 1 + tanh(0) = 1.0 → trit = +1 (safe)
        # H_exp   = PHI^0 = 1.0 → trit = +1 (safe)
        assert tv.t_score <= 0  # at or below transition
        assert tv.t_wall == 1
        assert tv.t_exp == 1
        assert tv.phase_incoherent

    def test_deeply_hostile_phase_incoherent(self):
        """d*=0.0, pd=1.5 → H_score deep in hostile → t_score = -1."""
        tv = ternary_vector(0.0, 1.5)
        # H_score = 1/(1 + 0 + 3.0) = 0.25 → trit = -1 (hostile)
        assert tv.t_score == -1
        assert tv.t_wall == 1
        assert tv.t_exp == 1

    def test_h_trit_dict_matches_ternary_vector(self):
        """h_trit() and ternary_vector() must produce identical trits."""
        for d in [0.1, 1.0, 3.0]:
            for pd in [0.0, 0.5, 1.0]:
                trits = h_trit(d, pd)
                tv = ternary_vector(d, pd)
                assert trits["t_score"] == tv.t_score
                assert trits["t_wall"] == tv.t_wall
                assert trits["t_exp"] == tv.t_exp

    def test_raw_values_stored(self):
        """TritVector stores the raw H values for diagnostics."""
        tv = ternary_vector(1.0, 0.0)
        assert abs(tv.h_score - 0.5) < 1e-10
        assert abs(tv.h_wall - (1.0 + math.tanh(1.0))) < 1e-10
        assert abs(tv.h_exp - PHI) < 1e-10

    def test_as_tuple(self):
        tv = ternary_vector(0.1)
        assert tv.as_tuple == (tv.t_score, tv.t_wall, tv.t_exp)

    def test_sum_fully_safe(self):
        tv = ternary_vector(0.1)
        assert tv.sum == 3

    def test_sum_fully_hostile(self):
        tv = ternary_vector(5.0, 0.5)
        assert tv.sum == -3


# ── Trit-Based Decision Bridge ──────────────────────────────────────────


class TestTritDecisionBridge:
    """Trit vector → governance decision mapping."""

    def test_all_safe_allows(self):
        tv = ternary_vector(0.1, 0.0)
        assert trit_decision(tv) == ALLOW

    def test_all_hostile_denies(self):
        tv = ternary_vector(5.0, 0.5)
        assert trit_decision(tv) == DENY

    def test_any_hostile_denies(self):
        """Even one hostile trit forces DENY."""
        # d*=3, pd=0 → H_score≈0.25(-1), H_wall≈1.995(-1), H_exp≈PHI^9(-1)
        tv = ternary_vector(3.0, 0.0)
        assert trit_decision(tv) == DENY

    def test_transition_zone_quarantines(self):
        """Transition trits (no hostile, no all-safe) → QUARANTINE."""
        tv = ternary_vector(1.0, 0.0)
        # At least one trit should be 0
        if not tv.any_hostile and not tv.all_safe:
            assert trit_decision(tv) == QUARANTINE

    def test_phase_incoherent_escalates(self):
        """Phase-incoherent close attacker → ESCALATE."""
        tv = ternary_vector(0.1, 0.8)
        if tv.phase_incoherent:
            assert trit_decision(tv) == ESCALATE

    def test_extreme_phase_incoherent_escalates(self):
        """Phase deviation at d*≈0 with t_score=0 → ESCALATE.

        At d*=0.01, pd=1.0: H_score=0.332 → t_score=0 (transition).
        Since t_wall=+1, t_exp=+1 but t_score<=0, this is
        phase_incoherent → ESCALATE.
        """
        tv = ternary_vector(0.01, 1.0)
        assert trit_decision(tv) == ESCALATE

    def test_deeply_hostile_phase_incoherent_denies(self):
        """Deeply hostile phase deviation (pd=1.5) → t_score=-1 → DENY.

        Rule 1 (any hostile trit) beats Rule 2 (phase_incoherent).
        """
        tv = ternary_vector(0.0, 1.5)
        assert tv.t_score == -1
        assert trit_decision(tv) == DENY

    def test_decision_ordering_deny_beats_escalate(self):
        """DENY > ESCALATE > QUARANTINE > ALLOW (severity ordering)."""
        # Construct a TritVector where phase_incoherent but also hostile
        tv = TritVector(t_score=-1, t_wall=1, t_exp=1)
        # This is phase_incoherent AND has a hostile trit
        # Rule 1 (any hostile → DENY) must beat Rule 2 (phase_incoherent → ESCALATE)
        assert trit_decision(tv) == DENY


# ── Trit Labels ─────────────────────────────────────────────────────────


class TestTritLabels:
    """Human-readable labels for trit vectors."""

    def test_fully_safe_label(self):
        tv = ternary_vector(0.1)
        assert trit_label(tv) == "fully_safe"

    def test_fully_adversarial_label(self):
        tv = ternary_vector(5.0, 0.5)
        assert trit_label(tv) == "fully_adversarial"

    def test_phase_incoherent_label(self):
        tv = TritVector(t_score=-1, t_wall=1, t_exp=1)
        assert trit_label(tv) == "phase_incoherent_close"

    def test_unknown_label_format(self):
        tv = TritVector(t_score=1, t_wall=0, t_exp=-1)
        label = trit_label(tv)
        assert label.startswith("unknown_")


# ── Cross-validation with Hamiltonian Braid ─────────────────────────────


class TestBraidAlignment:
    """Verify canonical formulas align with hamiltonian_braid.py."""

    def test_harmonic_cost_is_h_exp_phi(self):
        """harmonic_cost(d) must equal H_exp(d, PHI) = PHI^(d²)."""
        for d in [0, 0.5, 1.0, 2.0, 3.0, 5.0]:
            assert abs(harmonic_cost(d) - H_exp(d, PHI)) < 1e-10

    def test_phi_constant_matches(self):
        """PHI must be the golden ratio."""
        assert abs(PHI - (1 + math.sqrt(5)) / 2) < 1e-15

    def test_braid_mode_thresholds_consistent(self):
        """Braid modes use PHI-based cost thresholds.

        From hamiltonian_braid.py braid_step():
          cost < PHI     → RUN   (d < 1.0)
          cost < PHI^4   → HOLD  (d < 2.0)
          cost < PHI^9   → QUAR  (d < 3.0)
          else           → ROLLBACK

        H_exp(1.0) = PHI → boundary of RUN
        H_exp(2.0) = PHI^4 → boundary of HOLD
        H_exp(3.0) = PHI^9 → boundary of QUAR
        """
        assert abs(H_exp(1.0) - PHI) < 1e-10
        assert abs(H_exp(2.0) - PHI**4) < 1e-6
        assert abs(H_exp(3.0) - PHI**9) < 1e-3

    def test_braid_phase_deviation_range(self):
        """Braid phase_deviation returns [0, 1].

        Chebyshev distance / 2 in {-1,0,+1}² grid.
        Max deviation = 2 (corner to corner), normalized to 1.0.

        H_score must accept pd in [0, 1] and produce valid output.
        """
        for pd in [0.0, 0.25, 0.5, 0.75, 1.0]:
            result = H_score(1.0, pd)
            assert 0 < result <= 1.0


# ── Security Bits ───────────────────────────────────────────────────────


class TestSecurityBits:
    """Security bits = d*² · log₂(PHI)."""

    def test_zero_distance_zero_bits(self):
        sl = security_bits(0.0)
        assert sl.bits == 0.0
        assert sl.label == "trivial"

    def test_d10_is_strong(self):
        """d*=10 → bits = 100 · log₂(1.618) ≈ 69.4."""
        sl = security_bits(10.0)
        assert 60 < sl.bits < 80
        assert sl.label == "moderate"

    def test_d16_is_military(self):
        """d*=16 → bits = 256 · 0.694 ≈ 177.7."""
        sl = security_bits(16.0)
        assert sl.bits > 128
        assert sl.label == "military"

    def test_monotonic(self):
        prev = security_bits(0.0).bits
        for d in [1, 5, 10, 20]:
            cur = security_bits(d).bits
            assert cur > prev
            prev = cur


# ── Sweep Tests (Property-like) ─────────────────────────────────────────


class TestSweepProperties:
    """Sweep d* and pd to verify structural properties hold everywhere."""

    D_VALUES = [0, 0.01, 0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0]
    PD_VALUES = [0, 0.1, 0.5, 1.0]

    def test_h_score_always_in_range(self):
        for d in self.D_VALUES:
            for pd in self.PD_VALUES:
                v = H_score(d, pd)
                assert 0 < v <= 1.0, f"H_score({d},{pd})={v} out of (0,1]"

    def test_h_wall_always_in_range(self):
        for d in self.D_VALUES:
            v = H_wall(d)
            assert 1.0 <= v <= 2.0 + 1e-10, f"H_wall({d})={v} out of [1,2]"

    def test_h_exp_always_ge_1(self):
        for d in self.D_VALUES:
            v = H_exp(d)
            assert v >= 1.0, f"H_exp({d})={v} < 1"

    def test_trits_always_valid(self):
        """Every trit must be in {-1, 0, +1}."""
        for d in self.D_VALUES:
            for pd in self.PD_VALUES:
                tv = ternary_vector(d, pd)
                assert tv.t_score in (-1, 0, 1)
                assert tv.t_wall in (-1, 0, 1)
                assert tv.t_exp in (-1, 0, 1)

    def test_decision_always_valid(self):
        """Decision must be one of the four tiers."""
        valid = {ALLOW, QUARANTINE, ESCALATE, DENY}
        for d in self.D_VALUES:
            for pd in self.PD_VALUES:
                tv = ternary_vector(d, pd)
                dec = trit_decision(tv)
                assert dec in valid, f"Invalid decision '{dec}' at d={d}, pd={pd}"

    def test_all_three_formulas_agree_at_origin(self):
        """d*=0: H_score=1, H_wall=1, H_exp=1 — all neutral."""
        assert H_score(0.0) == 1.0
        assert H_wall(0.0) == 1.0
        assert H_exp(0.0) == 1.0

    def test_formulas_diverge_monotonically(self):
        """As d* grows, H_score falls, H_wall rises, H_exp rises."""
        prev_score = H_score(0.0)
        prev_wall = H_wall(0.0)
        prev_exp = H_exp(0.0)
        for d in [0.1, 0.5, 1.0, 2.0, 5.0]:
            assert H_score(d) < prev_score
            assert H_wall(d) > prev_wall
            assert H_exp(d) > prev_exp
            prev_score = H_score(d)
            prev_wall = H_wall(d)
            prev_exp = H_exp(d)


# Allow running standalone
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
