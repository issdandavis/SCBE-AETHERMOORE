"""Controls for the preregistered Clay held-sector gate."""

from __future__ import annotations

from copy import deepcopy

import pytest

from python.scbe.clay_multiview_stratified_gate import (
    StratifiedGateError,
    evaluate_stratified_gate,
)
from python.scbe.clay_paired_orbit_training import sha256_json


def _producer(candidate: float = 0.80, control: float = 0.70) -> dict:
    horses = []
    for held in (1, 4, 7):
        for arm, score in (
            ("static_unique", control),
            ("static_repeated", control - 0.01),
            ("curriculum_independent", candidate),
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
            "primary_arm": "curriculum_independent",
            "controls": ["static_unique", "static_repeated"],
            "held_sectors": [1, 4, 7],
            "evaluation_records": 10_000,
        },
        "horses": horses,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    return {**body, "result_sha256": sha256_json(body)}


def test_stratified_gate_passes_only_large_consistent_effect() -> None:
    report = evaluate_stratified_gate(_producer())
    assert report["verdict"] == "PASS_STRATIFIED_MECHANICS_NO_PROMOTION"
    assert report["finite_evaluation_floor"] == pytest.approx(0.02)
    assert report["promotion_authorized"] is False
    assert report["partial_unfreeze_authorized"] is False
    assert all(row["passes"] for row in report["comparisons"].values())


def test_finite_evaluation_floor_blocks_small_zero_variance_lead() -> None:
    report = evaluate_stratified_gate(_producer(candidate=0.715, control=0.70))
    assert report["verdict"] == "NO_SELECTION"
    row = report["comparisons"]["static_unique"]["sectors"]["1"]["metrics"]["accuracy"]
    assert row["two_pooled_sd"] == 0.0
    assert row["delta"] == pytest.approx(0.015)
    assert row["clears_gate"] is False


def test_stratified_gate_rejects_unmatched_seeds() -> None:
    producer = _producer()
    producer["horses"] = [
        row
        for row in producer["horses"]
        if not (row["held_sector"] == 1 and row["arm"] == "static_repeated" and row["seed"] == 47)
    ]
    body = {key: value for key, value in producer.items() if key != "result_sha256"}
    producer["result_sha256"] = sha256_json(body)
    with pytest.raises(StratifiedGateError, match="matched seeds differ"):
        evaluate_stratified_gate(producer)


def test_stratified_gate_rejects_tampered_producer_receipt() -> None:
    producer = deepcopy(_producer())
    producer["horses"][0]["holdout"]["accuracy"] = 1.0
    with pytest.raises(StratifiedGateError, match="receipt does not verify"):
        evaluate_stratified_gate(producer)
