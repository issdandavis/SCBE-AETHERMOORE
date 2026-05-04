"""
Physics Simulation Module

Real physics calculations only - no pseudoscience.
Covers: Classical Mechanics, Quantum Mechanics, Electromagnetism,
        Thermodynamics, and Relativity.
"""

from .core import (
    classical_mechanics,
    quantum_mechanics,
    electromagnetism,
    thermodynamics,
    relativity,
    harsh_physics_mode,
    lambda_handler,
    PLANCK,
    HBAR,
    C,
    G,
    ELECTRON_MASS,
    PROTON_MASS,
    ELEMENTARY_CHARGE,
    BOLTZMANN,
    AVOGADRO,
)
from .space_stack import (
    SwarmVehicle,
    FDIRThresholds,
    CoordinationThresholds,
    evaluate_pair_safety,
    evaluate_fdir_status,
    authorize_roundtable_operation,
    assign_energy_roles,
    electrodynamic_tether_power,
    governance_decision,
    decide_vehicle_governance,
)

__all__ = [
    "classical_mechanics",
    "quantum_mechanics",
    "electromagnetism",
    "thermodynamics",
    "relativity",
    "harsh_physics_mode",
    "lambda_handler",
    "PLANCK",
    "HBAR",
    "C",
    "G",
    "ELECTRON_MASS",
    "PROTON_MASS",
    "ELEMENTARY_CHARGE",
    "BOLTZMANN",
    "AVOGADRO",
    "SwarmVehicle",
    "FDIRThresholds",
    "CoordinationThresholds",
    "evaluate_pair_safety",
    "evaluate_fdir_status",
    "authorize_roundtable_operation",
    "assign_energy_roles",
    "electrodynamic_tether_power",
    "governance_decision",
    "decide_vehicle_governance",
]
