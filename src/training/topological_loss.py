"""Topological loss primitives used by SCBE training loops.

This module is intentionally pure-numpy and deterministic: it is used by unit tests and
as a lightweight stand-in for a future torch/JAX implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import math

import numpy as np

PHI: float = (1.0 + math.sqrt(5.0)) / 2.0
PHI_INV: float = 1.0 / PHI


def tetrahedral_generators_A4() -> List[np.ndarray]:
    """Return two 4x4 permutation generators for the alternating group A4."""

    g1 = np.zeros((4, 4), dtype=float)
    perm1 = [1, 2, 0, 3]  # (0 1 2)
    for i, j in enumerate(perm1):
        g1[i, j] = 1.0

    g2 = np.zeros((4, 4), dtype=float)
    perm2 = [2, 1, 3, 0]  # (0 2 3)
    for i, j in enumerate(perm2):
        g2[i, j] = 1.0

    return [g1, g2]


def _rotation_matrix(axis: np.ndarray, angle: float) -> np.ndarray:
    axis = np.asarray(axis, dtype=float)
    norm = float(np.linalg.norm(axis))
    if norm == 0:
        raise ValueError("axis must be non-zero")
    axis = axis / norm
    x, y, z = axis
    c = math.cos(angle)
    s = math.sin(angle)
    C = 1.0 - c
    return np.array(
        [
            [c + x * x * C, x * y * C - z * s, x * z * C + y * s],
            [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
            [z * x * C - y * s, z * y * C + x * s, c + z * z * C],
        ],
        dtype=float,
    )


def octahedral_generators_S4() -> List[np.ndarray]:
    """Return two 3x3 rotation generators that generate the octahedral group (isomorphic to S4)."""

    r1 = _rotation_matrix(np.array([1.0, 0.0, 0.0]), math.pi / 2.0)
    r2 = _rotation_matrix(np.array([0.0, 1.0, 0.0]), math.pi / 2.0)
    return [r1, r2]


def icosahedral_generators_A5() -> List[np.ndarray]:
    """Return two 3x3 rotation generators for the icosahedral group (isomorphic to A5)."""

    r_z_72 = _rotation_matrix(np.array([0.0, 0.0, 1.0]), 2.0 * math.pi / 5.0)
    r_diag_120 = _rotation_matrix(np.array([1.0, 1.0, 1.0]), 2.0 * math.pi / 3.0)
    return [r_z_72, r_diag_120]


SYMMETRY_GENERATORS: Dict[str, Callable[[], List[np.ndarray]]] = {
    "A4": tetrahedral_generators_A4,
    "S4": octahedral_generators_S4,
    "A5": icosahedral_generators_A5,
}


_PHDM_POLYHEDRA: List[Dict[str, float]] = [
    {"name": "tetrahedron", "faces": 4, "edges": 6, "vertices": 4, "euler_chi": 2, "depth": 0.05},
    {"name": "cube", "faces": 6, "edges": 12, "vertices": 8, "euler_chi": 2, "depth": 0.08},
    {"name": "octahedron", "faces": 8, "edges": 12, "vertices": 6, "euler_chi": 2, "depth": 0.10},
    {"name": "dodecahedron", "faces": 12, "edges": 30, "vertices": 20, "euler_chi": 2, "depth": 0.12},
    {"name": "icosahedron", "faces": 20, "edges": 30, "vertices": 12, "euler_chi": 2, "depth": 0.15},
    {"name": "cuboctahedron", "faces": 14, "edges": 24, "vertices": 12, "euler_chi": 2, "depth": 0.18},
    {"name": "icosidodecahedron", "faces": 32, "edges": 60, "vertices": 30, "euler_chi": 2, "depth": 0.22},
    {"name": "truncated_tetrahedron", "faces": 8, "edges": 18, "vertices": 12, "euler_chi": 2, "depth": 0.25},
    {"name": "truncated_cube", "faces": 14, "edges": 36, "vertices": 24, "euler_chi": 2, "depth": 0.28},
    {"name": "truncated_octahedron", "faces": 14, "edges": 36, "vertices": 24, "euler_chi": 2, "depth": 0.30},
    {"name": "toroidal_7_21_14", "faces": 14, "edges": 21, "vertices": 7, "euler_chi": 0, "depth": 0.33},
    {"name": "toroidal_9_27_18", "faces": 18, "edges": 27, "vertices": 9, "euler_chi": 0, "depth": 0.36},
    {"name": "toroidal_12_36_24", "faces": 24, "edges": 36, "vertices": 12, "euler_chi": 0, "depth": 0.40},
    {"name": "toroidal_16_48_32", "faces": 32, "edges": 48, "vertices": 16, "euler_chi": 0, "depth": 0.44},
    {"name": "toroidal_20_60_40", "faces": 40, "edges": 60, "vertices": 20, "euler_chi": 0, "depth": 0.48},
    {"name": "toroidal_24_72_48", "faces": 48, "edges": 72, "vertices": 24, "euler_chi": 0, "depth": 0.52},
]


_FLOW_ADJACENCY: Dict[int, List[int]] = {
    0: [1, 2],
    1: [0, 3],
    2: [0, 3, 4],
    3: [1, 2, 5],
    4: [2, 6],
    5: [3, 7],
    6: [4, 8],
    7: [5, 9],
    8: [6, 10],
    9: [7, 11],
    10: [8, 12],
    11: [9, 13],
    12: [10, 14],
    13: [11, 15],
    14: [12, 15],
    15: [13, 14],
}


def _natural_frequency(poly: Dict[str, float]) -> float:
    faces = float(poly["faces"])
    edges = float(poly["edges"])
    vertices = float(poly["vertices"])
    euler = float(poly.get("euler_chi", vertices - edges + faces))
    depth = float(poly.get("depth", 0.0))

    euler_term = abs(euler) + 1.0
    return (faces + 0.5 * edges + 0.25 * vertices) / euler_term + (1.0 + depth) * PHI_INV


@dataclass(frozen=True)
class FrictionLaplacian:
    matrix: np.ndarray

    @property
    def n_nodes(self) -> int:
        return int(self.matrix.shape[0])

    @property
    def n_edges(self) -> int:
        off = self.matrix.copy()
        np.fill_diagonal(off, 0.0)
        return int(np.sum(off < 0) // 2)

    @property
    def total_friction(self) -> float:
        return float(np.trace(self.matrix))

    @property
    def fiedler_value(self) -> float:
        vals = np.linalg.eigvalsh(self.matrix)
        vals = np.sort(np.real(vals))
        if len(vals) < 2:
            return 0.0
        return float(max(vals[1], 0.0))


def build_default_friction_laplacian() -> FrictionLaplacian:
    n = 16
    freqs = [_natural_frequency(p) for p in _PHDM_POLYHEDRA]

    W = np.zeros((n, n), dtype=float)
    for i, neighbors in _FLOW_ADJACENCY.items():
        for j in neighbors:
            if i == j:
                continue
            w = 1.0 / (1.0 + abs(freqs[i] - freqs[j]))
            W[i, j] = max(W[i, j], w)
            W[j, i] = max(W[j, i], w)

    D = np.diag(W.sum(axis=1))
    L = D - W

    # Symmetric normalization: D^{-1/2} L D^{-1/2}
    d = np.diag(D).copy()
    with np.errstate(divide="ignore"):
        inv_sqrt = 1.0 / np.sqrt(np.maximum(d, 1e-12))
    S = np.diag(inv_sqrt)
    L = S @ L @ S

    L = 0.5 * (L + L.T)
    return FrictionLaplacian(matrix=L)


@dataclass(frozen=True)
class TopologicalLossConfig:
    gamma: float = 1.0
    lambda_torsion: float = 0.1
    phi: float = PHI
    normalize_laplacian: bool = True


class TopologicalLoss:
    def __init__(self, config: Optional[TopologicalLossConfig] = None):
        self.config = config or TopologicalLossConfig()
        self.laplacian = build_default_friction_laplacian()

    def internalization_penalty(self, h_predicted: float, h_true: float) -> float:
        diff = float(h_true) - float(h_predicted)
        return float(self.config.gamma * (diff * diff))

    def torsional_penalty(self, W: Optional[np.ndarray]) -> float:
        if W is None:
            return 0.0

        W_arr = np.asarray(W, dtype=float)
        if W_arr.ndim == 1:
            W_arr = W_arr.reshape((-1, 1))

        n = self.laplacian.n_nodes
        if W_arr.shape[0] < n:
            pad = np.zeros((n - W_arr.shape[0], W_arr.shape[1]), dtype=float)
            W_arr = np.vstack([W_arr, pad])
        elif W_arr.shape[0] > n:
            W_arr = W_arr[:n, :]

        q = float(np.trace(W_arr.T @ self.laplacian.matrix @ W_arr)) / float(max(n, 1))
        return float(self.config.lambda_torsion * max(q, 0.0))

    def compute(
        self,
        *,
        l_task: float,
        h_predicted: float,
        h_true: float,
        W: Optional[np.ndarray],
    ) -> Dict[str, float]:
        l_task_f = float(l_task)
        l_int = self.internalization_penalty(h_predicted, h_true)
        l_tors = self.torsional_penalty(W)
        l_total = l_task_f + l_int + l_tors
        return {
            "l_total": float(l_total),
            "l_task": float(l_task_f),
            "l_internalization": float(l_int),
            "l_torsion": float(l_tors),
        }

    def generator_alignment_loss(self, W: np.ndarray, group: str) -> float:
        group = str(group)
        if group not in SYMMETRY_GENERATORS:
            return 0.0
        gens = SYMMETRY_GENERATORS[group]()
        W_arr = np.asarray(W, dtype=float)
        dists = [float(np.linalg.norm(W_arr - g)) for g in gens]
        return float(min(dists))


def topological_training_step(
    *,
    task_loss: float,
    h_predicted: float,
    polyhedral_distances: Dict[str, float],
    phase_deviation: float,
    weight_matrix: Optional[np.ndarray] = None,
    config: Optional[TopologicalLossConfig] = None,
) -> Dict[str, float | str]:
    cfg = config or TopologicalLossConfig()
    loss = TopologicalLoss(config=cfg)

    distances = [float(v) for v in polyhedral_distances.values()] or [0.0]
    mean_dist = float(sum(distances) / len(distances))

    h_true = math.exp(-cfg.phi * mean_dist) * math.exp(-abs(float(phase_deviation)) / 10.0)
    h_true = float(max(min(h_true, 1.0), 1e-12))

    breakdown = loss.compute(l_task=task_loss, h_predicted=h_predicted, h_true=h_true, W=weight_matrix)
    tier = "ALLOW" if h_true >= 0.75 else ("DENY" if h_true < 0.15 else "QUARANTINE")

    return {
        **breakdown,
        "tier": tier,
        "h_true": float(h_true),
        "gamma": float(cfg.gamma),
    }
