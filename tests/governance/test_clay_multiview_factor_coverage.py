"""Controls for Clay multi-view factor-covered data selection."""

from __future__ import annotations

from copy import deepcopy

import pytest

from python.scbe import clay_multiview_factor_coverage as factor
from python.scbe.clay_paired_orbit_training import sha256_json
from tests.governance.test_clay_paired_orbit_training import FakeProvider


def test_factor_banks_match_quotas_and_remain_disjoint() -> None:
    banks, candidate, receipt = factor.build_factor_data_arms(
        FakeProvider(),
        held_sector=1,
        rows_per_view=30,
        candidate_rows_per_view=120,
        seed=1234,
    )
    assert tuple(banks) == factor.ARMS
    assert candidate.features.shape == (360, 37)
    assert all(bank.features.shape == (90, 37) for bank in banks.values())
    quotas = receipt["view_action_quotas"]
    assert quotas["multiview_random"] == quotas["multiview_factor"]
    assert quotas["multiview_random"] == quotas["multiview_factor_shuffled"]
    assert not any(receipt["selected_index_overlap"].values())
    assert not any(receipt["exact_feature_overlap"].values())
    assert receipt["intervention_verified"] is True
    assert receipt["holdout_used_for_selection"] is False


def _producer(candidate: float = 0.80, control: float = 0.70) -> dict:
    horses = []
    for held in (1, 4, 7):
        for arm, score in (
            ("static_unique", control),
            ("multiview_random", control + 0.01),
            ("multiview_factor", candidate),
            ("multiview_factor_shuffled", control + 0.005),
        ):
            for seed in (11, 29, 47):
                horses.append(
                    {
                        "held_sector": held,
                        "arm": arm,
                        "seed": seed,
                        "holdout": {
                            "accuracy": score,
                            "stable_macro_f1": score - 0.05,
                        },
                        "anchor": {"accuracy": 0.90},
                    }
                )
    body = {
        "configuration": {
            "primary_arm": factor.PRIMARY_ARM,
            "controls": list(factor.CONTROLS),
            "held_sectors": [1, 4, 7],
            "evaluation_records": 10_000,
        },
        "horses": horses,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    return {**body, "result_sha256": sha256_json(body)}


def test_factor_gate_requires_all_controls() -> None:
    report = factor.evaluate_factor_gate(_producer())
    assert report["verdict"] == "PASS_FACTOR_DATA_MECHANICS_NO_PROMOTION"
    assert all(row["passes"] for row in report["comparisons"].values())
    assert report["promotion_authorized"] is False
    assert report["partial_unfreeze_authorized"] is False


def test_factor_gate_rejects_small_lead_and_tampering() -> None:
    report = factor.evaluate_factor_gate(_producer(candidate=0.719, control=0.70))
    assert report["verdict"] == "NO_SELECTION"
    assert report["finite_evaluation_floor"] == pytest.approx(0.02)

    tampered = deepcopy(_producer())
    tampered["horses"][0]["holdout"]["accuracy"] = 1.0
    with pytest.raises(factor.FactorCoverageError, match="receipt does not verify"):
        factor.evaluate_factor_gate(tampered)


def test_small_factor_campaign_changes_weights_and_writes_gate(tmp_path) -> None:
    result = factor.run_factor_campaign(
        tmp_path / "run",
        FakeProvider(),
        seeds=(11, 29),
        held_sectors=(1, 4, 7),
        rows_per_view=30,
        candidate_rows_per_view=120,
        evaluation_records=32,
        steps=2,
        batch_size=12,
        log_every=1,
        hidden_width=8,
        device_name="cpu",
        evaluation_min_class_support=1,
    )
    assert len(result["horses"]) == 3 * 4 * 2
    assert all(row["final_weight_effect"]["changed_scalars"] > 0 for row in result["horses"])
    assert result["promotion_authorized"] is False
    assert (tmp_path / "run" / "STRATIFIED_GATE.json").is_file()
    assert (tmp_path / "run" / "MARKET_REPORT.md").is_file()
