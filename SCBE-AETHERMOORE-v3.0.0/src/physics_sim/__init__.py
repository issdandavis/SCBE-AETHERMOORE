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
    ELEMENTARY_CHARGE,
    BOLTZMANN,
    AVOGADRO,
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
    "ELEMENTARY_CHARGE",
    "BOLTZMANN",
    "AVOGADRO",
]
