from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from python.scbe import concept_orbit_replay as orbit


def test_orbit_dataset_has_matched_labels_and_sealed_sources() -> None:
    dataset = orbit.build_concept_orbit_dataset()

    assert dataset.static_train_x.shape == (740, 16, 16)
    assert dataset.orbit_train_x.shape == (740, 16, 16)
    assert dataset.validation_x.shape == (480, 16, 16)
    assert dataset.holdout_x.shape == (600, 16, 16)
    assert np.bincount(dataset.train_y).tolist() == [240, 200, 120, 80, 60, 40]
    assert dataset.manifest["source_disjoint"] is True
    assert len(dataset.static_samples) == 1820
    assert len(dataset.orbit_samples) == 1820
    all_digests = {
        *(sample.payload_sha256 for sample in dataset.static_samples),
        *(sample.payload_sha256 for sample in dataset.orbit_samples if sample.split == "train"),
    }
    assert len(all_digests) == 2560


def test_all_arms_share_field_and_initialization_and_never_trace_holdout(
    tmp_path: Path,
) -> None:
    result = orbit.run_campaign(
        tmp_path / "run",
        seeds=(11,),
        arms=orbit.ARMS,
        steps=8,
        batch_size=16,
        learning_rate=0.003,
        log_every=4,
    )
    horses = result["horses"]

    assert result["state"] == "COMPLETE_MECHANICS_NO_SELECTION"
    assert result["aggregate"]["enough_seeds"] is False
    assert len(horses) == len(orbit.ARMS)
    assert len({row["trainable_parameters"] for row in horses}) == 1
    assert len({row["initial_weight_sha256"] for row in horses}) == 1
    assert len({row["frozen_feature_sha256"] for row in horses}) == 1
    assert all(row["weight_effect"]["changed_scalars"] > 0 for row in horses)
    assert all(row["exposure"]["total_exposures"] == 8 * 16 for row in horses)
    assert all(row["authority"]["holdout_sampling"] == "PROHIBITED" for row in horses)
    for horse_dir in (tmp_path / "run" / "horses").iterdir():
        for line in (horse_dir / "TRACE.jsonl").read_text(encoding="utf-8").splitlines():
            assert "holdout" not in json.loads(line)

    replay = orbit.run_campaign(
        tmp_path / "run",
        seeds=(11,),
        arms=orbit.ARMS,
        steps=8,
        batch_size=16,
        learning_rate=0.003,
        log_every=4,
    )
    assert replay["result_sha256"] == result["result_sha256"]


def test_frozen_sheet_field_is_deterministic_and_finite() -> None:
    dataset = orbit.build_concept_orbit_dataset()
    first = orbit.build_frozen_sheet_feature_field(dataset.calibration_x, seed=29)
    second = orbit.build_frozen_sheet_feature_field(dataset.calibration_x, seed=29)
    transformed = first.transform(dataset.orbit_train_x)

    assert first.sha256 == second.sha256
    assert np.array_equal(first.projection, second.projection)
    assert transformed.shape[0] == 740
    assert transformed.shape[1] > 96
    assert np.all(np.isfinite(transformed))
