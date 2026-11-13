"""Independent replay parity tests for the frozen multi-view adapter."""

from __future__ import annotations

import inspect
import random

import torch

from python.scbe.clay_frozen_multiview_adapter import FrozenActionModel
from python.scbe.clay_frozen_multiview_data import build_frozen_multiview_dataset
from python.scbe.clay_frozen_multiview_replay import (
    ReplayFrozenActionModel,
    build_replay_dataset,
    replay_action_metrics,
)


class FakeReplayProvider:
    source_hashes = {"fake": "b" * 64}

    def training_sandboxes(self) -> tuple[int, ...]:
        return (0, 1, 2)

    def holdout_sandbox(self) -> int:
        return 9

    def sample_state(self, sandbox: int, rng: random.Random) -> int:
        return rng.randrange(1, 1_000_000)

    def materialize(self, sandbox: int, state: int) -> tuple[torch.Tensor, int, int]:
        label = state % 5
        sector = (state // 5) % 8
        feature = torch.arange(37, dtype=torch.float32) * 0.03125 + state * 1e-5 + sandbox * 0.125
        return feature, label, sector


def test_replay_model_matches_producer_without_importing_it() -> None:
    torch.manual_seed(1717)
    producer = FrozenActionModel(37)
    replay = ReplayFrozenActionModel(37)
    replay.load_state_dict(producer.state_dict(), strict=True)
    inputs = torch.randint(0, 37, (3, 11))

    producer.set_path("adapter")
    producer_action, _ = producer(inputs, "action")
    replay_action, _ = replay(inputs, head="action", null_carrier=False)
    assert torch.equal(producer_action, replay_action)

    producer.set_path("adapter_null")
    producer_null, _ = producer(inputs, "action")
    replay_null, _ = replay(inputs, head="action", null_carrier=True)
    assert torch.equal(producer_null, replay_null)

    producer_count, _ = producer(inputs, "count")
    replay_count, _ = replay(inputs, head="count", null_carrier=False)
    assert torch.equal(producer_count, replay_count)

    source = inspect.getsource(__import__("python.scbe.clay_frozen_multiview_replay", fromlist=["*"]))
    assert "from python.scbe.clay_frozen_multiview_adapter import" not in source
    assert "from python.scbe.clay_frozen_multiview_data import" not in source


def test_replay_rebuilds_dataset_without_producer_data_builder() -> None:
    producer = build_frozen_multiview_dataset(FakeReplayProvider(), rows_per_view=10, holdout_rows=15, seed=20261113)
    replay = build_replay_dataset(FakeReplayProvider(), rows_per_view=10, holdout_rows=15, seed=20261113)

    assert replay.manifest == producer.manifest
    for replay_rows, producer_rows in (
        (replay.static_rows, producer.static_rows),
        (replay.multiview_rows, producer.multiview_rows),
        (replay.holdout_rows, producer.holdout_rows),
    ):
        assert [row.pair() for row in replay_rows] == [row.pair() for row in producer_rows]
        assert [row.identity_record() for row in replay_rows] == [row.identity_record() for row in producer_rows]


def test_replay_metrics_expose_action_and_sector_failures() -> None:
    predictions = [
        {"target": 0, "prediction": 0, "correct": True, "sector": 1},
        {"target": 1, "prediction": 0, "correct": False, "sector": 1},
        {"target": 2, "prediction": 2, "correct": True, "sector": 4},
        {"target": 3, "prediction": 2, "correct": False, "sector": 4},
        {"target": 4, "prediction": 4, "correct": True, "sector": 7},
    ]

    metrics = replay_action_metrics(predictions)

    assert metrics["accuracy"] == 0.6
    assert metrics["macro_f1"] > 0.0
    assert metrics["worst_action_accuracy"] == 0.0
    assert metrics["per_action"]["1"]["false_negative"] == 1
    assert metrics["per_sector_accuracy"] == {"1": 0.5, "4": 0.5, "7": 1.0}
