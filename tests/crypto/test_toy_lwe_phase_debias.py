"""Exact tests for the complete-orbit phase coverage correction."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from src.crypto import toy_lwe_phase_debias as D
from src.crypto import toy_lwe_phase_search as P


def test_mod_three_phase_action_is_bijective_and_closes_after_twelve_steps() -> None:
    field = [D._decode_balanced(index, 4) for index in range(3**4)]
    for step in range(12):
        images = {D.rotate_phase_mod3(candidate, step) for candidate in field}
        assert len(images) == len(field)
    assert all(D.rotate_phase_mod3(candidate, 12) == candidate for candidate in field)


def test_phase_orbits_partition_the_complete_toy_field() -> None:
    orbits = D.phase_orbits(8)
    flattened = [candidate for orbit in orbits for candidate in orbit]
    assert len(flattened) == len(set(flattened)) == 3**8
    assert {len(orbit) for orbit in orbits} == {1, 4, 12}


def test_default_cover_removes_legacy_projection_and_prefix_imbalance() -> None:
    corrected = D.phase_orbit_cover_candidates(8)
    corrected_stats = D.orbit_cover_stats(corrected)
    legacy_stats = D.orbit_cover_stats(P.phase_wheel_candidates(8))
    assert len(corrected.candidates) == len(set(corrected.candidates)) == 360
    assert corrected_stats.complete_phase_orbit_members == 360
    assert corrected_stats.radius_one_covered == 4906
    assert corrected_stats.nearest_distance_sum == 7857
    assert corrected_stats.max_coordinate_discrepancy_scaled_by_three == 6
    assert corrected_stats.max_pair_cell_discrepancy_scaled_by_nine == 36
    assert corrected_stats.nearest_distance_sum < legacy_stats.nearest_distance_sum
    assert (
        corrected_stats.max_coordinate_discrepancy_scaled_by_three
        < legacy_stats.max_coordinate_discrepancy_scaled_by_three
    )
    assert (
        corrected_stats.max_pair_cell_discrepancy_scaled_by_nine < legacy_stats.max_pair_cell_discrepancy_scaled_by_nine
    )


def test_cover_translation_preserves_exact_torus_coverage() -> None:
    anchor = (-1, 0, 1, -1, 0, 1, -1, 0)
    origin = D.phase_orbit_cover_candidates(8, count=120)
    shifted = D.phase_orbit_cover_candidates(8, count=120, anchor=anchor)
    assert shifted.candidates == tuple(P.move_on_trit_torus(anchor, value) for value in origin.candidates)
    assert D.orbit_cover_stats(shifted).nearest_distance_sum == D.orbit_cover_stats(origin).nearest_distance_sum


def test_partial_cover_is_unique_and_exactly_bounded() -> None:
    cover = D.phase_orbit_cover_candidates(4, count=30)
    assert len(cover.candidates) == len(set(cover.candidates)) == 30
    assert cover.proposals == 3**4 * 12
    assert cover.duplicate_proposals == cover.proposals - 3**4


def test_debias_core_contains_no_floating_point_constants() -> None:
    tree = ast.parse(Path(D.__file__).read_text(encoding="utf-8"))
    floats = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, float)]
    assert floats == []


@pytest.mark.parametrize(
    "call",
    [
        lambda: D.phase_orbit_cover_candidates(3, count=10),
        lambda: D.phase_orbit_cover_candidates(12, count=10),
        lambda: D.phase_orbit_cover_candidates(4, count=82),
        lambda: D.rotate_phase_mod3((0, 0, 0, 2), 1),
    ],
)
def test_invalid_or_unbounded_phase_cover_inputs_are_rejected(call) -> None:
    with pytest.raises(ValueError):
        call()
