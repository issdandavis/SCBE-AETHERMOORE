"""
@file qr_cube_kdf.py
@module scbe_aethermoore/qr_cube_kdf
@layer Layer 12, Layer 13
@component Holographic QR Cube π^φ Key Derivation
@version 1.0.0

Holographic QR Cube π^φ Key Derivation (kdf='pi_phi')
=====================================================

Derives cryptographic keys bound to the harmonic geometry of a voxel record.
The core innovation is mixing the super-exponential cost scalar π^(φ·d*)
into the key material, making key derivation computationally coupled to
the agent's position in hyperbolic space.

Construction:
  1. Validate inputs (reject NaN, Inf, out-of-range coherence)
  2. Compute harmonic cost scalar: cost = π^(φ · d*)
  3. Build IKM by hashing all inputs with domain-separated prefixes
  4. HKDF-Extract: PRK = HMAC-SHA256(salt, IKM)
  5. HKDF-Expand: OKM = expand(PRK, context || committed_fields, out_len)

Security properties:
  - Deterministic for identical inputs
  - Input-sensitive: any single-field change → different key
  - Domain-separated via context parameter
  - NaN/Inf rejection (numeric hygiene)
  - HKDF-Expand prefix property: shorter output is prefix of longer

Reference: VoxelRecord.seal.kdf = 'pi_phi' (src/harmonic/voxelRecord.ts)
"""

from __future__ import annotations

import hashlib
import hmac
import math
import struct
from typing import Optional


# =============================================================================
# CONSTANTS
# =============================================================================

PI = math.pi
PHI = (1 + math.sqrt(5)) / 2  # Golden ratio ≈ 1.6180339887


# =============================================================================
# HKDF-SHA256 (RFC 5869)
# =============================================================================

def _hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    """HKDF-Extract: PRK = HMAC-SHA256(salt, ikm)."""
    if not salt:
        salt = b"\x00" * 32
    return hmac.new(salt, ikm, hashlib.sha256).digest()


def _hkdf_expand(prk: bytes, info: bytes, length: int) -> bytes:
    """HKDF-Expand: OKM = T(1) || T(2) || ... truncated to length."""
    t = b""
    okm = b""
    counter = 1
    while len(okm) < length:
        t = hmac.new(prk, t + info + bytes([counter]), hashlib.sha256).digest()
        okm += t
        counter += 1
    return okm[:length]


# =============================================================================
# HELPERS
# =============================================================================

def _pi_phi_scalar(d_star: float) -> float:
    """
    Compute the harmonic cost scalar: π^(φ · d*).

    Monotonically increasing with d* (φ > 0, π > 1).
    At d*=0: returns 1.0
    At d*=1: returns π^φ ≈ 5.047
    Super-exponential growth makes adversarial drift expensive.
    """
    return PI ** (PHI * d_star)


def _assert_finite(value: float, name: str) -> None:
    """Reject NaN and ±Inf with a descriptive error."""
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value!r}")


def _commit_field(domain: bytes, data: bytes) -> bytes:
    """
    Domain-separated SHA-256 commitment of a single field.

    Format: SHA-256(domain || le64(len(data)) || data)

    The 8-byte little-endian length prefix prevents boundary-ambiguity
    attacks where domain suffix could alias with data prefix.
    """
    length_prefix = struct.pack("<Q", len(data))
    return hashlib.sha256(domain + length_prefix + data).digest()


# =============================================================================
# CORE
# =============================================================================

def derive_pi_phi_key(
    *,
    d_star: float,
    coherence: float,
    cube_id: str,
    aad: bytes,
    nonce: bytes,
    salt: bytes = b"",
    out_len: int = 32,
    context: bytes = b"scbe:qr-cube:pi_phi:v1",
) -> bytes:
    """
    Derive a key from the π^φ harmonic cost function bound to voxel geometry.

    Parameters
    ----------
    d_star : float
        Hyperbolic distance (harmonic drift). Must be finite.
    coherence : float
        Coherence metric ∈ [0, 1]. Must be finite and in range.
    cube_id : str
        Voxel cube identifier (e.g., "cube-001").
    aad : bytes
        Additional authenticated data (e.g., header hash).
    nonce : bytes
        Per-derivation nonce (e.g., 12 bytes from SacredEggSeal).
    salt : bytes
        Optional salt for HKDF-Extract (default: empty → 32 zero bytes).
    out_len : int
        Desired output length in bytes (default: 32).
    context : bytes
        Domain separation context for HKDF-Expand info field.

    Returns
    -------
    bytes
        Derived key of exactly `out_len` bytes.

    Raises
    ------
    ValueError
        If d_star or coherence is NaN/Inf, or coherence is outside [0, 1].
    """
    # ------------------------------------------------------------------
    # 1. Input validation (numeric hygiene)
    # ------------------------------------------------------------------
    _assert_finite(d_star, "d_star")
    _assert_finite(coherence, "coherence")
    if not (0.0 <= coherence <= 1.0):
        raise ValueError(
            f"coherence must be in range 0..1, got {coherence!r}"
        )

    # ------------------------------------------------------------------
    # 2. Compute harmonic cost scalar: π^(φ · d*)
    # ------------------------------------------------------------------
    cost = _pi_phi_scalar(d_star)

    # ------------------------------------------------------------------
    # 3. Build IKM from domain-separated field commitments
    #
    # Each field gets its own SHA-256 commitment with a unique prefix,
    # then all are concatenated. This ensures every input contributes
    # to the derived key and no two fields can collide.
    # ------------------------------------------------------------------
    cost_bytes = struct.pack(">d", cost)          # IEEE 754 big-endian double
    d_star_bytes = struct.pack(">d", d_star)
    coherence_bytes = struct.pack(">d", coherence)

    ikm = b"".join([
        _commit_field(b"pi_phi:cost:", cost_bytes),
        _commit_field(b"pi_phi:d_star:", d_star_bytes),
        _commit_field(b"pi_phi:coherence:", coherence_bytes),
        _commit_field(b"pi_phi:cube_id:", cube_id.encode("utf-8")),
        _commit_field(b"pi_phi:aad:", aad),
        _commit_field(b"pi_phi:nonce:", nonce),
    ])

    # ------------------------------------------------------------------
    # 4. HKDF-Extract: PRK = HMAC-SHA256(salt, IKM)
    # ------------------------------------------------------------------
    prk = _hkdf_extract(salt, ikm)

    # ------------------------------------------------------------------
    # 5. HKDF-Expand: OKM with context as info
    # ------------------------------------------------------------------
    return _hkdf_expand(prk, context, out_len)
