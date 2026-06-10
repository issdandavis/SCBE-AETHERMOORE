#!/usr/bin/env python3
"""tensor_foam_reservoir.py — does "intelligent foam" actually COMPUTE?

Vision under test: a structural foam whose cells sense + propagate + route
signals "becomes part of the computer" (mechanical metamaterials / physical
neural networks / programmable matter). The honest field that decides this is
RESERVOIR COMPUTING: a fixed nonlinear medium computes a temporal task only if
its state has (a) fading memory of past input and (b) high-dimensional
separation a *linear* readout can exploit. If a linear readout on the foam's
state beats a linear readout on the raw input, the medium did real work.

Second, sharper claim under test: does the PRIME-RATIONED coupling (residue-lane
weights from prime_rationed_lattice) do anything a random foam doesn't? So this
ships with its null, in the instrument-family spirit:

  NULL 1 (does the foam compute?): compare a linear readout on reservoir state
          vs on raw input, for memory + a nonlinear temporal task. If state >>
          raw, the medium computes.
  NULL 2 (does prime structure matter?): build prime / random / uniform / and
          shuffled-prime couplings on the SAME connectivity, rescaled to the
          SAME spectral radius (so only the weight PATTERN differs). If prime
          ~= random, the prime-rationing is DECORATIVE; the computation is from
          the nonlinear dynamics + dimensionality, not the prime pattern.

Method controls (the part that makes it a test and not a demo):
  - identical grid connectivity, input weights, and driving signal across modes
  - every coupling matrix rescaled to spectral radius rho (fair gain)
  - washout, train/test split, ridge readout
  - shuffled-prime null = same weight histogram, structure destroyed

Usage:  PYTHONPATH=. python scripts/research/tensor_foam_reservoir.py
Self-contained; reuses the verified sieve from nth_prime_baseline_gate.
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nth_prime_baseline_gate import simple_sieve  # noqa: E402

GRID = 12  # 12x12 = 144 cells
N = GRID * GRID
RHO = 0.95  # target spectral radius (edge of stability — good reservoir regime)
LEAK = 0.3
T = 2600
WASHOUT = 300
SEED = 0


def grid_adjacency(g: int) -> np.ndarray:
    """4-neighbour grid connectivity mask (symmetric, no self-loops)."""
    A = np.zeros((g * g, g * g), dtype=float)
    for r in range(g):
        for c in range(g):
            i = r * g + c
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < g and 0 <= cc < g:
                    A[i, rr * g + cc] = 1.0
    return A


def coupling(mode: str, A: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Weight the connectivity by mode, then rescale to spectral radius RHO."""
    n = A.shape[0]
    primes = simple_sieve(2000)[:n]  # one prime label per cell
    W = np.zeros_like(A)
    edges = np.argwhere(A > 0)

    if mode == "prime":
        # residue-lane weight: (p_i mod p_j)/p_j mapped to [-1,1]. Deterministic,
        # heterogeneous, derived purely from the cells' prime channels.
        for i, j in edges:
            W[i, j] = 2.0 * ((primes[i] % primes[j]) / primes[j]) - 1.0
    elif mode == "random":
        for i, j in edges:
            W[i, j] = rng.normal()
    elif mode == "uniform":
        W[A > 0] = 1.0
    elif mode == "prime_shuffled":
        vals = np.array([2.0 * ((primes[i] % primes[j]) / primes[j]) - 1.0 for i, j in edges])
        rng.shuffle(vals)  # same histogram, structure destroyed
        for (i, j), v in zip(edges, vals):
            W[i, j] = v
    else:
        raise ValueError(mode)

    radius = max(abs(np.linalg.eigvals(W)))
    if radius > 0:
        W *= RHO / radius
    return W


def run_reservoir(W: np.ndarray, W_in: np.ndarray, u: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Leaky-tanh echo-state update; return state matrix X (T x N).

    The bias b is essential: tanh is ODD, so tanh(linear-in-u) has no even-order
    component and cannot synthesize u^2 around 0. A nonzero operating point (b)
    breaks that symmetry so the foam can compute squares.
    """
    n = W.shape[0]
    x = np.zeros(n)
    X = np.zeros((len(u), n))
    for t in range(len(u)):
        pre = W @ x + W_in * u[t] + b
        x = (1 - LEAK) * x + LEAK * np.tanh(pre)
        X[t] = x
    return X


def ridge_readout(X: np.ndarray, y: np.ndarray, reg: float = 1e-6) -> tuple[float, np.ndarray]:
    """Fit linear readout (with bias) on train half, return test NMSE + weights."""
    Xb = np.hstack([X, np.ones((len(X), 1))])
    half = len(X) // 2
    Xtr, ytr, Xte, yte = Xb[:half], y[:half], Xb[half:], y[half:]
    A = Xtr.T @ Xtr + reg * np.eye(Xtr.shape[1])
    w = np.linalg.solve(A, Xtr.T @ ytr)
    pred = Xte @ w
    nmse = float(np.mean((pred - yte) ** 2) / (np.var(yte) + 1e-12))
    return nmse, w


def memory_capacity(X: np.ndarray, u: np.ndarray, kmax: int = 25) -> float:
    """Jaeger short-term memory: sum_k corr^2(readout for u[t-k], u[t-k])."""
    mc = 0.0
    for k in range(1, kmax + 1):
        target = np.roll(u, k)
        target[:k] = 0.0
        Xb = np.hstack([X, np.ones((len(X), 1))])
        half = len(X) // 2
        A = Xb[:half].T @ Xb[:half] + 1e-6 * np.eye(Xb.shape[1])
        w = np.linalg.solve(A, Xb[:half].T @ target[:half])
        pred = Xb[half:] @ w
        yte = target[half:]
        if np.var(yte) < 1e-9:
            continue
        r = np.corrcoef(pred, yte)[0, 1]
        mc += 0.0 if np.isnan(r) else r * r
    return mc


def nonlinear_task(u: np.ndarray) -> np.ndarray:
    """Nonlinear MEMORY target: y(t) = u(t-2)^2.

    Clean discriminator: a linear readout on raw input history CANNOT produce a
    square (best linear predictor of u^2 from symmetric u is the mean -> NMSE~1),
    while a tanh reservoir operating in its nonlinear regime can approximate it.
    Needs memory (delay 2) AND nonlinearity (square) — exactly the foam claim.
    """
    y = np.zeros_like(u)
    y[2:] = u[:-2] ** 2
    return y


def echo_state_check(W: np.ndarray, W_in: np.ndarray, u: np.ndarray, b: np.ndarray) -> float:
    """Two different initial states must converge (fading memory). Return final gap."""
    n = W.shape[0]
    xa, xb = np.ones(n) * 0.5, -np.ones(n) * 0.5
    for t in range(min(400, len(u))):
        xa = (1 - LEAK) * xa + LEAK * np.tanh(W @ xa + W_in * u[t] + b)
        xb = (1 - LEAK) * xb + LEAK * np.tanh(W @ xb + W_in * u[t] + b)
    return float(np.linalg.norm(xa - xb))


def evaluate(mode: str, A: np.ndarray, W_in: np.ndarray, b: np.ndarray, u: np.ndarray, y: np.ndarray) -> dict:
    rng = np.random.default_rng(SEED + hash(mode) % 1000)
    W = coupling(mode, A, rng)
    esp_gap = echo_state_check(W, W_in, u, b)
    X = run_reservoir(W, W_in, u, b)[WASHOUT:]
    uu, yy = u[WASHOUT:], y[WASHOUT:]
    mc = memory_capacity(X, uu)
    nmse, _ = ridge_readout(X, yy)
    return {"mode": mode, "esp_gap": esp_gap, "memory_capacity": mc, "task_nmse": nmse}


def main() -> int:
    rng = np.random.default_rng(SEED)
    A = grid_adjacency(GRID)
    # Input scaling chosen so tanh operates in its NONLINEAR regime (needed to
    # synthesize squares); too small -> near-linear foam, too large -> saturation.
    W_in = rng.uniform(-1.2, 1.2, size=N)
    b = rng.uniform(-0.6, 0.6, size=N)  # bias breaks tanh odd-symmetry -> enables squares
    u = rng.uniform(-1.0, 1.0, size=T)
    y = nonlinear_task(u)

    # NULL 1 baseline: linear readout on RAW INPUT history (no foam).
    hist = np.column_stack([np.roll(u, k) for k in range(8)])
    raw_mc_nmse, _ = ridge_readout(hist[WASHOUT:], y[WASHOUT:])

    print("TENSOR FOAM RESERVOIR — does the foam compute, and do primes matter?")
    print("=" * 70)
    print(f"  cells={N}  spectral_radius={RHO}  leak={LEAK}  T={T}  washout={WASHOUT}\n")

    modes = ["prime", "random", "uniform", "prime_shuffled"]
    results = [evaluate(m, A, W_in, b, u, y) for m in modes]

    print(f"  {'mode':<16}{'esp_gap':>12}{'mem_capacity':>15}{'task_nmse':>12}")
    print("  " + "-" * 53)
    for r in results:
        print(f"  {r['mode']:<16}{r['esp_gap']:>12.2e}{r['memory_capacity']:>15.3f}{r['task_nmse']:>12.4f}")
    print(f"\n  NULL 1 baseline — linear readout on RAW input history: task_nmse={raw_mc_nmse:.4f}")

    best = min(results, key=lambda r: r["task_nmse"])
    prime = next(r for r in results if r["mode"] == "prime")
    rand = next(r for r in results if r["mode"] == "random")

    print("\n--- VERDICT ---")
    foam_computes = prime["task_nmse"] < 0.9 * raw_mc_nmse or rand["task_nmse"] < 0.9 * raw_mc_nmse
    print(
        f"  NULL 1 (does the foam compute?): "
        f"{'YES' if foam_computes else 'NO'} — best foam nmse {best['task_nmse']:.4f} "
        f"vs raw-input {raw_mc_nmse:.4f}"
    )
    rel = (rand["task_nmse"] - prime["task_nmse"]) / (rand["task_nmse"] + 1e-12)
    if abs(rel) < 0.10:
        prime_verdict = f"DECORATIVE — prime ~= random (within 10%: {rel*100:+.1f}%)"
    elif rel > 0:
        prime_verdict = f"prime BEATS random by {rel*100:.1f}% (structure helps)"
    else:
        prime_verdict = f"prime WORSE than random by {-rel*100:.1f}% (structure hurts)"
    print(f"  NULL 2 (does prime structure matter?): {prime_verdict}")
    print("\n  (matched connectivity + spectral radius; only the weight PATTERN differs)")

    # self-checks
    assert all(r["esp_gap"] < 1.0 for r in results if r["mode"] != "uniform"), "echo-state property should hold"
    assert prime["memory_capacity"] > 1.0, "a working reservoir must store >1 bit of memory"
    assert foam_computes, "foam should beat raw-input baseline on the nonlinear task"
    print("\n  self-checks: echo-state holds, memory>1, foam beats raw — all passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
