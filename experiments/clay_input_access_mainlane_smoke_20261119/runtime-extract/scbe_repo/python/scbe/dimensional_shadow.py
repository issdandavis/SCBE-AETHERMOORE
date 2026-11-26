"""dimensional_shadow: a structure that is TANGLED in dimension d becomes COMPRESSED in d+1, and the
d-dim version is recovered as the SHADOW (projection) of the higher one.

Issac's idea made precise: don't think 1, 2, 3, 4 -- think a continuous LIFT parameter lam that raises the
effective dimension "by perspective". A pattern you cannot describe simply in your own dimension (here: two
concentric rings -- NO straight line separates them in 2D) is the boundary projection of a SIMPLE object one
dimension up. Lift z = lam * (x^2 + y^2) (a paraboloid; lam in [0,1] is the perspective gradient): as lam
rises the rings pull apart along z until a single FLAT plane (one number) separates them -- the curved,
many-parameter 2D boundary has folded into a 1-parameter 3D boundary (compression). Drop z and you get the
original rings back exactly: the 2D pattern is the SHADOW of the 3D one.

This is the kernel trick (lift to where it's linear) = Nash embedding (always foldable up) = the
holographic shadow (lower-D is the boundary of higher-D), which is what Issac described by feel.

    from python.scbe.dimensional_shadow import demo
    demo()   # sweeps the perspective gradient; prints separability rising + boundary compressing
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

Point = Tuple[float, float]


def rings(n: int = 240, seed: int = 7) -> Tuple[List[Point], List[int]]:
    """Two concentric rings: inner (label 0, r~1) and outer (label 1, r~2). NOT linearly separable in 2D."""
    rng = _Rng(seed)
    pts: List[Point] = []
    labels: List[int] = []
    for i in range(n):
        inner = i % 2 == 0
        r = (1.0 if inner else 2.0) + 0.08 * (rng.next() - 0.5)
        a = 2 * math.pi * rng.next()
        pts.append((r * math.cos(a), r * math.sin(a)))
        labels.append(0 if inner else 1)
    return pts, labels


def lift(pts: List[Point], lam: float) -> List[Tuple[float, float, float]]:
    """Raise the dimension 'by perspective': z = lam*(x^2+y^2). lam=0 is flat 2D, lam=1 fully lifted."""
    return [(x, y, lam * (x * x + y * y)) for (x, y) in pts]


def shadow(lifted: List[Tuple[float, float, float]]) -> List[Point]:
    """The lower dimension as the SHADOW of the higher: drop the lifted axis (project z->0)."""
    return [(x, y) for (x, y, _z) in lifted]


def best_axis_split(values: List[float], labels: List[int]) -> Tuple[float, float]:
    """The simplest possible boundary in the lifted axis: ONE threshold. Returns (accuracy, threshold).
    A single number separating the classes = maximal compression of the boundary."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    best_acc, best_thr = 0.0, 0.0
    n = len(values)
    for k in range(n + 1):
        thr = (
            (values[order[k - 1]] + values[order[k % n]]) / 2
            if 0 < k < n
            else (values[order[0]] - 1 if k == 0 else values[order[-1]] + 1)
        )
        correct = sum(1 for i in range(n) if (values[i] >= thr) == (labels[i] == 1))
        acc = correct / n
        if acc > best_acc:
            best_acc, best_thr = acc, thr
    return best_acc, best_thr


def linear_2d_separability(pts: List[Point], labels: List[int], dirs: int = 36) -> float:
    """Best accuracy ANY straight line achieves in 2D (scan directions x threshold). For concentric rings
    this caps near chance -- the pattern does not fit a 2D linear boundary (you are 'askew to 2D')."""
    best = 0.0
    for d in range(dirs):
        a = math.pi * d / dirs
        proj = [px * math.cos(a) + py * math.sin(a) for (px, py) in pts]
        acc, _ = best_axis_split(proj, labels)
        best = max(best, acc)
    return best


def sweep(lams: List[float] = None) -> List[Dict[str, float]]:
    """The perspective gradient: for each lam, how separable is the lifted set by ONE plane, and does the
    shadow still equal the original 2D?"""
    if lams is None:
        lams = [0.0, 0.25, 0.5, 0.75, 1.0]
    pts, labels = rings()
    base2d = linear_2d_separability(pts, labels)  # how well 2D alone can do -- the 'own dimension'
    out = []
    for lam in lams:
        lifted = lift(pts, lam)
        z = [p[2] for p in lifted]
        acc_z, _ = best_axis_split(z, labels)  # one flat plane in the lifted axis
        recovered = shadow(lifted)
        shadow_exact = all(abs(a[0] - b[0]) < 1e-12 and abs(a[1] - b[1]) < 1e-12 for a, b in zip(recovered, pts))
        # boundary "cost": params to describe the separating surface. 2D needs a curve (a circle: cx,cy,r
        # = 3 nonlinear params); the lifted plane needs 1 (a threshold). cost falls as the dim rises.
        boundary_params = 1 if acc_z > 0.98 else 3
        out.append(
            {
                "lam": lam,
                "one_plane_accuracy": round(acc_z, 3),
                "boundary_params": boundary_params,
                "shadow_recovers_2d": shadow_exact,
                "best_2d_line": round(base2d, 3),
            }
        )
    return out


def demo() -> None:
    print("DIMENSIONAL SHADOW -- a 2D pattern (concentric rings) folded into a compressed 3D boundary\n")
    rows = sweep()
    print(
        "  best a 2D straight line can do (your own dimension): %.0f%%  <- tangled, can't fit 2D"
        % (100 * rows[0]["best_2d_line"])
    )
    print("\n  lam   one-plane-acc   boundary-params   shadow=2D")
    for r in rows:
        print(
            "  %.2f      %5.0f%%            %d                %s"
            % (r["lam"], 100 * r["one_plane_accuracy"], r["boundary_params"], r["shadow_recovers_2d"])
        )
    last = rows[-1]
    print(
        "\n  => as the perspective dimension rises, ONE flat plane separates the rings (%.0f%%): the curved"
        % (100 * last["one_plane_accuracy"])
    )
    print("     3-parameter 2D boundary FOLDED into a 1-parameter 3D one (compression), and the 2D pattern")
    print("     is exactly the SHADOW of the 3D object. Lower dimension = shadow of the new one.")


def wave(scales: List[float] = None) -> List[Dict[str, float]]:
    """Issac's WAVE: the SAME lift-to-shadow process at every realm. The universe (the process) is FIXED;
    only scale changes. Generate the rings at scale s, apply the IDENTICAL operator, and confirm it still
    folds to a 1-parameter boundary at 100% -- the process doesn't care what dimension/scale it runs at.
    That scale-invariance is what makes it a recurring wave you can climb, not a one-off trick."""
    if scales is None:
        scales = [1.0, 10.0, 100.0, 1000.0]
    out = []
    for s in scales:
        pts0, labels = rings()
        pts = [(s * x, s * y) for (x, y) in pts0]  # same pattern, different scale
        z = [p[2] for p in lift(pts, 1.0)]  # the IDENTICAL operator
        acc, _ = best_axis_split(z, labels)
        out.append({"scale": s, "one_plane_accuracy": round(acc, 3), "boundary_params": 1 if acc > 0.98 else 3})
    return out


def wave_demo() -> None:
    print("\nWAVE -- the same lift process at every scale (the universe/process is fixed, scale is not)\n")
    print("  scale     one-plane-acc   boundary-params")
    for r in wave(scales=[1.0, 10.0, 100.0, 1000.0]):
        print("  %7.0f       %5.0f%%            %d" % (r["scale"], 100 * r["one_plane_accuracy"], r["boundary_params"]))
    print("\n  => identical operator, identical 1-parameter compressed boundary at every scale: the process")
    print("     is the fixed thing; the realm/scale is the variable. Same process, higher abstraction each")
    print("     time -- a wave you climb, with the lower realm always the shadow of the next.")


class _Rng:
    """Tiny deterministic LCG (no numpy dep, reproducible)."""

    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self) -> float:
        self.s = (1103515245 * self.s + 12345) & 0x7FFFFFFF
        return self.s / 0x7FFFFFFF
