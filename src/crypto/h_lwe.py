"""
H-LWE: Hyperbolic Learning With Errors - Poincaré Ball Vector Encryption
=========================================================================

@file h_lwe.py
@module crypto/h_lwe
@layer Layer 5, Layer 6, Layer 12, Layer 13
@component Hyperbolic Vector Encryption
@version 1.0.0
@since 2026-02-08

Symmetric "hyperbolic vector encryption" on the Poincaré ball using
Möbius addition + tangent-space noise (breathing-safe behavior).

Features:
  - Geometry-preserving: encryption/decryption stay inside the ball
  - Containment breach detection: decrypt raises if recovered vector
    drifts toward or past the safety radius
  - Optional hybrid wrapper: uses Kyber768 KEM to exchange session key,
    then encrypts with symmetric H-LWE
  - HMAC authentication for hybrid mode

Security note:
  This is a *governance/containment* primitive, not a proven IND-CCA
  scheme. It ensures vectors stay within the Poincaré ball and detects
  boundary violations. Use with AEAD/HMAC/signatures for transport.
"""

from __future__ import annotations

import hmac as hmac_mod
import hashlib
import math
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class HLWEError(Exception):
    """Base class for H-LWE errors."""


class ContainmentBreach(HLWEError):
    """Raised when decrypted vector exits the allowed Poincaré radius."""


class InvalidVector(HLWEError):
    """Raised when inputs are not valid hyperbolic vectors."""


class AuthenticationError(HLWEError):
    """Raised when ciphertext authenticity check fails."""


# ---------------------------------------------------------------------------
# Hyperbolic (Poincaré ball) operations
# ---------------------------------------------------------------------------

def _norm(x: np.ndarray) -> float:
    return float(np.linalg.norm(x))


def project_to_ball(x: np.ndarray, *, max_norm: float = 1.0 - 1e-8) -> np.ndarray:
    """Radially project to inside the open ball (norm < 1)."""
    x = np.asarray(x, dtype=float)
    n = _norm(x)
    if not np.isfinite(n):
        raise InvalidVector("Vector norm is not finite.")
    if n >= max_norm:
        if n == 0.0:
            return x
        x = x * (max_norm / n)
    return x


def exp_map_zero(v: np.ndarray, *, c: float = 1.0) -> np.ndarray:
    """
    Exponential map at origin for Poincaré ball of curvature c > 0.
    Maps tangent vector v (Euclidean) -> point in ball.
    """
    v = np.asarray(v, dtype=float)
    if c <= 0:
        raise ValueError("Curvature c must be positive.")
    v_norm = _norm(v)
    if v_norm == 0.0:
        return v.copy()
    sqrt_c = math.sqrt(c)
    scale = math.tanh(sqrt_c * v_norm) / (sqrt_c * v_norm)
    return v * scale


def log_map_zero(x: np.ndarray, *, c: float = 1.0) -> np.ndarray:
    """
    Log map at origin for Poincaré ball of curvature c > 0.
    Maps point x in ball -> tangent vector at origin.
    """
    x = np.asarray(x, dtype=float)
    if c <= 0:
        raise ValueError("Curvature c must be positive.")
    x_norm = _norm(x)
    if x_norm == 0.0:
        return x.copy()
    if x_norm >= 1.0:
        raise InvalidVector("log_map input must have norm < 1.")
    sqrt_c = math.sqrt(c)
    t = sqrt_c * x_norm
    scale = math.atanh(t) / (sqrt_c * x_norm)
    return x * scale


def mobius_add(x: np.ndarray, y: np.ndarray, *, c: float = 1.0) -> np.ndarray:
    """Möbius addition on Poincaré ball (curvature c)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.shape != y.shape:
        raise InvalidVector("Möbius add requires matching shapes.")
    if c <= 0:
        raise ValueError("Curvature c must be positive.")

    x2 = min(float(np.dot(x, x)), 1.0 - 1e-12)
    y2 = min(float(np.dot(y, y)), 1.0 - 1e-12)
    xy = float(np.dot(x, y))

    num = (1 + 2 * c * xy + c * y2) * x + (1 - c * x2) * y
    den = 1 + 2 * c * xy + (c * c) * x2 * y2

    if abs(den) < 1e-15:
        xx = project_to_ball(x, max_norm=1.0 - 1e-6)
        yy = project_to_ball(y, max_norm=1.0 - 1e-6)
        return mobius_add(xx, yy, c=c)

    out = num / den
    return project_to_ball(out, max_norm=1.0 - 1e-10)


def mobius_neg(x: np.ndarray) -> np.ndarray:
    """Negate a Poincaré ball vector (Möbius inverse)."""
    return -np.asarray(x, dtype=float)


# ---------------------------------------------------------------------------
# Key derivation helpers
# ---------------------------------------------------------------------------

def hkdf_sha256(
    ikm: bytes, *, salt: bytes = b"", info: bytes = b"", length: int = 32
) -> bytes:
    """Minimal HKDF (RFC 5869) with SHA-256."""
    if length <= 0:
        raise ValueError("HKDF length must be > 0.")
    prk = hmac_mod.new(salt, ikm, hashlib.sha256).digest()
    t = b""
    okm = b""
    counter = 1
    while len(okm) < length:
        t = hmac_mod.new(prk, t + info + bytes([counter]), hashlib.sha256).digest()
        okm += t
        counter += 1
        if counter > 255:
            raise ValueError("HKDF output too long.")
    return okm[:length]


def key_vector_from_secret(
    secret: bytes,
    *,
    dim: int,
    c: float,
    tangent_scale: float = 0.08,
    max_radius: float = 0.95,
) -> np.ndarray:
    """
    Derive a small hyperbolic key vector from secret bytes.
    Keeps key near origin to avoid pushing ciphertext toward boundary.
    """
    raw = hkdf_sha256(secret, salt=b"scbe-hlwe", info=b"keyvec", length=4 * dim)
    ints = np.frombuffer(raw, dtype=np.uint32).astype(np.float64)
    u = (ints / (2**32 - 1.0)) * 2.0 - 1.0
    tangent = u * tangent_scale
    k = exp_map_zero(tangent, c=c)
    if _norm(k) >= max_radius * 0.5:
        k = project_to_ball(k, max_norm=max_radius * 0.5)
    return k


# ---------------------------------------------------------------------------
# Symmetric H-LWE
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HLWECiphertext:
    """
    Ciphertext for symmetric H-LWE vector encryption.

    ct = x ⊕ k ⊕ n
    where ⊕ is Möbius addition and n is noise from tangent space via exp_map_zero.
    """
    ct: np.ndarray
    radius_ct: float
    meta: Dict[str, Any]


class HLWESymmetric:
    """
    Geometry-preserving encryption for Poincaré-ball vectors.

    Encrypt: ct = (x ⊕ k) ⊕ noise
    Decrypt: x_hat = ct ⊕ (-k)

    The noise is small (tangent-space Gaussian mapped via exp_map),
    so decryption recovers x approximately (noise adds breathing).

    Containment: if decrypt produces ||x_hat|| >= max_radius, raises
    ContainmentBreach — the vector has escaped the safe zone.
    """

    def __init__(
        self,
        *,
        dim: int,
        c: float = 1.0,
        noise_scale: float = 0.02,
        max_radius: float = 0.95,
        rng: Optional[np.random.Generator] = None,
    ):
        if dim <= 0:
            raise ValueError("dim must be positive.")
        if not (0.0 < max_radius < 1.0):
            raise ValueError("max_radius must be in (0,1).")
        if noise_scale < 0:
            raise ValueError("noise_scale must be >= 0.")
        self.dim = dim
        self.c = float(c)
        self.noise_scale = float(noise_scale)
        self.max_radius = float(max_radius)
        self.rng = rng or np.random.default_rng()

    def validate_vector(
        self, x: np.ndarray, *, label: str = "vector"
    ) -> np.ndarray:
        """Validate that a vector is inside the Poincaré ball."""
        x = np.asarray(x, dtype=float).reshape(-1)
        if x.shape[0] != self.dim:
            raise InvalidVector(
                f"{label} must have shape ({self.dim},), got {x.shape}."
            )
        n = _norm(x)
        if not np.isfinite(n):
            raise InvalidVector(f"{label} norm not finite.")
        if n >= 1.0:
            raise InvalidVector(
                f"{label} must satisfy ||x|| < 1.0 (Poincaré ball)."
            )
        if n >= self.max_radius:
            raise InvalidVector(
                f"{label} too close to boundary: ||x||={n:.6f} >= max_radius={self.max_radius}."
            )
        return x

    def sample_noise(self) -> np.ndarray:
        """Sample noise in tangent space and map to hyperbolic."""
        z = self.rng.normal(loc=0.0, scale=self.noise_scale, size=(self.dim,))
        return exp_map_zero(z, c=self.c)

    def encrypt(
        self,
        key: np.ndarray,
        x: np.ndarray,
        *,
        meta: Optional[Dict[str, Any]] = None,
    ) -> HLWECiphertext:
        """Encrypt a Poincaré ball vector with a symmetric key vector."""
        key = self.validate_vector(
            project_to_ball(key, max_norm=self.max_radius * 0.5), label="key"
        )
        x = self.validate_vector(x, label="plaintext")
        n_hyp = self.sample_noise()
        ct = mobius_add(mobius_add(x, key, c=self.c), n_hyp, c=self.c)
        rct = _norm(ct)
        return HLWECiphertext(ct=ct, radius_ct=rct, meta=dict(meta or {}))

    def decrypt(
        self, key: np.ndarray, ct: HLWECiphertext
    ) -> Tuple[np.ndarray, float]:
        """
        Decrypt a ciphertext and check containment.

        Returns (recovered_vector, radius).
        Raises ContainmentBreach if radius >= max_radius.
        """
        key = self.validate_vector(
            project_to_ball(key, max_norm=self.max_radius * 0.5), label="key"
        )
        ctv = np.asarray(ct.ct, dtype=float).reshape(-1)
        if ctv.shape[0] != self.dim:
            raise InvalidVector(f"ciphertext vector has wrong shape: {ctv.shape}")
        if _norm(ctv) >= 1.0:
            raise InvalidVector("ciphertext vector must be inside unit ball.")

        x_hat = mobius_add(ctv, mobius_neg(key), c=self.c)
        r = _norm(x_hat)
        if r >= self.max_radius:
            raise ContainmentBreach(
                f"Decrypted radius {r:.6f} >= max_radius {self.max_radius}."
            )
        return x_hat, r


# ---------------------------------------------------------------------------
# Optional Hybrid wrapper: Kyber768 KEM + symmetric H-LWE + HMAC tag
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HLWEHybridCiphertext:
    """Hybrid ciphertext: Kyber KEM + H-LWE vector + HMAC tag."""
    kem_ct: bytes
    vec_ct: HLWECiphertext
    tag: bytes
    meta: Dict[str, Any]


class HLWEHybridKEM:
    """
    Asymmetric transport for hyperbolic vectors:
      1. Use Kyber768 KEM to derive a shared secret
      2. Derive hyperbolic key vector from the shared secret
      3. Encrypt vector with HLWESymmetric
      4. Authenticate with HMAC(secret, kem_ct || vec_ct)

    Requires symphonic_cipher.scbe_aethermoore.pqc to be importable.
    """

    def __init__(
        self,
        *,
        dim: int,
        c: float = 1.0,
        noise_scale: float = 0.02,
        max_radius: float = 0.95,
    ):
        self.sym = HLWESymmetric(
            dim=dim, c=c, noise_scale=noise_scale, max_radius=max_radius
        )
        # Lazy import to avoid hard dependency
        from symphonic_cipher.scbe_aethermoore.pqc.pqc_core import Kyber768

        self._kyber = Kyber768

    def _tag(
        self, secret: bytes, kem_ct: bytes, vec_ct: HLWECiphertext
    ) -> bytes:
        """Compute HMAC tag binding KEM ciphertext to vector ciphertext."""
        data = kem_ct + b"||" + vec_ct.ct.astype(np.float64).tobytes()
        return hmac_mod.new(secret, data, hashlib.sha256).digest()

    def encrypt(
        self,
        pk: bytes,
        x: np.ndarray,
        *,
        meta: Optional[Dict[str, Any]] = None,
    ) -> HLWEHybridCiphertext:
        """Encrypt a vector using Kyber768 KEM + H-LWE."""
        result = self._kyber.encapsulate(pk)
        shared_secret = result.shared_secret
        kem_ct = result.ciphertext

        key_vec = key_vector_from_secret(
            shared_secret,
            dim=self.sym.dim,
            c=self.sym.c,
            max_radius=self.sym.max_radius,
        )
        vec_ct = self.sym.encrypt(key_vec, x, meta=meta)
        tag = self._tag(shared_secret, kem_ct, vec_ct)

        return HLWEHybridCiphertext(
            kem_ct=kem_ct, vec_ct=vec_ct, tag=tag, meta=dict(meta or {})
        )

    def decrypt(
        self, sk: bytes, ct: HLWEHybridCiphertext
    ) -> Tuple[np.ndarray, float]:
        """Decrypt a hybrid ciphertext. Verifies HMAC tag first."""
        shared_secret = self._kyber.decapsulate(sk, ct.kem_ct)

        expected = self._tag(shared_secret, ct.kem_ct, ct.vec_ct)
        if not hmac_mod.compare_digest(expected, ct.tag):
            raise AuthenticationError("HLWEHybridCiphertext tag mismatch.")

        key_vec = key_vector_from_secret(
            shared_secret,
            dim=self.sym.dim,
            c=self.sym.c,
            max_radius=self.sym.max_radius,
        )
        return self.sym.decrypt(key_vec, ct.vec_ct)
