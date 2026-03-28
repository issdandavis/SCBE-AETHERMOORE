from __future__ import annotations

from dataclasses import dataclass
import torch


@dataclass
class TIEKB:
    """TIE knowledge base container."""

    kb: torch.Tensor  # (M, D_T)
    timestamps: torch.Tensor | None = None


def cosine_sim(a: torch.Tensor, b: torch.Tensor, eps: float = 1e-12) -> torch.Tensor:
    """Cosine similarity between vector a (D,) and rows of b (M,D)."""

    a_n = a / (a.norm() + eps)
    b_n = b / (b.norm(dim=1, keepdim=True) + eps)
    return b_n @ a_n


def retrieve_tie(
    tie_kb: TIEKB, q: torch.Tensor, top_k: int, temperature: float
) -> torch.Tensor:
    """Deterministic top-k retrieval with temperature-weighted average."""

    sims = cosine_sim(q, tie_kb.kb)
    k = min(int(top_k), sims.numel())
    vals, idx = torch.topk(sims, k=k, largest=True)
    w = torch.softmax(vals / max(float(temperature), 1e-6), dim=0)
    return (w.unsqueeze(1) * tie_kb.kb[idx]).sum(dim=0)
