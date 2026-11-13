from __future__ import annotations

import random

import torch

from python.scbe.clay_frozen_multiview_adapter import (
    FrozenActionModel,
    RunConfig,
    action_metrics,
    counting_rows,
    frozen_state,
    frozen_state_identical,
    train_steps,
    vocab_of,
)
from python.scbe.clay_frozen_multiview_data import build_frozen_multiview_dataset
from python.scbe.concept_exposure_ledger import ConceptExposureLedger


class FakeProvider:
    source_hashes = {"fake": "b" * 64}

    def training_sandboxes(self) -> tuple[int, ...]:
        return (0, 1, 2)

    def holdout_sandbox(self) -> int:
        return 9

    def sample_state(self, sandbox: int, rng: random.Random) -> int:
        return rng.randrange(1, 10_000_000)

    def materialize(self, sandbox: int, state: int) -> tuple[torch.Tensor, int, int]:
        feature = torch.arange(37, dtype=torch.float32) * 0.0625 + state * 1e-6 + sandbox * 0.25
        return feature, state % 5, (state // 5) % 8


def _config(dataset_hash: str) -> RunConfig:
    return RunConfig(
        seeds=(1, 2, 3),
        data_seed=11,
        rows_per_view=5,
        holdout_rows=5,
        count_steps=1,
        grow_steps=2,
        checkpoint_every=1,
        batch_size=5,
        learning_rate=0.002,
        threads=1,
        device="cpu",
        source_dir="fake",
        source_hashes={"fake": "b" * 64},
        dataset_manifest_sha256=dataset_hash,
    )


def test_matched_adapter_step_changes_only_trainable_surface_and_records_exposure(
    tmp_path,
) -> None:
    dataset = build_frozen_multiview_dataset(FakeProvider(), rows_per_view=5, holdout_rows=5, seed=11)
    count_train = counting_rows(False)
    count_holdout = counting_rows(True)
    pairs = tuple(row.pair() for row in dataset.multiview_rows)
    vocab, stoi = vocab_of(
        count_train,
        count_holdout,
        pairs,
        tuple(row.pair() for row in dataset.holdout_rows),
    )
    torch.manual_seed(7)
    model = FrozenActionModel(len(vocab))
    frozen_before = frozen_state(model)
    adapter_before = {
        name: value.detach().clone()
        for name, value in model.state_dict().items()
        if name.startswith(("adapter.", "adapter_head."))
    }
    ledger = ConceptExposureLedger(
        [
            *(row.sample for row in dataset.multiview_rows),
            *(row.sample for row in dataset.holdout_rows),
        ],
        gradient_width=5,
    )

    steps, loss, parameters = train_steps(
        model=model,
        stage="frozen_adapter_multiview",
        seed=7,
        rows=pairs,
        samples=dataset.multiview_rows,
        ledger=ledger,
        stoi=stoi,
        config=_config(str(dataset.manifest["manifest_sha256"])),
        total_steps=2,
        checkpoint_dir=tmp_path / "checkpoints",
        config_hash="c" * 64,
    )

    assert steps == 2
    assert loss >= 0.0
    assert parameters > 0
    assert frozen_state_identical(frozen_before, model)
    assert any(
        not torch.equal(adapter_before[name], value)
        for name, value in model.state_dict().items()
        if name in adapter_before
    )
    assert ledger.report()["total_exposures"] == 10
    assert (tmp_path / "checkpoints" / "latest.json").is_file()


def test_action_metrics_exposes_class_and_sector_failures() -> None:
    predictions = [
        {"target": 0, "prediction": 0, "correct": True, "sector": 1},
        {"target": 1, "prediction": 0, "correct": False, "sector": 1},
        {"target": 2, "prediction": 2, "correct": True, "sector": 4},
        {"target": 3, "prediction": 2, "correct": False, "sector": 4},
        {"target": 4, "prediction": 4, "correct": True, "sector": 7},
    ]

    metrics = action_metrics(predictions)

    assert metrics["accuracy"] == 0.6
    assert metrics["worst_action_accuracy"] == 0.0
    assert metrics["per_action"]["1"]["false_negative"] == 1
    assert metrics["per_sector_accuracy"] == {"1": 0.5, "4": 0.5, "7": 1.0}
