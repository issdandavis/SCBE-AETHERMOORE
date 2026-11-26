"""Opt-in numerically stable hard-target softmax cross entropy.

The stable formulation is Equation 6 from Barron, Gnanapragasam, and
Tschannen, "A Fix for Softmax and Cross-Entropy" (arXiv:2610.31642v3).
The standard mode deliberately delegates to PyTorch unchanged so existing
Clay campaigns remain byte-for-byte behavior compatible unless a caller opts
in explicitly.
"""

from __future__ import annotations

import torch
from torch import Tensor
import torch.nn.functional as F


STANDARD = "standard"
STABLE_LOG1P = "stable_log1p"
LOSS_MODES = frozenset((STANDARD, STABLE_LOG1P))


def stable_hard_target_cross_entropy(
    logits: Tensor,
    targets: Tensor,
    *,
    reduction: str = "mean",
) -> Tensor:
    """Compute hard-target CE without adding the target exponential early.

    Excluding the target term from the exponential sum avoids rounding a tiny
    non-target contribution away when it is added to one. Keeping the target
    slot constant-zero also makes autograd form the target derivative as the
    negative sum of the non-target derivatives.
    """

    if logits.ndim < 2 or targets.shape != logits.shape[:-1]:
        raise ValueError("targets must match every non-class logit dimension")
    if not logits.is_floating_point():
        raise TypeError("logits must use a floating dtype")
    if reduction not in {"none", "sum", "mean"}:
        raise ValueError(f"unsupported reduction: {reduction}")

    target_logits = logits.gather(-1, targets[..., None])
    is_target = F.one_hot(targets, logits.shape[-1]).to(dtype=torch.bool)
    shifted = torch.where(is_target, 0.0, logits - target_logits)
    offset = shifted.amax(dim=-1, keepdim=True)
    non_target_sum = torch.where(
        is_target,
        0.0,
        torch.exp(shifted - offset),
    ).sum(dim=-1)
    losses = offset[..., 0] + torch.log1p(
        non_target_sum + torch.expm1(-offset[..., 0])
    )

    if reduction == "none":
        return losses
    if reduction == "sum":
        return losses.sum()
    return losses.mean()


def hard_target_cross_entropy(
    logits: Tensor,
    targets: Tensor,
    *,
    reduction: str = "mean",
    mode: str = STANDARD,
) -> Tensor:
    """Dispatch to unchanged PyTorch CE or the opt-in stable formulation."""

    if mode == STANDARD:
        return F.cross_entropy(logits, targets, reduction=reduction)
    if mode == STABLE_LOG1P:
        return stable_hard_target_cross_entropy(
            logits,
            targets,
            reduction=reduction,
        )
    raise ValueError(f"unsupported hard-target cross-entropy mode: {mode}")
