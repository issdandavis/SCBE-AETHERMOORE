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

__all__ = [
    "SymphonicCipher",
    "ConlangDictionary",
    "ModalityEncoder",
    "FeistelPermutation",
    "HarmonicSynthesizer",
    "RWPEnvelope",
    "GainStage",
    "MicPatternFilter",
    "DAWRoutingMatrix",
    "ParametricEQ",
    "DynamicCompressor",
    "ConvolutionReverb",
    "StereoPanner",
    "DSPChain",
    "FeatureExtractor",
    "HarmonicVerifier",
    "IntentClassifier",
]
