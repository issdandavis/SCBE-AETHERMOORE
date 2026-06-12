#!/usr/bin/env python3
"""collatz_manifold — null-test the Collatz tree as a pressure-routing / governance
topology, and place it in its true geometric home (the hyperbolic ball).

The proposal (user + a flattering external AI, 2026-06-11): use the inverse Collatz
tree as a fluidic manifold — even gates (n/2) are pressure drops, odd gates (3n+1)
are accumulators, chamber 1 is the sump; "no dead ends", "safely manages spikes",
"mathematically guaranteed" to drain. And the wider claim: you can MIX systems —
embed a network of hierarchical spaces in hyperbolic space.

House rule: separate the load-bearing from the decorative from the wrong.

  1. DRAIN — "guaranteed" is the open Collatz conjecture; only VERIFIED in range
     (~2^68 in the literature; re-verified live here for our range). Also: draining
     to a root is GENERIC to any rooted tree — not Collatz-specific.
  2. SPIKES — the manifold does not damp spikes, it MANUFACTURES them: odd steps
     triple before parity lets the flow fall. The engineering number is the worst
     excursion peak/n in range (27 -> 9232 is the famous one). Chambers must be
     rated for the verified-range maximum, not the average.
  3. ENERGY LEDGER — pressure cannot passively triple (the 3n+1 chamber must be
     FUNDED). Exact arithmetic ledger: along any draining trajectory,
        sum(log 2 over even steps) - sum(log(3 + 1/n_i) over odd steps) = log n.
     So every trajectory is NET energy-releasing with budget exactly log(n): the
     even drops fund all the odd compressions, with log(n) left over. This is the
     answer to "what do the odd chambers do": they can do work (drive shuttles) up
     to a budget the arithmetic guarantees closes.
  4. TABLE-FREE ROUTING — the genuinely Collatz-specific, load-bearing property:
     the router needs NO routing table. Each chamber decides from its own PARITY
     (an O(1) local rule); a generic tree needs O(N) stored structure to drain.
  5. HYPERBOLIC HOME — ring populations grow geometrically (~1.26^d), so the tree
     CROWDS OUT of the Euclidean plane at a measurable depth (ring count exceeds
     2*pi*d), while hyperbolic ring capacity (2*pi*sinh d) holds every depth with
     exponential room to spare. Trees live natively in the ball — the same
     hierarchy-fit theorem behind the SCBE geometry choice.

No dependencies. Run:
  python scripts/research/collatz_manifold.py [--n 100000] [--depth 40] [--json]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import deque


def step(n: int) -> int:
    """One forward Collatz move — the parity rule IS the router (no table)."""
    return n // 2 if n % 2 == 0 else 3 * n + 1


def trajectory(n: int, cap: int = 100_000) -> list[int]:
    out = [n]
    while n != 1:
        n = step(n)
        out.append(n)
        if len(out) > cap:
            raise RuntimeError(f"trajectory cap exceeded at {out[0]}")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 1+2. Drain verification + excursion audit (memoized walk-and-backfill).
# ─────────────────────────────────────────────────────────────────────────────


def audit_range(N: int) -> dict:
    """Verify every n <= N drains to 1; record stopping times and excursion peaks."""
    stop: dict[int, int] = {1: 0}
    peak: dict[int, int] = {1: 1}
    worst_stop = (1, 0)
    worst_ratio = (1, 1.0, 1)
    worst_peak = (1, 1)
    for start in range(2, N + 1):
        path = []
        n = start
        while n not in stop:
            path.append(n)
            n = step(n)
        s, p = stop[n], peak[n]
        for m in reversed(path):
            s += 1
            p = max(m, p)
            if m <= N:
                stop[m], peak[m] = s, p
        # backfill gives the values for `start` itself
        st, pk = stop[start], peak[start]
        if st > worst_stop[1]:
            worst_stop = (start, st)
        if pk > worst_peak[1]:
            worst_peak = (start, pk)
        ratio = pk / start
        if ratio > worst_ratio[1]:
            worst_ratio = (start, ratio, pk)
    return {
        "range_verified": N,
        "all_drain": True,  # the loop completes only if every start reached 1
        "max_stopping_time": {"n": worst_stop[0], "steps": worst_stop[1]},
        "max_peak": {"n": worst_peak[0], "peak": worst_peak[1]},
        "max_amplification": {
            "n": worst_ratio[0],
            "ratio": round(worst_ratio[1], 1),
            "peak": worst_ratio[2],
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. The energy ledger — what funds the odd chambers.
# ─────────────────────────────────────────────────────────────────────────────


def energy_ledger(n: int) -> dict:
    """Exact budget identity for one trajectory.

    Even steps release log 2 each; odd steps consume log(3 + 1/m) each. The books
    close at exactly log(n): sum(releases) - sum(costs) = log n > 0. Every shuttle
    the odd chambers drive is funded by the even drops, with log(n) to spare.
    """
    release = cost = 0.0
    evens = odds = 0
    for m in trajectory(n)[:-1]:
        if m % 2 == 0:
            release += math.log(2)
            evens += 1
        else:
            cost += math.log(3 + 1 / m)
            odds += 1
    net = release - cost
    return {
        "n": n,
        "even_steps": evens,
        "odd_steps": odds,
        "released": round(release, 6),
        "consumed_by_odd_chambers": round(cost, 6),
        "net": round(net, 6),
        "log_n": round(math.log(n), 6),
        "ledger_residual": abs(net - math.log(n)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4+5. The inverse tree and its geometric home.
# ─────────────────────────────────────────────────────────────────────────────


def inverse_children(m: int) -> list[int]:
    """Predecessors of m in the forward map — the tree grown outward from 1.

    2m is always a child; (m-1)/3 is a child when it is an odd integer > 1
    (excluding the trivial 4->1 backedge so the sump stays a root, not a cycle).
    """
    kids = [2 * m]
    if (m - 1) % 3 == 0:
        c = (m - 1) // 3
        if c > 1 and c % 2 == 1:
            kids.append(c)
    return kids


def ring_counts(depth: int) -> list[int]:
    """Population of each tree ring (BFS shell) outward from the sump."""
    counts = [1]
    ring = deque([1])
    for _ in range(depth):
        nxt = deque()
        for m in ring:
            nxt.extend(inverse_children(m))
        counts.append(len(nxt))
        ring = nxt
    return counts


def embedding_capacity(depth: int) -> dict:
    """Where the tree crowds out of the flat plane vs the hyperbolic ball.

    Unit-separated nodes on a radius-d ring: the plane offers circumference 2*pi*d;
    the hyperbolic plane offers 2*pi*sinh(d). Geometric ring growth (~1.26^d)
    eventually exceeds the linear Euclidean capacity but never the exponential
    hyperbolic one — the quantitative form of 'hierarchies live in the ball'.
    """
    counts = ring_counts(depth)
    euclid_crowd_depth = None
    hyper_ok = True
    rows = []
    for d, c in enumerate(counts):
        if d == 0:
            continue
        e_cap, h_cap = 2 * math.pi * d, 2 * math.pi * math.sinh(d)
        if euclid_crowd_depth is None and c > e_cap:
            euclid_crowd_depth = d
        if c > h_cap:
            hyper_ok = False
        if d % 5 == 0 or d == depth:
            rows.append({"depth": d, "ring": c, "euclid_cap": round(e_cap, 1), "hyper_cap": f"{h_cap:.3g}"})
    gr = (counts[-1] / counts[-6]) ** 0.2 if len(counts) > 6 and counts[-6] else None
    return {
        "max_depth": depth,
        "ring_growth_rate": round(gr, 3) if gr else None,
        "euclid_crowds_at_depth": euclid_crowd_depth,
        "hyperbolic_holds_all_depths": hyper_ok,
        "sample_rings": rows,
    }


def routing_table_cost(depth: int) -> dict:
    """The Collatz-specific property: O(1) parity routing vs O(N) stored tree.

    A generic rooted tree drains too — but only if every chamber stores its parent
    (a routing table the size of the network). The Collatz rule computes the parent
    from the chamber's own number. Verified: forward-stepping every tree node
    reaches its BFS parent with zero stored state.
    """
    nodes = 0
    ring = [1]
    ok = True
    parents = {1: None}
    for _ in range(depth):
        nxt = []
        for m in ring:
            for c in inverse_children(m):
                parents[c] = m
                # the LOCAL rule must recover the stored parent — table-free routing
                if step(c) != m:
                    ok = False
                nxt.append(c)
        nodes += len(nxt)
        ring = nxt
    return {
        "tree_nodes": nodes + 1,
        "generic_tree_routing_state": f"O(N) = {nodes + 1} stored parent pointers",
        "collatz_routing_state": "O(1) — parity of the chamber's own value",
        "local_rule_recovers_parent_everywhere": ok,
    }


# ─────────────────────────────────────────────────────────────────────────────


def run(N: int, depth: int) -> dict:
    ledger_samples = [energy_ledger(n) for n in (7, 27, 703, 97)]
    return {
        "schema": "collatz_manifold_v1",
        "drain_and_spikes": audit_range(N),
        "energy_ledger": ledger_samples,
        "routing": routing_table_cost(min(depth, 25)),
        "geometry": embedding_capacity(depth),
        "verdict": [
            "DRAIN: verified in range (live), CONJECTURE beyond — say 'verified to N', never 'guaranteed'. "
            "And drain-to-root is GENERIC to any rooted tree, not Collatz-specific.",
            "SPIKES: the manifold MANUFACTURES transients, it does not damp them — rate chambers for the "
            "verified-range max peak, not the average ('safely manages spikes' is backwards).",
            "ENERGY: odd chambers cannot triple pressure passively; they are FUNDED by the even drops. "
            "Ledger closes at exactly log(n) net release per injection — that is the shuttle work budget.",
            "LOAD-BEARING & Collatz-specific: table-free O(1) parity routing (generic trees need O(N) state) "
            "+ the closed log(n) ledger.",
            "GEOMETRY: ring growth ~1.26^d crowds out of the Euclidean plane at a finite depth but fits the "
            "hyperbolic ball at every depth — the hierarchy-fit theorem, quantified on THIS tree.",
        ],
    }


def _print(r: dict) -> None:
    print("=== collatz manifold — null-tested as routing topology + geometric object ===\n")
    a = r["drain_and_spikes"]
    print(f"drain: all n <= {a['range_verified']} reach the sump (verified LIVE; beyond range it is conjecture)")
    print(f"  longest path : n={a['max_stopping_time']['n']} takes {a['max_stopping_time']['steps']} steps")
    print(f"  worst peak   : n={a['max_peak']['n']} spikes to {a['max_peak']['peak']:,}")
    ma = a["max_amplification"]
    print(f"  worst ratio  : n={ma['n']} amplifies x{ma['ratio']} (to {ma['peak']:,}) — chamber rating, not a footnote")
    print("\nenergy ledger (releases - odd-chamber costs = log n, exact):")
    for e in r["energy_ledger"]:
        print(
            f"  n={e['n']:>4}: {e['even_steps']:>3} drops release {e['released']:8.4f}, "
            f"{e['odd_steps']:>3} odd chambers consume {e['consumed_by_odd_chambers']:8.4f}, "
            f"net {e['net']:7.4f} = log n {e['log_n']:7.4f} (residual {e['ledger_residual']:.1e})"
        )
    ro = r["routing"]
    print(f"\nrouting ({ro['tree_nodes']} tree nodes):")
    print(f"  generic tree: {ro['generic_tree_routing_state']}")
    recovered = ro["local_rule_recovers_parent_everywhere"]
    print(f"  collatz     : {ro['collatz_routing_state']} (parent recovered everywhere: {recovered})")
    g = r["geometry"]
    print(f"\ngeometry: ring growth ~{g['ring_growth_rate']}^d")
    print(f"  {'depth':>5s} {'ring':>8s} {'euclid cap 2(pi)d':>18s} {'hyperbolic cap 2(pi)sinh(d)':>28s}")
    for row in g["sample_rings"]:
        print(f"  {row['depth']:>5d} {row['ring']:>8d} {row['euclid_cap']:>18} {row['hyper_cap']:>28}")
    print(
        f"  -> crowds out of the Euclidean plane at depth {g['euclid_crowds_at_depth']}; "
        f"hyperbolic holds all {g['max_depth']} depths: {g['hyperbolic_holds_all_depths']}"
    )
    print("\nverdict:")
    for v in r["verdict"]:
        print(f"  - {v}")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="collatz_manifold")
    ap.add_argument("--n", type=int, default=100_000, help="verify drain + excursions for all n <= N")
    ap.add_argument("--depth", type=int, default=40, help="inverse-tree depth for geometry audit")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    r = run(args.n, args.depth)
    print(json.dumps(r, indent=2)) if args.json else _print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
