from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts" / "experiments" / "spiral_staircase_lattice_snap.py"
SPEC = importlib.util.spec_from_file_location("spiral_staircase_lattice_snap", SOURCE)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def test_forward_states_are_lattice_nodes() -> None:
    assert M.states_snap_to_lattice()


def test_snap_keeps_soft_gradient() -> None:
    model = M.LatticeSnapStaircaseNet()
    prototypes = torch.nn.functional.normalize(torch.randn(64, M.BASE.CORE_DIM), dim=-1)
    candidate = torch.randn(4, M.BASE.CORE_DIM, requires_grad=True)
    snapped, _ = model.snap(candidate, prototypes)
    snapped.sum().backward()
    assert candidate.grad is not None
    assert float(candidate.grad.abs().sum()) > 0.0


def test_all_arms_match_parameter_count() -> None:
    counts = [sum(p.numel() for p in M.LatticeSnapStaircaseNet().parameters()) for _ in M.ARMS]
    assert len(set(counts)) == 1


def test_one_update_is_finite() -> None:
    model, trace = M.train_arm(
        M.ARMS[0], 31, 1, torch.device("cpu"), batch_size=16, trace_every=1
    )
    assert torch.isfinite(torch.tensor(trace[-1]["loss"]))
    assert all(torch.isfinite(parameter).all() for parameter in model.parameters())
