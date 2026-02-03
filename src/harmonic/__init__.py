"""
Harmonic Module - SCBE-AETHERMOORE

Core harmonic scaling and temporal intent tracking for the 14-layer pipeline.

Components:
- temporal_intent_scaling: H_eff(d, R, x) = R^(d²) · x formula with drift protection
- temporal_bridge: Bridges stateless pipeline with stateful agent tracking
- context_encoder: Context encoding utilities
- spectral_identity: Spectral identity computation

@module harmonic
@layer Layer 11, Layer 12
@version 1.0.0
@since 2026-02-02
"""

# Temporal Intent Scaling - Core formula H_eff(d, R, x) = R^(d²) · x
from .temporal_intent_scaling import (
    # Data structures
    DeviationChannels,
    TriadicTemporalState,
    TrajectoryCoherence,
    TemporalIntentState,
    TemporalRiskAssessment,
    # Drift protection
    DriftMonitor,
    with_drift_protection,
    reset_drift_monitor,
    get_drift_status,
    DRIFT_TOLERANCE,
    MAX_ACCUMULATED_DRIFT,
    PRECISION_DIGITS,
    # Core functions
    compute_temporal_intent_factor,
    update_temporal_state,
    harmonic_scale_basic,
    harmonic_scale_effective,
    harmonic_scale_with_state,
    security_bits_effective,
    assess_risk_temporal,
    # Convenience
    create_temporal_state,
    quick_harmonic_effective,
    # Constants
    PHI,
    PERFECT_FIFTH,
)

# Temporal Pipeline Bridge - Agent-level stateful tracking
from .temporal_bridge import (
    # Main class
    TemporalPipelineBridge,
    # Data classes
    AgentDecisionRecord,
    AgentProfile,
    # Registry functions
    get_bridge,
    clear_bridges,
    list_agents,
    get_all_summaries,
    # Global hive
    set_global_hive,
    get_global_hive,
    HIVE_AVAILABLE,
    # Helper
    process_with_temporal,
)

__all__ = [
    # === Temporal Intent Scaling ===
    # Data structures
    "DeviationChannels",
    "TriadicTemporalState",
    "TrajectoryCoherence",
    "TemporalIntentState",
    "TemporalRiskAssessment",
    # Drift protection
    "DriftMonitor",
    "with_drift_protection",
    "reset_drift_monitor",
    "get_drift_status",
    "DRIFT_TOLERANCE",
    "MAX_ACCUMULATED_DRIFT",
    "PRECISION_DIGITS",
    # Core functions
    "compute_temporal_intent_factor",
    "update_temporal_state",
    "harmonic_scale_basic",
    "harmonic_scale_effective",
    "harmonic_scale_with_state",
    "security_bits_effective",
    "assess_risk_temporal",
    # Convenience
    "create_temporal_state",
    "quick_harmonic_effective",
    # Constants
    "PHI",
    "PERFECT_FIFTH",
    # === Temporal Pipeline Bridge ===
    # Main class
    "TemporalPipelineBridge",
    # Data classes
    "AgentDecisionRecord",
    "AgentProfile",
    # Registry functions
    "get_bridge",
    "clear_bridges",
    "list_agents",
    "get_all_summaries",
    # Global hive
    "set_global_hive",
    "get_global_hive",
    "HIVE_AVAILABLE",
    # Helper
    "process_with_temporal",
]

__version__ = "1.0.0"
