#!/usr/bin/env python3
r"""Signature-parameterised phase deviation. ALTERNATIVES ARM -- primary is untouched.

CLAIM-BEARING GUARDRAIL, READ FIRST. `src/geoseal.py::phase_deviation` is PBHG's phase-deviation
mechanism and is claim-bearing. It stays `primary`, unmodified, and remains the default everywhere.
This module only ADDS a labelled alternative. Any decision record must name which one fired. Never
swap the algebra under the primary -- that breaks patent provenance invisibly and no test catches it.

THE OBSERVATION THIS ARM EXISTS TO TEST. PBHG authorizes on hyperbolic distance (arcosh in the
Poincare ball) but computes phase on a CIRCLE:

    TONGUE_PHASES = {KO:0, AV:pi/3, RU:2pi/3, CA:pi, UM:4pi/3, DR:5pi/3}
    diff = |p1 - p2|;  if diff > pi: diff = 2pi - diff;  return diff / pi
    raw_trust = 1 / (1 + dist + phase_weight * phase_dev)

That single wrap line IS the mu = -1 assumption, and it has a consequence nobody chose on purpose:
**KO and DR become ADJACENT** -- first and last tongue, 60 degrees apart the short way -- while
KO and CA are maximally far. A circular invariant is being added to a hyperbolic distance.

WHAT CHANGES UNDER mu = +1. Hyperbolic rotation has NO period, so there is no wrap: the tongue
ladder becomes an ordered line and KO..DR are the two extremes. Whether the wrap-around adjacency
of KO<->DR helps retrieval or is an artefact of an inherited number system is an empirical
question, and this makes it one.

    mu = -1   circular      exp(theta*u) = cos + u sin      wraps, KO adjacent to DR
    mu =  0   shear         exp(theta*u) = 1 + theta*u      pure ordering, no curvature
    mu = +1   hyperbolic    exp(theta*u) = cosh + u sinh    no wrap, KO farthest from DR

Both return values in [0, 1] so they are drop-in comparable and `phase_weight` keeps its meaning.

    python src/geoseal_phase_mu.py selftest
"""

from __future__ import annotations

import math
import sys
from typing import Optional

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

MU_CIRCULAR = -1.0
MU_SHEAR = 0.0
MU_HYPERBOLIC = +1.0

TONGUE_ORDER = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_PHASES = {t: i * math.pi / 3 for i, t in enumerate(TONGUE_ORDER)}
_PHASE_SPAN = 5 * math.pi / 3  # KO..DR, the full ladder


def phase_deviation_mu(phase1: Optional[float], phase2: Optional[float], mu: float = MU_CIRCULAR) -> float:
    """Normalised deviation in [0, 1]. mu = -1 reproduces the primary EXACTLY.

    None phase = maximum deviation (1.0), matching the primary's contract.
    """
    if phase1 is None or phase2 is None:
        return 1.0
    diff = abs(phase1 - phase2)

    if mu < 0:
        # circular: the ladder closes into a ring, so the far end wraps back around
        if diff > math.pi:
            diff = 2 * math.pi - diff
        return diff / math.pi

    if mu == 0:
        # shear: no curvature at all, pure ordering along the ladder
        return min(1.0, diff / _PHASE_SPAN)

    # hyperbolic: rapidity separation, no period. Normalised by the span so the
    # scale stays comparable to the primary's diff/pi and phase_weight still means something.
    w = math.sqrt(mu)
    return min(1.0, math.sinh(w * diff) / math.sinh(w * _PHASE_SPAN))


def deviation_matrix(mu: float):
    return [[phase_deviation_mu(TONGUE_PHASES[a], TONGUE_PHASES[b], mu) for b in TONGUE_ORDER] for a in TONGUE_ORDER]


def selftest() -> int:
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  {'PASS' if cond else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")

    print("mu = -1 must reproduce the PRIMARY bit-for-bit (else the arm is not comparable)")
    try:
        from src.geoseal import phase_deviation as primary

        worst = 0.0
        for a in TONGUE_ORDER:
            for b in TONGUE_ORDER:
                p, q = TONGUE_PHASES[a], TONGUE_PHASES[b]
                worst = max(worst, abs(primary(p, q) - phase_deviation_mu(p, q, MU_CIRCULAR)))
        check("matches src.geoseal.phase_deviation on all 36 tongue pairs", worst < 1e-12, f"max dev {worst:.2e}")
        check("None handling matches", primary(None, 0.0) == phase_deviation_mu(None, 0.0, -1.0) == 1.0)
    except Exception as exc:
        check("import primary geoseal", False, f"{type(exc).__name__}: {str(exc)[:80]}")

    print("all arms stay in [0,1] so phase_weight keeps its meaning")
    for mu in (MU_CIRCULAR, MU_SHEAR, MU_HYPERBOLIC, 2.0):
        vals = [v for row in deviation_matrix(mu) for v in row]
        check(
            f"mu={mu:+g} in range",
            min(vals) >= -1e-12 and max(vals) <= 1 + 1e-12,
            f"[{min(vals):.3f}, {max(vals):.3f}]",
        )

    print("self-deviation is zero for every arm")
    for mu in (MU_CIRCULAR, MU_SHEAR, MU_HYPERBOLIC):
        m = deviation_matrix(mu)
        check(f"mu={mu:+g} diagonal is 0", all(abs(m[i][i]) < 1e-12 for i in range(6)))

    print("THE STRUCTURAL DIFFERENCE: does the ladder wrap?")
    for mu, label in ((MU_CIRCULAR, "circular"), (MU_SHEAR, "shear"), (MU_HYPERBOLIC, "hyperbolic")):
        m = deviation_matrix(mu)
        ko_dr, ko_ca = m[0][5], m[0][3]
        print(
            f"    mu={mu:+g} ({label:<10}) KO-DR={ko_dr:.4f}  KO-CA={ko_ca:.4f}  "
            f"-> {'DR is NEARER than CA (wraps)' if ko_dr < ko_ca else 'DR is FARTHEST (no wrap)'}"
        )
    m_c, m_h = deviation_matrix(MU_CIRCULAR), deviation_matrix(MU_HYPERBOLIC)
    check("mu=-1 wraps: KO-DR closer than KO-CA", m_c[0][5] < m_c[0][3])
    check("mu=+1 does NOT wrap: KO-DR is maximal", m_h[0][5] >= max(m_h[0]) - 1e-12)
    check(
        "the two arms genuinely disagree",
        abs(m_c[0][5] - m_h[0][5]) > 0.5,
        f"KO-DR differs by {abs(m_c[0][5] - m_h[0][5]):.3f}",
    )

    print("monotone along the ladder for the non-wrapping arms")
    for mu in (MU_SHEAR, MU_HYPERBOLIC):
        row = deviation_matrix(mu)[0]
        check(f"mu={mu:+g} KO-row increases with ladder position", all(row[i] < row[i + 1] + 1e-12 for i in range(5)))

    print()
    print("ALL PASS" if ok else "FAILURES ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selftest())
