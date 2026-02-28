"""
Symbiotic Network — Graph Laplacian Topology (Python reference).

Mirrors src/game/symbioticNetwork.ts.
Pure Python (no FAISS, no numpy for v1). Uses dict-based adjacency.

A4: Hodge dual pairs bond 30% stronger.
A5: Pipeline integrity via graph connectivity.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .types import (
    HODGE_DUAL_PAIRS,
    TONGUE_CODES,
    TongueCode,
    TongueVector,
    tongue_distance,
)


@dataclass(frozen=True)
class NetworkBonuses:
    xp_multiplier: float
    insight_bonus: float
    resilience: float
    governance_weight: float
    diversity_bonus: float
    algebraic_connectivity: float
    density: float


class SymbioticNetwork:
    """Weighted graph of companion bonds with Laplacian spectral analysis."""

    def __init__(self) -> None:
        self._nodes: Dict[str, TongueVector] = {}
        self._edges: Dict[str, Tuple[str, str, float, int]] = {}  # key → (src, tgt, weight, battles)
        self._adjacency: Dict[str, Set[str]] = {}

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def _edge_key(self, a: str, b: str) -> str:
        return f"{a}::{b}" if a < b else f"{b}::{a}"

    def _dominant_tongue(self, v: TongueVector) -> TongueCode:
        max_idx = 0
        for i in range(1, 6):
            if v[i] > v[max_idx]:
                max_idx = i
        return TONGUE_CODES[max_idx]

    def _is_hodge_dual(self, a: TongueVector, b: TongueVector) -> bool:
        dom_a = self._dominant_tongue(a)
        dom_b = self._dominant_tongue(b)
        return any(
            (dom_a == x and dom_b == y) or (dom_a == y and dom_b == x)
            for x, y in HODGE_DUAL_PAIRS
        )

    # -- Node ops --

    def add_companion(self, id: str, tongue_position: TongueVector) -> None:
        self._nodes[id] = tongue_position
        if id not in self._adjacency:
            self._adjacency[id] = set()

    def remove_companion(self, id: str) -> None:
        neighbors = self._adjacency.pop(id, set())
        for nb in neighbors:
            key = self._edge_key(id, nb)
            self._edges.pop(key, None)
            if nb in self._adjacency:
                self._adjacency[nb].discard(id)
        self._nodes.pop(id, None)

    # -- Edge ops --

    def add_bond(self, a_id: str, b_id: str, shared_battles: int = 0) -> None:
        if a_id not in self._nodes or b_id not in self._nodes:
            return

        dist = tongue_distance(self._nodes[a_id], self._nodes[b_id])
        weight = 1.0 / (1.0 + dist)

        if self._is_hodge_dual(self._nodes[a_id], self._nodes[b_id]):
            weight *= 1.3

        weight += math.log1p(shared_battles) * 0.1

        key = self._edge_key(a_id, b_id)
        self._edges[key] = (a_id, b_id, weight, shared_battles)
        self._adjacency[a_id].add(b_id)
        self._adjacency[b_id].add(a_id)

    # -- Laplacian --

    def compute_laplacian(self) -> Tuple[List[List[float]], List[str]]:
        node_order = sorted(self._nodes.keys())
        n = len(node_order)
        idx_map = {nid: i for i, nid in enumerate(node_order)}
        L = [[0.0] * n for _ in range(n)]

        for src, tgt, w, _ in self._edges.values():
            i, j = idx_map.get(src), idx_map.get(tgt)
            if i is None or j is None:
                continue
            L[i][j] = -w
            L[j][i] = -w
            L[i][i] += w
            L[j][j] += w

        return L, node_order

    def get_algebraic_connectivity(self) -> float:
        """λ₂ = second smallest eigenvalue of Laplacian."""
        if self.node_count < 2:
            return 0.0

        L, _ = self.compute_laplacian()
        eigenvalues = self._jacobi_eigenvalues(L)
        eigenvalues.sort()
        return max(0.0, eigenvalues[1]) if len(eigenvalues) > 1 else 0.0

    def _jacobi_eigenvalues(self, matrix: List[List[float]]) -> List[float]:
        """Jacobi eigenvalue algorithm for symmetric matrices."""
        n = len(matrix)
        if n == 0:
            return []
        if n == 1:
            return [matrix[0][0]]
        if n == 2:
            a, b = matrix[0][0], matrix[0][1]
            c, d = matrix[1][0], matrix[1][1]
            trace = a + d
            det = a * d - b * c
            disc = math.sqrt(max(0, trace * trace - 4 * det))
            return [(trace + disc) / 2, (trace - disc) / 2]

        A = [row[:] for row in matrix]
        max_iter = 100 * n * n
        eps = 1e-10

        for _ in range(max_iter):
            max_val, p, q = 0.0, 0, 1
            for i in range(n):
                for j in range(i + 1, n):
                    if abs(A[i][j]) > max_val:
                        max_val = abs(A[i][j])
                        p, q = i, j
            if max_val < eps:
                break

            if abs(A[p][p] - A[q][q]) < eps:
                theta = math.pi / 4
            else:
                theta = 0.5 * math.atan2(2 * A[p][q], A[p][p] - A[q][q])

            c = math.cos(theta)
            s = math.sin(theta)

            for i in range(n):
                if i != p and i != q:
                    aip, aiq = A[i][p], A[i][q]
                    A[i][p] = c * aip + s * aiq
                    A[p][i] = A[i][p]
                    A[i][q] = -s * aip + c * aiq
                    A[q][i] = A[i][q]

            app, aqq, apq = A[p][p], A[q][q], A[p][q]
            A[p][p] = c * c * app + 2 * s * c * apq + s * s * aqq
            A[q][q] = s * s * app - 2 * s * c * apq + c * c * aqq
            A[p][q] = 0.0
            A[q][p] = 0.0

        return [A[i][i] for i in range(n)]

    # -- Network bonuses --

    def compute_network_bonuses(self) -> NetworkBonuses:
        lambda2 = self.get_algebraic_connectivity()
        density = self._compute_density()
        total_bond = sum(w for _, _, w, _ in self._edges.values())
        unique_tongues = len({self._dominant_tongue(v) for v in self._nodes.values()})

        return NetworkBonuses(
            xp_multiplier=1 + lambda2 * 0.5,
            insight_bonus=density * 0.3,
            resilience=min(1.0, lambda2 * 0.2),
            governance_weight=min(2.0, total_bond * 0.1 + 1),
            diversity_bonus=unique_tongues / 6,
            algebraic_connectivity=lambda2,
            density=density,
        )

    def _compute_density(self) -> float:
        n = self.node_count
        if n < 2:
            return 0.0
        return self.edge_count / (n * (n - 1) / 2)

    # -- Artifact governance (L12 gate) --

    def submit_artifact(self, state: TongueVector, threshold: float = 5.0) -> str:
        """Layer 12 gate: reject if ds² > threshold."""
        if not self._nodes:
            return "approved"
        centroid = self._compute_centroid()
        ds2 = tongue_distance(state, centroid) ** 2
        return "approved" if ds2 <= threshold else "quarantined"

    def _compute_centroid(self) -> TongueVector:
        n = self.node_count
        if n == 0:
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        sums = [0.0] * 6
        for v in self._nodes.values():
            for i in range(6):
                sums[i] += v[i]
        return tuple(s / n for s in sums)  # type: ignore[return-value]
