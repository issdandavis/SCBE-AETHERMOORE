"""Measured comparison: pure-Python minimal cores (observer_dynamics) vs OR-Tools CP-SAT.

The point is to DECIDE, with numbers, whether the CP-SAT dependency is justified for the observer's
explanation/core extraction -- not to adopt it on faith. Both extract the minimal conflict core from a
contradictory decision history (a route carrying both ALLOW and DENY); we check they AGREE and time them as
the history and the conflict grow.

HONEST: ortools is NOT a project dependency. This research script runs only where it is installed
(pip install ortools); CI does not have it. It does not modify observer_dynamics -- it sits beside it.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from python.scbe.observer_dynamics import (  # noqa: E402
    ALLOW,
    DENY,
    DecisionRecord,
    minimal_core,
    no_contradictory_route_decisions,
)

try:
    from ortools.sat.python import cp_model

    HAVE_ORTOOLS = True
except ImportError:  # pragma: no cover - exercised only where ortools is absent
    HAVE_ORTOOLS = False


def make_history(n_records: int, route_size: int) -> List[DecisionRecord]:
    """A history with one contradictory route 'r' (route_size records, half ALLOW half DENY) and the rest on
    unique non-conflicting routes -- so the minimal core is exactly one ALLOW + one DENY on 'r'."""
    recs: List[DecisionRecord] = []
    half = route_size // 2
    for i in range(half):
        recs.append(DecisionRecord(i, "i%d" % i, ALLOW, route="r"))
    for i in range(half, route_size):
        recs.append(DecisionRecord(i, "i%d" % i, DENY, route="r"))
    for i in range(route_size, n_records):
        recs.append(DecisionRecord(i, "i%d" % i, ALLOW, route="u%d" % i))
    return recs


def custom_core(recs: List[DecisionRecord]) -> Tuple[Optional[List[int]], float]:
    viols = no_contradictory_route_decisions(recs)
    if not viols:
        return None, 0.0
    t = time.perf_counter()
    core = minimal_core(recs, no_contradictory_route_decisions, viols[0])
    return sorted(core), time.perf_counter() - t


def cpsat_core(recs: List[DecisionRecord]) -> Tuple[Optional[List[int]], float]:
    """Encode each record as a present-assumption Bool; forbid ALLOW+DENY coexisting on a route via pairwise
    clauses; assume all present; on INFEASIBLE, get the sufficient-assumptions core. Times build+solve+core."""
    t = time.perf_counter()
    routes: dict = {}
    for i, r in enumerate(recs):
        if not r.route:
            continue
        bucket = routes.setdefault(r.route, {"A": [], "D": []})
        if r.decision == ALLOW:
            bucket["A"].append(i)
        elif r.decision == DENY:
            bucket["D"].append(i)
    model = cp_model.CpModel()
    present = [model.NewBoolVar("p%d" % i) for i in range(len(recs))]
    for bucket in routes.values():
        for a in bucket["A"]:
            for d in bucket["D"]:
                model.AddBoolOr([present[a].Not(), present[d].Not()])
    model.AddAssumptions(present)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    dt = time.perf_counter() - t
    if status != cp_model.INFEASIBLE:
        return None, dt
    idx_to_rec = {present[i].Index(): i for i in range(len(recs))}
    core = sorted(idx_to_rec[v] for v in solver.SufficientAssumptionsForInfeasibility())
    return core, dt


def compare(n_records: int, route_size: int) -> dict:
    recs = make_history(n_records, route_size)
    c_core, c_t = custom_core(recs)
    s_core, s_t = cpsat_core(recs) if HAVE_ORTOOLS else (None, float("nan"))
    return {
        "n_records": n_records,
        "route_size": route_size,
        "custom_core_size": len(c_core) if c_core else 0,
        "cpsat_core_size": len(s_core) if s_core else None,
        "both_minimal_pair": (len(c_core) == 2) and (s_core is None or len(s_core) == 2),
        "agree_is_a_valid_pair": _valid_pair(recs, c_core) and (s_core is None or _valid_pair(recs, s_core)),
        "custom_ms": round(c_t * 1000, 3),
        "cpsat_ms": round(s_t * 1000, 3) if HAVE_ORTOOLS else None,
    }


def _valid_pair(recs: List[DecisionRecord], core: Optional[List[int]]) -> bool:
    if not core or len(core) != 2:
        return False
    return {recs[core[0]].decision, recs[core[1]].decision} == {ALLOW, DENY}


GRID = [(50, 4), (200, 20), (1000, 100), (5000, 500)]


def main() -> int:
    print("OBSERVER CORE EXTRACTION -- pure-Python minimal_core vs OR-Tools CP-SAT get_core")
    print("  (ortools %s)\n" % ("AVAILABLE" if HAVE_ORTOOLS else "NOT installed -- custom-only"))
    print(
        "  %9s %10s | %12s %12s | %10s %10s | %s"
        % ("records", "route", "custom_core", "cpsat_core", "custom_ms", "cpsat_ms", "ok")
    )
    for n, k in GRID:
        r = compare(n, k)
        print(
            "  %9d %10d | %12d %12s | %10s %10s | %s"
            % (
                r["n_records"],
                r["route_size"],
                r["custom_core_size"],
                str(r["cpsat_core_size"]),
                r["custom_ms"],
                str(r["cpsat_ms"]),
                "pair+valid" if r["both_minimal_pair"] and r["agree_is_a_valid_pair"] else "DIFF",
            )
        )
    print("\n  Both find a minimal contradicting pair (ALLOW+DENY). Compare the ms columns to judge the dep.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
