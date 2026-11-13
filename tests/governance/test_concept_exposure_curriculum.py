from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "research" / "run_concept_exposure_curriculum.py"
SPEC = importlib.util.spec_from_file_location("concept_exposure_curriculum", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
campaign = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = campaign
SPEC.loader.exec_module(campaign)


def test_shape_dataset_is_byte_bound_and_source_disjoint() -> None:
    dataset = campaign.build_shape_dataset()

    assert dataset.train_x.shape == (740, 16, 16)
    assert dataset.holdout_x.shape == (600, 16, 16)
    assert dataset.manifest["source_disjoint"] is True
    assert dataset.manifest["train_source_family"] != dataset.manifest["holdout_source_family"]
    assert len(dataset.samples) == 1340
    assert len({sample.payload_sha256 for sample in dataset.samples}) == len(dataset.samples)


def test_all_arms_share_initialization_and_change_real_weights(tmp_path: Path) -> None:
    arguments = {
        "seeds": (11,),
        "arms": campaign.ARMS,
        "steps": 8,
        "batch_size": 16,
        "learning_rate": 0.003,
        "log_every": 4,
    }
    result = campaign.run_campaign(
        tmp_path / "run",
        **arguments,
    )
    horses = result["horses"]

    assert result["state"] == "COMPLETE_MECHANICS_NO_SELECTION"
    assert result["aggregate"]["enough_seeds"] is False
    assert len({row["trainable_parameters"] for row in horses}) == 1
    assert len({row["initial_weight_sha256"] for row in horses}) == 1
    assert len({row["frozen_feature_sha256"] for row in horses}) == 1
    assert all(row["weight_effect"]["changed_scalars"] > 0 for row in horses)
    assert all(row["exposure"]["total_exposures"] == 8 * 16 for row in horses)
    assert all(row["exposure"]["holdout_sample_count"] == 600 for row in horses)
    assert all(row["exposure"]["authority"]["holdout_sampling"] == "PROHIBITED" for row in horses)

    replay = campaign.run_campaign(tmp_path / "run", **arguments)
    assert replay["result_sha256"] == result["result_sha256"]


def test_frozen_feature_field_is_deterministic_and_finite() -> None:
    dataset = campaign.build_shape_dataset()
    first = campaign.build_frozen_feature_field(dataset.train_x, seed=29)
    second = campaign.build_frozen_feature_field(dataset.train_x, seed=29)
    train_features = first.transform(dataset.train_x)
    holdout_features = first.transform(dataset.holdout_x)

    assert first.sha256 == second.sha256
    assert np.array_equal(first.projection, second.projection)
    assert train_features.shape == (740, 96)
    assert holdout_features.shape == (600, 96)
    assert np.all(np.isfinite(train_features))
    assert np.all(np.isfinite(holdout_features))
