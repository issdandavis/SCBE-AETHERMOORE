from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts" / "experiments" / "triadic_evidence_reasoning.py"
SPEC = importlib.util.spec_from_file_location("triadic_evidence_reasoning", SOURCE)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def test_softplus_roles_retain_signed_contribution() -> None:
    values = torch.linspace(-4.0, 4.0, 41)
    affirm = torch.nn.functional.softplus(M.ROLE_BETA * values) / M.ROLE_BETA
    counter = torch.nn.functional.softplus(-M.ROLE_BETA * values) / M.ROLE_BETA
    assert torch.allclose(affirm - counter, values, atol=1e-6)
    assert (torch.minimum(affirm, counter) > 0).all()


def test_omitted_axis_is_removed_from_both_roles() -> None:
    model = M.TriadicPerspectiveNet()
    core = torch.randn(2, M.BASE.CORE_DIM)
    omitted = torch.tensor([1, 4])
    _, receipt = model.decision(core, omitted)
    assert receipt["affirm"][0, 1] == 0
    assert receipt["counter"][0, 1] == 0
    assert receipt["affirm"][1, 4] == 0
    assert receipt["counter"][1, 4] == 0


def test_all_arms_have_identical_parameter_count() -> None:
    counts = [sum(p.numel() for p in M.TriadicPerspectiveNet().parameters()) for _ in M.ARMS]
    assert len(set(counts)) == 1


def test_reason_receipt_uses_disagreement_not_a_free_label() -> None:
    truth = torch.tensor([0, 1, 2, 1])
    stance = torch.tensor([0, 2, 1, 1])
    lens = torch.tensor([3, 4, 5, 2])
    reason = torch.where(stance != truth, lens, torch.full_like(lens, 6))
    assert reason.tolist() == [6, 4, 5, 6]


def test_one_update_is_finite() -> None:
    device = torch.device("cpu")
    M.BASE.configure_determinism(device)
    model, trace = M.train_arm(M.ARMS[0], 19, 1, device, trace_every=1)
    assert torch.isfinite(torch.tensor(trace[-1]["loss"]))
    assert all(torch.isfinite(parameter).all() for parameter in model.parameters())
