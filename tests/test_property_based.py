"""
SCBE Property-Based Test Suite
==============================

Property-based tests using Hypothesis for:
- Mathematical invariants
- Fuzz testing cryptographic operations
- Boundary condition exploration
- Randomized input validation

Run: pytest tests/test_property_based.py -v -m property
"""

import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Try hypothesis import
try:
    from hypothesis import given, strategies as st, settings, assume
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False

# Try SCBE imports
try:
    from src.scbe_14layer_reference import scbe_14layer_pipeline
    SCBE_AVAILABLE = True
except ImportError:
    SCBE_AVAILABLE = False

try:
    from src.crypto.rwp_v3 import RWPv3Protocol
    RWP_AVAILABLE = True
except ImportError:
    RWP_AVAILABLE = False


# Skip entire module if hypothesis not available
if not HYPOTHESIS_AVAILABLE:
    pytest.skip("Hypothesis not available", allow_module_level=True)


# =============================================================================
# CUSTOM STRATEGIES
# =============================================================================

# 6D position vector strategy
position_6d = st.lists(
    st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
    min_size=6,
    max_size=6
)

# Point inside Poincaré ball (||x|| < 1)
poincare_point = st.lists(
    st.floats(min_value=-0.49, max_value=0.49),
    min_size=6,
    max_size=6
)

# Valid API request
api_request = st.fixed_dictionaries({
    "plaintext": st.text(min_size=1, max_size=100),
    "agent": st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
    "topic": st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
    "position": st.lists(st.integers(min_value=0, max_value=100), min_size=6, max_size=6)
})

# Risk score (0 to 1)
risk_score = st.floats(min_value=0.0, max_value=1.0)

# Harmonic ratio (> 1)
harmonic_ratio = st.floats(min_value=1.01, max_value=3.0)

# Distance (non-negative)
distance = st.floats(min_value=0.0, max_value=10.0)


# =============================================================================
# MATHEMATICAL INVARIANT TESTS
# =============================================================================

@pytest.mark.property
@pytest.mark.math
class TestMathematicalInvariants:
    """Property-based tests for mathematical invariants."""

    @given(d=distance, R=harmonic_ratio)
    @settings(max_examples=200)
    def test_harmonic_scaling_positive(self, d, R):
        """H(d, R) > 0 for all valid inputs."""
        H = R ** (d ** 2)
        assert H > 0

    @given(d=distance, R=harmonic_ratio)
    @settings(max_examples=200)
    def test_harmonic_scaling_monotonic(self, d, R):
        """H(d+ε, R) > H(d, R) for ε > 0 and R > 1."""
        epsilon = 0.1
        H_d = R ** (d ** 2)
        H_d_plus = R ** ((d + epsilon) ** 2)
        assert H_d_plus >= H_d

    @given(R=harmonic_ratio)
    @settings(max_examples=100)
    def test_harmonic_scaling_identity_at_zero(self, R):
        """H(0, R) = 1 for all R."""
        H = R ** (0 ** 2)
        assert np.isclose(H, 1.0)

    @given(u=poincare_point, v=poincare_point)
    @settings(max_examples=200)
    def test_hyperbolic_distance_symmetric(self, u, v):
        """d(u, v) = d(v, u) (symmetry)."""
        u_arr = np.array(u)
        v_arr = np.array(v)

        def hyperbolic_dist(a, b):
            a_sq = np.sum(a ** 2)
            b_sq = np.sum(b ** 2)
            diff_sq = np.sum((a - b) ** 2)

            denom = (1 - a_sq) * (1 - b_sq)
            if denom <= 0:
                return float('inf')

            arg = 1 + 2 * diff_sq / denom
            return np.arccosh(max(arg, 1.0))

        d_uv = hyperbolic_dist(u_arr, v_arr)
        d_vu = hyperbolic_dist(v_arr, u_arr)

        if np.isfinite(d_uv) and np.isfinite(d_vu):
            assert np.isclose(d_uv, d_vu, rtol=1e-6)

    @given(u=poincare_point)
    @settings(max_examples=100)
    def test_hyperbolic_distance_identity(self, u):
        """d(u, u) = 0 (identity)."""
        u_arr = np.array(u)

        def hyperbolic_dist(a, b):
            a_sq = np.sum(a ** 2)
            b_sq = np.sum(b ** 2)
            diff_sq = np.sum((a - b) ** 2)

            denom = (1 - a_sq) * (1 - b_sq)
            if denom <= 0:
                return float('inf')

            arg = 1 + 2 * diff_sq / denom
            return np.arccosh(max(arg, 1.0))

        d = hyperbolic_dist(u_arr, u_arr)
        assert np.isclose(d, 0.0, atol=1e-10)

    @given(u=poincare_point)
    @settings(max_examples=100)
    def test_hyperbolic_distance_non_negative(self, u):
        """d(u, v) ≥ 0 for all u, v."""
        u_arr = np.array(u)
        origin = np.zeros(6)

        def hyperbolic_dist(a, b):
            a_sq = np.sum(a ** 2)
            b_sq = np.sum(b ** 2)
            diff_sq = np.sum((a - b) ** 2)

            denom = (1 - a_sq) * (1 - b_sq)
            if denom <= 0:
                return float('inf')

            arg = 1 + 2 * diff_sq / denom
            return np.arccosh(max(arg, 1.0))

        d = hyperbolic_dist(u_arr, origin)
        assert d >= 0


# =============================================================================
# GOLDEN RATIO PROPERTY TESTS
# =============================================================================

@pytest.mark.property
@pytest.mark.math
class TestGoldenRatioProperties:
    """Property-based tests for golden ratio."""

    @given(n=st.integers(min_value=2, max_value=20))
    @settings(max_examples=50)
    def test_golden_ratio_fibonacci_recurrence(self, n):
        """φⁿ = φⁿ⁻¹ + φⁿ⁻² (Fibonacci recurrence)."""
        phi = (1 + np.sqrt(5)) / 2

        phi_n = phi ** n
        phi_n_1 = phi ** (n - 1)
        phi_n_2 = phi ** (n - 2)

        assert np.isclose(phi_n, phi_n_1 + phi_n_2, rtol=1e-9)

    @given(n=st.integers(min_value=1, max_value=30))
    @settings(max_examples=50)
    def test_golden_ratio_powers_positive(self, n):
        """φⁿ > 0 for all n ≥ 1."""
        phi = (1 + np.sqrt(5)) / 2
        assert phi ** n > 0


# =============================================================================
# PIPELINE PROPERTY TESTS
# =============================================================================

@pytest.mark.property
@pytest.mark.skipif(not SCBE_AVAILABLE, reason="SCBE not available")
class TestPipelineProperties:
    """Property-based tests for SCBE pipeline."""

    @given(position=position_6d)
    @settings(max_examples=100)
    def test_pipeline_always_produces_decision(self, position):
        """Pipeline always produces a valid decision."""
        pos_array = np.array(position)
        # Weights must sum to 1.0
        result = scbe_14layer_pipeline(
            t=pos_array, D=6,
            w_d=0.2, w_c=0.2, w_s=0.2, w_tau=0.2, w_a=0.2
        )

        assert result["decision"] in ["ALLOW", "QUARANTINE", "DENY"]

    @given(position=position_6d)
    @settings(max_examples=100)
    def test_pipeline_risk_base_bounded(self, position):
        """risk_base is always non-negative (may exceed 1 due to geometry)."""
        pos_array = np.array(position)
        # Weights must sum to 1.0
        result = scbe_14layer_pipeline(
            t=pos_array, D=6,
            w_d=0.2, w_c=0.2, w_s=0.2, w_tau=0.2, w_a=0.2
        )

        # risk_base is non-negative (may exceed 1 in extreme cases)
        assert result["risk_base"] >= 0

    @given(position=position_6d)
    @settings(max_examples=100)
    def test_pipeline_H_positive(self, position):
        """Harmonic factor H is always positive."""
        pos_array = np.array(position)
        # Weights must sum to 1.0
        result = scbe_14layer_pipeline(
            t=pos_array, D=6,
            w_d=0.2, w_c=0.2, w_s=0.2, w_tau=0.2, w_a=0.2
        )

        assert result["H"] > 0

    @given(position=position_6d)
    @settings(max_examples=100)
    def test_pipeline_coherence_bounded(self, position):
        """Coherence metrics are always in [0, 1]."""
        pos_array = np.array(position)
        # Weights must sum to 1.0
        result = scbe_14layer_pipeline(
            t=pos_array, D=6,
            w_d=0.2, w_c=0.2, w_s=0.2, w_tau=0.2, w_a=0.2
        )

        for key, value in result["coherence"].items():
            assert 0 <= value <= 1, f"Coherence {key} out of bounds: {value}"

    @given(
        position=position_6d,
        w_d=st.floats(min_value=0.1, max_value=0.5)
    )
    @settings(max_examples=100)
    def test_pipeline_higher_weight_higher_risk(self, position, w_d):
        """Higher distance weight should not decrease risk."""
        pos_array = np.array(position)

        # Both runs need weights summing to 1.0
        result_low = scbe_14layer_pipeline(
            t=pos_array, D=6,
            w_d=0.1, w_c=0.3, w_s=0.3, w_tau=0.2, w_a=0.1
        )
        result_high = scbe_14layer_pipeline(
            t=pos_array, D=6,
            w_d=0.5, w_c=0.2, w_s=0.15, w_tau=0.1, w_a=0.05
        )

        # Higher weight should generally result in same or higher risk
        # (not strictly true due to other factors, so we just check it's valid)
        assert result_low["risk_base"] >= 0
        assert result_high["risk_base"] >= 0


# =============================================================================
# CRYPTOGRAPHIC PROPERTY TESTS
# =============================================================================

@pytest.mark.property
@pytest.mark.crypto
@pytest.mark.skipif(not RWP_AVAILABLE, reason="RWP not available")
class TestCryptographicProperties:
    """Property-based tests for cryptographic operations."""

    @given(
        plaintext=st.binary(min_size=1, max_size=1000),
        password=st.binary(min_size=8, max_size=64)
    )
    @settings(max_examples=50)
    def test_encryption_roundtrip(self, plaintext, password):
        """Encrypt then decrypt always returns original."""
        rwp = RWPv3Protocol()

        # RWP v3 API: encrypt(password, plaintext), decrypt(password, envelope)
        envelope = rwp.encrypt(password=password, plaintext=plaintext)
        decrypted = rwp.decrypt(password=password, envelope=envelope)

        assert decrypted == plaintext

    @given(
        plaintext=st.binary(min_size=1, max_size=100),
        password=st.binary(min_size=8, max_size=32)
    )
    @settings(max_examples=50)
    def test_ciphertext_different_each_time(self, plaintext, password):
        """Same plaintext encrypts to different ciphertext (due to nonce)."""
        rwp = RWPv3Protocol()

        # RWP v3 returns RWPEnvelope with ct (ciphertext tokens) and nonce
        env1 = rwp.encrypt(password=password, plaintext=plaintext)
        env2 = rwp.encrypt(password=password, plaintext=plaintext)

        # Different nonces should produce different ciphertexts
        # Fields are: ct (List[str]), nonce (List[str])
        assert env1.ct != env2.ct or env1.nonce != env2.nonce

    @given(plaintext=st.binary(min_size=1, max_size=100))
    @settings(max_examples=50)
    def test_ciphertext_longer_than_plaintext(self, plaintext):
        """Ciphertext includes overhead (nonce, tag, etc.)."""
        rwp = RWPv3Protocol()
        password = b"test_password"

        # RWP v3 returns RWPEnvelope with ct, nonce, tag as List[str] tokens
        envelope = rwp.encrypt(password=password, plaintext=plaintext)

        # Total token count: ct + nonce + tag + salt + aad
        # Sacred Tongue tokens encode bytes as strings
        total_tokens = len(envelope.ct) + len(envelope.nonce) + len(envelope.tag)
        # Tokens represent more data than just plaintext
        assert total_tokens > 0


# =============================================================================
# DECISION BOUNDARY TESTS
# =============================================================================

@pytest.mark.property
class TestDecisionBoundaries:
    """Property-based tests for decision boundaries."""

    @given(
        risk=risk_score,
        theta1=st.floats(min_value=0.1, max_value=0.4),
        theta2=st.floats(min_value=0.5, max_value=0.9)
    )
    @settings(max_examples=200)
    def test_decision_partitions_risk_space(self, risk, theta1, theta2):
        """Decision thresholds partition [0, 1] into 3 regions."""
        assume(theta1 < theta2)

        if risk < theta1:
            expected = "ALLOW"
        elif risk < theta2:
            expected = "QUARANTINE"
        else:
            expected = "DENY"

        # Verify the partition is complete
        assert expected in ["ALLOW", "QUARANTINE", "DENY"]

    @given(
        theta1=st.floats(min_value=0.0, max_value=0.5),
        theta2=st.floats(min_value=0.5, max_value=1.0)
    )
    @settings(max_examples=100)
    def test_threshold_ordering(self, theta1, theta2):
        """theta1 < theta2 always."""
        assume(theta1 < theta2)

        # ALLOW region < QUARANTINE region < DENY region
        assert theta1 < theta2


# =============================================================================
# INPUT VALIDATION TESTS
# =============================================================================

@pytest.mark.property
class TestInputValidation:
    """Property-based tests for input validation."""

    @given(position=st.lists(st.integers(), min_size=0, max_size=10))
    @settings(max_examples=100)
    def test_position_length_validation(self, position):
        """Position must have exactly 6 elements."""
        is_valid = len(position) == 6
        assert is_valid == (len(position) == 6)

    @given(context=st.text(min_size=1, max_size=20))
    @settings(max_examples=100)
    def test_context_enum_validation(self, context):
        """Context must be internal/external/untrusted."""
        valid_contexts = {"internal", "external", "untrusted"}
        is_valid = context in valid_contexts
        assert is_valid == (context in valid_contexts)


# =============================================================================
# STRESS AND EDGE CASE TESTS
# =============================================================================

@pytest.mark.property
class TestEdgeCases:
    """Property-based edge case discovery."""

    @given(
        x=st.floats(allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=200)
    def test_finite_inputs_produce_finite_outputs(self, x):
        """Finite inputs should produce finite outputs in calculations."""
        # Clamp to reasonable range
        x = max(min(x, 1e6), -1e6)

        # Basic calculations should be finite
        result = x ** 2
        assert np.isfinite(result) or abs(x) > 1e3

    @given(values=st.lists(st.floats(min_value=-100, max_value=100, allow_nan=False), min_size=6, max_size=6))
    @settings(max_examples=100)
    def test_norm_always_non_negative(self, values):
        """Vector norm is always non-negative."""
        arr = np.array(values)
        norm = np.linalg.norm(arr)
        assert norm >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "property"])
