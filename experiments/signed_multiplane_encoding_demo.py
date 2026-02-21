"""
Signed multi-plane encoding demo.

Idea implemented:
1. Signed-binary states per plane: {-1, -0, +0, +1}
2. Balanced ternary per plane: {-1, 0, +1}
3. Two planes (a, b) -> combinational state expansion
4. Sphere/spiral codebook (Fibonacci sphere anchors + rotated local vectors)
5. Decode by nearest codeword and compare capacity/collision behavior
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import argparse
import math
from typing import Dict, Iterable, List, Tuple

import numpy as np


@dataclass(frozen=True)
class SignedBit:
    """A signed binary symbol: magnitude in {0,1} and sign in {-1,+1}."""

    magnitude: int
    sign: int

    def __post_init__(self) -> None:
        if self.magnitude not in (0, 1):
            raise ValueError("magnitude must be 0 or 1")
        if self.sign not in (-1, 1):
            raise ValueError("sign must be -1 or +1")

    def scalar(self) -> float:
        if self.magnitude == 0:
            return math.copysign(0.0, float(self.sign))
        return float(self.sign * self.magnitude)

    def label(self) -> str:
        if self.magnitude == 0:
            return "-0" if self.sign < 0 else "+0"
        return "-1" if self.sign < 0 else "+1"


@dataclass(frozen=True)
class SignedDualPlane:
    a: SignedBit
    b: SignedBit

    def label(self) -> str:
        return f"({self.a.label()}a,{self.b.label()}b)"


@dataclass(frozen=True)
class TernaryDualPlane:
    a: int
    b: int

    def __post_init__(self) -> None:
        if self.a not in (-1, 0, 1) or self.b not in (-1, 0, 1):
            raise ValueError("ternary values must be -1, 0, or +1")

    def label(self) -> str:
        return f"({self.a}a,{self.b}b)"


def signed_states() -> List[SignedDualPlane]:
    # Stable ordering: -1, -0, +0, +1 on each plane.
    one_plane = [
        SignedBit(1, -1),
        SignedBit(0, -1),
        SignedBit(0, 1),
        SignedBit(1, 1),
    ]
    return [SignedDualPlane(a, b) for a, b in product(one_plane, repeat=2)]


def ternary_states() -> List[TernaryDualPlane]:
    return [TernaryDualPlane(a, b) for a, b in product((-1, 0, 1), repeat=2)]


def to_unit_interval_signed(bit: SignedBit, eps: float = 1e-3) -> float:
    """
    Map signed-binary state into (0,1), keeping +0 and -0 distinct.
    -1 -> 0
    -0 -> 0.5 - eps
    +0 -> 0.5 + eps
    +1 -> 1
    """
    if bit.magnitude == 0:
        return 0.5 + (eps if bit.sign > 0 else -eps)
    return (bit.scalar() + 1.0) / 2.0


def fibonacci_sphere(n: int) -> np.ndarray:
    """Deterministic spiral-distributed points on a unit sphere."""
    if n <= 0:
        raise ValueError("n must be positive")
    points = np.zeros((n, 3), dtype=float)
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(n):
        z = 1.0 - 2.0 * (i + 0.5) / n
        r = math.sqrt(max(0.0, 1.0 - z * z))
        theta = golden_angle * i
        points[i] = [r * math.cos(theta), r * math.sin(theta), z]
    return points


def rotation_matrix_xyz(ax: float, ay: float, az: float) -> np.ndarray:
    """3D rotation matrix from Euler angles (x,y,z)."""
    cx, sx = math.cos(ax), math.sin(ax)
    cy, sy = math.cos(ay), math.sin(ay)
    cz, sz = math.cos(az), math.sin(az)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]], dtype=float)
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], dtype=float)
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]], dtype=float)
    return rz @ ry @ rx


def signed_local_vector(symbol: SignedDualPlane, eps: float) -> np.ndarray:
    # Re-center to [-1,1] and encode signed-zero direction as a third axis.
    a = 2.0 * to_unit_interval_signed(symbol.a, eps=eps) - 1.0
    b = 2.0 * to_unit_interval_signed(symbol.b, eps=eps) - 1.0
    z = 0.0
    if symbol.a.magnitude == 0:
        z += 0.5 * symbol.a.sign
    if symbol.b.magnitude == 0:
        z += 0.5 * symbol.b.sign
    return np.array([a, b, z], dtype=float)


def ternary_local_vector(symbol: TernaryDualPlane) -> np.ndarray:
    return np.array([float(symbol.a), float(symbol.b), 0.0], dtype=float)


def build_signed_codebook(
    angles: Tuple[float, float, float] = (0.35, 0.2, 0.55),
    local_scale: float = 0.18,
    zero_eps: float = 1e-3,
) -> Dict[SignedDualPlane, np.ndarray]:
    states = signed_states()
    anchors = fibonacci_sphere(len(states))
    rot = rotation_matrix_xyz(*angles)
    codebook: Dict[SignedDualPlane, np.ndarray] = {}
    for i, state in enumerate(states):
        local = rot @ signed_local_vector(state, eps=zero_eps)
        codebook[state] = anchors[i] + local_scale * local
    return codebook


def build_ternary_codebook(
    angles: Tuple[float, float, float] = (0.2, 0.5, 0.1),
    local_scale: float = 0.2,
) -> Dict[TernaryDualPlane, np.ndarray]:
    states = ternary_states()
    anchors = fibonacci_sphere(len(states))
    rot = rotation_matrix_xyz(*angles)
    codebook: Dict[TernaryDualPlane, np.ndarray] = {}
    for i, state in enumerate(states):
        local = rot @ ternary_local_vector(state)
        codebook[state] = anchors[i] + local_scale * local
    return codebook


def decode_nearest(point: np.ndarray, codebook: Dict[object, np.ndarray]) -> object:
    best_state = None
    best_dist = float("inf")
    for state, vec in codebook.items():
        dist = float(np.linalg.norm(point - vec))
        if dist < best_dist:
            best_dist = dist
            best_state = state
    return best_state


def min_pairwise_distance(codebook: Dict[object, np.ndarray]) -> float:
    points = list(codebook.values())
    min_d = float("inf")
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            min_d = min(min_d, float(np.linalg.norm(points[i] - points[j])))
    return min_d


def capacity_bits(num_states: int) -> float:
    return math.log2(float(num_states))


def roundtrip_accuracy(
    codebook: Dict[object, np.ndarray],
    noise_std: float,
    seed: int = 42,
) -> float:
    rng = np.random.default_rng(seed)
    total = 0
    good = 0
    for state, vec in codebook.items():
        noisy = vec + rng.normal(0.0, noise_std, size=vec.shape)
        pred = decode_nearest(noisy, codebook)
        total += 1
        if pred == state:
            good += 1
    return good / max(total, 1)


def print_system_table() -> None:
    binary_states = 4  # two standard bits
    ternary_states_n = 9  # (-1,0,1)^2
    signed_states_n = 16  # (+/-0, +/-1)^2

    print("System capacity comparison (2-plane symbols)")
    print("  binary(0/1)^2         states=%2d  bits=%.3f" % (binary_states, capacity_bits(binary_states)))
    print("  ternary(-1/0/1)^2     states=%2d  bits=%.3f" % (ternary_states_n, capacity_bits(ternary_states_n)))
    print("  signed(+/-0,+/-1)^2   states=%2d  bits=%.3f" % (signed_states_n, capacity_bits(signed_states_n)))


def run_demo(noise_std: float = 0.04) -> None:
    signed = build_signed_codebook()
    ternary = build_ternary_codebook()

    print_system_table()
    print()

    signed_min = min_pairwise_distance(signed)
    ternary_min = min_pairwise_distance(ternary)
    print("Codebook separation")
    print(f"  signed   min pairwise distance: {signed_min:.4f}")
    print(f"  ternary  min pairwise distance: {ternary_min:.4f}")

    signed_acc = roundtrip_accuracy(signed, noise_std=noise_std, seed=7)
    ternary_acc = roundtrip_accuracy(ternary, noise_std=noise_std, seed=7)
    print()
    print(f"Round-trip nearest decode accuracy (noise_std={noise_std:.3f})")
    print(f"  signed:  {signed_acc:.3f}")
    print(f"  ternary: {ternary_acc:.3f}")

    # Show a few concrete encodings for inspection.
    print()
    print("Sample signed symbols")
    for i, state in enumerate(signed_states()[:6]):
        vec = signed[state]
        print(f"  {i:02d} {state.label():>14} -> [{vec[0]: .3f}, {vec[1]: .3f}, {vec[2]: .3f}]")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Signed multi-plane encoding demo")
    parser.add_argument(
        "--noise-std",
        type=float,
        default=0.04,
        help="Gaussian noise std used for round-trip decode test",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    run_demo(noise_std=args.noise_std)


if __name__ == "__main__":
    main()
