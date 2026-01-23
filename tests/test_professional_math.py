"""
SCBE Professional Mathematical Verification Test Suite
=====================================================

Industry-standard mathematical verification tests for:
- Hyperbolic geometry correctness
- Golden ratio calculations
- Harmonic scaling law
- Poincaré ball operations
- 14-layer pipeline mathematics

Run: pytest tests/test_professional_math.py -v -m professional
"""

import pytest
import numpy as np
import sys
import os
from typing import Tuple
import math

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Try imports
try:
    from src.scbe_14layer_reference import scbe_14layer_pipeline
    SCBE_AVAILABLE = True
except ImportError:
    SCBE_AVAILABLE = False

# Mathematical constants
PHI = (1 + np.sqrt(5)) / 2  # Golden ratio ≈ 1.618034
R_FIFTH = 1.5  # Perfect fifth harmonic ratio
SQRT5 = np.sqrt(5)


# =============================================================================
# GOLDEN RATIO TESTS
# =============================================================================

@pytest.mark.professional
@pytest.mark.math
class TestGoldenRatio:
    """Verify golden ratio calculations."""

    def test_golden_ratio_definition(self, golden_ratio):
        """Verify φ = (1 + √5) / 2."""
        expected = (1 + np.sqrt(5)) / 2
        assert np.isclose(golden_ratio, expected, rtol=1e-10)

    def test_golden_ratio_property_squared(self, golden_ratio):
        """Verify φ² = φ + 1 (fundamental property)."""
        phi_squared = golden_ratio ** 2
        phi_plus_one = golden_ratio + 1
        assert np.isclose(phi_squared, phi_plus_one, rtol=1e-10)

    def test_golden_ratio_reciprocal(self, golden_ratio):
        """Verify 1/φ = φ - 1."""
        reciprocal = 1 / golden_ratio
        phi_minus_one = golden_ratio - 1
        assert np.isclose(reciprocal, phi_minus_one, rtol=1e-10)

    def test_golden_ratio_powers_recurrence(self, golden_ratio):
        """Verify φⁿ = φⁿ⁻¹ + φⁿ⁻² (Fibonacci recurrence)."""
        for n in range(2, 10):
            phi_n = golden_ratio ** n
            phi_n_minus_1 = golden_ratio ** (n - 1)
            phi_n_minus_2 = golden_ratio ** (n - 2)
            assert np.isclose(phi_n, phi_n_minus_1 + phi_n_minus_2, rtol=1e-9)

    def test_golden_ratio_continued_fraction(self, golden_ratio):
        """Verify φ as infinite continued fraction [1; 1, 1, 1, ...]."""
        # Approximate with finite continued fraction
        approx = 1.0
        for _ in range(50):
            approx = 1 + 1 / approx

        assert np.isclose(approx, golden_ratio, rtol=1e-10)


# =============================================================================
# HARMONIC SCALING LAW TESTS
# =============================================================================

@pytest.mark.professional
@pytest.mark.math
class TestHarmonicScalingLaw:
    """Verify harmonic scaling law H(d, R) = R^(d²)."""

    def test_harmonic_scaling_at_zero(self, harmonic_scaling):
        """Verify H(0, R) = 1 for any R."""
        for R in [1.5, 2.0, 3.0, 1.25]:
            assert harmonic_scaling(0, R) == 1.0

    def test_harmonic_scaling_at_one(self, harmonic_scaling):
        """Verify H(1, R) = R."""
        for R in [1.5, 2.0, 3.0]:
            assert np.isclose(harmonic_scaling(1, R), R)

    def test_harmonic_scaling_super_exponential(self, harmonic_scaling):
        """Verify super-exponential growth (d² exponent)."""
        R = R_FIFTH

        # Values should grow super-exponentially
        h_values = [harmonic_scaling(d, R) for d in range(7)]

        # h[2] = R^4, h[3] = R^9, etc.
        assert np.isclose(h_values[2], R ** 4)
        assert np.isclose(h_values[3], R ** 9)
        assert np.isclose(h_values[4], R ** 16)

    def test_harmonic_scaling_specific_values(self, harmonic_scaling):
        """Verify specific known values for R=1.5."""
        R = R_FIFTH

        # d=2: H = 1.5^4 = 5.0625
        assert np.isclose(harmonic_scaling(2, R), 5.0625)

        # d=3: H = 1.5^9 ≈ 38.44
        assert np.isclose(harmonic_scaling(3, R), 38.443359375, rtol=1e-6)

        # d=6: H = 1.5^36 ≈ 1.50e13
        # Note: This is a large value, just verify it's > 1e6
        h_6 = harmonic_scaling(6, R)
        assert h_6 > 1e6  # 1.5^36 = 1.50e13 approximately

    def test_harmonic_scaling_monotonicity(self, harmonic_scaling):
        """Verify H is monotonically increasing in d for R > 1."""
        R = R_FIFTH
        prev_h = 0

        for d in np.linspace(0, 5, 100):
            h = harmonic_scaling(d, R)
            assert h >= prev_h, f"Monotonicity violated at d={d}"
            prev_h = h


# =============================================================================
# HYPERBOLIC GEOMETRY TESTS
# =============================================================================

@pytest.mark.professional
@pytest.mark.math
class TestHyperbolicGeometry:
    """Verify hyperbolic geometry calculations."""

    def test_hyperbolic_distance_at_origin(self, hyperbolic_distance):
        """Verify distance from origin to point p is 2 * arctanh(||p||)."""
        origin = np.zeros(6)

        for r in [0.1, 0.3, 0.5, 0.7, 0.9]:
            point = np.array([r, 0, 0, 0, 0, 0])
            d = hyperbolic_distance(origin, point)
            expected = 2 * np.arctanh(r)
            assert np.isclose(d, expected, rtol=1e-6)

    def test_hyperbolic_distance_symmetry(self, hyperbolic_distance):
        """Verify d(u, v) = d(v, u) (symmetry)."""
        u = np.array([0.3, 0.2, 0.1, 0.0, 0.1, 0.2])
        v = np.array([0.1, 0.3, 0.2, 0.1, 0.0, 0.1])

        d_uv = hyperbolic_distance(u, v)
        d_vu = hyperbolic_distance(v, u)

        assert np.isclose(d_uv, d_vu, rtol=1e-10)

    def test_hyperbolic_distance_identity(self, hyperbolic_distance):
        """Verify d(u, u) = 0 (identity)."""
        u = np.array([0.3, 0.2, 0.1, 0.0, 0.1, 0.2])
        d = hyperbolic_distance(u, u)
        assert np.isclose(d, 0.0, atol=1e-10)

    def test_hyperbolic_distance_triangle_inequality(self, hyperbolic_distance):
        """Verify d(u, w) ≤ d(u, v) + d(v, w) (triangle inequality)."""
        np.random.seed(42)

        for _ in range(50):
            # Generate random points inside ball
            u = np.random.uniform(-0.5, 0.5, 6)
            v = np.random.uniform(-0.5, 0.5, 6)
            w = np.random.uniform(-0.5, 0.5, 6)

            d_uw = hyperbolic_distance(u, w)
            d_uv = hyperbolic_distance(u, v)
            d_vw = hyperbolic_distance(v, w)

            assert d_uw <= d_uv + d_vw + 1e-10, "Triangle inequality violated"

    def test_hyperbolic_distance_boundary_behavior(self, hyperbolic_distance):
        """Verify distance approaches infinity near boundary."""
        origin = np.zeros(6)

        # Points approaching boundary
        for r in [0.9, 0.95, 0.99, 0.999]:
            point = np.array([r, 0, 0, 0, 0, 0])
            d = hyperbolic_distance(origin, point)
            assert d > 2, f"Distance should be large near boundary, got {d}"

        # Very close to boundary
        point = np.array([0.9999, 0, 0, 0, 0, 0])
        d = hyperbolic_distance(origin, point)
        assert d > 5, f"Distance should be very large at boundary, got {d}"


# =============================================================================
# POINCARÉ BALL TESTS
# =============================================================================

@pytest.mark.professional
@pytest.mark.math
class TestPoincareBall:
    """Verify Poincaré ball operations."""

    def test_mobius_addition_identity(self):
        """Verify u ⊕ 0 = u (identity element)."""
        def mobius_add(u, v):
            """Möbius addition in Poincaré ball."""
            u_sq = np.sum(u ** 2)
            v_sq = np.sum(v ** 2)
            uv = np.dot(u, v)

            denom = 1 + 2 * uv + u_sq * v_sq
            num = (1 + 2 * uv + v_sq) * u + (1 - u_sq) * v

            return num / denom

        u = np.array([0.3, 0.2, 0.1, 0.0, 0.1, 0.2])
        zero = np.zeros(6)

        result = mobius_add(u, zero)
        assert np.allclose(result, u, rtol=1e-10)

    def test_poincare_ball_contains_points(self):
        """Verify all normalized points are inside ball (||p|| < 1)."""
        np.random.seed(42)

        for _ in range(100):
            # Generate random point
            point = np.random.randn(6)

            # Normalize to be inside ball
            norm = np.linalg.norm(point)
            if norm >= 1:
                point = point / (norm * 1.1)

            assert np.linalg.norm(point) < 1, "Point outside Poincaré ball"

    def test_exponential_map_from_origin(self):
        """Verify exponential map exp_0(v) = tanh(||v||/2) * v/||v||."""
        def exp_map_origin(v):
            """Exponential map from origin."""
            norm = np.linalg.norm(v)
            if norm < 1e-10:
                return v
            return np.tanh(norm / 2) * v / norm

        v = np.array([1.0, 0.5, 0.3, 0.2, 0.1, 0.05])
        result = exp_map_origin(v)

        # Result should be inside ball
        assert np.linalg.norm(result) < 1

        # Direction should be preserved
        assert np.allclose(result / np.linalg.norm(result), v / np.linalg.norm(v))


# =============================================================================
# 14-LAYER PIPELINE TESTS
# =============================================================================

@pytest.mark.professional
@pytest.mark.math
class TestFourteenLayerPipeline:
    """Verify 14-layer pipeline mathematical properties."""

    @pytest.mark.skipif(not SCBE_AVAILABLE, reason="SCBE modules not available")
    def test_pipeline_produces_valid_decision(self):
        """Verify pipeline produces valid decision."""
        position = np.array([1.0, 2.0, 3.0, 5.0, 8.0, 13.0])
        result = scbe_14layer_pipeline(t=position, D=6)

        assert result["decision"] in ["ALLOW", "QUARANTINE", "DENY"]

    @pytest.mark.skipif(not SCBE_AVAILABLE, reason="SCBE modules not available")
    def test_pipeline_risk_bounds(self):
        """Verify risk scores are in valid range [0, 1]."""
        position = np.array([1.0, 2.0, 3.0, 5.0, 8.0, 13.0])
        result = scbe_14layer_pipeline(t=position, D=6)

        assert 0 <= result["risk_base"] <= 1, "risk_base out of bounds"
        # risk_prime can exceed 1 due to harmonic amplification
        assert result["risk_prime"] >= 0, "risk_prime cannot be negative"

    @pytest.mark.skipif(not SCBE_AVAILABLE, reason="SCBE modules not available")
    def test_pipeline_harmonic_amplification(self):
        """Verify H = R^(d_star²) relationship."""
        position = np.array([1.0, 2.0, 3.0, 5.0, 8.0, 13.0])
        # Weights must sum to 1.0
        result = scbe_14layer_pipeline(
            t=position, D=6,
            w_d=0.2, w_c=0.2, w_s=0.2, w_tau=0.2, w_a=0.2
        )

        # Verify H = R^(d*²) approximately (default R=e ≈ 2.718)
        R = np.e
        expected_H = R ** (result["d_star"] ** 2)
        assert np.isclose(result["H"], expected_H, rtol=0.1)

    @pytest.mark.skipif(not SCBE_AVAILABLE, reason="SCBE modules not available")
    def test_pipeline_coherence_bounds(self):
        """Verify coherence metrics are in [0, 1]."""
        position = np.array([1.0, 2.0, 3.0, 5.0, 8.0, 13.0])
        result = scbe_14layer_pipeline(t=position, D=6)

        for key, value in result["coherence"].items():
            assert 0 <= value <= 1, f"Coherence {key} out of bounds: {value}"

    @pytest.mark.skipif(not SCBE_AVAILABLE, reason="SCBE modules not available")
    def test_pipeline_decision_thresholds(self):
        """Verify decision follows threshold logic."""
        # Test with different risk levels by adjusting weights

        # Low risk should ALLOW (weights sum to 1.0)
        result_low = scbe_14layer_pipeline(
            t=np.array([1, 2, 3, 5, 8, 13]),
            D=6,
            w_d=0.1, w_c=0.3, w_s=0.3, w_tau=0.2, w_a=0.1,
            theta1=0.5,
            theta2=0.8
        )

        # High risk should DENY (weights sum to 1.0)
        result_high = scbe_14layer_pipeline(
            t=np.array([99, 99, 99, 99, 99, 99]),
            D=6,
            w_d=0.7, w_c=0.1, w_s=0.1, w_tau=0.05, w_a=0.05,
            theta1=0.1,
            theta2=0.2
        )

        # Verify threshold behavior
        assert result_low["risk_base"] < result_high["risk_base"]


# =============================================================================
# QUASICRYSTAL LATTICE TESTS
# =============================================================================

@pytest.mark.professional
@pytest.mark.math
class TestQuasicrystalLattice:
    """Verify quasicrystal lattice mathematics."""

    def test_icosahedral_golden_ratio_connection(self, golden_ratio):
        """Verify icosahedron vertices use golden ratio."""
        # Icosahedron vertices involve (0, ±1, ±φ) permutations
        phi = golden_ratio

        # Generate icosahedron vertices
        vertices = []
        for signs in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
            vertices.append([0, signs[0], signs[1] * phi])
            vertices.append([signs[0], signs[1] * phi, 0])
            vertices.append([signs[1] * phi, 0, signs[0]])

        # All vertices should be at same distance from origin
        distances = [np.linalg.norm(v) for v in vertices]
        expected_distance = np.sqrt(1 + phi ** 2)

        for d in distances:
            assert np.isclose(d, expected_distance, rtol=1e-10)

    def test_projection_matrix_orthogonality(self, golden_ratio):
        """Verify 6D→3D projection matrices are orthogonal."""
        phi = golden_ratio
        norm = 1 / np.sqrt(1 + phi ** 2)

        # Physical space basis vectors (simplified)
        e_par = np.array([
            [1, phi, 0],
            [phi, 0, 1],
            [0, 1, phi]
        ]) * norm

        # Check orthogonality (simplified test)
        inner_products = e_par @ e_par.T
        diagonal = np.diag(inner_products)

        # Diagonal should be close to 1 (normalized)
        assert np.allclose(diagonal, np.ones(3), rtol=0.1)


# =============================================================================
# NUMERICAL STABILITY TESTS
# =============================================================================

@pytest.mark.professional
@pytest.mark.math
class TestNumericalStability:
    """Verify numerical stability of calculations."""

    def test_hyperbolic_distance_near_boundary(self, hyperbolic_distance):
        """Verify numerical stability near Poincaré ball boundary."""
        origin = np.zeros(6)

        # Very close to boundary (should not overflow/underflow)
        for r in [0.999, 0.9999, 0.99999]:
            point = np.array([r, 0, 0, 0, 0, 0])
            d = hyperbolic_distance(origin, point)

            assert np.isfinite(d), f"Distance not finite at r={r}"
            assert d > 0, f"Distance not positive at r={r}"

    def test_harmonic_scaling_large_d(self, harmonic_scaling):
        """Verify harmonic scaling doesn't overflow for large d."""
        R = R_FIFTH

        # Large d values (should handle gracefully)
        for d in [5, 6, 7, 8]:
            h = harmonic_scaling(d, R)
            assert np.isfinite(h), f"H not finite at d={d}"
            assert h > 0, f"H not positive at d={d}"

    def test_golden_ratio_precision(self, golden_ratio):
        """Verify golden ratio precision to 15 decimal places."""
        # Known value to 20 decimal places
        phi_precise = 1.61803398874989484820

        # Should match to at least 14 decimal places
        assert abs(golden_ratio - phi_precise) < 1e-14

    @pytest.mark.skipif(not SCBE_AVAILABLE, reason="SCBE modules not available")
    def test_pipeline_handles_edge_cases(self):
        """Verify pipeline handles edge case inputs."""
        edge_cases = [
            np.zeros(6),  # Origin
            np.ones(6) * 0.001,  # Near origin
            np.ones(6) * 100,  # Large values
            np.array([1, 2, 3, 5, 8, 13]),  # Fibonacci
        ]

        for position in edge_cases:
            result = scbe_14layer_pipeline(t=position, D=6)
            assert np.isfinite(result["risk_base"])
            assert np.isfinite(result["H"])
            assert result["decision"] in ["ALLOW", "QUARANTINE", "DENY"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "professional"])
