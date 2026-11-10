from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "research" / "replay_l14a_predictive_audio_independent.py"
SPEC = importlib.util.spec_from_file_location("replay_l14a_predictive_audio_independent", MODULE_PATH)
assert SPEC and SPEC.loader
replay = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = replay
SPEC.loader.exec_module(replay)


def test_independent_features_are_causal_and_complete() -> None:
    scores = np.linspace(0.05, 0.95, 30, dtype=np.float32)
    original = replay.replay_features(scores, "independent-test")
    changed = scores.copy()
    changed[15:] = changed[15:][::-1]
    perturbed = replay.replay_features(changed, "independent-test")
    assert set(original) == {
        "predictive_trits",
        "raw_lags",
        "raw_current",
        "no_adaptation",
        "no_omission",
        "shuffled_binding",
        "random_features",
        "zero_features",
    }
    np.testing.assert_array_equal(original["predictive_trits"][:15], perturbed["predictive_trits"][:15])


def test_independent_targets_preserve_three_states() -> None:
    targets = replay._targets(np.asarray([0.0, 0.2, 0.21, 0.0], dtype=np.float32), 0.05)
    assert targets.tolist() == [2, 1, 0]


def test_argmax_replay_accepts_only_numerical_ties() -> None:
    matched, tied = replay._argmax_matches_or_is_tied(1, np.asarray([0.5, 0.5 - 1e-7, 0.0]))
    assert matched and tied
    matched, tied = replay._argmax_matches_or_is_tied(1, np.asarray([0.7, 0.2, 0.1]))
    assert not matched and not tied
