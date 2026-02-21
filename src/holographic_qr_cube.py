"""Holographic QR cube pi^phi derivation primitives.

Spec wall scalar:
    H(d*, R) = R * pi^(phi * d*)
"""

from __future__ import annotations

import hashlib
import math
from typing import Iterable

PHI = 1.618033988749895


def pi_phi_wall(d_star: float, R: float = 1.5) -> float:
    """Return scalar harmonic wall value H(d*,R) = R * pi^(phi*d*)."""
    return float(R) * math.pow(math.pi, PHI * float(d_star))


def pi_phi_key_derivation(
    d_star: float,
    R: float = 1.5,
    *,
    as_bytes: bool = False,
    domain_axes: Iterable[float] | None = None,
) -> float | bytes:
    """Derive scalar wall value or deterministic key material.

    When `as_bytes=False`, returns wall scalar.
    When `as_bytes=True`, returns SHA-256 digest of canonicalized inputs.
    """
    wall = pi_phi_wall(d_star=d_star, R=R)
    if not as_bytes:
        return wall

    axes = tuple(domain_axes or ())
    payload = f"R={R:.17g}|d*={d_star:.17g}|H={wall:.17g}|axes={axes}".encode("utf-8")
    return hashlib.sha256(payload).digest()


def derive_pi_phi_key(d_star: float, R: float = 1.5) -> float:
    """Alias to keep compatibility with variant naming in tests/callers."""
    return pi_phi_wall(d_star=d_star, R=R)
