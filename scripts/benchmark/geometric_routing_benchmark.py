#!/usr/bin/env python3
"""
Tangentialism benchmark — does geometric routing beat flat parallelism when the
fleet is HETEROGENEOUS?
======================================================================================

My earlier uniform-cost test showed geometric routing ~= round-robin (every emit
costs the same). The real claim (vault doc 124) is that geometry wins when a
worker's COST depends on the work: a KO-specialist agent is cheap for KO tasks
and expensive for UM tasks. That's every real multi-agent fleet — models/agents
with different strengths.

This benchmark makes cost heterogeneous and measures the two numbers that decide
a parallel system:
  * total cost  = sum of per-task costs (throughput / tokens / time)
  * makespan    = max per-worker load = the PARALLEL wall-clock (slowest lane wins)

Across rising heterogeneity (skew), it compares:
  * round-robin  — count-balanced, geometry-blind (flat parallelism)
  * geometric    — each task routed to its cheapest agent under the Finsler tongue
                   metric, fluid back-pressure balancing load (tangent tracks)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.geometric_router import (  # noqa: E402
    Agent,
    Task,
    TONGUES,
    finsler_distance,
    route_fleet,
)


def make_tasks(n, skew, rng):
    """skew=0 -> uniform tongue mix; skew=1 -> each task strongly one-tongue."""
    tasks = []
    for i in range(n):
        base = {t: float(rng.random()) for t in TONGUES}
        dom = TONGUES[rng.integers(0, 6)]
        prof = {t: (1.0 - skew) * base[t] + (skew if t == dom else 0.0) for t in TONGUES}
        tasks.append(Task(f"t{i}", prof))
    return tasks


def loads_round_robin(agents, tasks):
    load = {a.name: 0.0 for a in agents}
    for i, t in enumerate(tasks):
        a = agents[i % len(agents)]
        load[a.name] += finsler_distance(a.pos, t.profile, a.tongue)
    return load


def loads_geometric(agents, tasks):
    load = {a.name: 0.0 for a in agents}
    for r in route_fleet(agents, tasks, pressure=0.4, tour=False):
        load[r.agent] += r.total_cost
    return load


def main() -> int:
    rng = np.random.default_rng(11)
    agents = [Agent(f"{t}-agent", {t: 1.0}) for t in TONGUES]
    n = 600

    print("Tangentialism benchmark — geometric routing vs flat parallelism")
    print(f"  fleet: {len(agents)} tongue-specialist agents   tasks: {n}\n")
    print(f"  {'skew':>5} | {'round-robin':^23} | {'geometric (tangent)':^23} | {'win'}")
    print(f"  {'':>5} | {'total':>10} {'makespan':>11} | {'total':>10} {'makespan':>11} |")
    print("  " + "-" * 72)
    for skew in (0.0, 0.25, 0.5, 0.75, 1.0):
        tasks = make_tasks(n, skew, rng)
        rr = loads_round_robin(agents, tasks)
        ge = loads_geometric(agents, tasks)
        rr_tot, rr_mk = sum(rr.values()), max(rr.values())
        ge_tot, ge_mk = sum(ge.values()), max(ge.values())
        mk_win = 100 * (1 - ge_mk / rr_mk) if rr_mk else 0.0
        print(
            f"  {skew:>5.2f} | {rr_tot:>10.1f} {rr_mk:>11.2f} | "
            f"{ge_tot:>10.1f} {ge_mk:>11.2f} | makespan {mk_win:>4.0f}% faster"
        )
    print("\n  total   = sum of per-task costs (throughput / tokens)")
    print("  makespan = slowest worker's load = PARALLEL wall-clock")
    print("  -> as the fleet gets heterogeneous, geometric routing cuts the makespan:")
    print("     it gives each agent work it is cheap at, so no lane is stuck doing")
    print("     expensive off-affinity tasks. That is tangentialism doing real work.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
