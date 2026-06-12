"""Regression locks for the foliation probe (scripts/eval/foliation_probe.py).

The probe's verdicts, frozen as invariants of the real pipeline:

  1. leaf-purity     decision is exactly the d* threshold function
  2. transversality  instrument inputs never flip a decision at frozen context
  3. multi-well      min-over-wells genuinely moves decisions vs one well
  4. dead branch     SNAP is unreachable while L12 caps H at 1.0
  5. leaf packing    Euclidean room between leaves shrinks like 1/e

If any of these breaks, either the gate's geometry changed (intentional? update
the probe) or a refactor silently bent the decision surface (bug).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[1]
_PROBE = _REPO / "scripts" / "eval" / "foliation_probe.py"

sys.path.insert(0, str(_REPO))
_spec = importlib.util.spec_from_file_location("foliation_probe_under_test", _PROBE)
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)

L = P.L  # the real fourteen_layer_pipeline module, loaded by the probe


def _pipe():
    return P.make_pipeline()


def test_decision_is_pure_d_star_threshold():
    pipe = _pipe()
    t1, t2 = pipe.theta_1, pipe.theta_2
    seen = set()
    for _ in range(120):
        s = P.run(pipe, P.swept_context(), P.random_instruments())
        assert s["decision"] == P.threshold_decision(s["d_star"], t1, t2)
        seen.add(s["decision"])
    # the sweep must actually cross the leaves, or the purity check is vacuous
    assert {"ALLOW", "DENY"} <= seen


def test_instruments_never_flip_decision_at_frozen_context():
    pipe = _pipe()
    moved = 0.0
    for _ in range(6):
        ctx = P.swept_context()
        base = P.run(pipe, ctx, P.random_instruments())
        for _ in range(25):
            r = P.run(pipe, ctx, P.random_instruments())
            moved = max(moved, abs(r["d_tri"] - base["d_tri"]), abs(r["coherence"] - base["coherence"]))
            assert r["decision"] == base["decision"]
    # the needles must have actually moved for the invariance to mean anything
    assert moved > 0.02


def test_multi_well_is_load_bearing():
    pipe = _pipe()
    t1, t2 = pipe.theta_1, pipe.theta_2
    changed = 0
    for _ in range(150):
        ctx = P.swept_context()
        c = L.layer_1_complex_context(**ctx)
        x = L.layer_2_realify(c)
        xw = L.layer_3_weighted(x, pipe.langues_metric)
        u = L.layer_4_poincare(xw, pipe.alpha)
        dists = [L.layer_5_hyperbolic_distance(u, mu) for mu in pipe.realm_centers]
        if P.threshold_decision(min(dists), t1, t2) != P.threshold_decision(dists[0], t1, t2):
            changed += 1
    assert changed > 0, "wells never changed a decision — multi-well structure went decorative"


def test_snap_branch_is_dead_while_l12_is_bounded():
    # L12 Form B sup is exactly 1.0 (d=0, pd=0) and SNAP needs H_d > 100.
    assert L.layer_12_harmonic_scaling(0.0, 0.0) == 1.0
    for d in np.linspace(0, 50, 200):
        assert L.layer_12_harmonic_scaling(float(d), 0.0) <= 1.0
    risk = L.layer_13_decision(d_star=0.1, H_d=1.0, coherence=0.5, realm_idx=0)
    assert risk.decision != "SNAP"


def test_leaf_packing_is_exponential():
    # Euclidean radius of the leaf at hyperbolic distance d (real L5 ruler).
    def leaf_radius(d_target: float) -> float:
        lo, hi = 0.0, 1.0 - 1e-12
        e1 = np.zeros(12)
        e1[0] = 1.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if L.layer_5_hyperbolic_distance(np.zeros(12), mid * e1) < d_target:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    radii = [leaf_radius(float(d)) for d in range(1, 9)]
    gaps = np.diff([0.0] + radii)
    ratios = gaps[1:] / gaps[:-1]
    mean_ratio = float(np.mean(ratios[2:]))
    assert abs(mean_ratio - np.exp(-1)) < 0.05
