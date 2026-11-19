"""Adversarial guards for the input-access campaign.

These tests exercise restart inputs as untrusted persisted state.  They are
kept separate from the producer suite so the breaker lane can mutate receipts
without changing the campaign's happy-path fixtures.
"""

from __future__ import annotations

import json

import pytest
import torch
import torch.nn.functional as F

from python.scbe.clay_frozen_multiview_adapter import (
    FrozenActionModel,
    RunConfig,
    file_sha256,
    stable_hash,
)
from python.scbe.clay_input_access_campaign import (
    AUTHORITY,
    DOWNSTREAM_ONLY,
    EXPECTED_TRAINABLE_PARAMETERS,
    EXPECTED_VOCAB_SIZE,
    EXPECTED_SEEDS,
    INPUT_ACCESS,
    TRAIN_STAGE,
    InputAccessActionModel,
    _train_one_arm,
    construct_arm_model,
    trainable_parameter_names,
)


def _gradient_support(model: FrozenActionModel) -> tuple[int, int, dict[str, int]]:
    selected = {id(parameter) for parameter in model.parameters_for(TRAIN_STAGE)}
    per_tensor: dict[str, int] = {}
    total = 0
    expected = 0
    for name, parameter in model.named_parameters():
        if id(parameter) not in selected:
            continue
        nonzero = 0 if parameter.grad is None else int(torch.count_nonzero(parameter.grad))
        per_tensor[name] = nonzero
        total += nonzero
        expected += parameter.numel()
    return total, expected, per_tensor


def test_every_selected_scalar_has_a_gradient_path_in_both_arms() -> None:
    """Padding or masking may not make nominal capacity permanently inert."""

    torch.manual_seed(101)
    candidate = InputAccessActionModel(EXPECTED_VOCAB_SIZE)
    control = FrozenActionModel(EXPECTED_VOCAB_SIZE)
    assert candidate.input_embedding.padding_idx is None
    with torch.no_grad():
        candidate.input_up.weight.copy_(
            torch.linspace(
                -0.05,
                0.05,
                candidate.input_up.weight.numel(),
            ).reshape_as(candidate.input_up.weight)
        )
        candidate.input_up.bias.copy_(torch.linspace(-0.02, 0.02, candidate.input_up.bias.numel()))
        control.adapter.up.weight.copy_(
            torch.linspace(
                -0.05,
                0.05,
                control.adapter.up.weight.numel(),
            ).reshape_as(control.adapter.up.weight)
        )
        control.adapter.up.bias.copy_(torch.linspace(-0.02, 0.02, control.adapter.up.bias.numel()))

    # Cover every vocabulary row exactly once.  The input-access arm also
    # prepends token zero as its causal, trainable start anchor.
    inputs = torch.arange(EXPECTED_VOCAB_SIZE).reshape(12, 23)
    frozen_hidden = torch.randn(
        (12, 23, 192),
        generator=torch.Generator().manual_seed(202),
    )
    targets = (inputs + 1) % EXPECTED_VOCAB_SIZE
    candidate_logits, _ = candidate.action_logits_from_hidden(inputs, frozen_hidden)
    F.cross_entropy(
        candidate_logits.reshape(-1, EXPECTED_VOCAB_SIZE),
        targets.reshape(-1),
    ).backward()
    control_logits = control.adapter_head(control.adapter(frozen_hidden))
    F.cross_entropy(
        control_logits.reshape(-1, EXPECTED_VOCAB_SIZE),
        targets.reshape(-1),
    ).backward()

    candidate_nonzero, candidate_count, candidate_tensors = _gradient_support(candidate)
    control_nonzero, control_count, control_tensors = _gradient_support(control)
    assert candidate_count == control_count == EXPECTED_TRAINABLE_PARAMETERS
    assert candidate_nonzero == candidate_count, candidate_tensors
    assert control_nonzero == control_count, control_tensors


def test_zero_init_opens_raw_input_gradients_after_one_optimizer_step() -> None:
    """The zero projection preserves init, then opens the causal input path."""

    torch.manual_seed(303)
    parent_model = FrozenActionModel(EXPECTED_VOCAB_SIZE)
    parent = {
        "vocab": list(range(EXPECTED_VOCAB_SIZE)),
        "model_state": parent_model.state_dict(),
    }
    candidate = construct_arm_model(
        arm=INPUT_ACCESS,
        parent=parent,
        seed=EXPECTED_SEEDS[0],
        device="cpu",
    )
    control = construct_arm_model(
        arm=DOWNSTREAM_ONLY,
        parent=parent,
        seed=EXPECTED_SEEDS[0],
        device="cpu",
    )
    assert sum(p.numel() for p in candidate.parameters_for(TRAIN_STAGE)) == 140_820
    assert sum(p.numel() for p in control.parameters_for(TRAIN_STAGE)) == 140_820

    inputs = torch.arange(EXPECTED_VOCAB_SIZE).reshape(12, 23)
    frozen_hidden = torch.randn(
        (12, 23, 192),
        generator=torch.Generator().manual_seed(404),
    )
    targets = (inputs + 17) % EXPECTED_VOCAB_SIZE
    with torch.no_grad():
        initial_candidate, _ = candidate.action_logits_from_hidden(
            inputs,
            frozen_hidden,
        )
        initial_control = control.adapter_head(control.adapter(frozen_hidden))
    assert torch.equal(initial_candidate, initial_control)

    optimizer = torch.optim.Adam(candidate.parameters_for(TRAIN_STAGE), lr=0.002)
    optimizer.zero_grad()
    logits, _ = candidate.action_logits_from_hidden(inputs, frozen_hidden)
    F.cross_entropy(
        logits.reshape(-1, EXPECTED_VOCAB_SIZE),
        targets.reshape(-1),
    ).backward()
    assert candidate.input_embedding.weight.grad is not None
    assert int(torch.count_nonzero(candidate.input_embedding.weight.grad)) == 0
    assert candidate.input_recurrence.weight_ih_l0.grad is not None
    assert int(torch.count_nonzero(candidate.input_recurrence.weight_ih_l0.grad)) == 0
    assert candidate.input_up.weight.grad is not None
    assert float(candidate.input_up.weight.grad.abs().sum()) > 0.0
    optimizer.step()

    optimizer.zero_grad()
    logits, _ = candidate.action_logits_from_hidden(inputs, frozen_hidden)
    F.cross_entropy(
        logits.reshape(-1, EXPECTED_VOCAB_SIZE),
        targets.reshape(-1),
    ).backward()
    embedding_grad = candidate.input_embedding.weight.grad
    assert embedding_grad is not None
    assert float(embedding_grad[0].abs().sum()) > 0.0
    assert float(embedding_grad[1:].abs().sum()) > 0.0
    recurrent_gradients = (
        candidate.input_recurrence.weight_ih_l0.grad,
        candidate.input_recurrence.weight_hh_l0.grad,
        candidate.input_recurrence.bias_ih_l0.grad,
        candidate.input_recurrence.bias_hh_l0.grad,
    )
    assert all(gradient is not None and float(gradient.abs().sum()) > 0.0 for gradient in recurrent_gradients)


def test_completed_arm_resume_rejects_mutated_seed(tmp_path) -> None:
    """A self-consistent file hash must not make a foreign receipt resumable."""

    campaign_config_hash = "campaign-config"
    arm_config_hash = stable_hash(
        {
            "campaign_config_hash": campaign_config_hash,
            "arm": DOWNSTREAM_ONLY,
        }
    )
    directory = tmp_path / "arms" / f"{DOWNSTREAM_ONLY}-seed-{EXPECTED_SEEDS[0]}"
    directory.mkdir(parents=True)
    model_path = directory / "MODEL.pt"
    model_path.write_bytes(b"not a trusted model payload")
    torch.manual_seed(11)
    parent_model = FrozenActionModel(EXPECTED_VOCAB_SIZE)
    parent = {
        "vocab": list(range(EXPECTED_VOCAB_SIZE)),
        "model_state": parent_model.state_dict(),
    }
    config = RunConfig(
        seeds=EXPECTED_SEEDS,
        data_seed=20261113,
        rows_per_view=1000,
        holdout_rows=1500,
        count_steps=28000,
        grow_steps=2000,
        checkpoint_every=250,
        batch_size=128,
        learning_rate=0.002,
        threads=2,
        device="cpu",
        source_dir="source",
        source_hashes={},
        dataset_manifest_sha256="dataset",
        authority=AUTHORITY,
        arms=("no_intervention_adapter", DOWNSTREAM_ONLY, INPUT_ACCESS),
    )
    expected_model = construct_arm_model(
        arm=DOWNSTREAM_ONLY,
        parent=parent,
        seed=EXPECTED_SEEDS[0],
        device="cpu",
    )
    parent_result = {
        "parent_sha256": "parent",
        "counting_accuracy": 0.5,
    }
    forged = {
        "schema": "clay.input-access-efficacy-campaign.v1.arm-result",
        "status": "COMPLETE",
        "authority": AUTHORITY,
        "seed": EXPECTED_SEEDS[1],
        "arm": DOWNSTREAM_ONLY,
        "loss_mode": "standard",
        "campaign_config_hash": campaign_config_hash,
        "arm_config_hash": arm_config_hash,
        "steps": 2000,
        "trainable_parameters": EXPECTED_TRAINABLE_PARAMETERS,
        "parent_sha256": "parent",
        "frozen_core_bit_identical": True,
        "all_nonselected_tensors_bit_identical": True,
        "trainable_parameter_names": list(trainable_parameter_names(expected_model)),
        "parent_counting_accuracy": 0.5,
        "final_loss": 1.0,
        "model_sha256": file_sha256(model_path),
    }
    (directory / "RESULT.json").write_text(
        json.dumps(forged),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError):
        _train_one_arm(
            seed=EXPECTED_SEEDS[0],
            arm=DOWNSTREAM_ONLY,
            output=tmp_path,
            config=config,
            campaign_config_hash=campaign_config_hash,
            parent=parent,
            parent_result=parent_result,
            dataset=None,
            stoi={},
            itos={},
            count_holdout=(),
            poll_seconds=0.01,
        )
