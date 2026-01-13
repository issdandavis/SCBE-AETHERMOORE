"""
Symphonic Cipher: Intent-Modulated Conlang + Harmonic Verification System

A mathematically rigorous authentication protocol that combines:
- Private conlang dictionary mapping
- Modality-driven harmonic synthesis
- Key-driven Feistel permutation
- Studio engineering DSP pipeline (gain, EQ, compression, reverb, panning)
- AI-based feature extraction and verification
- RWP v3 cryptographic envelope

All formulas follow the mathematical specification exactly.
"""

__version__ = "1.0.0"
__author__ = "Spiralverse RWP v3"

from .core import (
    SymphonicCipher,
    ConlangDictionary,
    ModalityEncoder,
    FeistelPermutation,
    HarmonicSynthesizer,
    RWPEnvelope,
)

from .dsp import (
    GainStage,
    MicPatternFilter,
    DAWRoutingMatrix,
    ParametricEQ,
    DynamicCompressor,
    ConvolutionReverb,
    StereoPanner,
    DSPChain,
)

from .ai_verifier import (
    FeatureExtractor,
    HarmonicVerifier,
    IntentClassifier,
)

from .harmonic_scaling_law import (
    HarmonicScalingLaw,
    ScalingMode,
    PQContextCommitment,
    BehavioralRiskComponents,
    SecurityDecisionEngine,
    hyperbolic_distance_poincare,
    find_nearest_trusted_realm,
    quantum_resistant_harmonic_scaling,
    create_context_commitment,
    verify_test_vectors,
)

__all__ = [
    # Core cipher components
    "SymphonicCipher",
    "ConlangDictionary",
    "ModalityEncoder",
    "FeistelPermutation",
    "HarmonicSynthesizer",
    "RWPEnvelope",
    # DSP chain
    "GainStage",
    "MicPatternFilter",
    "DAWRoutingMatrix",
    "ParametricEQ",
    "DynamicCompressor",
    "ConvolutionReverb",
    "StereoPanner",
    "DSPChain",
    # AI verification
    "FeatureExtractor",
    "HarmonicVerifier",
    "IntentClassifier",
    # Harmonic Scaling Law (SCBE-AETHERMOORE)
    "HarmonicScalingLaw",
    "ScalingMode",
    "PQContextCommitment",
    "BehavioralRiskComponents",
    "SecurityDecisionEngine",
    "hyperbolic_distance_poincare",
    "find_nearest_trusted_realm",
    "quantum_resistant_harmonic_scaling",
    "create_context_commitment",
    "verify_test_vectors",
]
