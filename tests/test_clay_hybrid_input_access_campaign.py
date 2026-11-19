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
)
from python.scbe.clay_hybrid_input_access_campaign import (
    COMPACT_EMBEDDING_WIDTH,
    COMPACT_INPUT_ROWS,
    COMPACT_RECURRENT_WIDTH,
    DOWNSTREAM_ONLY,
    EXPECTED_ABSENT_FULL_IDS,
    EXPECTED_COMPACT_FULL_IDS,
    EXPECTED_SEEDS,
    EXPECTED_TRAINABLE_PARAMETERS,
    EXPECTED_VOCAB_SIZE,
    HYBRID_ADAPTER_BOTTLENECK,
    HYBRID_INPUT_ACCESS,
    TRAIN_STAGE,
    HybridInputAccessActionModel,
    construct_arm_model,
    derive_compact_input_ids,
    effective_capacity_receipt,
    initial_pair_receipt,
    parse_args,
    validate_preregistration,
)


def _parent(seed: int = 7) -> dict:
    torch.manual_seed(seed)
    model = FrozenActionModel(EXPECTED_VOCAB_SIZE)
    return {
        "vocab": list(range(EXPECTED_VOCAB_SIZE)),
        "model_state": model.state_dict(),
    }


def _full_vocab_fixture() -> tuple[list[tuple[str, str]], dict[str, int]]:
    # IDs 0..3 retain the production special-token meaning.  Every other ID
    # receives one unique Unicode code point so the real encoder drives the
    # exact compact-alphabet contract without using holdout data.
    chars = [chr(0x1000 + index) for index in range(EXPECTED_VOCAB_SIZE)]
    stoi = {chars[index]: index for index in range(EXPECTED_VOCAB_SIZE)}
    stoi.update({"\x00": 0, "\x01": 1, "\x02": 2, "\x03": 3})
    observed = [index for index in EXPECTED_COMPACT_FULL_IDS if index >= 4]
    rows = [
        ("".join(chars[index] for index in observed[start : start + 20]), chars[4])
        for start in range(0, len(observed), 20)
    ]
    # encode() imports the production special constants, which are these four
    # characters.  Keep the test mapping explicit and local.
    from python.scbe.clay_frozen_multiview_adapter import BOS, EOS, PAD, SEP

    stoi[PAD], stoi[BOS], stoi[SEP], stoi[EOS] = 0, 1, 2, 3
    return rows, stoi


def test_preregistered_architecture_has_exact_matched_budget() -> None:
    adapter = (
        192 * HYBRID_ADAPTER_BOTTLENECK
        + HYBRID_ADAPTER_BOTTLENECK
        + HYBRID_ADAPTER_BOTTLENECK**2
        + HYBRID_ADAPTER_BOTTLENECK
        + HYBRID_ADAPTER_BOTTLENECK * 192
        + 192
    )
    input_path = (
        COMPACT_INPUT_ROWS * COMPACT_EMBEDDING_WIDTH
        + 3 * COMPACT_RECURRENT_WIDTH * (COMPACT_EMBEDDING_WIDTH + COMPACT_RECURRENT_WIDTH + 2)
        + COMPACT_RECURRENT_WIDTH * 192
        + 192
    )
    head = 192 * EXPECTED_VOCAB_SIZE + EXPECTED_VOCAB_SIZE
    assert (adapter, input_path, head) == (49_379, 38_173, 53_268)
    assert adapter + input_path + head == EXPECTED_TRAINABLE_PARAMETERS


def test_parse_args_pins_three_seed_standard_ce_budget() -> None:
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
    assert args.steps == 2_000
    assert args.checkpoint_every == 250
    assert args.batch_size == 128
    assert args.threads == 2
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
def test_parse_args_rejects_budget_drift(flag: str, value: str) -> None:
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


def test_preregistration_is_hash_pinned_and_mutation_fails(tmp_path: Path) -> None:
    pinned = Path(__file__).parents[1] / "docs" / "research" / "CLAY_HYBRID_INPUT_ACCESS_PREREGISTRATION_20261119.json"
    assert validate_preregistration(pinned)["status"] == "PREREGISTERED_BEFORE_RESULTS"
    mutated = tmp_path / "prereg.json"
    value = json.loads(pinned.read_text(encoding="utf-8"))
    value["run"]["steps"] = 1
    mutated.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(RuntimeError, match="hash differs"):
        validate_preregistration(mutated)


def test_compact_alphabet_comes_from_training_inputs_and_excludes_seven_ids() -> None:
    rows, stoi = _full_vocab_fixture()
    compact = derive_compact_input_ids(rows, stoi)
    assert compact == EXPECTED_COMPACT_FULL_IDS
    assert len(compact) == 269
    assert tuple(index for index in range(276) if index not in compact) == (EXPECTED_ABSENT_FULL_IDS)


def test_hybrid_rejects_absent_action_ids_but_count_path_bypasses_sidecar() -> None:
    model = HybridInputAccessActionModel(
        EXPECTED_VOCAB_SIZE,
        EXPECTED_COMPACT_FULL_IDS,
    ).eval()
    absent = torch.tensor([[EXPECTED_ABSENT_FULL_IDS[0]]], dtype=torch.long)
    with pytest.raises(RuntimeError, match="unmapped hybrid action input"):
        model(absent, "action")
    with torch.inference_mode():
        count_logits, _ = model(absent, "count")
    assert count_logits.shape == (1, 1, EXPECTED_VOCAB_SIZE)


def test_hybrid_and_control_are_exactly_matched_and_bit_identical_at_init() -> None:
    parent = _parent()
    rows, stoi = _full_vocab_fixture()
    probe = initial_pair_receipt(
        parent=parent,
        seed=EXPECTED_SEEDS[0],
        compact_input_ids=EXPECTED_COMPACT_FULL_IDS,
        rows=rows,
        stoi=stoi,
        device="cpu",
    )
    assert probe["bit_identical_logits"] is True
    assert probe["control_trainable_parameters"] == EXPECTED_TRAINABLE_PARAMETERS
    assert probe["candidate_trainable_parameters"] == EXPECTED_TRAINABLE_PARAMETERS


def test_hybrid_input_path_is_causal() -> None:
    model = HybridInputAccessActionModel(
        EXPECTED_VOCAB_SIZE,
        EXPECTED_COMPACT_FULL_IDS,
    ).eval()
    with torch.no_grad():
        model.input_up.weight.fill_(0.25)
        model.input_up.bias.zero_()
    left = torch.tensor([[1, 20, 21, 22]], dtype=torch.long)
    right = torch.tensor([[1, 20, 21, 23]], dtype=torch.long)
    hidden = torch.zeros((1, 4, 192), dtype=torch.float32)
    with torch.inference_mode():
        left_logits, _ = model.action_logits_from_hidden(left, hidden)
        right_logits, _ = model.action_logits_from_hidden(right, hidden)
    assert torch.equal(left_logits[:, :3], right_logits[:, :3])
    assert not torch.equal(left_logits[:, 3], right_logits[:, 3])


def test_actual_encoder_rows_reach_and_change_all_selected_scalars() -> None:
    parent = _parent()
    rows, stoi = _full_vocab_fixture()
    receipt = effective_capacity_receipt(
        parent=parent,
        seed=EXPECTED_SEEDS[0],
        compact_input_ids=EXPECTED_COMPACT_FULL_IDS,
        rows=rows,
        stoi=stoi,
        device="cpu",
    )
    assert receipt["status"] == "PASS"
    for arm in (DOWNSTREAM_ONLY, HYBRID_INPUT_ACCESS):
        assert receipt["arms"][arm]["selected_scalars"] == 140_820
        assert receipt["arms"][arm]["gradient_reachable_scalars"] == 140_820
        assert receipt["arms"][arm]["two_step_changed_scalars"] == 140_820


def test_hybrid_checkpoint_advances_and_foreign_identity_is_rejected(
    tmp_path: Path,
) -> None:
    parent = _parent()
    rows = (("a", "b"), ("b", "a"))
    from python.scbe.clay_frozen_multiview_adapter import BOS, EOS, PAD, SEP

    stoi = {PAD: 0, BOS: 1, SEP: 2, EOS: 3, "a": 4, "b": 5}
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
        arms=(HYBRID_INPUT_ACCESS,),
    )
    identity = stable_hash({"test": "hybrid-resume"})
    checkpoint_dir = tmp_path / "checkpoints"
    first = construct_arm_model(
        arm=HYBRID_INPUT_ACCESS,
        parent=parent,
        seed=EXPECTED_SEEDS[0],
        compact_input_ids=EXPECTED_COMPACT_FULL_IDS,
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
        config_hash=identity,
    )
    assert step == 1
    resumed = construct_arm_model(
        arm=HYBRID_INPUT_ACCESS,
        parent=parent,
        seed=EXPECTED_SEEDS[0],
        compact_input_ids=EXPECTED_COMPACT_FULL_IDS,
        device="cpu",
    )
    step, _, _ = train_steps(
        model=resumed,
        stage=TRAIN_STAGE,
        seed=EXPECTED_SEEDS[0],
        rows=rows,
        samples=None,
        ledger=None,
        stoi=stoi,
        config=config,
        total_steps=2,
        checkpoint_dir=checkpoint_dir,
        config_hash=identity,
    )
    assert step == 2
    foreign = construct_arm_model(
        arm=HYBRID_INPUT_ACCESS,
        parent=parent,
        seed=EXPECTED_SEEDS[0],
        compact_input_ids=EXPECTED_COMPACT_FULL_IDS,
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
            config_hash="foreign",
        )
