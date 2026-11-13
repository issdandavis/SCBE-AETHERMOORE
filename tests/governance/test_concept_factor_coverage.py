from __future__ import annotations

import json
from pathlib import Path

from python.scbe import concept_factor_coverage as factor


def test_factor_lattice_covers_cross_axis_pairs_without_changing_labels() -> None:
    correlated, balanced, manifest = factor.build_factor_comparison_datasets()

    assert correlated.orbit_train_x.shape == balanced.orbit_train_x.shape == (740, 16, 16)
    assert (correlated.train_y == balanced.train_y).all()
    assert manifest["factor_pair_coverage"]["diag_up"] == 49
    assert manifest["factor_pair_coverage"]["horizontal"] == 49
    assert manifest["factor_pair_coverage"]["box"] == 40
    assert correlated.calibration_x is balanced.calibration_x
    assert correlated.manifest["manifest_sha256"] != balanced.manifest["manifest_sha256"]


def test_factor_campaign_is_matched_and_replayable(tmp_path: Path) -> None:
    arguments = {
        "seeds": (11,),
        "arms": factor.ARMS,
        "steps": 8,
        "batch_size": 16,
        "learning_rate": 0.003,
        "log_every": 4,
    }
    result = factor.run_factor_campaign(tmp_path / "run", **arguments)
    horses = result["horses"]

    assert result["state"] == "COMPLETE_MECHANICS_NO_SELECTION"
    assert len(horses) == len(factor.ARMS)
    assert len({row["trainable_parameters"] for row in horses}) == 1
    assert len({row["initial_weight_sha256"] for row in horses}) == 1
    assert len({row["frozen_feature_sha256"] for row in horses}) == 1
    assert all(row["weight_effect"]["changed_scalars"] > 0 for row in horses)
    assert all(row["exposure"]["total_exposures"] == 8 * 16 for row in horses)
    for horse_dir in (tmp_path / "run" / "horses").iterdir():
        for line in (horse_dir / "TRACE.jsonl").read_text(encoding="utf-8").splitlines():
            assert "holdout" not in json.loads(line)

    replay = factor.run_factor_campaign(tmp_path / "run", **arguments)
    assert replay["result_sha256"] == result["result_sha256"]
