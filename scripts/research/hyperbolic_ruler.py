#!/usr/bin/env python3
"""hyperbolic_ruler.py — the ruler as a geodesic in the Poincaré ball.

Issac's "fine-tune across axes": don't keep the line on one straight axis — in a
hyperbolic ball you can angle / skew / invert it (Möbius isometries) and read the
answer across many frames, AS LONG AS you obey congruency. The payoff:

  CONGRUENCE-INVARIANCE IS THE LEVEL, lifted into curved space.
  The hyperbolic distance d_H is invariant under every Möbius isometry. So a
  measurement that reads the SAME across all angles is real (frame-free); one that
  drifts when you reframe is an artifact of the angle, not the geometry.

This also tests whether your instrument is *actually* hyperbolic: real arcosh d_H
is Möbius-invariant; a phi-weighted-Euclidean surrogate is NOT (cf. the gate's
d_H finding). Invariance under reframing is the litmus.

And it shows the "innate stretching": a finite coordinate near the boundary sits
at near-infinite d_H — one short ruler, unbounded range.

Usage:  python scripts/research/hyperbolic_ruler.py
"""
from __future__ import annotations

import cmath
import math
import random
import statistics

SEED = 0


def d_H(u: complex, v: complex) -> float:
    """Poincaré-disk hyperbolic distance (L5)."""
    num = abs(u - v) ** 2
    den = (1 - abs(u) ** 2) * (1 - abs(v) ** 2)
    return math.acosh(1 + 2 * num / den)


def mobius_isometry(a: complex, theta: float):
    """A congruence of the disk: f(z) = e^{iθ}(z - a)/(1 - ā z), |a|<1. Preserves d_H."""
    def f(z: complex) -> complex:
        return cmath.exp(1j * theta) * (z - a) / (1 - a.conjugate() * z)
    return f


def main() -> int:
    rng = random.Random(SEED)
    # an "answer set" embedded in the ball (5 points at assorted radii/angles)
    pts = [0.0 + 0.0j]
    for _ in range(4):
        r = rng.uniform(0.2, 0.85)
        th = rng.uniform(0, 2 * math.pi)
        pts.append(cmath.rect(r, th))

    pairs = [(i, j) for i in range(len(pts)) for j in range(i + 1, len(pts))]
    base_dH = [d_H(pts[i], pts[j]) for i, j in pairs]
    base_eu = [abs(pts[i] - pts[j]) for i, j in pairs]

    # reframe through several congruent angles/skews
    frames = []
    for _ in range(6):
        a = cmath.rect(rng.uniform(0.0, 0.7), rng.uniform(0, 2 * math.pi))
        f = mobius_isometry(a, rng.uniform(0, 2 * math.pi))
        tp = [f(z) for z in pts]
        frames.append((
            [d_H(tp[i], tp[j]) for i, j in pairs],
            [abs(tp[i] - tp[j]) for i, j in pairs],
        ))

    # how much does each measurement drift across angles?
    dH_drift = max(
        abs(frames[k][0][p] - base_dH[p])
        for k in range(len(frames)) for p in range(len(pairs))
    )
    eu_spreads = []
    for p in range(len(pairs)):
        vals = [base_eu[p]] + [frames[k][1][p] for k in range(len(frames))]
        eu_spreads.append((max(vals) - min(vals)))
    eu_drift = max(eu_spreads)

    print("HYPERBOLIC RULER — read the answer across angles (Möbius reframes)")
    print(f"  points embedded in the ball: {len(pts)};  pairwise measurements: {len(pairs)}")
    print(f"  reframed through {len(frames)} congruent angles\n")
    print(f"  d_H   (the congruent metric): max drift across all angles = {dH_drift:.2e}   -> INVARIANT")
    print(f"  euclid (naive flat reading):  max drift across all angles = {eu_drift:.3f}    -> frame-dependent")
    print(f"  => only d_H survives reframing. An alignment real in d_H is real at EVERY angle;")
    print(f"     a euclidean 'alignment' is an artifact of the skew you happened to pick.\n")

    # innate stretching: finite coordinate, near-infinite distance
    print("  innate stretching (finite coordinate -> unbounded range):")
    for r in (0.9, 0.99, 0.999, 0.9999):
        print(f"    |z|={r:<7}  d_H(z, center) = {d_H(complex(r), 0):.2f}")

    # self-checks
    assert dH_drift < 1e-9, f"d_H not invariant under Möbius — instrument isn't truly hyperbolic ({dH_drift:.2e})"
    assert eu_drift > 0.05, "euclidean reading didn't move under reframing — demo is degenerate"
    assert d_H(complex(0.9999), 0) > d_H(complex(0.9), 0) > 1.0, "boundary stretching missing"
    print("\n  self-checks: d_H invariant across angles; euclidean is not; boundary stretches  OK")
    print("  honest gate: hyperbolic room only helps if the answer-space is ACTUALLY negatively")
    print("  curved/hierarchical. Embed flat data in a ball and the extra room is empty (curvature")
    print("  must be earned — cf. the inner-dimension null). Invariance proves the metric; it does")
    print("  not prove the curvature was needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
