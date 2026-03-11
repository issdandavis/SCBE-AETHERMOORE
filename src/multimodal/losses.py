"""
Multimodal Training Losses
============================

CLIP-style contrastive loss + conflict penalty + optional SCBE
governance term for the multimodal alignment system.

@module multimodal/losses
@layer Layer 12 (Harmonic Wall — cost scaling)
"""

from __future__ import annotations

import torch
import torch.nn.functional as F


def clip_contrastive_loss(
    z_a: torch.Tensor,
    z_b: torch.Tensor,
    temperature: float = 0.07,
) -> torch.Tensor:
    """
    Symmetric CLIP-style contrastive loss.

    Aligned pairs (same index) should have high similarity;
    non-aligned pairs should have low similarity.

    Args:
        z_a: [B, D] embeddings from modality A.
        z_b: [B, D] embeddings from modality B.
        temperature: Softmax temperature (default: 0.07).

    Returns:
        Scalar loss tensor.
    """
    z_a = F.normalize(z_a, dim=-1)
    z_b = F.normalize(z_b, dim=-1)
    logits = (z_a @ z_b.T) / temperature  # [B, B]
    labels = torch.arange(z_a.size(0), device=z_a.device)
    loss_ab = F.cross_entropy(logits, labels)
    loss_ba = F.cross_entropy(logits.T, labels)
    return (loss_ab + loss_ba) * 0.5


def conflict_penalty(
    A: torch.Tensor,
    margin: float = 0.0,
) -> torch.Tensor:
    """
    Penalize cross-modal disagreement in the alignment matrix.

    Only considers off-diagonal terms (cross-modal pairs).
    Values below the margin are penalized.

    Args:
        A: [B, M, M] alignment matrix.
        margin: Minimum acceptable similarity (default: 0.0).

    Returns:
        Scalar penalty tensor.
    """
    B, M, _ = A.shape
    mask = (1.0 - torch.eye(M, device=A.device)).unsqueeze(0)  # [1, M, M]
    off = A * mask
    return F.relu(margin - off).mean()


def harmonic_governance_loss(
    A: torch.Tensor,
    distance: torch.Tensor | None = None,
    phase_deviation: torch.Tensor | None = None,
) -> torch.Tensor:
    """
    SCBE governance term: penalize based on harmonic wall cost.

    H(d, pd) = 1 / (1 + d + 2 * pd)

    When modalities conflict (low coherence), the governance cost
    should increase exponentially.

    Args:
        A: [B, M, M] alignment matrix.
        distance: [B] optional hyperbolic distance from safe origin.
        phase_deviation: [B] optional breathing phase deviation.

    Returns:
        Scalar governance loss.
    """
    B, M, _ = A.shape
    mask = 1.0 - torch.eye(M, device=A.device).unsqueeze(0)
    off_diag = A * mask

    # Coherence = mean off-diagonal similarity
    coherence = off_diag.sum(dim=(-1, -2)) / (M * (M - 1))  # [B]

    # Map low coherence to high distance
    if distance is None:
        distance = 1.0 - coherence  # [B] low coherence → high distance

    if phase_deviation is None:
        phase_deviation = torch.zeros_like(distance)

    # Harmonic wall: H(d, pd) = 1 / (1 + d + 2*pd)
    h = 1.0 / (1.0 + distance + 2.0 * phase_deviation)

    # We want to minimize (1 - H), i.e., push towards safe operation
    return (1.0 - h).mean()


def combined_loss(
    z_text: torch.Tensor,
    z_image: torch.Tensor,
    A: torch.Tensor,
    contrastive_weight: float = 1.0,
    conflict_weight: float = 0.5,
    governance_weight: float = 0.1,
    temperature: float = 0.07,
    conflict_margin: float = 0.0,
) -> dict[str, torch.Tensor]:
    """
    Combined training loss: contrastive + conflict + governance.

    Returns a dict with individual losses and the total.
    """
    l_contrastive = clip_contrastive_loss(z_text, z_image, temperature)
    l_conflict = conflict_penalty(A, conflict_margin)
    l_governance = harmonic_governance_loss(A)

    total = (
        contrastive_weight * l_contrastive
        + conflict_weight * l_conflict
        + governance_weight * l_governance
    )

    return {
        "total": total,
        "contrastive": l_contrastive,
        "conflict": l_conflict,
        "governance": l_governance,
    }
