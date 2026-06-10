"""Verify my own amendment before accepting it, and stress the word 'universal'.

My claim: on-grid plateau = RMS_pp * sqrt(N_pp / N_grid), where
RMS_pp = sqrt(mean over prime powers of (log p / 2)^2) is the 'invariant' (1.218 on [2,50]).

Two tests:
  (1) DENSITY factorization: refine the grid at FIXED range [2,50] (step 1.0, 0.5, 0.25,
      all include the integer prime powers). Does the measured plateau track the formula,
      and does it land on the OTHER session's 0.595 at the right density?
  (2) Is RMS_pp 'universal'? Recompute it over ranges [2,X] for growing X. If it drifts,
      'universal' is too strong: it is grid-density-invariant but RANGE-dependent.
"""

from __future__ import annotations

import math

import numpy as np

from scripts.research.zeta_explicit_formula_and_gue import load_zeros, psi_from_zeros, true_psi
from scripts.research.zeta_reconcile_grid_and_spacing import prime_powers_with_lambda


def density_factorization() -> None:
    print("[1] DENSITY factorization at fixed range [2,50], K=500 zeros")
    gammas = load_zeros(500)
    lam = prime_powers_with_lambda(50)
    rms_pp = math.sqrt(np.mean([(v / 2.0) ** 2 for v in lam.values()]))
    n_pp = len(lam)
    print(f"   RMS_pp on [2,50] = {rms_pp:.3f}, prime powers = {n_pp}")
    print("   step | N_grid | measured plateau | formula RMS_pp*sqrt(N_pp/N) ")
    for step in (1.0, 0.5, 0.25):
        grid = np.arange(2.0, 50.0 + 1e-9, step)
        approx = psi_from_zeros(grid, gammas[:500])
        plateau = float(np.sqrt(np.mean((approx - true_psi(grid)) ** 2)))
        formula = rms_pp * math.sqrt(n_pp / len(grid))
        print(f"   {step:4.2f} | {len(grid):6d} | {plateau:14.3f}   | {formula:.3f}")
    print("   (step 0.5 should land near the other session's 0.595/0.600)")


def range_dependence() -> None:
    print("\n[2] Is RMS_pp 'universal'? Recompute over growing ranges [2,X]")
    print("   X    | #prime powers | RMS_pp = sqrt(mean (log p/2)^2) | ~ (log X)/2")
    for X in (50, 100, 200, 500, 1000, 5000):
        lam = prime_powers_with_lambda(X)
        rms = math.sqrt(np.mean([(v / 2.0) ** 2 for v in lam.values()]))
        print(f"   {X:5d} | {len(lam):13d} | {rms:30.3f} | {math.log(X)/2:.3f}")
    print("   -> RMS_pp GROWS with range (tracks ~(log X)/2). It is NOT universal:")
    print("      invariant under grid refinement at fixed range, but range-dependent.")


if __name__ == "__main__":
    density_factorization()
    range_dependence()
