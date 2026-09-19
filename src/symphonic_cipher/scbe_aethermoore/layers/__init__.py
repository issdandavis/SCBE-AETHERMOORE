"""
14-Layer SCBE Phase-Breath Hyperbolic Governance Pipeline

Layer Structure:
    Layer 1:  Complex Context State (c(t) ∈ ℂᴰ)
    Layer 2:  Realification (Φ₁: ℂᴰ → ℝ²ᴰ)
    Layer 3:  Weighted Transform (G^½ x) - Langues Metric Tensor
    Layer 4:  Poincaré Embedding (Ψ_α with tanh)
    Layer 5:  Hyperbolic Distance (d_H - THE INVARIANT)
    Layer 6:  Breathing Transform (T_breath)
    Layer 7:  Phase Transform (Möbius ⊕ + rotation)
    Layer 8:  Multi-Well Realms (d* = min_k d_H(ũ, μ_k))
    Layer 9:  Spectral Coherence (S_spec = 1 - r_HF)
    Layer 10: Spin Coherence (C_spin)
    Layer 11: Triadic Temporal Distance (d_tri)
    Layer 12: Bounded Safety (H = 1/(1+d+2*phase_deviation))
    Layer 13: Decision & Risk (Risk' with thresholds θ₁, θ₂)
    Layer 14: Audio Axis (S_audio)

Contracts:
    Phase isometries require valid domains; breathing intentionally deforms distance.
    Positive breathing has an explicit inverse and radial/tangential Jacobian.
    Bounded safety decreases with distance; decision thresholds are discrete.
    These are component contracts, not whole-system security guarantees.
"""

from .fourteen_layer_pipeline import (
    # Main pipeline class
    FourteenLayerPipeline,
    PipelineState,
    RiskAssessment,
    RiskLevel,
    # Individual layer functions
    layer_1_complex_context,
    layer_2_realify,
    layer_3_weighted,
    layer_4_poincare,
    layer_5_hyperbolic_distance,
    layer_6_breathing,
    layer_6_inverse,
    layer_6_breathing_jacobian,
    layer_7_phase,
    layer_8_multi_well,
    layer_9_spectral_coherence,
    layer_10_spin_coherence,
    layer_11_triadic_distance,
    layer_12_harmonic_scaling,
    layer_13_decision,
    layer_14_audio_axis,
    # Helper functions
    build_langues_metric,
    breathing_factor,
    mobius_addition,
    generate_realm_centers,
    # Theorem verification
    verify_theorem_A_metric_invariance,
    verify_theorem_B_continuity,
    verify_theorem_C_risk_monotonicity,
    verify_theorem_D_diffeomorphism,
    run_all_theorem_verification,
    # Constants
    PHI,
    R_BASE,
    ALPHA_EMBED,
    B_BREATH_MAX,
    OMEGA_BREATH,
    N_REALMS,
    THETA_1,
    THETA_2,
    EPS,
)

__all__ = [
    # Pipeline
    "FourteenLayerPipeline",
    "PipelineState",
    "RiskAssessment",
    "RiskLevel",
    # Layers
    "layer_1_complex_context",
    "layer_2_realify",
    "layer_3_weighted",
    "layer_4_poincare",
    "layer_5_hyperbolic_distance",
    "layer_6_breathing",
    "layer_6_inverse",
    "layer_6_breathing_jacobian",
    "layer_7_phase",
    "layer_8_multi_well",
    "layer_9_spectral_coherence",
    "layer_10_spin_coherence",
    "layer_11_triadic_distance",
    "layer_12_harmonic_scaling",
    "layer_13_decision",
    "layer_14_audio_axis",
    # Helpers
    "build_langues_metric",
    "breathing_factor",
    "mobius_addition",
    "generate_realm_centers",
    # Theorems
    "verify_theorem_A_metric_invariance",
    "verify_theorem_B_continuity",
    "verify_theorem_C_risk_monotonicity",
    "verify_theorem_D_diffeomorphism",
    "run_all_theorem_verification",
    # Constants
    "PHI",
    "R_BASE",
    "ALPHA_EMBED",
    "B_BREATH_MAX",
    "OMEGA_BREATH",
    "N_REALMS",
    "THETA_1",
    "THETA_2",
    "EPS",
]
