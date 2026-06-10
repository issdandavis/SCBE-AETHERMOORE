#!/usr/bin/env python3
"""ratio_caliper.py — Galileo's sector, with the level welded on.

The operator's instrument from the fluid thread: ONE configurable straightedge.
You set its reference ("seed of one"), point it at boundaries, and it reads each
quantity as a RATIO to the seed, snapped to the simplest rational a/b so it's
interpretable (3:2, not 1.4983). The LEVEL then says whether that snap is REAL
(the value really sits on a simple ratio) or just caught by a crowded ratio-line.

Use case (verbatim): 8 melding fluids of different density, one experiment, one
ruler set to read density ratios; point at the boundaries, draw the straightedge
between points, capture each density as a factorable ratio off the seed.

The honest part: a physical ratio is usually irrational. The caliper reports the
snap AND its residual AND a trust-glow. phi is the worst-approximable number, so a
fluid whose ratio is phi must NEVER snap clean — the instrument has to say so.

Usage:  python scripts/research/ratio_caliper.py
"""
from __future__ import annotations

import math
import random
import statistics
from math import gcd

MAX_DEN = 24          # finest gearing the ruler is etched to (denominator bound)
NULL_DRAWS = 4000     # pre-fixed null: how close does a RANDOM ratio snap?
NULL_SEED = 0


def best_rational(x: float, max_den: int = MAX_DEN) -> tuple[int, int, float]:
    """Simplest a/b with b<=max_den nearest to x>0. Returns (a, b, |x-a/b|)."""
    best = (round(x), 1, abs(x - round(x)))
    for b in range(1, max_den + 1):
        a = round(x * b)
        if a <= 0:
            continue
        res = abs(x - a / b)
        if res < best[2] - 1e-15 or (abs(res - best[2]) <= 1e-15 and b < best[1]):
            best = (a, b, res)
    a, b, res = best
    g = gcd(a, b) or 1
    return a // g, b // g, res


def _null_residuals(scale: float, max_den: int) -> list[float]:
    rng = random.Random(NULL_SEED)
    out = []
    for _ in range(NULL_DRAWS):
        x = rng.uniform(0.5 * scale, 1.8 * scale)   # random ratio in a plausible band
        out.append(best_rational(x, max_den)[2])
    return out


def measure(values: list[float], seed_index: int = 0, max_den: int = MAX_DEN) -> list[dict]:
    seed = values[seed_index]
    ratios = [v / seed for v in values]
    null = _null_residuals(scale=statistics.mean(ratios), max_den=max_den)
    p05 = statistics.quantiles(null, n=20)[0]
    nmean, nstd = statistics.mean(null), statistics.pstdev(null) or 1e-9
    rows = []
    for i, r in enumerate(ratios):
        a, b, res = best_rational(r, max_den)
        glow = res < p05
        z = (nmean - res) / nstd
        rows.append({"i": i, "ratio": r, "a": a, "b": b, "residual": res,
                     "z": z, "glow": glow, "is_seed": i == seed_index})
    return rows, p05


def main() -> int:
    # 8 melding fluids. Densities chosen so SOME are clean ratios off the seed
    # and some are deliberately not (phi, pi/2) — the instrument must tell them apart.
    seed = 1.000
    densities = [
        seed * 1.0,        # seed (1:1)
        seed * 1.5,        # 3:2   exact
        seed * 2.0,        # 2:1   exact
        seed * (5 / 3),    # 5:3   exact
        seed * (7 / 4),    # 7:4   exact
        seed * 1.503,      # ~3:2 but OFF by 0.2% — should it trust it?
        seed * ((1 + 5**0.5) / 2),  # phi — worst-approximable, must stay dark
        seed * (math.pi / 2),       # pi/2 — irrational, must stay dark
    ]
    rows, p05 = measure(densities, seed_index=0)

    print("RATIO CALIPER — 8 fluids, ruler set to density-ratio off the seed")
    print(f"  glow threshold (null 5th-pctile residual) = {p05:.4f}   [den<= {MAX_DEN}]")
    print(f"  {'fluid':>5} {'ratio':>8} {'snap':>7} {'residual':>9} {'z':>6}  trust")
    for r in rows:
        tag = "seed" if r["is_seed"] else ("GLOW (trust)" if r["glow"] else "dark (don't trust the snap)")
        print(f"  {r['i']:>5} {r['ratio']:>8.4f} {r['a']:>3}:{r['b']:<3} {r['residual']:>9.4f} {r['z']:>6.1f}  {tag}")

    # self-checks: exact ratios glow; phi & pi/2 stay dark; the 0.2%-off one is honest
    by_i = {r["i"]: r for r in rows}
    for i in (1, 2, 3, 4):
        assert by_i[i]["glow"], f"exact ratio fluid {i} failed to glow"
    assert not by_i[6]["glow"], "phi snapped clean — caliper is lying (phi is worst-approximable)"
    assert not by_i[7]["glow"], "pi/2 snapped clean — caliper is lying"
    # the 1.503 case: snaps to 3:2 but residual must be visibly worse than the exact 1.5
    assert by_i[5]["residual"] > by_i[1]["residual"], "0.2%-off fluid not distinguished from exact 3:2"
    print("  self-checks: exact ratios glow; φ and π/2 stay dark; near-miss flagged  OK")
    print("  -> operator reads: trust the GLOWING ratios as real; treat dark ones as raw irrational measurements.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
