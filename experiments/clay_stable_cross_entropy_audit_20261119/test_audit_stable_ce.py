import torch
import torch.nn.functional as F

from audit_stable_ce import stable_hard_target_cross_entropy


def _loss_and_gradient(loss_function, values):
    logits = torch.tensor([values], dtype=torch.float32, requires_grad=True)
    targets = torch.tensor([0])
    loss = loss_function(logits, targets)
    gradient = torch.autograd.grad(loss.sum(), logits)[0]
    return loss.detach(), gradient.detach()


def test_paper_float32_collapse_control() -> None:
    standard_loss, standard_gradient = _loss_and_gradient(
        lambda z, t: F.cross_entropy(z, t, reduction="none"),
        [9.0, -9.0, -9.0],
    )
    fixed_loss, fixed_gradient = _loss_and_gradient(
        lambda z, t: stable_hard_target_cross_entropy(z, t, reduction="none"),
        [9.0, -9.0, -9.0],
    )
    assert standard_loss.item() == 0.0
    assert standard_gradient[0, 0].item() == 0.0
    assert fixed_loss.item() > 0.0
    assert fixed_gradient[0, 0].item() < 0.0
    assert fixed_gradient.sum().item() == 0.0
    assert standard_gradient.sum().item() > 0.0


def test_ordinary_margin_matches_standard() -> None:
    logits = torch.tensor(
        [[2.0, 1.0, 0.0], [-1.0, 0.5, 3.0]], dtype=torch.float64
    )
    targets = torch.tensor([0, 2])
    standard = F.cross_entropy(logits, targets, reduction="none")
    fixed = stable_hard_target_cross_entropy(logits, targets, reduction="none")
    torch.testing.assert_close(fixed, standard, atol=1e-15, rtol=1e-15)


def test_reductions_and_shape_guard() -> None:
    logits = torch.tensor([[2.0, 1.0, 0.0]], dtype=torch.float32)
    targets = torch.tensor([0])
    losses = stable_hard_target_cross_entropy(logits, targets, reduction="none")
    assert torch.equal(
        stable_hard_target_cross_entropy(logits, targets, reduction="sum"),
        losses.sum(),
    )
    assert torch.equal(
        stable_hard_target_cross_entropy(logits, targets, reduction="mean"),
        losses.mean(),
    )
