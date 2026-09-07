"""Correctness and accounting tests for the bounded phase/torus probe."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from src.crypto import toy_lwe_box_field as B
from src.crypto import toy_lwe_phase_search as P


def test_existing_dual_trit_state_space_is_reused_completely() -> None:
    assert len(P.DUAL_TRIT_STATES) == 9
    assert set(P.DUAL_TRIT_STATES) == {(left, right) for left in P.TRITS for right in P.TRITS}


def test_phase_wheel_has_360_unique_integer_points_and_is_deterministic() -> None:
    first = P.phase_wheel_candidates(8)
    second = P.phase_wheel_candidates(8)
    assert first == second
    assert len(first.candidates) == len(set(first.candidates)) == 360
    assert first.proposals >= 360
    assert first.duplicate_proposals == first.proposals - 360
    assert all(all(type(value) is int and value in P.TRITS for value in candidate) for candidate in first.candidates)


def test_phase_wheel_can_translate_around_an_arbitrary_torus_intercept() -> None:
    origin = P.phase_wheel_candidates(8, count=120)
    anchor = (-1, 0, 1, -1, 0, 1, -1, 0)
    shifted = P.phase_wheel_candidates(8, count=120, anchor=anchor)
    expected = tuple(P.move_on_trit_torus(anchor, direction) for direction in origin.candidates)
    assert shifted.candidates == expected
    assert len(set(shifted.candidates)) == 120


def test_small_spaces_fill_without_claiming_360_distinct_angles() -> None:
    batch = P.phase_wheel_candidates(3, count=27)
    assert len(set(batch.candidates)) == 27
    assert batch.proposals > 27


def test_balanced_trit_torus_is_an_exact_three_cycle() -> None:
    for start in P.TRITS:
        first = P.balanced_trit_wrap(start + 1)
        second = P.balanced_trit_wrap(first + 1)
        third = P.balanced_trit_wrap(second + 1)
        assert third == start


def test_torus_hypercube_has_two_one_coordinate_neighbors_per_axis() -> None:
    candidate = (-1, 0, 1, 0, -1, 1)
    neighbors = P.trit_torus_hypercube_neighbors(candidate)
    assert len(neighbors) == 2 * len(candidate)
    assert len(set(neighbors)) == len(neighbors)
    assert all(P.hamming_distance(candidate, neighbor) == 1 for neighbor in neighbors)
    for index in range(len(candidate)):
        values = {
            neighbor[index]
            for neighbor in neighbors
            if P.hamming_distance(candidate, neighbor) == 1 and neighbor[index] != candidate[index]
        }
        assert values == set(P.TRITS) - {candidate[index]}


def test_random_control_is_unique_deterministic_and_seeded() -> None:
    first = P.random_candidates(8, count=360, seed=91)
    assert first == P.random_candidates(8, count=360, seed=91)
    assert first != P.random_candidates(8, count=360, seed=92)
    assert len(first.candidates) == len(set(first.candidates)) == 360


def test_probe_and_foothold_respect_exact_objective_budget() -> None:
    instance = B.generate_toy_lwe(7, dimension=6, samples=10, modulus=97)
    seeds = P.phase_wheel_candidates(6, count=24)
    probe = P.evaluate_candidates(instance, seeds)
    search = P.foothold_search(instance, seeds, max_evaluations=120)
    assert probe.evaluated_candidates == 24
    assert search.evaluated_candidates == 120
    assert search.candidate_proposals >= 120
    assert search.score == min(score for _, score in search.evaluated)
    assert (search.score, search.candidate) == min((score, candidate) for candidate, score in search.evaluated)


def test_foothold_search_is_deterministic() -> None:
    instance = B.generate_toy_lwe(19, dimension=6, samples=10, modulus=97)
    seeds = P.phase_wheel_candidates(6, count=18)
    assert P.foothold_search(instance, seeds, max_evaluations=90) == P.foothold_search(
        instance, seeds, max_evaluations=90
    )


def test_phase_core_contains_no_floating_point_constants() -> None:
    tree = ast.parse(Path(P.__file__).read_text(encoding="utf-8"))
    floats = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, float)]
    assert floats == []


@pytest.mark.parametrize(
    "call",
    [
        lambda: P.phase_wheel_candidates(0, count=1),
        lambda: P.phase_wheel_candidates(2, count=10),
        lambda: P.random_candidates(2, count=10, seed=1),
        lambda: P.move_on_trit_torus((0, 0), (0, 2)),
    ],
)
def test_invalid_phase_domains_fail_closed(call) -> None:
    with pytest.raises((TypeError, ValueError)):
        call()
