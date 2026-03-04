from __future__ import annotations

import torch

from .mesh_graph import MeshOps, normalized_laplacian, row_stochastic

# 16 PHDM polyhedra grouped by governance zone.
CORE_LIMBIC = list(range(0, 5))
CORTEX = list(range(5, 8))
RISK = list(range(8, 10))
CEREBELLUM = list(range(10, 12))
CONNECTOME = list(range(12, 16))


def build_phdm_adjacency(device=None) -> torch.Tensor:
    """Build sparse adjacency for the canonical 16-node PHDM layout."""
    n = 16
    edges: set[tuple[int, int]] = set()

    zones = [CORE_LIMBIC, CORTEX, RISK, CEREBELLUM, CONNECTOME]
    for zone in zones:
        for i in zone:
            for j in zone:
                if i != j:
                    edges.add((i, j))

    # Connectome hubs bridge all non-connectome zones.
    for c in CONNECTOME:
        for other in range(n):
            if other not in CONNECTOME:
                edges.add((c, other))
                edges.add((other, c))

    # Core <-> Cortex direct escalation path.
    for i in CORE_LIMBIC:
        for j in CORTEX:
            edges.add((i, j))
            edges.add((j, i))

    # Cortex <-> Risk direct escalation path.
    for i in CORTEX:
        for j in RISK:
            edges.add((i, j))
            edges.add((j, i))

    rows, cols = zip(*sorted(edges))
    indices = torch.tensor([list(rows), list(cols)], dtype=torch.long, device=device)
    values = torch.ones(indices.shape[1], dtype=torch.float32, device=device)
    return torch.sparse_coo_tensor(indices, values, (n, n), device=device).coalesce()


def build_phdm_mesh_ops(device=None) -> MeshOps:
    """Build normalized adjacency + laplacian operators for PHDM graph."""
    a = build_phdm_adjacency(device=device)
    a_norm = row_stochastic(a)
    l_norm = normalized_laplacian(a_norm)
    return MeshOps(A_norm=a_norm, L_norm=l_norm, N=16)

