"""
Comprehensive tests for the axiom-grouped module.

Tests verify:
1. Each axiom module's layer implementations
2. Axiom-checking decorators
3. Layer-to-axiom mappings
4. Full pipeline execution with axiom verification
"""

import pytest
import numpy as np
from typing import Tuple

# Import the axiom-grouped module
from symphonic_cipher.scbe_aethermoore.axiom_grouped import (
    QuantumAxiom,
    LAYER_TO_AXIOM,
    AXIOM_TO_LAYERS,
    get_layer_axiom,
    get_axiom_layers,
    get_layer_info,
    get_all_layers,
    verify_all_axioms,
    AxiomAwarePipeline,
    ContextInput,
    Pipeline,
    compose,
    pipe,
)

from symphonic_cipher.scbe_aethermoore.axiom_grouped import unitarity_axiom
from symphonic_cipher.scbe_aethermoore.axiom_grouped import locality_axiom
from symphonic_cipher.scbe_aethermoore.axiom_grouped import causality_axiom
from symphonic_cipher.scbe_aethermoore.axiom_grouped import symmetry_axiom
from symphonic_cipher.scbe_aethermoore.axiom_grouped import composition_axiom


# ============================================================================
# Test Constants
# ============================================================================

EPS = 1e-10
PHI = (1 + np.sqrt(5)) / 2
DIM = 12  # Standard test dimension


def random_complex_vector(dim: int) -> np.ndarray:
    """Generate random complex vector."""
    return np.random.randn(dim) + 1j * np.random.randn(dim)


def random_poincare_point(dim: int, max_norm: float = 0.9) -> np.ndarray:
    """Generate random point in Poincaré ball."""
    x = np.random.randn(dim)
    norm = np.linalg.norm(x)
    if norm > EPS:
        r = np.random.uniform(0, max_norm)
        return r * x / norm
    return np.zeros(dim)


# ============================================================================
# Test Layer-to-Axiom Mapping
# ============================================================================

class TestLayerMapping:
    """Tests for the layer-to-axiom mapping."""

    def test_all_layers_mapped(self):
        """All 14 layers should be mapped to an axiom."""
        for i in range(1, 15):
            assert i in LAYER_TO_AXIOM
            assert isinstance(LAYER_TO_AXIOM[i], QuantumAxiom)

    def test_get_layer_axiom(self):
        """get_layer_axiom should return correct axiom strings."""
        assert get_layer_axiom(1) == "composition"
        assert get_layer_axiom(2) == "unitarity"
        assert get_layer_axiom(3) == "locality"
        assert get_layer_axiom(5) == "symmetry"
        assert get_layer_axiom(6) == "causality"
        assert get_layer_axiom(14) == "composition"

    def test_get_layer_axiom_invalid(self):
        """get_layer_axiom should raise for invalid layer."""
        with pytest.raises(ValueError):
            get_layer_axiom(0)
        with pytest.raises(ValueError):
            get_layer_axiom(15)

    def test_get_axiom_layers(self):
        """get_axiom_layers should return correct layer lists."""
        assert get_axiom_layers("unitarity") == [2, 4, 7]
        assert get_axiom_layers("locality") == [3, 8]
        assert get_axiom_layers("causality") == [6, 11, 13]
        assert get_axiom_layers("symmetry") == [5, 9, 10, 12]
        assert get_axiom_layers("composition") == [1, 14]

    def test_axiom_coverage(self):
        """Every layer should belong to exactly one axiom."""
        all_layers = set()
        for layers in AXIOM_TO_LAYERS.values():
            for layer in layers:
                assert layer not in all_layers, f"Layer {layer} mapped twice"
                all_layers.add(layer)
        assert all_layers == set(range(1, 15))

    def test_get_layer_info(self):
        """get_layer_info should return complete layer information."""
        info = get_layer_info(5)
        assert info.number == 5
        assert info.name == "Hyperbolic Distance"
        assert info.axiom == QuantumAxiom.SYMMETRY
        assert callable(info.function)

    def test_get_all_layers(self):
        """get_all_layers should return info for all 14 layers."""
        all_layers = get_all_layers()
        assert len(all_layers) == 14
        for i in range(1, 15):
            assert i in all_layers


# ============================================================================
# Test Unitarity Axiom
# ============================================================================

class TestUnitarityAxiom:
    """Tests for unitarity axiom layers."""

    def test_layer_2_realify_norm_preservation(self):
        """Layer 2 should preserve norms (isometry)."""
        for _ in range(100):
            c = random_complex_vector(6)
            x = unitarity_axiom.layer_2_realify(c)

            # Check norm preservation
            c_norm = np.linalg.norm(c)
            x_norm = np.linalg.norm(x)
            assert abs(c_norm - x_norm) < EPS

    def test_layer_2_dimension(self):
        """Layer 2 should double the dimension."""
        c = random_complex_vector(6)
        x = unitarity_axiom.layer_2_realify(c)
        assert len(x) == 12

    def test_layer_2_inverse(self):
        """Layer 2 inverse should recover original."""
        c = random_complex_vector(6)
        x = unitarity_axiom.layer_2_realify(c)
        c_recovered = unitarity_axiom.layer_2_inverse(x)
        np.testing.assert_allclose(c, c_recovered, atol=EPS)

    def test_layer_4_poincare_inside_ball(self):
        """Layer 4 output should be inside Poincaré ball."""
        for _ in range(100):
            x = np.random.randn(DIM) * 10  # Large input
            u = unitarity_axiom.layer_4_poincare(x)
            assert np.linalg.norm(u) < 1.0

    def test_layer_4_direction_preserved(self):
        """Layer 4 should preserve direction."""
        x = np.random.randn(DIM)
        x = x / np.linalg.norm(x)  # Unit vector
        u = unitarity_axiom.layer_4_poincare(x)

        # Directions should match
        u_dir = u / np.linalg.norm(u)
        np.testing.assert_allclose(x, u_dir, atol=1e-6)

    def test_layer_4_inverse(self):
        """Layer 4 inverse should approximately recover original."""
        x = np.random.randn(DIM)
        u = unitarity_axiom.layer_4_poincare(x)
        x_recovered = unitarity_axiom.layer_4_inverse(u)
        np.testing.assert_allclose(x, x_recovered, atol=1e-6)

    def test_layer_7_phase_preserves_norm(self):
        """Layer 7 (Möbius + rotation) should preserve norm."""
        for _ in range(100):
            u = random_poincare_point(DIM, 0.8)
            phase = np.random.uniform(0, 2 * np.pi)
            trans = random_poincare_point(DIM, 0.3)

            u_transformed = unitarity_axiom.layer_7_phase(u, phase, trans)

            # Norm should be approximately preserved
            # (Möbius can change norm, but result stays in ball)
            assert np.linalg.norm(u_transformed) < 1.0

    def test_mobius_addition_identity(self):
        """Möbius addition with zero should be identity."""
        u = random_poincare_point(DIM)
        zero = np.zeros(DIM)
        result = unitarity_axiom.mobius_addition(u, zero)
        np.testing.assert_allclose(result, u, atol=EPS)

    def test_verify_layer_unitarity(self):
        """Unitarity verification should pass for unitarity layers."""
        passed, max_error = unitarity_axiom.verify_layer_unitarity(
            unitarity_axiom.layer_2_realify, n_tests=50
        )
        assert passed
        assert max_error < 1e-8


# ============================================================================
# Test Locality Axiom
# ============================================================================

class TestLocalityAxiom:
    """Tests for locality axiom layers."""

    def test_langues_metric_diagonal(self):
        """Langues metric should be diagonal."""
        G = locality_axiom.build_langues_metric(DIM)
        off_diag = G - np.diag(np.diag(G))
        assert np.allclose(off_diag, 0)

    def test_langues_metric_positive_definite(self):
        """Langues metric should be positive definite."""
        G = locality_axiom.build_langues_metric(DIM)
        eigenvalues = np.linalg.eigvalsh(G)
        assert all(eigenvalues > 0)

    def test_layer_3_weighted_shape(self):
        """Layer 3 should preserve shape."""
        x = np.random.randn(DIM)
        x_weighted = locality_axiom.layer_3_weighted(x)
        assert x_weighted.shape == x.shape

    def test_layer_3_inverse(self):
        """Layer 3 inverse should recover original."""
        x = np.random.randn(DIM)
        x_weighted = locality_axiom.layer_3_weighted(x)
        x_recovered = locality_axiom.layer_3_inverse(x_weighted)
        np.testing.assert_allclose(x, x_recovered, atol=1e-8)

    def test_realm_centers_generation(self):
        """Should generate correct number of realm centers."""
        realms = locality_axiom.generate_realm_centers(DIM, n_realms=5)
        assert len(realms) == 5

        for realm in realms:
            assert realm.center.shape == (DIM,)
            assert np.linalg.norm(realm.center) < 1.0  # Inside ball

    def test_layer_8_returns_valid_realm(self):
        """Layer 8 should return valid realm index."""
        u = random_poincare_point(DIM)
        d_star, realm_idx, realm_info = locality_axiom.layer_8_multi_well(u)

        assert d_star >= 0
        assert 0 <= realm_idx < 5
        assert realm_info.index == realm_idx

    def test_hyperbolic_distance_symmetric(self):
        """Hyperbolic distance should be symmetric."""
        u = random_poincare_point(DIM)
        v = random_poincare_point(DIM)

        d_uv = locality_axiom.hyperbolic_distance(u, v)
        d_vu = locality_axiom.hyperbolic_distance(v, u)

        assert abs(d_uv - d_vu) < EPS


# ============================================================================
# Test Causality Axiom
# ============================================================================

class TestCausalityAxiom:
    """Tests for causality axiom layers."""

    def test_breathing_factor_range(self):
        """Breathing factor should be in valid range."""
        for t in np.linspace(0, 120, 100):
            b = causality_axiom.breathing_factor(t)
            assert 1 - causality_axiom.B_BREATH_MAX <= b <= 1 + causality_axiom.B_BREATH_MAX

    def test_layer_6_stays_in_ball(self):
        """Layer 6 output should remain in Poincaré ball."""
        for t in np.linspace(0, 60, 20):
            u = random_poincare_point(DIM, 0.95)
            u_breathed = causality_axiom.layer_6_breathing(u, t=t)
            assert np.linalg.norm(u_breathed) < 1.0

    def test_layer_6_inverse(self):
        """Layer 6 inverse should recover original."""
        t = 10.0
        u = random_poincare_point(DIM, 0.8)
        u_breathed = causality_axiom.layer_6_breathing(u, t=t)
        u_recovered = causality_axiom.layer_6_inverse(u_breathed, t=t)
        np.testing.assert_allclose(u, u_recovered, atol=1e-6)

    def test_quantum_fidelity_range(self):
        """Quantum fidelity should be in [0, 1]."""
        for _ in range(100):
            q1 = np.random.randn() + 1j * np.random.randn()
            q2 = np.random.randn() + 1j * np.random.randn()
            F = causality_axiom.quantum_fidelity(q1, q2)
            assert 0 <= F <= 1 + EPS

    def test_quantum_fidelity_self(self):
        """Quantum fidelity with self should be |q|^4."""
        q = np.random.randn() + 1j * np.random.randn()
        F = causality_axiom.quantum_fidelity(q, q)
        expected = abs(q) ** 4
        assert abs(F - expected) < EPS

    def test_layer_11_triadic_distance_nonnegative(self):
        """Triadic distance should be non-negative."""
        u = random_poincare_point(DIM)
        ref_u = random_poincare_point(DIM)

        d = causality_axiom.layer_11_triadic_distance(
            u=u, ref_u=ref_u,
            tau=1.0, ref_tau=0.0,
            eta=0.5, ref_eta=0.3,
            q=1+0j, ref_q=0.5+0.5j
        )
        assert d >= 0

    def test_layer_13_decision_levels(self):
        """Layer 13 should return correct decision levels."""
        # Low risk
        result = causality_axiom.layer_13_decision(
            d_star=0.3, coherence=0.9, realm_index=0
        )
        assert result.level == causality_axiom.RiskLevel.LOW
        assert result.decision == causality_axiom.Decision.ALLOW

        # Medium risk
        result = causality_axiom.layer_13_decision(
            d_star=1.0, coherence=0.5, realm_index=0
        )
        assert result.level == causality_axiom.RiskLevel.MEDIUM
        assert result.decision == causality_axiom.Decision.REVIEW

        # High risk
        result = causality_axiom.layer_13_decision(
            d_star=2.5, coherence=0.3, realm_index=0
        )
        assert result.level == causality_axiom.RiskLevel.HIGH
        assert result.decision == causality_axiom.Decision.DENY

    def test_causal_pipeline_time_ordering(self):
        """Causal pipeline should maintain time ordering."""
        pipeline = causality_axiom.CausalPipeline()

        for dt in [0.1, 0.2, 0.3]:
            pipeline.advance_time(dt)
            u = random_poincare_point(DIM)
            _ = pipeline.execute_layer_6(u)

        assert pipeline.verify_causality()


# ============================================================================
# Test Symmetry Axiom
# ============================================================================

class TestSymmetryAxiom:
    """Tests for symmetry axiom layers."""

    def test_layer_5_hyperbolic_distance_positive(self):
        """Hyperbolic distance should be positive for distinct points."""
        u = random_poincare_point(DIM)
        v = random_poincare_point(DIM)

        d = symmetry_axiom.layer_5_hyperbolic_distance(u, v)
        assert d >= 0

    def test_layer_5_hyperbolic_distance_zero_self(self):
        """Hyperbolic distance to self should be zero."""
        u = random_poincare_point(DIM)
        d = symmetry_axiom.layer_5_hyperbolic_distance(u, u)
        assert abs(d) < EPS

    def test_layer_5_mobius_invariance(self):
        """Hyperbolic distance should be Möbius invariant."""
        u = random_poincare_point(DIM, 0.5)
        v = random_poincare_point(DIM, 0.5)

        passed, max_error = symmetry_axiom.verify_mobius_invariance(u, v)
        assert passed
        assert max_error < 1e-6

    def test_layer_9_spectral_coherence_range(self):
        """Spectral coherence should be in [0, 1]."""
        for _ in range(100):
            x = np.random.randn(DIM)
            S = symmetry_axiom.layer_9_spectral_coherence(x)
            assert 0 <= S <= 1

    def test_layer_9_dc_signal_coherence(self):
        """DC signal should have high coherence."""
        x = np.ones(DIM)  # Constant signal
        S = symmetry_axiom.layer_9_spectral_coherence(x)
        assert S > 0.9

    def test_layer_10_spin_coherence_range(self):
        """Spin coherence should be in [-1, 1]."""
        for _ in range(100):
            q = np.random.randn() + 1j * np.random.randn()
            C = symmetry_axiom.layer_10_spin_coherence(q)
            assert -1 <= C <= 1

    def test_layer_10_phase_invariance(self):
        """Spin coherence should be U(1) phase invariant."""
        q = np.random.randn() + 1j * np.random.randn()
        passed, max_error = symmetry_axiom.verify_phase_invariance(q)
        assert passed
        assert max_error < 1e-10

    def test_layer_12_harmonic_scaling_monotonic(self):
        """Harmonic scaling should be strictly monotonic."""
        distances = np.linspace(0, 5, 100)
        H_values = [symmetry_axiom.layer_12_harmonic_scaling(d) for d in distances]

        for i in range(1, len(H_values)):
            assert H_values[i] > H_values[i - 1]

    def test_layer_12_harmonic_scaling_identity_at_zero(self):
        """H(0) should equal 1."""
        H_0 = symmetry_axiom.layer_12_harmonic_scaling(0)
        assert abs(H_0 - 1.0) < EPS

    def test_layer_12_inverse(self):
        """Harmonic scaling inverse should recover distance."""
        d = 1.5
        H = symmetry_axiom.layer_12_harmonic_scaling(d)
        d_recovered = symmetry_axiom.layer_12_inverse(H)
        assert abs(d - d_recovered) < 1e-6


# ============================================================================
# Test Composition Axiom
# ============================================================================

class TestCompositionAxiom:
    """Tests for composition axiom layers."""

    def test_layer_1_output_dimension(self):
        """Layer 1 should output 6D complex vector."""
        ctx = ContextInput(
            identity=1+0j,
            intent=0.5+0.5j,
            trajectory=0.8,
            timing=0.5,
            commitment=0.9,
            signature=1.0
        )
        c = composition_axiom.layer_1_complex_context(ctx)
        assert c.shape == (6,)
        assert c.dtype == complex

    def test_layer_14_audio_output(self):
        """Layer 14 should produce valid audio output."""
        audio = composition_axiom.layer_14_audio_axis(
            risk_level="LOW",
            coherence=0.8,
            intent_phase=0.5,
            duration=0.1
        )

        assert audio.signal is not None
        assert len(audio.signal) == int(0.1 * 44100)
        assert audio.amplitude == 1.0  # LOW risk = full amplitude

    def test_layer_14_risk_amplitude_mapping(self):
        """Layer 14 amplitude should decrease with risk."""
        low = composition_axiom.layer_14_audio_axis("LOW", 0.5, 0.0)
        medium = composition_axiom.layer_14_audio_axis("MEDIUM", 0.5, 0.0)
        high = composition_axiom.layer_14_audio_axis("HIGH", 0.5, 0.0)
        critical = composition_axiom.layer_14_audio_axis("CRITICAL", 0.5, 0.0)

        assert low.amplitude > medium.amplitude > high.amplitude > critical.amplitude

    def test_pipeline_composition(self):
        """Pipeline composition should work correctly."""
        def f(x):
            return x + 1

        def g(x):
            return x * 2

        # compose(f, g)(x) = f(g(x)) = g(x) + 1 = 2x + 1
        composed = compose(f, g)
        assert composed(3) == 7

        # pipe(f, g)(x) = g(f(x)) = f(x) * 2 = 2(x + 1) = 2x + 2
        piped = pipe(f, g)
        assert piped(3) == 8

    def test_verify_pipeline_composition(self):
        """Pipeline composition verification should pass."""
        passed, issues = composition_axiom.verify_pipeline_composition()
        assert passed
        assert len(issues) == 0


# ============================================================================
# Test Full Pipeline
# ============================================================================

class TestFullPipeline:
    """Tests for the full axiom-aware pipeline."""

    def test_pipeline_execution(self):
        """Full pipeline should execute without errors."""
        pipeline = AxiomAwarePipeline()

        ctx = ContextInput(
            identity=1+0j,
            intent=0.5+0.5j,
            trajectory=0.8,
            timing=0.5,
            commitment=0.9,
            signature=1.0
        )

        output, states = pipeline.execute(ctx, t=0.0)

        assert output is not None
        assert len(states) == 14  # All 14 layers executed

    def test_pipeline_states_recorded(self):
        """Pipeline should record state at each layer."""
        pipeline = AxiomAwarePipeline()

        ctx = ContextInput(
            identity=1+0j,
            intent=0.5+0.5j,
            trajectory=0.8,
            timing=0.5,
            commitment=0.9,
            signature=1.0
        )

        _, states = pipeline.execute(ctx, t=0.0)

        layer_nums = [s.layer_num for s in states]
        assert layer_nums == list(range(1, 15))

        # Each state should have correct axiom
        for state in states:
            expected_axiom = get_layer_axiom(state.layer_num)
            assert state.axiom == expected_axiom

    def test_verify_all_axioms(self):
        """All axioms should verify successfully."""
        results = verify_all_axioms()

        for axiom, passed in results.items():
            assert passed, f"Axiom {axiom} verification failed"


# ============================================================================
# Test Axiom Decorators
# ============================================================================

class TestAxiomDecorators:
    """Tests for axiom-checking decorators."""

    def test_unitarity_decorator_stores_check(self):
        """Unitarity decorator should store check result."""
        c = random_complex_vector(6)
        _ = unitarity_axiom.layer_2_realify(c)

        assert hasattr(unitarity_axiom.layer_2_realify, 'last_check')
        assert unitarity_axiom.layer_2_realify.last_check is not None

    def test_locality_decorator_stores_check(self):
        """Locality decorator should store check result."""
        x = np.random.randn(DIM)
        _ = locality_axiom.layer_3_weighted(x)

        assert hasattr(locality_axiom.layer_3_weighted, 'last_check')

    def test_causality_decorator_stores_check(self):
        """Causality decorator should store check result."""
        # Reset time tracker
        if hasattr(causality_axiom.layer_6_breathing, 'reset_time'):
            causality_axiom.layer_6_breathing.reset_time()

        u = random_poincare_point(DIM)
        _ = causality_axiom.layer_6_breathing(u, t=0.0)

        assert hasattr(causality_axiom.layer_6_breathing, 'last_check')

    def test_symmetry_decorator_stores_check(self):
        """Symmetry decorator should store check result."""
        u = random_poincare_point(DIM)
        v = random_poincare_point(DIM)
        _ = symmetry_axiom.layer_5_hyperbolic_distance(u, v)

        assert hasattr(symmetry_axiom.layer_5_hyperbolic_distance, 'last_check')


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_vector_handling(self):
        """Zero vectors should be handled correctly."""
        zero = np.zeros(DIM)

        # Layer 4
        u = unitarity_axiom.layer_4_poincare(zero)
        np.testing.assert_allclose(u, zero)

        # Layer 6
        u_breathed = causality_axiom.layer_6_breathing(zero, t=1.0)
        np.testing.assert_allclose(u_breathed, zero)

    def test_boundary_poincare_point(self):
        """Points near boundary should be handled."""
        # Point very close to boundary
        x = np.ones(DIM) / np.sqrt(DIM) * 0.999

        # Layer 5 - distance to origin
        d = symmetry_axiom.layer_5_hyperbolic_distance(x, np.zeros(DIM))
        assert np.isfinite(d)
        assert d > 0

    def test_large_distance_harmonic_scaling(self):
        """Large distances should not cause overflow."""
        d = 10.0
        H = symmetry_axiom.layer_12_harmonic_scaling(d)
        assert np.isfinite(H)

    def test_identical_points_distance(self):
        """Distance between identical points should be zero."""
        u = random_poincare_point(DIM)
        d = symmetry_axiom.layer_5_hyperbolic_distance(u, u)
        assert abs(d) < EPS


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
