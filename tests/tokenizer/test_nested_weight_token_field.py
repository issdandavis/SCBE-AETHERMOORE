"""Checks the nested weighted token-path field and its claim boundaries."""

from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

import pytest

from python.scbe.nested_weight_token_field import (
    DEFAULT_LAYER_COUNT,
    NestedWeightFieldError,
    NestedWeightFieldSpec,
    WeightedTokenPoint,
    build_nested_weight_token_field,
    ratios_are_preserved,
    world_to_layer_local,
)


def sample_path(*, middle_weight: float = -0.75):
    return (
        WeightedTokenPoint("KO:open", 1.0, (0.0, 0.0, 0.0)),
        WeightedTokenPoint("AV:turn", middle_weight, (0.8, 0.5, 0.2)),
        WeightedTokenPoint("CA:grow", 1.25, (1.5, 1.1, 0.6)),
        WeightedTokenPoint("RU:seal", 0.5, (2.0, 1.8, 1.0)),
    )


def test_default_build_is_ten_nested_matrices_with_one_growth_ratio() -> None:
    field = build_nested_weight_token_field(sample_path(), field_seed="fizzle-globe")

    assert len(field.layers) == DEFAULT_LAYER_COUNT == 10
    assert ratios_are_preserved(field)
    assert all(inner.side < outer.side for outer, inner in zip(field.layers, field.layers[1:]))
    assert field.common_growth_ratio >= 1.0
    assert field.common_growth_ratio <= math.exp(NestedWeightFieldSpec().growth_gain)


def test_nested_vertices_round_trip_through_each_layer_matrix() -> None:
    field = build_nested_weight_token_field(sample_path(), field_seed=b"round-trip")
    expected = (
        (-0.5, -0.5, 0.0),
        (0.5, -0.5, 0.0),
        (0.5, 0.5, 0.0),
        (-0.5, 0.5, 0.0),
    )

    for layer in field.layers:
        recovered = tuple(world_to_layer_local(field, layer.index, vertex) for vertex in layer.vertices)
        for actual, wanted in zip(recovered, expected, strict=True):
            assert actual == pytest.approx(wanted, abs=3e-11)


def test_token_path_is_tangent_axis_and_key_region_is_behind_it() -> None:
    path = (
        WeightedTokenPoint("a", 1.0, (0.0, 0.0, 0.0)),
        WeightedTokenPoint("b", 1.0, (1.0, 0.0, 0.0)),
        WeightedTokenPoint("c", 1.0, (2.0, 0.0, 0.0)),
    )
    spec = NestedWeightFieldSpec(key_depth=0.25)
    field = build_nested_weight_token_field(path, field_seed="axis", spec=spec)

    assert field.tangent_axis == pytest.approx((1.0, 0.0, 0.0), abs=1e-12)
    offset = tuple(anchor - center for anchor, center in zip(field.key_anchor, field.path_centroid, strict=True))
    assert math.sqrt(sum(value * value for value in offset)) == pytest.approx(0.25)
    assert sum(a * b for a, b in zip(offset, field.tangent_axis, strict=True)) == pytest.approx(0.0)


def test_replay_is_deterministic_but_path_and_seed_changes_are_visible() -> None:
    first = build_nested_weight_token_field(sample_path(), field_seed="same")
    replay = build_nested_weight_token_field(sample_path(), field_seed="same")
    changed_weight = build_nested_weight_token_field(sample_path(middle_weight=-0.5), field_seed="same")
    changed_seed = build_nested_weight_token_field(sample_path(), field_seed="different")

    assert first == replay
    assert first.receipt_sha256 != changed_weight.receipt_sha256
    assert first.receipt_sha256 != changed_seed.receipt_sha256
    assert first.token_ids == changed_weight.token_ids == changed_seed.token_ids
    assert first.token_path_sha256 != changed_weight.token_path_sha256
    assert first.token_path_sha256 == changed_seed.token_path_sha256
    assert first.receipt_is_valid()
    assert not replace(first, common_growth_ratio=first.common_growth_ratio + 0.001).receipt_is_valid()


def test_weight_magnitude_grows_while_weight_sign_orients() -> None:
    negative = build_nested_weight_token_field(sample_path(middle_weight=-0.75), field_seed="weight-channels")
    positive = build_nested_weight_token_field(sample_path(middle_weight=0.75), field_seed="weight-channels")

    assert negative.path_energy == positive.path_energy
    assert negative.common_growth_ratio == positive.common_growth_ratio
    assert tuple(layer.side for layer in negative.layers) == tuple(layer.side for layer in positive.layers)
    assert negative.rotation_radians != positive.rotation_radians
    assert negative.receipt_sha256 != positive.receipt_sha256


def test_growth_power_changes_size_without_changing_nested_ratio() -> None:
    linear = build_nested_weight_token_field(
        sample_path(),
        field_seed="power",
        spec=NestedWeightFieldSpec(growth_power=1.0),
    )
    powered = build_nested_weight_token_field(
        sample_path(),
        field_seed="power",
        spec=NestedWeightFieldSpec(growth_power=3.0),
    )

    assert linear.common_growth_ratio != powered.common_growth_ratio
    assert ratios_are_preserved(linear)
    assert ratios_are_preserved(powered)


@pytest.mark.parametrize(
    ("path", "seed", "spec", "message"),
    [
        ((), "x", NestedWeightFieldSpec(), "at least two"),
        (
            (
                WeightedTokenPoint("a", 1.0, (0.0, 0.0, 0.0)),
                WeightedTokenPoint("b", 1.0, (0.0, 0.0, 0.0)),
            ),
            "x",
            NestedWeightFieldSpec(),
            "distinct coordinates",
        ),
        (
            (
                WeightedTokenPoint("a", 0.0, (0.0, 0.0, 0.0)),
                WeightedTokenPoint("b", 0.0, (1.0, 0.0, 0.0)),
            ),
            "x",
            NestedWeightFieldSpec(),
            "non-zero weight",
        ),
        (sample_path(), "", NestedWeightFieldSpec(), "must not be empty"),
    ],
)
def test_invalid_or_degenerate_fields_fail_closed(path, seed, spec, message) -> None:
    with pytest.raises(NestedWeightFieldError, match=message):
        build_nested_weight_token_field(path, field_seed=seed, spec=spec)


def test_source_states_that_geometry_is_not_secret_entropy() -> None:
    source = (
        Path(__file__)
        .resolve()
        .parents[2]
        .joinpath("python", "scbe", "nested_weight_token_field.py")
        .read_text(encoding="utf-8")
    )
    assert "not a cryptographic primitive" in source
    assert "add no secret entropy" in source
    assert "signature or key-exchange protocol" in source
