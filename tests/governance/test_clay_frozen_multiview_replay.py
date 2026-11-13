"""Independent replay parity tests for the frozen multi-view adapter."""

from __future__ import annotations

import inspect
import random

import pytest
import torch

from python.scbe.clay_frozen_multiview_adapter import FrozenActionModel
from python.scbe.clay_frozen_multiview_data import build_frozen_multiview_dataset
from python.scbe.clay_frozen_multiview_replay import (
    ReplayFrozenActionModel,
    byte_token_identity_receipt,
    build_replay_dataset,
    paired_output_diagnostics,
    replay_action_metrics,
    replay_output_diagnostics,
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


def test_byte_token_identity_receipt_requires_the_complete_256_plane() -> None:
    byte_plane = [chr(0xE100 + value) for value in range(256)]
    receipt = byte_token_identity_receipt(["\x00", "\x02", "\x1f", "\x03", *byte_plane])

    assert receipt["pass"] is True
    assert receipt["present_byte_token_count"] == 256
    assert receipt["model_token_ids_contiguous"] is True
    assert receipt["logical_model_tokens_per_payload_byte"] == 1
    assert receipt["utf8_storage_bytes_per_carrier_token"] == [3]
    assert receipt["feature_payload_bytes"] == 148
    assert receipt["feature_payload_model_tokens"] == 148

    missing = byte_token_identity_receipt(["\x00", *byte_plane[:-1]])
    assert missing["pass"] is False
    assert missing["missing_byte_values"] == [255]


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

    outputs = replay_output_diagnostics(
        [*predictions, {"target": 0, "prediction": None, "correct": False, "sector": 7}]
    )
    assert outputs["correct_count"] == 3
    assert outputs["invalid_prediction_count"] == 1
    assert outputs["prediction_distribution"] == {
        "0": 2,
        "1": 0,
        "2": 2,
        "3": 0,
        "4": 1,
        "invalid": 1,
    }
    assert outputs["confusion"]["0"] == {
        "0": 1,
        "1": 0,
        "2": 0,
        "3": 0,
        "4": 0,
        "invalid": 1,
    }


def test_paired_output_diagnostics_expose_fixes_regressions_and_changed_answers() -> None:
    def row(index: int, target: int, prediction: int | None, sector: int) -> dict[str, object]:
        return {
            "example_index": index,
            "payload_sha256": f"{index:064x}",
            "target": target,
            "prediction": prediction,
            "correct": prediction == target,
            "sector": sector,
        }

    control = [
        row(0, 0, 1, 0),
        row(1, 1, 1, 0),
        row(2, 2, 2, 1),
        row(3, 3, 4, 1),
        row(4, 4, None, 2),
    ]
    contender = [
        row(0, 0, 0, 0),
        row(1, 1, 2, 0),
        row(2, 2, 2, 1),
        row(3, 3, 0, 1),
        row(4, 4, None, 2),
    ]

    result = paired_output_diagnostics(contender, control)

    assert result["wins"] == 1
    assert result["losses"] == 1
    assert result["both_correct"] == 1
    assert result["both_wrong_same_output"] == 1
    assert result["both_wrong_different_output"] == 1
    assert result["prediction_changed_count"] == 3
    assert result["two_sided_exact_p"] == 1.0
    assert result["clears_finite_uncertainty_gate"] is False


def test_output_diagnostics_reject_fractional_ids_and_false_correctness() -> None:
    fractional = {
        "target": 1,
        "prediction": 1.75,
        "correct": False,
        "sector": 0,
    }
    outputs = replay_output_diagnostics([fractional])
    assert outputs["invalid_prediction_count"] == 1

    with pytest.raises(ValueError, match="correctness flag"):
        replay_output_diagnostics([{**fractional, "correct": True}])


def test_paired_output_diagnostics_reject_duplicate_examples() -> None:
    row = {
        "example_index": 0,
        "payload_sha256": "0" * 64,
        "target": 0,
        "prediction": 0,
        "correct": True,
        "sector": 0,
    }
    with pytest.raises(RuntimeError, match="duplicate contender"):
        paired_output_diagnostics([row, row], [row])
