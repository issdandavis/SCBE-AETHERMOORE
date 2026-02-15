"""
Physics Simulation Module

Real physics calculations only - no pseudoscience.
Covers: Classical Mechanics, Quantum Mechanics, Electromagnetism,
        Thermodynamics, and Relativity.

SCBE integration: scbe_guard provides patrol/wall input validation.
"""

from .core import (
    classical_mechanics,
    quantum_mechanics,
    electromagnetism,
    thermodynamics,
    relativity,
    lambda_handler,
    PLANCK,
    HBAR,
    C,
    G,
    ELECTRON_MASS,
    PROTON_MASS,
    NEUTRON_MASS,
    ELEMENTARY_CHARGE,
    BOLTZMANN,
    AVOGADRO,
)
from .scbe_guard import guard_params, guarded_simulate, GuardResult, PhysicsViolation

__all__ = [
    "classical_mechanics",
    "quantum_mechanics",
    "electromagnetism",
    "thermodynamics",
    "relativity",
    "lambda_handler",
    "guard_params",
    "guarded_simulate",
    "GuardResult",
    "PhysicsViolation",
    "PLANCK",
    "HBAR",
    "C",
    "G",
    "ELECTRON_MASS",
    "PROTON_MASS",
    "NEUTRON_MASS",
    "ELEMENTARY_CHARGE",
    "BOLTZMANN",
    "AVOGADRO",
]
