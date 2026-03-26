"""Tests for Phi-Lifted Poincare Projection + Fibonacci Ternary Consensus."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from primitives.phi_poincare import (
    phi_lifted_poincare_projection,
    phi_shell_radius,
    fibonacci_ternary_consensus,
    fibonacci_trust_level,
    harmonic_cost_at_shell,
    PHI, FIB_LADDER,
)


class TestPhiLiftedProjection:
    def test_zero_vector_stays_zero(self):
        v = np.array([0, 0, 0, 0, 0, 0], dtype=float)
        k = np.array([0, 1, 2, 3, 4, 5])
        result = phi_lifted_poincare_projection(v, k)
        assert np.allclose(result, 0)

    def test_result_inside_ball(self):
        v = np.array([1, -1, 1, 0, -1, 1], dtype=float)
        k = np.array([0, 1, 2, 3, 4, 5])
        result = phi_lifted_poincare_projection(v, k)
        assert np.linalg.norm(result) < 1.0

    def test_higher_k_closer_to_boundary(self):
        v = np.array([1, 0, 0, 0, 0, 0], dtype=float)
        r_low = np.linalg.norm(phi_lifted_poincare_projection(v, np.array([0, 0, 0, 0, 0, 0])))
        r_high = np.linalg.norm(phi_lifted_poincare_projection(v, np.array([5, 0, 0, 0, 0, 0])))
        assert r_high > r_low

    def test_negative_mirrors_positive(self):
        k = np.array([0, 1, 2, 3, 4, 5])
        pos = phi_lifted_poincare_projection(np.array([1, 1, 1, 1, 1, 1], dtype=float), k)
        neg = phi_lifted_poincare_projection(np.array([-1, -1, -1, -1, -1, -1], dtype=float), k)
        # Should be opposite direction, same magnitude
        assert np.allclose(np.linalg.norm(pos), np.linalg.norm(neg), atol=1e-10)


class TestPhiShellRadius:
    def test_k0_is_half(self):
        # phi^0 = 1, r = 1/(1+1) = 0.5
        assert abs(phi_shell_radius(0) - 0.5) < 1e-10

    def test_monotonically_increasing(self):
        radii = [phi_shell_radius(k) for k in range(10)]
        for i in range(1, len(radii)):
            assert radii[i] > radii[i - 1]

    def test_always_less_than_1(self):
        for k in range(20):
            assert phi_shell_radius(k) < 1.0

    def test_approaches_1(self):
        assert phi_shell_radius(20) > 0.99


class TestFibonacciConsensus:
    def test_empty_history(self):
        assert fibonacci_ternary_consensus([]) == FIB_LADDER[0]

    def test_all_positive_climbs(self):
        result = fibonacci_ternary_consensus([1, 1, 1, 1, 1])
        assert result == FIB_LADDER[5]  # 8

    def test_single_negative_drops(self):
        # Climb 5, then drop 1
        result = fibonacci_ternary_consensus([1, 1, 1, 1, 1, -1])
        assert result == FIB_LADDER[4]  # 5

    def test_neutral_holds(self):
        result_with = fibonacci_ternary_consensus([1, 1, 1, 0, 0, 0])
        result_without = fibonacci_ternary_consensus([1, 1, 1])
        assert result_with == result_without

    def test_cannot_go_below_zero(self):
        result = fibonacci_ternary_consensus([-1, -1, -1, -1])
        assert result == FIB_LADDER[0]

    def test_nonlinear_trust(self):
        # 5 positive steps: weight = 8
        # 10 positive steps: weight = 89
        w5 = fibonacci_ternary_consensus([1] * 5)
        w10 = fibonacci_ternary_consensus([1] * 10)
        assert w10 > w5 * 5  # Much more than linear scaling

    def test_asymmetric_attack_defense(self):
        # Build trust over 8 steps, then one attack
        history = [1, 1, 1, 1, 1, 1, 1, 1, -1]
        result = fibonacci_ternary_consensus(history)
        # Should be at index 7, not 8
        assert result == FIB_LADDER[7]


class TestFibonacciTrustLevel:
    def test_untrusted(self):
        result = fibonacci_trust_level([])
        assert result["level"] == "UNTRUSTED"

    def test_provisional(self):
        result = fibonacci_trust_level([1, 1, 1])
        assert result["level"] == "PROVISIONAL"

    def test_trusted(self):
        result = fibonacci_trust_level([1] * 6)
        assert result["level"] == "TRUSTED"

    def test_core(self):
        result = fibonacci_trust_level([1] * 10)
        assert result["level"] == "CORE"

    def test_demotion(self):
        # Build to CORE then get inhibited
        history = [1] * 10 + [-1] * 5
        result = fibonacci_trust_level(history)
        assert result["level"] != "CORE"


class TestHarmonicCostAtShell:
    def test_k0_cost(self):
        # At shell 0 (r=0.5), H = 4^(0.25) = sqrt(2) ≈ 1.414
        cost = harmonic_cost_at_shell(0)
        assert abs(cost - 4 ** 0.25) < 1e-6

    def test_cost_increases_with_k(self):
        costs = [harmonic_cost_at_shell(k) for k in range(6)]
        for i in range(1, len(costs)):
            assert costs[i] > costs[i - 1]

    def test_high_k_very_expensive(self):
        cost = harmonic_cost_at_shell(10)
        assert cost > 3.0  # Significant cost near boundary

    def test_matches_harmonic_wall(self):
        # H(d, R) = R^(d^2) where d = shell radius
        R = 4.0
        for k in range(6):
            r = phi_shell_radius(k)
            expected = R ** (r ** 2)
            actual = harmonic_cost_at_shell(k, R)
            assert abs(actual - expected) < 1e-10
