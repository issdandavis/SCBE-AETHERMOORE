"""Tests for the optical-transistor iterated-map model (src/physics_sim).

Covers the three physics pieces (bistable round-trip map, Adler locking
window, multi-beam gain competition), the triple cascadability figure of
merit, and the null gates that must fail when the physics is removed.
"""

import math

import pytest

from src.physics_sim.optical_transistor import (
    AdlerConfig,
    CavityConfig,
    MultiBeamConfig,
    evaluate_transistor,
    find_fixed_points,
    gate_extinction_ratio,
    integrate_adler,
    is_bistable,
    iterate_cascade,
    locking_window,
    run_null_gates,
)

# ---------------------------------------------------------------------------
# 1. Round-trip map: bistability and restoration
# ---------------------------------------------------------------------------


def test_default_cavity_is_bistable():
    """The default cavity has stable 0, stable high state, unstable threshold."""
    cfg = CavityConfig()
    pts = find_fixed_points(cfg)
    stable = sorted(p.power for p in pts if p.stable)
    unstable = sorted(p.power for p in pts if not p.stable)
    assert is_bistable(cfg)
    assert stable[0] == 0.0
    assert len(stable) >= 2
    assert unstable, "an unstable threshold must separate the basins"
    assert stable[0] < unstable[0] < stable[-1]


def test_high_fixed_point_is_contracting():
    """Restoration criterion: |f'(P*)| < 1 at the high stable point."""
    cfg = CavityConfig()
    high = max((p for p in find_fixed_points(cfg) if p.stable), key=lambda p: p.power)
    assert high.power > 1.0
    assert abs(high.derivative) < 1.0


def test_below_threshold_decays_above_threshold_latches():
    """Inputs below the threshold fall to 0; above it they latch to P*."""
    cfg = CavityConfig()
    pts = find_fixed_points(cfg)
    threshold = min(p.power for p in pts if not p.stable and p.power > 0)
    high = max(p.power for p in pts if p.stable)

    low_run = iterate_cascade(0.5 * threshold, cfg, n_stages=200)
    high_run = iterate_cascade(2.0 * threshold, cfg, n_stages=200)
    assert low_run[-1] < 1e-6
    assert high_run[-1] == pytest.approx(high, rel=1e-3)


def test_cascade_regenerates_noisy_logic_levels():
    """20% multiplicative noise per stage still converges to the clean level."""
    cfg = CavityConfig()
    high = max(p.power for p in find_fixed_points(cfg) if p.stable)
    run = iterate_cascade(high, cfg, n_stages=300, noise_amplitude=0.2)
    tail = run[-50:]
    assert all(abs(p - high) / high < 0.5 for p in tail)
    assert sum(tail) / len(tail) == pytest.approx(high, rel=0.2)


# ---------------------------------------------------------------------------
# 2. Adler equation: the locking window
# ---------------------------------------------------------------------------


def test_locking_window_boundary_is_K():
    """Locks iff |detuning| < K, with the boundary at the Adler bandwidth."""
    window = locking_window(locking_bandwidth=1.0, detunings=[0.0, 0.5, 0.9, 1.1, 2.0, -0.5, -1.5])
    assert window[0.0] and window[0.5] and window[0.9] and window[-0.5]
    assert not window[1.1] and not window[2.0] and not window[-1.5]


def test_locked_drive_transfers_energy():
    """Inside the window the mean cos(dphi) settles to sqrt(1-(dw/K)^2)."""
    res = integrate_adler(AdlerConfig(locking_bandwidth=1.0, detuning=0.6))
    assert res.locked
    assert res.mean_energy_transfer == pytest.approx(math.sqrt(1 - 0.6**2), abs=0.02)


def test_scrambled_drive_transfers_nothing():
    """Phase scrambling kills the mean energy transfer (the 939x lesson)."""
    coherent = integrate_adler(AdlerConfig(locking_bandwidth=1.0, detuning=0.3))
    scrambled = integrate_adler(AdlerConfig(locking_bandwidth=1.0, detuning=0.3, scramble_phase=True))
    assert abs(coherent.mean_energy_transfer) > 0.9
    assert abs(scrambled.mean_energy_transfer) < 0.1


# ---------------------------------------------------------------------------
# 3. Multi-beam: gain competition / transistor action
# ---------------------------------------------------------------------------


def test_gate_beam_switches_signal_through_shared_gain():
    """With one shared reservoir the gate beam suppresses the signal."""
    ratio = gate_extinction_ratio(MultiBeamConfig())
    assert ratio > 5.0


def test_severed_reservoir_makes_gate_decorative():
    """Without shared gain (and kappa=0) the gate cannot touch the signal."""
    ratio = gate_extinction_ratio(MultiBeamConfig(shared_reservoir=False))
    assert ratio == pytest.approx(1.0, abs=0.2)


# ---------------------------------------------------------------------------
# 4. Figure of merit and null gates
# ---------------------------------------------------------------------------


def test_default_cavity_passes_triple_figure_of_merit():
    """G >= 1, fan-out >= 2, and contraction < 1 hold simultaneously."""
    verdict = evaluate_transistor(CavityConfig())
    assert verdict.gain_above_unity
    assert verdict.fan_out >= 2
    assert verdict.contraction < 1.0
    assert verdict.cascadable


def test_linear_amp_fails_figure_of_merit():
    """A cavity without absorber saturation is not cascadable."""
    cfg = CavityConfig(sat_power_absorber=float("inf"))
    verdict = evaluate_transistor(cfg)
    assert not verdict.bistable
    assert not verdict.cascadable


def test_all_null_gates_pass():
    """Every effect collapses when its load-bearing physics is removed."""
    reports = run_null_gates()
    by_name = {r.name: r for r in reports}
    assert set(by_name) == {"saturable_absorber", "phase_coherence", "shared_gain_reservoir"}
    for report in reports:
        assert report.passed, f"null gate failed: {report.name} (ratio={report.collapse_ratio:.2f})"


def test_null_gate_collapse_is_large_not_marginal():
    """The coherent/scrambled transfer ratio is decisive, not borderline."""
    by_name = {r.name: r for r in run_null_gates()}
    assert by_name["phase_coherence"].collapse_ratio > 10.0
    assert by_name["shared_gain_reservoir"].collapse_ratio > 10.0
