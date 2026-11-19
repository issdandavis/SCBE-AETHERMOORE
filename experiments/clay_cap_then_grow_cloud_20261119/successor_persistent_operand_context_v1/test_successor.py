from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest
import torch

import run_persistent_operand_context as runner


def test_context_values_are_exactly_six_and_position_bounded() -> None:
    train, _, _ = runner.BASE.build_rows()
    start = runner.context_values(train[0], 0)
    end = runner.context_values(train[0], 7)
    assert len(start) == runner.CONTEXT_WIDTH == 6
    assert start[:5] == end[:5]
    assert start[5] == 0.0
    assert end[5] == 1.0
    with pytest.raises(ValueError):
        runner.context_values(train[0], 8)


def test_context_control_is_deterministic_stratified_derangement() -> None:
    train, held, _ = runner.BASE.build_rows()
    for rows in (train, held):
        first = runner.build_arm_rows(rows, runner.SEEDS[0], "context_permuted")
        second = runner.build_arm_rows(rows, runner.SEEDS[0], "context_permuted")
        assert first.assignment_sha256 == second.assignment_sha256
        for destination, source in zip(rows, first.context_rows, strict=True):
            assert destination.identity_sha256 != source.identity_sha256
            assert (destination.operation, len(str(destination.result)), destination.split) == (
                source.operation,
                len(str(source.result)),
                source.split,
            )


def test_all_trained_arms_have_exact_parameter_contract() -> None:
    assert runner.CONTEXT_PROJECTION_PARAMETERS == 1_344
    assert runner.EXPECTED_TRAINABLE_PARAMETERS == 142_164
    prereg = json.loads((Path(__file__).parent / "PREREGISTRATION.json").read_text(encoding="utf-8"))
    for arm in ("candidate", "context_permuted_control", "target_shuffle_control"):
        assert prereg["arms"][arm]["trainable_parameters"] == runner.EXPECTED_TRAINABLE_PARAMETERS


def test_context_batch_persists_record_and_advances_only_decode_position() -> None:
    train, _, _ = runner.BASE.build_rows()
    rows = train[:2]
    arm = runner.build_arm_rows(rows, runner.SEEDS[0], "candidate")

    class FakeCore:
        @staticmethod
        def make_batch(pairs, indices, stoi, device):
            del pairs, stoi
            batch = len(tuple(indices))
            inputs = torch.zeros((batch, 4), dtype=torch.long, device=device)
            labels = torch.zeros_like(inputs)
            masks = torch.tensor([[0.0, 1.0, 1.0, 1.0]] * batch, device=device)
            return inputs, labels, masks

    _, _, masks, context = runner.make_context_batch(FakeCore, arm, (0, 1), {}, "cpu")
    assert arm.context_rows == tuple(rows)
    assert torch.equal(context[0, :, :5], context[0, :1, :5].expand(4, 5))
    assert torch.allclose(context[0, :, 5], torch.tensor([0.0, 0.0, 1 / 7, 2 / 7]))
    assert torch.equal(masks[0], torch.tensor([0.0, 1.0, 1.0, 1.0]))


def test_synthetic_smoke_changes_only_trainable_path() -> None:
    receipt = runner.run_smoke()
    assert receipt["status"] == "PASS_NO_PARENT_LOAD_NO_CLOUD_EXECUTION"
    assert receipt["matched_initialization"] is True
    assert receipt["frozen_tensors_bit_identical_after_synthetic_update"] is True
    assert receipt["context_projection_parameters"] == 1_344
    assert receipt["campaign_trainable_parameters"] == 142_164
    assert torch.isfinite(torch.tensor(receipt["synthetic_loss"]))


def test_cli_writes_bounded_receipt(tmp_path: Path) -> None:
    output = tmp_path / "SMOKE.json"
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "run_persistent_operand_context.py"), "--smoke-output", str(output)],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["status"] == "PASS_NO_PARENT_LOAD_NO_CLOUD_EXECUTION"
    assert receipt["promotion"] == "NONE"
