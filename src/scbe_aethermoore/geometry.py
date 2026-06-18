"""The geometry router: routing IS the geometry (PHDM rails + Trust Tube), not a lookup.

From the Crystal Cranium doc: the valid transitions are not a hand-wired edge list -- they
are the RAIL FAMILY, the Hamiltonian paths through the polyhedral regions. The TRUST TUBE is
the epsilon-neighborhood around the rails; project_to_tube() re-anchors a drifting intent
back to the nearest rail. So here the cranium's synapses are DERIVED from the rails (a
transition is valid iff it is a consecutive pair on some rail -- an off-rail jump is an
orthogonal excursion), and a continuous intent point is routed by projecting it onto the
nearest rail.

    from scbe_aethermoore.geometry import build_geometric_cranium, route_intent
    c = build_geometric_cranium()                 # synapses = rail segments
    route_intent((0.14, 0.0))                      # project an intent onto the nearest rail
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

from scbe_aethermoore.cranium import _REGIONS
from scbe_aethermoore.synapses import Connectome, Region, Synapse

TUBE_RADIUS = 0.15  # the Trust Tube epsilon from the doc

# The rail family: canonical Hamiltonian paths through the regions (the doc's example rails).
RAILS: Dict[str, List[str]] = {
    "entry": ["entry", "cube"],
    "safe": ["tetrahedron", "cube", "octahedron", "dodecahedron", "icosahedron"],
    "creative": ["cube", "rhombicuboctahedron", "truncated_icosahedron", "snub_dodecahedron"],
    "risk_excursion": [
        "snub_dodecahedron",
        "johnson_b",
        "small_stellated_dodecahedron",
        "great_stellated_dodecahedron",
        "szilassi",
        "tetrahedron",
    ],
    "audit": ["szilassi", "cube"],
}

_RING = {name: ring for name, ring, r, fn in _REGIONS}
_R = {name: r for name, ring, r, fn in _REGIONS}
_TONGUE_BY_RING = {"core": "KO", "bridge": "RU", "cortex": "AV", "cerebellum": "DR", "risk": "UM"}


def positions() -> Dict[str, Tuple[float, float]]:
    """Each region as a point in the Poincare disk: radius = r, angle spread by index."""
    n = len(_REGIONS)
    pos = {"entry": (0.0, 0.0)}
    for i, (name, ring, r, fn) in enumerate(_REGIONS):
        theta = 2.0 * math.pi * i / n
        pos[name] = (r * math.cos(theta), r * math.sin(theta))
    return pos


def _edge_tongue(source: str, target: str) -> str:
    if source == "entry":
        return "DR"  # govern entry into the skull, hard
    return _TONGUE_BY_RING.get(_RING.get(target, ""), "KO")


def rail_edges() -> List[Tuple[str, str, str]]:
    """Synapses DERIVED from the rails: every consecutive pair, deduped, tongue by target ring."""
    seen, edges = set(), []
    for rail in RAILS.values():
        for a, b in zip(rail, rail[1:]):
            if (a, b) not in seen:
                seen.add((a, b))
                edges.append((a, b, _edge_tongue(a, b)))
    return edges


def valid_edge(source: str, target: str) -> bool:
    """A transition is valid iff it is a consecutive pair on some rail (geometry, not lookup)."""
    return any((source, target) == (a, b) for rail in RAILS.values() for a, b in zip(rail, rail[1:]))


def build_geometric_cranium() -> Connectome:
    """A cranium whose synapses are the rail segments -- adjacency derived from the geometry."""
    c = Connectome()
    for name, ring, r, fn in _REGIONS:
        c.add_region(Region(name, fn, (lambda m, nm=name, f=fn: f"visited {nm} [{f}]"), r=r, ring=ring))
    for a, b, tongue in rail_edges():
        c.add_synapse(Synapse(a, b, tongue))
    return c


def _closest_on_segment(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    seg_len2 = dx * dx + dy * dy
    if seg_len2 == 0.0:
        return (ax, ay), 0.0
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg_len2))
    return (ax + t * dx, ay + t * dy), t


def _dist(p, q):
    return math.hypot(p[0] - q[0], p[1] - q[1])


def project_to_tube(point, tube_radius: float = TUBE_RADIUS) -> dict:
    """Project a continuous intent point onto the nearest rail (Trust Tube projection).

    Returns the nearest rail, the region you are at, the next region on that rail, the
    distance to the rail, whether you are inside the tube, and the re-anchored point.
    """
    pos = positions()
    best = None
    for rail_id, rail in RAILS.items():
        pts = [pos[r] for r in rail if r in pos]
        for i in range(len(pts) - 1):
            proj, t = _closest_on_segment(point, pts[i], pts[i + 1])
            d = _dist(point, proj)
            if best is None or d < best["_d"]:
                best = {
                    "_d": d,
                    "rail": rail_id,
                    "distance": round(d, 4),
                    "at_region": rail[i] if t < 0.5 else rail[i + 1],
                    "next_region": rail[i + 1],
                    "t": round(t, 3),
                    "reanchored_point": (round(proj[0], 4), round(proj[1], 4)),
                }
    best["in_tube"] = best["_d"] <= tube_radius
    del best["_d"]
    return best


def route_intent(point, tube_radius: float = TUBE_RADIUS) -> dict:
    """Route a continuous intent: project onto the nearest rail; if it has drifted outside the
    tube, flag it and re-anchor to the rail (the doc's forced projection)."""
    proj = project_to_tube(point, tube_radius)
    proj["action"] = "route" if proj["in_tube"] else "re-anchor (drift outside Trust Tube)"
    return proj
