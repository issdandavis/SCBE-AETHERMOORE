"""Tests for the matched-control Kaprekar mirror benchmark."""

from __future__ import annotations

from copy import deepcopy

import pytest

from src.training.kaprekar_mirror_benchmark import (
    CONDITIONS,
    FEATURE_DIM,
    FeatureBuilder,
    apply_promotion_gate,
    assert_route_pair_contract,
    build_route_pairs,
)
from src.training.kaprekar_mirror_dataset import build_records


@pytest.fixture(scope="module")
def records() -> list[dict]:
    return build_records(width=4, split_seed=6174)


def test_all_feature_arms_have_identical_width(records: list[dict]) -> None:
    builder = FeatureBuilder(records, seed=6174)
    record = records[3524]

    vectors = {condition: builder.vector(record, condition) for condition in CONDITIONS}
    assert {vector.shape for vector in vectors.values()} == {(FEATURE_DIM,)}
    assert vectors["raw"][4:].tolist() == [0.0] * (FEATURE_DIM - 4)
    assert vectors["digit_stats"][10:].tolist() == [0.0] * (FEATURE_DIM - 10)
    assert vectors["primary_random_pad"][:15].tolist() == vectors["primary"][:15].tolist()
    assert vectors["primary_random_pad"][15:].tolist() != [0.0] * 5


def test_feature_builder_cannot_observe_labels(records: list[dict]) -> None:
    original = records[3524]
    poisoned = deepcopy(original)
    poisoned["labels"] = {
        "primary_next_state": "999",
        "mirror_next_state": "111",
    }

    original_builder = FeatureBuilder(records, seed=6174)
    poisoned_records = list(records)
    poisoned_records[3524] = poisoned
    poisoned_builder = FeatureBuilder(poisoned_records, seed=6174)

    for condition in CONDITIONS:
        assert (
            original_builder.vector(original, condition).tolist()
            == poisoned_builder.vector(
                poisoned,
                condition,
            ).tolist()
        )


def test_route_pairs_are_balanced_and_match_depth_and_basin(
    records: list[dict],
) -> None:
    pairs = build_route_pairs(records, seed=6174)

    assert pairs
    assert_route_pair_contract(pairs)
    assert sum(pair["label"] == 1 for pair in pairs) == sum(pair["label"] == 0 for pair in pairs)


def _aggregate_for_gate(
    *,
    mirror_f1: list[float],
    digit_stats_f1: list[float],
    primary_f1: list[float],
) -> dict:
    aggregate = {}
    for condition in CONDITIONS:
        route_values = [0.70, 0.70, 0.70]
        if condition == "mirror":
            route_values = mirror_f1
        elif condition == "digit_stats":
            route_values = digit_stats_f1
        elif condition == "primary":
            route_values = primary_f1
        aggregate[condition] = {
            "route_f1": {
                "values": route_values,
                "mean": sum(route_values) / len(route_values),
                "sd": 0.0,
            },
            "transition_mae": {
                "values": [0.01, 0.01, 0.01],
                "mean": 0.01,
                "sd": 0.0,
            },
        }
    return aggregate


def test_promotion_gate_qualifies_only_a_large_consistent_lift() -> None:
    aggregate = _aggregate_for_gate(
        mirror_f1=[0.90, 0.90, 0.90],
        digit_stats_f1=[0.80, 0.80, 0.80],
        primary_f1=[0.82, 0.82, 0.82],
    )

    gate = apply_promotion_gate(aggregate)

    assert gate["status"] == "QUALIFIED"
    assert gate["qualified"] is True
    assert gate["comparisons"]["strongest_control"]["name"] == "primary"


def test_promotion_gate_marks_small_positive_lift_underpowered() -> None:
    aggregate = _aggregate_for_gate(
        mirror_f1=[0.821, 0.821, 0.821],
        digit_stats_f1=[0.80, 0.80, 0.80],
        primary_f1=[0.82, 0.82, 0.82],
    )

    gate = apply_promotion_gate(aggregate)

    assert gate["status"] == "UNDERPOWERED"
    assert gate["qualified"] is False


def test_promotion_gate_rejects_no_lift() -> None:
    aggregate = _aggregate_for_gate(
        mirror_f1=[0.79, 0.79, 0.79],
        digit_stats_f1=[0.80, 0.80, 0.80],
        primary_f1=[0.82, 0.82, 0.82],
    )

    gate = apply_promotion_gate(aggregate)

    assert gate["status"] == "NO_LIFT"
    assert gate["qualified"] is False
