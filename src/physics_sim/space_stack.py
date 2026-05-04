#!/usr/bin/env python3
"""
Space stack helpers for autonomous swarm coordination and self-maintenance.

This module extends existing orbital/simulation tooling with:
- formation coordination checks,
- FDIR-style health scoring and safe-hold decisions,
- roundtable authorization tiers for critical maneuvers,
- simple electrodynamic-tether style energy accounting.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

try:
    from python.scbe.state9d_engine import State9D, quantum_norm
except Exception:  # pragma: no cover - fallback for environments without SCBE python package path
    State9D = None  # type: ignore[assignment]
    quantum_norm = None  # type: ignore[assignment]


@dataclass
class SwarmVehicle:
    """Runtime state for one autonomous vehicle in the swarm."""

    vehicle_id: str
    position_m: List[float]
    velocity_m_s: List[float]
    battery_soc: float
    thermal_margin_c: float
    actuator_health: float
    comm_link_quality: float


@dataclass
class FDIRThresholds:
    """Thresholds used to trigger fault responses."""

    min_battery_soc: float = 0.20
    min_thermal_margin_c: float = 5.0
    min_actuator_health: float = 0.65
    min_comm_link_quality: float = 0.40


@dataclass
class CoordinationThresholds:
    """Coordination constraints for close-proximity operations."""

    min_separation_m: float = 5.0
    max_closure_rate_m_s: float = 0.20


POLICY_TIER_SIGNATURES: Dict[str, Tuple[str, ...]] = {
    "standard": ("AV",),
    "strict": ("KO", "RU", "UM"),
    "critical": ("KO", "RU", "UM", "CA"),
}

_STATE9D_CACHE_MAX = 512
_STATE9D_SCORE_CACHE: Dict[Tuple[str, float, float, float], Tuple[float, Dict[str, Any] | None]] = {}


def _vec_sub(a: List[float], b: List[float]) -> List[float]:
    return [a[i] - b[i] for i in range(3)]


def _vec_norm(v: List[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def _vec_dot(a: List[float], b: List[float]) -> float:
    return sum(a[i] * b[i] for i in range(3))


def evaluate_pair_safety(
    vehicle_a: SwarmVehicle,
    vehicle_b: SwarmVehicle,
    thresholds: CoordinationThresholds | None = None,
) -> Dict[str, float | bool]:
    """
    Evaluate separation and closure rate between two vehicles.
    """
    thresholds = thresholds or CoordinationThresholds()
    rel_pos = _vec_sub(vehicle_b.position_m, vehicle_a.position_m)
    rel_vel = _vec_sub(vehicle_b.velocity_m_s, vehicle_a.velocity_m_s)

    separation = _vec_norm(rel_pos)
    if separation < 1e-9:
        closure_rate = float("inf")
    else:
        # Positive means closing, negative means opening.
        closure_rate = -_vec_dot(rel_vel, rel_pos) / separation

    separation_ok = separation >= thresholds.min_separation_m
    closure_ok = closure_rate <= thresholds.max_closure_rate_m_s

    return {
        "separation_m": separation,
        "closure_rate_m_s": closure_rate,
        "separation_ok": separation_ok,
        "closure_ok": closure_ok,
        "safe_for_proximity_ops": separation_ok and closure_ok,
    }


def evaluate_fdir_status(
    vehicle: SwarmVehicle,
    thresholds: FDIRThresholds | None = None,
    state_time_s: float | None = None,
    include_state9d_payload: bool = True,
) -> Dict[str, object]:
    """
    Produce health/fault view and safe-hold recommendation for one vehicle.
    """
    thresholds = thresholds or FDIRThresholds()
    faults: List[str] = []

    if vehicle.battery_soc < thresholds.min_battery_soc:
        faults.append("low_power")
    if vehicle.thermal_margin_c < thresholds.min_thermal_margin_c:
        faults.append("thermal_margin_low")
    if vehicle.actuator_health < thresholds.min_actuator_health:
        faults.append("actuator_degraded")
    if vehicle.comm_link_quality < thresholds.min_comm_link_quality:
        faults.append("comm_unreliable")

    local_health_score = (
        0.35 * max(0.0, min(1.0, vehicle.battery_soc))
        + 0.20 * max(0.0, min(1.0, vehicle.thermal_margin_c / 20.0))
        + 0.30 * max(0.0, min(1.0, vehicle.actuator_health))
        + 0.15 * max(0.0, min(1.0, vehicle.comm_link_quality))
    )

    state9d_used = False
    state9d_health_score = local_health_score
    state9d_payload: Dict[str, Any] | None = None

    if State9D is not None and state_time_s is not None:
        trajectory_score = (vehicle.actuator_health + vehicle.comm_link_quality) / 2.0
        cache_key = (
            vehicle.vehicle_id,
            round(state_time_s, 6),
            round(trajectory_score, 6),
            round(vehicle.comm_link_quality, 6),
        )
        cached = _STATE9D_SCORE_CACHE.get(cache_key)
        if cached is not None:
            state9d_health_score, cached_payload = cached
            if include_state9d_payload:
                state9d_payload = cached_payload
        else:
            state = State9D.from_params(
                t=state_time_s,
                trajectory_score=trajectory_score,
                commitment_str=vehicle.vehicle_id,
                signature_validity=vehicle.comm_link_quality,
                use_ode_entropy=True,
                eta0=4.0,
            )
            entropy_score = max(0.0, min(1.0, 1.0 - abs(state.eta - 4.0) / 2.0))
            coherence_score = max(0.0, min(1.0, float(quantum_norm(state.q)))) if quantum_norm is not None else 1.0
            time_drift = max(0.0, state.tau - state_time_s)
            time_score = max(0.0, min(1.0, 1.0 - time_drift / 20.0))
            context_score = max(0.0, min(1.0, (float(state.context[2]) + float(state.context[5])) / 2.0))
            state9d_health_score = (
                0.30 * context_score + 0.25 * entropy_score + 0.25 * coherence_score + 0.20 * time_score
            )
            if include_state9d_payload:
                state9d_payload = state.to_dict()
            if len(_STATE9D_SCORE_CACHE) >= _STATE9D_CACHE_MAX:
                _STATE9D_SCORE_CACHE.pop(next(iter(_STATE9D_SCORE_CACHE)))
            _STATE9D_SCORE_CACHE[cache_key] = (state9d_health_score, state9d_payload)
        state9d_used = True

    health_score = 0.55 * local_health_score + 0.45 * state9d_health_score

    return {
        "vehicle_id": vehicle.vehicle_id,
        "faults": faults,
        "health_score": health_score,
        "local_health_score": local_health_score,
        "state9d_health_score": state9d_health_score,
        "state9d_used": state9d_used,
        "state9d": state9d_payload,
        "safe_hold_required": len(faults) > 0,
    }


def authorize_roundtable_operation(tier: str, signatures: List[str]) -> bool:
    """
    Verify if provided signatures satisfy policy tier requirements.
    """
    required = POLICY_TIER_SIGNATURES.get(tier)
    if required is None:
        raise ValueError(f"Unknown policy tier: {tier}")
    signature_set = set(signatures)
    return all(sig in signature_set for sig in required)


def assign_energy_roles(vehicles: List[SwarmVehicle]) -> Dict[str, str]:
    """
    Assign swarm roles based on health and state of charge.

    Roles:
    - injector: strongest power reserve for maneuver initiation
    - harvester: good reserve, available for regen windows
    - stabilizer: best actuator+comm quality
    - standby: everyone else
    """
    if not vehicles:
        return {}

    injector = max(vehicles, key=lambda v: (v.battery_soc, v.actuator_health))
    stabilizer = max(vehicles, key=lambda v: (v.actuator_health, v.comm_link_quality))

    remaining = [v for v in vehicles if v.vehicle_id not in {injector.vehicle_id, stabilizer.vehicle_id}]
    harvester = max(remaining, key=lambda v: v.battery_soc) if remaining else injector

    roles = {v.vehicle_id: "standby" for v in vehicles}
    roles[injector.vehicle_id] = "injector"
    roles[stabilizer.vehicle_id] = "stabilizer"
    roles[harvester.vehicle_id] = "harvester"
    return roles


def electrodynamic_tether_power(
    tether_length_m: float,
    magnetic_field_t: float,
    orbital_velocity_m_s: float,
    current_a: float,
    efficiency: float = 0.8,
) -> Dict[str, float]:
    """
    Estimate generated electrical power and orbital energy debit.

    Approximation:
    - Induced EMF ~ v * B * L
    - Electrical power ~= EMF * I * efficiency
    - Generated electrical power is extracted from orbital/mechanical energy.
    """
    emf_v = abs(orbital_velocity_m_s * magnetic_field_t * tether_length_m)
    generated_power_w = max(0.0, emf_v * current_a * max(0.0, min(1.0, efficiency)))
    orbital_energy_debit_w = generated_power_w
    return {
        "emf_v": emf_v,
        "generated_power_w": generated_power_w,
        "orbital_energy_debit_w": orbital_energy_debit_w,
    }


def governance_decision(
    safety_score: float,
    allow_threshold: float = 0.85,
    quarantine_threshold: float = 0.65,
    escalate_threshold: float = 0.45,
) -> str:
    """Map safety score into ALLOW/QUARANTINE/ESCALATE/DENY."""
    if safety_score >= allow_threshold:
        return "ALLOW"
    if safety_score >= quarantine_threshold:
        return "QUARANTINE"
    if safety_score >= escalate_threshold:
        return "ESCALATE"
    return "DENY"


def decide_vehicle_governance(
    vehicle: SwarmVehicle,
    state_time_s: float,
    thresholds: FDIRThresholds | None = None,
    allow_threshold: float = 0.85,
    quarantine_threshold: float = 0.65,
    escalate_threshold: float = 0.45,
    include_state9d_payload: bool = False,
) -> Dict[str, object]:
    """
    Evaluate FDIR + State9D then return governance decision packet.
    """
    status = evaluate_fdir_status(
        vehicle,
        thresholds=thresholds,
        state_time_s=state_time_s,
        include_state9d_payload=include_state9d_payload,
    )
    decision = governance_decision(
        float(status["health_score"]),
        allow_threshold=allow_threshold,
        quarantine_threshold=quarantine_threshold,
        escalate_threshold=escalate_threshold,
    )
    return {
        "vehicle_id": vehicle.vehicle_id,
        "decision": decision,
        "fdir_status": status,
    }
