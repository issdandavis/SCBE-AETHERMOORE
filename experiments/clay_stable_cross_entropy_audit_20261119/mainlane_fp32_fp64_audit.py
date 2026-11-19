"""Compare float32 hard-target CE implementations against float64 ground truth.

This is a numerical-fidelity audit, not a training-efficacy measurement.  It
uses a deterministic sweep from unsaturated through deeply saturated margins
and reports loss and gradient errors for unchanged PyTorch cross entropy and
the opt-in stable-log1p implementation.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import torch

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from python.scbe.clay_stable_cross_entropy import stable_hard_target_cross_entropy


SEED = 261_031_642
EXAMPLES = 4_096
CLASSES = 257


def _audit(
    *,
    mode: str,
    logits64: torch.Tensor,
    targets: torch.Tensor,
    reference_loss: torch.Tensor,
    reference_gradient: torch.Tensor,
) -> dict[str, object]:
    logits32 = logits64.detach().float().requires_grad_(True)
    if mode == "standard":
        losses = torch.nn.functional.cross_entropy(logits32, targets, reduction="none")
    elif mode == "stable_log1p":
        losses = stable_hard_target_cross_entropy(logits32, targets, reduction="none")
    else:
        raise ValueError(f"unsupported mode: {mode}")

    gradient = torch.autograd.grad(losses.sum(), logits32)[0].double()
    detached_losses = losses.detach().double()
    detached_gradient = gradient.detach()
    loss_error = (detached_losses - reference_loss).abs()
    target_error = (detached_gradient[:, 0] - reference_gradient[:, 0]).abs()
    non_target_error = (detached_gradient[:, 1:] - reference_gradient[:, 1:]).abs()
    return {
        "zero_loss_count": int((detached_losses == 0).sum()),
        "zero_target_gradient_count": int((detached_gradient[:, 0] == 0).sum()),
        "loss_max_abs_error": float(loss_error.max()),
        "loss_mean_abs_error": float(loss_error.mean()),
        "target_grad_max_abs_error": float(target_error.max()),
        "target_grad_mean_abs_error": float(target_error.mean()),
        "all_non_target_grad_max_abs_error": float(non_target_error.max()),
        "finite": bool(torch.isfinite(detached_losses).all() and torch.isfinite(detached_gradient).all()),
    }


def run() -> dict[str, object]:
    torch.manual_seed(SEED)
    targets = torch.zeros(EXAMPLES, dtype=torch.long)
    margins = torch.linspace(0.0, 80.0, EXAMPLES, dtype=torch.float64)
    noise = torch.rand((EXAMPLES, CLASSES - 1), dtype=torch.float64) * 12.0
    logits64 = torch.cat(
        [
            torch.zeros((EXAMPLES, 1), dtype=torch.float64),
            -(margins[:, None] + noise),
        ],
        dim=1,
    ).requires_grad_(True)
    reference_loss_live = torch.logsumexp(logits64, dim=-1) - logits64[:, 0]
    reference_gradient_live = torch.autograd.grad(reference_loss_live.sum(), logits64)[0]
    reference_loss = reference_loss_live.detach()
    reference_gradient = reference_gradient_live.detach()

    return {
        "schema": "mainlane.stable-ce-fp32-vs-fp64-audit.v1",
        "seed": SEED,
        "examples": EXAMPLES,
        "classes": CLASSES,
        "margin_range": [0.0, 80.0],
        "standard": _audit(
            mode="standard",
            logits64=logits64,
            targets=targets,
            reference_loss=reference_loss,
            reference_gradient=reference_gradient,
        ),
        "stable_log1p": _audit(
            mode="stable_log1p",
            logits64=logits64,
            targets=targets,
            reference_loss=reference_loss,
            reference_gradient=reference_gradient,
        ),
        "claim_boundary": "Numerical fidelity only; this does not establish improved training efficacy.",
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
