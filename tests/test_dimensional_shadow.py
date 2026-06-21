"""Tests for dimensional_shadow -- the tangled-low -> compressed-high -> low-is-the-shadow claim, and the
scale-invariant 'wave' (same process every realm).
"""

from __future__ import annotations

from python.scbe.dimensional_shadow import best_axis_split, lift, linear_2d_separability, rings, shadow, sweep, wave


def test_rings_are_askew_to_2d():
    pts, labels = rings()
    # no straight line separates concentric rings -- you are 'askew to your own dimension'
    assert linear_2d_separability(pts, labels) < 0.8


def test_lift_compresses_the_boundary_to_one_parameter():
    pts, labels = rings()
    z = [p[2] for p in lift(pts, 1.0)]
    acc, _ = best_axis_split(z, labels)
    assert acc >= 0.98  # one flat plane (a single number) separates them in the lifted dimension


def test_lower_dimension_is_the_exact_shadow():
    pts, labels = rings()
    lifted = lift(pts, 0.6)
    recovered = shadow(lifted)
    assert all(abs(a[0] - b[0]) < 1e-12 and abs(a[1] - b[1]) < 1e-12 for a, b in zip(recovered, pts))


def test_sweep_shows_compression_as_dimension_rises():
    rows = sweep([0.0, 1.0])
    flat, lifted = rows[0], rows[-1]
    assert flat["one_plane_accuracy"] < 0.7 and flat["boundary_params"] == 3  # tangled at lam=0
    assert lifted["one_plane_accuracy"] >= 0.98 and lifted["boundary_params"] == 1  # compressed when lifted
    assert all(r["shadow_recovers_2d"] for r in rows)


def test_wave_is_scale_invariant():
    # the SAME operator gives the SAME 1-parameter compressed boundary at every scale -> process is fixed
    rows = wave([1.0, 10.0, 100.0, 1000.0])
    assert all(r["one_plane_accuracy"] >= 0.98 and r["boundary_params"] == 1 for r in rows)
