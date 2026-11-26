from __future__ import annotations

import numpy as np

from python.scbe.clay_frozen_multiview_data import (
    BYTE_TOKEN_BASE,
    action_prompt,
)
from python.scbe.clay_frozen_transport_probe import (
    decode_feature,
    probe_report,
)


def test_decode_feature_recovers_exact_float32_values() -> None:
    import torch

    feature = torch.linspace(-1.0, 1.0, 37, dtype=torch.float32)
    decoded = decode_feature(
        action_prompt(feature),
        byte_token_base=BYTE_TOKEN_BASE,
        width=37,
    )
    assert np.array_equal(decoded, feature.numpy())


def test_fixed_probes_separate_simple_classes_and_control_does_not() -> None:
    rng = np.random.default_rng(7)
    labels = np.repeat(np.arange(3), 80)
    train = np.eye(3, dtype=np.float32)[labels] * 8.0
    train += rng.normal(0.0, 0.15, train.shape).astype(np.float32)
    test_labels = np.repeat(np.arange(3), 30)
    test = np.eye(3, dtype=np.float32)[test_labels] * 8.0
    test += rng.normal(0.0, 0.15, test.shape).astype(np.float32)
    report = probe_report(
        train,
        labels,
        test,
        test_labels,
        shuffle_seed=17,
    )
    assert report["nearest_centroid_accuracy"] == 1.0
    assert report["ridge_alpha_1_accuracy"] == 1.0
    assert report["shuffled_label_ridge_accuracy"] < 0.5
