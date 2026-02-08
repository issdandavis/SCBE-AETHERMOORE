"""
Hyperbolic LWE (H-LWE) Vector Encryption
=========================================

@file h_lwe.py
@module crypto/h_lwe
@layer Layer 5, Layer 6, Layer 7, Layer 12
@component Poincaré-ball vector encryption with containment enforcement
@version 3.2.5

Symmetric "hyperbolic vector encryption" on the Poincaré ball using
Möbius addition + tangent-space noise ("breathing-safe" behavior).

Security model:
- Containment breach detection: decrypt raises if the recovered vector
  drifts toward/over the safety radius.
- Optional hybrid/asymmetric wrapper: uses QuasiLWE KEM (if present)
  only to exchange a session key; the actual vector encryption stays
  hyperbolic.
- HMAC-SHA256 authentication for the hybrid path.

NOTE: This is a governance/containment primitive, not a proven IND-CCA
scheme. Treat it as an authenticated transport layer only when wrapped
with AEAD/HMAC/signatures.
"""

from __future__ import annotations

import hmac
import hashlib
import math
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np


# ----------------------------
# Exceptions
# ----------------------------

class HLWEError(Exception):
    """Base class for H-LWE errors."""


class ContainmentBreach(HLWEError):
    """Raised when decrypted vector exits the allowed Poincaré radius."""


class InvalidVector(HLWEError):
    """Raised when inputs are not valid hyperbolic vectors."""


class AuthenticationError(HLWEError):
    """Raised when ciphertext authenticity check fails."""


# ----------------------------
# Hyperbolic (Poincaré ball) ops
# ----------------------------

def _norm(x: np.ndarray) -> float:
    """L2 norm of a vector."""
    return float(np.linalg.norm(x))


def project_to_ball(x: np.ndarray, *, max_norm: float = 1.0 - 1e-8) -> np.ndarray:
    """
    Radially project to inside the open ball (norm < 1).

    Args:
        x: Input vector.
        max_norm: Maximum allowed norm (must be < 1.0).

    Returns:
        Vector projected inside the ball.
    """
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

    Formula: tanh(sqrt(c) * ||v||) * v / (sqrt(c) * ||v||)
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

    Formula: atanh(sqrt(c) * ||x||) * x / (sqrt(c) * ||x||)
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
    """
    Möbius addition on Poincaré ball (curvature c).

    Formula:
        ((1 + 2c<x,y> + c||y||²)x + (1 - c||x||²)y) / (1 + 2c<x,y> + c²||x||²||y||²)
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.shape != y.shape:
        raise InvalidVector("Möbius add requires matching shapes.")
    if c <= 0:
        raise ValueError("Curvature c must be positive.")

    x2 = float(np.dot(x, x))
    y2 = float(np.dot(y, y))
    xy = float(np.dot(x, y))

    # Clamp to avoid denom blowups near boundary
    x2 = min(x2, 1.0 - 1e-12)
    y2 = min(y2, 1.0 - 1e-12)

    num = (1 + 2 * c * xy + c * y2) * x + (1 - c * x2) * y
    den = 1 + 2 * c * xy + (c * c) * x2 * y2
    if abs(den) < 1e-15:
        xx = project_to_ball(x, max_norm=1.0 - 1e-6)
        yy = project_to_ball(y, max_norm=1.0 - 1e-6)
        return mobius_add(xx, yy, c=c)
    out = num / den
    return project_to_ball(out, max_norm=1.0 - 1e-10)


def mobius_neg(x: np.ndarray) -> np.ndarray:
    """Möbius negation (additive inverse) on Poincaré ball."""
    return -np.asarray(x, dtype=float)


# ----------------------------
# KDF helpers
# ----------------------------

def hkdf_sha256(
    ikm: bytes,
    *,
    salt: bytes = b"",
    info: bytes = b"",
    length: int = 32,
) -> bytes:
    """
    Minimal HKDF (RFC 5869) with SHA-256.

    Args:
        ikm: Input keying material.
        salt: Optional salt value.
        info: Optional context/application info.
        length: Output length in bytes.

    Returns:
        Derived key material of requested length.
    """
    if length <= 0:
        raise ValueError("HKDF length must be > 0.")
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    t = b""
    okm = b""
    counter = 1
    while len(okm) < length:
        t = hmac.new(prk, t + info + bytes([counter]), hashlib.sha256).digest()
        okm += t
        counter += 1
        if counter > 255:
            raise ValueError("HKDF too long.")
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

    Args:
        secret: Raw secret bytes (e.g. from KEM shared secret).
        dim: Vector dimensionality.
        c: Poincaré ball curvature.
        tangent_scale: Scale factor for tangent-space projection.
        max_radius: Maximum allowed radius for any vector.

    Returns:
        Key vector inside the Poincaré ball.
    """
    raw = hkdf_sha256(secret, salt=b"scbe-hlwe", info=b"keyvec", length=4 * dim)
    ints = np.frombuffer(raw, dtype=np.uint32).astype(np.float64)
    # Map to [-1, 1]
    u = (ints / (2**32 - 1.0)) * 2.0 - 1.0
    tangent = u * tangent_scale
    k = exp_map_zero(tangent, c=c)
    # Ensure comfortably inside
    if _norm(k) >= max_radius * 0.5:
        k = project_to_ball(k, max_norm=max_radius * 0.5)
    return k


# ----------------------------
# Symmetric H-LWE
# ----------------------------

@dataclass(frozen=True)
class HLWECiphertext:
    """
    Ciphertext for symmetric H-LWE vector encryption.

    ct = x (+) k (+) n
    where (+) is Möbius addition and n is noise mapped from
    tangent space via exp_map_zero.
    """
    ct: np.ndarray
    radius_ct: float
    meta: Dict[str, Any]


class HLWESymmetric:
    """
    Geometry-preserving encryption for Poincaré-ball vectors.

    Encrypts a vector x inside the Poincaré ball by adding a key vector
    via Möbius addition, plus small tangent-space noise.  Decryption
    subtracts the key and checks that the result remains inside the
    containment radius.

    Args:
        dim: Vector dimensionality.
        c: Poincaré ball curvature (default 1.0).
        noise_scale: Std-dev for Gaussian tangent-space noise.
        max_radius: Maximum allowed norm for valid vectors.
        rng: NumPy random generator (for reproducibility).
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

    def validate_vector(self, x: np.ndarray, *, label: str = "vector") -> np.ndarray:
        """Validate that x is a proper Poincaré-ball vector."""
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
                f"{label} too close to boundary: ||x||={n:.6f} >= "
                f"max_radius={self.max_radius}."
            )
        return x

    def sample_noise(self) -> np.ndarray:
        """Sample small noise in tangent space, map to hyperbolic via exp_map."""
        z = self.rng.normal(loc=0.0, scale=self.noise_scale, size=(self.dim,))
        return exp_map_zero(z, c=self.c)

    def encrypt(
        self,
        key: np.ndarray,
        x: np.ndarray,
        *,
        meta: Optional[Dict[str, Any]] = None,
    ) -> HLWECiphertext:
        """
        Encrypt a Poincaré-ball vector x with symmetric key.

        ct = (x (+) key) (+) noise

        Args:
            key: Symmetric key vector (small, near origin).
            x: Plaintext vector inside the ball.
            meta: Optional metadata dict (not encrypted).

        Returns:
            HLWECiphertext with the encrypted vector and metadata.
        """
        key = self.validate_vector(
            project_to_ball(key, max_norm=self.max_radius * 0.5), label="key"
        )
        x = self.validate_vector(x, label="plaintext")
        n_hyp = self.sample_noise()
        # Left-key convention: ct = k (+) (x (+) n)
        # This allows exact left-cancellation on decrypt: (-k) (+) ct = x (+) n
        ct = mobius_add(key, mobius_add(x, n_hyp, c=self.c), c=self.c)
        rct = _norm(ct)
        return HLWECiphertext(ct=ct, radius_ct=rct, meta=dict(meta or {}))

    def decrypt(
        self, key: np.ndarray, ct: HLWECiphertext
    ) -> Tuple[np.ndarray, float]:
        """
        Decrypt a ciphertext and enforce containment.

        x_hat = ct (+) (-key)

        Raises ContainmentBreach if ||x_hat|| >= max_radius.

        Args:
            key: Same symmetric key used for encryption.
            ct: The ciphertext to decrypt.

        Returns:
            Tuple of (decrypted vector, its radius).

        Raises:
            ContainmentBreach: If decrypted vector exceeds safety radius.
            InvalidVector: If ciphertext is malformed.
        """
        key = self.validate_vector(
            project_to_ball(key, max_norm=self.max_radius * 0.5), label="key"
        )
        ctv = np.asarray(ct.ct, dtype=float).reshape(-1)
        if ctv.shape[0] != self.dim:
            raise InvalidVector(
                f"ciphertext vector has wrong shape: {ctv.shape}"
            )
        if _norm(ctv) >= 1.0:
            raise InvalidVector("ciphertext vector must be inside unit ball.")
        # Left-cancellation: (-k) (+) ct = (-k) (+) (k (+) (x (+) n)) = x (+) n
        x_hat = mobius_add(mobius_neg(key), ctv, c=self.c)
        r = _norm(x_hat)
        if r >= self.max_radius:
            raise ContainmentBreach(
                f"Decrypted radius {r:.6f} >= max_radius {self.max_radius}."
            )
        return x_hat, r


# ----------------------------
# Optional Hybrid wrapper
# ----------------------------

@dataclass(frozen=True)
class HLWEHybridCiphertext:
    """Hybrid ciphertext: KEM ciphertext + H-LWE vector + HMAC tag."""
    kem_ct: Any
    vec_ct: HLWECiphertext
    tag: bytes  # HMAC over (kem_ct || vec_ct.ct)
    meta: Dict[str, Any]


class HLWEHybridKEM:
    """
    Asymmetric transport for hyperbolic vectors.

    Uses QuasiLWE KEM to derive a shared secret, then encrypts the
    vector with HLWESymmetric and authenticates with HMAC(secret, ct).

    If QuasiLWE KEM isn't available, import will fail; tests should skip.

    Args:
        dim: Vector dimensionality.
        c: Poincaré ball curvature.
        noise_scale: Noise for symmetric H-LWE.
        max_radius: Containment radius.
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
        from src.crypto.quasi_lwe import QuasiLWEKEM  # type: ignore

        self.kem = QuasiLWEKEM()

    @staticmethod
    def _serialize_any(obj: Any) -> bytes:
        """Best-effort stable serialization for HMAC binding."""
        if obj is None:
            return b"null"
        if isinstance(obj, bytes):
            return b"b:" + obj
        if isinstance(obj, str):
            return b"s:" + obj.encode("utf-8", "surrogatepass")
        if isinstance(obj, (int, float, bool)):
            return f"n:{obj!r}".encode("utf-8")
        if isinstance(obj, np.ndarray):
            return b"nd:" + obj.astype(np.float64).tobytes()
        if isinstance(obj, dict):
            items = sorted((str(k), obj[k]) for k in obj.keys())
            return b"d:" + b"|".join(
                k.encode() + b"=" + HLWEHybridKEM._serialize_any(v)
                for k, v in items
            )
        if isinstance(obj, (list, tuple)):
            return b"a:" + b"|".join(
                HLWEHybridKEM._serialize_any(v) for v in obj
            )
        return b"repr:" + repr(obj).encode("utf-8", "surrogatepass")

    def _tag(
        self, secret: bytes, kem_ct: Any, vec_ct: HLWECiphertext
    ) -> bytes:
        """Compute HMAC tag binding KEM ciphertext to vector ciphertext."""
        data = (
            self._serialize_any(kem_ct)
            + b"||"
            + self._serialize_any(vec_ct.ct)
        )
        return hmac.new(secret, data, hashlib.sha256).digest()

    def encrypt(
        self,
        pk: Any,
        x: np.ndarray,
        *,
        meta: Optional[Dict[str, Any]] = None,
    ) -> HLWEHybridCiphertext:
        """
        Encrypt a vector with asymmetric H-LWE (KEM + symmetric).

        Args:
            pk: Public key for the KEM.
            x: Plaintext vector inside the ball.
            meta: Optional metadata dict.

        Returns:
            HLWEHybridCiphertext with KEM ct, vector ct, and HMAC tag.
        """
        shared_secret, kem_ct = self.kem.encapsulate(pk)
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
        self, sk: Any, ct: HLWEHybridCiphertext
    ) -> Tuple[np.ndarray, float]:
        """
        Decrypt a hybrid ciphertext with secret key.

        Verifies HMAC tag before decryption.

        Args:
            sk: Secret key for the KEM.
            ct: The hybrid ciphertext.

        Returns:
            Tuple of (decrypted vector, its radius).

        Raises:
            AuthenticationError: If HMAC tag doesn't match.
            ContainmentBreach: If decrypted vector exceeds safety radius.
        """
        shared_secret = self.kem.decapsulate(sk, ct.kem_ct)
        expected = self._tag(shared_secret, ct.kem_ct, ct.vec_ct)
        if not hmac.compare_digest(expected, ct.tag):
            raise AuthenticationError("HLWEHybridCiphertext tag mismatch.")
        key_vec = key_vector_from_secret(
            shared_secret,
            dim=self.sym.dim,
            c=self.sym.c,
            max_radius=self.sym.max_radius,
        )
        return self.sym.decrypt(key_vec, ct.vec_ct)
