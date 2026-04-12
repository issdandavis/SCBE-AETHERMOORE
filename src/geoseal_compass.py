"""
GeoSeal Compass: Multi-Point Navigation through Sacred Tongue Space-Time
=========================================================================

Python reference implementation of the GeoSeal Compass routing system.

The Six Sacred Tongues form a hexagonal compass rose in the Poincaré ball:

        Kor'aelin (0°)
          /    \\
   Draumric      Avali
   (300°)         (60°)
      |             |
   Umbroth       Runethic
   (240°)         (120°)
          \\    /
       Cassisivadan (180°)

Any direction through the manifold can be expressed as a weighted blend
of tongue bearings. Routes between waypoints follow hyperbolic geodesics,
with governance scoring at each hop.

Axioms:
- Unitarity: Route preserves total signal through manifold
- Locality: Each hop respects spatial bounds (ball containment)
- Causality: Temporal windows enforce time-ordering
- Symmetry: Compass rose is symmetric under tongue rotation
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple

from src.geoseal import hyperbolic_distance, phase_deviation, clamp_to_ball

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2
EPSILON = 1e-8

COMPASS_BEARINGS: Dict[str, float] = {
    "KO": 0.0,
    "AV": math.pi / 3,
    "RU": 2 * math.pi / 3,
    "CA": math.pi,
    "UM": 4 * math.pi / 3,
    "DR": 5 * math.pi / 3,
}

TONGUE_WEIGHTS: Dict[str, float] = {
    "KO": 1.0,
    "AV": PHI,
    "RU": PHI**2,
    "CA": PHI**3,
    "UM": PHI**4,
    "DR": PHI**5,
}

TONGUES: List[str] = ["KO", "AV", "RU", "CA", "UM", "DR"]


# ---------------------------------------------------------------------------
# Poincaré ball primitives (log/exp maps)
# ---------------------------------------------------------------------------


def _norm_sq(v: List[float]) -> float:
    return sum(x * x for x in v)


def _norm(v: List[float]) -> float:
    return math.sqrt(_norm_sq(v))


def _scale(v: List[float], s: float) -> List[float]:
    return [x * s for x in v]


def _add(u: List[float], v: List[float]) -> List[float]:
    return [a + b for a, b in zip(u, v)]


def _sub(u: List[float], v: List[float]) -> List[float]:
    return [a - b for a, b in zip(u, v)]


def _dot(u: List[float], v: List[float]) -> float:
    return sum(a * b for a, b in zip(u, v))


def _mobius_add(u: List[float], v: List[float]) -> List[float]:
    """Möbius addition in the Poincaré ball: u ⊕ v."""
    u_sq = _norm_sq(u)
    v_sq = _norm_sq(v)
    uv = _dot(u, v)

    denom = 1 + 2 * uv + u_sq * v_sq
    if abs(denom) < EPSILON:
        return list(u)

    coeff_u = (1 + 2 * uv + v_sq) / denom
    coeff_v = (1 - u_sq) / denom

    return [coeff_u * ui + coeff_v * vi for ui, vi in zip(u, v)]


def exponential_map(p: List[float], v: List[float]) -> List[float]:
    """Exponential map at p in direction v (Poincaré ball)."""
    v_norm = _norm(v)
    if v_norm < EPSILON:
        return list(p)

    p_sq = _norm_sq(p)
    lambda_p = 2.0 / (1.0 - p_sq + EPSILON)

    direction = _scale(v, 1.0 / v_norm)
    tanh_term = math.tanh(lambda_p * v_norm / 2.0)
    exp_v = _scale(direction, tanh_term)

    result = _mobius_add(p, exp_v)
    return clamp_to_ball(result, 0.99)


def logarithmic_map(p: List[float], q: List[float]) -> List[float]:
    """Logarithmic map: tangent vector at p pointing toward q."""
    p_sq = _norm_sq(p)
    lambda_p = 2.0 / (1.0 - p_sq + EPSILON)

    neg_p = _scale(p, -1)
    diff = _mobius_add(neg_p, q)

    diff_norm = _norm(diff)
    if diff_norm < EPSILON:
        return [0.0] * len(p)

    atanh_val = math.atanh(min(diff_norm, 1.0 - EPSILON))
    factor = (2.0 / lambda_p) * atanh_val / diff_norm
    return _scale(diff, factor)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompassBearing:
    """Direction expressed as tongue-weight blend."""

    angle: float
    dominant_tongue: str
    secondary_tongue: str
    blend: float
    tongue_affinities: Dict[str, float]


@dataclass(frozen=True)
class Waypoint:
    """Named point in the product manifold."""

    id: str
    label: str
    position: List[float]
    phase: Optional[float]
    time: float
    tongue: Optional[str] = None
    governance_score: float = 0.0


@dataclass(frozen=True)
class RouteSegment:
    """A single hop between two waypoints."""

    from_wp: Waypoint
    to_wp: Waypoint
    distance: float
    bearing: CompassBearing
    governance_score: float
    phase_deviation: float
    temporal_span: float
    geodesic_points: List[List[float]]


@dataclass(frozen=True)
class Route:
    """Complete route through multiple waypoints."""

    waypoints: List[Waypoint]
    segments: List[RouteSegment]
    total_distance: float
    min_governance_score: float
    avg_governance_score: float
    temporal_span: float
    is_viable: bool


@dataclass(frozen=True)
class TemporalWindow:
    """Time window for route validity."""

    open_time: float
    close_time: float
    resonant_tongue: str
    bandwidth: int


# ---------------------------------------------------------------------------
# Compass Rose — Direction computation
# ---------------------------------------------------------------------------


def _normalize_angle(angle: float) -> float:
    TWO_PI = 2 * math.pi
    return ((angle % TWO_PI) + TWO_PI) % TWO_PI


def compute_bearing(from_pos: List[float], to_pos: List[float]) -> CompassBearing:
    """Compute compass bearing between two points in the Poincaré ball."""
    tangent = logarithmic_map(from_pos, to_pos)

    dx = tangent[0] if len(tangent) > 0 else 0.0
    dy = tangent[1] if len(tangent) > 1 else 0.0
    angle = _normalize_angle(math.atan2(dy, dx))

    sector = math.pi / 3
    dominant_idx = round(angle / sector) % 6
    dominant_angle = dominant_idx * sector

    angle_diff = _normalize_angle(angle - dominant_angle)
    blend = angle_diff / sector

    secondary_idx = (dominant_idx + 1) % 6 if blend >= 0.5 else (dominant_idx + 5) % 6

    # Per-tongue affinities
    affinities: Dict[str, float] = {}
    total = 0.0
    for i in range(6):
        t_angle = i * sector
        dev = min(abs(angle - t_angle), 2 * math.pi - abs(angle - t_angle))
        aff = max(0.0, math.cos(dev))
        affinities[TONGUES[i]] = aff
        total += aff
    if total > EPSILON:
        for t in TONGUES:
            affinities[t] /= total

    return CompassBearing(
        angle=angle,
        dominant_tongue=TONGUES[dominant_idx],
        secondary_tongue=TONGUES[secondary_idx],
        blend=min(blend, 1 - blend),
        tongue_affinities=affinities,
    )


def tongue_anchor_position(tongue: str, dimension: int = 6) -> List[float]:
    """Canonical compass position for a tongue in the Poincaré ball."""
    bearing = COMPASS_BEARINGS.get(tongue)
    if bearing is None:
        raise ValueError(f"Unknown tongue: {tongue}")
    pos = [0.0] * dimension
    pos[0] = 0.3 * math.cos(bearing)
    pos[1] = 0.3 * math.sin(bearing)
    return pos


# ---------------------------------------------------------------------------
# Waypoint creation
# ---------------------------------------------------------------------------


def create_waypoint(
    id: str,
    label: str,
    position: List[float],
    phase: Optional[float] = None,
    time: float = 0.0,
    tongue: Optional[str] = None,
) -> Waypoint:
    """Create a waypoint with governance score computed from origin distance."""
    safe_pos = clamp_to_ball(list(position), 0.99)
    origin = [0.0] * len(safe_pos)
    d = hyperbolic_distance(origin, safe_pos)
    gov = 1.0 / (1.0 + PHI * d)
    return Waypoint(id=id, label=label, position=safe_pos, phase=phase, time=time, tongue=tongue, governance_score=gov)


def create_tongue_waypoint(tongue: str, time: float = 0.0, dimension: int = 6) -> Waypoint:
    """Create a waypoint at a tongue's anchor position."""
    bearing = COMPASS_BEARINGS.get(tongue)
    if bearing is None:
        raise ValueError(f"Unknown tongue: {tongue}")
    return create_waypoint(f"tongue-{tongue}", tongue, tongue_anchor_position(tongue, dimension), bearing, time, tongue)


# ---------------------------------------------------------------------------
# Geodesic interpolation
# ---------------------------------------------------------------------------


def geodesic_interpolate(p: List[float], q: List[float], steps: int = 5) -> List[List[float]]:
    """Interpolate along hyperbolic geodesic from p to q."""
    if steps < 2:
        return [p, q]

    points: List[List[float]] = [p]
    tangent = logarithmic_map(p, q)

    for i in range(1, steps - 1):
        t = i / (steps - 1)
        scaled = _scale(tangent, t)
        point = exponential_map(p, scaled)
        points.append(clamp_to_ball(point, 0.99))

    points.append(q)
    return points


# ---------------------------------------------------------------------------
# Route segment & planning
# ---------------------------------------------------------------------------

DEFAULT_MIN_GOVERNANCE = 0.3


def _segment_governance(distance: float, perturbation_density: float) -> float:
    """H(d, pd) = 1 / (1 + φ * d_H + 2 * pd)"""
    return 1.0 / (1.0 + PHI * distance + 2.0 * perturbation_density)


def build_segment(
    from_wp: Waypoint,
    to_wp: Waypoint,
    geodesic_resolution: int = 5,
    perturbation_density: float = 0.0,
) -> RouteSegment:
    """Build a route segment between two waypoints."""
    distance = hyperbolic_distance(from_wp.position, to_wp.position)
    bearing = compute_bearing(from_wp.position, to_wp.position)
    phase_dev = phase_deviation(from_wp.phase, to_wp.phase)
    temporal_span = to_wp.time - from_wp.time

    effective_pd = perturbation_density + phase_dev * 0.5
    gov = _segment_governance(distance, effective_pd)
    geo_points = geodesic_interpolate(from_wp.position, to_wp.position, geodesic_resolution)

    return RouteSegment(
        from_wp=from_wp,
        to_wp=to_wp,
        distance=distance,
        bearing=bearing,
        governance_score=gov,
        phase_deviation=phase_dev,
        temporal_span=temporal_span,
        geodesic_points=geo_points,
    )


def plan_route(
    waypoints: List[Waypoint],
    min_governance: float = DEFAULT_MIN_GOVERNANCE,
    geodesic_resolution: int = 5,
    perturbation_density: float = 0.0,
) -> Route:
    """Plan a multi-hop route through waypoints."""
    if len(waypoints) < 2:
        raise ValueError("Route requires at least 2 waypoints")

    segments: List[RouteSegment] = []
    total_dist = 0.0
    min_gov = float("inf")
    total_gov = 0.0

    for i in range(len(waypoints) - 1):
        seg = build_segment(waypoints[i], waypoints[i + 1], geodesic_resolution, perturbation_density)
        segments.append(seg)
        total_dist += seg.distance
        min_gov = min(min_gov, seg.governance_score)
        total_gov += seg.governance_score

    avg_gov = total_gov / len(segments) if segments else 0.0
    temporal_span = waypoints[-1].time - waypoints[0].time

    return Route(
        waypoints=waypoints,
        segments=segments,
        total_distance=total_dist,
        min_governance_score=min_gov if min_gov != float("inf") else 0.0,
        avg_governance_score=avg_gov,
        temporal_span=temporal_span,
        is_viable=min_gov >= min_governance,
    )


def auto_route(
    origin: Waypoint,
    destination: Waypoint,
    max_hops: int = 14,
    min_governance: float = DEFAULT_MIN_GOVERNANCE,
    perturbation_density: float = 0.0,
) -> Route:
    """Auto-route using tongue anchors as relay stations."""
    direct = plan_route([origin, destination], min_governance, perturbation_density=perturbation_density)
    if direct.is_viable:
        return direct

    bearing = compute_bearing(origin.position, destination.position)
    dim = len(origin.position)

    ranked = sorted(TONGUES, key=lambda t: bearing.tongue_affinities.get(t, 0), reverse=True)

    time_step = (destination.time - origin.time) / (max_hops + 1)
    intermediates: List[Waypoint] = []

    for i, t in enumerate(ranked):
        if bearing.tongue_affinities.get(t, 0) < EPSILON:
            break
        if i >= max_hops - 1:
            break
        wp = create_waypoint(
            f"relay-{t}-{i}",
            f"{t} relay",
            tongue_anchor_position(t, dim),
            COMPASS_BEARINGS[t],
            origin.time + time_step * (i + 1),
            t,
        )
        intermediates.append(wp)

    if not intermediates:
        return direct

    intermediates.sort(key=lambda w: hyperbolic_distance(origin.position, w.position))
    full_path = [origin, *intermediates, destination]

    return plan_route(full_path, min_governance, perturbation_density=perturbation_density)


# ---------------------------------------------------------------------------
# Triadic temporal distance (L11)
# ---------------------------------------------------------------------------


def triadic_temporal_distance(route: Route) -> float:
    """Compute L11 triadic temporal distance for a route.

    Three scales: immediate (phase deviation), medium (governance variance
    in 3-segment windows), long-term (overall governance trend).
    """
    if not route.segments:
        return 0.0

    immediate = sum(s.phase_deviation for s in route.segments) / len(route.segments)

    medium = 0.0
    if len(route.segments) >= 3:
        windows = []
        for i in range(len(route.segments) - 2):
            avg = sum(route.segments[i + j].governance_score for j in range(3)) / 3
            windows.append(avg)
        mean = sum(windows) / len(windows)
        medium = sum((w - mean) ** 2 for w in windows) / len(windows)

    long_term = 1.0 - route.avg_governance_score

    w_i, w_m, w_l = 1.0, PHI, PHI**2
    total = w_i + w_m + w_l
    return (w_i * immediate + w_m * medium + w_l * long_term) / total


# ---------------------------------------------------------------------------
# Compass Rose (visualization data)
# ---------------------------------------------------------------------------


def generate_compass_rose() -> List[Dict[str, object]]:
    """Generate the 6-point compass rose for visualization."""
    return [
        {
            "tongue": t,
            "angle": COMPASS_BEARINGS[t],
            "weight": TONGUE_WEIGHTS[t],
            "position": (math.cos(COMPASS_BEARINGS[t]), math.sin(COMPASS_BEARINGS[t])),
        }
        for t in TONGUES
    ]


def bearing_to_string(bearing: CompassBearing) -> str:
    """Human-readable compass direction."""
    FULL_NAMES = {
        "KO": "Kor'aelin",
        "AV": "Avali",
        "RU": "Runethic",
        "CA": "Cassisivadan",
        "UM": "Umbroth",
        "DR": "Draumric",
    }
    if bearing.blend < 0.1:
        return f"{FULL_NAMES[bearing.dominant_tongue]}-ward"
    return f"between {FULL_NAMES[bearing.dominant_tongue]} and {FULL_NAMES[bearing.secondary_tongue]}"
