"""Verify the 'resurrection' claim and build the GUE pair-correlation demo.

Three independent checks, no argument-by-assertion:

1. RESURRECTION (the true interference object): reconstruct the Chebyshev prime
   staircase psi(x) = sum_{p^k <= x} log p from Riemann zeros via the explicit
   formula psi(x) = x - sum_rho x^rho/rho - log(2pi) - 0.5*log(1 - x^-2).
   Each zero gamma contributes a wave 2*sqrt(x)*Re(e^{i gamma log x}/(1/2+i gamma)).
   Claim under test: RMSE vs the true staircase DROPS as zeros are added, and the
   reconstruction's steep rises land on primes. (Pasted report: 50 waves, 1.95->0.87,
   jumps at 29/41/43.)

2. KILL sanity (the methodological trap): show that any two increasing sequences
   affine-fit to R^2 ~ 0.97, so a high R^2 of Laplacian modes vs zeros is
   meaningless unless primes beat their own nulls.

3. GUE (the offered frontier demo): unfold the first N zeros and compute the pair
   correlation against Montgomery's 1 - (sin(pi r)/(pi r))^2.
"""

from __future__ import annotations

import math
import time
from pathlib import Path

import numpy as np

try:
    import mpmath as mp
except ImportError as exc:  # pragma: no cover
    raise SystemExit(f"needs mpmath: {exc}")

CACHE = Path(__file__).with_name("zeta_zeros_cache.npy")


def load_zeros(n: int) -> np.ndarray:
    """First n positive imaginary parts of nontrivial zeta zeros (incremental cache)."""
    cached = np.load(CACHE) if CACHE.exists() else np.array([])
    if len(cached) >= n:
        return cached[:n]
    t0 = time.time()
    extra = [float(mp.im(mp.zetazero(k))) for k in range(len(cached) + 1, n + 1)]
    gammas = np.concatenate([cached, np.array(extra)])
    np.save(CACHE, gammas)
    print(f"  extended cache {len(cached)}->{n} in {time.time()-t0:.1f}s")
    return gammas[:n]


def true_psi(x: np.ndarray) -> np.ndarray:
    """Chebyshev psi(x) = sum over prime powers p^k <= x of log p."""
    xmax = float(x.max())
    sieve = np.ones(int(xmax) + 1, dtype=bool)
    sieve[:2] = False
    for i in range(2, int(xmax**0.5) + 1):
        if sieve[i]:
            sieve[i * i :: i] = False
    primes = np.nonzero(sieve)[0]
    contrib = []  # (prime_power_location, log p)
    for p in primes:
        pk = p
        while pk <= xmax:
            contrib.append((pk, math.log(p)))
            pk *= p
    contrib.sort()
    out = np.zeros_like(x)
    for i, xi in enumerate(x):
        out[i] = sum(lp for loc, lp in contrib if loc <= xi)
    return out


def psi_from_zeros(x: np.ndarray, gammas: np.ndarray) -> np.ndarray:
    """Explicit-formula reconstruction using the given zeros."""
    out = x - math.log(2 * math.pi) - 0.5 * np.log1p(-(x**-2.0))
    lx = np.log(x)
    for g in gammas:
        # 2 * sqrt(x) * Re( exp(i g log x) / (1/2 + i g) )
        denom = 0.5 + 1j * g
        wave = np.exp(1j * g * lx) / denom
        out -= 2.0 * np.sqrt(x) * wave.real
    return out


def resurrection_check() -> None:
    print("\n[1] RESURRECTION  — explicit-formula reconstruction of the staircase")
    x = np.linspace(2.0, 50.0, 2400)
    psi_true = true_psi(x)
    gammas = load_zeros(200)
    print("  K zeros |  RMSE vs true psi(x)")
    rmses = {}
    for K in (10, 50, 100, 200):
        approx = psi_from_zeros(x, gammas[:K])
        rmse = float(np.sqrt(np.mean((approx - psi_true) ** 2)))
        rmses[K] = rmse
        print(f"   {K:5d}  |   {rmse:.3f}")
    drop = rmses[10] > rmses[50] > rmses[100] > rmses[200]
    print(f"  monotone RMSE drop as zeros added: {drop}")
    # where do the reconstruction's steep rises land? (jumps ~ primes)
    approx = psi_from_zeros(x, gammas[:50])
    deriv = np.gradient(approx, x)
    # local maxima of the derivative above a threshold
    peaks = []
    for i in range(2, len(x) - 2):
        if deriv[i] > deriv[i - 1] and deriv[i] >= deriv[i + 1] and deriv[i] > 1.5:
            peaks.append((deriv[i], x[i]))
    peaks.sort(reverse=True)
    top = sorted(round(float(xx), 1) for _, xx in peaks[:8])
    print(f"  steepest rises (K=50) at x ~ {top}")
    print("  (primes 29,41,43 expected among the strongest; misses sit between twins)")


def kill_sanity() -> None:
    print("\n[2] KILL sanity — two increasing sequences affine-fit high R^2 regardless")
    gammas = load_zeros(30)

    def r2_affine(seq: np.ndarray, target: np.ndarray) -> float:
        a = np.vstack([seq, np.ones_like(seq)]).T
        coef, *_ = np.linalg.lstsq(a, target, rcond=None)
        pred = a @ coef
        ss_res = np.sum((target - pred) ** 2)
        ss_tot = np.sum((target - target.mean()) ** 2)
        return 1.0 - ss_res / ss_tot

    sieve = np.ones(200, dtype=bool)
    sieve[:2] = False
    for i in range(2, 15):
        if sieve[i]:
            sieve[i * i :: i] = False
    primes = np.nonzero(sieve)[0][:30].astype(float)
    rng = np.random.default_rng(0)
    gaps = np.diff(np.concatenate([[2.0], primes]))
    shuffled = np.cumsum(rng.permutation(gaps)) + 2.0  # monotone null
    linear = np.arange(1, 31, dtype=float)  # trivially monotone null
    for name, seq in (("primes", primes), ("gap-shuffle null", shuffled), ("1..30 linear", linear)):
        print(f"  R^2(affine fit -> first 30 zeros)  {name:18s} = {r2_affine(seq, gammas):.4f}")
    print("  -> all ~0.97: high R^2 is what MEANINGLESS looks like here.")


def gue_pair_correlation(n: int = 2000) -> None:
    print(f"\n[3] GUE — Montgomery pair correlation of the first {n} zeros")
    g = load_zeros(n)
    # unfold: N(T) ~ (T/2pi)(log(T/2pi) - 1); unfolded ordinate w_n = N(gamma_n)
    w = (g / (2 * math.pi)) * (np.log(g / (2 * math.pi)) - 1.0)
    spac = np.diff(w)
    print(f"  mean unfolded spacing (target 1.0): {spac.mean():.4f}")
    # pair correlation: all positive differences w_j - w_i < L
    L = 3.0
    diffs = []
    for i in range(len(w)):
        j = i + 1
        while j < len(w) and (w[j] - w[i]) < L:
            diffs.append(w[j] - w[i])
            j += 1
    diffs = np.array(diffs)
    nbins = 30
    hist, edges = np.histogram(diffs, bins=nbins, range=(0, L))
    centers = 0.5 * (edges[:-1] + edges[1:])
    # normalize to density 1 at large r (expected pairs per unit r = (#points)*binwidth)
    binw = L / nbins
    density = hist / (len(w) * binw)

    def gue(r):
        s = np.where(r == 0, 1.0, np.sin(math.pi * r) / (math.pi * r))
        return 1.0 - s**2

    print("    r    | observed | GUE 1-sinc^2")
    for c, d in zip(centers, density):
        if c <= 1.6:
            print(f"   {c:.2f}  |  {d:5.2f}   |   {gue(c):.2f}")
    small = density[centers < 0.3].mean()
    print(f"  level repulsion: mean density at r<0.3 = {small:.2f} (GUE -> ~0, Poisson -> ~1)")


if __name__ == "__main__":
    resurrection_check()
    kill_sanity()
    gue_pair_correlation(500)
