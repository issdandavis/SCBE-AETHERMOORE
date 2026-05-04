#!/usr/bin/env python3
"""Tests for space swarm coordination/self-maintenance helpers."""

from src.physics_sim.space_stack import (
    SwarmVehicle,
    CoordinationThresholds,
    evaluate_pair_safety,
    evaluate_fdir_status,
    authorize_roundtable_operation,
    assign_energy_roles,
    electrodynamic_tether_power,
    governance_decision,
    decide_vehicle_governance,
)


def _vehicle(
    vehicle_id: str,
    x: float,
    y: float,
    vx: float,
    vy: float,
    soc: float = 0.8,
    thermal_margin_c: float = 10.0,
    actuator_health: float = 0.9,
    comm_link_quality: float = 0.9,
) -> SwarmVehicle:
    return SwarmVehicle(
        vehicle_id=vehicle_id,
        position_m=[x, y, 0.0],
        velocity_m_s=[vx, vy, 0.0],
        battery_soc=soc,
        thermal_margin_c=thermal_margin_c,
        actuator_health=actuator_health,
        comm_link_quality=comm_link_quality,
    )


def test_pair_safety_detects_closure_violations():
    a = _vehicle("A", 0.0, 0.0, 0.0, 0.0)
    b = _vehicle("B", 3.0, 0.0, -0.4, 0.0)
    result = evaluate_pair_safety(a, b, CoordinationThresholds(min_separation_m=5.0, max_closure_rate_m_s=0.2))
    assert result["separation_ok"] is False
    assert result["closure_ok"] is False
    assert result["safe_for_proximity_ops"] is False


def test_fdir_flags_low_power_and_comm():
    vehicle = _vehicle("faulty", 0.0, 0.0, 0.0, 0.0, soc=0.15, comm_link_quality=0.2)
    status = evaluate_fdir_status(vehicle)
    assert "low_power" in status["faults"]
    assert "comm_unreliable" in status["faults"]
    assert status["safe_hold_required"] is True


def test_fdir_uses_state9d_when_time_provided():
    vehicle = _vehicle("stateful", 0.0, 0.0, 0.0, 0.0, soc=0.8, comm_link_quality=0.85)
    status = evaluate_fdir_status(vehicle, state_time_s=12.0)
    assert status["state9d_used"] is True
    assert isinstance(status["state9d"], dict)
    assert "context" in status["state9d"]
    assert status["health_score"] >= 0.0
    assert status["health_score"] <= 1.0


def test_roundtable_critical_requires_all_signatures():
    assert authorize_roundtable_operation("critical", ["KO", "RU", "UM", "CA"]) is True
    assert authorize_roundtable_operation("critical", ["KO", "RU", "UM"]) is False


def test_assign_energy_roles_sets_key_positions():
    v1 = _vehicle("v1", 0, 0, 0, 0, soc=0.95, actuator_health=0.85)
    v2 = _vehicle("v2", 10, 0, 0, 0, soc=0.70, actuator_health=0.98, comm_link_quality=0.97)
    v3 = _vehicle("v3", 20, 0, 0, 0, soc=0.90, actuator_health=0.70)
    roles = assign_energy_roles([v1, v2, v3])
    assert roles["v1"] == "injector"
    assert roles["v2"] == "stabilizer"
    assert roles["v3"] == "harvester"


def test_electrodynamic_tether_energy_is_positive():
    p = electrodynamic_tether_power(
        tether_length_m=1000.0,
        magnetic_field_t=3e-5,
        orbital_velocity_m_s=7600.0,
        current_a=2.0,
        efficiency=0.8,
    )
    assert p["emf_v"] > 0
    assert p["generated_power_w"] > 0
    assert p["generated_power_w"] == p["orbital_energy_debit_w"]


def test_governance_decision_thresholds():
    assert governance_decision(0.9) == "ALLOW"
    assert governance_decision(0.7) == "QUARANTINE"
    assert governance_decision(0.5) == "ESCALATE"
    assert governance_decision(0.2) == "DENY"


def test_decide_vehicle_governance_packet():
    vehicle = _vehicle("gov", 0.0, 0.0, 0.0, 0.0, soc=0.92, comm_link_quality=0.95)
    packet = decide_vehicle_governance(vehicle, state_time_s=30.0)
    assert packet["vehicle_id"] == "gov"
    assert packet["decision"] in {"ALLOW", "QUARANTINE", "ESCALATE", "DENY"}
    assert "fdir_status" in packet
