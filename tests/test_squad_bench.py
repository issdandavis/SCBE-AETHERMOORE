"""Tests for squad_bench -- the offline, deterministic benchmark of the squad's differentiation claim.

The benchmark's own run already self-verifies (coverage vs holes must agree; energy metering must reproduce
via an independent solve_energy). These pin the load-bearing benchmark properties: it is reproducible
(seeded), the differentiation LIFT is real and positive, and solvable region-agree boards are forward-only
(0 J -- the cost is only in the erasures).
"""

from __future__ import annotations

from python.helm.squad_bench import run_bench, run_coverage, run_energy


def test_benchmark_is_reproducible_same_seed_same_numbers():
    assert run_bench(40, 40, 7) == run_bench(40, 40, 7)  # seeded -> identical (the whole point)


def test_differentiation_lift_is_real_and_positive():
    cov = run_coverage(120, seed=7)
    assert cov["coverage_lift"] > 0.1  # a differentiated squad covers materially more than a clone
    assert cov["diff_coverage_avg"] > cov["clone_coverage_avg"]
    assert cov["diff_fully_covered_rate"] > cov["clone_fully_covered_rate"]


def test_energy_solved_boards_are_forward_only_free():
    # the honest finding: solvable region-agree boards solve without CBJ jump-backs -> 0 erasures, 0 J.
    e = run_energy(120, seed=7)
    assert e["solved_rate"] > 0.5
    assert e["conflict_free_rate_of_solved"] == 1.0  # every solved board was forward-only (free)
    assert e["median_overwrites_solved"] == 0.0


def test_run_bench_structure():
    b = run_bench(20, 20, 3)
    assert b["benchmark"] == "squad-offline"
    assert set(b) == {"benchmark", "seed", "coverage", "energy"}
    assert b["coverage"]["tasks"] == 20 and b["energy"]["tasks"] == 20
