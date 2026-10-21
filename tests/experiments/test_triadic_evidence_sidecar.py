from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts" / "experiments" / "triadic_evidence_sidecar.py"
SPEC = importlib.util.spec_from_file_location("triadic_evidence_sidecar", SOURCE)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def expected_coordinates() -> torch.Tensor:
    return torch.tensor(
        [M.BASE.signed_bits(state) for state in range(M.BASE.N_STATES)], dtype=torch.float32
    )


def test_aligned_and_ordinary_sidecars_are_exact() -> None:
    for mode in ("aligned", "ordinary"):
        coordinates, agreement = M.coordinate_sidecar(M.BASE.build_features(mode))
        assert torch.equal(coordinates, expected_coordinates())
        assert torch.equal(agreement, torch.ones_like(agreement))


def test_shuffled_sidecar_exposes_disagreement() -> None:
    _, agreement = M.coordinate_sidecar(M.BASE.build_features("shuffled"))
    assert float(agreement.mean()) < 1.0


def test_semantic_loss_does_not_reach_route_core() -> None:
    model = M.SidecarTriadicNet()
    features = M.BASE.build_features("aligned")
    sidecar, _ = M.coordinate_sidecar(features)
    logits, _ = model.decide_coordinates(sidecar)
    logits.sum().backward()
    assert model.axis_scale.grad is not None
    assert all(parameter.grad is None for parameter in model.encoder.parameters())


def test_all_arms_match_parameter_count() -> None:
    counts = [sum(p.numel() for p in M.SidecarTriadicNet().parameters()) for _ in M.ARMS]
    assert len(set(counts)) == 1


def test_one_update_is_finite() -> None:
    model, trace = M.train_arm(M.ARMS[0], 31, 1, torch.device("cpu"), trace_every=1)
    assert torch.isfinite(torch.tensor(trace[-1]["loss"]))
    assert all(torch.isfinite(parameter).all() for parameter in model.parameters())
