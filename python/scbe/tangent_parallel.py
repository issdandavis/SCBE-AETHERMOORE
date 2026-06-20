"""Tangential parallelism — bounded divergence around the fleet's prime line.

When a fleet forks a task across agents, each agent traces its own tangent track
(see ``geometric_router``). Left alone, those tracks can diverge arbitrarily. This
module keeps them like the grain of a ship's hull: every track runs mostly along
the keel — the PRIME LINE — and is pulled back if it strays past a bound, with
periodic NODES where the tracks reconverge before diverging again.

Built directly on ``geometric_router``:

  prime line  = geodesic(fleet origin -> goal)          # the keel / centerline
  divergence  = min hyperbolic distance(point, keel)    # perpendicular drift
  alignment   = cos(origin->point, origin->goal)        # grain direction (1 = with the keel)
  reproject   = slide a strayed point toward the keel until divergence <= bound
  node        = a checkpoint on the keel where tracks reconverge, then diverge again

The metaphor, made literal: agents diverge to cover ground, but the keel keeps the
grain mostly going one way; a plank that warps too far is planed back to the bound.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

import numpy as np

from . import geometric_router as gr


def _interp_ball(a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
    """Linear blend between two ball points (a good local proxy for the short geodesic)."""
    return a + (b - a) * t


@dataclass
class PrimeLine:
    """The keel: a geodesic ray from the fleet origin to the goal, sampled in the ball."""

    origin: np.ndarray  # raw 6-vec
    goal: np.ndarray  # raw 6-vec
    samples: List[np.ndarray]  # ball-space points along the keel

    def nearest(self, point_ball: np.ndarray) -> tuple[int, float]:
        """Index and hyperbolic distance of the closest keel sample to a ball point."""
        dists = [gr.poincare_distance(point_ball, s) for s in self.samples]
        idx = int(np.argmin(dists))
        return idx, dists[idx]


def _centroid(profiles: Sequence[Any]) -> np.ndarray:
    vecs = [gr.to_vec(p) for p in profiles]
    return np.mean(vecs, axis=0) if vecs else np.zeros(6)


def prime_line(origin: Any, goal: Any, steps: int = 24) -> PrimeLine:
    """The keel: the geodesic ray from the fleet origin to the goal."""
    o, g = gr.to_vec(origin), gr.to_vec(goal)
    return PrimeLine(o, g, gr.geodesic(o, g, steps=steps))


def divergence(profile: Any, line: PrimeLine) -> float:
    """Perpendicular drift: hyperbolic distance from the point to the nearest keel sample."""
    _, d = line.nearest(gr.to_ball(gr.to_vec(profile)))
    return d


def grain_alignment(profile: Any, line: PrimeLine) -> float:
    """Cosine of (origin->point) against the keel direction (origin->goal), in ball space.

    1.0 = the grain runs with the keel; 0 = perpendicular; <0 = against the bow.
    """
    ob, gb = gr.to_ball(line.origin), gr.to_ball(line.goal)
    pb = gr.to_ball(gr.to_vec(profile))
    keel, leg = gb - ob, pb - ob
    nk, nl = float(np.linalg.norm(keel)), float(np.linalg.norm(leg))
    if nk < gr._EPS or nl < gr._EPS:
        return 1.0
    return float(np.clip((keel @ leg) / (nk * nl), -1.0, 1.0))


def reproject(profile: Any, line: PrimeLine, max_divergence: float) -> Dict[str, Any]:
    """Plane a strayed point back toward the keel until it is within the divergence bound.

    Returns the new ball point, the original and new divergence, and whether it moved.
    """
    pb = gr.to_ball(gr.to_vec(profile))
    idx, d0 = line.nearest(pb)
    if d0 <= max_divergence:
        return {"point": pb, "before": d0, "after": d0, "reprojected": False}
    target = line.samples[idx]  # the nearest point on the keel
    lo, hi = 0.0, 1.0  # bisect the blend fraction toward the keel for divergence == bound
    for _ in range(24):
        mid = 0.5 * (lo + hi)
        _, dm = line.nearest(_interp_ball(pb, target, mid))
        if dm > max_divergence:
            lo = mid
        else:
            hi = mid
    cand = _interp_ball(pb, target, hi)
    _, d1 = line.nearest(cand)
    return {"point": cand, "before": d0, "after": d1, "reprojected": True}


@dataclass
class TangentTrack:
    agent: str
    tasks: List[str]
    divergence: float  # worst drift over the track AFTER reprojection
    raw_divergence: float  # worst drift BEFORE reprojection
    alignment: float  # mean grain alignment of the track's tasks
    reprojected: int  # how many task points had to be planed back

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "tasks": self.tasks,
            "divergence": round(self.divergence, 6),
            "raw_divergence": round(self.raw_divergence, 6),
            "alignment": round(self.alignment, 6),
            "reprojected": self.reprojected,
        }


@dataclass
class TangentPlan:
    origin: List[float]
    goal: List[float]
    tracks: List[TangentTrack]
    grain_alignment: float  # fleet-wide mean alignment to the keel
    max_divergence: float  # worst track drift after bounding (<= bound)
    bound: float
    nodes: int
    node_points: List[List[float]]  # keel checkpoints where tracks reconverge

    def to_dict(self) -> Dict[str, Any]:
        return {
            "origin": [round(x, 4) for x in self.origin],
            "goal": [round(x, 4) for x in self.goal],
            "bound": self.bound,
            "nodes": self.nodes,
            "grain_alignment": round(self.grain_alignment, 6),
            "max_divergence": round(self.max_divergence, 6),
            "tracks": [t.to_dict() for t in self.tracks],
            "node_points": [[round(x, 4) for x in p] for p in self.node_points],
        }


def _node_points(line: PrimeLine, nodes: int) -> List[np.ndarray]:
    """Evenly spaced keel checkpoints (the reconvergence points), including bow and stern."""
    nodes = max(1, nodes)
    last = len(line.samples) - 1
    idxs = sorted({round(i * last / nodes) for i in range(nodes + 1)})
    return [line.samples[i] for i in idxs]


def plan(
    agents: Sequence[gr.Agent],
    tasks: Sequence[gr.Task],
    goal: Any,
    max_divergence: float = 1.5,
    nodes: int = 1,
    pressure: float = 0.6,
) -> TangentPlan:
    """Route a fleet with bounded tangential divergence from the prime line (the keel).

    The keel runs from the fleet's origin (centroid of agent identities) to the goal.
    Tasks are assigned with the existing fluid Finsler routing, then each task's drift
    from the keel is measured and — if it exceeds ``max_divergence`` — planed back.
    """
    if not agents:
        raise ValueError("need at least one agent")
    origin = _centroid([a.tongue for a in agents])
    line = prime_line(origin, goal)
    routes = gr.route_fleet(list(agents), list(tasks), pressure=pressure, tour=False)
    by_name = {t.name: t for t in tasks}

    tracks: List[TangentTrack] = []
    all_aligns: List[float] = []
    worst = 0.0
    for r in routes:
        raws, news, aligns, repro = [], [], [], 0
        for name in r.tasks:
            prof = by_name[name].profile
            rp = reproject(prof, line, max_divergence)
            raws.append(rp["before"])
            news.append(rp["after"])
            aligns.append(grain_alignment(prof, line))
            if rp["reprojected"]:
                repro += 1
        td = max(news) if news else 0.0
        worst = max(worst, td)
        all_aligns.extend(aligns)
        tracks.append(
            TangentTrack(
                agent=r.agent,
                tasks=r.tasks,
                divergence=td,
                raw_divergence=max(raws) if raws else 0.0,
                alignment=float(np.mean(aligns)) if aligns else 1.0,
                reprojected=repro,
            )
        )

    return TangentPlan(
        origin=list(map(float, origin)),
        goal=list(map(float, gr.to_vec(goal))),
        tracks=tracks,
        grain_alignment=float(np.mean(all_aligns)) if all_aligns else 1.0,
        max_divergence=worst,
        bound=max_divergence,
        nodes=max(1, nodes),
        node_points=[list(map(float, p)) for p in _node_points(line, nodes)],
    )
