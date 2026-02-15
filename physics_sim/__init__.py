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

from .patrol import (
    validate_params,
    validated_simulation,
    ValidationResult,
    Decision,
)

__all__ = [
    "classical_mechanics",
    "quantum_mechanics",
    "electromagnetism",
    "thermodynamics",
    "relativity",
    "lambda_handler",
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
    "validate_params",
    "validated_simulation",
    "ValidationResult",
    "Decision",
]
