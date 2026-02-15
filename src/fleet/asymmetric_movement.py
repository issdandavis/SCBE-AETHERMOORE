#!/usr/bin/env python3
"""
Asymmetric Movement Model — Human vs AI Navigation in 6D Poincaré Ball.

Formalises the fundamental asymmetry between human and AI movement
in the 6D governance space.

  Humans:  2D lateral (X, Y) — left/right, forward/back
  AI:      6D hyperbolic (X, Y, Z, V, P, S) — including vertical depth

This is complementarity, not limitation:
  • Humans provide LATERAL coverage (breadth, context, judgment)
  • AI provides VERTICAL coverage (depth, speed, parallelism)
  • Together they span the full manifold

@module fleet/asymmetric_movement
@layer Layer 5, Layer 8, Layer 13
@component Asymmetric Movement Model
@version 3.2.4
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Literal, Tuple

# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════

Lang = Literal["KO", "AV", "RU", "CA", "UM", "DR"]
Decision = Literal["ALLOW", "QUARANTINE", "DENY"]
AxisLabel = Literal["X", "Y", "Z", "V", "P", "S"]
AgentKind = Literal["HUMAN", "AI", "HYBRID"]

Hyperbolic6D = Tuple[float, float, float, float, float, float]
ORIGIN: Hyperbolic6D = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

AXIS_LABELS: Tuple[AxisLabel, ...] = ("X", "Y", "Z", "V", "P", "S")
LATERAL_AXES: Tuple[AxisLabel, ...] = ("X", "Y")
VERTICAL_AXES: Tuple[AxisLabel, ...] = ("Z", "V", "P", "S")

TONGUE_AXIS: dict[Lang, AxisLabel] = {
    "KO": "X",  # flow orientation → lateral
    "AV": "Y",  # boundary condition → lateral
    "RU": "Z",  # constraint field → vertical (trust depth)
    "CA": "V",  # active operator → vertical (coherence)
    "UM": "P",  # entropic sink → vertical (policy)
    "DR": "S",  # structural tensor → vertical (stability)
}

AUTH_TIER_DEPTH: dict[Lang, float] = {
    "KO": 0.3,
    "AV": 0.5,
    "RU": 0.65,
    "CA": 0.8,
    "UM": 0.9,
    "DR": 0.95,
}


# ═══════════════════════════════════════════════════════════════
# Cost Functions
# ═══════════════════════════════════════════════════════════════


def _norm2(v: tuple[float, ...] | list[float]) -> float:
    return sum(x * x for x in v)


def ai_movement_cost(
    from_pos: Hyperbolic6D,
    to_pos: Hyperbolic6D,
    coherence: float,
    R: float = 1.5,
) -> float:
    """AI movement cost via H_eff in 6D Poincaré ball. Returns ∈ (0, 1]."""
    delta = tuple(t - f for f, t in zip(from_pos, to_pos))
    from_n2 = _norm2(from_pos)
    to_n2 = _norm2(to_pos)
    delta_n2 = _norm2(delta)

    denom = max((1 - from_n2) * (1 - to_n2), 1e-12)
    arg = 1 + 2 * delta_n2 / denom
    d = math.acosh(max(arg, 1.0))

    p = 1 - max(0.0, min(1.0, coherence))
    x = coherence
    return 1.0 / (1.0 + d + 2.0 * p * d * (1.0 - x / R))


def human_movement_cost(
    from_pos: Hyperbolic6D,
    to_pos: Hyperbolic6D,
) -> dict[str, float | bool]:
    """Human movement cost — free lateral, infinite vertical."""
    d_lat = math.sqrt((to_pos[0] - from_pos[0]) ** 2 + (to_pos[1] - from_pos[1]) ** 2)
    d_vert = math.sqrt(sum((to_pos[i] - from_pos[i]) ** 2 for i in range(2, 6)))
    has_vert = d_vert > 1e-9
    return {
        "lateral": d_lat,
        "vertical": float("inf") if has_vert else 0.0,
        "total": float("inf") if has_vert else d_lat,
        "reachable": not has_vert,
    }


# ═══════════════════════════════════════════════════════════════
# Fleet Unit
# ═══════════════════════════════════════════════════════════════


@dataclass
class HumanState:
    id: str
    lateral: Tuple[float, float] = (0.0, 0.0)
    physical: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    auth_tier: Lang = "CA"
    attention: float = 0.9
    latency_ms: float = 200.0


@dataclass
class AIState:
    id: str
    position: Hyperbolic6D = ORIGIN
    coherence: float = 0.85
    active_tongue: Lang = "RU"
    active_probes: int = 3


@dataclass
class FleetUnit:
    unit_id: str
    human: HumanState
    agents: List[AIState] = field(default_factory=list)
    composite_position: Hyperbolic6D = ORIGIN
    decision: Decision = "ALLOW"


def composite_position(unit: FleetUnit) -> Hyperbolic6D:
    """Compute 6D composite: human lateral + AI median vertical."""
    if not unit.agents:
        return (unit.human.lateral[0], unit.human.lateral[1], 0, 0, 0, 0)

    x, y = unit.human.lateral

    medians: list[float] = []
    for dim in range(2, 6):
        vals = sorted(a.position[dim] for a in unit.agents)
        mid = len(vals) // 2
        if len(vals) % 2 == 0:
            median = (vals[mid - 1] + vals[mid]) / 2
        else:
            median = vals[mid]
        medians.append(median)

    return (x, y, medians[0], medians[1], medians[2], medians[3])


def complementarity_score(unit: FleetUnit) -> float:
    """How well human + AI complement each other. Returns ∈ [0, 1]."""
    if not unit.agents:
        return 0.0

    lateral_cov = min(1.0, unit.human.attention)
    active = [a for a in unit.agents if a.coherence > 0.3]
    unique = len(set(a.active_tongue for a in active))
    vertical_cov = min(1.0, unique / 4.0)

    return math.sqrt(lateral_cov * vertical_cov)


def blind_spots(unit: FleetUnit) -> list[AxisLabel]:
    """Which dimensions have no active navigator."""
    covered: set[AxisLabel] = set()
    if unit.human.attention > 0.1:
        covered.add("X")
        covered.add("Y")
    for agent in unit.agents:
        if agent.coherence > 0.3:
            covered.add(TONGUE_AXIS[agent.active_tongue])
    return [a for a in AXIS_LABELS if a not in covered]


def validate_movement(
    unit: FleetUnit,
    proposed: Hyperbolic6D,
    proposer: Literal["HUMAN", "AI"],
) -> dict:
    """Validate a proposed movement for a fleet unit."""
    current = unit.composite_position
    moved: list[AxisLabel] = []
    for i, label in enumerate(AXIS_LABELS):
        if abs(proposed[i] - current[i]) > 1e-9:
            moved.append(label)

    # Human cannot move vertical
    if proposer == "HUMAN":
        vert_moved = [a for a in moved if a in VERTICAL_AXES]
        if vert_moved:
            return {
                "allowed": False,
                "human_cost": float("inf"),
                "ai_cost": 0,
                "moved_axes": moved,
                "reason": f"Human cannot move vertical axes: {', '.join(vert_moved)}. Delegate to AI.",
            }

    h_cost = human_movement_cost(current, proposed)
    median_coh = 0.0
    if unit.agents:
        cohs = sorted(a.coherence for a in unit.agents)
        median_coh = cohs[len(cohs) // 2]
    ai_cost = ai_movement_cost(current, proposed, median_coh)

    # Depth limit
    depth_limit = AUTH_TIER_DEPTH[unit.human.auth_tier]
    vert_depth = math.sqrt(sum(proposed[i] ** 2 for i in range(2, 6)))
    if vert_depth > depth_limit:
        return {
            "allowed": False,
            "human_cost": h_cost["lateral"],
            "ai_cost": ai_cost,
            "moved_axes": moved,
            "reason": f"Vertical depth {vert_depth:.3f} exceeds auth tier {unit.human.auth_tier} limit {depth_limit:.3f}",
        }

    if ai_cost < 0.05:
        return {
            "allowed": False,
            "human_cost": h_cost["lateral"],
            "ai_cost": ai_cost,
            "moved_axes": moved,
            "reason": f"AI movement cost too high (H_eff={ai_cost:.4f} < 0.05). Target is adversarially far.",
        }

    return {
        "allowed": True,
        "human_cost": h_cost["lateral"],
        "ai_cost": ai_cost,
        "moved_axes": moved,
    }
