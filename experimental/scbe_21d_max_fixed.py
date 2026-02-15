"""SCBE 21D Maximum Build (correctness-hardened experimental module).

IMPORTANT:
- This module is EXPERIMENTAL and non-authoritative.
- Cryptographic primitives marked "toy" are placeholders and must not be used in production.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import math
import secrets
from typing import Iterable, Tuple

import numpy as np


TARGET_P_NORM = 4.0


def poincare_ball_distance(u: np.ndarray, v: np.ndarray, eps: float = 1e-12) -> float:
    """Geodesic distance on the Poincaré ball using arcosh metric form."""
    u = np.asarray(u, dtype=float)
    v = np.asarray(v, dtype=float)
    nu2 = float(np.dot(u, u))
    nv2 = float(np.dot(v, v))
    if nu2 >= 1.0 or nv2 >= 1.0:
        raise ValueError("Inputs must lie inside unit ball (||x|| < 1).")

    denom = max((1.0 - nu2) * (1.0 - nv2), eps)
    diff2 = float(np.dot(u - v, u - v))
    arg = 1.0 + (2.0 * diff2 / denom)
    return float(np.arccosh(max(arg, 1.0 + eps)))


def hkdf_sha3_256(ikm: bytes, salt: bytes, info: bytes, length: int) -> bytes:
    """RFC5869-style HKDF with HMAC-SHA3-256."""
    hash_len = hashlib.sha3_256().digest_size
    if length <= 0:
        raise ValueError("length must be > 0")
    if length > 255 * hash_len:
        raise ValueError("length too large for HKDF")

    prk = hmac.new(salt, ikm, hashlib.sha3_256).digest()
    okm = bytearray()
    t = b""
    counter = 1
    while len(okm) < length:
        t = hmac.new(prk, t + info + bytes([counter]), hashlib.sha3_256).digest()
        okm.extend(t)
        counter += 1
    return bytes(okm[:length])


def derive_sacred_egg_keypair(master_secret: bytes, context: bytes = b"scbe-sacred-egg") -> Tuple[bytes, bytes]:
    """Deterministic derivation of a toy keypair from a master secret.

    root_pk derivation remains toy and should be replaced with a real signature scheme.
    """
    out = hkdf_sha3_256(master_secret, salt=b"scbe-root-salt", info=context, length=64)
    root_sk = out[:32]
    root_pk = hashlib.sha3_256(root_sk).digest()  # toy public key mapping
    return root_sk, root_pk


def fail_to_noise(reason: str, length: int = 256) -> bytes:
    """Returns fixed-size noise blob to avoid shape leaks on failure paths."""
    _ = reason
    return secrets.token_bytes(length)


def project_momentum_norm(p: np.ndarray, target_norm: float = TARGET_P_NORM, eps: float = 1e-12) -> np.ndarray:
    """Safely projects momentum vector onto fixed L2 norm sphere."""
    p = np.asarray(p, dtype=float)
    nrm = float(np.linalg.norm(p))
    if nrm < eps:
        out = np.zeros_like(p)
        out[0] = target_norm
        return out
    return p * (target_norm / nrm)


def ring_lattice_project(state: np.ndarray, max_step: float = 0.5) -> Tuple[np.ndarray, bool, float]:
    """Deterministically limit adjacent deltas and report pre-repair violation."""
    state = np.asarray(state, dtype=float).copy()
    if state.size < 2:
        return state, False, 0.0

    deltas = np.diff(state)
    pre_residual = float(np.max(np.abs(deltas)))
    violated = pre_residual > max_step

    for i in range(1, state.size):
        delta = state[i] - state[i - 1]
        if abs(delta) > max_step:
            state[i] = state[i - 1] + math.copysign(max_step, delta)

    return state, violated, pre_residual


def governance_weight(base_gamma: float, delta_tau: float) -> float:
    """Increase weight under time pressure (delta_tau < 1), decrease otherwise."""
    if delta_tau <= 0:
        raise ValueError("delta_tau must be positive")
    return base_gamma / delta_tau


@dataclass(frozen=True)
class GenesisCertificate:
    version: str
    root_pk_hex: str
    transcript_hash_hex: str


def make_genesis_certificate(master_secret: bytes, transcript_chunks: Iterable[bytes]) -> GenesisCertificate:
    """Generate deterministic toy genesis artifact for test vectors."""
    _, root_pk = derive_sacred_egg_keypair(master_secret)
    h = hashlib.sha3_256()
    for chunk in transcript_chunks:
        h.update(len(chunk).to_bytes(8, "big"))
        h.update(chunk)

    return GenesisCertificate(
        version="scbe-21d-max-fixed-experimental",
        root_pk_hex=root_pk.hex(),
        transcript_hash_hex=h.hexdigest(),
    )


def _self_test() -> None:
    u = np.array([0.1, 0.2, 0.1])
    v = np.array([0.2, -0.1, 0.1])
    d = poincare_ball_distance(u, v)
    assert math.isfinite(d) and d > 0.0

    sk, pk = derive_sacred_egg_keypair(b"master")
    assert len(sk) == 32 and len(pk) == 32

    p = project_momentum_norm(np.array([2.0, 0.0, 0.0]), target_norm=4.0)
    assert np.isclose(np.linalg.norm(p), 4.0)

    repaired, violated, residual = ring_lattice_project(np.array([0.0, 2.0, 5.0]), max_step=1.0)
    assert violated is True and residual == 3.0
    assert np.allclose(repaired, np.array([0.0, 1.0, 2.0]))

    assert governance_weight(2.0, 0.5) > 2.0


if __name__ == "__main__":
    _self_test()
    print("scbe_21d_max_fixed self-test passed")
