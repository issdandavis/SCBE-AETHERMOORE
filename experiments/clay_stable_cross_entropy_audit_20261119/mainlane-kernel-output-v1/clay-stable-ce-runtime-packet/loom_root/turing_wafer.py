#!/usr/bin/env python3
"""turing_wafer.py -- Mobius tapes on every row and column, edge-to-edge, as one wafer.

Issac, 2026-07-31: "muli mubiious turing tapes for each conalgs row adn colame and edge toe
dge for a conwytor effect across grid space as a turing wafer and you then tile them over
the thign" -- and before that, "thats becuae we use a mobiius".

WHY MOBIUS IS THE RIGHT TAPE AND NOT A DECORATION. A tape joined with a half twist returns
the head to cell 0 with the frame INVERTED, so a finite tape of length L behaves as an
infinite tape of period 2L whose polarity alternates every pass. That is exactly
negabinary's grading, sigma(d) = (-1)^d, which balanced_state.py already builds and verifies
-- the same object stated as a surface instead of as a number system. A plain cylindrical
join gives period L and no sign; the twist is what buys the second half.

THE WAFER. Each tongue's sheet is 11 floors x 16 slots. Every row is a Mobius tape of length
16, every column a Mobius tape of length 11: 27 tapes per tongue, 162 across the six. Running
off the end of a row enters the column that shares that cell -- that is the conveyor, and it
is what makes the sheet one machine rather than 27.

WHAT IS ACTUALLY MEASURED. Coverage and orbit. A head starts at one cell with positive frame
and follows the rule; the question is how many DISTINCT (cell, polarity) states it reaches
before it repeats. There are 176 cells x 2 polarities = 352 states available per sheet. If
the orbit is 352 the wafer is a single Hamiltonian cycle over the doubled sheet and every
cell is visited in both frames. Anything less and the sheet fragments into separate orbits
that never exchange -- which would make the conveyor a claim rather than a mechanism.

    python turing_wafer.py
"""
from __future__ import annotations

import json
from math import gcd
from pathlib import Path

GRID = Path(r"C:\dev\clay-memory-architecture\src\opcode_grid.json")
F, S = 11, 16          # floors, slots -- the sheet


def step(state, mode):
    """One move, and the first version of this was wrong in a way the control caught.

    WRONG (v1): run along a row, and at the end reset slot to 0 and hand to the column.
    That resets the orthogonal coordinate, so the head walks row 0 into column 0 and
    closes after 27 states -- identical to the cylinder, 0 cells in both frames. The
    twist bought nothing because the walk never went anywhere for it to accumulate.

    RIGHT: advance BOTH coordinates every step. The head rides the row tape and the
    column tape simultaneously, which is what edge-to-edge actually means -- leaving a
    row does not put you at the start of a column, it puts you one further along both.
    Because gcd(11,16) = 1 the diagonal visits all 176 cells before returning, and the
    half twist flips polarity on each wrap so the true period is 352. Coprimality is
    load-bearing: on a 12 x 16 sheet gcd = 4 and this fragments into four orbits.
    """
    f, s, pol, run = state
    ns, nf = s + 1, f + 1

    # Row and column are independent tapes.  Crossing one seam applies one
    # half-twist; crossing their shared corner applies two half-twists.  The
    # first implementation collapsed that corner to a boolean "any seam"
    # event, incorrectly turning two crossings into one.  Preserve crossing
    # parity so the product surface carries the charge of both walls.
    seam_crossings = int(ns >= S) + int(nf >= F)
    if mode == "mobius" and seam_crossings % 2:
        pol = -pol
    return (nf % F, ns % S, pol, run)


def orbit(start, mode="mobius"):
    seen, order = set(), []
    st = start
    while st not in seen:
        seen.add(st)
        order.append(st)
        st = step(st, mode)
    return order


def cylinder_step(state):
    """Control: identical diagonal walk, NO twist. Isolates what the twist buys."""
    f, s, pol, run = state
    return ((f + 1) % F, (s + 1) % S, pol, run)


def cyl_orbit(start):
    seen, order = set(), []
    st = start
    while st not in seen:
        seen.add(st)
        order.append(st)
        st = cylinder_step(st)
    return order


def main() -> int:
    d = json.loads(GRID.read_text(encoding="utf-8"))
    tongues = d["tongues"]
    cells = [c for fl in d["overlay"] for c in fl if c and "byte" in c]

    print("=" * 74)
    print("TURING WAFER -- Mobius tapes, row and column, edge to edge")
    print("=" * 74)
    print("sheet      : %d floors x %d slots = %d cells" % (F, S, F * S))
    print("tapes/sheet: %d rows + %d columns = %d" % (F, S, F + S))
    print("tongues    : %d  ->  %d tapes total" % (len(tongues), len(tongues) * (F + S)))
    print("occupied   : %d of %d cells carry a real opcode" % (len(cells), F * S))
    print()

    start = (0, 0, +1, 0)
    mob = orbit(start)
    cyl = cyl_orbit(start)
    total = F * S * 2

    print("ORBIT from (floor 0, slot 0, +frame)")
    print("  Mobius   : %4d states   of %d available (cells x 2 polarities)" % (len(mob), total))
    print("  cylinder : %4d states   <- control, no twist" % len(cyl))
    print()

    cov = {(f, s) for f, s, _, _ in mob}
    both = {(f, s) for f, s in cov
            if (f, s, +1, 0) in set((a, b, c, dd) for a, b, c, dd in mob)
            and (f, s, -1, 0) in set((a, b, c, dd) for a, b, c, dd in mob)}
    print("  distinct cells reached : %d of %d" % (len(cov), F * S))
    print("  reached in BOTH frames : %d" % len(both))
    print()

    # why the number is what it is
    print("WHY. The head alternates a %d-run and an %d-run, so a full circuit of both tapes"
          % (S, F))
    print("is lcm-driven: gcd(%d,%d) = %d, lcm = %d." % (F, S, gcd(F, S), F * S // gcd(F, S)))
    print("11 and 16 are coprime, which is the only reason a single orbit can reach every")
    print("cell -- a sheet of 12 x 16 would fragment into gcd = 4 separate orbits that")
    print("never exchange, and the conveyor would be four conveyors.")
    print()

    if len(mob) == total:
        print("VERDICT: single Hamiltonian orbit over the doubled sheet. Every cell visited")
        print("in both frames before any repeat. The conveyor is a mechanism.")
    elif len(mob) > len(cyl):
        print("VERDICT: the twist doubles the orbit as designed (%d vs %d), but the walk does"
              % (len(mob), len(cyl)))
        print("not reach every state -- it closes early, so the sheet holds more than one orbit.")
    else:
        print("VERDICT: the twist bought nothing here. The rule closes before the frame flips")
        print("can accumulate, so this is a cylinder wearing a Mobius name.")
    print()
    print("MEASUREMENT ONLY. Nothing trained, nothing written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
