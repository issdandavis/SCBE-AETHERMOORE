"""Tests for squad_bench -- the offline benchmark, after the self-audit replaced the strawman lift.

Pins the HONEST instruments: (1) coverage-union does NOT measure differentiation -- a DOMINO clone leaves ~0
gap, exposing the strawman; (2) the RIGHT instrument is exact TILING at matched area, where a domino-only
clone fails a parity wall a domino+monomino set clears (re-verified); (3) the energy benchmark is a
forward-checking TAUTOLOGY among solved boards (disclosed), not an empirical Landauer distribution.
"""

from __future__ import annotations

from python.helm.squad_bench import run_bench, run_energy, run_reach, run_tiling


def test_benchmark_is_reproducible_same_seed_same_numbers():
    assert run_bench(40, 40, 7) == run_bench(40, 40, 7)  # seeded -> identical


def test_reach_is_a_single_shape_fact_not_differentiation():
    # the strawman exposed: the 2x2 SQUARE has a real reach deficit, but a DOMINO reaches ~everything, so
    # coverage-union cannot be a differentiation metric (any all-reaching shape saturates it).
    rc = run_reach(150, seed=7)
    assert rc["square_deficit"] > 0.2  # the 2x2 frame genuinely starves on thin/branchy regions
    assert rc["domino_deficit"] < 0.02  # ...but a single domino reaches nearly all cells
    # so the old "differentiation lift" (square vs differentiated) was measuring the square's deficit, not diversity


def test_tiling_is_the_right_instrument_diversity_beats_a_parity_wall():
    ti = run_tiling()
    assert ti["clone_fails_all"]  # a domino-only roster cannot tile the parity-obstructed regions
    assert ti["diff_tiles_all_verified"]  # domino+monomino (same area) tiles them, independently re-verified
    # this is differentiation genuinely load-bearing, at matched area -- the honest claim


def test_energy_among_solved_is_a_forward_checking_tautology():
    # honest disclosure: forward-checking makes a SOLVED board forward-only by construction, so 0 J among
    # solved is structural, not measured. Energy appears only on unsolvable boards (the solver flailing).
    en = run_energy(150, seed=7)
    assert en["solved_with_nonzero_energy"] == 0  # the tautology, stated as such
    assert en["energy_is_structural_not_measured"] is True
    assert en["solved_rate"] > 0.0


def test_run_bench_structure():
    b = run_bench(20, 20, 3)
    assert b["benchmark"] == "squad-offline"
    assert set(b) == {"benchmark", "seed", "reach", "tiling", "energy"}
