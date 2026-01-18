"""
Axiom-Grouped Module for SCBE-AETHERMOORE

Contains the Langues Metric with fluxing dimensions (Polly/Quasi/Demi).
"""

from .langues_metric import (
    # Constants
    PHI,
    TAU,
    TONGUES,
    TONGUE_WEIGHTS,
    TONGUE_PHASES,
    TONGUE_FREQUENCIES,
    DIMENSIONS,
    
    # Core classes
    HyperspacePoint,
    IdealState,
    LanguesMetric,
    DimensionFlux,
    FluxingLanguesMetric,
    
    # Functions
    langues_distance,
    build_langues_metric_matrix,
    
    # Verification functions
    verify_monotonicity,
    verify_phase_bounded,
    verify_tongue_weights,
    verify_six_fold_symmetry,
    verify_flux_bounded,
    verify_dimension_conservation,
    verify_1d_projection,
)

__all__ = [
    # Constants
    "PHI",
    "TAU",
    "TONGUES",
    "TONGUE_WEIGHTS",
    "TONGUE_PHASES",
    "TONGUE_FREQUENCIES",
    "DIMENSIONS",
    
    # Core classes
    "HyperspacePoint",
    "IdealState",
    "LanguesMetric",
    "DimensionFlux",
    "FluxingLanguesMetric",
    
    # Functions
    "langues_distance",
    "build_langues_metric_matrix",
    
    # Verification functions
    "verify_monotonicity",
    "verify_phase_bounded",
    "verify_tongue_weights",
    "verify_six_fold_symmetry",
    "verify_flux_bounded",
    "verify_dimension_conservation",
    "verify_1d_projection",
]

__version__ = "1.0.0"
