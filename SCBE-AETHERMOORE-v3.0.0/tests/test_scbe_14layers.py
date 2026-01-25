#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Test Suite for SCBE 14-Layer System
=================================================
Tests each layer individually and validates full pipeline integration.
"""

import sys
import os

# Set UTF-8 encoding for Windows compatibility
if sys.platform == 'win32':
    # Reconfigure stdout/stderr to use UTF-8 encoding
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from scbe_14layer_reference import *


class TestSCBE14Layers:
    """Test suite for all 14 SCBE layers."""

    def __init__(self):
        self.D = 6
        self.n = 2 * self.D
        self.eps = 1e-5
        self.eps_ball = 0.01
        self.passed = 0
        self.failed = 0

    def assert_test(self, condition: bool, test_name: str):
        """Assert and track test results."""
        if condition:
            print(f"  ✓ {test_name}")
            self.passed += 1
        else:
            print(f"  ✗ {test_name}")
            self.failed += 1

    def test_layer_1_complex_state(self):
        """Test Layer 1: Complex state construction."""
        print("\n[Layer 1] Complex State Tests:")

        # Test 1: Output dimension
        t = np.random.rand(2 * self.D)
        c = layer_1_complex_state(t, self.D)
        self.assert_test(c.shape == (self.D,), "Output has correct dimension")
        self.assert_test(np.iscomplexobj(c), "Output is complex-valued")

        # Test 2: Zero phases → real output
        t_real = np.concatenate([np.ones(self.D), np.zeros(self.D)])
        c_real = layer_1_complex_state(t_real, self.D)
        self.assert_test(np.allclose(np.imag(c_real), 0), "Zero phases produce real values")

        # Test 3: Amplitude encoding
        amplitudes = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        phases = np.zeros(self.D)
        t = np.concatenate([amplitudes, phases])
        c = layer_1_complex_state(t, self.D)
        self.assert_test(np.allclose(np.abs(c), amplitudes), "Amplitudes correctly encoded")

    def test_layer_2_realification(self):
        """Test Layer 2: Realification."""
        print("\n[Layer 2] Realification Tests:")

        # Test 1: Dimension doubling
        c = np.array([1+2j, 3+4j, 5+6j, 7+8j, 9+10j, 11+12j])
        x = layer_2_realification(c)
        self.assert_test(x.shape == (2 * self.D,), "Output dimension is 2D")
        self.assert_test(np.isrealobj(x), "Output is real-valued")

        # Test 2: Isometry (norm preservation)
        c = np.random.randn(self.D) + 1j * np.random.randn(self.D)
        x = layer_2_realification(c)
        c_norm = np.linalg.norm(c)
        x_norm = np.linalg.norm(x)
        self.assert_test(np.isclose(c_norm, x_norm), "Isometry: norm preserved")

        # Test 3: Invertibility
        real_part = x[:self.D]
        imag_part = x[self.D:]
        c_recovered = real_part + 1j * imag_part
        self.assert_test(np.allclose(c, c_recovered), "Invertible: can recover complex state")

    def test_layer_3_weighted_transform(self):
        """Test Layer 3: Weighted transform."""
        print("\n[Layer 3] Weighted Transform Tests:")

        # Test 1: Dimension preservation
        x = np.random.randn(self.n)
        x_G = layer_3_weighted_transform(x)
        self.assert_test(x_G.shape == x.shape, "Dimension preserved")

        # Test 2: Non-trivial transformation
        self.assert_test(not np.allclose(x, x_G), "Transform is non-trivial")

        # Test 3: Custom SPD matrix
        G = np.eye(self.n)
        x_G_identity = layer_3_weighted_transform(x, G)
        self.assert_test(np.allclose(x, x_G_identity), "Identity matrix → identity transform")

        # Test 4: Linearity
        x1 = np.random.randn(self.n)
        x2 = np.random.randn(self.n)
        x_sum = layer_3_weighted_transform(x1 + x2)
        x_sum_alt = layer_3_weighted_transform(x1) + layer_3_weighted_transform(x2)
        self.assert_test(np.allclose(x_sum, x_sum_alt), "Linear transformation")

    def test_layer_4_poincare_embedding(self):
        """Test Layer 4: Poincaré embedding with clamping."""
        print("\n[Layer 4] Poincaré Embedding Tests:")

        # Test 1: Output in Poincaré ball
        x_G = np.random.randn(self.n) * 10
        u = layer_4_poincare_embedding(x_G)
        self.assert_test(np.linalg.norm(u) < 1.0, "Output ||u|| < 1")

        # Test 2: Clamping to compact sub-ball
        max_norm = 1.0 - self.eps_ball
        self.assert_test(np.linalg.norm(u) <= max_norm, f"Clamped to ||u|| ≤ {max_norm}")

        # Test 3: Zero input → zero output
        u_zero = layer_4_poincare_embedding(np.zeros(self.n))
        self.assert_test(np.allclose(u_zero, 0), "Zero input → zero output")

        # Test 4: Large input saturates near boundary
        x_large = np.ones(self.n) * 1000
        u_large = layer_4_poincare_embedding(x_large)
        self.assert_test(np.linalg.norm(u_large) > 0.9, "Large input saturates")

    def test_layer_5_hyperbolic_distance(self):
        """Test Layer 5: Hyperbolic distance."""
        print("\n[Layer 5] Hyperbolic Distance Tests:")

        # Test 1: Distance to self is zero
        u = np.random.rand(self.n) * 0.5
        d_self = layer_5_hyperbolic_distance(u, u)
        self.assert_test(np.isclose(d_self, 0), "d(u, u) = 0")

        # Test 2: Symmetry
        v = np.random.rand(self.n) * 0.5
        d_uv = layer_5_hyperbolic_distance(u, v)
        d_vu = layer_5_hyperbolic_distance(v, u)
        self.assert_test(np.isclose(d_uv, d_vu), "Symmetry: d(u,v) = d(v,u)")

        # Test 3: Positive definiteness
        self.assert_test(d_uv > 0, "d(u, v) > 0 for u ≠ v")

        # Test 4: Distance increases with separation
        w = np.random.rand(self.n) * 0.8
        d_uw = layer_5_hyperbolic_distance(u, w)
        self.assert_test(d_uw > 0, "Distance is positive")

    def test_layer_6_breathing_transform(self):
        """Test Layer 6: Breathing transform."""
        print("\n[Layer 6] Breathing Transform Tests:")

        # Test 1: Output stays in ball
        u = np.random.rand(self.n) * 0.5
        u_breath = layer_6_breathing_transform(u, b=1.5)
        self.assert_test(np.linalg.norm(u_breath) < 1.0, "Output stays in 𝔹^n")

        # Test 2: b > 1 expands radius
        u_expand = layer_6_breathing_transform(u, b=1.5)
        self.assert_test(np.linalg.norm(u_expand) > np.linalg.norm(u), "b > 1 expands")

        # Test 3: b < 1 contracts radius
        u_contract = layer_6_breathing_transform(u, b=0.7)
        self.assert_test(np.linalg.norm(u_contract) < np.linalg.norm(u), "b < 1 contracts")

        # Test 4: b = 1 approximately identity
        u_identity = layer_6_breathing_transform(u, b=1.0)
        self.assert_test(np.allclose(u, u_identity, rtol=0.01), "b = 1 ≈ identity")

        # Test 5: NOT an isometry (distances change)
        v = np.random.rand(self.n) * 0.5
        d_before = layer_5_hyperbolic_distance(u, v)
        u_b = layer_6_breathing_transform(u, b=1.5)
        v_b = layer_6_breathing_transform(v, b=1.5)
        d_after = layer_5_hyperbolic_distance(u_b, v_b)
        self.assert_test(not np.isclose(d_before, d_after), "NOT isometry (distance changes)")

    def test_layer_7_phase_transform(self):
        """Test Layer 7: Phase transform (isometry)."""
        print("\n[Layer 7] Phase Transform Tests:")

        # Test 1: Output stays in ball
        u = np.random.rand(self.n) * 0.5
        a = np.zeros(self.n)
        Q = np.eye(self.n)
        u_phase = layer_7_phase_transform(u, a, Q)
        self.assert_test(np.linalg.norm(u_phase) < 1.0, "Output stays in 𝔹^n")

        # Test 2: Identity transform
        u_identity = layer_7_phase_transform(u, np.zeros(self.n), np.eye(self.n))
        self.assert_test(np.allclose(u, u_identity), "Identity: a=0, Q=I → u")

        # Test 3: Rotation is isometry (preserves distances)
        v = np.random.rand(self.n) * 0.5
        theta = np.pi / 4
        Q_rot = np.eye(self.n)
        Q_rot[0, 0] = np.cos(theta)
        Q_rot[0, 1] = -np.sin(theta)
        Q_rot[1, 0] = np.sin(theta)
        Q_rot[1, 1] = np.cos(theta)

        d_before = layer_5_hyperbolic_distance(u, v)
        u_rot = layer_7_phase_transform(u, a, Q_rot)
        v_rot = layer_7_phase_transform(v, a, Q_rot)
        d_after = layer_5_hyperbolic_distance(u_rot, v_rot)

        self.assert_test(np.isclose(d_before, d_after, rtol=0.01), "Rotation preserves distance (isometry)")

    def test_layer_8_realm_distance(self):
        """Test Layer 8: Realm distance."""
        print("\n[Layer 8] Realm Distance Tests:")

        # Test 1: Returns minimum distance
        u = np.zeros(self.n)
        realms = [
            np.ones(self.n) * 0.1,
            np.ones(self.n) * 0.2,
            np.ones(self.n) * 0.3,
        ]
        d_star, distances = layer_8_realm_distance(u, realms)
        self.assert_test(d_star == np.min(distances), "d* = min(distances)")

        # Test 2: Distances array has correct length
        self.assert_test(len(distances) == len(realms), "Distance array length = K")

        # Test 3: All distances non-negative
        self.assert_test(np.all(distances >= 0), "All distances ≥ 0")

    def test_layer_9_spectral_coherence(self):
        """Test Layer 9: Spectral coherence."""
        print("\n[Layer 9] Spectral Coherence Tests:")

        # Test 1: Output in [0, 1]
        signal = np.random.randn(256)
        S_spec = layer_9_spectral_coherence(signal)
        self.assert_test(0 <= S_spec <= 1, "S_spec ∈ [0, 1]")

        # Test 2: Pure low-frequency signal → high coherence
        signal_low = np.sin(np.linspace(0, 2*np.pi, 256))
        S_low = layer_9_spectral_coherence(signal_low)
        self.assert_test(S_low > 0.5, "Low-frequency signal → high coherence")

        # Test 3: White noise → moderate coherence
        signal_noise = np.random.randn(256)
        S_noise = layer_9_spectral_coherence(signal_noise)
        self.assert_test(0.3 < S_noise < 0.7, "White noise → moderate coherence")

        # Test 4: None input → default 0.5
        S_none = layer_9_spectral_coherence(None)
        self.assert_test(S_none == 0.5, "None input → 0.5")

    def test_layer_10_spin_coherence(self):
        """Test Layer 10: Spin coherence."""
        print("\n[Layer 10] Spin Coherence Tests:")

        # Test 1: Output in [0, 1]
        phases = np.random.rand(self.D) * 2 * np.pi
        C_spin = layer_10_spin_coherence(phases)
        self.assert_test(0 <= C_spin <= 1, "C_spin ∈ [0, 1]")

        # Test 2: Aligned phases → high coherence
        phases_aligned = np.zeros(self.D)
        C_aligned = layer_10_spin_coherence(phases_aligned)
        self.assert_test(C_aligned > 0.99, "Aligned phases → C_spin ≈ 1")

        # Test 3: Random phases → low coherence
        phases_random = np.random.rand(100) * 2 * np.pi
        C_random = layer_10_spin_coherence(phases_random)
        self.assert_test(C_random < 0.3, "Random phases → low coherence")

        # Test 4: Works with complex phasors
        phasors = np.exp(1j * phases)
        C_phasor = layer_10_spin_coherence(phasors)
        self.assert_test(0 <= C_phasor <= 1, "Works with complex input")

    def test_layer_11_triadic_temporal(self):
        """Test Layer 11: Triadic temporal aggregation."""
        print("\n[Layer 11] Triadic Temporal Tests:")

        # Test 1: Output in [0, 1] (normalized)
        d_tri = layer_11_triadic_temporal(0.5, 0.3, 0.2)
        self.assert_test(0 <= d_tri <= 1, "d_tri ∈ [0, 1]")

        # Test 2: Weights sum to 1 (validated internally)
        try:
            d_tri = layer_11_triadic_temporal(0.1, 0.2, 0.3,
                                             lambda1=0.33, lambda2=0.33, lambda3=0.34)
            self.assert_test(True, "Weights sum to 1 validation passes")
        except AssertionError:
            self.assert_test(False, "Weights sum to 1 validation passes")

        # Test 3: Equal inputs → output equals input
        d_equal = layer_11_triadic_temporal(0.5, 0.5, 0.5)
        self.assert_test(np.isclose(d_equal, 0.5), "Equal inputs → equal output")

    def test_layer_12_harmonic_scaling(self):
        """Test Layer 12: Harmonic scaling."""
        print("\n[Layer 12] Harmonic Scaling Tests:")

        # Test 1: H(0) = 1
        H_zero = layer_12_harmonic_scaling(0)
        self.assert_test(np.isclose(H_zero, 1.0), "H(0, R) = 1")

        # Test 2: Monotonically increasing
        H_small = layer_12_harmonic_scaling(0.1)
        H_large = layer_12_harmonic_scaling(0.5)
        self.assert_test(H_large > H_small, "H(d) increases with d")

        # Test 3: Exponential growth
        H_1 = layer_12_harmonic_scaling(1.0, R=np.e)
        self.assert_test(np.isclose(H_1, np.e), "H(1, e) = e")

        # Test 4: Different base
        H_2 = layer_12_harmonic_scaling(2.0, R=2.0)
        self.assert_test(np.isclose(H_2, 2.0**4), "H(2, 2) = 2^4 = 16")

    def test_layer_13_risk_decision(self):
        """Test Layer 13: Risk decision."""
        print("\n[Layer 13] Risk Decision Tests:")

        # Test 1: Low risk → ALLOW
        decision = layer_13_risk_decision(0.1, H=1.0, theta1=0.33, theta2=0.67)
        self.assert_test(decision == "ALLOW", "Low risk → ALLOW")

        # Test 2: Medium risk → QUARANTINE
        decision = layer_13_risk_decision(0.5, H=1.0, theta1=0.33, theta2=0.67)
        self.assert_test(decision == "QUARANTINE", "Medium risk → QUARANTINE")

        # Test 3: High risk → DENY
        decision = layer_13_risk_decision(0.9, H=1.0, theta1=0.33, theta2=0.67)
        self.assert_test(decision == "DENY", "High risk → DENY")

        # Test 4: Harmonic amplification increases risk
        decision_no_amp = layer_13_risk_decision(0.3, H=1.0, theta1=0.33, theta2=0.67)
        decision_amp = layer_13_risk_decision(0.3, H=2.0, theta1=0.33, theta2=0.67)
        # 0.3 * 1.0 = 0.3 < 0.33 → ALLOW
        # 0.3 * 2.0 = 0.6 > 0.33 → QUARANTINE or DENY
        self.assert_test(decision_no_amp == "ALLOW" and decision_amp != "ALLOW",
                        "Harmonic amplification escalates decision")

    def test_layer_14_audio_axis(self):
        """Test Layer 14: Audio axis."""
        print("\n[Layer 14] Audio Axis Tests:")

        # Test 1: Output in [0, 1]
        audio = np.random.randn(256)
        S_audio = layer_14_audio_axis(audio)
        self.assert_test(0 <= S_audio <= 1, "S_audio ∈ [0, 1]")

        # Test 2: Pure tone → high stability
        audio_tone = np.sin(np.linspace(0, 10*np.pi, 512))
        S_tone = layer_14_audio_axis(audio_tone)
        self.assert_test(S_tone > 0.3, "Pure tone → moderate/high stability")

        # Test 3: None input → default 0.5
        S_none = layer_14_audio_axis(None)
        self.assert_test(S_none == 0.5, "None input → 0.5")

    def test_full_pipeline(self):
        """Test full 14-layer pipeline integration."""
        print("\n[Full Pipeline] Integration Tests:")

        # Test 1: Pipeline executes without errors
        t = np.random.rand(2 * self.D)
        try:
            result = scbe_14layer_pipeline(t)
            self.assert_test(True, "Pipeline executes successfully")
        except Exception as e:
            self.assert_test(False, f"Pipeline executes successfully (ERROR: {e})")
            return

        # Test 2: All required keys present
        required_keys = ['decision', 'risk_base', 'risk_prime', 'd_star',
                        'coherence', 'geometry']
        all_present = all(k in result for k in required_keys)
        self.assert_test(all_present, "All required output keys present")

        # Test 3: Decision is valid
        valid_decisions = ["ALLOW", "QUARANTINE", "DENY"]
        self.assert_test(result['decision'] in valid_decisions,
                        f"Valid decision: {result['decision']}")

        # Test 4: Risk values are non-negative
        self.assert_test(result['risk_base'] >= 0 and result['risk_prime'] >= 0,
                        "Risk values are non-negative")

        # Test 5: Coherence values in [0, 1]
        coherence = result['coherence']
        all_in_range = all(0 <= v <= 1 for v in coherence.values())
        self.assert_test(all_in_range, "All coherence values ∈ [0, 1]")

        # Test 6: Geometry values valid
        geometry = result['geometry']
        all_in_ball = all(v < 1.0 for v in geometry.values())
        self.assert_test(all_in_ball, "All geometry norms < 1")

    def run_all_tests(self):
        """Run complete test suite."""
        print("=" * 80)
        print("SCBE 14-Layer Test Suite")
        print("=" * 80)

        self.test_layer_1_complex_state()
        self.test_layer_2_realification()
        self.test_layer_3_weighted_transform()
        self.test_layer_4_poincare_embedding()
        self.test_layer_5_hyperbolic_distance()
        self.test_layer_6_breathing_transform()
        self.test_layer_7_phase_transform()
        self.test_layer_8_realm_distance()
        self.test_layer_9_spectral_coherence()
        self.test_layer_10_spin_coherence()
        self.test_layer_11_triadic_temporal()
        self.test_layer_12_harmonic_scaling()
        self.test_layer_13_risk_decision()
        self.test_layer_14_audio_axis()
        self.test_full_pipeline()

        print("\n" + "=" * 80)
        print(f"Test Results: {self.passed} passed, {self.failed} failed")
        if self.failed == 0:
            print("✓ ALL TESTS PASSED")
        else:
            print(f"✗ {self.failed} TESTS FAILED")
        print("=" * 80)

        return self.failed == 0


if __name__ == "__main__":
    tester = TestSCBE14Layers()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
