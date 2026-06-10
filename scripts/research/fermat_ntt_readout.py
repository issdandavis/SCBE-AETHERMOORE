#!/usr/bin/env python3
"""fermat_ntt_readout.py — does the Fermat/NTT structure buy anything in the readout?

Tests my own earlier claim ("Fermat/NTT is the one load-bearing prime lever") on
the Tensor Foam reservoir (tensor_foam_reservoir.py). Ships with the null, and
confronts the hard fact first:

  HARD FACT (absorption): a LINEAR readout absorbs any invertible linear map.
  NTT and DFT are linear, so NTT-then-linear-readout gives IDENTICAL accuracy to
  raw state. => for a linear readout, NTT buys exactly zero accuracy. Demonstrated
  with OLS: raw vs orthogonally-rotated state -> same NMSE.

So NTT can only matter via:
  TEST A (compression): does the Fourier/spectral basis CONCENTRATE the foam's
          task-relevant signal into fewer modes than random projection or raw
          truncation? Null = random projection (J-L preserves but doesn't
          concentrate) and raw-first-K; ceiling = PCA (optimal linear compressor).
          If DFT-lowK ~= PCA and >> random/raw, spectral structure is load-bearing
          for compression. If DFT ~= random, decorative.

  TEST B (exactness): the genuinely Fermat-SPECIFIC property is that the NTT mod
          65537 is an EXACT integer transform (zero floating-point error), because
          65536 = 2^16 gives a primitive 2^16-th root of unity. This is a COST /
          hardware property ("compute in the material, no float"), not an accuracy
          one. Demonstrated by exact round-trip vs float-DFT round-trip error.

Verdict shape: NTT in a linear readout is decorative for ACCURACY (absorption);
the Fermat win is EXACTNESS (cost), and spectral compression helps only insofar
as the foam state actually has low-frequency structure (measured, not assumed).

Usage:  PYTHONPATH=. python scripts/research/fermat_ntt_readout.py
Reuses the foam from tensor_foam_reservoir and the sieve upstream.
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tensor_foam_reservoir import (  # noqa: E402
    GRID,
    N,
    T,
    WASHOUT,
    SEED,
    grid_adjacency,
    coupling,
    run_reservoir,
    nonlinear_task,
)

P = 65537  # Fermat prime F4 = 2^16 + 1
G = 3  # primitive root of 65537 (base of Pepin's test)


# --------------------------------------------------------------------------- #
# Readout + bases
# --------------------------------------------------------------------------- #
def ols_nmse(F: np.ndarray, y: np.ndarray) -> float:
    """Ordinary least squares (no penalty) test NMSE; basis-invariant for full rank."""
    Fb = np.hstack([F, np.ones((len(F), 1))])
    half = len(F) // 2
    w, *_ = np.linalg.lstsq(Fb[:half], y[:half], rcond=None)
    pred = Fb[half:] @ w
    yte = y[half:]
    return float(np.mean((pred - yte) ** 2) / (np.var(yte) + 1e-12))


def ridge_nmse(F: np.ndarray, y: np.ndarray, reg: float = 1e-4) -> float:
    Fb = np.hstack([F, np.ones((len(F), 1))])
    half = len(F) // 2
    A = Fb[:half].T @ Fb[:half] + reg * np.eye(Fb.shape[1])
    w = np.linalg.solve(A, Fb[:half].T @ y[:half])
    pred = Fb[half:] @ w
    yte = y[half:]
    return float(np.mean((pred - yte) ** 2) / (np.var(yte) + 1e-12))


def dft_lowk(X: np.ndarray, k: int) -> np.ndarray:
    """First k scalar features of the real-DFT (low spatial frequencies)."""
    C = np.fft.rfft(X, axis=1)  # complex, (T, N//2+1)
    feats = np.hstack([C.real, C.imag])  # linear in X
    return feats[:, :k]


def pca_topk(X: np.ndarray, k: int) -> np.ndarray:
    Xc = X - X.mean(0, keepdims=True)
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    return Xc @ Vt[:k].T


def random_proj(X: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    R = rng.normal(size=(X.shape[1], k)) / np.sqrt(X.shape[1])
    return X @ R


def spectral_power_topk(X: np.ndarray, k: int) -> np.ndarray:
    """NONLINEAR feature: |DFT|^2 power spectrum, top-k low-freq bins. Basis-dependent."""
    C = np.fft.rfft(X, axis=1)
    power = (C.real**2 + C.imag**2)[:, : max(k, 1)]
    return power


def random_rotation_power_topk(X: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    """Null for spectral power: square of a random orthogonal projection."""
    Q, _ = np.linalg.qr(rng.normal(size=(X.shape[1], X.shape[1])))
    R = (X @ Q)[:, :k]
    return R**2


# --------------------------------------------------------------------------- #
# NTT mod 65537 (exact integer transform) — the Fermat-specific lever
# --------------------------------------------------------------------------- #
def ntt_matrices(n: int) -> tuple[np.ndarray, np.ndarray, int]:
    """Forward/inverse NTT matrices mod P for length n (n must divide P-1=2^16)."""
    assert (P - 1) % n == 0, "n must divide 2^16"
    w = pow(G, (P - 1) // n, P)
    winv = pow(w, P - 2, P)
    fwd = np.array([[pow(w, (i * j) % n, P) for j in range(n)] for i in range(n)], dtype=np.int64)
    inv = np.array([[pow(winv, (i * j) % n, P) for j in range(n)] for i in range(n)], dtype=np.int64)
    return fwd, inv, pow(n, P - 2, P)


def ntt_roundtrip_error(state: np.ndarray, n: int = 256) -> tuple[int, float]:
    """Exact NTT round-trip vs float-DFT round-trip on the same quantized state."""
    fwd, inv, ninv = ntt_matrices(n)
    x = np.zeros(n, dtype=np.int64)
    q = np.mod(np.round(state * 10000).astype(np.int64), P)
    x[: len(state)] = q
    X = (fwd @ x) % P
    xr = ((inv @ X) % P * ninv) % P
    ntt_err = int(np.max(np.abs(xr - x)))  # should be exactly 0
    # float DFT round-trip on the same (un-quantized) data
    fx = np.fft.ifft(np.fft.fft(x.astype(float))).real
    float_err = float(np.max(np.abs(fx - x)))
    return ntt_err, float_err


def main() -> int:
    rng = np.random.default_rng(SEED)
    # Build the foam (prime coupling) and its state stream.
    A = grid_adjacency(GRID)
    W = coupling("prime", A, np.random.default_rng(SEED))
    W_in = rng.uniform(-1.2, 1.2, size=N)
    b = rng.uniform(-0.6, 0.6, size=N)
    u = rng.uniform(-1.0, 1.0, size=T)
    y = nonlinear_task(u)
    X = run_reservoir(W, W_in, u, b)[WASHOUT:]
    yy = y[WASHOUT:]

    print("FERMAT / NTT IN THE READOUT — does it buy anything?")
    print("=" * 68)
    print(f"  foam cells={N}  samples={len(X)}  task=u(t-2)^2\n")

    # --- HARD FACT: linear absorption (OLS, full rank) --------------------- #
    Q, _ = np.linalg.qr(rng.normal(size=(N, N)))  # orthogonal basis change
    raw_ols = ols_nmse(X, yy)
    rot_ols = ols_nmse(X @ Q, yy)
    print("[absorption]  a LINEAR readout absorbs any invertible linear map (NTT/DFT included)")
    print(f"    raw-state OLS nmse      = {raw_ols:.6f}")
    print(f"    rotated-state OLS nmse  = {rot_ols:.6f}   (identical => NTT-in-linear = ZERO accuracy gain)")

    # --- TEST A: compression — does the spectral basis concentrate signal? - #
    print("\n[TEST A: compression]  test NMSE vs #features K, by basis (lower=better)")
    Ks = [4, 8, 16, 32, 64]
    print(f"    {'K':>4}{'dft_lowK':>12}{'pca(ceil)':>12}{'random':>10}{'raw_firstK':>12}")
    a_rows = []
    for k in Ks:
        d = ridge_nmse(dft_lowk(X, k), yy)
        p = ridge_nmse(pca_topk(X, k), yy)
        r = ridge_nmse(random_proj(X, k, np.random.default_rng(7)), yy)
        f = ridge_nmse(X[:, :k], yy)
        a_rows.append((k, d, p, r, f))
        print(f"    {k:>4}{d:>12.4f}{p:>12.4f}{r:>10.4f}{f:>12.4f}")

    # --- TEST A': nonlinear spectral power (genuinely basis-dependent) ----- #
    print("\n[TEST A': nonlinear spectral power]  |DFT|^2 vs |random-rotation|^2 (lower=better)")
    for k in [8, 16, 32]:
        sp = ridge_nmse(spectral_power_topk(X, k), yy)
        rp = ridge_nmse(random_rotation_power_topk(X, k, np.random.default_rng(11)), yy)
        print(f"    K={k:>3}  |DFT|^2 nmse={sp:.4f}    |rand-rot|^2 nmse={rp:.4f}")

    # --- TEST B: exactness — the Fermat-specific lever (cost, not accuracy) - #
    print("\n[TEST B: exactness]  NTT mod 65537 is an EXACT integer transform")
    ntt_err, float_err = ntt_roundtrip_error(X[0])
    print(f"    NTT-mod-65537 round-trip max error = {ntt_err}        (exact, integer)")
    print(f"    float-DFT round-trip max error     = {float_err:.3e}  (nonzero, float drift)")

    # --- verdict ----------------------------------------------------------- #
    print("\n--- VERDICT ---")
    absorbed = abs(raw_ols - rot_ols) < 1e-4
    # compression load-bearing iff dft beats random clearly AND tracks PCA at small K
    k8 = next(r for r in a_rows if r[0] == 8)
    dft_beats_random = k8[1] < 0.9 * k8[3]
    dft_tracks_pca = k8[1] < 1.3 * k8[2]
    print(
        f"  ACCURACY (linear readout): NTT/DFT is DECORATIVE — absorbed by the readout " f"(raw==rotated: {absorbed})."
    )
    if dft_beats_random and dft_tracks_pca:
        comp = "LOAD-BEARING — spectral basis concentrates the foam signal (DFT ~ PCA, << random)"
    elif dft_beats_random:
        comp = "PARTIAL — DFT beats random but trails PCA"
    else:
        comp = "DECORATIVE — DFT ~ random; the foam state has no low-freq structure to exploit"
    print(f"  COMPRESSION: {comp}")
    print("  EXACTNESS (Fermat-specific): NTT mod 65537 round-trips with ZERO error — the real")
    print("  Fermat lever is exact integer compute (no float), a COST/hardware win, not accuracy.")

    # self-checks
    assert pow(G, (P - 1) // 2, P) == P - 1, "3 must be a primitive root mod 65537 (order 2^16)"
    assert ntt_err == 0, "NTT round-trip must be exact"
    assert float_err >= 0.0
    assert absorbed, "linear readout must absorb an orthogonal basis change"
    print("\n  self-checks: primitive root ok, NTT exact, linear absorption confirmed — all passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
