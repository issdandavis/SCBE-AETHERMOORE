from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts" / "experiments" / "spiral_staircase_sidecar.py"
SPEC = importlib.util.spec_from_file_location("spiral_staircase_sidecar", SOURCE)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def test_receipt_route_loss_is_detached_from_stack_rail() -> None:
    assert M.receipt_route_is_detached()


def test_state_transition_and_stack_have_distinct_parameters() -> None:
    model = M.DecoupledStaircaseNet()
    state_ids = {id(parameter) for parameter in model.state_transition.parameters()}
    stack_ids = {id(parameter) for parameter in model.stack_cell.parameters()}
    assert state_ids.isdisjoint(stack_ids)


def test_all_arms_match_parameter_count() -> None:
    counts = [sum(p.numel() for p in M.DecoupledStaircaseNet().parameters()) for _ in M.ARMS]
    assert len(set(counts)) == 1


def test_one_update_is_finite() -> None:
    model, trace = M.train_arm(
        M.ARMS[0], 31, 1, torch.device("cpu"), batch_size=16, trace_every=1
    )
    assert torch.isfinite(torch.tensor(trace[-1]["loss"]))
    assert all(torch.isfinite(parameter).all() for parameter in model.parameters())
