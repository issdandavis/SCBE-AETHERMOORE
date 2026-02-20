"""
Decision envelope predicate evaluator.

This module intentionally does not invent policy. It only evaluates whether a
given action/state is inside or outside the constraints encoded in a signed
decision envelope.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Tuple


RISK_TIER_ORDER: Dict[str, int] = {
    "REFLEX": 1,
    "DELIBERATION": 2,
    "CRITICAL": 3,
}


@dataclass(frozen=True)
class TargetRef:
    kind: str
    id: str


@dataclass(frozen=True)
class ResourceState:
    power_mw: float
    bandwidth_kbps: float
    thermal_headroom_c: float


@dataclass(frozen=True)
class ActionState:
    mission_phase: str
    agent_id: str
    capability_id: str
    target: TargetRef
    risk_tier: str
    resources: ResourceState


@dataclass(frozen=True)
class EnvelopePredicateResult:
    inside_boundary: bool
    scarcity_score: float
    harmonic_cost: float
    violations: Tuple[str, ...]


def evaluate_action_inside_envelope(
    action: ActionState,
    envelope: Mapping[str, Any],
) -> EnvelopePredicateResult:
    """
    Return whether action/state is inside the envelope constraints.

    The return value is a pure predicate result and supporting math telemetry.
    It does not assign runtime policy behavior.
    """

    scope = _mapping(envelope, "scope")
    constraints = _mapping(envelope, "constraints")
    boundary = _mapping(envelope, "boundary")
    _validate_boundary_recovery(boundary)

    violations = []

    phase_allow = _string_set(_iterable(constraints, "mission_phase_allowlist"))
    if action.mission_phase not in phase_allow:
        violations.append(f"mission_phase_not_allowed:{action.mission_phase}")

    agent_allow = _string_set(_iterable(scope, "agent_allowlist"))
    if action.agent_id not in agent_allow:
        violations.append(f"agent_not_allowed:{action.agent_id}")

    capability_allow = _string_set(_iterable(scope, "capability_allowlist"))
    if action.capability_id not in capability_allow:
        violations.append(f"capability_not_allowed:{action.capability_id}")

    target_allow = {
        (str(item.get("kind", "")), str(item.get("id", "")))
        for item in _iterable(scope, "target_allowlist")
        if isinstance(item, Mapping)
    }
    if (action.target.kind, action.target.id) not in target_allow:
        violations.append(f"target_not_allowed:{action.target.kind}:{action.target.id}")

    max_risk_tier = str(constraints.get("max_risk_tier", ""))
    if not _risk_tier_is_within(action.risk_tier, max_risk_tier):
        violations.append(f"risk_tier_exceeds_max:{action.risk_tier}>{max_risk_tier}")

    floors = _mapping(constraints, "resource_floors")
    harmonic = _mapping(constraints, "harmonic_wall")
    power_floor = float(floors.get("power_mw_min", 0.0))
    bandwidth_floor = float(floors.get("bandwidth_kbps_min", 0.0))
    thermal_floor = float(floors.get("thermal_headroom_c_min", 0.0))
    if action.resources.power_mw < power_floor:
        violations.append(
            f"resource_floor_power_below:{action.resources.power_mw:.6f}<"
            f"{power_floor:.6f}"
        )
    if action.resources.bandwidth_kbps < bandwidth_floor:
        violations.append(
            "resource_floor_bandwidth_below:"
            f"{action.resources.bandwidth_kbps:.6f}<{bandwidth_floor:.6f}"
        )
    if action.resources.thermal_headroom_c < thermal_floor:
        violations.append(
            "resource_floor_thermal_below:"
            f"{action.resources.thermal_headroom_c:.6f}<{thermal_floor:.6f}"
        )

    scarcity_score, harmonic_cost = _harmonic_wall_score(action.resources, floors, harmonic)
    scarcity_limit = float(harmonic.get("scarcity_limit", 0.0))
    if scarcity_score > scarcity_limit:
        violations.append(
            f"scarcity_limit_exceeded:{scarcity_score:.6f}>{scarcity_limit:.6f}"
        )

    return EnvelopePredicateResult(
        inside_boundary=not violations,
        scarcity_score=scarcity_score,
        harmonic_cost=harmonic_cost,
        violations=tuple(violations),
    )


def evaluate_action_dict_inside_envelope(
    action: Mapping[str, Any],
    envelope: Mapping[str, Any],
) -> EnvelopePredicateResult:
    """Dictionary-friendly adapter around evaluate_action_inside_envelope()."""

    state = ActionState(
        mission_phase=str(action.get("mission_phase", "")),
        agent_id=str(action.get("agent_id", "")),
        capability_id=str(action.get("capability_id", "")),
        target=TargetRef(
            kind=str(_mapping(action, "target").get("kind", "")),
            id=str(_mapping(action, "target").get("id", "")),
        ),
        risk_tier=str(action.get("risk_tier", "")),
        resources=ResourceState(
            power_mw=float(_mapping(action, "resources").get("power_mw", 0.0)),
            bandwidth_kbps=float(
                _mapping(action, "resources").get("bandwidth_kbps", 0.0)
            ),
            thermal_headroom_c=float(
                _mapping(action, "resources").get("thermal_headroom_c", 0.0)
            ),
        ),
    )
    return evaluate_action_inside_envelope(state, envelope)


def _validate_boundary_recovery(boundary: Mapping[str, Any]) -> None:
    behavior = str(boundary.get("behavior", ""))
    if behavior in {"QUARANTINE", "DENY"} and not isinstance(
        boundary.get("recovery"), Mapping
    ):
        raise ValueError(
            "Decision envelope boundary requires recovery metadata when "
            "behavior is QUARANTINE or DENY."
        )


def _risk_tier_is_within(actual: str, max_allowed: str) -> bool:
    a = RISK_TIER_ORDER.get(actual, 10_000)
    m = RISK_TIER_ORDER.get(max_allowed, -1)
    return a <= m


def _harmonic_wall_score(
    resources: ResourceState,
    floors: Mapping[str, Any],
    harmonic: Mapping[str, Any],
) -> Tuple[float, float]:
    power_floor = float(floors.get("power_mw_min", 0.0))
    bandwidth_floor = float(floors.get("bandwidth_kbps_min", 0.0))
    thermal_floor = float(floors.get("thermal_headroom_c_min", 0.0))

    deficits = (
        _relative_deficit(resources.power_mw, power_floor),
        _relative_deficit(resources.bandwidth_kbps, bandwidth_floor),
        _relative_deficit(resources.thermal_headroom_c, thermal_floor),
    )
    scarcity_score = sum(deficits) / 3.0

    base = float(harmonic.get("base", 2.0))
    alpha = float(harmonic.get("alpha", 1.0))
    harmonic_cost = base ** (alpha * (scarcity_score**2))
    return scarcity_score, harmonic_cost


def _relative_deficit(value: float, floor: float) -> float:
    if floor <= 0:
        return 0.0
    return max(0.0, (floor - value) / floor)


def _mapping(obj: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = obj.get(key)
    if isinstance(value, Mapping):
        return value
    return {}


def _iterable(obj: Mapping[str, Any], key: str) -> Iterable[Any]:
    value = obj.get(key)
    if isinstance(value, list):
        return value
    return []


def _string_set(items: Iterable[Any]) -> set[str]:
    return {str(item) for item in items}
