"""Reconcile the cross-session RMSE discrepancy + corroborate GUE a second way.

Claim under test (from the other instance's reconciliation):
  1. On-grid (evaluation points sitting ON the integers = on psi's jumps), the
     explicit formula converges to the jump MIDPOINT, leaving an irreducible error
     log(p)/2 at every prime power -> the RMSE ladder PLATEAUS, no matter how many
     zeros. Predicted floor sqrt(mean (log p / 2)^2) ~ 0.595.
  2. Off-grid (quarter-step off the integers), no point lands on a jump -> the
     ladder DESCENDS toward 0.
  3. A *different* statistic, nearest-neighbor spacing vs the Wigner GUE surmise,
     returns the same verdict as pair correlation: the zeros repel (beta=2).
"""

from __future__ import annotations

import math

import numpy as np

from scripts.research.zeta_explicit_formula_and_gue import load_zeros, psi_from_zeros, true_psi


def prime_powers_with_lambda(xmax: int) -> dict[int, float]:
    """{n: log p} for every prime power p^k <= xmax (von Mangoldt support)."""
    sieve = np.ones(xmax + 1, dtype=bool)
    sieve[:2] = False
    for i in range(2, int(xmax**0.5) + 1):
        if sieve[i]:
            sieve[i * i :: i] = False
    out: dict[int, float] = {}
    for p in np.nonzero(sieve)[0]:
        pk = int(p)
        while pk <= xmax:
            out[pk] = math.log(p)
            pk *= p
    return out


def rmse_ladder(grid: np.ndarray, gammas: np.ndarray, Ks: list[int]) -> list[float]:
    psi_true = true_psi(grid)
    out = []
    for K in Ks:
        approx = psi_from_zeros(grid, gammas[:K])
        out.append(float(np.sqrt(np.mean((approx - psi_true) ** 2))))
    return out


def grid_diagnosis() -> None:
    print("[1/2] GRID DIAGNOSIS — on-integer plateau vs off-integer descent")
    gammas = load_zeros(500)
    Ks = [10, 50, 100, 200, 500]
    xmax = 50
    lam = prime_powers_with_lambda(xmax)

    on = np.arange(2, xmax + 1, dtype=float)              # exactly on the jumps
    off = np.arange(2, xmax + 1, dtype=float) + 0.25       # quarter-step off

    on_ladder = rmse_ladder(on, gammas, Ks)
    off_ladder = rmse_ladder(off, gammas, Ks)

    # predicted floor: error = log(p)/2 at on-grid prime powers, ~0 elsewhere
    errs = np.array([lam.get(int(n), 0.0) / 2.0 for n in on])
    floor_over_grid = float(np.sqrt(np.mean(errs**2)))
    floor_over_pp = float(np.sqrt(np.mean([(v / 2.0) ** 2 for v in lam.values()])))

    print(f"   K-zeros:            {Ks}")
    print(f"   ON-integer  RMSE:   {[round(v,3) for v in on_ladder]}  (claim: plateaus)")
    print(f"   OFF (+0.25) RMSE:   {[round(v,3) for v in off_ladder]}  (claim: descends)")
    print(f"   predicted floor sqrt(mean over grid (log p/2)^2)        = {floor_over_grid:.3f}")
    print(f"   predicted floor sqrt(mean over prime powers (log p/2)^2) = {floor_over_pp:.3f}  (their 0.595)")
    plateaued = on_ladder[-1] > 0.5 and (on_ladder[1] - on_ladder[-1]) < 0.15
    descends = off_ladder[0] > off_ladder[-1] * 1.5
    print(f"   on-grid plateaus near floor? {plateaued}   off-grid descends? {descends}")


def wigner_spacing(n: int = 500) -> None:
    print(f"\n[2/2] NEAREST-NEIGHBOR SPACING — {n} zeros vs Wigner GUE surmise")
    g = load_zeros(n)
    w = (g / (2 * math.pi)) * (np.log(g / (2 * math.pi)) - 1.0)  # unfold
    s = np.diff(w)
    print(f"   mean unfolded spacing (target 1.0): {s.mean():.4f}")

    # Wigner GUE surmise P(s) = (32/pi^2) s^2 exp(-4 s^2/pi); Poisson P(s)=exp(-s)
    def gue_cdf(x: float) -> float:
        xs = np.linspace(0, x, 2000)
        p = (32 / math.pi**2) * xs**2 * np.exp(-4 * xs**2 / math.pi)
        return float(np.trapezoid(p, xs))

    p_obs = float(np.mean(s < 0.3))
    print(f"   P(s<0.3): observed {p_obs:.3f} | GUE {gue_cdf(0.3):.3f} | Poisson {1-math.exp(-0.3):.3f}")
    n_close = int(np.sum(s < 0.3))
    print(f"   close pairs s<0.3: {n_close}  (independence/Poisson would predict ~{0.259*len(s):.0f})")

    # KS distance of empirical spacing CDF to GUE and to Poisson
    grid = np.linspace(0, 4, 400)
    emp = np.array([np.mean(s <= x) for x in grid])
    gue = np.array([gue_cdf(x) for x in grid])
    poi = 1 - np.exp(-grid)
    print(f"   KS distance: to GUE {np.max(np.abs(emp-gue)):.3f}  vs to Poisson {np.max(np.abs(emp-poi)):.3f}")
    print("   -> smaller KS to GUE = zeros repel like random-matrix eigenvalues (beta=2)")


if __name__ == "__main__":
    grid_diagnosis()
    wigner_spacing(500)
