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
from .multiscale_spectrum import (
    analyze_trajectory,
    analyze_subsystem,
    multiscale_spectrum_features,
    sliding_window_analysis,
    MultiscaleReport,
    ScaleFeatures,
)
from .mirror_shift import (
    analyze_transition,
    compute_dual_ternary,
    dual_ternary_trajectory,
    mirror_shift,
    mirror_asymmetry_score,
    quantize_ternary,
    refactor_align,
    MirrorAnalysis,
    MirrorShiftResult,
    AlignmentResult,
)
from .governance_adapter import (
    MicroStateType,
    MicroStateCensus,
    census_from_ternary,
    check_valence,
    AsymmetryTracker,
    flux_contract,
    GovernanceVerdict,
    evaluate_governance,
    evaluate_trajectory_governance,
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
    # Multiscale Spectrum Analysis
    "analyze_trajectory",
    "analyze_subsystem",
    "multiscale_spectrum_features",
    "sliding_window_analysis",
    "MultiscaleReport",
    "ScaleFeatures",
    # Mirror Shift + Refactor Align
    "analyze_transition",
    "compute_dual_ternary",
    "dual_ternary_trajectory",
    "mirror_shift",
    "mirror_asymmetry_score",
    "quantize_ternary",
    "refactor_align",
    "MirrorAnalysis",
    "MirrorShiftResult",
    "AlignmentResult",
    # Governance Adapter (6-state dual propagation)
    "MicroStateType",
    "MicroStateCensus",
    "census_from_ternary",
    "check_valence",
    "AsymmetryTracker",
    "flux_contract",
    "GovernanceVerdict",
    "evaluate_governance",
    "evaluate_trajectory_governance",
]
