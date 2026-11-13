from __future__ import annotations

import random

import torch

from python.scbe.clay_frozen_multiview_data import (
    BYTE_TOKEN_BASE,
    HOLDOUT_SOURCE,
    MULTIVIEW_SOURCES,
    STATIC_SOURCE,
    action_prompt,
    build_frozen_multiview_dataset,
    byte_token_text,
    decode_byte_token_text,
    feature_bytes,
)
from python.scbe.concept_exposure_ledger import ConceptExposureLedger


class FakeProvider:
    source_hashes = {"fake": "a" * 64}

    def training_sandboxes(self) -> tuple[int, ...]:
        return (0, 1, 2)

    def holdout_sandbox(self) -> int:
        return 9

    def sample_state(self, sandbox: int, rng: random.Random) -> int:
        return rng.randrange(1, 1_000_000)

    def materialize(self, sandbox: int, state: int) -> tuple[torch.Tensor, int, int]:
        label = state % 5
        sector = (state // 5) % 8
        base = torch.arange(37, dtype=torch.float32)
        feature = base * 0.03125 + state * 1e-5 + sandbox * 0.125
        return feature, label, sector


def test_byte_tokens_round_trip_exact_float32_state() -> None:
    feature = torch.linspace(-3.5, 4.25, 37, dtype=torch.float32)
    payload = feature_bytes(feature)
    encoded = byte_token_text(payload)

    assert len(payload) == 148
    assert len(encoded) == 148
    assert min(map(ord, encoded)) >= BYTE_TOKEN_BASE
    assert decode_byte_token_text(encoded) == payload
    assert decode_byte_token_text(action_prompt(feature)[3:-3]) == payload


def test_dataset_has_equal_support_disjoint_sources_and_explicit_tensor_axes() -> None:
    dataset = build_frozen_multiview_dataset(FakeProvider(), rows_per_view=10, holdout_rows=15, seed=20261113)

    assert dataset.verify()
    assert len(dataset.static_rows) == len(dataset.multiview_rows) == 30
    assert len(dataset.holdout_rows) == 15
    assert dataset.manifest["static_action_counts"] == {f"action-{index}": 6 for index in range(5)}
    assert dataset.manifest["multiview_action_counts"] == {f"action-{index}": 6 for index in range(5)}
    assert {row.sample.source_family for row in dataset.static_rows} == {STATIC_SOURCE}
    assert {row.sample.source_family for row in dataset.multiview_rows} == set(MULTIVIEW_SOURCES)
    assert {row.sample.source_family for row in dataset.holdout_rows} == {HOLDOUT_SOURCE}

    ledger = ConceptExposureLedger(
        [
            *(row.sample for row in dataset.multiview_rows),
            *(row.sample for row in dataset.holdout_rows),
        ],
        gradient_width=5,
    )
    first = dataset.multiview_rows[:3]
    ledger.observe_batch(
        [row.sample.sample_id for row in first],
        [0.5, 0.6, 0.7],
        [[0.0] * 5] * 3,
    )
    report = ledger.report()

    assert report["total_exposures"] == 3
    assert report["exposure_tensor"]["view_ids"] == [
        "train-view-0",
        "train-view-1",
        "train-view-2",
    ]
    assert HOLDOUT_SOURCE in report["evaluation_source_families"]
    assert HOLDOUT_SOURCE not in report["train_source_families"]
