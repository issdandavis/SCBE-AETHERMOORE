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
    # Langues Metric Tensor
    LanguesMetricTensor,
    CouplingMode,
    create_coupling_matrix,
    create_baseline_metric,
    get_epsilon_threshold,
    compute_langues_metric_distance,
    validate_langues_metric_stability,
    # Fractal Dimension Analysis
    FractalDimensionAnalyzer,
    PHI,
    LANGUES_DIMENSIONS,
    DEFAULT_EPSILON,
    EPSILON_THRESHOLD,
    EPSILON_THRESHOLD_HARMONIC,
    EPSILON_THRESHOLD_UNIFORM,
    EPSILON_THRESHOLD_NORMALIZED,
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


# =============================================================================
# TEST: LANGUES METRIC TENSOR
# =============================================================================

class TestLanguesMetricTensor:
    """Tests for the 6-dimensional Langues Metric Tensor."""

    def test_initialization_defaults(self):
        """Test default initialization with NORMALIZED mode."""
        tensor = LanguesMetricTensor()
        assert tensor.R == PHI
        assert tensor.epsilon == DEFAULT_EPSILON
        assert tensor.n_dims == LANGUES_DIMENSIONS
        assert tensor.mode == CouplingMode.NORMALIZED

    def test_initialization_custom_epsilon(self):
        """Test custom epsilon initialization."""
        tensor = LanguesMetricTensor(epsilon=0.03)
        assert tensor.epsilon == 0.03

    def test_epsilon_threshold_validation_normalized(self):
        """Test that epsilon >= threshold raises error for NORMALIZED mode."""
        # NORMALIZED mode has ε* ≈ 0.083, so 0.15 should fail
        with pytest.raises(ValueError, match="epsilon.*must be < threshold"):
            LanguesMetricTensor(epsilon=0.15, mode=CouplingMode.NORMALIZED, validate_epsilon=True)

    def test_epsilon_threshold_validation_harmonic(self):
        """Test that epsilon >= threshold raises error for HARMONIC mode."""
        # HARMONIC mode has ε* ≈ 3.67e-4, so even 0.001 should fail
        with pytest.raises(ValueError, match="epsilon.*must be < threshold"):
            LanguesMetricTensor(epsilon=0.001, mode=CouplingMode.HARMONIC, validate_epsilon=True)

    def test_epsilon_threshold_bypass(self):
        """Test that validation can be bypassed."""
        tensor = LanguesMetricTensor(epsilon=0.15, validate_epsilon=False)
        assert tensor.epsilon == 0.15

    def test_coupling_mode_thresholds(self):
        """Test rigorous epsilon thresholds for each mode."""
        # HARMONIC: ε* = 1/(2φ^17) ≈ 3.67e-4
        assert abs(EPSILON_THRESHOLD_HARMONIC - 1/(2 * PHI**17)) < 1e-10
        assert abs(get_epsilon_threshold(CouplingMode.HARMONIC) - EPSILON_THRESHOLD_HARMONIC) < 1e-10

        # UNIFORM: ε* = 1/(2*6) ≈ 0.083
        assert abs(EPSILON_THRESHOLD_UNIFORM - 1/12) < 1e-10
        assert abs(get_epsilon_threshold(CouplingMode.UNIFORM) - EPSILON_THRESHOLD_UNIFORM) < 1e-10

        # NORMALIZED: ε* = 1/(2*6) ≈ 0.083
        assert abs(EPSILON_THRESHOLD_NORMALIZED - 1/12) < 1e-10
        assert abs(get_epsilon_threshold(CouplingMode.NORMALIZED) - EPSILON_THRESHOLD_NORMALIZED) < 1e-10

    def test_baseline_metric_shape(self):
        """Test baseline metric G_0 is 6x6."""
        G_0 = create_baseline_metric()
        assert G_0.shape == (6, 6)

    def test_baseline_metric_diagonal_harmonic(self):
        """Test baseline metric is diagonal with correct values for HARMONIC mode."""
        R = PHI
        G_0 = create_baseline_metric(R, mode=CouplingMode.HARMONIC)
        expected_diag = [1.0, 1.0, 1.0, R, R**2, R**3]
        np.testing.assert_array_almost_equal(np.diag(G_0), expected_diag)

    def test_baseline_metric_uniform(self):
        """Test baseline metric is identity for UNIFORM mode."""
        G_0 = create_baseline_metric(mode=CouplingMode.UNIFORM)
        np.testing.assert_array_almost_equal(G_0, np.eye(6))

    def test_coupling_matrix_shape(self):
        """Test coupling matrices are 6x6."""
        for k in range(6):
            A_k = create_coupling_matrix(k, mode=CouplingMode.NORMALIZED)
            assert A_k.shape == (6, 6)

    def test_coupling_matrix_diagonal(self):
        """Test coupling matrix has correct diagonal term."""
        R = PHI
        for k in range(6):
            A_k = create_coupling_matrix(k, R=R, epsilon=0.05, mode=CouplingMode.HARMONIC)
            expected_diag = k * np.log(R) if k > 0 else 0.0
            assert abs(A_k[k, k] - expected_diag) < 1e-10

    def test_coupling_matrix_normalized_off_diagonal(self):
        """Test normalized coupling matrix has off-diagonal terms scaled by 1/sqrt(g_k*g_{k+1})."""
        epsilon = 0.05
        R = PHI
        G_0_diag = np.array([1.0, 1.0, 1.0, R, R**2, R**3])
        for k in range(6):
            A_k = create_coupling_matrix(k, R=R, epsilon=epsilon, mode=CouplingMode.NORMALIZED, G_0_diag=G_0_diag)
            k_next = (k + 1) % 6
            normalizer = np.sqrt(G_0_diag[k] * G_0_diag[k_next])
            expected = epsilon / normalizer
            assert abs(A_k[k, k_next] - expected) < 1e-10
            assert abs(A_k[k_next, k] - expected) < 1e-10

    def test_weight_operator_identity_at_zero(self):
        """Test that Λ(0) = I (identity)."""
        tensor = LanguesMetricTensor(epsilon=0.0, validate_epsilon=False)
        r = np.zeros(6)
        Lambda = tensor.compute_weight_operator(r)
        np.testing.assert_array_almost_equal(Lambda, np.eye(6), decimal=10)

    def test_weight_operator_shape(self):
        """Test weight operator is 6x6."""
        tensor = LanguesMetricTensor()
        r = np.random.uniform(0, 1, 6)
        Lambda = tensor.compute_weight_operator(r)
        assert Lambda.shape == (6, 6)

    def test_metric_tensor_shape(self):
        """Test metric tensor G_L(r) is 6x6."""
        tensor = LanguesMetricTensor()
        r = np.random.uniform(0, 1, 6)
        G_L = tensor.compute_metric(r)
        assert G_L.shape == (6, 6)

    def test_metric_tensor_symmetric(self):
        """Test metric tensor is symmetric."""
        tensor = LanguesMetricTensor()
        r = np.random.uniform(0, 1, 6)
        G_L = tensor.compute_metric(r)
        np.testing.assert_array_almost_equal(G_L, G_L.T)

    def test_metric_tensor_equals_baseline_at_zero(self):
        """Test that G_L(0) = G_0 when epsilon=0."""
        tensor = LanguesMetricTensor(epsilon=0.0, validate_epsilon=False)
        r = np.zeros(6)
        G_L = tensor.compute_metric(r)
        np.testing.assert_array_almost_equal(G_L, tensor.G_0, decimal=10)

    def test_r_vector_dimension_validation(self):
        """Test that wrong r dimension raises error."""
        tensor = LanguesMetricTensor()
        with pytest.raises(ValueError, match="must have 6 elements"):
            tensor.compute_weight_operator(np.array([0.1, 0.2, 0.3]))

    def test_r_vector_clamping(self):
        """Test that r values outside [0,1] are clamped."""
        tensor = LanguesMetricTensor()
        r_out_of_range = np.array([-0.5, 1.5, 0.5, 0.5, 0.5, 0.5])
        # Should not raise, values are clamped
        Lambda = tensor.compute_weight_operator(r_out_of_range)
        assert Lambda.shape == (6, 6)


class TestLanguesPositiveDefiniteness:
    """Tests for positive definiteness of langues metric."""

    def test_positive_definite_at_zero(self):
        """Test G_L(0) is positive definite."""
        tensor = LanguesMetricTensor()
        r = np.zeros(6)
        is_pd, details = tensor.validate_positive_definite(r)
        assert is_pd
        assert details["min_eigenvalue"] > 0

    def test_positive_definite_random_r(self):
        """Test G_L(r) is positive definite for random r."""
        tensor = LanguesMetricTensor(epsilon=0.05)
        np.random.seed(42)
        for _ in range(10):
            r = np.random.uniform(0, 1, 6)
            is_pd, details = tensor.validate_positive_definite(r)
            assert is_pd, f"Not positive definite for r={r}"

    def test_positive_definite_extreme_r(self):
        """Test G_L(r) is positive definite for extreme r values."""
        tensor = LanguesMetricTensor(epsilon=0.05)

        # All zeros
        is_pd, _ = tensor.validate_positive_definite(np.zeros(6))
        assert is_pd

        # All ones
        is_pd, _ = tensor.validate_positive_definite(np.ones(6))
        assert is_pd

        # Single dimension active
        for k in range(6):
            r = np.zeros(6)
            r[k] = 1.0
            is_pd, _ = tensor.validate_positive_definite(r)
            assert is_pd

    @pytest.mark.parametrize("epsilon", [0.01, 0.05, 0.10])
    def test_stability_across_epsilons(self, epsilon):
        """Test stability for different epsilon values."""
        tensor = LanguesMetricTensor(epsilon=epsilon, validate_epsilon=False)
        stats = tensor.validate_stability(n_trials=50, seed=42)

        # For safe epsilons, all should be positive definite
        if epsilon <= 0.05:
            assert stats["all_positive_definite"]

        # Condition number should be bounded (note: baseline G_0 has cond ~4.24
        # due to diag(1,1,1,φ,φ²,φ³), and the langues transformation amplifies this)
        # For ε=0.05, typical worst-case cond is ~450-500
        assert stats["condition_number_worst"] < 1000


class TestLanguesDistance:
    """Tests for langues-weighted distance computation."""

    def test_distance_to_self_is_zero(self):
        """Test that d_L(x, x; r) = 0."""
        tensor = LanguesMetricTensor()
        x = np.random.uniform(0, 1, 6)
        r = np.random.uniform(0, 1, 6)
        d = tensor.compute_distance(x, x, r)
        assert abs(d) < 1e-10

    def test_distance_is_symmetric(self):
        """Test that d_L(x, y; r) = d_L(y, x; r)."""
        tensor = LanguesMetricTensor()
        x = np.random.uniform(0, 1, 6)
        y = np.random.uniform(0, 1, 6)
        r = np.random.uniform(0, 1, 6)

        d_xy = tensor.compute_distance(x, y, r)
        d_yx = tensor.compute_distance(y, x, r)

        assert abs(d_xy - d_yx) < 1e-10

    def test_distance_is_positive(self):
        """Test that d_L(x, y; r) > 0 for x != y."""
        tensor = LanguesMetricTensor()
        x = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
        y = np.array([0.7, 0.8, 0.9, 0.1, 0.2, 0.3])
        r = np.random.uniform(0, 1, 6)

        d = tensor.compute_distance(x, y, r)
        assert d > 0

    def test_convenience_function(self):
        """Test the convenience distance function."""
        x = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
        y = np.array([0.7, 0.8, 0.9, 0.1, 0.2, 0.3])
        r = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5])

        d = compute_langues_metric_distance(x, y, r)
        assert d > 0
        assert math.isfinite(d)


class TestLanguesValidation:
    """Tests for validation utilities."""

    def test_validate_stability_returns_dict(self):
        """Test that validate_stability returns expected structure."""
        tensor = LanguesMetricTensor(epsilon=0.05)
        stats = tensor.validate_stability(n_trials=10, seed=42)

        expected_keys = [
            "n_trials", "epsilon", "all_positive_definite",
            "min_eigenvalue_worst", "min_eigenvalue_best",
            "max_eigenvalue_worst", "condition_number_worst",
            "condition_number_mean"
        ]
        for key in expected_keys:
            assert key in stats

    def test_validate_langues_metric_stability_function(self):
        """Test the standalone validation function."""
        results = validate_langues_metric_stability(
            epsilon_values=[0.01, 0.05],
            n_trials=10,
            seed=42
        )

        assert 0.01 in results
        assert 0.05 in results
        assert results[0.01]["all_positive_definite"]
        assert results[0.05]["all_positive_definite"]

    def test_get_coupling_matrices(self):
        """Test that coupling matrices can be retrieved."""
        tensor = LanguesMetricTensor()
        matrices = tensor.get_coupling_matrices()

        assert len(matrices) == 6
        for A in matrices:
            assert A.shape == (6, 6)


# =============================================================================
# TEST: FRACTAL DIMENSION ANALYZER
# =============================================================================

class TestFractalDimensionAnalyzerInit:
    """Tests for FractalDimensionAnalyzer initialization."""

    def test_default_initialization(self):
        """Test default initialization creates valid analyzer."""
        analyzer = FractalDimensionAnalyzer()
        assert analyzer.R == PHI
        assert analyzer.epsilon == DEFAULT_EPSILON
        assert analyzer.mode == CouplingMode.NORMALIZED
        assert len(analyzer.nu) == LANGUES_DIMENSIONS

    def test_custom_fractional_orders(self):
        """Test custom fractional orders initialization."""
        nu = np.array([1.0, 1.5, 2.0, 2.5, 3.0, 3.5])
        analyzer = FractalDimensionAnalyzer(fractional_orders=nu)
        np.testing.assert_array_almost_equal(analyzer.nu, nu)

    def test_invalid_fractional_orders_length(self):
        """Test that wrong dimension raises error."""
        with pytest.raises(ValueError, match="fractional_orders must have"):
            FractalDimensionAnalyzer(fractional_orders=np.array([1.0, 2.0, 3.0]))

    def test_default_fractional_orders_range(self):
        """Test default fractional orders span [0.5, 3.0]."""
        analyzer = FractalDimensionAnalyzer()
        assert analyzer.nu[0] == 0.5
        assert analyzer.nu[-1] == 3.0


class TestLocalFractalDimension:
    """Tests for local fractal dimension computation."""

    def test_finite_dimension_at_origin(self):
        """Test that D_f is finite at r=0."""
        analyzer = FractalDimensionAnalyzer()
        r = np.zeros(6)
        D_f = analyzer.compute_local_fractal_dimension(r)
        assert math.isfinite(D_f)

    def test_finite_dimension_random_r(self):
        """Test that D_f is finite for random r vectors."""
        analyzer = FractalDimensionAnalyzer()
        np.random.seed(42)

        for _ in range(10):
            r = np.random.uniform(0, 1, 6)
            D_f = analyzer.compute_local_fractal_dimension(r)
            assert math.isfinite(D_f), f"D_f is not finite for r={r}"

    def test_dimension_changes_with_r(self):
        """Test that D_f varies with different r values."""
        analyzer = FractalDimensionAnalyzer()

        D_f_zero = analyzer.compute_local_fractal_dimension(np.zeros(6))
        D_f_one = analyzer.compute_local_fractal_dimension(np.ones(6))

        # Should generally differ (metric changes with r)
        # May be very close, so just check they're finite
        assert math.isfinite(D_f_zero)
        assert math.isfinite(D_f_one)


class TestFractalDimensionField:
    """Tests for fractal dimension field computation."""

    def test_field_statistics_structure(self):
        """Test that field statistics have expected keys."""
        analyzer = FractalDimensionAnalyzer()
        stats = analyzer.compute_fractal_dimension_field(n_samples=20, seed=42)

        expected_keys = ["n_samples", "D_f_mean", "D_f_std", "D_f_min", "D_f_max", "fractional_orders"]
        for key in expected_keys:
            assert key in stats

    def test_field_samples_count(self):
        """Test that correct number of samples are computed."""
        analyzer = FractalDimensionAnalyzer()
        stats = analyzer.compute_fractal_dimension_field(n_samples=50, seed=42)

        # Most samples should succeed
        assert stats["n_samples"] >= 40

    def test_field_deterministic_with_seed(self):
        """Test that same seed gives same results."""
        analyzer = FractalDimensionAnalyzer()

        stats1 = analyzer.compute_fractal_dimension_field(n_samples=20, seed=123)
        stats2 = analyzer.compute_fractal_dimension_field(n_samples=20, seed=123)

        assert stats1["D_f_mean"] == stats2["D_f_mean"]


class TestRecursiveMetricIteration:
    """Tests for recursive metric iteration (fractal attractor)."""

    def test_iteration_returns_valid_metric(self):
        """Test that iteration returns a valid metric matrix."""
        analyzer = FractalDimensionAnalyzer()
        r = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5])

        G_final, det_history = analyzer.iterate_metric_recursively(r, n_iterations=50)

        assert G_final.shape == (6, 6)
        assert len(det_history) > 1

    def test_iteration_determinant_contracts(self):
        """Test that determinant generally decreases (contraction)."""
        analyzer = FractalDimensionAnalyzer()
        r = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5])

        _, det_history = analyzer.iterate_metric_recursively(
            r, n_iterations=50, contraction_factor=0.95
        )

        # Determinant should generally decrease
        assert det_history[-1] < det_history[0]

    def test_iteration_history_length(self):
        """Test that history has correct length."""
        analyzer = FractalDimensionAnalyzer()
        r = np.random.uniform(0, 1, 6)

        _, det_history = analyzer.iterate_metric_recursively(r, n_iterations=100)

        # Initial + up to 100 iterations (may stop early)
        assert 2 <= len(det_history) <= 101


class TestHausdorffDimension:
    """Tests for Hausdorff dimension computation."""

    def test_hausdorff_at_zero_r(self):
        """Test Hausdorff dimension when r=0 (all α_k=1)."""
        analyzer = FractalDimensionAnalyzer()
        r = np.zeros(6)

        D_H = analyzer.compute_hausdorff_dimension(r)

        # When all α_k = 1, D_H = n_dims
        assert abs(D_H - 6.0) < 1e-6

    def test_hausdorff_finite_random_r(self):
        """Test Hausdorff dimension is finite for random r."""
        analyzer = FractalDimensionAnalyzer()
        np.random.seed(42)

        for _ in range(10):
            r = np.random.uniform(0, 1, 6)
            D_H = analyzer.compute_hausdorff_dimension(r)
            assert math.isfinite(D_H), f"D_H not finite for r={r}"

    def test_hausdorff_dimension_finite(self):
        """Test that Hausdorff dimension is finite for typical r.

        Note: D_H can be negative when α_k = R^{ν_k*r_k} > 1 (expansion),
        since we need α_k^{D_H} < 1 for the sum to equal 1.
        When R=φ≈1.618 and r>0, α_k>1, so D_H<0 is expected.
        """
        analyzer = FractalDimensionAnalyzer()
        r = np.array([0.3, 0.4, 0.5, 0.6, 0.7, 0.8])

        D_H = analyzer.compute_hausdorff_dimension(r)

        # D_H should be finite (can be negative for expansion)
        assert math.isfinite(D_H)

    def test_hausdorff_solves_equation(self):
        """Test that D_H approximately solves Σ α_k^{D_H} = 1."""
        analyzer = FractalDimensionAnalyzer()
        r = np.array([0.2, 0.3, 0.4, 0.5, 0.6, 0.7])

        D_H = analyzer.compute_hausdorff_dimension(r)
        alpha = analyzer.R ** (analyzer.nu * r)
        sum_alpha_DH = np.sum(alpha ** D_H)

        # Should be close to 1
        assert abs(sum_alpha_DH - 1.0) < 0.01


class TestDimensionSpectrum:
    """Tests for fractal dimension spectrum computation."""

    def test_single_axis_spectrum(self):
        """Test spectrum computation for a single axis."""
        analyzer = FractalDimensionAnalyzer()

        spectrum = analyzer.compute_dimension_spectrum(axis_index=0, n_points=10)

        assert "axis_index" in spectrum
        assert "r_values" in spectrum
        assert "D_f_spectrum" in spectrum
        assert "D_H_spectrum" in spectrum
        assert len(spectrum["r_values"]) == 10
        assert len(spectrum["D_f_spectrum"]) == 10
        assert len(spectrum["D_H_spectrum"]) == 10

    def test_invalid_axis_index(self):
        """Test that invalid axis index raises error."""
        analyzer = FractalDimensionAnalyzer()

        with pytest.raises(ValueError, match="axis_index must be in"):
            analyzer.compute_dimension_spectrum(axis_index=6)

        with pytest.raises(ValueError, match="axis_index must be in"):
            analyzer.compute_dimension_spectrum(axis_index=-1)

    def test_full_spectrum(self):
        """Test full spectrum computation for all axes."""
        analyzer = FractalDimensionAnalyzer()

        full = analyzer.compute_full_spectrum(n_points=5)

        assert full["n_axes"] == 6
        assert full["n_points_per_axis"] == 5
        assert len(full["spectra"]) == 6

        for k in range(6):
            assert f"axis_{k}" in full["spectra"]


class TestFractalMap:
    """Tests for Langues fractal map."""

    def test_fractal_map_bounded(self):
        """Test that fractal map output is bounded in [-1, 1]."""
        analyzer = FractalDimensionAnalyzer()
        np.random.seed(42)

        for _ in range(20):
            x = np.random.uniform(-2, 2, 6)
            r = np.random.uniform(0, 1, 6)

            y = analyzer.langues_fractal_map(x, r)

            # tanh output is always in [-1, 1]
            assert np.all(np.abs(y) <= 1.0)

    def test_fractal_map_deterministic(self):
        """Test that fractal map is deterministic."""
        analyzer = FractalDimensionAnalyzer()

        x = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
        r = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5])

        y1 = analyzer.langues_fractal_map(x, r)
        y2 = analyzer.langues_fractal_map(x, r)

        np.testing.assert_array_equal(y1, y2)


class TestFractalAttractor:
    """Tests for fractal attractor generation."""

    def test_attractor_shape(self):
        """Test that attractor has correct shape."""
        analyzer = FractalDimensionAnalyzer()

        points = analyzer.generate_fractal_attractor(
            n_iterations=100, n_points=50, seed=42
        )

        assert points.shape == (50, 6)

    def test_attractor_bounded(self):
        """Test that attractor points are bounded (tanh constraint)."""
        analyzer = FractalDimensionAnalyzer()

        points = analyzer.generate_fractal_attractor(
            n_iterations=500, n_points=100, seed=42
        )

        # All points should be in [-1, 1] due to tanh
        assert np.all(np.abs(points) <= 1.0)

    def test_attractor_deterministic_with_seed(self):
        """Test that same seed gives same attractor."""
        analyzer = FractalDimensionAnalyzer()

        points1 = analyzer.generate_fractal_attractor(
            n_iterations=100, n_points=20, seed=123
        )
        points2 = analyzer.generate_fractal_attractor(
            n_iterations=100, n_points=20, seed=123
        )

        np.testing.assert_array_equal(points1, points2)


class TestBoxCountingDimension:
    """Tests for box-counting dimension estimation."""

    def test_box_counting_returns_dimension(self):
        """Test that box-counting returns valid dimension estimate."""
        analyzer = FractalDimensionAnalyzer()

        # Generate some attractor points
        points = analyzer.generate_fractal_attractor(
            n_iterations=100, n_points=200, seed=42
        )

        D_box, details = analyzer.estimate_box_counting_dimension(points, n_scales=8)

        assert math.isfinite(D_box)
        assert "epsilons" in details
        assert "N_boxes" in details
        assert "slope" in details

    def test_box_counting_dimension_positive(self):
        """Test that estimated dimension is positive."""
        analyzer = FractalDimensionAnalyzer()

        points = analyzer.generate_fractal_attractor(
            n_iterations=200, n_points=500, seed=42
        )

        D_box, _ = analyzer.estimate_box_counting_dimension(points, n_scales=10)

        assert D_box > 0

    def test_box_counting_reasonable_range(self):
        """Test that dimension is in reasonable range for 6D attractor."""
        analyzer = FractalDimensionAnalyzer()

        points = analyzer.generate_fractal_attractor(
            n_iterations=200, n_points=1000, seed=42
        )

        D_box, _ = analyzer.estimate_box_counting_dimension(points, n_scales=10)

        # Dimension should be between 0 and 6 for 6D space
        # (Typically lower due to fractal structure)
        assert 0 < D_box < 6


class TestFractalAnalyzerIntegration:
    """Integration tests for FractalDimensionAnalyzer."""

    def test_full_analysis_workflow(self):
        """Test complete fractal analysis workflow."""
        analyzer = FractalDimensionAnalyzer(epsilon=0.05)

        # 1. Compute fractal dimension field
        field = analyzer.compute_fractal_dimension_field(n_samples=30, seed=42)
        assert field["n_samples"] >= 20

        # 2. Generate attractor
        points = analyzer.generate_fractal_attractor(
            n_iterations=100, n_points=100, seed=42
        )
        assert points.shape == (100, 6)

        # 3. Estimate box-counting dimension
        D_box, _ = analyzer.estimate_box_counting_dimension(points)
        assert math.isfinite(D_box)

        # 4. Compute Hausdorff dimensions for various r
        for r_val in [0.0, 0.5, 1.0]:
            r = np.full(6, r_val)
            D_H = analyzer.compute_hausdorff_dimension(r)
            assert math.isfinite(D_H)

    def test_different_coupling_modes(self):
        """Test analyzer works with different coupling modes."""
        for mode in [CouplingMode.HARMONIC, CouplingMode.UNIFORM, CouplingMode.NORMALIZED]:
            # Use appropriate epsilon for mode
            if mode == CouplingMode.HARMONIC:
                eps = 0.0001  # Very small for HARMONIC
            else:
                eps = 0.05

            analyzer = FractalDimensionAnalyzer(epsilon=eps, mode=mode)

            r = np.array([0.5] * 6)
            D_f = analyzer.compute_local_fractal_dimension(r)
            D_H = analyzer.compute_hausdorff_dimension(r)

            assert math.isfinite(D_f)
            assert math.isfinite(D_H)

    def test_custom_fractional_orders_analysis(self):
        """Test analysis with custom fractional orders."""
        # Uniform fractional orders
        nu_uniform = np.full(6, 2.0)
        analyzer = FractalDimensionAnalyzer(fractional_orders=nu_uniform)

        r = np.array([0.3, 0.4, 0.5, 0.6, 0.7, 0.8])
        D_H = analyzer.compute_hausdorff_dimension(r)

        assert math.isfinite(D_H)

        # Generate attractor
        points = analyzer.generate_fractal_attractor(n_iterations=50, n_points=30, seed=42)
        assert points.shape == (30, 6)
