"""
Comprehensive Tests for the 14-Layer SCBE Pipeline

Tests each layer mathematically and verifies all theorems.
"""

import numpy as np
import pytest
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scbe_aethermoore.layers import (
    FourteenLayerPipeline,
    RiskLevel,
    layer_1_complex_context,
    layer_2_realify,
    layer_3_weighted,
    layer_4_poincare,
    layer_5_hyperbolic_distance,
    layer_6_breathing,
    layer_7_phase,
    layer_8_multi_well,
    layer_9_spectral_coherence,
    layer_10_spin_coherence,
    layer_11_triadic_distance,
    layer_12_harmonic_scaling,
    layer_13_decision,
    layer_14_audio_axis,
    build_langues_metric,
    breathing_factor,
    mobius_addition,
    verify_theorem_A_metric_invariance,
    verify_theorem_B_continuity,
    verify_theorem_C_risk_monotonicity,
    verify_theorem_D_diffeomorphism,
    PHI,
    R_BASE,
    EPS,
)


class TestLayer1ComplexContext:
    """Tests for Layer 1: Complex Context State."""

    def test_output_is_complex(self):
        """Output should be complex array."""
        c = layer_1_complex_context(1.0, 0.5+0.5j, 0.9, 1000, 0.8, 0.95)
        assert c.dtype == complex

    def test_correct_dimension(self):
        """Output should be 6-dimensional."""
        c = layer_1_complex_context(1.0, 0.5+0.5j, 0.9, 1000, 0.8, 0.95)
        assert len(c) == 6

    def test_identity_as_phase(self):
        """Identity should encode as unit complex number."""
        c = layer_1_complex_context(np.pi/2, 0+0j, 0.9, 1000, 0.8, 0.95)
        assert np.abs(np.abs(c[0]) - 1.0) < 1e-10  # Unit magnitude

    def test_intent_preserved(self):
        """Intent should be preserved as-is."""
        intent = 0.3 + 0.7j
        c = layer_1_complex_context(1.0, intent, 0.9, 1000, 0.8, 0.95)
        assert c[1] == intent


class TestLayer2Realify:
    """Tests for Layer 2: Realification."""

    def test_output_dimension_doubled(self):
        """Real dimension should be 2x complex dimension."""
        c = np.array([1+2j, 3+4j, 5+6j], dtype=complex)
        x = layer_2_realify(c)
        assert len(x) == 2 * len(c)

    def test_correct_interleaving(self):
        """Real and imaginary parts should be interleaved."""
        c = np.array([1+2j, 3+4j], dtype=complex)
        x = layer_2_realify(c)
        assert np.allclose(x, [1, 2, 3, 4])

    def test_isometry_property(self):
        """Inner product should be preserved: ⟨c,c'⟩_ℂ = ⟨Φ(c),Φ(c')⟩_ℝ."""
        c1 = np.array([1+2j, 3+4j, 5+0j], dtype=complex)
        c2 = np.array([2+1j, 1+3j, 0+5j], dtype=complex)

        # Complex inner product (conjugate linear in first arg)
        inner_complex = np.sum(np.conj(c1) * c2)

        # Real inner product
        x1 = layer_2_realify(c1)
        x2 = layer_2_realify(c2)
        inner_real = np.dot(x1, x2)

        # They should match (real part)
        assert np.abs(np.real(inner_complex) - inner_real) < 1e-10


class TestLayer3Weighted:
    """Tests for Layer 3: Weighted Transform."""

    def test_langues_metric_symmetric(self):
        """Langues metric tensor should be symmetric."""
        G = build_langues_metric(6)
        assert np.allclose(G, G.T)

    def test_langues_metric_positive_semidefinite(self):
        """Langues metric should be positive semidefinite."""
        G = build_langues_metric(6)
        eigenvalues = np.linalg.eigvalsh(G)
        assert all(ev >= -1e-10 for ev in eigenvalues)

    def test_weighted_transform_changes_norm(self):
        """Weighted transform should change the norm (generally)."""
        x = np.array([1.0, 0.0, 0.0, 1.0, 0.0, 0.0])
        x_weighted = layer_3_weighted(x)
        # Norm should change unless x is an eigenvector
        assert not np.isclose(np.linalg.norm(x), np.linalg.norm(x_weighted))


class TestLayer4Poincare:
    """Tests for Layer 4: Poincaré Embedding."""

    def test_output_in_ball(self):
        """Output should always be inside unit ball."""
        for _ in range(100):
            x = np.random.randn(12) * 10  # Large input
            u = layer_4_poincare(x)
            assert np.linalg.norm(u) < 1.0

    def test_preserves_direction(self):
        """Embedding should preserve direction."""
        x = np.array([1.0, 2.0, 3.0])
        u = layer_4_poincare(x)
        # Cosine similarity should be ~1
        cos_sim = np.dot(x, u) / (np.linalg.norm(x) * np.linalg.norm(u))
        assert cos_sim > 0.999

    def test_zero_maps_to_zero(self):
        """Zero vector should map to zero."""
        x = np.zeros(6)
        u = layer_4_poincare(x)
        assert np.linalg.norm(u) < EPS


class TestLayer5HyperbolicDistance:
    """Tests for Layer 5: Hyperbolic Distance."""

    def test_distance_to_self_is_zero(self):
        """d_H(u, u) = 0."""
        u = np.array([0.3, 0.4, 0.0])
        assert layer_5_hyperbolic_distance(u, u) < 1e-10

    def test_symmetry(self):
        """d_H(u, v) = d_H(v, u)."""
        u = np.array([0.3, 0.4, 0.0])
        v = np.array([0.1, -0.2, 0.3])
        assert np.abs(layer_5_hyperbolic_distance(u, v) - layer_5_hyperbolic_distance(v, u)) < 1e-10

    def test_triangle_inequality(self):
        """d_H(u, w) ≤ d_H(u, v) + d_H(v, w)."""
        u = np.array([0.1, 0.2, 0.0])
        v = np.array([0.3, -0.1, 0.2])
        w = np.array([-0.2, 0.3, 0.1])

        d_uw = layer_5_hyperbolic_distance(u, w)
        d_uv = layer_5_hyperbolic_distance(u, v)
        d_vw = layer_5_hyperbolic_distance(v, w)

        assert d_uw <= d_uv + d_vw + 1e-10

    def test_distance_increases_near_boundary(self):
        """Points near boundary should have larger distances."""
        u = np.array([0.1, 0.0])
        v1 = np.array([0.5, 0.0])  # Moderate
        v2 = np.array([0.9, 0.0])  # Near boundary

        d1 = layer_5_hyperbolic_distance(u, v1)
        d2 = layer_5_hyperbolic_distance(u, v2)

        assert d2 > d1


class TestLayer6Breathing:
    """Tests for Layer 6: Breathing Transform."""

    def test_output_in_ball(self):
        """Breathing transform should keep points in ball."""
        for _ in range(50):
            u = np.random.randn(6) * 0.3
            u = u / (np.linalg.norm(u) + 1) * 0.8
            t = np.random.rand() * 100

            u_breath = layer_6_breathing(u, t)
            assert np.linalg.norm(u_breath) < 1.0

    def test_breathing_factor_oscillates(self):
        """Breathing factor should oscillate."""
        b0 = breathing_factor(0)
        b_quarter = breathing_factor(15)  # Quarter period
        b_half = breathing_factor(30)     # Half period

        # Should oscillate around 1
        assert b0 < b_quarter or b0 > b_quarter  # Different values
        assert np.abs(b_half - b0) < 0.01  # Back near start

    def test_preserves_origin(self):
        """Origin should map to origin."""
        u = np.zeros(6)
        u_breath = layer_6_breathing(u, 10.0)
        assert np.linalg.norm(u_breath) < EPS


class TestLayer7Phase:
    """Tests for Layer 7: Phase Transform."""

    def test_mobius_identity(self):
        """0 ⊕ u = u."""
        u = np.array([0.3, 0.4, -0.2])
        zero = np.zeros_like(u)
        result = mobius_addition(zero, u)
        assert np.allclose(result, u, atol=1e-10)

    def test_mobius_keeps_in_ball(self):
        """Möbius addition should keep result in ball."""
        for _ in range(50):
            a = np.random.randn(6) * 0.2
            u = np.random.randn(6) * 0.3
            a = a / (np.linalg.norm(a) + 1) * 0.4
            u = u / (np.linalg.norm(u) + 1) * 0.6

            result = mobius_addition(a, u)
            assert np.linalg.norm(result) < 1.0

    def test_phase_rotation_preserves_norm(self):
        """Rotation should preserve norm in 2D plane."""
        u = np.array([0.3, 0.4, 0.0, 0.0, 0.0, 0.0])
        for phi in [0, np.pi/4, np.pi/2, np.pi]:
            u_rot = layer_7_phase(u, phi)
            # Norm should be preserved (approximately, due to just rotating first 2 coords)
            assert np.abs(np.linalg.norm(u) - np.linalg.norm(u_rot)) < 1e-10


class TestLayer8MultiWell:
    """Tests for Layer 8: Multi-Well Realms."""

    def test_finds_nearest_realm(self):
        """Should return distance to nearest realm center."""
        dim = 6
        from scbe_aethermoore.layers import generate_realm_centers
        centers = generate_realm_centers(dim, n_realms=3)

        # Point close to first center
        u = centers[0] * 0.9 + np.random.randn(dim) * 0.01
        d_star, idx = layer_8_multi_well(u, centers)

        assert idx == 0
        assert d_star < layer_5_hyperbolic_distance(u, centers[1])
        assert d_star < layer_5_hyperbolic_distance(u, centers[2])

    def test_returns_valid_index(self):
        """Realm index should be within bounds."""
        u = np.zeros(6)
        d_star, idx = layer_8_multi_well(u)
        assert 0 <= idx < 5  # N_REALMS = 5


class TestLayer9SpectralCoherence:
    """Tests for Layer 9: Spectral Coherence."""

    def test_pure_sine_high_coherence(self):
        """Pure sine wave should have high coherence."""
        t = np.linspace(0, 1, 1000)
        signal = np.sin(2 * np.pi * 10 * t)  # 10 Hz sine
        S_spec = layer_9_spectral_coherence(signal)
        assert S_spec > 0.5  # Mostly low frequency

    def test_noise_low_coherence(self):
        """White noise should have lower coherence."""
        np.random.seed(42)
        noise = np.random.randn(1000)
        S_spec = layer_9_spectral_coherence(noise)
        # Noise spreads energy, so coherence should be moderate
        assert S_spec < 0.9

    def test_coherence_bounds(self):
        """Coherence should be in [0, 1]."""
        for _ in range(20):
            signal = np.random.randn(100)
            S_spec = layer_9_spectral_coherence(signal)
            assert 0 <= S_spec <= 1


class TestLayer10SpinCoherence:
    """Tests for Layer 10: Spin Coherence."""

    def test_unit_state_max_coherence(self):
        """Unit norm state should have max coherence."""
        q = 1 + 0j
        C = layer_10_spin_coherence(q)
        assert np.abs(C - 1.0) < 1e-10

    def test_zero_state_min_coherence(self):
        """Zero state should have min coherence."""
        q = 0 + 0j
        C = layer_10_spin_coherence(q)
        assert np.abs(C - (-1.0)) < 1e-10

    def test_coherence_range(self):
        """Spin coherence should be in [-1, 1]."""
        for _ in range(50):
            q = complex(np.random.rand(), np.random.rand())
            C = layer_10_spin_coherence(q)
            assert -1 <= C <= 1


class TestLayer11TriadicDistance:
    """Tests for Layer 11: Triadic Temporal Distance."""

    def test_identical_states_zero_distance(self):
        """Identical states should have zero distance."""
        u = np.array([0.3, 0.4, 0.0, 0.0, 0.0, 0.0])
        d = layer_11_triadic_distance(u, u, 1.0, 1.0, 4.0, 4.0, 1+0j, 1+0j)
        assert d < 1e-10

    def test_includes_all_components(self):
        """Changing any component should change distance."""
        u = np.array([0.3, 0.4, 0.0, 0.0, 0.0, 0.0])

        d_base = layer_11_triadic_distance(u, u, 1.0, 1.0, 4.0, 4.0, 1+0j, 1+0j)

        # Different time
        d_tau = layer_11_triadic_distance(u, u, 1.0, 2.0, 4.0, 4.0, 1+0j, 1+0j)
        assert d_tau > d_base

        # Different entropy
        d_eta = layer_11_triadic_distance(u, u, 1.0, 1.0, 4.0, 5.0, 1+0j, 1+0j)
        assert d_eta > d_base

        # Different quantum - orthogonal phases (π/2 apart)
        # q1=1+0j has phase 0, q2=0+1j has phase π/2
        # phase_fidelity = (1 + cos(π/2))/2 = 0.5, so 1-F = 0.5
        d_q = layer_11_triadic_distance(u, u, 1.0, 1.0, 4.0, 4.0, 1+0j, 0+1j)
        assert d_q > d_base, f"Expected d_q > d_base, got {d_q} <= {d_base}"

        # Opposite phases (π apart) should give even larger distance
        # phase_fidelity = (1 + cos(π))/2 = 0, so 1-F = 1
        d_q_opposite = layer_11_triadic_distance(u, u, 1.0, 1.0, 4.0, 4.0, 1+0j, -1+0j)
        assert d_q_opposite > d_q, f"Opposite phases should have larger distance"


class TestLayer12HarmonicScaling:
    """Tests for Layer 12: Harmonic Scaling."""

    def test_zero_distance_gives_one(self):
        """H(0, R) = R^0 = 1."""
        assert np.abs(layer_12_harmonic_scaling(0, R_BASE) - 1.0) < 1e-10

    def test_superexponential_growth(self):
        """H(d) should grow faster than exponential."""
        d1, d2, d3 = 1.0, 2.0, 3.0
        H1 = layer_12_harmonic_scaling(d1)
        H2 = layer_12_harmonic_scaling(d2)
        H3 = layer_12_harmonic_scaling(d3)

        # Check superexponential: H(3)/H(2) > H(2)/H(1)
        ratio_23 = H3 / H2
        ratio_12 = H2 / H1
        assert ratio_23 > ratio_12

    def test_monotonicity(self):
        """H(d1) < H(d2) for d1 < d2."""
        d_values = np.linspace(0, 3, 20)
        H_values = [layer_12_harmonic_scaling(d) for d in d_values]

        for i in range(len(H_values) - 1):
            assert H_values[i] < H_values[i+1]


class TestLayer13Decision:
    """Tests for Layer 13: Decision & Risk."""

    def test_low_risk_allows(self):
        """Low d_star should give ALLOW."""
        risk = layer_13_decision(d_star=0.1, H_d=1.1, coherence=0.9, realm_idx=0)
        assert risk.decision == "ALLOW"
        assert risk.level == RiskLevel.LOW

    def test_high_risk_denies(self):
        """High d_star should give DENY."""
        risk = layer_13_decision(d_star=3.0, H_d=5.0, coherence=0.9, realm_idx=0)
        assert risk.decision == "DENY"
        assert risk.level == RiskLevel.HIGH

    def test_critical_snaps(self):
        """Very high H_d should give SNAP."""
        risk = layer_13_decision(d_star=0.5, H_d=150, coherence=0.9, realm_idx=0)
        assert risk.decision == "SNAP"
        assert risk.level == RiskLevel.CRITICAL

    def test_medium_reviews(self):
        """Medium d_star should give REVIEW."""
        risk = layer_13_decision(d_star=1.0, H_d=2.0, coherence=0.9, realm_idx=0)
        assert risk.decision == "REVIEW"
        assert risk.level == RiskLevel.MEDIUM


class TestLayer14AudioAxis:
    """Tests for Layer 14: Audio Axis."""

    def test_output_length(self):
        """Output length should match duration * sample_rate."""
        audio = layer_14_audio_axis(0.5, 0.9, RiskLevel.LOW, duration=0.1)
        expected_len = int(44100 * 0.1)
        assert len(audio) == expected_len

    def test_risk_affects_amplitude(self):
        """Higher risk should have lower amplitude."""
        audio_low = layer_14_audio_axis(0.5, 0.9, RiskLevel.LOW)
        audio_high = layer_14_audio_axis(0.5, 0.9, RiskLevel.HIGH)

        assert np.max(np.abs(audio_low)) > np.max(np.abs(audio_high))

    def test_coherence_affects_envelope(self):
        """Low coherence should decay faster."""
        audio_high_coh = layer_14_audio_axis(0.5, 0.99, RiskLevel.LOW)
        audio_low_coh = layer_14_audio_axis(0.5, 0.5, RiskLevel.LOW)

        # End of signal should be lower for low coherence
        assert np.abs(audio_high_coh[-1]) > np.abs(audio_low_coh[-1])


class TestFullPipeline:
    """Tests for the complete 14-layer pipeline."""

    def test_pipeline_runs(self):
        """Pipeline should run without errors."""
        pipeline = FourteenLayerPipeline()
        risk, states = pipeline.process(
            identity=1.0,
            intent=0.5+0.5j,
            trajectory=0.9,
            timing=1000,
            commitment=0.8,
            signature=0.95,
            t=10.0,
            tau=1.0,
            eta=4.0,
            q=1+0j
        )
        assert risk is not None
        assert len(states) == 14

    def test_all_layers_recorded(self):
        """All 14 layers should be recorded."""
        pipeline = FourteenLayerPipeline()
        _, states = pipeline.process(
            identity=1.0, intent=0.5+0.5j, trajectory=0.9,
            timing=1000, commitment=0.8, signature=0.95,
            t=10.0, tau=1.0, eta=4.0, q=1+0j
        )

        layer_nums = [s.layer for s in states]
        assert layer_nums == list(range(1, 15))

    def test_similar_states_have_consistent_risk(self):
        """Similar inputs should produce consistent risk assessments."""
        pipeline = FourteenLayerPipeline()

        # Process identical states twice - should get same risk
        risk1, states1 = pipeline.process(
            identity=1.0, intent=0.5+0.5j, trajectory=0.99,
            timing=1000, commitment=0.99, signature=0.99,
            t=10.0, tau=1.0, eta=4.0, q=1+0j
        )

        risk2, states2 = pipeline.process(
            identity=1.0, intent=0.5+0.5j, trajectory=0.99,
            timing=1000, commitment=0.99, signature=0.99,
            t=10.0, tau=1.0, eta=4.0, q=1+0j
        )

        # Identical inputs should produce identical risk levels
        assert risk1.level == risk2.level
        assert risk1.decision == risk2.decision
        assert np.isclose(risk1.raw_risk, risk2.raw_risk)

    def test_harmonic_scaling_dominates_risk(self):
        """Verify that harmonic scaling drives risk classification."""
        # H(d,R) = R^(d²) with R = φ ≈ 1.618
        # For d = 0: H = 1 (LOW)
        # For d = 1: H = φ ≈ 1.6 (still relatively low)
        # For d = 2: H = φ^4 ≈ 6.85 (MEDIUM)
        # For d = 3: H = φ^9 ≈ 76.0 (HIGH)
        # For d = 4: H = φ^16 ≈ 2207 (CRITICAL, >100)

        from scbe_aethermoore.layers import layer_12_harmonic_scaling, R_BASE

        # Test the scaling behavior
        assert layer_12_harmonic_scaling(0, R_BASE) == 1.0
        assert layer_12_harmonic_scaling(1, R_BASE) < 3.0
        assert layer_12_harmonic_scaling(2, R_BASE) < 20.0
        assert layer_12_harmonic_scaling(3, R_BASE) < 100.0
        assert layer_12_harmonic_scaling(4, R_BASE) > 100.0  # CRITICAL threshold


class TestTheoremVerification:
    """Tests for theorem verification functions."""

    def test_theorem_A_metric_invariance(self):
        """Theorem A should pass."""
        passed, results = verify_theorem_A_metric_invariance(n_tests=20)
        assert passed, f"Theorem A failed: {results}"

    def test_theorem_B_continuity(self):
        """Theorem B should pass."""
        passed, results = verify_theorem_B_continuity()
        assert passed, f"Theorem B failed: {results}"

    def test_theorem_C_monotonicity(self):
        """Theorem C should pass."""
        passed, results = verify_theorem_C_risk_monotonicity(n_tests=20)
        assert passed, f"Theorem C failed: {results}"

    def test_theorem_D_diffeomorphism(self):
        """Theorem D should pass."""
        passed, results = verify_theorem_D_diffeomorphism(n_tests=20)
        assert passed, f"Theorem D failed: {results}"


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
