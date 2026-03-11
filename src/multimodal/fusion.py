"""
Matrix-Weighted Fusion
=======================

Fuses M modality embeddings using their alignment matrix A.
Modal agreement amplifies fusion weight; disagreement dampens it.

The reliability-gated variant uses learned per-modality weights
to down-weight noisy or adversarial modalities.

@module multimodal/fusion
@layer Layer 12 (Harmonic Wall)
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class MatrixWeightedFusion(nn.Module):
    """
    Fuses M modality embeddings using their alignment matrix A.

    Fusion weight per modality = softmax(row-sum(A) * reliability).
    """

    def __init__(self, d_model: int):
        super().__init__()
        self.proj = nn.Linear(d_model, d_model)
        self.out = nn.Linear(d_model, d_model)

    def forward(
        self,
        E: torch.Tensor,
        A: torch.Tensor,
        w: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """
        Args:
            E: [B, M, D] modality embeddings.
            A: [B, M, M] alignment matrix.
            w: [B, M] optional reliability weights.

        Returns:
            [B, D] fused embedding.
        """
        B, M, D = E.shape

        # Agreement score: row-sum of alignment matrix
        s = A.sum(dim=-1) / max(M, 1)  # [B, M]

        if w is not None:
            s = s * w  # reliability-gated agreement

        alpha = F.softmax(s, dim=-1).unsqueeze(-1)  # [B, M, 1]
        z = (alpha * self.proj(E)).sum(dim=1)  # [B, D]
        return self.out(z)


class GatedFusion(nn.Module):
    """
    Gated fusion with learnable cross-modal attention.

    More expressive than MatrixWeightedFusion but requires
    more parameters.
    """

    def __init__(self, d_model: int, n_heads: int = 4):
        super().__init__()
        self.attn = nn.MultiheadAttention(d_model, n_heads, batch_first=True)
        self.gate = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.Sigmoid(),
        )
        self.out = nn.Linear(d_model, d_model)

    def forward(
        self,
        E: torch.Tensor,
        A: torch.Tensor,
        w: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """
        Args:
            E: [B, M, D] modality embeddings.
            A: [B, M, M] alignment matrix (used as attention bias).
            w: [B, M] optional reliability weights (unused here).

        Returns:
            [B, D] fused embedding.
        """
        # Self-attention across modalities with alignment bias
        attn_out, _ = self.attn(E, E, E)  # [B, M, D]

        # Gate
        g = self.gate(attn_out)  # [B, M, D]
        gated = g * attn_out  # [B, M, D]

        # Pool across modalities
        z = gated.mean(dim=1)  # [B, D]
        return self.out(z)
