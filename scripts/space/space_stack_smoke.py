#!/usr/bin/env python3
"""Smoke run for space swarm coordination + FDIR helpers."""

import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.physics_sim.space_stack import (
    SwarmVehicle,
    evaluate_pair_safety,
    evaluate_fdir_status,
    assign_energy_roles,
    decide_vehicle_governance,
    electrodynamic_tether_power,
)


def main() -> None:
    swarm = [
        SwarmVehicle(
            vehicle_id="SHEPHERD-01",
            position_m=[0.0, 0.0, 0.0],
            velocity_m_s=[0.0, 0.0, 0.0],
            battery_soc=0.92,
            thermal_margin_c=12.0,
            actuator_health=0.86,
            comm_link_quality=0.80,
        ),
        SwarmVehicle(
            vehicle_id="SHEPHERD-02",
            position_m=[8.0, 0.0, 0.0],
            velocity_m_s=[-0.05, 0.0, 0.0],
            battery_soc=0.68,
            thermal_margin_c=14.0,
            actuator_health=0.95,
            comm_link_quality=0.94,
        ),
        SwarmVehicle(
            vehicle_id="SHEPHERD-03",
            position_m=[14.0, 0.0, 0.0],
            velocity_m_s=[0.0, 0.02, 0.0],
            battery_soc=0.84,
            thermal_margin_c=9.0,
            actuator_health=0.77,
            comm_link_quality=0.73,
        ),
    ]

    pair = evaluate_pair_safety(swarm[0], swarm[1])
    health = [evaluate_fdir_status(v) for v in swarm]
    roles = assign_energy_roles(swarm)
    power = electrodynamic_tether_power(
        tether_length_m=1200.0,
        magnetic_field_t=3e-5,
        orbital_velocity_m_s=7600.0,
        current_a=1.5,
        efficiency=0.82,
    )

    governance_packets = [decide_vehicle_governance(v, state_time_s=45.0) for v in swarm]

    print("Pair safety:", pair)
    print("FDIR health:", health)
    print("Roles:", roles)
    print("Tether power:", power)
    print("Governance packets:", governance_packets)


if __name__ == "__main__":
    main()
