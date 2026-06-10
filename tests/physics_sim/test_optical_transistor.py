#!/usr/bin/env python3
"""Gate for the synchronous-pump optical-transistor model.

Spec: docs/superpowers/specs/2026-06-09-synchronous-pump-optical-transistor-spec.md

Asserts the qualitative results the model is supposed to produce, with small
ensembles/grids so the suite stays fast (the full report at production sizes runs
~2 min; here we use coarse grids that still exercise every claim):

  * averaged map is bistable with a restoring contraction |f'(P*)| < 1;
  * the time-domain model REDUCES to the averaged one as rho -> inf (the anchor);
  * Probe 1: bistability requires rho >~ 1 (gain must survive between pulses);
  * Probe 2: far from the edge the cascade shrugs off the spontaneous floor, but
    NEAR the lasing edge a large enough floor flips bits (the falsification);
  * all four null gates bite (no absorber / scrambled phase / severed reservoir /
    randomized pump timing).
"""

from __future__ import annotations

import os
import sys
from dataclasses import replace

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from physics_sim import optical_transistor as ot  # noqa: E402


def test_averaged_map_is_bistable_and_restoring():
    fp = ot.find_fixed_points(ot.DEFAULT)
    assert fp["bistable"]
    assert fp["P_star"] > fp["P_threshold"] > 0.0
    assert abs(fp["contraction"]) < 1.0  # the '1' is a contracting (restoring) fixed point


def test_anchor_time_domain_reduces_to_averaged():
    """rho -> inf, beta -> 0 must reproduce the averaged fixed point."""
    a = ot.reduces_to_averaged()
    assert a["passes"], a
    assert a["rel_error"] < 0.05


def test_cascade_restores_through_noise_when_far_from_edge():
    s = ot.cascade_survival(ot.DEFAULT, n_stages=120, noise=0.20, n_traj=30, beta=0.0, seed=1)
    assert s["survival"] == 1.0


def test_probe1_bistability_needs_gain_recovery():
    """Pre-registered prediction: bistable at large rho, lost at small rho."""
    assert ot.simulate_synchronous_pump(rho=50.0, n_rt=600)["bistable"] is True
    assert ot.simulate_synchronous_pump(rho=0.3, n_rt=600)["bistable"] is False
    # recovery factor is the mechanism: ->1 at large rho, ->0 at small rho
    assert ot.recovery(100.0) > 0.98
    assert ot.recovery(0.1) < 0.15


def test_probe2_spontaneous_floor_breaks_cascade_near_edge():
    near = replace(ot.DEFAULT, g0=0.30)  # thin margin (P_t/P* ~ 0.23)
    clean = ot.cascade_survival(near, n_stages=100, noise=0.05, n_traj=40, beta=0.0, seed=2)
    floored = ot.cascade_survival(near, n_stages=100, noise=0.05, n_traj=40, beta=0.5, seed=2)
    assert clean["survival"] >= 0.95  # noiseless-ish: cascade holds
    assert floored["survival"] < 0.5  # strong spontaneous floor flips bits
    assert floored["survival"] < clean["survival"]


def test_null_no_absorber_is_not_bistable():
    assert ot.null_no_absorber()["passes"]  # remove saturable absorber -> linear amp


def test_null_scrambled_phase_collapses_gain():
    r = ot.null_scrambled_phase()
    assert r["passes"]
    assert r["collapse_ratio"] > 2.0  # coherent injection >> scrambled


def test_null_severed_reservoir_extinction():
    r = ot.null_severed_reservoir()
    assert r["passes"]
    assert r["extinction_shared"] > 5.0  # gate starves signal through shared gain
    assert abs(r["extinction_severed"] - 1.0) < 0.1  # severed -> coupling is gone


def test_null_random_timing_collapses_gating():
    """Synchronous pumping is load-bearing: jittered timing must kill the '1'."""
    assert ot.null_random_timing()["passes"]


def test_locking_window_exists_and_is_bounded_by_K():
    lw = ot.locking_window()
    assert 0.0 < lw["locked_window_edge"] <= lw["K"]


def test_material_regimes_classify_against_model_edges():
    """The self-reported grounding must put each cited material on the right side
    of the model's own edges (spec §8): inorganic clears beta, organic sits at it,
    long-cavity is the only rho-bound architecture."""
    mr = ot.material_regimes(rho_crit=1.47, beta_ceiling=0.1)  # edges passed in -> fast
    by = {r["name"]: r for r in mr["regimes"]}

    assert by["inorganic_gaas_microcavity"]["beta_pass"] is True  # beta ~1e-4 << ceiling
    assert "BOTH" in by["inorganic_gaas_microcavity"]["overall"]

    assert by["organic_microcavity"]["beta_pass"] is False  # high-beta room-temp tax
    assert "beta edge" in by["organic_microcavity"]["overall"]

    # microcavities are never rho-limited; only the long-cavity regime binds at rho_crit
    assert "NOT rho-limited" in by["organic_microcavity"]["rho_verdict"]
    assert by["long_cavity_soa_fiber_logic"]["beta_range"] is None
    assert "rho_crit" in by["long_cavity_soa_fiber_logic"]["rho_verdict"]
