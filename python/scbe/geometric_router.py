"""
Geometric fleet router — tangentialism.
=======================================

Elevates flat parallelism (round-robin chunks) to GEOMETRIC routing: every agent
/ worker is a TANGENT VECTOR tracing a geodesic through a tongue-weighted
hyperbolic lattice, advected by a fluid flow-field toward its work. Beams of
light through lattices of different structure; ray-tracing the optimal route.

The geometry is the user's own (vault docs 123/124):
  * Nodes (tasks, agents, URLs) live in 6-D Sacred-Tongue space (KO AV RU CA UM DR).
  * Base metric = Poincare ball (hyperbolic): safe/near-center is cheap, drift to
    the boundary is exponentially expensive  ->  d_H = arcosh(1 + 2|u-v|^2 / ((1-|u|^2)(1-|v|^2))).
  * Finsler layer: distance also depends on WHO walks. An agent's tongue identity
    scales each axis by phi^k * w_k (golden-ratio tongue tensor, doc 124), so the
    SAME route has different length for a KO agent vs a UM agent. Tasks route to the
    agent whose identity makes them geometrically closest.
  * Geodesics (the "rays") are straight lines in the Klein model — we map ball->Klein,
    interpolate, map back, to ray-trace the actual path through the lattice.
  * Fluid routing: agents flow like an incompressible fluid — a pressure term repels
    them off congested tasks (space-materials analog: streamlines that don't pile up).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

import numpy as np

TONGUES: Tuple[str, ...] = ("KO", "AV", "RU", "CA", "UM", "DR")
PHI = (1.0 + 5.0 ** 0.5) / 2.0
PHI_W = np.array([PHI ** k for k in range(6)])  # 1, 1.62, 2.62, 4.24, 6.85, 11.09
_EPS = 1e-9
_BALL = 0.93  # squash factor keeping points strictly inside the unit ball


def to_vec(profile) -> np.ndarray:
    """A tongue profile (dict or 6-seq) -> a raw 6-vector."""
    if isinstance(profile, dict):
        return np.array([float(profile.get(t, 0.0)) for t in TONGUES])
    v = np.asarray(profile, dtype=float)
    if v.shape != (6,):
        raise ValueError("tongue profile must be 6-D (KO AV RU CA UM DR)")
    return v


def to_ball(v: np.ndarray) -> np.ndarray:
    """Map a raw 6-vector into the open Poincare unit ball (||x|| < 1)."""
    v = np.asarray(v, dtype=float)
    n = float(np.linalg.norm(v))
    if n < _EPS:
        return np.zeros(6)
    return v * (_BALL * np.tanh(n) / n)


def poincare_distance(u: np.ndarray, v: np.ndarray) -> float:
    """Hyperbolic distance between two points in the Poincare ball."""
    u = np.asarray(u, float)
    v = np.asarray(v, float)
    nu = min(float(u @ u), 1.0 - _EPS)
    nv = min(float(v @ v), 1.0 - _EPS)
    diff = u - v
    arg = 1.0 + 2.0 * float(diff @ diff) / ((1.0 - nu) * (1.0 - nv))
    return float(np.arccosh(max(arg, 1.0)))


def tongue_weights(agent) -> np.ndarray:
    """Normalize an agent's tongue identity to weights that sum to 1."""
    w = to_vec(agent) if not isinstance(agent, np.ndarray) else agent
    w = np.clip(w, 0.0, None)
    s = float(w.sum())
    return w / s if s > _EPS else np.full(6, 1.0 / 6.0)


def agent_scale(agent) -> np.ndarray:
    """The per-axis Finsler scaling sqrt(phi^k * w_k) for an agent identity.
    Constant for a given agent — cache it and reuse via finsler_scaled()."""
    return np.sqrt(PHI_W * tongue_weights(agent) + _EPS)


def finsler_scaled(scale: np.ndarray, p, q) -> float:
    """Finsler distance with a precomputed agent scale (hot path — no re-weighting)."""
    return poincare_distance(to_ball(scale * to_vec(p)), to_ball(scale * to_vec(q)))


def finsler_distance(p, q, agent) -> float:
    """Tongue-weighted (Finsler) hyperbolic distance: WHERE x WHO.

    Each axis k is scaled by sqrt(phi^k * w_k) before embedding, so the agent's
    identity bends the metric — its strong tongues shrink distance along their axes.
    """
    return finsler_scaled(agent_scale(agent), p, q)


# --- geodesics: ray-trace the actual path through the lattice ----------------

def _ball_to_klein(x: np.ndarray) -> np.ndarray:
    return 2.0 * x / (1.0 + float(x @ x))


def _klein_to_ball(k: np.ndarray) -> np.ndarray:
    n2 = min(float(k @ k), 1.0 - _EPS)
    return k / (1.0 + np.sqrt(max(1.0 - n2, _EPS)))


def geodesic(p, q, steps: int = 16, agent=None) -> List[np.ndarray]:
    """Sample the geodesic 'ray' from p to q. Straight in Klein -> true geodesic
    in the Poincare ball. With an agent, traces the route under its Finsler metric."""
    scale = np.sqrt(PHI_W * tongue_weights(agent)) if agent is not None else np.ones(6)
    a = _ball_to_klein(to_ball(scale * to_vec(p)))
    b = _ball_to_klein(to_ball(scale * to_vec(q)))
    return [_klein_to_ball(a + (b - a) * (i / steps)) for i in range(steps + 1)]


# --- fleet routing: tangent-vector parallel tracks ---------------------------

@dataclass
class Agent:
    name: str
    tongue: object               # dict or 6-vector identity
    pos: np.ndarray = field(default=None)   # current point in tongue space
    load: int = 0

    def __post_init__(self):
        if self.pos is None:
            # an agent starts at its own identity (its strongest tongues)
            self.pos = to_vec(self.tongue)


@dataclass
class Task:
    name: str
    profile: object              # dict or 6-vector
    agent: str = None
    cost: float = 0.0


@dataclass
class Route:
    """One agent's parallel track: the tasks it owns + its geodesic ray through them."""
    agent: str
    tasks: List[str]
    track: List[np.ndarray]      # sampled geodesic visiting the tasks in order
    total_cost: float


def route_fleet(agents: Sequence[Agent], tasks: Sequence[Task],
                pressure: float = 0.6, tour: bool = True) -> List[Route]:
    """Assign every task to the agent whose Finsler metric makes it closest,
    with a FLUID PRESSURE term that penalizes piling onto a loaded agent — so the
    fleet spreads like an incompressible flow instead of all rushing one node.

    Returns one Route (parallel track) per agent, each a geodesic ray through its
    assigned tasks (a tangent-vector lane through the lattice). Set tour=False to
    skip the per-agent geodesic ordering (O(k^2)) when only the assignment is
    needed — e.g. routing work to parallel workers at scale."""
    loads = {a.name: 0 for a in agents}
    by_agent: Dict[str, List[Task]] = {a.name: [] for a in agents}
    # order tasks by how "decisive" they are (high norm = strongly-flavored) first
    ordered = sorted(tasks, key=lambda t: -float(np.linalg.norm(to_vec(t.profile))))
    for t in ordered:
        best, best_c = None, float("inf")
        for a in agents:
            d = finsler_distance(a.pos, t.profile, a.tongue)
            c = d + pressure * loads[a.name]   # additive fluid back-pressure
            if c < best_c:
                best, best_c = a, c
        t.agent = best.name
        t.cost = finsler_distance(best.pos, t.profile, best.tongue)
        loads[best.name] += 1
        by_agent[best.name].append(t)

    routes: List[Route] = []
    for a in agents:
        owned = by_agent[a.name]
        if not tour:
            # assignment only — skip the O(k^2) geodesic ordering
            routes.append(Route(a.name, [t.name for t in owned], [],
                                sum(t.cost for t in owned)))
            continue
        # order each agent's tasks along its geodesic (nearest-first greedy tour)
        seq, cur, tot = [], a.pos, 0.0
        pool = list(owned)
        while pool:
            nxt = min(pool, key=lambda t: finsler_distance(cur, t.profile, a.tongue))
            tot += finsler_distance(cur, nxt.profile, a.tongue)
            seq.append(nxt)
            cur = to_vec(nxt.profile)
            pool.remove(nxt)
        track: List[np.ndarray] = []
        cur = a.pos
        for t in seq:
            track.extend(geodesic(cur, t.profile, steps=8, agent=a.tongue))
            cur = to_vec(t.profile)
        routes.append(Route(a.name, [t.name for t in seq], track, tot))
    return routes


def round_robin(agents: Sequence[Agent], tasks: Sequence[Task]) -> float:
    """Flat parallelism baseline: chunk tasks across agents ignoring geometry."""
    tot = 0.0
    for i, t in enumerate(tasks):
        a = agents[i % len(agents)]
        tot += finsler_distance(a.pos, t.profile, a.tongue)
    return tot


# --- demo --------------------------------------------------------------------

def _demo() -> None:
    rng = np.random.default_rng(7)
    # a fleet of 6 tongue-specialist agents (one strong tongue each)
    fleet = [Agent(f"{t}-agent", {t: 1.0}) for t in TONGUES]
    # 30 tasks with random tongue flavor
    tasks = []
    for i in range(30):
        prof = {t: float(rng.random()) for t in TONGUES}
        # make some tasks strongly one-tongue-flavored
        if i % 3 == 0:
            dom = TONGUES[i % 6]
            prof = {t: (1.0 if t == dom else 0.1 * rng.random()) for t in TONGUES}
        tasks.append(Task(f"task{i:02d}", prof))

    routes = route_fleet(fleet, tasks, pressure=0.6)
    geo_cost = sum(r.total_cost for r in routes)
    rr_cost = round_robin(fleet, tasks)

    print("Geometric fleet router — tangent-vector parallel tracks\n")
    print(f"  fleet: {len(fleet)} tongue-specialist agents   tasks: {len(tasks)}")
    print(f"  metric: tongue-weighted Poincare (Finsler), phi-tongue tensor\n")
    print("  parallel tracks (each agent = a tangent vector tracing a geodesic):")
    for r in routes:
        ray = f"{len(r.track)} pts" if r.track else "-"
        print(f"    {r.agent:<10} {len(r.tasks):>2} tasks  track {ray:<8} "
              f"cost {r.total_cost:6.2f}   {', '.join(r.tasks[:5])}{' …' if len(r.tasks) > 5 else ''}")
    print(f"\n  total routing cost  geometric: {geo_cost:7.2f}")
    print(f"                      round-robin: {rr_cost:7.2f}   "
          f"-> geometric is {100 * (1 - geo_cost / rr_cost):.0f}% cheaper")
    # show affinity: strongly-flavored tasks land on the matching specialist
    print("\n  affinity check (one-tongue tasks route to their specialist):")
    for t in tasks[:9]:
        if t.cost < 1.5:
            dom = max(TONGUES, key=lambda g: to_vec(t.profile)[TONGUES.index(g)])
            print(f"    {t.name}  dominant {dom:<3} -> {t.agent:<10} (cost {t.cost:.2f})")
    # one ray-traced geodesic
    g = geodesic({"KO": 1.0}, {"DR": 1.0, "UM": 0.5}, steps=6, agent={"KO": 1.0})
    print(f"\n  ray-traced geodesic KO-agent -> DR/UM node ({len(g)} samples, "
          f"endpoints ||{np.linalg.norm(g[0]):.2f}|| -> ||{np.linalg.norm(g[-1]):.2f}||)")


if __name__ == "__main__":
    _demo()
