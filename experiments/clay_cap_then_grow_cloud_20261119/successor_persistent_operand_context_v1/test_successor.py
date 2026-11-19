from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest
import torch
from torch import nn

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


def test_generation_uses_independent_context_source_at_every_step() -> None:
    train, _, _ = runner.BASE.build_rows()
    prompt_row = train[0]
    context_row = next(row for row in train if row.operation == prompt_row.operation and row != prompt_row)
    seen: list[torch.Tensor] = []

    class RecordingModel(nn.Module):
        def eval(self):
            return self

        def forward(self, inputs, head, state=None, *, context=None):
            del head
            assert context is not None
            seen.append(context.detach().clone())
            logits = torch.zeros((*inputs.shape, 3), dtype=torch.float32)
            logits[..., 1] = 1.0
            return logits, state

    core = type("Core", (), {"BOS": "B", "SEP": "S", "EOS": "E"})
    stoi = {character: index for index, character in enumerate("BSE" + prompt_row.prompt)}
    stoi["x"] = 1
    itos = {0: "E", 1: "x", 2: "z"}
    runner.generate_text(
        core,
        RecordingModel(),
        prompt_row,
        stoi,
        itos,
        context_row=context_row,
        max_tokens=3,
    )
    assert len(seen) == 4
    expected_prefix = torch.tensor(runner.context_values(context_row, 0)[:5])
    for observed in seen:
        assert torch.allclose(observed[0, -1, :5], expected_prefix)
    assert [float(observed[0, -1, 5]) for observed in seen] == pytest.approx([0.0, 1 / 7, 2 / 7, 3 / 7])
    prompt_prefix = torch.tensor(runner.context_values(prompt_row, 0)[:5])
    assert not torch.equal(expected_prefix, prompt_prefix)


def test_evaluate_rows_binds_prompt_and_context_identities() -> None:
    train, _, _ = runner.BASE.build_rows()
    prompt_rows = train[:2]
    control = runner.build_arm_rows(prompt_rows, runner.SEEDS[0], "context_permuted")

    def fake_generate(core, model, prompt_row, stoi, itos, *, context_row=None, max_tokens=8):
        del core, model, stoi, itos, max_tokens
        assert context_row is not None
        return prompt_row.target if context_row.identity_sha256 != prompt_row.identity_sha256 else "wrong"

    original = runner.generate_text
    runner.generate_text = fake_generate
    try:
        predictions, metrics = runner.evaluate_rows(
            object(), object(), prompt_rows, control.context_rows, {}, {}
        )
    finally:
        runner.generate_text = original
    assert metrics["exact_accuracy"] == 1.0
    assert all(row["prompt_identity_sha256"] != row["context_identity_sha256"] for row in predictions)


def test_paired_bootstrap_gate_detects_signal_and_null() -> None:
    candidate = [True] * 80 + [False] * 20
    control = [True] * 50 + [False] * 50
    strata = ["add"] * 40 + ["subtract"] * 30 + ["multiply"] * 30
    signal = runner.paired_bootstrap_delta(
        candidate, control, seed=91, strata=strata, draws=1024
    )
    replay = runner.paired_bootstrap_delta(
        candidate, control, seed=91, strata=strata, draws=1024
    )
    null = runner.paired_bootstrap_delta(
        candidate, candidate, seed=91, strata=strata, draws=1024
    )
    assert signal == replay
    assert signal["lower_one_sided"] > 0.0
    assert signal["passes"] is True
    assert null["lower_one_sided"] == 0.0
    assert null["passes"] is False


def _gate_run(seed: int, correct_by_operation: dict[str, int], *, width: int = 100):
    predictions = []
    per_operation = {}
    for operation, correct_count in correct_by_operation.items():
        per_operation[operation] = correct_count / width
        predictions.extend(
            {
                "identity_sha256": f"{operation}-{index}",
                "operation": operation,
                "correct": index < correct_count,
            }
            for index in range(width)
        )
    exact = sum(bool(row["correct"]) for row in predictions) / len(predictions)
    return {
        "seed": seed,
        "metrics": {
            "exact_accuracy": exact,
            "macro_operation_accuracy": sum(per_operation.values()) / len(per_operation),
            "per_operation": per_operation,
        },
        "predictions": predictions,
        "retention_exact": True,
        "training": {"frozen_core_bit_identical": True},
    }


def test_admission_gate_retains_all_gates_and_rejects_one_example_lead() -> None:
    candidate = [
        _gate_run(seed, {"add": 80, "subtract": 80, "multiply": 80})
        for seed in runner.SEEDS
    ]
    controls = {
        "context_permuted": [
            _gate_run(seed, {"add": 40, "subtract": 40, "multiply": 40})
            for seed in runner.SEEDS
        ],
        "target_shuffle": [
            _gate_run(seed, {"add": 45, "subtract": 45, "multiply": 45})
            for seed in runner.SEEDS
        ],
        "zero_update": [
            _gate_run(seed, {"add": 50, "subtract": 50, "multiply": 50})
            for seed in runner.SEEDS
        ],
    }
    passed = runner.admission_gate(
        candidate,
        controls,
        independent_replay=True,
        bootstrap_seed=71,
        bootstrap_draws=1024,
    )
    assert passed["all_measurement_gates"] is True
    assert passed["promotion"] == "NONE"

    one_example_candidate = [
        _gate_run(seed, {"add": 51, "subtract": 50, "multiply": 50})
        for seed in runner.SEEDS
    ]
    one_example_controls = {
        name: [
            _gate_run(seed, {"add": 50, "subtract": 50, "multiply": 50})
            for seed in runner.SEEDS
        ]
        for name in ("context_permuted", "target_shuffle", "zero_update")
    }
    rejected = runner.admission_gate(
        one_example_candidate,
        one_example_controls,
        independent_replay=True,
        bootstrap_seed=71,
        bootstrap_draws=1024,
    )
    assert rejected["all_measurement_gates"] is False
    assert rejected["gates"]["three_seed_two_sd_three_of_three_and_finite_evaluation"] is False
    assert all(
        metric["seed_effect"]["passes"] is True
        and metric["finite_evaluation"]["passes"] is False
        for control in rejected["comparisons"].values()
        for metric in control.values()
    )


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
