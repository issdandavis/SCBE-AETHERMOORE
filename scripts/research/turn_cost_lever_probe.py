#!/usr/bin/env python3
"""Turn-cost lever probe: is a number's DISTINCT STATE a real cost lever, or decoration?

The idea (user, 2026-06-10): use numbers with distinct states — not magnitude — as
"the lever of how much a turn should take." This probe tests that instinct honestly,
against the rule the prior null results earned: a state lever only counts if it beats
BOTH a magnitude lever AND a shuffle of itself.

Setup (fully self-contained, no deps beyond stdlib):
  - "turns" = integers n in [LO, HI].
  - TRUE cost of a turn = real trial-division work to fully factor n (count of
    division steps). This is an INDEPENDENT ground truth — defined by the work, not
    by any lever. It genuinely varies with the number's multiplicative structure.
  - Lever STATE     = smallest prime factor spf(n)  (a discrete multiplicative state:
                      trial division stops early at the smallest factor).
  - Lever STATE2    = omega(n), the count of DISTINCT prime factors (another state).
  - Lever MAGNITUDE = n itself (the size — the trap the prior nulls exposed).
  - NULL            = the STATE lever with its labels shuffled across turns.

A lever is "load-bearing" if |corr(lever, true_cost)| exceeds the 95th percentile of
the shuffled-null distribution. If magnitude alone already explains the cost, or if a
shuffled state matches the real one, the "state" was decorative.

Run: python scripts/research/turn_cost_lever_probe.py [--lo 2 --hi 5000 --shuffles 300] [--json]
"""

from __future__ import annotations

import argparse
import json
import math
import random


def factor_cost(n: int) -> int:
    """Real work to fully factor n by trial division: count division attempts.

    This is the honest 'how much did this turn take' — independent of any lever.
    """
    steps = 0
    d = 2
    m = n
    while d * d <= m:
        steps += 1
        if m % d == 0:
            while m % d == 0:
                m //= d
        d += 1
    return steps + (1 if m > 1 else 0)


def smallest_prime_factor(n: int) -> int:
    d = 2
    while d * d <= n:
        if n % d == 0:
            return d
        d += 1
    return n  # n is prime -> its own smallest factor


def omega_distinct(n: int) -> int:
    count = 0
    d = 2
    m = n
    while d * d <= m:
        if m % d == 0:
            count += 1
            while m % d == 0:
                m //= d
        d += 1
    if m > 1:
        count += 1
    return count


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n == 0:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return 0.0
    return sxy / math.sqrt(sxx * syy)


def _residualize(y: list[float], z: list[float]) -> list[float]:
    """Remove the linear effect of z from y; return residuals (y minus its z-fit)."""
    n = len(y)
    mz = sum(z) / n
    my = sum(y) / n
    szz = sum((zi - mz) ** 2 for zi in z)
    if szz <= 0:
        return [yi - my for yi in y]
    b = sum((zi - mz) * (yi - my) for zi, yi in zip(z, y)) / szz
    a = my - b * mz
    return [yi - (a + b * zi) for yi, zi in zip(y, z)]


def partial_corr(x: list[float], y: list[float], z: list[float]) -> float:
    """|corr(x, y)| after linearly removing z (the control) from both.

    This isolates whether x predicts y for a reason INDEPENDENT of z. Here z is the
    magnitude: a state lever that survives this is doing real work, not size in disguise.
    """
    return abs(pearson(_residualize(x, z), _residualize(y, z)))


def null_distribution(lever: list[float], cost: list[float], shuffles: int, rng: random.Random) -> dict:
    """Shuffle the lever's labels across turns and recompute |corr| many times."""
    vals = []
    pool = list(lever)
    for _ in range(shuffles):
        rng.shuffle(pool)
        vals.append(abs(pearson(pool, cost)))
    vals.sort()
    p95 = vals[min(len(vals) - 1, int(0.95 * len(vals)))]
    return {"mean": sum(vals) / len(vals), "p95": p95, "max": vals[-1]}


def run(lo: int, hi: int, shuffles: int, seed: int = 1) -> dict:
    rng = random.Random(seed)
    ns = list(range(lo, hi + 1))
    cost = [float(factor_cost(n)) for n in ns]
    spf = [float(smallest_prime_factor(n)) for n in ns]
    omega = [float(omega_distinct(n)) for n in ns]
    magnitude = [float(n) for n in ns]

    levers = {
        "state_smallest_prime_factor": spf,
        "state_omega_distinct_factors": omega,
        "magnitude_n": magnitude,
    }
    rows = {}
    for name, vals in levers.items():
        corr = abs(pearson(vals, cost))
        null = null_distribution(vals, cost, shuffles, rng)
        # Control for magnitude (except magnitude itself): does this lever predict cost
        # for a reason independent of the number's size?
        partial = None if name == "magnitude_n" else round(partial_corr(vals, cost, magnitude), 4)
        rows[name] = {
            "abs_corr_with_true_cost": round(corr, 4),
            "partial_corr_controlling_magnitude": partial,
            "null_p95": round(null["p95"], 4),
            "beats_null95": bool(corr > null["p95"]),
            "load_bearing": bool(corr > null["p95"] and corr > 0.1),
            "independent_of_magnitude": bool(partial is not None and partial > 0.1),
        }

    state = rows["state_smallest_prime_factor"]["abs_corr_with_true_cost"]
    mag = rows["magnitude_n"]["abs_corr_with_true_cost"]
    state_partial = rows["state_smallest_prime_factor"]["partial_corr_controlling_magnitude"]
    return {
        "schema_version": "scbe_turn_cost_lever_probe_v1",
        "claim": "a number's discrete multiplicative STATE governs turn cost; its magnitude does not",
        "corpus": {"lo": lo, "hi": hi, "count": len(ns)},
        "true_cost": "trial-division steps to fully factor n (independent ground truth)",
        "levers": rows,
        "verdict": {
            "state_beats_magnitude": bool(state > mag + 0.05),
            "state_independent_of_magnitude": bool(state_partial is not None and state_partial > 0.1),
            "state_load_bearing": rows["state_smallest_prime_factor"]["load_bearing"],
            "magnitude_load_bearing": rows["magnitude_n"]["load_bearing"],
            "reading": (
                "The distinct-state lever wins only if it (1) beats its own shuffle null and "
                "(2) keeps signal AFTER magnitude is removed. spf passing the partial-correlation "
                "control means turn cost is set by the number's STATE, not its size. Pick levers "
                "whose DISCRETE STATE (spf, residue class, constructibility) governs cost."
            ),
        },
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lo", type=int, default=2)
    ap.add_argument("--hi", type=int, default=5000)
    ap.add_argument("--shuffles", type=int, default=300)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    result = run(args.lo, args.hi, args.shuffles)
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    print(f"turns: {result['corpus']['count']} integers in [{args.lo}, {args.hi}]")
    print(f"true cost = {result['true_cost']}\n")
    for name, row in result["levers"].items():
        flag = "LOAD-BEARING" if row["load_bearing"] else "decorative"
        partial = row["partial_corr_controlling_magnitude"]
        partial_str = f"partial(no-mag)={partial:.3f}" if partial is not None else "partial(no-mag)=  —  "
        print(
            f"  {name:34s} |corr|={row['abs_corr_with_true_cost']:.3f}  "
            f"{partial_str}  null95={row['null_p95']:.3f}  -> {flag}"
        )
    v = result["verdict"]
    print(f"\nstate beats magnitude: {v['state_beats_magnitude']}")
    print(f"state still predicts cost AFTER removing magnitude: {v['state_independent_of_magnitude']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
