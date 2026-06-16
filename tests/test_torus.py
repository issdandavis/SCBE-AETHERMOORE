"""Torus / hypercube embedding — periodic floating-point space + wormhole seams."""
import math

from python.scbe import torus as T


def test_torus_points_lie_on_unit_circles():
    for b in range(0, 64, 7):
        pt = T.to_torus(b)
        assert len(pt) == 2 * len(T.AXES)
        for i in range(0, len(pt), 2):           # each (cos, sin) pair is unit length
            assert abs(pt[i] ** 2 + pt[i + 1] ** 2 - 1.0) < 1e-9


def test_distance_is_symmetric_and_zero_on_self():
    for a in (0x00, 0x2A, 0x3F):
        assert T.torus_distance(a, a) == 0.0
        for b in (0x05, 0x11, 0x28):
            assert abs(T.torus_distance(a, b) - T.torus_distance(b, a)) < 1e-12


def test_wrap_is_the_short_way_round():
    # col 15 and col 0 are adjacent across the seam, not 15 apart
    d_wrap = T.torus_distance(0x0F, 0x00, ("lo",))
    d_step = T.torus_distance(0x00, 0x01, ("lo",))
    assert abs(d_wrap - d_step) < 1e-9           # 15->0 is one step, like 0->1
    assert T.is_wormhole(0x0F, 0x00)             # genuinely closer than the flat way


def test_hypercube_neighbors_are_one_bit_flips():
    nb = T.hypercube_neighbors(0x00)
    assert len(nb) == 6
    assert all(T.hamming(0x00, n) == 1 for n in nb)
    # flipping the band bit jumps to another plane (arithmetic 0x0_ -> comparison 0x2_)
    assert (0x00 ^ 0x20) in nb and ((0x00 ^ 0x20) >> 4) == 2


def test_no_false_wormhole_for_adjacent_cells():
    assert not T.is_wormhole(0x00, 0x01)         # neighbours already; wrap gains nothing
