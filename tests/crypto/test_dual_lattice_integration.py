"""
Tests for Dual Lattice Cross-Stitch 14-Layer Integration
=========================================================

Tests cover all 14 layers of the integration:
- Layer 1: PQC-gated lattice construction
- Layer 2-4: Signed context projection to Poincare
- Layer 5: Governance-aware hyperbolic distance
- Layer 6-7: Dynamic realm breathing
- Layer 8: Light/shadow clustering
- Layer 9-11: Hyperpath validation with spectral coherence
- Layer 12-13: Amplified path costs (harmonic scaling)
- Layer 14: Audio axis sonification
"""

import pytest
import numpy as np
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from crypto.dual_lattice_integration import (
    # Layer 1
    authorize_pqc_level,
    build_lattice_point_gated,
    # Layer 2-4
    GeoContext,
    realify_with_sign,
    project_to_poincare_with_realm,
    layers_2_4_process,
    RealmType,
    # Layer 5
    governance_aware_distance,
    layer_5_evaluate,
    # Layer 6-7
    breathing_transform,
    apply_realm_breathing,
    LIGHT_BREATH_FACTOR,
    SHADOW_BREATH_FACTOR,
    # Layer 8
    hierarchical_realm_clustering,
    layer_8_cluster,
    # Layer 9-11
    spectral_coherence,
    triadic_temporal_distance,
    validate_hyperpath,
    # Layer 12-13
    harmonic_scaling,
    compute_path_cost,
    layer_12_13_evaluate,
    HARMONIC_BASE_R,
    # Layer 14
    coord_to_frequency,
    hyperpath_to_audio,
    layer_14_sonify,
    # Integration
    DualLatticeIntegrator,
    LayerDecision
)

from crypto.dual_lattice import SacredTongue, FluxState


class TestLayer1PQCGating:
    """Test Layer 1: PQC-gated lattice construction."""

    def test_authorize_sufficient_levels(self):
        """Kyber-3 + Dilithium-3 should pass."""
        authorized, reason = authorize_pqc_level(3, 3)
        assert authorized is True
        assert "authorized" in reason.lower()

    def test_reject_low_kyber(self):
        """Kyber-2 should be rejected."""
        authorized, reason = authorize_pqc_level(2, 3)
        assert authorized is False
        assert "kyber" in reason.lower()

    def test_reject_low_dilithium(self):
        """Dilithium-2 should be rejected."""
        authorized, reason = authorize_pqc_level(3, 2)
        assert authorized is False
        assert "dilithium" in reason.lower()

    def test_high_security_levels_pass(self):
        """Kyber-5 + Dilithium-5 should pass."""
        authorized, _ = authorize_pqc_level(5, 5)
        assert authorized is True

    def test_build_lattice_point_gated_success(self):
        """Build lattice point with valid PQC levels."""
        vector, decision = build_lattice_point_gated(
            tongues={SacredTongue.KO: 0.9, SacredTongue.AV: 0.5},
            intent=0.7,
            flux_state=FluxState.POLLY,
            kyber_level=3,
            dilithium_level=3
        )
        assert vector is not None
        assert decision.layer == 1
        assert decision.decision == "ALLOW"

    def test_build_lattice_point_gated_fail(self):
        """Reject lattice point with weak PQC."""
        vector, decision = build_lattice_point_gated(
            tongues={SacredTongue.KO: 0.9},
            intent=0.5,
            flux_state=FluxState.QUASI,
            kyber_level=1,
            dilithium_level=2
        )
        assert vector is None
        assert decision.decision == "DENY"


class TestLayers2to4Projection:
    """Test Layers 2-4: Realification to Poincare projection."""

    def test_realify_positive_intent(self):
        """Positive intent should be preserved."""
        context = GeoContext(
            location=np.array([0.1, 0.2, 0.3]),
            intent_strength=0.8,
            temporal_offset=0.0,
            semantic_weight=1.0
        )
        real_vec = realify_with_sign(context)
        assert real_vec[3] == 0.8  # Intent at index 3

    def test_realify_negative_intent(self):
        """Negative intent for shadows should be preserved."""
        context = GeoContext(
            location=np.array([0.0, 0.0, 0.0]),
            intent_strength=-0.5,
            temporal_offset=0.1,
            semantic_weight=0.8
        )
        real_vec = realify_with_sign(context)
        assert real_vec[3] == -0.5

    def test_project_light_realm(self):
        """Positive intent projects to light realm."""
        real_vec = np.array([0.1, 0.1, 0.1, 0.5, 0.0, 1.0])
        projected, realm = project_to_poincare_with_realm(real_vec)
        assert realm == RealmType.LIGHT
        assert np.linalg.norm(projected) < 1.0

    def test_project_shadow_realm(self):
        """Negative intent projects to shadow realm."""
        real_vec = np.array([0.1, 0.1, 0.1, -0.5, 0.0, 1.0])
        projected, realm = project_to_poincare_with_realm(real_vec)
        assert realm == RealmType.SHADOW

    def test_project_stays_in_ball(self):
        """Large vectors are normalized to stay in ball."""
        real_vec = np.array([2.0, 2.0, 2.0, 0.5, 0.0, 1.0])
        projected, _ = project_to_poincare_with_realm(real_vec)
        assert np.linalg.norm(projected) < 1.0

    def test_layers_2_4_full_process(self):
        """Full processing through layers 2-4."""
        context = GeoContext(
            location=np.array([0.2, 0.3, 0.1]),
            intent_strength=0.7,
            temporal_offset=0.05,
            semantic_weight=1.0
        )
        projected, realm, decision = layers_2_4_process(context)
        assert realm == RealmType.LIGHT
        assert decision.layer == 4
        assert np.linalg.norm(projected) < 1.0


class TestLayer5GovernanceDistance:
    """Test Layer 5: Governance-aware hyperbolic distance."""

    def test_distance_same_point(self):
        """Distance from point to itself is 0."""
        point = np.array([0.2, 0.3, 0.0])
        d = governance_aware_distance(point, point)
        assert d < 0.01

    def test_distance_symmetric(self):
        """Distance is symmetric."""
        a = np.array([0.1, 0.2, 0.0])
        b = np.array([0.3, 0.1, 0.0])
        assert abs(governance_aware_distance(a, b) - governance_aware_distance(b, a)) < 1e-6

    def test_phase_affects_distance(self):
        """Phase difference increases total distance."""
        a = np.array([0.2, 0.0, 0.0])
        b = np.array([0.0, 0.2, 0.0])
        d1 = governance_aware_distance(a, b, 0.0, 0.0)
        d2 = governance_aware_distance(a, b, 0.0, np.pi)
        assert d2 > d1

    def test_layer_5_allow_near_origin(self):
        """Points near origin should be ALLOWED."""
        position = np.array([0.1, 0.0, 0.0])
        origin = np.zeros(3)
        decision = layer_5_evaluate(position, origin)
        assert decision.decision == "ALLOW"

    def test_layer_5_deny_far_points(self):
        """Far points should be DENIED."""
        position = np.array([0.9, 0.0, 0.0])
        target = np.array([-0.9, 0.0, 0.0])
        decision = layer_5_evaluate(position, target)
        # Large distance should lead to DENY or QUARANTINE
        assert decision.decision in ["DENY", "QUARANTINE"]


class TestLayers6to7Breathing:
    """Test Layers 6-7: Dynamic realm breathing."""

    def test_breathing_expansion(self):
        """b > 1 expands hyperbolic space (norm increases via tanh scaling)."""
        position = np.array([0.5, 0.0, 0.0])
        breathed = breathing_transform(position, b=1.5)
        # tanh(b * arctanh(r)) with b > 1 increases the radial coordinate
        assert np.linalg.norm(breathed) > np.linalg.norm(position)

    def test_breathing_contraction(self):
        """b < 1 contracts hyperbolic space (norm decreases via tanh scaling)."""
        position = np.array([0.3, 0.0, 0.0])
        breathed = breathing_transform(position, b=0.5)
        # tanh(b * arctanh(r)) with b < 1 decreases the radial coordinate
        assert np.linalg.norm(breathed) < np.linalg.norm(position)

    def test_light_realm_breathing(self):
        """Light realm uses expansion factor."""
        position = np.array([0.5, 0.3, 0.0])
        breathed, phase, decision = apply_realm_breathing(position, RealmType.LIGHT)
        assert decision.metadata["breathing_factor"] == LIGHT_BREATH_FACTOR

    def test_shadow_realm_breathing(self):
        """Shadow realm uses contraction factor."""
        position = np.array([0.5, 0.3, 0.0])
        breathed, phase, decision = apply_realm_breathing(position, RealmType.SHADOW)
        assert decision.metadata["breathing_factor"] == SHADOW_BREATH_FACTOR

    def test_phase_computed(self):
        """Phase should be computed from position."""
        position = np.array([0.5, 0.5, 0.0])
        _, phase, _ = apply_realm_breathing(position, RealmType.BALANCED)
        expected_phase = np.arctan2(0.5, 0.5)
        assert abs(phase - expected_phase) < 0.1  # Allow for breathing adjustment


class TestLayer8Clustering:
    """Test Layer 8: Light/shadow clustering."""

    def test_cluster_two_groups(self):
        """Should separate two distinct groups."""
        points = [
            np.array([0.1, 0.1, 0.0]),  # Near origin
            np.array([0.1, 0.0, 0.1]),  # Near origin
            np.array([0.8, 0.1, 0.0]),  # Far from origin
            np.array([0.8, 0.0, 0.1]),  # Far from origin
        ]
        realms = hierarchical_realm_clustering(points, n_clusters=2)
        # First two should be same realm, last two should be same realm
        assert realms[0] == realms[1]
        assert realms[2] == realms[3]
        assert realms[0] != realms[2]

    def test_single_point_balanced(self):
        """Single point returns BALANCED."""
        points = [np.array([0.3, 0.0, 0.0])]
        realms = hierarchical_realm_clustering(points)
        assert realms[0] == RealmType.BALANCED

    def test_layer_8_cluster_decision(self):
        """Layer 8 should produce cluster decision."""
        points = [
            np.array([0.1, 0.1, 0.0]),
            np.array([0.7, 0.7, 0.0]),
        ]
        realms, decision = layer_8_cluster(points)
        assert decision.layer == 8
        assert len(realms) == 2


class TestLayers9to11PathValidation:
    """Test Layers 9-11: Hyperpath validation."""

    def test_spectral_coherence_smooth_path(self):
        """Smooth path should have high coherence."""
        path = [np.array([i * 0.1, 0.0, 0.0]) for i in range(10)]
        coherence = spectral_coherence(path)
        assert coherence > 0.5

    def test_spectral_coherence_single_point(self):
        """Single point returns 1.0."""
        path = [np.array([0.5, 0.0, 0.0])]
        coherence = spectral_coherence(path)
        assert coherence == 1.0

    def test_triadic_geodesic_path(self):
        """Geodesic path should have low triadic distance."""
        path = [np.array([i * 0.1, 0.0, 0.0]) for i in range(5)]
        d_tri = triadic_temporal_distance(path)
        assert d_tri < 0.5

    def test_triadic_short_path(self):
        """Path with < 3 points returns 0."""
        path = [np.array([0.0, 0.0, 0.0]), np.array([0.5, 0.0, 0.0])]
        d_tri = triadic_temporal_distance(path)
        assert d_tri == 0.0

    def test_validate_smooth_path(self):
        """Smooth path should be valid."""
        path = [np.array([i * 0.1, 0.0, 0.0]) for i in range(10)]
        valid, decision = validate_hyperpath(path)
        assert valid is True
        assert decision.decision == "ALLOW"

    def test_validate_empty_path(self):
        """Empty path should be invalid."""
        valid, decision = validate_hyperpath([])
        assert valid is False
        assert decision.decision == "DENY"


class TestLayers12to13HarmonicScaling:
    """Test Layers 12-13: Harmonic scaling and decision."""

    def test_harmonic_scaling_zero_distance(self):
        """H(0) = 1/(1+0) = 1.0."""
        h = harmonic_scaling(0.0)
        assert abs(h - 1.0) < 1e-6

    def test_harmonic_scaling_decreases_with_distance(self):
        """Larger distance = lower safety score."""
        h1 = harmonic_scaling(0.5)
        h2 = harmonic_scaling(1.0)
        assert h2 < h1

    def test_harmonic_scaling_bounded(self):
        """H(d) = 1/(1+d+2*pd) is bounded in (0, 1]."""
        d = 0.5
        pd = 0.1
        expected = 1.0 / (1.0 + d + 2.0 * pd)
        actual = harmonic_scaling(d, pd)
        assert abs(actual - expected) < 1e-6
        assert 0 < actual <= 1.0

    def test_path_cost_short_path(self):
        """Short path has low cost."""
        path = [np.array([0.0, 0.0, 0.0]), np.array([0.1, 0.0, 0.0])]
        cost = compute_path_cost(path)
        assert cost < 10.0

    def test_layer_12_13_allow_low_risk(self):
        """Low-risk path should be ALLOWED."""
        path = [np.array([0.0, 0.0, 0.0]), np.array([0.05, 0.0, 0.0])]
        decision_str, decision = layer_12_13_evaluate(path)
        assert decision_str == "ALLOW"


class TestLayer14Sonification:
    """Test Layer 14: Audio axis sonification."""

    def test_coord_to_frequency_center(self):
        """Center point gives base frequency."""
        coord = np.array([0.0, 0.0, 0.0])
        freq = coord_to_frequency(coord, 440.0)
        # Near center, should be close to base (adjusted for 0 norm)
        assert 200 < freq < 800

    def test_coord_to_frequency_range(self):
        """Frequencies should be in valid range."""
        coords = [
            np.array([0.0, 0.0, 0.0]),
            np.array([0.5, 0.5, 0.5]),
            np.array([0.9, 0.0, 0.0]),
        ]
        for coord in coords:
            freq = coord_to_frequency(coord)
            assert 110 <= freq <= 1760

    def test_hyperpath_light_positive_freq(self):
        """Light realm produces positive frequencies."""
        path = [np.array([0.1, 0.0, 0.0])]
        realms = [RealmType.LIGHT]
        frequencies = hyperpath_to_audio(path, realms)
        assert frequencies[0] > 0

    def test_hyperpath_shadow_negative_freq(self):
        """Shadow realm produces negative (signed) frequencies."""
        path = [np.array([0.5, 0.0, 0.0])]
        realms = [RealmType.SHADOW]
        frequencies = hyperpath_to_audio(path, realms)
        assert frequencies[0] < 0

    def test_layer_14_sonify(self):
        """Layer 14 produces audio signature."""
        path = [np.array([0.1, 0.0, 0.0]), np.array([0.3, 0.0, 0.0])]
        realms = [RealmType.LIGHT, RealmType.LIGHT]
        frequencies, decision = layer_14_sonify(path, realms)
        assert len(frequencies) == 2
        assert decision.layer == 14
        assert "signature_hash" in decision.metadata


class TestDualLatticeIntegrator:
    """Test complete 14-layer integration."""

    @pytest.fixture
    def integrator(self):
        return DualLatticeIntegrator()

    def test_process_low_sensitivity_action(self, integrator):
        """Low sensitivity action should be ALLOWED."""
        result = integrator.process_action("navigate", "https://example.com", 0.2)
        assert result.final_decision in ["ALLOW", "ESCALATE"]
        assert result.trust_score > 0.3

    def test_process_high_sensitivity_action(self, integrator):
        """High sensitivity action should have lower trust."""
        result = integrator.process_action("execute", "rm -rf /", 0.95)
        # High sensitivity reduces trust
        assert result.trust_score < 0.8 or result.final_decision != "ALLOW"

    def test_process_returns_all_layer_decisions(self, integrator):
        """Result should contain decisions from multiple layers."""
        result = integrator.process_action("read", "file.txt", 0.5)
        layer_numbers = [d.layer for d in result.decisions]
        # Should have decisions from layers 1, 4, 5, 7, 8, 11, 13, 14
        assert 1 in layer_numbers
        assert 13 in layer_numbers or 14 in layer_numbers

    def test_audio_signature_generated(self, integrator):
        """Audio signature should be generated."""
        result = integrator.process_action("read", "test.py", 0.3)
        assert result.audio_signature is not None
        assert len(result.audio_signature) > 0

    def test_realm_assignment(self, integrator):
        """Realm should be assigned based on context."""
        result = integrator.process_action("navigate", "https://trusted.com", 0.1)
        assert result.realm in [RealmType.LIGHT, RealmType.BALANCED, RealmType.SHADOW]


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_vector_projection(self):
        """Zero vector should project correctly."""
        real_vec = np.zeros(6)
        projected, realm = project_to_poincare_with_realm(real_vec)
        assert np.allclose(projected, np.zeros(6))

    def test_empty_cluster_points(self):
        """Empty points list should return empty realms."""
        realms = hierarchical_realm_clustering([])
        assert realms == []

    def test_breathing_at_origin(self):
        """Breathing at origin should not change position."""
        position = np.zeros(3)
        breathed = breathing_transform(position, b=1.5)
        assert np.allclose(breathed, position)

    def test_very_small_coherence_threshold(self):
        """Very small threshold should still work."""
        path = [np.array([i * 0.1, 0.0, 0.0]) for i in range(5)]
        valid, _ = validate_hyperpath(path, coherence_threshold=0.01)
        assert valid is True

    def test_single_point_path_cost(self):
        """Single point path has zero cost."""
        path = [np.array([0.5, 0.0, 0.0])]
        cost = compute_path_cost(path)
        assert cost == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
