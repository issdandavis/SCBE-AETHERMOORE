"""
H-LWE (Hyperbolic Learning With Errors) Test Suite
===================================================

@file test_h_lwe.py
@layer Layer 5, Layer 6, Layer 7, Layer 12
@component H-LWE symmetric + hybrid encryption tests

Tests:
- Poincaré ball math invariants (exp/log inverse, Möbius identity/inverse)
- Symmetric H-LWE roundtrip with noise tolerance
- Containment breach detection on tampered ciphertexts
- Input validation (wrong dimensions, out-of-ball vectors)
- Hybrid KEM roundtrip + tamper detection (skipped if QuasiLWE unavailable)
- Property-based: roundtrip closeness across 200 random vectors
- Deterministic key derivation reproducibility
"""

from __future__ import annotations

import numpy as np
import pytest

from src.crypto.h_lwe import (
    HLWECiphertext,
    HLWESymmetric,
    ContainmentBreach,
    InvalidVector,
    exp_map_zero,
    log_map_zero,
    mobius_add,
    mobius_neg,
    project_to_ball,
    key_vector_from_secret,
    hkdf_sha256,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def rand_ball_vec(
    dim: int, rng: np.random.Generator, max_r: float = 0.85
) -> np.ndarray:
    """Generate a random vector inside the Poincaré ball."""
    v = rng.normal(size=(dim,))
    n = np.linalg.norm(v) or 1.0
    v = v / n
    r = rng.random() * max_r
    return v * r


# ---------------------------------------------------------------------------
# Poincaré ball math invariants
# ---------------------------------------------------------------------------

class TestPoincareMath:
    """Tests for Poincaré ball operations (exp/log maps, Möbius add)."""

    def test_log_exp_inverse_near_origin(self):
        """exp_map(log_map(x)) = x and log_map(exp_map(v)) = v near origin."""
        rng = np.random.default_rng(0)
        for _ in range(200):
            v = rng.normal(scale=0.1, size=(6,))
            x = exp_map_zero(v, c=1.0)
            v2 = log_map_zero(x, c=1.0)
            assert np.linalg.norm(v - v2) < 5e-6, (
                f"log(exp(v)) != v: diff={np.linalg.norm(v - v2):.2e}"
            )

    def test_exp_log_inverse_various_curvatures(self):
        """Roundtrip holds for curvatures c in {0.5, 1.0, 2.0}."""
        rng = np.random.default_rng(10)
        for c in [0.5, 1.0, 2.0]:
            for _ in range(50):
                v = rng.normal(scale=0.05, size=(4,))
                x = exp_map_zero(v, c=c)
                v2 = log_map_zero(x, c=c)
                assert np.linalg.norm(v - v2) < 1e-5

    def test_mobius_add_identity(self):
        """x (+) 0 = x for any x in the ball."""
        rng = np.random.default_rng(1)
        zero = np.zeros(6)
        for _ in range(200):
            x = rand_ball_vec(6, rng, max_r=0.8)
            a = mobius_add(x, zero, c=1.0)
            assert np.linalg.norm(a - x) < 1e-10

    def test_mobius_add_inverse(self):
        """x (+) (-x) ≈ 0 for any x in the ball."""
        rng = np.random.default_rng(2)
        for _ in range(200):
            x = rand_ball_vec(6, rng, max_r=0.8)
            b = mobius_add(x, mobius_neg(x), c=1.0)
            assert np.linalg.norm(b) < 1e-8

    def test_project_to_ball_clamps(self):
        """Vectors outside the ball get projected inside."""
        big = np.array([10.0, 0.0, 0.0])
        p = project_to_ball(big, max_norm=0.9)
        assert np.linalg.norm(p) <= 0.9 + 1e-12

    def test_project_to_ball_preserves_inside(self):
        """Vectors already inside the ball are unchanged."""
        small = np.array([0.1, 0.2, 0.3])
        p = project_to_ball(small, max_norm=0.9)
        assert np.allclose(p, small)

    def test_exp_map_zero_vector(self):
        """exp_map of zero vector returns zero vector."""
        z = np.zeros(5)
        result = exp_map_zero(z, c=1.0)
        assert np.allclose(result, z)

    def test_log_map_zero_vector(self):
        """log_map of zero vector returns zero vector."""
        z = np.zeros(5)
        result = log_map_zero(z, c=1.0)
        assert np.allclose(result, z)

    def test_exp_map_invalid_curvature(self):
        """exp_map rejects non-positive curvature."""
        with pytest.raises(ValueError, match="positive"):
            exp_map_zero(np.ones(3), c=0.0)
        with pytest.raises(ValueError, match="positive"):
            exp_map_zero(np.ones(3), c=-1.0)

    def test_log_map_out_of_ball(self):
        """log_map rejects vectors with norm >= 1."""
        with pytest.raises(InvalidVector, match="norm < 1"):
            log_map_zero(np.array([1.0, 0.0, 0.0]), c=1.0)

    def test_mobius_add_shape_mismatch(self):
        """Möbius add rejects mismatched shapes."""
        with pytest.raises(InvalidVector, match="matching shapes"):
            mobius_add(np.zeros(3), np.zeros(4))


# ---------------------------------------------------------------------------
# KDF helpers
# ---------------------------------------------------------------------------

class TestKDF:
    """Tests for HKDF and key vector derivation."""

    def test_hkdf_deterministic(self):
        """Same inputs produce same output."""
        a = hkdf_sha256(b"secret", salt=b"s", info=b"i", length=32)
        b = hkdf_sha256(b"secret", salt=b"s", info=b"i", length=32)
        assert a == b

    def test_hkdf_different_info_different_output(self):
        """Different info strings produce different keys."""
        a = hkdf_sha256(b"secret", info=b"a", length=32)
        b = hkdf_sha256(b"secret", info=b"b", length=32)
        assert a != b

    def test_hkdf_invalid_length(self):
        """HKDF rejects length <= 0."""
        with pytest.raises(ValueError):
            hkdf_sha256(b"x", length=0)

    def test_key_vector_deterministic(self):
        """Same secret -> same key vector."""
        k1 = key_vector_from_secret(b"test", dim=6, c=1.0)
        k2 = key_vector_from_secret(b"test", dim=6, c=1.0)
        assert np.allclose(k1, k2)

    def test_key_vector_inside_ball(self):
        """Key vectors are always well inside the ball."""
        for _ in range(20):
            import secrets
            s = secrets.token_bytes(32)
            k = key_vector_from_secret(s, dim=6, c=1.0, max_radius=0.95)
            assert np.linalg.norm(k) < 0.95 * 0.5 + 1e-6

    def test_key_vector_different_secrets(self):
        """Different secrets produce different key vectors."""
        k1 = key_vector_from_secret(b"alpha", dim=6, c=1.0)
        k2 = key_vector_from_secret(b"beta", dim=6, c=1.0)
        assert not np.allclose(k1, k2)


# ---------------------------------------------------------------------------
# Symmetric H-LWE
# ---------------------------------------------------------------------------

class TestHLWESymmetric:
    """Tests for symmetric H-LWE encrypt/decrypt."""

    def test_roundtrip_close(self):
        """Encrypt then decrypt recovers a vector close to the original."""
        rng = np.random.default_rng(2)
        hlwe = HLWESymmetric(
            dim=6, noise_scale=0.01, max_radius=0.95, rng=rng
        )
        key = rand_ball_vec(6, rng, max_r=0.2)
        key = project_to_ball(key, max_norm=0.3)
        for _ in range(50):
            x = rand_ball_vec(6, rng, max_r=0.8)
            ct = hlwe.encrypt(key, x)
            x2, r2 = hlwe.decrypt(key, ct)
            assert r2 < 0.95
            # Not exact because of noise; should be close
            assert np.linalg.norm(x - x2) < 0.15, (
                f"Roundtrip error too large: {np.linalg.norm(x - x2):.4f}"
            )

    def test_zero_noise_exact_roundtrip(self):
        """With noise_scale=0, decrypt recovers the exact plaintext."""
        rng = np.random.default_rng(42)
        hlwe = HLWESymmetric(
            dim=6, noise_scale=0.0, max_radius=0.95, rng=rng
        )
        key = rand_ball_vec(6, rng, max_r=0.2)
        for _ in range(30):
            x = rand_ball_vec(6, rng, max_r=0.7)
            ct = hlwe.encrypt(key, x)
            x2, r2 = hlwe.decrypt(key, ct)
            assert np.linalg.norm(x - x2) < 1e-10, (
                f"Zero-noise roundtrip not exact: {np.linalg.norm(x - x2):.2e}"
            )

    def test_containment_breach_on_tamper(self):
        """Pushing ciphertext toward boundary triggers ContainmentBreach."""
        rng = np.random.default_rng(3)
        hlwe = HLWESymmetric(
            dim=6, noise_scale=0.0, max_radius=0.95, rng=rng
        )
        key = rand_ball_vec(6, rng, max_r=0.2)
        x = rand_ball_vec(6, rng, max_r=0.6)
        ct = hlwe.encrypt(key, x)

        # Tamper: push ciphertext toward boundary
        tampered = ct.ct.copy()
        n = np.linalg.norm(tampered)
        if n > 0:
            tampered = tampered / n * 0.999999
        else:
            tampered = np.ones(6) / np.sqrt(6) * 0.999999
        ct2 = HLWECiphertext(
            ct=tampered,
            radius_ct=float(np.linalg.norm(tampered)),
            meta=ct.meta,
        )
        with pytest.raises(ContainmentBreach):
            hlwe.decrypt(key, ct2)

    def test_wrong_key_gives_different_result(self):
        """Decrypting with wrong key gives a different (wrong) vector."""
        rng = np.random.default_rng(7)
        hlwe = HLWESymmetric(
            dim=6, noise_scale=0.0, max_radius=0.95, rng=rng
        )
        key1 = rand_ball_vec(6, rng, max_r=0.15)
        key2 = rand_ball_vec(6, rng, max_r=0.15)
        x = rand_ball_vec(6, rng, max_r=0.5)
        ct = hlwe.encrypt(key1, x)
        # Decrypt with wrong key — may or may not breach, but result differs
        try:
            x2, _ = hlwe.decrypt(key2, ct)
            assert np.linalg.norm(x - x2) > 0.01, (
                "Wrong key should not recover the correct plaintext"
            )
        except ContainmentBreach:
            pass  # Also valid — wrong key may push outside boundary

    def test_metadata_preserved(self):
        """Metadata dict is preserved through encrypt."""
        rng = np.random.default_rng(8)
        hlwe = HLWESymmetric(dim=4, noise_scale=0.0, max_radius=0.95, rng=rng)
        key = rand_ball_vec(4, rng, max_r=0.2)
        x = rand_ball_vec(4, rng, max_r=0.5)
        meta = {"layer": 5, "tongue": "KO"}
        ct = hlwe.encrypt(key, x, meta=meta)
        assert ct.meta == meta

    def test_radius_ct_accurate(self):
        """Ciphertext radius_ct matches actual norm of ct vector."""
        rng = np.random.default_rng(9)
        hlwe = HLWESymmetric(dim=6, noise_scale=0.01, max_radius=0.95, rng=rng)
        key = rand_ball_vec(6, rng, max_r=0.2)
        x = rand_ball_vec(6, rng, max_r=0.7)
        ct = hlwe.encrypt(key, x)
        assert abs(ct.radius_ct - np.linalg.norm(ct.ct)) < 1e-12


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestInputValidation:
    """Tests that invalid inputs are properly rejected."""

    def test_wrong_dimension_rejected(self):
        """Plaintext with wrong number of dimensions is rejected."""
        hlwe = HLWESymmetric(dim=6, noise_scale=0.01, max_radius=0.95)
        key = np.zeros(6)
        with pytest.raises(InvalidVector):
            hlwe.encrypt(key, np.ones(5))  # dim mismatch

    def test_unit_norm_rejected(self):
        """Vector with norm >= 1 (on boundary) is rejected."""
        hlwe = HLWESymmetric(dim=6, noise_scale=0.01, max_radius=0.95)
        key = np.zeros(6)
        with pytest.raises(InvalidVector):
            hlwe.encrypt(key, np.ones(6))  # norm = sqrt(6) >> 1

    def test_over_max_radius_rejected(self):
        """Vector with norm >= max_radius is rejected."""
        hlwe = HLWESymmetric(dim=3, noise_scale=0.0, max_radius=0.8)
        key = np.zeros(3)
        # norm = 0.85 > 0.8
        with pytest.raises(InvalidVector, match="too close to boundary"):
            hlwe.encrypt(key, np.array([0.85, 0.0, 0.0]))

    def test_nan_rejected(self):
        """NaN vectors are rejected."""
        hlwe = HLWESymmetric(dim=3, noise_scale=0.0, max_radius=0.95)
        key = np.zeros(3)
        with pytest.raises(InvalidVector, match="not finite"):
            hlwe.encrypt(key, np.array([float("nan"), 0.0, 0.0]))

    def test_invalid_dim_constructor(self):
        """dim <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="positive"):
            HLWESymmetric(dim=0)

    def test_invalid_max_radius_constructor(self):
        """max_radius outside (0, 1) raises ValueError."""
        with pytest.raises(ValueError, match="max_radius"):
            HLWESymmetric(dim=3, max_radius=1.0)
        with pytest.raises(ValueError, match="max_radius"):
            HLWESymmetric(dim=3, max_radius=0.0)

    def test_negative_noise_scale_constructor(self):
        """Negative noise_scale raises ValueError."""
        with pytest.raises(ValueError, match="noise_scale"):
            HLWESymmetric(dim=3, noise_scale=-0.1)


# ---------------------------------------------------------------------------
# Hybrid KEM (skipped if QuasiLWE unavailable)
# ---------------------------------------------------------------------------

class TestHybridKEM:
    """Tests for the HLWEHybridKEM wrapper (requires QuasiLWE)."""

    def test_hybrid_kem_roundtrip_if_available(self):
        """Hybrid KEM encrypt/decrypt roundtrip."""
        pytest.importorskip("src.crypto.quasi_lwe")
        from src.crypto.quasi_lwe import QuasiLWEKEM  # type: ignore
        from src.crypto.h_lwe import HLWEHybridKEM

        rng = np.random.default_rng(4)
        kem = QuasiLWEKEM()
        pk, sk = kem.keygen()

        hybrid = HLWEHybridKEM(dim=6, noise_scale=0.01, max_radius=0.95)
        x = rand_ball_vec(6, rng, max_r=0.75)
        ct = hybrid.encrypt(pk, x)
        x2, r2 = hybrid.decrypt(sk, ct)
        assert r2 < 0.95
        assert np.linalg.norm(x - x2) < 0.20

    def test_hybrid_kem_detects_tamper_if_available(self):
        """Flipped HMAC tag byte triggers AuthenticationError."""
        pytest.importorskip("src.crypto.quasi_lwe")
        from src.crypto.quasi_lwe import QuasiLWEKEM  # type: ignore
        from src.crypto.h_lwe import HLWEHybridKEM, AuthenticationError

        rng = np.random.default_rng(5)
        kem = QuasiLWEKEM()
        pk, sk = kem.keygen()

        hybrid = HLWEHybridKEM(dim=6, noise_scale=0.01, max_radius=0.95)
        x = rand_ball_vec(6, rng, max_r=0.75)
        ct = hybrid.encrypt(pk, x)

        # Flip one byte in tag
        bad_tag = bytearray(ct.tag)
        bad_tag[0] ^= 0x01
        from src.crypto.h_lwe import HLWEHybridCiphertext

        ct_bad = HLWEHybridCiphertext(
            kem_ct=ct.kem_ct,
            vec_ct=ct.vec_ct,
            tag=bytes(bad_tag),
            meta=ct.meta,
        )
        with pytest.raises(AuthenticationError):
            hybrid.decrypt(sk, ct_bad)


# ---------------------------------------------------------------------------
# Property: roundtrip closeness over many random vectors
# ---------------------------------------------------------------------------

class TestPropertyBased:
    """Property-based tests across many random vectors."""

    def test_roundtrip_closeness_200_vectors(self):
        """200 random vectors all roundtrip within tolerance."""
        rng = np.random.default_rng(100)
        hlwe = HLWESymmetric(
            dim=6, noise_scale=0.005, max_radius=0.95, rng=rng
        )
        key = rand_ball_vec(6, rng, max_r=0.15)
        max_err = 0.0
        for _ in range(200):
            x = rand_ball_vec(6, rng, max_r=0.75)
            ct = hlwe.encrypt(key, x)
            x2, _ = hlwe.decrypt(key, ct)
            err = np.linalg.norm(x - x2)
            max_err = max(max_err, err)
            assert err < 0.10, f"Roundtrip error {err:.4f} exceeds 0.10"
        # Worst-case should still be small
        assert max_err < 0.10

    def test_ciphertext_always_inside_ball(self):
        """Ciphertext vector is always inside the unit ball."""
        rng = np.random.default_rng(101)
        hlwe = HLWESymmetric(
            dim=6, noise_scale=0.02, max_radius=0.95, rng=rng
        )
        key = rand_ball_vec(6, rng, max_r=0.15)
        for _ in range(200):
            x = rand_ball_vec(6, rng, max_r=0.85)
            ct = hlwe.encrypt(key, x)
            assert ct.radius_ct < 1.0, (
                f"Ciphertext escaped ball: r={ct.radius_ct}"
            )

    def test_decrypted_always_inside_max_radius(self):
        """Decrypted vectors always stay within max_radius."""
        rng = np.random.default_rng(102)
        hlwe = HLWESymmetric(
            dim=6, noise_scale=0.005, max_radius=0.95, rng=rng
        )
        key = rand_ball_vec(6, rng, max_r=0.1)
        for _ in range(200):
            x = rand_ball_vec(6, rng, max_r=0.7)
            ct = hlwe.encrypt(key, x)
            _, r = hlwe.decrypt(key, ct)
            assert r < 0.95
