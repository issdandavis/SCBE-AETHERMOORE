"""
Axiom-Grouped Module for SCBE-AETHERMOORE

Contains:
- Langues Metric with fluxing dimensions (Polly/Quasi/Demi)
- Layer 14 Audio Axis (FFT-based telemetry)
- Hamiltonian CFI (Control Flow Integrity)

Document ID: SCBE-AXIOM-2026-001
Version: 2.0.0
"""

# Langues Metric
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

# Layer 14: Audio Axis
from .audio_axis import (
    # Constants
    DEFAULT_N_FFT,
    DEFAULT_HF_FRAC,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_WA,
    
    # Enums
    AudioStability,
    
    # Classes
    AudioFeatures,
    AudioAxisProcessor,
    
    # Functions
    compute_fft,
    extract_energy,
    extract_centroid,
    extract_flux,
    extract_hf_ratio,
    classify_stability,
    extract_audio_features,
    audio_risk_additive,
    audio_risk_multiplicative,
    
    # Verification
    verify_stability_bounded,
    verify_hf_detection,
    verify_flux_sensitivity,
)

# Hamiltonian CFI (Topological Control Flow Integrity)
from .hamiltonian_cfi import (
    # Constants
    PHI as CFI_PHI,
    DEFAULT_EMBEDDING_DIM,
    DEFAULT_DEVIATION_THRESHOLD,
    DEFAULT_MAX_VERTICES,
    
    # Enums
    CFIDecision,
    
    # Classes
    CFGVertex,
    ControlFlowGraph,
    GoldenPath,
    CFIResult,
    HamiltonianCFI,
    
    # Functions
    compute_embedding_dimension,
    embed_cfg,
    compute_golden_path,
    
    # Verification
    verify_dirac_theorem,
    verify_bipartite_detection,
    verify_deviation_detection,
)

__all__ = [
    # === Langues Metric ===
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
    
    # === Layer 14: Audio Axis ===
    "DEFAULT_N_FFT",
    "DEFAULT_HF_FRAC",
    "DEFAULT_SAMPLE_RATE",
    "DEFAULT_WA",
    "AudioStability",
    "AudioFeatures",
    "AudioAxisProcessor",
    "compute_fft",
    "extract_energy",
    "extract_centroid",
    "extract_flux",
    "extract_hf_ratio",
    "classify_stability",
    "extract_audio_features",
    "audio_risk_additive",
    "audio_risk_multiplicative",
    "verify_stability_bounded",
    "verify_hf_detection",
    "verify_flux_sensitivity",
    
    # === Hamiltonian CFI (Topological) ===
    "CFI_PHI",
    "DEFAULT_EMBEDDING_DIM",
    "DEFAULT_DEVIATION_THRESHOLD",
    "DEFAULT_MAX_VERTICES",
    "CFIDecision",
    "CFGVertex",
    "ControlFlowGraph",
    "GoldenPath",
    "CFIResult",
    "HamiltonianCFI",
    "compute_embedding_dimension",
    "embed_cfg",
    "compute_golden_path",
    "verify_dirac_theorem",
    "verify_bipartite_detection",
    "verify_deviation_detection",
]

__version__ = "2.0.0"
