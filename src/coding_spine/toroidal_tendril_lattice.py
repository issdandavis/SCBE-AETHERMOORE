"""Exact sparse addressing for toroidal tendrils and infinite-zoom views.

The module never allocates an infinite canvas.  It stores finite objects with
unbounded integer winding and zoom addresses, then materializes only objects
that intersect a requested viewport.  Empty space is implicit.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from heapq import heappop, heappush
import json
from math import gcd
from typing import Iterable, Mapping


ROLE_ORDER = {
    "Scout": 0,
    "Sniper": 1,
    "Support": 2,
    "Tank": 3,
    "Assassin": 4,
    "Adjutant": 5,
}


def _integer(value: object, name: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be an exact integer")
    return value


def _positive(value: object, name: str) -> int:
    result = _integer(value, name)
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


@dataclass(frozen=True)
class ProjectivePoint:
    """Canonical homogeneous point [x:y:w], including exact w=0 infinity."""

    x: int
    y: int
    w: int

    def __post_init__(self) -> None:
        x = _integer(self.x, "x")
        y = _integer(self.y, "y")
        w = _integer(self.w, "w")
        divisor = gcd(gcd(abs(x), abs(y)), abs(w))
        if divisor == 0:
            raise ValueError("[0:0:0] is not a projective point")
        x, y, w = x // divisor, y // divisor, w // divisor
        if w < 0 or (w == 0 and (x < 0 or (x == 0 and y < 0))):
            x, y, w = -x, -y, -w
        object.__setattr__(self, "x", x)
        object.__setattr__(self, "y", y)
        object.__setattr__(self, "w", w)

    @property
    def at_infinity(self) -> bool:
        return self.w == 0


@dataclass(frozen=True)
class Dyadic:
    """Exact symbolic value ``coefficient * 2**power``."""

    coefficient: int
    power: int

    def __post_init__(self) -> None:
        coefficient = _integer(self.coefficient, "coefficient")
        power = _integer(self.power, "power")
        if coefficient == 0:
            power = 0
        else:
            while coefficient % 2 == 0:
                coefficient //= 2
                power += 1
        object.__setattr__(self, "coefficient", coefficient)
        object.__setattr__(self, "power", power)


@dataclass(frozen=True)
class TendrilVertex:
    id: str
    local_x: int
    local_y: int
    winding_x: int
    winding_y: int
    zoom_level: int
    phase: int
    phase_winding: int
    mark: str
    port_type: str
    role: str
    projective: ProjectivePoint
    lod_max: int | None = None

    def world_x(self, period_x: int) -> int:
        return self.winding_x * period_x + self.local_x

    def world_y(self, period_y: int) -> int:
        return self.winding_y * period_y + self.local_y


@dataclass(frozen=True)
class TendrilArc:
    id: str
    source: str
    target: str
    winding_x: int
    winding_y: int
    phase: int
    phase_winding: int
    angle: int
    mark: str
    port_type: str
    reinforcement: int = 0
    verified_commits: int = 0


@dataclass(frozen=True)
class ToroidalLattice:
    period_x: int
    period_y: int
    phase_period: int
    scale: int
    saturation: int
    vertices: tuple[TendrilVertex, ...]
    arcs: tuple[TendrilArc, ...]


@dataclass(frozen=True)
class ProjectedVertex:
    id: str
    screen_x: Dyadic
    screen_y: Dyadic
    zoom_level: int
    phase: int
    mark: str
    port_type: str


@dataclass(frozen=True)
class ScrollWindow:
    zoom: int
    center_x: int
    center_y: int
    width: int
    height: int
    vertices: tuple[ProjectedVertex, ...]
    arc_ids: tuple[str, ...]
    infinity_directions: tuple[tuple[str, ProjectivePoint], ...]
    implicit_blank: bool
    truncated: bool


@dataclass(frozen=True)
class TendrilRoute:
    vertex_ids: tuple[str, ...]
    arc_ids: tuple[str, ...]
    cost: int


def shortest_wrapped_delta(start: int, end: int, period: int) -> int:
    """Return the shortest signed torus delta; exact ties choose positive."""

    start = _integer(start, "start")
    end = _integer(end, "end")
    period = _positive(period, "period")
    raw = end - start
    choices = (raw, raw - period, raw + period)
    return min(choices, key=lambda value: (abs(value), 0 if value >= 0 else 1))


def _projective(value: object, x: int, y: int, scale: int) -> ProjectivePoint:
    if value is None:
        return ProjectivePoint(x, y, scale)
    if isinstance(value, ProjectivePoint):
        return value
    if isinstance(value, Mapping):
        return ProjectivePoint(value.get("x"), value.get("y"), value.get("w"))
    if isinstance(value, (tuple, list)) and len(value) == 3:
        return ProjectivePoint(value[0], value[1], value[2])
    raise TypeError("projective must be ProjectivePoint, mapping, or three integers")


def _mapping(value: object, kind: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{kind} must be a mapping")
    return value


def compile_toroidal_lattice(
    vertices: Iterable[Mapping[str, object]],
    arcs: Iterable[Mapping[str, object]] = (),
    *,
    period_x: int,
    period_y: int,
    phase_period: int = 6,
    scale: int = 1,
    saturation: int = 9,
) -> ToroidalLattice:
    """Compile mappings into a canonical exact lattice."""

    period_x = _positive(period_x, "period_x")
    period_y = _positive(period_y, "period_y")
    phase_period = _positive(phase_period, "phase_period")
    scale = _positive(scale, "scale")
    saturation = _positive(saturation, "saturation")
    compiled_vertices: list[TendrilVertex] = []
    seen_vertices: set[str] = set()
    for raw_value in vertices:
        raw = _mapping(raw_value, "vertex")
        vertex_id = str(raw.get("id", ""))
        if not vertex_id or vertex_id in seen_vertices:
            raise ValueError(f"invalid or duplicate vertex id: {vertex_id!r}")
        seen_vertices.add(vertex_id)
        x = _integer(raw.get("x", 0), "vertex.x")
        y = _integer(raw.get("y", 0), "vertex.y")
        winding_x, local_x = divmod(x, period_x)
        winding_y, local_y = divmod(y, period_y)
        raw_phase = _integer(raw.get("phase", 0), "vertex.phase")
        phase_winding, phase = divmod(raw_phase, phase_period)
        zoom_level = _integer(raw.get("zoom_level", 0), "vertex.zoom_level")
        lod_max_value = raw.get("lod_max")
        lod_max = None if lod_max_value is None else _integer(lod_max_value, "vertex.lod_max")
        if lod_max is not None and lod_max < zoom_level:
            raise ValueError("vertex.lod_max cannot be below zoom_level")
        compiled_vertices.append(TendrilVertex(
            id=vertex_id,
            local_x=local_x,
            local_y=local_y,
            winding_x=winding_x,
            winding_y=winding_y,
            zoom_level=zoom_level,
            phase=phase,
            phase_winding=phase_winding,
            mark=str(raw.get("mark", "")),
            port_type=str(raw.get("port_type", "generic")),
            role=str(raw.get("role", "Adjutant")),
            projective=_projective(raw.get("projective"), x, y, scale),
            lod_max=lod_max,
        ))
    compiled_vertices.sort(key=lambda vertex: vertex.id)

    compiled_arcs: list[TendrilArc] = []
    seen_arcs: set[str] = set()
    for raw_value in arcs:
        raw = _mapping(raw_value, "arc")
        arc_id = str(raw.get("id", ""))
        source = str(raw.get("source", ""))
        target = str(raw.get("target", ""))
        if not arc_id or arc_id in seen_arcs:
            raise ValueError(f"invalid or duplicate arc id: {arc_id!r}")
        if source not in seen_vertices or target not in seen_vertices:
            raise ValueError(f"arc {arc_id!r} references an unknown endpoint")
        seen_arcs.add(arc_id)
        raw_phase = _integer(raw.get("phase", 0), "arc.phase")
        phase_winding, phase = divmod(raw_phase, phase_period)
        reinforcement = _integer(raw.get("reinforcement", 0), "arc.reinforcement")
        commits = _integer(raw.get("verified_commits", 0), "arc.verified_commits")
        if not 0 <= reinforcement <= saturation or commits < 0:
            raise ValueError("arc accounting is outside its allowed range")
        compiled_arcs.append(TendrilArc(
            id=arc_id,
            source=source,
            target=target,
            winding_x=_integer(raw.get("winding_x", 0), "arc.winding_x"),
            winding_y=_integer(raw.get("winding_y", 0), "arc.winding_y"),
            phase=phase,
            phase_winding=phase_winding,
            angle=_integer(raw.get("angle", 0), "arc.angle") % 360,
            mark=str(raw.get("mark", "")),
            port_type=str(raw.get("port_type", "generic")),
            reinforcement=reinforcement,
            verified_commits=commits,
        ))
    compiled_arcs.sort(key=lambda arc: arc.id)
    return ToroidalLattice(
        period_x=period_x,
        period_y=period_y,
        phase_period=phase_period,
        scale=scale,
        saturation=saturation,
        vertices=tuple(compiled_vertices),
        arcs=tuple(compiled_arcs),
    )


def _dyadic_within(value: Dyadic, half_extent: int) -> bool:
    half_extent = _integer(half_extent, "half_extent")
    if half_extent < 0:
        return False
    coefficient = abs(value.coefficient)
    if coefficient == 0:
        return True
    if value.power >= 0:
        if coefficient.bit_length() + value.power > max(1, half_extent.bit_length()):
            return False
        return (coefficient << value.power) <= half_extent
    shift = -value.power
    if shift > coefficient.bit_length() + max(1, half_extent.bit_length()) + 1:
        return True
    return coefficient <= (half_extent << shift)


def project_scroll_window(
    lattice: ToroidalLattice,
    *,
    center_x: int,
    center_y: int,
    width: int,
    height: int,
    zoom: int,
    max_items: int = 1024,
) -> ScrollWindow:
    """Materialize only finite vertices visible in an exact sparse viewport."""

    center_x = _integer(center_x, "center_x")
    center_y = _integer(center_y, "center_y")
    width = _positive(width, "width")
    height = _positive(height, "height")
    zoom = _integer(zoom, "zoom")
    max_items = _positive(max_items, "max_items")
    visible: list[ProjectedVertex] = []
    directions: list[tuple[str, ProjectivePoint]] = []
    for vertex in lattice.vertices:
        if vertex.projective.at_infinity:
            directions.append((vertex.id, vertex.projective))
            continue
        if zoom < vertex.zoom_level or (vertex.lod_max is not None and zoom > vertex.lod_max):
            continue
        screen_x = Dyadic(vertex.world_x(lattice.period_x) - center_x, zoom)
        screen_y = Dyadic(vertex.world_y(lattice.period_y) - center_y, zoom)
        if _dyadic_within(screen_x, width // 2) and _dyadic_within(screen_y, height // 2):
            visible.append(ProjectedVertex(
                id=vertex.id,
                screen_x=screen_x,
                screen_y=screen_y,
                zoom_level=vertex.zoom_level,
                phase=vertex.phase,
                mark=vertex.mark,
                port_type=vertex.port_type,
            ))
    visible.sort(key=lambda item: item.id)
    truncated = len(visible) > max_items
    visible = visible[:max_items]
    ids = {item.id for item in visible}
    arc_ids = tuple(arc.id for arc in lattice.arcs if arc.source in ids and arc.target in ids)
    return ScrollWindow(
        zoom=zoom,
        center_x=center_x,
        center_y=center_y,
        width=width,
        height=height,
        vertices=tuple(visible),
        arc_ids=arc_ids,
        infinity_directions=tuple(sorted(directions, key=lambda item: item[0])),
        implicit_blank=True,
        truncated=truncated,
    )


def route_tendril(lattice: ToroidalLattice, start: str, goal: str) -> TendrilRoute:
    """Find the lowest receipted arc cost; roles only resolve equal-cost ties."""

    vertex_by_id = {vertex.id: vertex for vertex in lattice.vertices}
    if start not in vertex_by_id or goal not in vertex_by_id:
        raise ValueError("route endpoints must exist")
    outgoing: dict[str, list[TendrilArc]] = {}
    for arc in lattice.arcs:
        outgoing.setdefault(arc.source, []).append(arc)
    for values in outgoing.values():
        values.sort(key=lambda arc: (
            ROLE_ORDER.get(vertex_by_id[arc.target].role, len(ROLE_ORDER)),
            arc.phase,
            arc.angle,
            arc.id,
        ))
    queue: list[tuple[int, int, tuple[int, ...], tuple[str, ...], tuple[str, ...], str]] = []
    heappush(queue, (0, 0, (), (), (start,), start))
    best: dict[str, tuple[int, int, tuple[int, ...], tuple[str, ...]]] = {}
    while queue:
        cost, hops, role_trace, arc_trace, vertex_trace, node = heappop(queue)
        key = (cost, hops, role_trace, arc_trace)
        if node in best and best[node] <= key:
            continue
        best[node] = key
        if node == goal:
            return TendrilRoute(vertex_trace, arc_trace, cost)
        for arc in outgoing.get(node, ()):
            penalty = lattice.saturation - arc.reinforcement
            edge_cost = 1 + penalty + abs(arc.winding_x) + abs(arc.winding_y)
            role_rank = ROLE_ORDER.get(vertex_by_id[arc.target].role, len(ROLE_ORDER))
            heappush(queue, (
                cost + edge_cost,
                hops + 1,
                role_trace + (role_rank,),
                arc_trace + (arc.id,),
                vertex_trace + (arc.target,),
                arc.target,
            ))
    raise ValueError(f"no tendril route from {start!r} to {goal!r}")


def reinforce_verified(
    lattice: ToroidalLattice,
    arc_ids: Iterable[str],
    *,
    verified: int,
    amount: int = 1,
) -> ToroidalLattice:
    """Reinforce named arcs only after an exact binary verification bit."""

    verified = _integer(verified, "verified")
    if verified not in (0, 1):
        raise ValueError("verified must be binary 0 or 1")
    amount = _positive(amount, "amount")
    requested = tuple(sorted(set(str(value) for value in arc_ids)))
    known = {arc.id for arc in lattice.arcs}
    unknown = set(requested) - known
    if unknown:
        raise ValueError(f"unknown arcs: {sorted(unknown)}")
    if verified == 0:
        return lattice
    selected = set(requested)
    arcs = tuple(
        replace(
            arc,
            reinforcement=min(lattice.saturation, arc.reinforcement + amount),
            verified_commits=arc.verified_commits + 1,
        ) if arc.id in selected else arc
        for arc in lattice.arcs
    )
    return replace(lattice, arcs=arcs)


def decay_reinforcement(lattice: ToroidalLattice, *, amount: int = 1) -> ToroidalLattice:
    """Apply bounded forgetting without deleting topology or provenance."""

    amount = _positive(amount, "amount")
    return replace(lattice, arcs=tuple(
        replace(arc, reinforcement=max(0, arc.reinforcement - amount))
        for arc in lattice.arcs
    ))


def tendril_receipt(lattice: ToroidalLattice) -> dict[str, object]:
    """Return a canonical audit receipt. Self-reinforcement is not independent evidence."""

    payload = {
        "schema": "scbe-toroidal-tendril/1",
        "period": [lattice.period_x, lattice.period_y],
        "phase_period": lattice.phase_period,
        "scale": lattice.scale,
        "saturation": lattice.saturation,
        "blank_space": "implicit",
        "independent_evidence": False,
        "vertices": [
            {
                "id": vertex.id,
                "local": [vertex.local_x, vertex.local_y],
                "winding": [vertex.winding_x, vertex.winding_y],
                "zoom_level": vertex.zoom_level,
                "phase": [vertex.phase, vertex.phase_winding],
                "mark": vertex.mark,
                "port_type": vertex.port_type,
                "role": vertex.role,
                "projective": [vertex.projective.x, vertex.projective.y, vertex.projective.w],
                "lod_max": vertex.lod_max,
            }
            for vertex in lattice.vertices
        ],
        "arcs": [
            {
                "id": arc.id,
                "endpoints": [arc.source, arc.target],
                "winding": [arc.winding_x, arc.winding_y],
                "phase": [arc.phase, arc.phase_winding],
                "angle": arc.angle,
                "mark": arc.mark,
                "port_type": arc.port_type,
                "reinforcement": arc.reinforcement,
                "verified_commits": arc.verified_commits,
            }
            for arc in lattice.arcs
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return {**payload, "sha256": sha256(encoded).hexdigest()}


__all__ = [
    "Dyadic",
    "ProjectivePoint",
    "ProjectedVertex",
    "ScrollWindow",
    "TendrilArc",
    "TendrilRoute",
    "TendrilVertex",
    "ToroidalLattice",
    "compile_toroidal_lattice",
    "decay_reinforcement",
    "project_scroll_window",
    "reinforce_verified",
    "route_tendril",
    "shortest_wrapped_delta",
    "tendril_receipt",
]
