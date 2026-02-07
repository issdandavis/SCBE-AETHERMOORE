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
]
