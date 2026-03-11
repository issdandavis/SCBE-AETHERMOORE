"""
Multimodal Alignment Matrix
============================

Computes a trainable, differentiable alignment matrix A for M modalities.
The matrix captures pairwise cross-modal agreement (cosine similarity)
and optional per-modality reliability weights.

Integrates with SCBE governance: A feeds into the harmonic wall to
compute governance costs when modalities disagree.

@module multimodal/multimodal_matrix
@layer Layer 9-10 (Spectral + Spin Coherence)
@component MultiModal Matrix
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class MultiModalMatrix(nn.Module):
    """
    Computes a multimodal alignment matrix A for M modalities.

    Inputs:
        E: [B, M, D] modality embeddings (batch, modalities, dimension)

    Outputs:
        A: [B, M, M] pairwise cosine similarity matrix
        w: [B, M] learned reliability weights (optional, sigmoid-gated)
    """

    def __init__(self, d_model: int, use_reliability: bool = True):
        super().__init__()
        self.d_model = d_model
        self.use_reliability = use_reliability

        if use_reliability:
            self.reliability = nn.Sequential(
                nn.Linear(d_model, d_model),
                nn.GELU(),
                nn.Linear(d_model, 1),
            )

    def forward(self, E: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor | None]:
        # Normalize embeddings for cosine similarity
        En = F.normalize(E, dim=-1)  # [B, M, D]
        A = torch.einsum("bmd,bnd->bmn", En, En)  # [B, M, M]

        if not self.use_reliability:
            return A, None

        # Reliability weight per modality (sigmoid => 0..1)
        w = torch.sigmoid(self.reliability(E)).squeeze(-1)  # [B, M]
        return A, w

    def coherence(self, A: torch.Tensor) -> torch.Tensor:
        """
        Compute mean off-diagonal coherence — governance metric.

        Returns:
            Scalar tensor: mean agreement across modality pairs.
        """
        B, M, _ = A.shape
        mask = 1.0 - torch.eye(M, device=A.device).unsqueeze(0)
        off_diag = A * mask
        return off_diag.sum(dim=(-1, -2)) / (M * (M - 1))

    def drift(self, A: torch.Tensor) -> torch.Tensor:
        """
        Compute alignment drift — variance of off-diagonal terms.

        High drift signals inter-modal conflict (governance flag).
        """
        B, M, _ = A.shape
        mask = 1.0 - torch.eye(M, device=A.device).unsqueeze(0)
        off_diag = A * mask
        mean = off_diag.sum(dim=(-1, -2)) / (M * (M - 1))
        diff = (off_diag - mean.unsqueeze(-1).unsqueeze(-1)) * mask
        return (diff**2).sum(dim=(-1, -2)) / (M * (M - 1))
