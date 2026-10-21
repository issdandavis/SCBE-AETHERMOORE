from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts" / "experiments" / "spiral_staircase_reasoning.py"
SPEC = importlib.util.spec_from_file_location("spiral_staircase_reasoning", SOURCE)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def test_every_action_has_exact_inverse() -> None:
    check = M.verify_actions()
    assert check["exact"]
    assert check["checks"] == 64 * M.N_ACTIONS


def test_nested_routes_return_to_start() -> None:
    check = M.verify_routes()
    assert check["exact"]
    assert check["passed"] == check["checks"]


def test_receipt_control_changes_only_close_inputs() -> None:
    device = torch.device("cpu")
    with_receipt = M.make_route_batch(
        4,
        8,
        torch.Generator().manual_seed(17),
        device,
        receipts=True,
        schedule_mode="phi",
    )
    without_receipt = M.make_route_batch(
        4,
        8,
        torch.Generator().manual_seed(17),
        device,
        receipts=False,
        schedule_mode="phi",
    )
    assert torch.equal(with_receipt.starts, without_receipt.starts)
    assert torch.equal(with_receipt.targets, without_receipt.targets)
    assert torch.equal(with_receipt.input_actions[:4], without_receipt.input_actions[:4])
    assert torch.equal(without_receipt.input_actions[4:], torch.full_like(without_receipt.input_actions[4:], M.NULL_ACTION))
    assert torch.equal(without_receipt.realms[4:], torch.full_like(without_receipt.realms[4:], M.NULL_REALM))


def test_phi_open_and_close_share_landing_coordinates() -> None:
    batch = M.make_route_batch(
        7,
        2,
        torch.Generator().manual_seed(9),
        torch.device("cpu"),
        receipts=True,
        schedule_mode="phi",
    )
    assert torch.equal(batch.schedules[:7], batch.schedules[7:].flip(0))
    assert float(batch.schedules.abs().max()) <= 1.0


def test_all_arms_match_parameter_count() -> None:
    counts = [sum(p.numel() for p in M.SpiralStaircaseNet().parameters()) for _ in M.ARMS]
    assert len(set(counts)) == 1


def test_one_update_is_finite() -> None:
    model, trace = M.train_arm(
        M.ARMS[0], 31, 1, torch.device("cpu"), batch_size=16, trace_every=1
    )
    assert torch.isfinite(torch.tensor(trace[-1]["loss"]))
    assert all(torch.isfinite(parameter).all() for parameter in model.parameters())
