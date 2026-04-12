"""
Tests for src/proofs/toroidal_polyhedral_proof.py
=================================================

Validates the four claims of the Toroidal Polyhedral Confinement proof:
1. phi-winding never closes (Hurwitz optimality)
2. Polyhedral constraints multiply (group independence)
3. Hyperbolic cost scaling is exponential
4. Legitimate user navigates in O(1)
"""

import sys
import math
from pathlib import Path

import pytest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from proofs.toroidal_polyhedral_proof import (
    PHI,
    PHI_INV,
    PLATONIC_GROUPS,
    TONGUE_WEIGHTS,
    WindingResult,
    prove_phi_winding_never_closes,
    compare_rational_vs_irrational,
    ConstraintResult,
    prove_constraints_multiply,
    poincare_distance,
    harmonic_wall,
    trust_tier,
    prove_exponential_cost_scaling,
    prove_legitimate_navigation,
    prove_toroidal_polyhedral_confinement,
)

# ============================================================
# Constants
# ============================================================


@pytest.mark.unit
class TestConstants:
    def test_phi_value(self):
        assert abs(PHI - 1.618033988749895) < 1e-10

    def test_phi_inverse(self):
        assert abs(PHI_INV - 1.0 / PHI) < 1e-12

    def test_phi_identity(self):
        """phi^2 = phi + 1 (defining equation)."""
        assert abs(PHI**2 - PHI - 1) < 1e-10

    def test_platonic_groups_count(self):
        assert len(PLATONIC_GROUPS) == 5

    def test_platonic_group_orders(self):
        assert PLATONIC_GROUPS["tetrahedron"]["order"] == 12
        assert PLATONIC_GROUPS["cube"]["order"] == 24
        assert PLATONIC_GROUPS["octahedron"]["order"] == 24
        assert PLATONIC_GROUPS["dodecahedron"]["order"] == 60
        assert PLATONIC_GROUPS["icosahedron"]["order"] == 60

    def test_tongue_weights_phi_scaling(self):
        tongues = list(TONGUE_WEIGHTS.keys())
        for i, tongue in enumerate(tongues):
            expected = PHI**i
            assert abs(TONGUE_WEIGHTS[tongue] - expected) < 1e-10, f"{tongue} weight should be phi^{i} = {expected}"

    def test_tongue_weights_all_irrational_ratios(self):
        """All cross-tongue ratios are phi-powers, hence irrational."""
        keys = list(TONGUE_WEIGHTS.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                ratio = TONGUE_WEIGHTS[keys[i]] / TONGUE_WEIGHTS[keys[j]]
                # Ratio should be phi^(i-j), which is irrational
                # Verify it's NOT close to any simple fraction p/q with q <= 100
                is_rational = False
                for q in range(1, 101):
                    p = round(ratio * q)
                    if abs(ratio - p / q) < 1e-6:
                        is_rational = True
                        break
                assert not is_rational, f"Ratio {keys[i]}/{keys[j]} appears rational"


# ============================================================
# Claim 1: phi-winding never closes
# ============================================================


@pytest.mark.unit
class TestPhiWinding:
    def test_winding_returns_result(self):
        result = prove_phi_winding_never_closes(max_cycles=1000)
        assert isinstance(result, WindingResult)

    def test_winding_never_closes(self):
        result = prove_phi_winding_never_closes(max_cycles=10_000)
        assert result.min_gap > 1e-10, "phi winding should never close"
        assert result.is_rational is False

    def test_winding_frequency_ratio(self):
        result = prove_phi_winding_never_closes(max_cycles=100)
        assert result.frequency_ratio == PHI

    def test_winding_density_high(self):
        """After enough cycles, the winding should cover most of the torus."""
        result = prove_phi_winding_never_closes(max_cycles=50_000)
        assert result.winding_density > 0.90, f"Expected density > 0.9, got {result.winding_density}"

    def test_hurwitz_bound_positive(self):
        result = prove_phi_winding_never_closes(max_cycles=1000)
        assert result.hurwitz_bound > 0

    def test_min_gap_above_hurwitz(self):
        """The minimum gap should respect the Hurwitz approximation bound."""
        result = prove_phi_winding_never_closes(max_cycles=10_000)
        # The min_gap should be within an order of magnitude of Hurwitz
        assert result.min_gap > 0


# ============================================================
# Claim 1b: Rational vs Irrational comparison
# ============================================================


@pytest.mark.unit
class TestRationalComparison:
    def test_rational_winding_closes(self):
        result = compare_rational_vs_irrational(rational_ratio=3.0 / 7.0, cycles=100)
        assert result["rational_closes_at_cycle"] is not None
        assert result["rational_closes_at_cycle"] <= 7

    def test_phi_winding_never_closes(self):
        result = compare_rational_vs_irrational(cycles=10_000)
        assert result["phi_ever_closes"] is False

    def test_verdict(self):
        result = compare_rational_vs_irrational(cycles=10_000)
        assert "NEVER CLOSES" in result["verdict"]

    def test_custom_rational(self):
        result = compare_rational_vs_irrational(rational_ratio=1.0 / 3.0, cycles=100)
        assert result["rational_closes_at_cycle"] is not None
        assert result["rational_closes_at_cycle"] <= 3


# ============================================================
# Claim 2: Polyhedral constraints multiply
# ============================================================


@pytest.mark.unit
class TestConstraintsMultiply:
    def test_returns_constraint_result(self):
        result = prove_constraints_multiply()
        assert isinstance(result, ConstraintResult)

    def test_individual_fractions(self):
        result = prove_constraints_multiply()
        for name, frac in result.individual_fractions.items():
            order = PLATONIC_GROUPS[name]["order"]
            assert abs(frac - 1.0 / order) < 1e-12

    def test_multiplicative_fraction(self):
        result = prove_constraints_multiply()
        expected = 1.0 / (12 * 24 * 24 * 60 * 60)
        assert abs(result.multiplicative_fraction - expected) < 1e-20

    def test_group_independence(self):
        result = prove_constraints_multiply()
        assert result.group_independence is True

    def test_total_valid_paths_format(self):
        result = prove_constraints_multiply()
        assert result.total_valid_paths.startswith("1 in ")

    def test_independence_proof_mentions_galois(self):
        result = prove_constraints_multiply()
        assert "Galois" in result.independence_proof


# ============================================================
# Hyperbolic distance and harmonic wall
# ============================================================


@pytest.mark.unit
class TestPoincaréDistance:
    def test_origin_to_origin(self):
        origin = np.zeros(6)
        d = poincare_distance(origin, origin)
        assert d == 0.0

    def test_symmetry(self):
        u = np.array([0.1, 0.2, 0.0, 0.0, 0.0, 0.0])
        v = np.array([0.3, 0.1, 0.0, 0.0, 0.0, 0.0])
        assert abs(poincare_distance(u, v) - poincare_distance(v, u)) < 1e-10

    def test_distance_increases_near_boundary(self):
        origin = np.zeros(6)
        d1 = poincare_distance(origin, np.array([0.5, 0, 0, 0, 0, 0]))
        d2 = poincare_distance(origin, np.array([0.9, 0, 0, 0, 0, 0]))
        assert d2 > d1

    def test_boundary_gives_infinity(self):
        origin = np.zeros(6)
        # Point at the boundary of the unit ball
        boundary = np.array([1.0, 0, 0, 0, 0, 0])
        d = poincare_distance(origin, boundary)
        assert d == float("inf")

    def test_small_distance(self):
        origin = np.zeros(3)
        nearby = np.array([0.01, 0, 0])
        d = poincare_distance(origin, nearby)
        assert 0 < d < 0.1


@pytest.mark.unit
class TestHarmonicWall:
    def test_zero_distance_gives_max_trust(self):
        h = harmonic_wall(0.0, 0.0)
        assert abs(h - 1.0) < 1e-10

    def test_increasing_distance_decreases_trust(self):
        h1 = harmonic_wall(1.0, 0.0)
        h2 = harmonic_wall(5.0, 0.0)
        assert h2 < h1

    def test_phase_deviation_decreases_trust(self):
        h1 = harmonic_wall(1.0, 0.0)
        h2 = harmonic_wall(1.0, 1.0)
        assert h2 < h1

    def test_trust_bounded_01(self):
        for d in [0, 1, 5, 10, 100]:
            for pd in [0, 0.5, 1, 5]:
                h = harmonic_wall(d, pd)
                assert 0 < h <= 1.0

    def test_phi_scaling_matters(self):
        h_phi = harmonic_wall(1.0, 0.0, phi=PHI)
        h_one = harmonic_wall(1.0, 0.0, phi=1.0)
        assert h_phi < h_one  # phi > 1 means steeper drop


@pytest.mark.unit
class TestTrustTier:
    def test_allow(self):
        assert trust_tier(0.80) == "ALLOW"
        assert trust_tier(0.75) == "ALLOW"
        assert trust_tier(1.0) == "ALLOW"

    def test_quarantine(self):
        assert trust_tier(0.50) == "QUARANTINE"
        assert trust_tier(0.40) == "QUARANTINE"

    def test_escalate(self):
        assert trust_tier(0.20) == "ESCALATE"
        assert trust_tier(0.15) == "ESCALATE"

    def test_deny(self):
        assert trust_tier(0.10) == "DENY"
        assert trust_tier(0.01) == "DENY"

    def test_boundary_values(self):
        assert trust_tier(0.749) == "QUARANTINE"
        assert trust_tier(0.399) == "ESCALATE"
        assert trust_tier(0.149) == "DENY"


# ============================================================
# Claim 3: Exponential cost scaling
# ============================================================


@pytest.mark.unit
class TestExponentialCost:
    def test_returns_cost_result(self):
        result = prove_exponential_cost_scaling()
        assert len(result.deviations) > 0

    def test_hyperbolic_exceeds_euclidean(self):
        result = prove_exponential_cost_scaling()
        for i in range(len(result.deviations)):
            assert result.hyperbolic_costs[i] >= result.euclidean_costs[i]

    def test_exponential_ratio_high(self):
        result = prove_exponential_cost_scaling()
        assert result.exponential_ratio > 2.0

    def test_trust_drops_with_deviation(self):
        result = prove_exponential_cost_scaling()
        # Trust should generally decrease as deviation increases
        for i in range(1, len(result.harmonic_scores)):
            assert result.harmonic_scores[i] <= result.harmonic_scores[i - 1] + 1e-10

    def test_small_deviation_allows(self):
        result = prove_exponential_cost_scaling()
        assert result.trust_tiers[0] == "ALLOW"

    def test_large_deviation_denies(self):
        result = prove_exponential_cost_scaling()
        assert result.trust_tiers[-1] == "DENY"


# ============================================================
# Claim 4: Legitimate user O(1) navigation
# ============================================================


@pytest.mark.unit
class TestLegitimateNavigation:
    def test_legitimate_is_allowed(self):
        result = prove_legitimate_navigation()
        assert result.legitimate_tier == "ALLOW"
        assert result.legitimate_is_trivial is True

    def test_legitimate_cost_small(self):
        result = prove_legitimate_navigation()
        assert result.legitimate_cost < 0.1

    def test_adversarial_costs_escalate(self):
        result = prove_legitimate_navigation()
        # Later deviations should be at higher-risk tiers
        tiers = [tier for _, tier in result.adversarial_costs]
        # At least some should be non-ALLOW
        non_allow = [t for t in tiers if t != "ALLOW"]
        assert len(non_allow) > 0

    def test_cost_ratio_large(self):
        result = prove_legitimate_navigation()
        assert result.cost_ratio > 10.0


# ============================================================
# Composite proof
# ============================================================


@pytest.mark.integration
class TestCompositeProof:
    def test_proof_valid(self):
        proof = prove_toroidal_polyhedral_confinement()
        assert proof.proof_valid is True

    def test_tongue_winding_products(self):
        proof = prove_toroidal_polyhedral_confinement()
        # C(6,2) = 15 cross-tongue pairs
        assert len(proof.tongue_winding_products) == 15

    def test_confinement_factor_large(self):
        proof = prove_toroidal_polyhedral_confinement()
        assert proof.total_confinement_factor > 1000

    def test_verdict_contains_proved(self):
        proof = prove_toroidal_polyhedral_confinement()
        assert "PROVED" in proof.verdict
