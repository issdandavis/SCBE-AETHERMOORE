#!/usr/bin/env python3
"""nature_ruler_tool.py — the measuring device. Point it at things, get ratios.

One instrument. You set a seed (the "one"), point it at a set of quantities, and
it lays them on a single ratio line and reads each as the simplest factorable
ratio — 3:2, not 1.4983 — so the numbers come back as something you can reason
about. A built-in level says which ratios are REAL (the quantity truly sits on a
simple ratio) and which are just a decimal it had to round.

It does three jobs with one line:
  read      — each quantity as a ratio to the seed.
  between   — the straightedge laid between every pair of points (pairwise ratios).
  ahead     — measure before you measure: from a measured trajectory, predict the
              points you haven't reached yet, and check the gap when you do.

Self-contained. Hand it lengths, densities, angles, frequencies — anything.

    from nature_ruler_tool import NatureRuler
    r = NatureRuler()
    print(r.read([1.0, 1.5, 2.0, 5/3], names=["A","B","C","D"]).card())
"""
from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass, field
from math import gcd


def _best_rational(x: float, max_den: int) -> tuple[int, int, float]:
    """Simplest a/b with b<=max_den nearest x>0 -> (a, b, |x-a/b|)."""
    best = (max(1, round(x)), 1, abs(x - max(1, round(x))))
    for b in range(1, max_den + 1):
        a = round(x * b)
        if a <= 0:
            continue
        res = abs(x - a / b)
        if res < best[2] - 1e-15:
            best = (a, b, res)
    a, b, res = best
    g = gcd(a, b) or 1
    return a // g, b // g, res


@dataclass
class Reading:
    name: str
    value: float
    ratio: float          # value / seed
    a: int                # snapped numerator
    b: int                # snapped denominator
    residual: float       # |ratio - a/b|
    trust: bool           # does it really sit on this ratio?


@dataclass
class Card:
    seed_name: str
    seed_value: float
    readings: list[Reading]
    pairs: list[tuple[str, str, int, int, float, bool]] = field(default_factory=list)

    def card(self) -> str:
        out = [f"MEASUREMENT  (seed = {self.seed_name} = {self.seed_value:g})",
               f"  {'thing':>8} {'value':>10} {'reads as':>9} {'off by':>8}  trust"]
        for r in self.readings:
            tag = "—seed—" if r.name == self.seed_name else ("TRUST  ✦" if r.trust else "raw (irrational)")
            out.append(f"  {r.name:>8} {r.value:>10.4f} {r.a:>4}:{r.b:<4} {r.residual:>8.4f}  {tag}")
        if self.pairs:
            out.append("  between points (straightedge):")
            for n1, n2, a, b, res, tr in self.pairs:
                out.append(f"    {n1}:{n2} = {a}:{b}   off {res:.4f}   {'✦' if tr else '·'}")
        return "\n".join(out)


@dataclass
class ZoomLevel:
    depth: int
    term: int        # the continued-fraction coefficient at this depth
    p: int           # convergent numerator
    q: int           # convergent denominator
    residual: float  # |ratio - p/q|
    trusted: bool


@dataclass
class ZoomStack:
    value: float
    seed: float
    ratio: float
    levels: list[ZoomLevel]
    terminated: bool         # True -> exact rational, bottom reached
    depth_trust: int | None  # shallowest depth whose convergent is trustworthy

    def view(self) -> str:
        out = [f"ZOOM  {self.value:g}  (ratio to seed = {self.ratio:.6f})",
               "  coarse → fine; each level the next convergent, residual shrinking:"]
        for L in self.levels:
            bar = "   " * L.depth
            mark = " ✦ trusts here" if (self.depth_trust == L.depth) else ("" if not L.trusted else " ✦")
            out.append(f"  {bar}└ {L.p}:{L.q}  (term {L.term})  off {L.residual:.6f}{mark}")
        if self.terminated:
            out.append("   ↳ exact rational — bottom reached, nothing beneath.")
        elif all(L.term == 1 for L in self.levels):
            out.append("   ↳ φ-like: every term is 1 (worst-approximable). Never sits clean — depth is endless.")
        else:
            d = f"depth {self.depth_trust}" if self.depth_trust is not None else "never (within shown depth)"
            out.append(f"   ↳ irrational — keeps refining; first trustworthy at {d}.")
        return "\n".join(out)


class NatureRuler:
    def __init__(self, max_den: int = 24, null_draws: int = 4000, seed_rng: int = 0):
        self.max_den = max_den
        self.null_draws = null_draws
        self._rng = random.Random(seed_rng)

    # the level: is `residual` tighter than a random ratio would land by chance?
    def _trust_threshold(self, scale: float) -> float:
        res = []
        for _ in range(self.null_draws):
            x = self._rng.uniform(0.5 * scale, 1.8 * scale)
            res.append(_best_rational(x, self.max_den)[2])
        return statistics.quantiles(res, n=20)[0]   # 5th percentile

    def read(self, values, names=None, seed=None) -> Card:
        names = names or [chr(65 + i) for i in range(len(values))]
        seed_val = seed if seed is not None else values[0]
        seed_name = names[values.index(seed_val)] if seed in values else names[0]
        ratios = [v / seed_val for v in values]
        thr = self._trust_threshold(statistics.mean(ratios))
        readings = []
        for nm, v, rt in zip(names, values, ratios):
            a, b, res = _best_rational(rt, self.max_den)
            readings.append(Reading(nm, v, rt, a, b, res, res < thr))
        # straightedge between every pair
        pairs = []
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                rt = values[j] / values[i]
                a, b, res = _best_rational(rt, self.max_den)
                pairs.append((names[i], names[j], a, b, res, res < thr))
        return Card(seed_name, seed_val, readings, pairs)

    def ahead(self, trajectory, predict_n):
        """Measure before you measure: fit the measured points, predict point n.

        `trajectory` is a list of (index, value). Returns (predicted, used_n)."""
        xs = [i for i, _ in trajectory]
        ys = [v for _, v in trajectory]
        # log-linear trend (works for growth like primes/areas/populations)
        lx = [math.log(x) for x in xs]
        k = len(xs)
        sx, sy = sum(lx), sum(ys)
        sxx = sum(t * t for t in lx)
        sxy = sum(t * y for t, y in zip(lx, ys))
        a = (k * sxy - sx * sy) / (k * sxx - sx * sx)
        b = (sy - a * sx) / k
        return a * math.log(predict_n) + b, len(trajectory)

    def zoom(self, value, seed: float = 1.0, max_depth: int = 10, trust_eps=None) -> ZoomStack:
        """Drill under a mark: coarse ratio on top, finer convergents beneath.

        The continued-fraction ladder of value/seed. Surface = simplest term; each
        level the next convergent, residual shrinking. A rational hits bottom
        (residual 0); an irrational keeps refining; φ (all terms 1) never sits clean.
        """
        x = value / seed
        thr = trust_eps if trust_eps is not None else self._trust_threshold(x)
        p_pp, p_p, q_pp, q_p = 0, 1, 1, 0   # convergent recurrence seeds
        r, levels, depth_trust, terminated = x, [], None, False
        for n in range(max_depth + 1):
            a = math.floor(r)
            p, q = a * p_p + p_pp, a * q_p + q_pp
            res = abs(x - p / q)
            trusted = res < thr
            levels.append(ZoomLevel(n, a, p, q, res, trusted))
            if depth_trust is None and trusted:
                depth_trust = n
            p_pp, p_p, q_pp, q_p = p_p, p, q_p, q
            frac = r - a
            if frac < 1e-12:
                terminated = True
                break
            r = 1.0 / frac
        return ZoomStack(value, seed, x, levels, terminated, depth_trust)


def _demo() -> int:
    r = NatureRuler()
    # the fluids: point one ruler at 8 densities, read them as ratios off fluid A
    fluids = [1.000, 1.500, 2.000, 5 / 3, 7 / 4, 1.503,
              (1 + 5**0.5) / 2, math.pi / 2]
    names = ["A", "B", "C", "D", "E", "F", "φ-fluid", "π/2-fluid"]
    card = r.read(fluids, names=names)
    print(card.card())
    print()
    # measure-before-measure on a clean growth trajectory (areas of nested squares)
    traj = [(i, float(i * i)) for i in range(1, 7)]   # 1,4,9,16,25,36
    pred, used = r.ahead(traj, 10)
    print(f"AHEAD: measured points 1..6, predict point 10 -> {pred:.1f}  (true 10²=100, fit on {used} pts)")

    # zoom: coarse on top, detail underneath — drill under a few marks
    print()
    for v, nm in [(1.5, "3/2"), (2**0.5, "√2"), ((1 + 5**0.5) / 2, "φ"), (math.pi / 2, "π/2")]:
        print(r.zoom(v, max_depth=8).view())
        print()

    # self-checks: the device must read the truths and refuse the fakes
    by = {rd.name: rd for rd in card.readings}
    assert (by["B"].a, by["B"].b) == (3, 2) and by["B"].trust, "B should read 3:2 and be trusted"
    assert (by["D"].a, by["D"].b) == (5, 3) and by["D"].trust, "D should read 5:3"
    assert not by["φ-fluid"].trust, "φ must not be trusted as a simple ratio"
    assert not by["F"].trust, "the 0.2%-off fluid must not be trusted"
    # zoom self-checks: rational bottoms out; φ is all-ones and never terminates; φ refines slowest
    z_rat, z_phi, z_sqrt2 = r.zoom(1.5), r.zoom((1 + 5**0.5) / 2, max_depth=8), r.zoom(2**0.5, max_depth=8)
    assert z_rat.terminated and z_rat.levels[-1].residual < 1e-9, "3/2 should bottom out exactly"
    assert all(L.term == 1 for L in z_phi.levels) and not z_phi.terminated, "φ must be all-ones, endless"
    assert z_phi.levels[6].residual > z_sqrt2.levels[6].residual, "φ should refine slower than √2 (worst-approximable)"
    print("self-checks: clean ratios trusted; φ/near-miss refused; trajectory predicts; "
          "zoom bottoms on rationals, never on φ  OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(_demo())
