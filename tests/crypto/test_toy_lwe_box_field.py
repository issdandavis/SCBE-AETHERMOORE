"""Correctness tests for the exact-integer toy LWE box-field experiment."""

from __future__ import annotations

import ast
from itertools import product
from pathlib import Path
import random

import pytest

from src.crypto import toy_lwe_box_field as B


def points(box: B.IntegerBox):
    ranges = [range(low, high + 1) for low, high in zip(box.low, box.high, strict=True)]
    return product(*ranges)


def test_centered_residue_is_exact_and_periodic() -> None:
    assert [B.centered_residue(value, 7) for value in range(7)] == [0, 1, 2, 3, -3, -2, -1]
    for value in range(-50, 51):
        assert B.centered_residue(value + 14, 7) == B.centered_residue(value, 7)


def test_interval_mod_distance_matches_exhaustive_integer_points() -> None:
    rng = random.Random(20260907)
    for _ in range(2_000):
        modulus = rng.choice((7, 11, 17, 97))
        low = rng.randint(-300, 300)
        high = rng.randint(low, low + 80)
        target = rng.randint(-300, 300)
        expected = min(abs(B.centered_residue(target - value, modulus)) for value in range(low, high + 1))
        assert B.interval_mod_distance(target, low, high, modulus) == expected


def test_box_bound_never_exceeds_any_candidate_score() -> None:
    rng = random.Random(411)
    for seed in range(30):
        instance = B.generate_toy_lwe(seed, dimension=4, samples=6, modulus=31)
        lows = []
        highs = []
        for _ in range(instance.dimension):
            left = rng.randint(instance.secret_low, instance.secret_high)
            right = rng.randint(left, instance.secret_high)
            lows.append(left)
            highs.append(right)
        box = B.IntegerBox(tuple(lows), tuple(highs))
        bound = B.box_lower_bound(instance, box)
        assert bound <= min(B.exact_score(instance, candidate) for candidate in points(box))


@pytest.mark.parametrize("seed", range(20))
def test_multiscale_and_bound_only_match_exhaustive(seed: int) -> None:
    instance = B.generate_toy_lwe(seed, dimension=7, samples=12, modulus=97)
    expected = B.exhaustive_search(instance)
    for strategy in ("bound-only", "multiscale"):
        actual = B.box_field_search(instance, strategy=strategy)
        assert (actual.score, actual.candidate) == (expected.score, expected.candidate)
        assert actual.evaluated_candidates <= expected.evaluated_candidates
        assert actual.candidate_volume_pruned <= actual.total_candidates


def test_planted_secret_has_its_declared_error_score() -> None:
    instance = B.generate_toy_lwe(91, dimension=8, samples=14, modulus=97)
    assert instance.planted_secret is not None and instance.error is not None
    assert B.exact_score(instance, instance.planted_secret) == sum(value * value for value in instance.error)


def test_pivot_field_uses_four_declared_views() -> None:
    instance = B.generate_toy_lwe(12, dimension=6, samples=10, modulus=97)
    box = B.IntegerBox((-1,) * 6, (1,) * 6)
    field = B.pivot_field(instance, box, bucket_width=4)
    candidates = B._candidate_points(box)
    assert field.near_full_score == min(B.exact_score(instance, point) for point in candidates)
    assert field.far_full_score == max(B.exact_score(instance, point) for point in candidates)
    assert field.near_coarse_score == min(B.coarse_score(instance, point, bucket_width=4) for point in candidates)
    assert field.far_coarse_score == max(B.coarse_score(instance, point, bucket_width=4) for point in candidates)


def test_core_search_module_contains_no_floating_point_constants() -> None:
    tree = ast.parse(Path(B.__file__).read_text(encoding="utf-8"))
    floats = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, float)]
    assert floats == []


@pytest.mark.parametrize(
    "change,match",
    [
        (lambda item: B.ToyLWEInstance(8, item.matrix, item.public, -1, 1), "odd"),
        (lambda item: B.ToyLWEInstance(item.modulus, item.matrix[:-1], item.public, -1, 1), "shapes"),
        (lambda item: B.ToyLWEInstance(item.modulus, item.matrix, item.public, 1, -1), "reversed"),
    ],
)
def test_malformed_instances_fail_closed(change, match: str) -> None:
    instance = B.generate_toy_lwe(1, dimension=3, samples=5)
    with pytest.raises(ValueError, match=match):
        B.box_field_search(change(instance))
