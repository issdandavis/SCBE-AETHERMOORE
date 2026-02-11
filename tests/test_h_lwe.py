"""
Tests for H-LWE: Hyperbolic Learning With Errors
=================================================

Covers:
- Poincaré ball operations (exp/log map roundtrip, Möbius addition)
- Symmetric H-LWE encrypt/decrypt roundtrip
- Containment breach detection on tampered ciphertext
- Input validation (wrong dimensions, outside ball)
- Key derivation from secret bytes
- Hybrid Kyber768 + H-LWE (skip if PQC not available)
- HMAC authentication (hybrid mode)

@module tests/test_h_lwe
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pytest

from crypto.h_lwe import (
    HLWESymmetric,
    HLWECiphertext,
    ContainmentBreach,
    InvalidVector,
    exp_map_zero,
    log_map_zero,
    mobius_add,
    mobius_neg,
    project_to_ball,
    key_vector_from_secret,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def rand_ball_vec(
    dim: int, rng: np.random.Generator, max_r: float = 0.85
) -> np.ndarray:
    """Generate a random vector strictly inside the Poincaré ball."""
    v = rng.normal(size=(dim,))
    n = np.linalg.norm(v) or 1.0
    v = v / n
    r = rng.random() * max_r
    return v * r


# ---------------------------------------------------------------------------
# Poincaré Ball Operations
# ---------------------------------------------------------------------------

class TestExpLogMaps:
    """Exponential and logarithmic maps should be inverse near origin."""

    def test_log_exp_roundtrip_near_origin(self):
        rng = np.random.default_rng(0)
        for _ in range(200):
            v = rng.normal(scale=0.1, size=(6,))
            x = exp_map_zero(v, c=1.0)
            v2 = log_map_zero(x, c=1.0)
            assert np.linalg.norm(v - v2) < 5e-6

    def test_exp_map_stays_in_ball(self):
        rng = np.random.default_rng(1)
        for _ in range(100):
            v = rng.normal(scale=1.0, size=(6,))
            x = exp_map_zero(v, c=1.0)
            assert np.linalg.norm(x) < 1.0

    def test_exp_map_zero_vector(self):
        z = np.zeros(6)
        out = exp_map_zero(z, c=1.0)
        assert np.allclose(out, z)

    def test_log_map_zero_vector(self):
        z = np.zeros(6)
        out = log_map_zero(z, c=1.0)
        assert np.allclose(out, z)

    def test_log_map_rejects_outside_ball(self):
        x = np.array([1.0, 0, 0, 0, 0, 0])  # on boundary
        with pytest.raises(InvalidVector):
            log_map_zero(x, c=1.0)


class TestMobiusAddition:
    """Möbius addition properties on the Poincaré ball."""

    def test_identity(self):
        """x ⊕ 0 = x."""
        rng = np.random.default_rng(2)
        zero = np.zeros(6)
        for _ in range(200):
            x = rand_ball_vec(6, rng, max_r=0.8)
            a = mobius_add(x, zero, c=1.0)
            assert np.linalg.norm(a - x) < 1e-10

    def test_inverse(self):
        """x ⊕ (-x) ≈ 0."""
        rng = np.random.default_rng(3)
        for _ in range(200):
            x = rand_ball_vec(6, rng, max_r=0.8)
            b = mobius_add(x, mobius_neg(x), c=1.0)
            assert np.linalg.norm(b) < 1e-8

    def test_stays_in_ball(self):
        rng = np.random.default_rng(4)
        for _ in range(200):
            x = rand_ball_vec(6, rng, max_r=0.9)
            y = rand_ball_vec(6, rng, max_r=0.9)
            result = mobius_add(x, y, c=1.0)
            assert np.linalg.norm(result) < 1.0

    def test_shape_mismatch_raises(self):
        with pytest.raises(InvalidVector):
            mobius_add(np.zeros(3), np.zeros(6), c=1.0)


# ---------------------------------------------------------------------------
# Symmetric H-LWE
# ---------------------------------------------------------------------------

class TestHLWESymmetric:
    """Symmetric H-LWE encrypt/decrypt."""

    def test_roundtrip(self):
        """Encrypt then decrypt should recover approximately the original."""
        rng = np.random.default_rng(10)
        hlwe = HLWESymmetric(dim=6, noise_scale=0.01, max_radius=0.95, rng=rng)
        key = rand_ball_vec(6, rng, max_r=0.2)
        key = project_to_ball(key, max_norm=0.3)
        for _ in range(50):
            x = rand_ball_vec(6, rng, max_r=0.8)
            ct = hlwe.encrypt(key, x)
            x2, r2 = hlwe.decrypt(key, ct)
            assert r2 < 0.95
            # Not exact because of noise; should be close
            assert np.linalg.norm(x - x2) < 0.15

    def test_zero_noise_exact_roundtrip(self):
        """With zero noise, should recover exactly."""
        rng = np.random.default_rng(11)
        hlwe = HLWESymmetric(dim=6, noise_scale=0.0, max_radius=0.95, rng=rng)
        key = rand_ball_vec(6, rng, max_r=0.2)
        key = project_to_ball(key, max_norm=0.3)
        x = rand_ball_vec(6, rng, max_r=0.7)
        ct = hlwe.encrypt(key, x)
        x2, r2 = hlwe.decrypt(key, ct)
        assert np.linalg.norm(x - x2) < 1e-3

    def test_wrong_key_gives_different_result(self):
        rng = np.random.default_rng(12)
        hlwe = HLWESymmetric(dim=6, noise_scale=0.0, max_radius=0.95, rng=rng)
        key1 = rand_ball_vec(6, rng, max_r=0.2)
        key2 = rand_ball_vec(6, rng, max_r=0.2)
        x = rand_ball_vec(6, rng, max_r=0.5)
        ct = hlwe.encrypt(key1, x)
        x2, _ = hlwe.decrypt(key2, ct)
        assert np.linalg.norm(x - x2) > 0.01

    def test_ciphertext_is_in_ball(self):
        rng = np.random.default_rng(13)
        hlwe = HLWESymmetric(dim=6, noise_scale=0.02, max_radius=0.95, rng=rng)
        key = rand_ball_vec(6, rng, max_r=0.2)
        for _ in range(50):
            x = rand_ball_vec(6, rng, max_r=0.8)
            ct = hlwe.encrypt(key, x)
            assert ct.radius_ct < 1.0

    def test_meta_preserved(self):
        rng = np.random.default_rng(14)
        hlwe = HLWESymmetric(dim=6, noise_scale=0.01, max_radius=0.95, rng=rng)
        key = rand_ball_vec(6, rng, max_r=0.2)
        x = rand_ball_vec(6, rng, max_r=0.5)
        ct = hlwe.encrypt(key, x, meta={"agent": "test-01"})
        assert ct.meta["agent"] == "test-01"


# ---------------------------------------------------------------------------
# Containment Breach Detection
# ---------------------------------------------------------------------------

class TestContainmentBreach:
    """Detect when decrypted vectors escape the safety zone."""

    def test_tampered_ciphertext_triggers_breach(self):
        rng = np.random.default_rng(20)
        hlwe = HLWESymmetric(dim=6, noise_scale=0.0, max_radius=0.95, rng=rng)
        key = rand_ball_vec(6, rng, max_r=0.2)
        x = rand_ball_vec(6, rng, max_r=0.6)
        ct = hlwe.encrypt(key, x)

        # Tamper: push ciphertext toward boundary
        tampered = ct.ct.copy()
        n = np.linalg.norm(tampered) or 1.0
        tampered = tampered / n * 0.999999
        ct2 = HLWECiphertext(
            ct=tampered, radius_ct=float(np.linalg.norm(tampered)), meta=ct.meta
        )

        with pytest.raises(ContainmentBreach):
            hlwe.decrypt(key, ct2)


# ---------------------------------------------------------------------------
# Input Validation
# ---------------------------------------------------------------------------

class TestInputValidation:
    """Reject invalid inputs cleanly."""

    def test_wrong_dimension_plaintext(self):
        hlwe = HLWESymmetric(dim=6, noise_scale=0.01, max_radius=0.95)
        key = np.zeros(6)
        with pytest.raises(InvalidVector):
            hlwe.encrypt(key, np.zeros(5))

    def test_unit_norm_plaintext_rejected(self):
        hlwe = HLWESymmetric(dim=6, noise_scale=0.01, max_radius=0.95)
        key = np.zeros(6)
        with pytest.raises(InvalidVector):
            hlwe.encrypt(key, np.ones(6))  # norm > 1

    def test_boundary_plaintext_rejected(self):
        hlwe = HLWESymmetric(dim=6, noise_scale=0.01, max_radius=0.95)
        key = np.zeros(6)
        x = np.zeros(6)
        x[0] = 0.96  # just past max_radius
        with pytest.raises(InvalidVector):
            hlwe.encrypt(key, x)


# ---------------------------------------------------------------------------
# Key Derivation
# ---------------------------------------------------------------------------

class TestKeyDerivation:
    """Derive hyperbolic key vectors from secret bytes."""

    def test_deterministic(self):
        secret = b"test-secret-key-material"
        k1 = key_vector_from_secret(secret, dim=6, c=1.0)
        k2 = key_vector_from_secret(secret, dim=6, c=1.0)
        assert np.allclose(k1, k2)

    def test_different_secrets_give_different_keys(self):
        k1 = key_vector_from_secret(b"secret-a", dim=6, c=1.0)
        k2 = key_vector_from_secret(b"secret-b", dim=6, c=1.0)
        assert np.linalg.norm(k1 - k2) > 0.001

    def test_key_stays_near_origin(self):
        k = key_vector_from_secret(b"any-secret", dim=6, c=1.0)
        assert np.linalg.norm(k) < 0.5

    def test_key_is_in_ball(self):
        k = key_vector_from_secret(b"key-material", dim=6, c=1.0, max_radius=0.95)
        assert np.linalg.norm(k) < 1.0

    def test_correct_dimension(self):
        for dim in [3, 6, 21]:
            k = key_vector_from_secret(b"secret", dim=dim, c=1.0)
            assert k.shape == (dim,)


# ---------------------------------------------------------------------------
# Hybrid Kyber768 + H-LWE
# ---------------------------------------------------------------------------

class TestHybridKEM:
    """Kyber768 KEM + H-LWE hybrid encryption."""

    @pytest.fixture(autouse=True)
    def _skip_if_no_pqc(self):
        try:
            from symphonic_cipher.scbe_aethermoore.pqc.pqc_core import Kyber768
            self._kyber = Kyber768
        except ImportError:
            pytest.skip("PQC module not available")

    def test_hybrid_roundtrip(self):
        from crypto.h_lwe import HLWEHybridKEM

        rng = np.random.default_rng(30)
        keypair = self._kyber.generate_keypair()

        hybrid = HLWEHybridKEM(dim=6, noise_scale=0.01, max_radius=0.95)
        x = rand_ball_vec(6, rng, max_r=0.75)
        ct = hybrid.encrypt(keypair.public_key, x)
        x2, r2 = hybrid.decrypt(keypair.secret_key, ct)
        assert r2 < 0.95
        assert np.linalg.norm(x - x2) < 0.20

    def test_hybrid_detects_tag_tamper(self):
        from crypto.h_lwe import HLWEHybridKEM, AuthenticationError, HLWEHybridCiphertext

        rng = np.random.default_rng(31)
        keypair = self._kyber.generate_keypair()

        hybrid = HLWEHybridKEM(dim=6, noise_scale=0.01, max_radius=0.95)
        x = rand_ball_vec(6, rng, max_r=0.75)
        ct = hybrid.encrypt(keypair.public_key, x)

        # Flip one byte in tag
        bad_tag = bytearray(ct.tag)
        bad_tag[0] ^= 0x01
        ct_bad = HLWEHybridCiphertext(
            kem_ct=ct.kem_ct, vec_ct=ct.vec_ct, tag=bytes(bad_tag), meta=ct.meta
        )

        with pytest.raises(AuthenticationError):
            hybrid.decrypt(keypair.secret_key, ct_bad)

    def test_hybrid_wrong_secret_key_fails(self):
        from crypto.h_lwe import HLWEHybridKEM

        rng = np.random.default_rng(32)
        kp1 = self._kyber.generate_keypair()
        kp2 = self._kyber.generate_keypair()

        hybrid = HLWEHybridKEM(dim=6, noise_scale=0.01, max_radius=0.95)
        x = rand_ball_vec(6, rng, max_r=0.6)
        ct = hybrid.encrypt(kp1.public_key, x)

        # Different secret key → HMAC mismatch
        with pytest.raises(Exception):
            hybrid.decrypt(kp2.secret_key, ct)
