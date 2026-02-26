from __future__ import annotations

import torch

from .wave import sparse_mm


def smear(u: torch.Tensor, A_norm: torch.Tensor, betas: list[float], J: int) -> torch.Tensor:
    """SMEAR(u) = sum_{j=0..J} beta_j * A^j u."""

    j_max = int(J)
    if len(betas) != j_max + 1:
        raise ValueError("betas must have length J+1")

    out = float(betas[0]) * u
    aj_u = u
    for j in range(1, j_max + 1):
        aj_u = sparse_mm(A_norm, aj_u)
        out = out + float(betas[j]) * aj_u
    return out
