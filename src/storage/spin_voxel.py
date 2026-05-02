"""Spin-voxel research primitives for MAZE storage experiments.

This module stays in storage/ as an experimental adapter layer and is not wired
into production routing by default.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal


SpinVector = tuple[float, float, float]
TPhase = Literal["fast", "memory", "governance", "day", "night", "set"]


@dataclass(frozen=True)
class SpinVoxelConfig:
    exchange_j: float = 0.5
    external_field: SpinVector = (0.0, 0.0, 0.1)
    alpha: float = 0.2
    spin_reference: float = 1.0
    phi: float = (1.0 + math.sqrt(5.0)) / 2.0
    epsilon: float = 1e-9


def _dot(a: SpinVector, b: SpinVector) -> float:
    return (a[0] * b[0]) + (a[1] * b[1]) + (a[2] * b[2])


def _norm(v: SpinVector) -> float:
    return math.sqrt(_dot(v, v))


def normalize_spin(v: SpinVector, epsilon: float = 1e-9) -> SpinVector:
    n = _norm(v)
    if n <= epsilon:
        return (0.0, 0.0, 0.0)
    return (v[0] / n, v[1] / n, v[2] / n)


def build_ring_edges(count: int) -> list[tuple[int, int]]:
    if count < 2:
        return []
    edges: list[tuple[int, int]] = []
    for i in range(count):
        j = (i + 1) % count
        if i < j:
            edges.append((i, j))
        else:
            edges.append((j, i))
    return sorted(set(edges))


def spin_coherence(spins: list[SpinVector], epsilon: float = 1e-9) -> float:
    if not spins:
        return 0.0
    sx = sum(v[0] for v in spins)
    sy = sum(v[1] for v in spins)
    sz = sum(v[2] for v in spins)
    numerator = math.sqrt((sx * sx) + (sy * sy) + (sz * sz))
    denominator = sum(_norm(v) for v in spins) + epsilon
    return numerator / denominator


def spin_hamiltonian(
    spins: list[SpinVector],
    *,
    edges: list[tuple[int, int]] | None = None,
    config: SpinVoxelConfig | None = None,
) -> float:
    cfg = config or SpinVoxelConfig()
    if not spins:
        return 0.0
    if edges is None:
        edges = build_ring_edges(len(spins))
    exchange = 0.0
    for i, j in edges:
        exchange += _dot(spins[i], spins[j])
    exchange_term = -cfg.exchange_j * exchange
    field_term = -sum(_dot(cfg.external_field, spin) for spin in spins)
    return exchange_term + field_term


def spin_disorder(
    spins: list[SpinVector], *, edges: list[tuple[int, int]] | None = None, epsilon: float = 1e-9
) -> float:
    if not spins:
        return 0.0
    if edges is None:
        edges = build_ring_edges(len(spins))
    if not edges:
        return 0.0
    disagreement = 0.0
    for i, j in edges:
        disagreement += 1.0 - _dot(normalize_spin(spins[i]), normalize_spin(spins[j]))
    return disagreement / (len(edges) + epsilon)


def phason_rotation_matrix(
    *, n: int = 1, phi: float = (1.0 + math.sqrt(5.0)) / 2.0
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    phase_n = max(1, int(n))
    theta = (2.0 * math.pi) / (phi**phase_n)
    c = math.cos(theta)
    s = math.sin(theta)
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def rotate_spin(
    spin: SpinVector, matrix: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]
) -> SpinVector:
    x = (matrix[0][0] * spin[0]) + (matrix[0][1] * spin[1]) + (matrix[0][2] * spin[2])
    y = (matrix[1][0] * spin[0]) + (matrix[1][1] * spin[1]) + (matrix[1][2] * spin[2])
    z = (matrix[2][0] * spin[0]) + (matrix[2][1] * spin[1]) + (matrix[2][2] * spin[2])
    return (x, y, z)


def apply_phason(spins: list[SpinVector], *, n: int = 1, config: SpinVoxelConfig | None = None) -> list[SpinVector]:
    cfg = config or SpinVoxelConfig()
    matrix = phason_rotation_matrix(n=n, phi=cfg.phi)
    return [rotate_spin(spin, matrix) for spin in spins]


def t_phase_factor(phase: TPhase) -> float:
    factors: dict[TPhase, float] = {
        "fast": 1.0,
        "memory": 4.0,
        "governance": 12.0,
        "day": 0.85,
        "night": 1.15,
        "set": 8.0,
    }
    return factors[phase]


def harmonic_scaling_spin_voxel(
    *,
    d: float,
    r: float,
    intent_norm: float,
    spins: list[SpinVector],
    phase: TPhase = "fast",
    edges: list[tuple[int, int]] | None = None,
    config: SpinVoxelConfig | None = None,
) -> float:
    cfg = config or SpinVoxelConfig()
    base = r ** (d**2)
    i_norm = max(intent_norm, cfg.epsilon)
    disorder = spin_disorder(spins, edges=edges, epsilon=cfg.epsilon)
    h_spin = spin_hamiltonian(spins, edges=edges, config=cfg)
    # Disorder drives penalty; Hamiltonian contributes soft stabilization signal.
    spin_penalty = max(0.0, disorder + (h_spin / max(cfg.spin_reference, cfg.epsilon)))
    return base * (t_phase_factor(phase) / i_norm) * (1.0 + (cfg.alpha * spin_penalty))
