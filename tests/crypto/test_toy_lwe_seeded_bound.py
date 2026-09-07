"""Correctness and accounting tests for geometry-seeded exact bounds."""

from __future__ import annotations

import pytest

from src.crypto import toy_lwe_box_field as B
from src.crypto import toy_lwe_phase_debias as D
from src.crypto import toy_lwe_seeded_bound as S


@pytest.mark.parametrize("seed", range(8))
def test_seeded_interval_search_remains_exact(seed: int) -> None:
    instance = B.generate_toy_lwe(seed, dimension=4, samples=7, modulus=31)
    truth = B.exhaustive_search(instance)
    cover = D.phase_orbit_cover_candidates(4, count=12)
    result = S.seeded_box_field_search(instance, cover.candidates)
    assert (result.score, result.candidate) == (truth.score, truth.candidate)
    assert result.total_objective_evaluations == (
        result.initial_unique_evaluations + result.post_seed_objective_evaluations
    )


def test_empty_seed_set_matches_bound_only_search_count() -> None:
    instance = B.generate_toy_lwe(91, dimension=5, samples=8, modulus=31)
    baseline = B.box_field_search(instance, strategy="bound-only")
    seeded = S.seeded_box_field_search(instance, ())
    assert (seeded.score, seeded.candidate) == (baseline.score, baseline.candidate)
    assert seeded.total_objective_evaluations == baseline.evaluated_candidates


def test_duplicate_initial_candidates_are_charged_once() -> None:
    instance = B.generate_toy_lwe(9, dimension=4, samples=7, modulus=31)
    result = S.seeded_box_field_search(instance, [(0, 0, 0, 0)] * 4)
    assert result.initial_unique_evaluations == 1


@pytest.mark.parametrize("candidate", [(0, 0), (0, 0, 0, 2), (0, 0, 0, True)])
def test_invalid_initial_candidates_fail_closed(candidate) -> None:
    instance = B.generate_toy_lwe(3, dimension=4, samples=7, modulus=31)
    with pytest.raises(ValueError):
        S.seeded_box_field_search(instance, [candidate])
