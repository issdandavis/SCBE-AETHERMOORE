from __future__ import annotations

import random
from typing import Any

import torch

from python.scbe import clay_paired_orbit_training as orbit
from python.scbe import clay_paired_orbit_evaluation as orbit_evaluation


class FakeSandbox:
    def __init__(self, view: int) -> None:
        self.view = view


class FakeProvider:
    source_hashes = {"fake": "0" * 64}

    def training_sandboxes(self) -> tuple[FakeSandbox, ...]:
        return (FakeSandbox(0), FakeSandbox(1), FakeSandbox(2))

    def holdout_sandbox(self) -> FakeSandbox:
        return FakeSandbox(3)

    def sample_state(self, sandbox: Any, rng: random.Random) -> int:
        del sandbox
        return rng.randrange(0, 1_000_000)

    def materialize(self, sandbox: FakeSandbox, state: int):
        feature = torch.zeros(orbit.FEATURE_WIDTH, dtype=torch.float32)
        feature[0] = (state % 97) / 97.0
        feature[1] = ((state // 97) % 89) / 89.0
        feature[2 + sandbox.view] = 1.0
        feature[19 + state % 4] = 1.0
        feature[23 + state % 3] = 1.0
        feature[26 + (state // 3) % 4] = 1.0
        feature[36] = 1.0
        sector = (state + sandbox.view * 2) % 8
        label = (state + sandbox.view) % orbit.ACTION_COUNT
        return feature, label, sector


def test_data_arms_are_equal_count_and_paired() -> None:
    banks = orbit.build_data_arms(FakeProvider(), held_sector=1, orbit_count=24, seed=101)
    assert tuple(banks) == orbit.ARMS
    assert {bank.features.shape for bank in banks.values()} == {(72, orbit.FEATURE_WIDTH)}
    paired = banks["paired_orbit_grouped"]
    assert paired.verify()
    assert torch.equal(paired.features, banks["paired_orbit_shuffled"].features)
    assert orbit.tensor_sha256(paired.features) == orbit.tensor_sha256(banks["paired_orbit_shuffled"].features)
    assert orbit.tensor_sha256(paired.labels) == orbit.tensor_sha256(banks["paired_orbit_shuffled"].labels)
    assert torch.all(torch.bincount(paired.groups) == 3)


def test_static_repeated_reuses_each_latent_row_three_times() -> None:
    provider = FakeProvider()
    bank = orbit.build_data_arms(provider, held_sector=4, orbit_count=12, seed=202)["static_repeated"]
    expected = orbit._collect_rows(
        provider,
        provider.training_sandboxes()[0],
        count=12,
        held_sector=4,
        include_held=False,
        seed=202 + 37,
        view=0,
    )
    expected_features = torch.stack([row[0] for row in expected])
    assert torch.equal(bank.features[:: orbit.VIEW_COUNT], expected_features)
    for group in range(12):
        rows = bank.features[bank.groups == group]
        assert rows.shape[0] == 3
        assert torch.equal(rows[0], rows[1])
        assert torch.equal(rows[1], rows[2])


def test_metrics_do_not_treat_absent_classes_as_failed_classes() -> None:
    labels = torch.tensor([0, 0, 1, 1], dtype=torch.int64)
    logits = torch.full((4, orbit.ACTION_COUNT), -8.0)
    logits[0:2, 0] = 8.0
    logits[2:4, 1] = 8.0
    metrics = orbit._metrics(logits, labels)
    assert metrics["accuracy"] == 1.0
    assert metrics["macro_f1"] == 1.0
    assert metrics["worst_class_accuracy"] == 1.0
    assert metrics["stable_macro_f1"] == 1.0
    assert metrics["worst_stable_class_accuracy"] == 1.0
    assert metrics["supported_class_count"] == 2
    assert metrics["absent_true_classes"] == [2, 3, 4]
    assert metrics["per_class_accuracy"] == [1.0, 1.0, None, None, None]


def test_small_campaign_changes_weights_and_preserves_controls(tmp_path) -> None:
    result = orbit.run_campaign(
        tmp_path / "run",
        FakeProvider(),
        seeds=(11,),
        held_sectors=(1,),
        orbit_count=24,
        evaluation_records=32,
        steps=4,
        batch_size=12,
        log_every=2,
        hidden_width=8,
        device_name="cpu",
    )
    assert result["state"] == "COMPLETE_MECHANICS_NO_PROMOTION"
    assert len(result["horses"]) == len(orbit.ARMS)
    assert len({row["trainable_parameters"] for row in result["horses"]}) == 1
    assert len({row["initial_weight_sha256"] for row in result["horses"]}) == 1
    assert all(row["final_weight_effect"]["changed_scalars"] > 0 for row in result["horses"])
    assert result["promotion_authorized"] is False
    assert (tmp_path / "run" / "MARKET_REPORT.md").is_file()

    checkpoint = tmp_path / "run" / "horses" / "held-1" / "static_unique-seed-11" / "BEST.pt"
    checkpoint_before = orbit.file_sha256(checkpoint)
    diagnostic = orbit_evaluation.evaluate_saved_campaign(
        tmp_path / "run",
        FakeProvider(),
        records=64,
        seed_offset=500_000,
        device_name="cpu",
        min_stable_support=1,
    )
    assert len(diagnostic["rows"]) == len(orbit.ARMS)
    assert diagnostic["source_records_per_split_per_fold"] == 32
    assert diagnostic["records_per_split_per_fold"] == 64
    assert diagnostic["evaluation_scale_factor"] == 2.0
    assert diagnostic["min_stable_support"] == 1
    assert diagnostic["promotion_authorized"] is False
    assert diagnostic["partial_unfreeze_authorized"] is False
    assert orbit.file_sha256(checkpoint) == checkpoint_before
    assert (tmp_path / "run" / "large-holdout-diagnostic" / "MARKET_REPORT.md").is_file()


def test_focused_campaign_declares_primary_and_controls(tmp_path) -> None:
    selected = ("static_unique", "static_repeated", "curriculum_independent")
    controls = ("static_unique", "static_repeated")
    result = orbit.run_campaign(
        tmp_path / "focused",
        FakeProvider(),
        seeds=(71,),
        held_sectors=(1,),
        orbit_count=12,
        evaluation_records=16,
        steps=2,
        batch_size=12,
        log_every=1,
        hidden_width=8,
        device_name="cpu",
        arms=selected,
        primary_arm="curriculum_independent",
        controls=controls,
        data_seed_offset=1_000_000,
        evaluation_min_class_support=4,
    )
    assert result["configuration"]["arms"] == list(selected)
    assert result["aggregate"]["primary_arm"] == "curriculum_independent"
    assert result["aggregate"]["controls"] == list(controls)
    assert result["configuration"]["data_seed_offset"] == 1_000_000
    assert result["configuration"]["evaluation_min_class_support"] == 4
    assert set(result["aggregate"]["comparisons"]) == set(controls)
    assert len(result["horses"]) == len(selected)
    assert result["promotion_authorized"] is False
