"""Tests for the shadow-mode Kaprekar mirror topology."""

from __future__ import annotations

import math

import pytest

from src.training.kaprekar_mirror_topology import KaprekarMirrorTopology

pytestmark = pytest.mark.unit


@pytest.fixture
def topology() -> KaprekarMirrorTopology:
    return KaprekarMirrorTopology()


def test_known_kaprekar_path_reaches_6174_at_depth_three(
    topology: KaprekarMirrorTopology,
) -> None:
    trace = topology.trace("3524")

    assert trace.path == ("3524", "3087", "8352", "6174")
    assert trace.cycle == ("6174",)
    assert trace.depth == 3
    assert trace.is_fixed_point


def test_mirror_realm_is_conjugate_and_bottoms_at_4716(
    topology: KaprekarMirrorTopology,
) -> None:
    pair = topology.pair("3524")

    assert pair.mirror_state == "4253"
    assert pair.mirror_trace.path == tuple(topology.mirror(state) for state in pair.primary_trace.path)
    assert pair.primary_bottom == "6174"
    assert pair.mirror_bottom == "4716"
    assert pair.primary_trace.depth == pair.mirror_trace.depth == 3
    assert topology.mirror_step("4716") == "4716"


def test_palindrome_envelope_contains_state_and_mirror(
    topology: KaprekarMirrorTopology,
) -> None:
    envelope = topology.palindrome("6174")

    assert envelope == "61744716"
    assert envelope == envelope[::-1]
    assert envelope[: topology.width] == "6174"
    assert envelope[topology.width :] == "4716"


def test_mirror_is_an_involution(topology: KaprekarMirrorTopology) -> None:
    for state in ("0001", "1221", "3524", "6174", "9990"):
        assert topology.mirror(topology.mirror(state)) == state


def test_palindromic_states_lie_on_the_mirror_seam(
    topology: KaprekarMirrorTopology,
) -> None:
    pair = topology.pair("1221")

    assert pair.is_mirror_seam
    assert pair.primary_point == pair.mirror_point
    assert pair.primary_point[2] == 0.0


def test_non_seam_points_reflect_across_lateral_and_realm_axes(
    topology: KaprekarMirrorTopology,
) -> None:
    pair = topology.pair("3524")
    px, py, pz = pair.primary_point
    mx, my, mz = pair.mirror_point

    assert mx == pytest.approx(px)
    assert my == pytest.approx(-py)
    assert mz == pytest.approx(-pz)


def test_all_points_stay_inside_unit_ball(topology: KaprekarMirrorTopology) -> None:
    for value in range(10_000):
        pair = topology.pair(value)
        for point in (pair.primary_point, pair.mirror_point):
            assert math.sqrt(sum(component * component for component in point)) < 1.0


def test_all_four_digit_non_repdigits_reach_6174_within_seven_steps(
    topology: KaprekarMirrorTopology,
) -> None:
    depths: list[int] = []

    for value in range(10_000):
        state = topology.normalize(value)
        if len(set(state)) == 1:
            continue
        trace = topology.trace(state)
        assert trace.cycle == ("6174",)
        depths.append(trace.depth)

    assert len(depths) == 9_990
    assert max(depths) == 7


def test_repdigits_use_the_separate_zero_basin(
    topology: KaprekarMirrorTopology,
) -> None:
    for digit in "0123456789":
        trace = topology.trace(digit * topology.width)
        assert trace.cycle == ("0000",)


def test_map_is_many_to_one_and_not_an_exact_codec(
    topology: KaprekarMirrorTopology,
) -> None:
    assert topology.kaprekar_step("3524") == topology.kaprekar_step("4253")


def test_radial_depth_increases_monotonically(topology: KaprekarMirrorTopology) -> None:
    radii = [topology.radial_depth(depth) for depth in range(8)]

    assert radii[0] == 0.0
    assert all(left < right for left, right in zip(radii, radii[1:]))
    assert radii[-1] < topology.max_planar_radius


@pytest.mark.parametrize(
    ("value", "error"),
    [
        (-1, ValueError),
        (10_000, ValueError),
        ("12x4", ValueError),
        ("12345", ValueError),
        (True, TypeError),
    ],
)
def test_invalid_states_are_rejected(
    topology: KaprekarMirrorTopology,
    value: int | str,
    error: type[Exception],
) -> None:
    with pytest.raises(error):
        topology.normalize(value)
