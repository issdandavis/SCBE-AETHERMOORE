"""cloud_router: route through the geometric router's lifted space by PROBABILITY-CLOUD flow, not a single
argmin. The unification -- the router supplies the lifted hyperbolic space + the Finsler cost field; the
cloud supplies multi-option resilience, gate-peaks, and stuck->escalate.

geometric_router already lifts tasks/agents into the Poincare ball (the dimensional-shadow space), measures
a tongue-weighted Finsler cost (WHERE x WHO), and repels congestion like a fluid. Classic routing picks the
single closest agent (argmin cost). This instead builds a probability field over the candidates -- each a
gravity WELL whose depth is its closeness, a gated/unsafe one a locked PEAK -- and lets the belief cloud
FLOW to the deepest ACCESSIBLE well. So if the geometrically-closest agent is gated, congested, or drifted
to the boundary, the route flows AROUND it to the next best (resilience); if every candidate is a peak, it
returns stuck -> escalate (the calibrated STOP rule), instead of force-routing to a bad agent.

    from python.scbe.cloud_router import route
    pick = route(task_profile, agents)   # agents: [{'name','profile','identity', optional 'locked'}]
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .geometric_router import finsler_distance
from .probability_cloud import Site, resolve


def route(
    task: Dict[str, float],
    agents: List[Dict[str, Any]],
    sigma: float = 1.0,
    boundary_cost: float = 8.0,
) -> Dict[str, Any]:
    """Route a task to an agent by cloud flow over the Finsler cost field. Each agent is a Site positioned
    at its Finsler distance from the task (closer = nearer the belief center = more reachable); its appeal
    (well depth) falls with distance; a 'locked' agent (a safety/gate veto) or one whose cost exceeds
    boundary_cost (drifted too far/unsafe) is a PEAK. Returns the chosen agent, the field, and stuck."""
    sites: List[Site] = []
    detail: Dict[str, float] = {}
    for a in agents:
        cost = finsler_distance(task, a["profile"], a.get("identity", a["profile"]))
        detail[a["name"]] = round(cost, 3)
        locked = bool(a.get("locked")) or cost > boundary_cost  # gated, or drifted past the safe radius
        sites.append(Site(name=a["name"], pos=cost, appeal=1.0 / (1.0 + cost), locked=locked))
    # the belief sits at the task itself (cost 0); sigma = how far the cloud is willing to reach
    field = resolve(sites, belief=0.0, sigma=sigma)
    return {
        "agent": field["choice"],
        "stuck": field["stuck"],  # every candidate gated/too-far -> escalate, don't force a bad route
        "costs": detail,
        "density": field["density"],
    }


def best_by_cost(task: Dict[str, float], agents: List[Dict[str, Any]]) -> Optional[str]:
    """The classic argmin baseline (single closest agent, ignores gates) -- for comparison against route()."""
    ranked = sorted(agents, key=lambda a: finsler_distance(task, a["profile"], a.get("identity", a["profile"])))
    return ranked[0]["name"] if ranked else None
