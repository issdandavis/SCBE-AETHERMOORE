"""
Sacred Eggs Reference Tests
============================

Tests for the patent-hardened Sacred Eggs decrypt-or-noise gate.
Covers: geometry, oscillation, fractal dimension, HATCH decrypt-or-noise,
fail-to-noise determinism, BFT quorum rule, and boundary/fuzz cases.

@layer Layer 8, Layer 13
@component Sacred Eggs Reference Validation
"""

import math
import random
import pytest
import numpy as np

from src.symphonic_cipher.scbe_aethermoore.sacred_eggs_ref import (
    Policy,
    SacredEgg,
    StateSnapshot,
    StateVector,
    compute_box_counting_dimension,
    bucket_ring,
    sphere_quantize,
    check_geometric_predicate,
    check_oscillation_predicate,
    check_fractal_predicate,
    hatch_ref,
    hkdf_sha256,
    prng_stream,
    hash_state,
    build_domain_separation_tag,
    norm3,
    T_PASS,
    T_HOLD,
    T_FAIL,
    PHI,
)


# ==============================================================================
# HELPERS
# ==============================================================================


def _now_fixed(t: int):
    """Return a fixed-time function for deterministic oscillation tests."""
    return lambda: t


def _mk_state(nav=(0.1, 0.1, 0.1), osc=0, history=None):
    """Create a minimal StateVector with given nav triad and oscillation."""
    vec = [0.0] * 21
    vec[3], vec[4], vec[5] = nav
    if history is None:
        history = []
    return StateVector(
        vector=tuple(vec), history=history, attestations=[], oscillation_state=osc
    )


def _mk_policy(**overrides):
    """Create a default Policy with optional overrides."""
    defaults = dict(
        primary_tongue="KO",
        required_ring=3,
        required_cell="S2:323232",
        path_mode="solitary",
        min_weight=1.0,
        min_signatures=0,
        req_oscillation_phase=-1,
        max_drift_variance=1.0,
        require_phi_convergence=False,
    )
    defaults.update(overrides)
    return Policy(**defaults)


# ==============================================================================
# A. RING BUCKETING
# ==============================================================================


@pytest.mark.unit
class TestBucketRing:
    """Ring boundary classification tests."""

    def test_core_region(self):
        assert bucket_ring(0.0) == 0
        assert bucket_ring(0.2999) == 0

    def test_inner_region(self):
        assert bucket_ring(0.3) == 1
        assert bucket_ring(0.6999) == 1

    def test_outer_region(self):
        assert bucket_ring(0.7) == 2
        assert bucket_ring(0.8999) == 2

    def test_edge_region(self):
        assert bucket_ring(0.9) == 3
        assert bucket_ring(0.9999) == 3

    def test_out_of_bounds(self):
        assert bucket_ring(1.0) == 99
        assert bucket_ring(1.5) == 99


# ==============================================================================
# B. SPHERE QUANTIZATION
# ==============================================================================


@pytest.mark.unit
class TestSphereQuantize:
    """Cell ID quantization tests."""

    def test_origin_cell(self):
        cell = sphere_quantize((0.0, 0.0, 0.0))
        assert cell.startswith("S2:")
        assert len(cell) == 9  # "S2:" + 6 digits

    def test_deterministic(self):
        """Same input always produces same cell."""
        assert sphere_quantize((0.5, 0.5, 0.5)) == sphere_quantize((0.5, 0.5, 0.5))

    def test_different_inputs_different_cells(self):
        assert sphere_quantize((0.0, 0.0, 0.0)) != sphere_quantize((0.5, 0.5, 0.5))


# ==============================================================================
# C. GEOMETRIC PREDICATE
# ==============================================================================


@pytest.mark.unit
class TestGeometricPredicate:
    """Poincaré ball radius and cell matching."""

    def test_matching_cell_and_ring_passes(self):
        nav = (0.0, 0.0, 0.0)
        cell = sphere_quantize(nav)
        policy = _mk_policy(required_ring=1, required_cell=cell)
        st = _mk_state(nav=nav, osc=0)
        assert check_geometric_predicate(policy, st) == T_PASS

    def test_radius_exceeds_ball_fails(self):
        policy = _mk_policy(required_ring=1, required_cell="S2:000000")
        st = _mk_state(nav=(1.0, 0.0, 0.0), osc=0)  # r = 1.0 → out of bounds
        assert check_geometric_predicate(policy, st) == T_FAIL

    def test_wrong_cell_fails(self):
        nav = (0.2, 0.2, 0.2)
        policy = _mk_policy(required_ring=3, required_cell="S2:000000")  # wrong cell
        st = _mk_state(nav=nav, osc=0)
        assert check_geometric_predicate(policy, st) == T_FAIL

    def test_ring_too_high_fails(self):
        """Ring index > required_ring → fail."""
        nav = (0.5, 0.5, 0.5)  # ||nav|| ≈ 0.87 → ring 2
        cell = sphere_quantize(nav)
        policy = _mk_policy(required_ring=1, required_cell=cell)  # requires ring ≤ 1
        st = _mk_state(nav=nav, osc=0)
        assert check_geometric_predicate(policy, st) == T_FAIL

    def test_nan_input_fails(self):
        policy = _mk_policy(required_ring=3, required_cell="S2:000000")
        st = _mk_state(nav=(float("nan"), 0.0, 0.0), osc=0)
        assert check_geometric_predicate(policy, st) == T_FAIL

    def test_inf_input_fails(self):
        policy = _mk_policy(required_ring=3, required_cell="S2:000000")
        st = _mk_state(nav=(float("inf"), 0.0, 0.0), osc=0)
        assert check_geometric_predicate(policy, st) == T_FAIL


# ==============================================================================
# D. OSCILLATION PREDICATE
# ==============================================================================


@pytest.mark.unit
class TestOscillationPredicate:
    """Phase window and replay detection."""

    def test_matching_phase_passes(self):
        policy = _mk_policy(req_oscillation_phase=-1)  # any phase
        # now=25, window=10 → phase = (25//10)%6 = 2
        st = _mk_state(osc=2)
        assert check_oscillation_predicate(policy, st, now_fn=_now_fixed(25), phase_window=10) == T_PASS

    def test_stale_oscillation_fails(self):
        """Replay attack: oscillation_state doesn't match current phase."""
        policy = _mk_policy(req_oscillation_phase=-1)
        st = _mk_state(osc=1)  # stale: current phase is 2
        assert check_oscillation_predicate(policy, st, now_fn=_now_fixed(25), phase_window=10) == T_FAIL

    def test_specific_phase_requirement(self):
        """Policy requires specific phase that doesn't match current."""
        policy = _mk_policy(req_oscillation_phase=4)  # requires phase 4
        st = _mk_state(osc=2)  # current phase = 2
        assert check_oscillation_predicate(policy, st, now_fn=_now_fixed(25), phase_window=10) == T_FAIL

    def test_phase_wraps_mod_6(self):
        """Phase cycles through 0..5."""
        policy = _mk_policy(req_oscillation_phase=-1)
        for t in range(60):
            expected = (t // 10) % 6
            st = _mk_state(osc=expected)
            assert check_oscillation_predicate(policy, st, now_fn=_now_fixed(t), phase_window=10) == T_PASS


# ==============================================================================
# E. FRACTAL PREDICATE (BOX COUNTING)
# ==============================================================================


@pytest.mark.unit
class TestFractalPredicate:
    """Box-counting dimension and φ convergence."""

    def test_insufficient_history_fails(self):
        policy = _mk_policy(require_phi_convergence=True)
        st = _mk_state(history=[])
        assert check_fractal_predicate(policy, st) == T_FAIL

    def test_phi_not_required_passes(self):
        policy = _mk_policy(require_phi_convergence=False)
        st = _mk_state(history=[])
        assert check_fractal_predicate(policy, st) == T_PASS

    def test_line_dimension_approx_1(self):
        """1D line trajectory → fractal dimension ≈ 1.0."""
        line = [(t, 0.0, 0.0) for t in [i / 200 for i in range(200)]]
        d = compute_box_counting_dimension(line)
        assert 0.7 < d < 1.3

    def test_plane_dimension_approx_2(self):
        """2D plane trajectory → fractal dimension ≈ 2.0."""
        plane = [(i / 40, j / 40, 0.0) for i in range(40) for j in range(40)]
        d = compute_box_counting_dimension(plane)
        assert 1.5 < d < 2.4

    def test_volume_dimension_approx_3(self):
        """3D volume fill → fractal dimension ≈ 3.0."""
        rng = random.Random(0)
        vol = [(rng.random(), rng.random(), rng.random()) for _ in range(3000)]
        d = compute_box_counting_dimension(vol)
        assert 2.2 < d < 3.3

    def test_single_point_returns_zero(self):
        assert compute_box_counting_dimension([(0.0, 0.0, 0.0)]) == 0.0


# ==============================================================================
# F. HATCH GATE (DECRYPT-OR-NOISE)
# ==============================================================================


@pytest.mark.unit
class TestHatchGate:
    """Decrypt-or-noise semantics."""

    def _make_egg(self, nav=(0.0, 0.0, 0.0)):
        cell = sphere_quantize(nav)
        policy = _mk_policy(required_ring=0, required_cell=cell)
        return SacredEgg(
            id="test",
            payload_cipher=b"\xAA" * 64 + b"\xBB" * 16,
            policy=policy,
            mac=b"",
        )

    def test_fail_to_noise_deterministic(self):
        """Same failed state → same noise output."""
        shared = b"shared_secret_32_bytes_min_pad___"
        egg = self._make_egg()
        st = _mk_state(nav=(0.9, 0.0, 0.0), osc=2)  # wrong cell → fail

        out1 = hatch_ref(egg, st, shared, now_fn=_now_fixed(25))
        out2 = hatch_ref(egg, st, shared, now_fn=_now_fixed(25))
        assert out1 == out2

    def test_different_state_different_noise(self):
        """Different failed states → different noise."""
        shared = b"shared_secret_32_bytes_min_pad___"
        egg = self._make_egg()

        st1 = _mk_state(nav=(0.9, 0.0, 0.0), osc=2)
        st2 = _mk_state(nav=(0.0, 0.9, 0.0), osc=2)

        out1 = hatch_ref(egg, st1, shared, now_fn=_now_fixed(25))
        out2 = hatch_ref(egg, st2, shared, now_fn=_now_fixed(25))
        assert out1 != out2

    def test_noise_length_equals_body_length(self):
        """Noise output = ciphertext length minus 16-byte tag."""
        shared = b"shared_secret_32_bytes_min_pad___"
        egg = self._make_egg()
        st = _mk_state(nav=(0.9, 0.0, 0.0), osc=2)  # will fail

        out = hatch_ref(egg, st, shared, now_fn=_now_fixed(25))
        expected_len = len(egg.payload_cipher) - 16  # body = cipher - tag
        assert len(out) == expected_len

    def test_noise_not_all_zeros(self):
        """Noise should not be degenerate."""
        shared = b"shared_secret_32_bytes_min_pad___"
        egg = self._make_egg()
        st = _mk_state(nav=(0.9, 0.0, 0.0), osc=2)

        out = hatch_ref(egg, st, shared, now_fn=_now_fixed(25))
        assert any(b != 0 for b in out)


# ==============================================================================
# G. CRYPTO HELPERS
# ==============================================================================


@pytest.mark.unit
class TestCryptoHelpers:
    """HKDF, PRNG, hash_state, and domain separation."""

    def test_hkdf_produces_correct_length(self):
        key = hkdf_sha256(b"secret", info=b"test", length=64)
        assert len(key) == 64

    def test_hkdf_deterministic(self):
        a = hkdf_sha256(b"secret", info=b"test")
        b = hkdf_sha256(b"secret", info=b"test")
        assert a == b

    def test_hkdf_different_info_different_key(self):
        a = hkdf_sha256(b"secret", info=b"info_a")
        b = hkdf_sha256(b"secret", info=b"info_b")
        assert a != b

    def test_prng_deterministic(self):
        a = prng_stream(b"key", 64)
        b = prng_stream(b"key", 64)
        assert a == b
        assert len(a) == 64

    def test_prng_different_keys(self):
        a = prng_stream(b"key_a", 32)
        b = prng_stream(b"key_b", 32)
        assert a != b

    def test_hash_state_deterministic(self):
        vec = tuple([0.5] * 21)
        a = hash_state(vec, 3)
        b = hash_state(vec, 3)
        assert a == b
        assert len(a) == 32  # SHA-256

    def test_hash_state_differs_with_osc(self):
        vec = tuple([0.5] * 21)
        a = hash_state(vec, 0)
        b = hash_state(vec, 1)
        assert a != b

    def test_domain_separation_tag_format(self):
        policy = _mk_policy()
        dst = build_domain_separation_tag(policy, 3)
        assert dst.startswith(b"SACRED_EGG_V4")
        assert b"|" in dst
        parts = dst.split(b"|")
        assert len(parts) == 6


# ==============================================================================
# H. BFT QUORUM RULE
# ==============================================================================


@pytest.mark.unit
class TestBFTQuorum:
    """Byzantine fault tolerance: n ≥ 3f+1."""

    def test_bft_threshold(self):
        def fmax(n):
            return (n - 1) // 3

        assert fmax(6) == 1
        assert 6 >= 3 * 1 + 1
        quorum = 2 * fmax(6) + 1
        assert quorum == 3

    def test_bft_various_sizes(self):
        for n in range(4, 20):
            f = (n - 1) // 3
            assert n >= 3 * f + 1


# ==============================================================================
# I. BOUNDARY / FUZZ CASES
# ==============================================================================


@pytest.mark.unit
class TestBoundaryFuzz:
    """Edge cases and degenerate inputs."""

    def test_zero_length_cipher_handled(self):
        """Ciphertext shorter than tag size."""
        policy = _mk_policy()
        egg = SacredEgg(id="tiny", payload_cipher=b"\x00" * 10, policy=policy, mac=b"")
        st = _mk_state(nav=(0.9, 0.0, 0.0), osc=0)
        shared = b"secret_32_bytes_pad_____________"

        # Should not raise — will go to noise path
        out = hatch_ref(egg, st, shared, now_fn=_now_fixed(0))
        # body_len = max(10 - 16, 0) = 0 → empty noise
        assert len(out) == 0

    def test_empty_history_fractal(self):
        """Empty trajectory history → T_FAIL if phi required."""
        policy = _mk_policy(require_phi_convergence=True)
        st = _mk_state(history=[])
        assert check_fractal_predicate(policy, st) == T_FAIL

    def test_norm3_handles_zeros(self):
        assert norm3((0.0, 0.0, 0.0)) == 0.0

    def test_norm3_unit_vector(self):
        assert abs(norm3((1.0, 0.0, 0.0)) - 1.0) < 1e-10

    def test_box_counting_empty_returns_zero(self):
        assert compute_box_counting_dimension([]) == 0.0

    def test_box_counting_two_identical_points(self):
        """Two identical points → dimension near 0."""
        d = compute_box_counting_dimension([(0.5, 0.5, 0.5), (0.5, 0.5, 0.5)])
        assert d < 0.5
