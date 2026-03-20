# aethermoore_patent_math.py
"""
@file aethermoore_patent_math.py
@module patent
@layer Layer 2, 5, 12, 14
@component Patent Claims Reference Implementation
@version 1.0.0

Reference implementation for 4 patent claims with testable,
deterministic functions. Each function maps to a specific patent claim.

Author: Issac Davis
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Iterable, Tuple, Sequence


# -------------------------
# PATENT 1: Harmonic Scaling
# -------------------------
def harmonic_security_scaling(d: int, R: float) -> float:
    """
    H(d, R) = R^(d^2)
    Domain constraints:
      - d must be >= 0 integer (dimensions)
      - R must be > 0 real
    """
    if not isinstance(d, int):
        raise TypeError("d must be int")
    if d < 0:
        raise ValueError("d must be >= 0")
    if not isinstance(R, (int, float)):
        raise TypeError("R must be a number")
    if R <= 0:
        raise ValueError("R must be > 0")
    return float(R) ** (d * d)


# --------------------------------
# PATENT 2: Cymatic Voxel Storage
# --------------------------------
def chladni_nodal_constraint(x: float, y: float, n: int, m: int) -> float:
    """
    cos(nπx)cos(mπy) - cos(mπx)cos(nπy)
    Nodal lines are where this expression == 0.
    """
    if not isinstance(n, int) or not isinstance(m, int):
        raise TypeError("n and m must be ints")
    return (
        math.cos(n * math.pi * x) * math.cos(m * math.pi * y)
        - math.cos(m * math.pi * x) * math.cos(n * math.pi * y)
    )


def derive_modes_from_6d(agent_vec_6d: Sequence[float], *, n_max: int = 64) -> Tuple[int, int]:
    """
    Deterministic mapping from a 6D agent vector -> integer Chladni mode indices (n, m).
    Patent-critical properties:
      - deterministic
      - bounded to [1..n_max]
      - small perturbations can change modes
    """
    if len(agent_vec_6d) != 6:
        raise ValueError("agent_vec_6d must have length 6")
    if n_max < 2:
        raise ValueError("n_max must be >= 2")

    payload = ",".join(f"{v:.12g}" for v in agent_vec_6d).encode("utf-8")
    digest = hashlib.sha256(payload).digest()

    a = int.from_bytes(digest[0:2], "big")
    b = int.from_bytes(digest[2:4], "big")

    n = 1 + (a % n_max)
    m = 1 + (b % n_max)

    if n == m:
        m = 1 + ((m + 1) % n_max)

    return n, m


@dataclass(frozen=True)
class VoxelAccessResult:
    visible: bool
    decoded_value: float


def cymatic_voxel_access(
    x: float,
    y: float,
    agent_vec_6d: Sequence[float],
    *,
    epsilon: float = 1e-6,
    n_max: int = 64,
    payload_value: float = 1.0,
    noise_seed: float = 0.3141592653,
) -> VoxelAccessResult:
    """
    Data is only "visible" if nodal constraint is satisfied.
    If not satisfied, return a noise-like value.
    """
    n, m = derive_modes_from_6d(agent_vec_6d, n_max=n_max)
    v = chladni_nodal_constraint(x, y, n, m)
    if abs(v) <= epsilon:
        return VoxelAccessResult(True, payload_value)
    obf = math.sin((v + noise_seed) * 1e6) * 0.5 + 0.5
    return VoxelAccessResult(False, obf)


# ------------------------------
# PATENT 3: Flux Interaction
# ------------------------------
def complementary_control_signals(base: float, *, authorized: bool) -> Tuple[float, float]:
    """
    Generate complementary signals (f, g) such that:
      - In authorized region: f * g ≈ 1
      - In unauthorized region: product is attenuated (< 1)
    """
    if base <= 0:
        raise ValueError("base must be > 0")
    if authorized:
        f = base
        g = 1.0 / base
        return f, g
    atten = 1e-3
    f = base * atten
    g = (1.0 / base) * atten
    return f, g


def grid_corner_mask(width: int, height: int) -> Iterable[Tuple[int, int]]:
    """
    Defines the 4 'nodal corners' on a grid where reinforcement is allowed.
    """
    if width < 2 or height < 2:
        raise ValueError("width and height must be >= 2")
    return {(0, 0), (0, height - 1), (width - 1, 0), (width - 1, height - 1)}


# --------------------------------
# PATENT 4: Stellar Pulse
# --------------------------------
def octave_transpose(f_env: float, n: int) -> float:
    """
    f_control = f_env * 2^n
    """
    if f_env <= 0:
        raise ValueError("f_env must be > 0")
    if not isinstance(n, int):
        raise TypeError("n must be int")
    return f_env * (2.0 ** n)


def choose_octave_n_for_band(f_env: float, band: Tuple[float, float]) -> int:
    """
    Choose integer n such that f_env * 2^n falls inside [band_low, band_high]
    when possible, otherwise choose n that minimizes distance to the band.
    """
    if f_env <= 0:
        raise ValueError("f_env must be > 0")
    low, high = band
    if low <= 0 or high <= 0 or low >= high:
        raise ValueError("band must be (low>0, high>low)")

    s_low = low / f_env
    s_high = high / f_env

    n_min = math.ceil(math.log2(s_low))
    n_max = math.floor(math.log2(s_high))
    if n_min <= n_max:
        return int(n_min)

    n_close_low = round(math.log2(s_low))
    n_close_high = round(math.log2(s_high))
    f1 = octave_transpose(f_env, int(n_close_low))
    f2 = octave_transpose(f_env, int(n_close_high))

    def dist_to_band(f: float) -> float:
        if f < low:
            return low - f
        if f > high:
            return f - high
        return 0.0

    return int(n_close_low) if dist_to_band(f1) <= dist_to_band(f2) else int(n_close_high)
