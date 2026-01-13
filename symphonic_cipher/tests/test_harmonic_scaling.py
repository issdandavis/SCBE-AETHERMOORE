"""
Test suite for Harmonic Scaling Law module.

Tests cover:
1. Bounded tanh form H(d*) = 1 + alpha * tanh(beta * d*)
2. Specification test vectors
3. Quantum-resistant context binding
4. Hyperbolic distance calculations
5. Security decision engine integration
6. Edge cases and numerical stability
"""

import math
import pytest
import numpy as np

from ..harmonic_scaling_law import (
    HarmonicScalingLaw,
    ScalingMode,
    PQContextCommitment,
    BehavioralRiskComponents,
    SecurityDecisionEngine,
    hyperbolic_distance_poincare,
    find_nearest_trusted_realm,
    quantum_resistant_harmonic_scaling,
    create_context_commitment,
    verify_test_vectors,
    DEFAULT_ALPHA,
    DEFAULT_BETA,
    PQ_CONTEXT_COMMITMENT_SIZE,
    TEST_VECTORS,
)


# =============================================================================
# TEST: BOUNDED TANH FORM
# =============================================================================

class TestHarmonicScalingLaw:
    """Tests for the HarmonicScalingLaw class."""

    def test_initialization_defaults(self):
        """Test default initialization."""
        law = HarmonicScalingLaw(require_pq_binding=False)
        assert law.alpha == DEFAULT_ALPHA
        assert law.beta == DEFAULT_BETA
        assert law.mode == ScalingMode.BOUNDED_TANH

    def test_initialization_custom_params(self):
        """Test custom parameter initialization."""
        law = HarmonicScalingLaw(alpha=5.0, beta=0.3, require_pq_binding=False)
        assert law.alpha == 5.0
        assert law.beta == 0.3

    def test_initialization_invalid_alpha(self):
        """Test that negative alpha raises error."""
        with pytest.raises(ValueError, match="alpha must be positive"):
            HarmonicScalingLaw(alpha=-1.0)

    def test_initialization_invalid_beta(self):
        """Test that negative beta raises error."""
        with pytest.raises(ValueError, match="beta must be positive"):
            HarmonicScalingLaw(beta=-0.5)

    def test_bounded_output_range(self):
        """Test that H is always in [1, 1 + alpha]."""
        law = HarmonicScalingLaw(alpha=10.0, beta=0.5, require_pq_binding=False)

        for d_star in [0.0, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 100.0, 1000.0]:
            H = law.compute(d_star)
            assert 1.0 <= H <= 1.0 + law.alpha, f"H={H} out of bounds for d*={d_star}"

    def test_monotonicity(self):
        """Test that H is monotonically increasing with d*."""
        law = HarmonicScalingLaw(alpha=10.0, beta=0.5, require_pq_binding=False)

        prev_H = 0.0
        for d_star in [0.0, 0.1, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 10.0]:
            H = law.compute(d_star)
            assert H >= prev_H, f"H not monotonic: H({d_star})={H} < H_prev={prev_H}"
            prev_H = H

    def test_perfect_match_at_zero(self):
        """Test that H(0) = 1 (perfect match)."""
        law = HarmonicScalingLaw(alpha=10.0, beta=0.5, require_pq_binding=False)
        H = law.compute(0.0)
        assert abs(H - 1.0) < 1e-10, f"H(0) should be 1.0, got {H}"

    def test_saturation_at_large_distance(self):
        """Test that H approaches 1 + alpha for large d*."""
        law = HarmonicScalingLaw(alpha=10.0, beta=0.5, require_pq_binding=False)
        H = law.compute(100.0)
        expected_max = 1.0 + law.alpha
        assert abs(H - expected_max) < 0.01, f"H(100) should approach {expected_max}, got {H}"

    def test_negative_distance_clamped(self):
        """Test that negative d* is clamped to 0."""
        law = HarmonicScalingLaw(alpha=10.0, beta=0.5, require_pq_binding=False)
        H = law.compute(-5.0)
        assert abs(H - 1.0) < 1e-10, f"H(-5) should be 1.0 (clamped), got {H}"


# =============================================================================
# TEST: SPECIFICATION TEST VECTORS
# =============================================================================

class TestSpecificationVectors:
    """Tests against the specification test vectors."""

    @pytest.mark.parametrize("d_star,expected_tanh,expected_H", TEST_VECTORS)
    def test_vector(self, d_star, expected_tanh, expected_H):
        """Test each specification test vector."""
        law = HarmonicScalingLaw(alpha=10.0, beta=0.5, require_pq_binding=False)
        computed_H = law.compute(d_star)
        computed_tanh = math.tanh(0.5 * d_star)

        # Allow small tolerance due to rounding in spec
        assert abs(computed_tanh - expected_tanh) < 0.01, \
            f"tanh mismatch at d*={d_star}: got {computed_tanh}, expected {expected_tanh}"
        assert abs(computed_H - expected_H) < 0.01, \
            f"H mismatch at d*={d_star}: got {computed_H}, expected {expected_H}"

    def test_verify_all_vectors(self):
        """Test the built-in vector verification function."""
        results = verify_test_vectors(tolerance=0.01)
        all_passed = all(passed for passed, _ in results)
        assert all_passed, f"Some test vectors failed: {[msg for passed, msg in results if not passed]}"


# =============================================================================
# TEST: SCALING MODES
# =============================================================================

class TestScalingModes:
    """Tests for different scaling modes."""

    def test_logarithmic_mode(self):
        """Test logarithmic scaling mode."""
        law = HarmonicScalingLaw(mode=ScalingMode.LOGARITHMIC, require_pq_binding=False)

        # log2(1 + 0) = 0, but we ensure minimum of 1.0
        H_0 = law.compute(0.0)
        assert H_0 >= 1.0

        # log2(1 + 1) = 1
        H_1 = law.compute(1.0)
        assert abs(H_1 - 1.0) < 0.01

        # log2(1 + 7) = 3
        H_7 = law.compute(7.0)
        assert abs(H_7 - 3.0) < 0.01

    def test_linear_clipped_mode(self):
        """Test linear clipped scaling mode."""
        law = HarmonicScalingLaw(
            alpha=10.0,
            mode=ScalingMode.LINEAR_CLIPPED,
            require_pq_binding=False
        )

        # H = min(1 + d*, 11)
        assert abs(law.compute(0.0) - 1.0) < 1e-10
        assert abs(law.compute(5.0) - 6.0) < 1e-10
        assert abs(law.compute(15.0) - 11.0) < 1e-10  # Clipped at 1 + alpha


# =============================================================================
# TEST: QUANTUM-RESISTANT BINDING
# =============================================================================

class TestQuantumResistantBinding:
    """Tests for PQ crypto binding."""

    def test_pq_binding_required_by_default(self):
        """Test that PQ binding is required by default."""
        law = HarmonicScalingLaw()  # require_pq_binding=True by default

        with pytest.raises(ValueError, match="PQ context commitment required"):
            law.compute(1.0)

    def test_pq_binding_with_valid_commitment(self):
        """Test computation with valid commitment."""
        law = HarmonicScalingLaw(require_pq_binding=True)
        commitment = b"\x00" * PQ_CONTEXT_COMMITMENT_SIZE
        H = law.compute(1.0, context_commitment=commitment)
        assert H > 1.0

    def test_pq_binding_with_invalid_size(self):
        """Test that invalid commitment size raises error."""
        law = HarmonicScalingLaw(require_pq_binding=True)

        with pytest.raises(ValueError, match="Invalid PQ context commitment size"):
            law.compute(1.0, context_commitment=b"\x00" * 16)

    def test_convenience_function_with_binding(self):
        """Test the standalone convenience function."""
        commitment = b"\x00" * 32
        H = quantum_resistant_harmonic_scaling(1.0, context_commitment=commitment)
        assert 1.0 <= H <= 11.0

    def test_convenience_function_invalid_commitment(self):
        """Test convenience function with invalid commitment."""
        with pytest.raises(ValueError, match="Invalid PQ context commitment"):
            quantum_resistant_harmonic_scaling(1.0, context_commitment=b"\x00" * 16)

    def test_context_commitment_creation(self):
        """Test context commitment creation."""
        commitment = create_context_commitment(
            d_star=1.5,
            behavioral_risk=0.3,
            session_id=b"test_session_123"
        )
        assert len(commitment) == 32  # SHA3-256 output

    def test_pq_context_commitment_class(self):
        """Test PQContextCommitment class."""
        context_data = b"test_context_data"
        commitment = PQContextCommitment.create(context_data)

        assert len(commitment.commitment_hash) == 32
        assert commitment.verify(context_data)
        assert not commitment.verify(b"wrong_data")


# =============================================================================
# TEST: HYPERBOLIC DISTANCE
# =============================================================================

class TestHyperbolicDistance:
    """Tests for hyperbolic distance calculations."""

    def test_distance_to_self_is_zero(self):
        """Test that distance from point to itself is zero."""
        u = np.array([0.3, 0.4])
        d = hyperbolic_distance_poincare(u, u)
        assert abs(d) < 1e-10

    def test_distance_is_symmetric(self):
        """Test that d(u, v) = d(v, u)."""
        u = np.array([0.1, 0.2])
        v = np.array([0.3, 0.4])

        d_uv = hyperbolic_distance_poincare(u, v)
        d_vu = hyperbolic_distance_poincare(v, u)

        assert abs(d_uv - d_vu) < 1e-10

    def test_distance_increases_toward_boundary(self):
        """Test that distance increases as points approach boundary."""
        origin = np.array([0.0, 0.0])

        # Points at increasing radial distances
        d1 = hyperbolic_distance_poincare(origin, np.array([0.1, 0.0]))
        d2 = hyperbolic_distance_poincare(origin, np.array([0.5, 0.0]))
        d3 = hyperbolic_distance_poincare(origin, np.array([0.9, 0.0]))

        assert d1 < d2 < d3

    def test_distance_from_origin(self):
        """Test distance from origin formula."""
        # d(0, r) = 2 * arctanh(r) for point at radius r from origin
        r = 0.5
        point = np.array([r, 0.0])
        origin = np.array([0.0, 0.0])

        d = hyperbolic_distance_poincare(origin, point)
        expected = 2 * np.arctanh(r)

        assert abs(d - expected) < 0.01

    def test_find_nearest_realm(self):
        """Test finding nearest trusted realm."""
        point = np.array([0.3, 0.3])
        realms = [
            np.array([0.1, 0.1]),  # Nearest
            np.array([0.7, 0.7]),
            np.array([-0.5, 0.0]),
        ]

        d_star, idx = find_nearest_trusted_realm(point, realms)

        assert idx == 0
        assert d_star > 0

    def test_find_nearest_realm_empty_raises(self):
        """Test that empty realm list raises error."""
        with pytest.raises(ValueError, match="At least one trusted realm"):
            find_nearest_trusted_realm(np.array([0.0, 0.0]), [])


# =============================================================================
# TEST: BEHAVIORAL RISK INTEGRATION
# =============================================================================

class TestBehavioralRiskIntegration:
    """Tests for behavioral risk component integration."""

    def test_behavioral_risk_perfect_match(self):
        """Test risk computation for perfect match."""
        components = BehavioralRiskComponents(
            D_hyp=0.0,
            C_spin=1.0,
            S_spec=1.0,
            T_temp=1.0,
            E_entropy=0.0
        )
        risk = components.compute()
        assert abs(risk) < 1e-10

    def test_behavioral_risk_maximum(self):
        """Test risk computation for maximum deviation."""
        components = BehavioralRiskComponents(
            D_hyp=1.0,
            C_spin=0.0,
            S_spec=0.0,
            T_temp=0.0,
            E_entropy=1.0
        )
        risk = components.compute()
        assert abs(risk - 1.0) < 1e-10

    def test_risk_is_bounded(self):
        """Test that risk is always in [0, 1]."""
        components = BehavioralRiskComponents(
            D_hyp=2.0,  # Out of range
            C_spin=-0.5,  # Out of range
            S_spec=1.5,  # Out of range
        )
        risk = components.compute()
        assert 0.0 <= risk <= 1.0


# =============================================================================
# TEST: SECURITY DECISION ENGINE
# =============================================================================

class TestSecurityDecisionEngine:
    """Tests for the security decision engine."""

    def test_accept_when_all_valid(self):
        """Test acceptance when crypto valid and risk below threshold."""
        engine = SecurityDecisionEngine(
            scaling_law=HarmonicScalingLaw(require_pq_binding=False),
            risk_threshold=0.7
        )

        decision, details = engine.evaluate(
            crypto_valid=True,
            behavioral_risk=0.1,  # Low risk
            d_star=0.5  # Close to trusted realm
        )

        assert decision is True
        assert details["crypto_valid"] is True
        assert details["risk_acceptable"] is True

    def test_reject_when_crypto_invalid(self):
        """Test rejection when crypto is invalid."""
        engine = SecurityDecisionEngine(
            scaling_law=HarmonicScalingLaw(require_pq_binding=False),
            risk_threshold=0.7
        )

        decision, details = engine.evaluate(
            crypto_valid=False,
            behavioral_risk=0.1,
            d_star=0.5
        )

        assert decision is False
        assert details["crypto_valid"] is False

    def test_reject_when_risk_too_high(self):
        """Test rejection when scaled risk exceeds threshold."""
        engine = SecurityDecisionEngine(
            scaling_law=HarmonicScalingLaw(alpha=10.0, require_pq_binding=False),
            risk_threshold=0.7
        )

        decision, details = engine.evaluate(
            crypto_valid=True,
            behavioral_risk=0.5,  # Moderate base risk
            d_star=5.0  # Far from trusted realm -> high H
        )

        # final_risk = 0.5 * H(5.0) ≈ 0.5 * 10.87 ≈ 5.4 > 0.7
        assert decision is False
        assert details["risk_acceptable"] is False
        assert details["final_risk"] > 0.7

    def test_details_contain_all_components(self):
        """Test that details dict contains expected keys."""
        engine = SecurityDecisionEngine(
            scaling_law=HarmonicScalingLaw(require_pq_binding=False)
        )

        _, details = engine.evaluate(
            crypto_valid=True,
            behavioral_risk=0.3,
            d_star=1.0
        )

        expected_keys = [
            "decision", "crypto_valid", "behavioral_risk", "d_star",
            "H", "final_risk", "risk_threshold", "risk_acceptable",
            "scaling_components"
        ]
        for key in expected_keys:
            assert key in details, f"Missing key: {key}"


# =============================================================================
# TEST: NUMERICAL STABILITY
# =============================================================================

class TestNumericalStability:
    """Tests for numerical stability edge cases."""

    def test_very_large_distance(self):
        """Test handling of very large distances."""
        law = HarmonicScalingLaw(alpha=10.0, beta=0.5, require_pq_binding=False)
        H = law.compute(1e10)
        assert math.isfinite(H)
        assert 1.0 <= H <= 11.0

    def test_very_small_distance(self):
        """Test handling of very small distances."""
        law = HarmonicScalingLaw(alpha=10.0, beta=0.5, require_pq_binding=False)
        H = law.compute(1e-15)
        assert math.isfinite(H)
        assert abs(H - 1.0) < 0.001

    def test_no_nan_or_inf(self):
        """Test that no NaN or Inf values are produced."""
        law = HarmonicScalingLaw(alpha=10.0, beta=0.5, require_pq_binding=False)

        test_values = [0.0, 1e-300, 1e-10, 1e-5, 0.1, 1.0, 10.0, 1e5, 1e10, 1e100]

        for d in test_values:
            H = law.compute(d)
            assert not math.isnan(H), f"NaN at d*={d}"
            assert not math.isinf(H), f"Inf at d*={d}"

    def test_hyperbolic_near_boundary(self):
        """Test hyperbolic distance near boundary of Poincare ball."""
        # Point very close to boundary
        u = np.array([0.999, 0.0])
        v = np.array([0.0, 0.0])

        d = hyperbolic_distance_poincare(u, v)
        assert math.isfinite(d)
        assert d > 0


# =============================================================================
# TEST: COMPUTE WITH COMPONENTS
# =============================================================================

class TestComputeWithComponents:
    """Tests for component breakdown output."""

    def test_component_breakdown(self):
        """Test that component breakdown contains expected values."""
        law = HarmonicScalingLaw(
            alpha=10.0,
            beta=0.5,
            require_pq_binding=False
        )

        result = law.compute_with_components(2.0)

        assert result["d_star"] == 2.0
        assert result["alpha"] == 10.0
        assert result["beta"] == 0.5
        assert result["mode"] == "tanh"
        assert result["H_min"] == 1.0
        assert result["H_max"] == 11.0
        assert 0 <= result["saturation_percent"] <= 100

    def test_saturation_percent_at_zero(self):
        """Test saturation is 0% at d*=0."""
        law = HarmonicScalingLaw(alpha=10.0, require_pq_binding=False)
        result = law.compute_with_components(0.0)
        assert abs(result["saturation_percent"]) < 0.1

    def test_saturation_percent_at_large_distance(self):
        """Test saturation approaches 100% at large d*."""
        law = HarmonicScalingLaw(alpha=10.0, require_pq_binding=False)
        result = law.compute_with_components(100.0)
        assert result["saturation_percent"] > 99.9
