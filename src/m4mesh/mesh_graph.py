from __future__ import annotations

from dataclasses import dataclass
import torch


@dataclass(frozen=True)
class MeshOps:
    """Precomputed sparse operators for deterministic M4 propagation."""

    A_norm: torch.Tensor  # sparse COO (N, N)
    L_norm: torch.Tensor  # sparse COO (N, N)
    N: int


def grid_2d_adjacency(h: int, w: int, device=None) -> torch.Tensor:
    """Create 4-neighborhood sparse adjacency for an h x w grid."""

    rows = []
    cols = []

    def idx(r: int, c: int) -> int:
        return r * w + c

    for r in range(h):
        for c in range(w):
            v = idx(r, c)
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < h and 0 <= cc < w:
                    u = idx(rr, cc)
                    rows.append(v)
                    cols.append(u)

    n = h * w
    indices = torch.tensor([rows, cols], dtype=torch.long, device=device)
    values = torch.ones(indices.shape[1], dtype=torch.float32, device=device)
    return torch.sparse_coo_tensor(indices, values, (n, n)).coalesce()


def row_stochastic(a: torch.Tensor, eps: float = 1e-12) -> torch.Tensor:
    """Convert sparse adjacency to row-stochastic sparse matrix."""

    a = a.coalesce()
    deg = torch.sparse.sum(a, dim=1).to_dense().clamp_min(eps)
    idx = a.indices()
    vals = a.values() / deg[idx[0]]
    return torch.sparse_coo_tensor(idx, vals, a.shape, device=a.device).coalesce()


def normalized_laplacian(a_row: torch.Tensor) -> torch.Tensor:
    """L = I - A_row using sparse COO tensors."""

    n = a_row.shape[0]
    eye_idx = torch.arange(n, device=a_row.device)
    eye = torch.sparse_coo_tensor(
        torch.stack([eye_idx, eye_idx]),
        torch.ones(n, dtype=a_row.dtype, device=a_row.device),
        (n, n),
        device=a_row.device,
    ).coalesce()
    return (eye - a_row).coalesce()


def build_mesh_ops_grid2d(h: int, w: int, device=None) -> MeshOps:
    """Build normalized adjacency + laplacian once (no graph ops in forward)."""

    a = grid_2d_adjacency(h, w, device=device)
    a_norm = row_stochastic(a)
    l_norm = normalized_laplacian(a_norm)
    return MeshOps(A_norm=a_norm, L_norm=l_norm, N=h * w)
