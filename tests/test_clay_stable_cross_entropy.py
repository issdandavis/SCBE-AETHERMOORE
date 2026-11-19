from __future__ import annotations

import pytest
import torch
import torch.nn.functional as F

from python.scbe.clay_stable_cross_entropy import (
    STABLE_LOG1P,
    hard_target_cross_entropy,
    stable_hard_target_cross_entropy,
)


def test_paper_float32_control_recovers_target_gradient_and_conservation() -> None:
    standard_logits = torch.tensor([[9.0, -9.0, -9.0]], dtype=torch.float32, requires_grad=True)
    targets = torch.tensor([0])
    standard_loss = F.cross_entropy(standard_logits, targets)
    standard_gradient = torch.autograd.grad(standard_loss, standard_logits)[0]

    stable_logits = standard_logits.detach().clone().requires_grad_(True)
    stable_loss = stable_hard_target_cross_entropy(stable_logits, targets)
    stable_gradient = torch.autograd.grad(stable_loss, stable_logits)[0]

    assert standard_loss.item() == 0.0
    assert standard_gradient[0, 0].item() == 0.0
    assert standard_gradient.sum().item() != 0.0
    assert stable_loss.item() == pytest.approx(3.045996e-8, rel=1e-6)
    assert stable_gradient[0, 0].item() == pytest.approx(-3.045996e-8, rel=1e-6)
    assert stable_gradient.sum().item() == 0.0


def test_default_dispatch_is_exactly_unchanged_pytorch_cross_entropy() -> None:
    logits = torch.tensor([[0.25, -0.5, 1.75], [-2.0, 0.5, 0.25]], dtype=torch.float32)
    targets = torch.tensor([2, 1])

    expected = F.cross_entropy(logits, targets, reduction="none")
    actual = hard_target_cross_entropy(logits, targets, reduction="none")

    assert torch.equal(actual, expected)


def test_stable_mode_matches_float64_reference_at_ordinary_margins() -> None:
    logits = torch.tensor([[0.25, -0.5, 1.75], [-2.0, 0.5, 0.25]], dtype=torch.float64)
    targets = torch.tensor([2, 1])

    expected = F.cross_entropy(logits, targets, reduction="none")
    actual = hard_target_cross_entropy(
        logits,
        targets,
        reduction="none",
        mode=STABLE_LOG1P,
    )

    assert torch.allclose(actual, expected, rtol=1e-15, atol=1e-15)


def test_unknown_mode_fails_closed() -> None:
    logits = torch.zeros((1, 2), dtype=torch.float32)
    targets = torch.tensor([0])

    with pytest.raises(ValueError, match="unsupported"):
        hard_target_cross_entropy(logits, targets, mode="automatic")
