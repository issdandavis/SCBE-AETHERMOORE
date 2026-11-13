"""Controls for the shuffled-factor versus hash-spread campaign."""

from __future__ import annotations

from copy import deepcopy

import pytest
import torch

from python.scbe import clay_multiview_hash_spread as hash_spread
from python.scbe.clay_paired_orbit_training import sha256_json
from tests.governance.test_clay_paired_orbit_training import FakeProvider


def test_hash_codes_are_deterministic_bounded_and_seeded() -> None:
    banks, candidate, _ = hash_spread.build_hash_spread_data_arms(
        FakeProvider(),
        held_sector=1,
        rows_per_view=30,
        candidate_rows_per_view=180,
        seed=1234,
    )
    widths = [3, 5, 7]
    first = hash_spread.hash_code_matrix(candidate, seed=99, widths=widths)
    repeated = hash_spread.hash_code_matrix(candidate, seed=99, widths=widths)
    changed = hash_spread.hash_code_matrix(candidate, seed=100, widths=widths)
    assert torch.equal(first, repeated)
    assert not torch.equal(first, changed)
    assert first.shape == (candidate.features.shape[0], len(widths))
    assert all(int(first[:, column].max()) < width for column, width in enumerate(widths))
    assert tuple(banks) == hash_spread.ARMS


def test_hash_spread_banks_are_matched_disjoint_and_causally_distinct() -> None:
    banks, candidate, receipt = hash_spread.build_hash_spread_data_arms(
        FakeProvider(),
        held_sector=4,
        rows_per_view=30,
        candidate_rows_per_view=180,
        seed=4321,
    )
    assert candidate.features.shape == (540, 37)
    assert all(bank.features.shape == (90, 37) for bank in banks.values())
    quotas = receipt["view_action_quotas"]
    assert len({str(value) for value in quotas.values()}) == 1
    assert not any(receipt["selected_index_overlap"].values())
    assert not any(receipt["exact_feature_overlap"].values())
    assert receipt["intervention_verified"] is True
    hash_coverage = receipt["hash_space_coverage"]
    assert hash_coverage["multiview_hash_spread"]["mean_entropy_evenness"] > max(
        hash_coverage["multiview_random"]["mean_entropy_evenness"],
        hash_coverage["multiview_factor_shuffled"]["mean_entropy_evenness"],
    )
    assert receipt["holdout_used_for_selection"] is False
    assert receipt["reward_or_post_outcome_used_for_selection"] is False


def _producer(candidate: float = 0.82, control: float = 0.70) -> dict:
    horses = []
    for held in (1, 4, 7):
        for arm, score in (
            ("static_unique", control),
            ("multiview_random", control + 0.01),
            ("multiview_factor_shuffled", candidate),
            ("multiview_hash_spread", control + 0.02),
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
            "arms": list(hash_spread.ARMS),
            "primary_arm": hash_spread.PRIMARY_ARM,
            "controls": list(hash_spread.CONTROLS),
            "held_sectors": [1, 4, 7],
            "evaluation_records": 10_000,
        },
        "horses": horses,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    return {**body, "result_sha256": sha256_json(body)}


def test_hash_gate_requires_all_controls_and_never_promotes() -> None:
    report = hash_spread.evaluate_hash_spread_gate(_producer())
    assert report["verdict"] == "PASS_SHUFFLED_OVER_HASH_MECHANICS_NO_PROMOTION"
    assert all(row["passes"] for row in report["comparisons"].values())
    assert report["promotion_authorized"] is False
    assert report["partial_unfreeze_authorized"] is False


def test_hash_gate_rejects_small_lead_and_tampering() -> None:
    report = hash_spread.evaluate_hash_spread_gate(_producer(candidate=0.721, control=0.70))
    assert report["verdict"] == "NO_SELECTION"
    tampered = deepcopy(_producer())
    tampered["horses"][0]["holdout"]["accuracy"] = 1.0
    with pytest.raises(hash_spread.HashSpreadError, match="receipt does not verify"):
        hash_spread.evaluate_hash_spread_gate(tampered)


def test_small_hash_campaign_changes_weights_and_writes_gate(tmp_path) -> None:
    result = hash_spread.run_hash_spread_campaign(
        tmp_path / "run",
        FakeProvider(),
        seeds=(11, 29),
        held_sectors=(1, 4, 7),
        rows_per_view=30,
        candidate_rows_per_view=180,
        evaluation_records=32,
        steps=1,
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
