from __future__ import annotations

from pathlib import Path

import pytest
import torch

from python.scbe.training_data_coverage import (
    CoverageAuditError,
    FEATURE_NAMES,
    TensorBundle,
    derive_factors,
    joint_receipt,
    load_tensor_bundle,
    simulate_uniform_replay,
)


def _bundle(tmp_path: Path, count: int = 48) -> TensorBundle:
    features = torch.zeros((count, len(FEATURE_NAMES)), dtype=torch.float32)
    for row in range(count):
        features[row, 0] = -0.9 + 1.8 * row / max(1, count - 1)
        features[row, 1] = -0.9 + 1.8 * ((row * 7) % count) / max(1, count - 1)
        features[row, 2] = -0.6 + 1.2 * ((row * 5) % count) / max(1, count - 1)
        features[row, 3] = -0.6 + 1.2 * ((row * 11) % count) / max(1, count - 1)
        features[row, 14] = (-1.0, 1.0)[row % 2]
        features[row, 15] = (-1.0, 1.0)[(row // 2) % 2]
        features[row, 18] = 0.1 * (row % 8)
        features[row, 19 + row % 4] = 1.0
        features[row, 23 + row % 3] = 1.0
        features[row, 26 + (row // 3) % 4] = 1.0
        features[row, 30] = (row % 3) / 8.0
        features[row, 31] = (row % 4) / 4.0
        features[row, 32] = (row % 3) / 2.0
        features[row, 33:36] = (row % 5) / 5.0
        features[row, 36] = 1.0
    labels = torch.arange(count, dtype=torch.int64) % 5
    sectors = torch.arange(count, dtype=torch.int64) % 8
    rewards = torch.zeros((count, 5), dtype=torch.float64)
    path = tmp_path / "TRAIN.pt"
    torch.save(
        {
            "features": features,
            "labels": labels,
            "sectors": sectors,
            "reward_values": rewards,
        },
        path,
    )
    return load_tensor_bundle(path)


def test_load_and_derive_declared_factors(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    factors = derive_factors(bundle)
    assert set(factors["phase"].tolist()) == {0, 1, 2, 3}
    assert set(factors["drive"].tolist()) == {-1, 0, 1}
    assert set(factors["memory_slots"].tolist()) == {0, 1, 2}
    assert set(factors["stagnation_ticks"].tolist()) == {0, 1, 2, 3}
    assert set(factors["outburst_ticks"].tolist()) == {0, 1, 2}


def test_joint_receipt_reports_cartesian_holes(tmp_path: Path) -> None:
    factors = derive_factors(_bundle(tmp_path, count=12))
    receipt = joint_receipt(factors, ("phase", "drive", "target"))
    assert receipt["cartesian_cells"] == 48
    assert receipt["observed_cells"] < receipt["cartesian_cells"]
    assert receipt["missing_cell_count"] > 0


def test_uniform_replay_is_deterministic_and_never_claims_support_growth() -> None:
    left = simulate_uniform_replay(32, held_sector=1, seed=11, steps=100, batch_size=16)
    right = simulate_uniform_replay(32, held_sector=1, seed=11, steps=100, batch_size=16)
    assert left == right
    assert left["draws"] == 1600
    assert left["unique_rows_seen"] == 32
    assert left["support_expansion_rows"] == 0


def test_loader_rejects_wrong_feature_width(tmp_path: Path) -> None:
    path = tmp_path / "bad.pt"
    torch.save(
        {
            "features": torch.zeros((2, 3)),
            "labels": torch.zeros(2, dtype=torch.int64),
            "sectors": torch.zeros(2, dtype=torch.int64),
            "reward_values": torch.zeros((2, 5), dtype=torch.float64),
        },
        path,
    )
    with pytest.raises(CoverageAuditError, match="37-column"):
        load_tensor_bundle(path)
