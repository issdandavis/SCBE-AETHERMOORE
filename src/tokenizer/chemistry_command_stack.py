from __future__ import annotations

from typing import Any


PRIMITIVES = [
    {
        "primitive": "measure_state",
        "intent": "establish the pre-change state window before mutation",
        "simulation_backends": ["rdkit", "openff"],
        "delta": 0.0,
    },
    {
        "primitive": "stabilize_fragment",
        "intent": "relax the current fragment toward a lower-energy local basin",
        "simulation_backends": ["openmm", "ase"],
        "delta": -0.2,
    },
    {
        "primitive": "bind_operation",
        "intent": "bind semantic command slots into an executable workflow unit",
        "simulation_backends": ["rdkit", "ase"],
        "delta": 0.1,
    },
    {
        "primitive": "verify_reversibility",
        "intent": "check that the transport and semantic lanes can be reconstructed",
        "simulation_backends": ["openff"],
        "delta": 0.0,
    },
]


def _operation(topology: dict[str, Any]) -> dict[str, Any]:
    return topology.get("operative_command") or {}


def _avg_valence(packet: dict[str, Any]) -> float:
    states = packet.get("atomic_states") or []
    if not states:
        return 0.0
    values = [float((state.get("element") or {}).get("valence", 0.0)) for state in states]
    return round(sum(values) / len(values), 6)


def _charge_spread(packet: dict[str, Any]) -> float:
    states = packet.get("atomic_states") or []
    if not states:
        return 0.0
    values = [float((state.get("element") or {}).get("electronegativity", 0.0)) for state in states]
    return round(max(values) - min(values), 6) if values else 0.0


def build_chemistry_command_stack(packet: dict[str, Any], topology: dict[str, Any]) -> dict[str, Any]:
    operation = _operation(topology)
    command_key = str(operation.get("command_key") or "operation")
    phase_operation = str(operation.get("phase_operation") or "compose")
    binary_input = str(operation.get("binary_input") or "")
    key_slot = str(operation.get("key_slot") or (packet.get("route") or {}).get("tongue") or "KO")

    commands = []
    for index, primitive in enumerate(PRIMITIVES):
        commands.append(
            {
                "command_id": f"chemcmd:{index:03d}",
                "command_key": command_key,
                "phase_operation": phase_operation,
                "binary_input": binary_input,
                "key_slot": key_slot,
                "primitive": primitive["primitive"],
                "intent": primitive["intent"],
                "reversible": True,
                "simulation_backends": list(primitive["simulation_backends"]),
                "state_revector": [0.0, 0.0, 0.0, 0.0, primitive["delta"], -0.5, 0.0, 1.0],
            }
        )

    return {
        "schema_version": "scbe-chemistry-command-stack-v1",
        "semantic_compound_commands": commands,
        "validation": {
            "avg_valence_proxy": _avg_valence(packet),
            "charge_spread": _charge_spread(packet),
            "deterministic_projection": True,
            "ready_for_external_simulation": True,
            "recommended_backends": ["rdkit", "openff", "openmm", "ase"],
        },
    }


__all__ = ["build_chemistry_command_stack"]
