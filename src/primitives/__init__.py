"""SCBE Primitives — fundamental building blocks."""
from .phi_ternary import (
    PhiTernary,
    DualPhiTernary,
    phi_ternary,
    dual_phi_ternary,
    tongue_phi_ternary,
    tongue_vector_to_phi_ternary,
    phi_ternary_energy,
    phi_ternary_center,
    phi_ternary_symmetry,
    PHI,
    TONGUE_PHI_K,
)

from .phi_poincare import (
    phi_lifted_poincare_projection,
    phi_shell_radius,
    fibonacci_ternary_consensus,
    fibonacci_trust_level,
    harmonic_cost_at_shell,
    FIB_LADDER,
)

__all__ = [
    "PhiTernary", "DualPhiTernary",
    "phi_ternary", "dual_phi_ternary", "tongue_phi_ternary",
    "tongue_vector_to_phi_ternary",
    "phi_ternary_energy", "phi_ternary_center", "phi_ternary_symmetry",
    "PHI", "TONGUE_PHI_K",
    "phi_lifted_poincare_projection", "phi_shell_radius",
    "fibonacci_ternary_consensus", "fibonacci_trust_level",
    "harmonic_cost_at_shell", "FIB_LADDER",
]
