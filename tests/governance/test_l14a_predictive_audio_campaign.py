from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "research" / "l14a_predictive_audio_campaign.py"
SPEC = importlib.util.spec_from_file_location("l14a_predictive_audio_campaign", MODULE_PATH)
assert SPEC and SPEC.loader
campaign = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = campaign
SPEC.loader.exec_module(campaign)


def test_feature_families_have_equal_shape_and_typed_distinctions() -> None:
    scores = np.asarray([0.2, 0.4, 0.0, 0.1, 0.5, 0.3], dtype=np.float32)
    features = campaign.features_from_scores(scores, "unit-source")
    assert set(features) == set(campaign.ARMS)
    assert all(value.shape == (6, campaign.FEATURE_WIDTH) for value in features.values())
    assert not np.array_equal(features["predictive_trits"], features["raw_lags"])
    assert features["predictive_trits"][2, 5] == 1.0  # expected signal was omitted
    assert features["no_omission"][2, 5] == 0.0
    assert np.count_nonzero(features["zero_features"]) == 0


def test_future_values_cannot_change_earlier_predictive_state() -> None:
    scores = np.linspace(0.05, 0.95, 40, dtype=np.float32)
    assert campaign.future_perturbation_count(scores, "causal-test") == 0


def test_targets_use_train_fitted_dead_zone() -> None:
    targets = campaign._targets(np.asarray([0.0, 0.1, 0.11, 0.0], dtype=np.float32), 0.05)
    assert targets.tolist() == [2, 1, 0]


def test_balanced_finite_bound_is_positive_and_shrinks() -> None:
    small = campaign._finite_balanced_bound([10, 10, 10])
    large = campaign._finite_balanced_bound([100, 100, 100])
    assert 0 < large < small
