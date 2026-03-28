"""
H-LWE tests: geometry, symmetric encryption, and optional hybrid path.
"""

from __future__ import annotations

import secrets

import numpy as np
import pytest

from src.crypto.h_lwe import (
    AuthenticationError,
    ContainmentBreach,
    HLWEHybridCiphertext,
    HLWEHybridKEM,
    HLWECiphertext,
    HLWESymmetric,
    InvalidVector,
    exp_map_zero,
    hkdf_sha256,
    key_vector_from_secret,
    log_map_zero,
    mobius_add,
    mobius_neg,
    project_to_ball,
)


def rand_ball_vec(dim: int, rng: np.random.Generator, max_r: float = 0.85) -> np.ndarray:
    v = rng.normal(size=(dim,))
    n = np.linalg.norm(v) or 1.0
    v = v / n
    r = rng.random() * max_r
    return v * r


class TestPoincareOps:
    def test_log_exp_roundtrip(self):
        rng = np.random.default_rng(0)
        for _ in range(100):
            v = rng.normal(scale=0.08, size=(6,))
            x = exp_map_zero(v, c=1.0)
            v2 = log_map_zero(x, c=1.0)
            assert np.linalg.norm(v - v2) < 1e-5

    def test_mobius_identity_and_inverse(self):
        rng = np.random.default_rng(1)
        z = np.zeros(6)
        for _ in range(100):
            x = rand_ball_vec(6, rng, max_r=0.8)
            assert np.linalg.norm(mobius_add(x, z, c=1.0) - x) < 1e-10
            assert np.linalg.norm(mobius_add(x, mobius_neg(x), c=1.0)) < 1e-8

    def test_projection_inside_ball(self):
        big = np.array([10.0, 0.0, 0.0], dtype=float)
        p = project_to_ball(big, max_norm=0.9)
        assert np.linalg.norm(p) <= 0.9 + 1e-12


class TestKDF:
    def test_hkdf_deterministic(self):
        a = hkdf_sha256(b"secret", salt=b"s", info=b"i", length=32)
        b = hkdf_sha256(b"secret", salt=b"s", info=b"i", length=32)
        assert a == b

    def test_key_vector_deterministic_and_bounded(self):
        s = secrets.token_bytes(32)
        k1 = key_vector_from_secret(s, dim=6, c=1.0, max_radius=0.95)
        k2 = key_vector_from_secret(s, dim=6, c=1.0, max_radius=0.95)
        assert np.allclose(k1, k2)
        assert np.linalg.norm(k1) < 0.95


class TestHLWESymmetric:
    def test_roundtrip_close(self):
        rng = np.random.default_rng(10)
        hlwe = HLWESymmetric(dim=6, noise_scale=0.01, max_radius=0.95, rng=rng)
        key = rand_ball_vec(6, rng, max_r=0.2)
        key = project_to_ball(key, max_norm=0.3)
        for _ in range(30):
            x = rand_ball_vec(6, rng, max_r=0.75)
            ct = hlwe.encrypt(key, x)
            x2, r2 = hlwe.decrypt(key, ct)
            assert r2 < 0.95
            assert np.linalg.norm(x - x2) < 0.20

    def test_tampered_ciphertext_triggers_containment_breach(self):
        rng = np.random.default_rng(11)
        hlwe = HLWESymmetric(dim=6, noise_scale=0.0, max_radius=0.95, rng=rng)
        key = rand_ball_vec(6, rng, max_r=0.15)
        x = rand_ball_vec(6, rng, max_r=0.6)
        ct = hlwe.encrypt(key, x)

        tampered = ct.ct.copy()
        n = np.linalg.norm(tampered) or 1.0
        tampered = tampered / n * 0.999999
        ct2 = HLWECiphertext(ct=tampered, radius_ct=float(np.linalg.norm(tampered)), meta=ct.meta)

        with pytest.raises(ContainmentBreach):
            hlwe.decrypt(key, ct2)

    def test_input_validation(self):
        hlwe = HLWESymmetric(dim=6, noise_scale=0.01, max_radius=0.95)
        key = np.zeros(6)
        with pytest.raises(InvalidVector):
            hlwe.encrypt(key, np.ones(5))
        with pytest.raises(InvalidVector):
            hlwe.encrypt(key, np.ones(6))


class TestHLWEHybrid:
    def test_hybrid_roundtrip_when_quasi_lwe_available(self):
        pytest.importorskip("src.crypto.quasi_lwe")
        from src.crypto.quasi_lwe import QuasiLWEKEM

        rng = np.random.default_rng(20)
        kem = QuasiLWEKEM()
        pk, sk = kem.keygen()
        hybrid = HLWEHybridKEM(dim=6, noise_scale=0.01, max_radius=0.95)

        x = rand_ball_vec(6, rng, max_r=0.7)
        ct = hybrid.encrypt(pk, x)
        x2, r2 = hybrid.decrypt(sk, ct)
        assert r2 < 0.95
        assert np.linalg.norm(x - x2) < 0.25

    def test_hybrid_tag_tamper_rejected_when_quasi_lwe_available(self):
        pytest.importorskip("src.crypto.quasi_lwe")
        from src.crypto.quasi_lwe import QuasiLWEKEM

        rng = np.random.default_rng(21)
        kem = QuasiLWEKEM()
        pk, sk = kem.keygen()
        hybrid = HLWEHybridKEM(dim=6, noise_scale=0.01, max_radius=0.95)

        x = rand_ball_vec(6, rng, max_r=0.7)
        ct = hybrid.encrypt(pk, x)
        bad_tag = bytearray(ct.tag)
        bad_tag[0] ^= 0x01
        ct_bad = HLWEHybridCiphertext(
            kem_ct=ct.kem_ct,
            vec_ct=ct.vec_ct,
            tag=bytes(bad_tag),
            meta=ct.meta,
        )
        with pytest.raises(AuthenticationError):
            hybrid.decrypt(sk, ct_bad)
