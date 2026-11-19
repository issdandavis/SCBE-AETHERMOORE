from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch

from python.scbe.clay_frozen_multiview_adapter import (
    FrozenActionModel,
    RunConfig,
    stable_hash,
    train_steps,
    vocab_of,
)
from python.scbe.clay_input_access_campaign import (
    DOWNSTREAM_ONLY,
    EXPECTED_SEEDS,
    EXPECTED_TRAINABLE_PARAMETERS,
    EXPECTED_VOCAB_SIZE,
    INPUT_ACCESS,
    TRAIN_STAGE,
    InputAccessActionModel,
    construct_arm_model,
    nonselected_state,
    parse_args,
    producer_gate_met,
    state_identical,
    trainable_parameter_names,
    validate_parent_lineage,
    validate_preregistration,
)


def _parent(seed: int = 9) -> dict:
    torch.manual_seed(seed)
    model = FrozenActionModel(EXPECTED_VOCAB_SIZE)
    return {
        "vocab": list(range(EXPECTED_VOCAB_SIZE)),
        "model_state": model.state_dict(),
    }


def test_parse_args_pins_three_seed_discovery_budget() -> None:
    args = parse_args(
        [
            "--baseline-run",
            "baseline",
            "--output-dir",
            "output",
            "--source-dir",
            "source",
            "--preregistration",
            "pre.json",
        ]
    )
    assert args.seeds == EXPECTED_SEEDS
    assert args.steps == 2000
    assert args.checkpoint_every == 250
    assert args.minimum_free_gib == 25.0


@pytest.mark.parametrize(
    ("flag", "value"),
    (
        ("--steps", "1"),
        ("--checkpoint-every", "1"),
        ("--batch-size", "1"),
        ("--threads", "1"),
        ("--minimum-free-gib", "0"),
    ),
)
def test_parse_args_rejects_preregistered_budget_drift(flag: str, value: str) -> None:
    with pytest.raises(SystemExit):
        parse_args(
            [
                "--baseline-run",
                "baseline",
                "--output-dir",
                "output",
                "--source-dir",
                "source",
                "--preregistration",
                "pre.json",
                flag,
                value,
            ]
        )


def test_input_access_and_downstream_control_are_exactly_parameter_matched() -> None:
    parent = _parent()
    downstream = construct_arm_model(
        arm=DOWNSTREAM_ONLY,
        parent=parent,
        seed=EXPECTED_SEEDS[0],
        device="cpu",
    )
    candidate = construct_arm_model(
        arm=INPUT_ACCESS,
        parent=parent,
        seed=EXPECTED_SEEDS[0],
        device="cpu",
    )
    downstream_count = sum(p.numel() for p in downstream.parameters_for(TRAIN_STAGE))
    candidate_count = sum(p.numel() for p in candidate.parameters_for(TRAIN_STAGE))
    assert downstream_count == candidate_count == EXPECTED_TRAINABLE_PARAMETERS
    assert trainable_parameter_names(downstream) == (
        "adapter.down.weight",
        "adapter.down.bias",
        "adapter.mid.weight",
        "adapter.mid.bias",
        "adapter.up.weight",
        "adapter.up.bias",
        "adapter_head.weight",
        "adapter_head.bias",
    )
    assert trainable_parameter_names(candidate) == (
        "adapter_head.weight",
        "adapter_head.bias",
        "input_embedding.weight",
        "input_recurrence.weight_ih_l0",
        "input_recurrence.weight_hh_l0",
        "input_recurrence.bias_ih_l0",
        "input_recurrence.bias_hh_l0",
        "input_up.weight",
        "input_up.bias",
    )


def test_nonselected_snapshot_covers_unused_adapter_and_parent_core() -> None:
    parent = _parent()
    candidate = construct_arm_model(
        arm=INPUT_ACCESS,
        parent=parent,
        seed=EXPECTED_SEEDS[0],
        device="cpu",
    )
    before = nonselected_state(candidate)
    assert "e.weight" in before
    assert "g.weight_ih_l0" in before
    assert "count_head.weight" in before
    assert "adapter.down.weight" in before
    with torch.no_grad():
        candidate.input_up.bias.add_(1.0)
    assert state_identical(before, candidate)
    with torch.no_grad():
        candidate.adapter.down.bias.add_(1.0)
    assert not state_identical(before, candidate)


def test_zero_projection_makes_initial_action_logits_bit_identical() -> None:
    parent = _parent()
    downstream = construct_arm_model(
        arm=DOWNSTREAM_ONLY,
        parent=parent,
        seed=EXPECTED_SEEDS[0],
        device="cpu",
    ).eval()
    candidate = construct_arm_model(
        arm=INPUT_ACCESS,
        parent=parent,
        seed=EXPECTED_SEEDS[0],
        device="cpu",
    ).eval()
    inputs = torch.tensor([[2, 11, 19, 3], [2, 7, 5, 3]], dtype=torch.long)
    with torch.inference_mode():
        downstream_logits, _ = downstream(inputs, "action")
        candidate_logits, _ = candidate(inputs, "action")
    assert torch.equal(downstream_logits, candidate_logits)


def test_input_sidecar_is_causal_and_reads_raw_tokens() -> None:
    model = InputAccessActionModel(EXPECTED_VOCAB_SIZE).eval()
    with torch.no_grad():
        model.input_up.weight.fill_(0.25)
        model.input_up.bias.zero_()
    left = torch.tensor([[2, 31, 41, 51]], dtype=torch.long)
    right = torch.tensor([[2, 31, 41, 61]], dtype=torch.long)
    frozen_hidden = torch.zeros((1, 4, 192), dtype=torch.float32)
    with torch.inference_mode():
        left_logits, _ = model.action_logits_from_hidden(left, frozen_hidden)
        right_logits, _ = model.action_logits_from_hidden(right, frozen_hidden)
    assert torch.equal(left_logits[:, :3], right_logits[:, :3])
    assert not torch.equal(left_logits[:, 3], right_logits[:, 3])


def test_downstream_control_cannot_distinguish_inputs_when_hidden_is_fixed() -> None:
    model = FrozenActionModel(EXPECTED_VOCAB_SIZE).eval()
    frozen_hidden = torch.randn((1, 4, 192), generator=torch.Generator().manual_seed(17))
    with torch.inference_mode():
        first = model.adapter_head(model.adapter(frozen_hidden))
        second = model.adapter_head(model.adapter(frozen_hidden.clone()))
    assert torch.equal(first, second)


def test_preregistration_is_hash_pinned_and_mutation_fails(tmp_path: Path) -> None:
    pinned = Path(__file__).parents[1] / "docs" / "research" / "CLAY_INPUT_ACCESS_PREREGISTRATION_20261119.json"
    assert validate_preregistration(pinned)["status"] == "PREREGISTERED_BEFORE_RESULTS"
    mutated = tmp_path / "prereg.json"
    value = json.loads(pinned.read_text(encoding="utf-8"))
    value["training"]["steps"] = 1
    mutated.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(RuntimeError, match="hash differs"):
        validate_preregistration(mutated)


def test_parent_lineage_uses_pinned_aggregate_not_adjacent_self_claim(tmp_path: Path) -> None:
    from python.scbe.clay_frozen_multiview_adapter import file_sha256

    parent_path = tmp_path / "PARENT.pt"
    parent_path.write_bytes(b"parent-bytes")
    digest = file_sha256(parent_path)
    aggregate = {
        "parents": [
            {
                "seed": EXPECTED_SEEDS[0],
                "parent_sha256": digest,
                "counting_accuracy": 0.5,
            }
        ]
    }
    adjacent = {
        "seed": EXPECTED_SEEDS[0],
        "parent_sha256": digest,
        "counting_accuracy": 0.5,
    }
    validate_parent_lineage(
        seed=EXPECTED_SEEDS[0],
        parent_result=adjacent,
        parent_path=parent_path,
        baseline_result=aggregate,
    )
    adjacent["parent_sha256"] = "forged-together"
    with pytest.raises(RuntimeError, match="aggregate"):
        validate_parent_lineage(
            seed=EXPECTED_SEEDS[0],
            parent_result=adjacent,
            parent_path=parent_path,
            baseline_result=aggregate,
        )


def test_producer_gate_requires_finite_uncertainty_for_both_metrics_and_controls() -> None:
    names = ("input_access_vs_downstream_only", "input_access_vs_no_intervention")
    comparisons = {
        name: {
            "metrics": {metric: {"clears_positive_gate": True} for metric in ("accuracy", "macro_f1")},
            "finite_evaluation": {
                metric: {"clears_finite_uncertainty_gate": True} for metric in ("accuracy", "macro_f1")
            },
        }
        for name in names
    }
    assert producer_gate_met(comparisons, True) == (True, True, True)
    comparisons[names[0]]["finite_evaluation"]["macro_f1"]["clears_finite_uncertainty_gate"] = False
    assert producer_gate_met(comparisons, True) == (True, False, False)


def test_input_access_checkpoint_advances_and_resume_is_identity_gated(tmp_path: Path) -> None:
    parent = _parent()
    rows = (("a", "0"), ("b", "1"), ("ab", "2"), ("ba", "3"))
    _, stoi = vocab_of(rows)
    config = RunConfig(
        seeds=EXPECTED_SEEDS,
        data_seed=1,
        rows_per_view=1,
        holdout_rows=1,
        count_steps=1,
        grow_steps=2,
        checkpoint_every=1,
        batch_size=2,
        learning_rate=0.002,
        threads=1,
        device="cpu",
        source_dir="source",
        source_hashes={},
        dataset_manifest_sha256="dataset",
        authority="test-only",
        arms=(INPUT_ACCESS,),
    )
    config_hash = stable_hash({"test": "input-access-resume"})
    checkpoint_dir = tmp_path / "checkpoints"
    first = construct_arm_model(
        arm=INPUT_ACCESS,
        parent=parent,
        seed=EXPECTED_SEEDS[0],
        device="cpu",
    )
    step, _, _ = train_steps(
        model=first,
        stage=TRAIN_STAGE,
        seed=EXPECTED_SEEDS[0],
        rows=rows,
        samples=None,
        ledger=None,
        stoi=stoi,
        config=config,
        total_steps=1,
        checkpoint_dir=checkpoint_dir,
        config_hash=config_hash,
    )
    assert step == 1
    second = construct_arm_model(
        arm=INPUT_ACCESS,
        parent=parent,
        seed=EXPECTED_SEEDS[0],
        device="cpu",
    )
    step, _, _ = train_steps(
        model=second,
        stage=TRAIN_STAGE,
        seed=EXPECTED_SEEDS[0],
        rows=rows,
        samples=None,
        ledger=None,
        stoi=stoi,
        config=config,
        total_steps=2,
        checkpoint_dir=checkpoint_dir,
        config_hash=config_hash,
    )
    assert step == 2
    pointer = json.loads((checkpoint_dir / "latest.json").read_text(encoding="utf-8"))
    assert pointer["step"] == 2
    foreign = construct_arm_model(
        arm=INPUT_ACCESS,
        parent=parent,
        seed=EXPECTED_SEEDS[0],
        device="cpu",
    )
    with pytest.raises(RuntimeError, match="checkpoint identity differs"):
        train_steps(
            model=foreign,
            stage=TRAIN_STAGE,
            seed=EXPECTED_SEEDS[0],
            rows=rows,
            samples=None,
            ledger=None,
            stoi=stoi,
            config=config,
            total_steps=2,
            checkpoint_dir=checkpoint_dir,
            config_hash="foreign-config",
        )
