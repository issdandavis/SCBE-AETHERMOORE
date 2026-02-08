"""
AI Brain Mapping Module - Python Reference Implementation

Multi-Vectored Quasi-Space Architecture with Lattice Mesh Integration.
Unifies all SCBE-AETHERMOORE components into a single coherent "AI brain"
architecture operating across a 21D manifold.

Version: 1.1.0 (Reference - canonical implementation is TypeScript)
"""

from .unified_state import UnifiedBrainState, safe_poincare_embed, hyperbolic_distance_safe
from .detection import (
    detect_phase_distance,
    detect_curvature_accumulation,
    detect_threat_lissajous,
    detect_decimal_drift,
    detect_six_tonic,
    run_combined_detection,
)
from .bft_consensus import BFTConsensus
from .dual_ternary import (
    DualTernarySystem,
    DualTernaryState,
    DualTernaryConfig,
    FULL_STATE_SPACE,
    compute_state_energy,
    state_index,
    state_from_index,
    transition,
    encode_to_dual_ternary,
    encode_sequence as encode_dual_ternary_sequence,
    compute_spectrum as compute_dual_ternary_spectrum,
    estimate_fractal_dimension as estimate_ternary_fractal_dimension,
)
from .dual_lattice import (
    DualLatticeSystem,
    DualLatticeConfig,
    Lattice6D,
    Lattice3D,
    PhasonShift,
    static_projection,
    dynamic_transform,
    generate_aperiodic_mesh,
    apply_phason_shift,
    estimate_fractal_dimension as estimate_lattice_fractal_dimension,
    lattice_norm_6d,
    lattice_distance_3d,
)

__all__ = [
    "UnifiedBrainState",
    "safe_poincare_embed",
    "hyperbolic_distance_safe",
    "detect_phase_distance",
    "detect_curvature_accumulation",
    "detect_threat_lissajous",
    "detect_decimal_drift",
    "detect_six_tonic",
    "run_combined_detection",
    "BFTConsensus",
    # Dual Ternary
    "DualTernarySystem",
    "DualTernaryState",
    "DualTernaryConfig",
    "FULL_STATE_SPACE",
    "compute_state_energy",
    "state_index",
    "state_from_index",
    "transition",
    "encode_to_dual_ternary",
    "encode_dual_ternary_sequence",
    "compute_dual_ternary_spectrum",
    "estimate_ternary_fractal_dimension",
    # Dual Lattice
    "DualLatticeSystem",
    "DualLatticeConfig",
    "Lattice6D",
    "Lattice3D",
    "PhasonShift",
    "static_projection",
    "dynamic_transform",
    "generate_aperiodic_mesh",
    "apply_phason_shift",
    "estimate_lattice_fractal_dimension",
    "lattice_norm_6d",
    "lattice_distance_3d",
]
