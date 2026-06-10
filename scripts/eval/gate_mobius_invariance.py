#!/usr/bin/env python3
"""gate_mobius_invariance.py — run the Congruence Test on the LIVE production gate.

Claim under test (Instrument Family §7): the production text gate's distance is a
phi-weighted Euclidean distance from a learned centroid, NOT the hyperbolic arcosh
metric — so it is NOT invariant under hyperbolic (Möbius) isometries of the Poincaré
ball. A true d_H would be invariant; a coordinate surrogate drifts.

Faithfulness: we call the actual RuntimeGate._harmonic_cost via a minimal shim (it
only reads self._centroid), and assert our weighted-distance reconstructs its cost
exactly before measuring anything. No strawman.

Verdict rule (pre-committed): gate-metric drift > 1e-6 under isometries that leave
d_H invariant  ==>  the gate measures a coordinate artifact, not a hyperbolic distance.

Usage:  PYTHONPATH=. python scripts/eval/gate_mobius_invariance.py
"""
from __future__ import annotations

import random
from types import SimpleNamespace

import numpy as np

from src.governance.runtime_gate import RuntimeGate, TONGUE_WEIGHTS, PHI, PI

W = np.array(TONGUE_WEIGHTS, dtype=float)        # (φ^0 .. φ^5)
DIM = 6
SEED = 0


def gate_weighted_dist(x: np.ndarray, c: np.ndarray) -> float:
    """The gate's actual inner metric (verified vs source lines 895-897)."""
    return float(np.sqrt(np.sum(W * (x - c) ** 2)))


def real_gate_cost(x: np.ndarray, c: np.ndarray) -> float:
    """Call the LIVE RuntimeGate._harmonic_cost (shim only supplies _centroid)."""
    shim = SimpleNamespace(_centroid=np.asarray(c, dtype=float))
    return RuntimeGate._harmonic_cost(shim, list(map(float, x)))


def d_H(u: np.ndarray, v: np.ndarray) -> float:
    """True Poincaré-ball hyperbolic distance."""
    diff = u - v
    return float(np.arccosh(1 + 2 * (diff @ diff) / ((1 - u @ u) * (1 - v @ v))))


def mobius_add(a: np.ndarray, x: np.ndarray) -> np.ndarray:
    """n-D Möbius addition a⊕x. The map x↦a⊕x is a hyperbolic isometry (NOT Euclidean)."""
    a2, x2, ax = a @ a, x @ x, a @ x
    num = (1 + 2 * ax + x2) * a + (1 - a2) * x
    den = 1 + 2 * ax + a2 * x2
    return num / den


def rand_ball(rng: random.Random, max_norm: float) -> np.ndarray:
    v = np.array([rng.gauss(0, 1) for _ in range(DIM)])
    v /= np.linalg.norm(v)
    return v * rng.uniform(0.05, max_norm)


def main() -> int:
    rng = random.Random(SEED)

    # 0) FIDELITY: our weighted-distance must reconstruct the live gate's cost exactly.
    for _ in range(200):
        x, c = rand_ball(rng, 0.6), rand_ball(rng, 0.6)
        recon = PI ** (PHI * min(gate_weighted_dist(x, c), 5.0))
        assert abs(recon - real_gate_cost(x, c)) < 1e-9, "shim does not match live _harmonic_cost"

    # 1) points + centroid in the ball; measure d_H and the gate metric, then reframe.
    pairs = [(rand_ball(rng, 0.55), rand_ball(rng, 0.55)) for _ in range(40)]
    isometries = [rand_ball(rng, 0.45) for _ in range(8)]   # Möbius translation vectors a

    dH_drift, gate_drift = 0.0, 0.0
    base_costs, moved_costs = [], []
    for (u, v) in pairs:
        dH0, g0 = d_H(u, v), gate_weighted_dist(u, v)
        for a in isometries:
            U, V = mobius_add(a, u), mobius_add(a, v)
            dH_drift = max(dH_drift, abs(d_H(U, V) - dH0))
            gd = abs(gate_weighted_dist(U, V) - g0)
            gate_drift = max(gate_drift, gd)
            base_costs.append(real_gate_cost(u, v))
            moved_costs.append(real_gate_cost(U, V))

    # cost-level drift on the live function (relative), to show it in the gate's own units
    cost_rel = max(abs(m - b) / b for b, m in zip(base_costs, moved_costs))

    print("CONGRUENCE TEST — live RuntimeGate._harmonic_cost vs true d_H")
    print(f"  fidelity: weighted-dist reconstructs live cost to <1e-9 (200 cases)  ✓")
    print(f"  isometries applied: {len(isometries)} Möbius translations × {len(pairs)} pairs\n")
    print(f"  true d_H          max drift = {dH_drift:.2e}   -> {'INVARIANT' if dH_drift < 1e-9 else 'DRIFTS'}")
    print(f"  gate metric       max drift = {gate_drift:.4f}   -> {'INVARIANT' if gate_drift < 1e-6 else 'DRIFTS'}")
    print(f"  live gate cost    max relative drift = {cost_rel*100:.1f}%  (same isometries)\n")

    verdict = gate_drift > 1e-6
    if verdict:
        print("  VERDICT: CONFIRMED. The production gate's distance is NOT invariant under")
        print("  hyperbolic isometries that leave d_H exactly invariant. It is measuring a")
        print("  coordinate artifact (phi-weighted Euclidean from centroid), not a hyperbolic")
        print("  distance. §7 is now a RESULT, not a prediction.")
    else:
        print("  VERDICT: NOT confirmed — the gate metric held invariant. §7 prediction was wrong.")

    # self-checks
    assert dH_drift < 1e-9, f"Möbius map isn't a true isometry (d_H drifted {dH_drift:.2e}) — test invalid"
    assert verdict, "expected the surrogate to drift; it did not — investigate"
    print("\n  self-checks: Möbius is a true isometry (d_H invariant); gate surrogate drifts  OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
