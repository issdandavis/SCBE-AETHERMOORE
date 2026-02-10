# tests/test_aethermoore_patents.py
"""
@file test_aethermoore_patents.py
@module tests
@layer Layer 2, 5, 12, 14
@component Patent Claims Validation Test Suite
@version 1.0.0

Unit tests for 4 patent claims: math correctness, boundary behavior,
determinism, and measurable machine effect.

Author: Issac Davis
"""
import math
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aethermoore_patent_math import (
    harmonic_security_scaling,
    chladni_nodal_constraint,
    derive_modes_from_6d,
    cymatic_voxel_access,
    complementary_control_signals,
    grid_corner_mask,
    octave_transpose,
    choose_octave_n_for_band,
)


# -------------------------
# PATENT 1: Harmonic Scaling
# -------------------------
def test_patent1_example_value_matches_expected_order():
    val = harmonic_security_scaling(6, 1.5)
    assert val == pytest.approx(1.5 ** 36, rel=0, abs=0)
    assert 2_000_000 <= val <= 2_400_000


@pytest.mark.parametrize("d,R", [(0, 1.5), (1, 1.5), (2, 1.1), (10, 1.01)])
def test_patent1_monotone_in_d_for_R_gt_1(d, R):
    v = harmonic_security_scaling(d, R)
    v_next = harmonic_security_scaling(d + 1, R)
    assert v_next >= v


@pytest.mark.parametrize("bad_d", [-1, -10])
def test_patent1_rejects_negative_d(bad_d):
    with pytest.raises(ValueError):
        harmonic_security_scaling(bad_d, 1.5)


@pytest.mark.parametrize("bad_R", [0, -1.0, -10])
def test_patent1_rejects_nonpositive_R(bad_R):
    with pytest.raises(ValueError):
        harmonic_security_scaling(2, bad_R)


# --------------------------------
# PATENT 2: Cymatic Voxel Storage
# --------------------------------
def test_patent2_expression_zero_on_diagonal_for_any_modes():
    for n in [1, 2, 7, 19]:
        for m in [1, 3, 8, 21]:
            v = chladni_nodal_constraint(0.123, 0.123, n, m)
            assert v == pytest.approx(0.0, abs=1e-12)


def test_patent2_degeneracy_when_n_equals_m():
    for x, y in [(0.1, 0.2), (0.33, 0.77), (0.0, 1.0)]:
        v = chladni_nodal_constraint(x, y, 5, 5)
        assert v == pytest.approx(0.0, abs=1e-12)


def test_patent2_derive_modes_is_deterministic_and_bounded():
    vec = [0.1, -2.0, 3.14159, 0.0, 9.9, -0.0001]
    n1, m1 = derive_modes_from_6d(vec, n_max=64)
    n2, m2 = derive_modes_from_6d(vec, n_max=64)
    assert (n1, m1) == (n2, m2)
    assert 1 <= n1 <= 64
    assert 1 <= m1 <= 64
    assert n1 != m1


def test_patent2_access_visible_on_nodal_constraint():
    vec = [1, 2, 3, 4, 5, 6]
    res = cymatic_voxel_access(0.42, 0.42, vec, epsilon=1e-9, payload_value=123.0)
    assert res.visible is True
    assert res.decoded_value == pytest.approx(123.0)


def test_patent2_access_obfuscated_off_nodal_constraint():
    vec = [1, 2, 3, 4, 5, 6]
    res = cymatic_voxel_access(0.42, 0.421, vec, epsilon=1e-12, payload_value=123.0)
    assert res.visible is False
    assert res.decoded_value != pytest.approx(123.0)


# ---------------------------------------
# PATENT 3: Flux Interaction
# ---------------------------------------
def test_patent3_authorized_region_product_is_unity():
    f, g = complementary_control_signals(base=7.5, authorized=True)
    assert f * g == pytest.approx(1.0, rel=0, abs=1e-12)


def test_patent3_unauthorized_region_is_attenuated():
    f, g = complementary_control_signals(base=7.5, authorized=False)
    assert (f * g) < 1e-3


def test_patent3_corner_mask_has_four_unique_corners():
    corners = grid_corner_mask(10, 8)
    assert len(corners) == 4
    assert (0, 0) in corners
    assert (9, 7) in corners


# -----------------------------------------
# PATENT 4: Stellar Pulse
# -----------------------------------------
def test_patent4_octave_transpose_is_exact_power_of_two():
    f_env = 10.0
    assert octave_transpose(f_env, 0) == pytest.approx(10.0)
    assert octave_transpose(f_env, 1) == pytest.approx(20.0)
    assert octave_transpose(f_env, -1) == pytest.approx(5.0)


def test_patent4_choose_n_falls_in_band_when_possible():
    f_env = 7.0
    band = (50.0, 60.0)
    n = choose_octave_n_for_band(f_env, band)
    f_control = octave_transpose(f_env, n)
    assert band[0] <= f_control <= band[1]


def test_patent4_choose_n_minimizes_distance_when_impossible():
    f_env = 7.0
    band = (1.0, 1.1)
    n = choose_octave_n_for_band(f_env, band)
    f_control = octave_transpose(f_env, n)

    def dist_to_band(f: float) -> float:
        low, high = band
        if f < low:
            return low - f
        if f > high:
            return f - high
        return 0.0

    d0 = dist_to_band(f_control)
    d_minus = dist_to_band(octave_transpose(f_env, n - 1))
    d_plus = dist_to_band(octave_transpose(f_env, n + 1))
    assert d0 <= d_minus + 1e-12
    assert d0 <= d_plus + 1e-12
