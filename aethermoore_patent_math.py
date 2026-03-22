"""Root import wrapper for the patent reference math helpers."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from typing import Iterable, Sequence, Tuple


def harmonic_security_scaling(d: int, R: float) -> float:
    if not isinstance(d, int):
        raise TypeError("d must be int")
    if d < 0:
        raise ValueError("d must be >= 0")
    if not isinstance(R, (int, float)):
        raise TypeError("R must be a number")
    if R <= 0:
        raise ValueError("R must be > 0")
    return float(R) ** (d * d)


def chladni_nodal_constraint(x: float, y: float, n: int, m: int) -> float:
    if not isinstance(n, int) or not isinstance(m, int):
        raise TypeError("n and m must be ints")
    return (
        math.cos(n * math.pi * x) * math.cos(m * math.pi * y)
        - math.cos(m * math.pi * x) * math.cos(n * math.pi * y)
    )


def derive_modes_from_6d(agent_vec_6d: Sequence[float], *, n_max: int = 64) -> Tuple[int, int]:
    if len(agent_vec_6d) != 6:
        raise ValueError("agent_vec_6d must have length 6")
    if n_max < 2:
        raise ValueError("n_max must be >= 2")

    payload = ",".join(f"{value:.12g}" for value in agent_vec_6d).encode("utf-8")
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
    n, m = derive_modes_from_6d(agent_vec_6d, n_max=n_max)
    value = chladni_nodal_constraint(x, y, n, m)
    if abs(value) <= epsilon:
        return VoxelAccessResult(True, payload_value)
    obfuscated = math.sin((value + noise_seed) * 1e6) * 0.5 + 0.5
    return VoxelAccessResult(False, obfuscated)


def complementary_control_signals(base: float, *, authorized: bool) -> Tuple[float, float]:
    if base <= 0:
        raise ValueError("base must be > 0")
    if authorized:
        return base, 1.0 / base
    attenuation = 1e-3
    return base * attenuation, (1.0 / base) * attenuation


def grid_corner_mask(width: int, height: int) -> Iterable[Tuple[int, int]]:
    if width < 2 or height < 2:
        raise ValueError("width and height must be >= 2")
    return {(0, 0), (0, height - 1), (width - 1, 0), (width - 1, height - 1)}


def octave_transpose(f_env: float, n: int) -> float:
    if f_env <= 0:
        raise ValueError("f_env must be > 0")
    if not isinstance(n, int):
        raise TypeError("n must be int")
    return f_env * (2.0 ** n)


def choose_octave_n_for_band(f_env: float, band: Tuple[float, float]) -> int:
    if f_env <= 0:
        raise ValueError("f_env must be > 0")
    low, high = band
    if low <= 0 or high <= 0 or low >= high:
        raise ValueError("band must be (low>0, high>low)")

    scale_low = low / f_env
    scale_high = high / f_env
    n_min = math.ceil(math.log2(scale_low))
    n_max = math.floor(math.log2(scale_high))
    if n_min <= n_max:
        return int(n_min)

    n_low = round(math.log2(scale_low))
    n_high = round(math.log2(scale_high))
    candidate_low = octave_transpose(f_env, int(n_low))
    candidate_high = octave_transpose(f_env, int(n_high))

    def _distance(value: float) -> float:
        if value < low:
            return low - value
        if value > high:
            return value - high
        return 0.0

    return int(n_low) if _distance(candidate_low) <= _distance(candidate_high) else int(n_high)


__all__ = [
    "VoxelAccessResult",
    "harmonic_security_scaling",
    "chladni_nodal_constraint",
    "derive_modes_from_6d",
    "cymatic_voxel_access",
    "complementary_control_signals",
    "grid_corner_mask",
    "octave_transpose",
    "choose_octave_n_for_band",
]
