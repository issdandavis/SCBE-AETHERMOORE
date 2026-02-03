#!/usr/bin/env python3
"""
Polyglot Alphabet → Layers 1-2 Integration
===========================================

Wires Polyglot Alphabet encoding to Layers 1-2 for semantic encoding:
- Text → Polyglot encoding → amplitude/phase pairs
- Layer 1: Complex state construction
- Layer 2: Realification

This enables semantic meaning to flow through the 14-layer pipeline,
allowing governance decisions to be based on message content.

Integration Points:
- Polyglot encode → amplitude (magnitude)
- Tongue signatures → phase (angle)
- 6 tongues → 6D semantic space

Date: February 2026
"""

from __future__ import annotations

import hashlib
import math
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any, Set
from enum import Enum

# Polyglot imports
try:
    from ...spiralverse.polyglot_alphabet import (
        TongueID, TongueAlphabet, TONGUE_ALPHABETS,
        SIGNATURE_TO_TONGUE, compose_polyglot_message,
        decompose_polyglot_message, identify_tongue
    )
    POLYGLOT_AVAILABLE = True
except ImportError:
    POLYGLOT_AVAILABLE = False

    class TongueID(Enum):
        AXIOM = "AXIOM"
        FLOW = "FLOW"
        GLYPH = "GLYPH"
        ORACLE = "ORACLE"
        CHARM = "CHARM"
        LEDGER = "LEDGER"


# =============================================================================
# CONSTANTS
# =============================================================================

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio ≈ 1.618

# Phase angles for each tongue (evenly distributed around circle)
TONGUE_PHASES = {
    TongueID.AXIOM: 0.0,          # 0°
    TongueID.FLOW: math.pi / 3,   # 60°
    TongueID.GLYPH: 2 * math.pi / 3,  # 120°
    TongueID.ORACLE: math.pi,     # 180°
    TongueID.CHARM: 4 * math.pi / 3,  # 240°
    TongueID.LEDGER: 5 * math.pi / 3,  # 300°
}

# Tongue signatures for validation
TONGUE_SIGNATURES = {
    TongueID.AXIOM: "a3f7c2e1",
    TongueID.FLOW: "b8e4d9c3",
    TongueID.GLYPH: "c1d5a7f2",
    TongueID.ORACLE: "d9a2b6e8",
    TongueID.CHARM: "e4f1c8d7",
    TongueID.LEDGER: "f7b3e5a9",
}


# =============================================================================
# SEMANTIC ENCODING
# =============================================================================

@dataclass
class SemanticVector:
    """
    Semantic encoding of text using the Six Tongues.

    Each tongue contributes an amplitude (encoding strength) and
    phase (semantic angle), creating a 6D complex semantic space.
    """
    # Per-tongue amplitudes (encoding strength)
    amplitudes: Dict[TongueID, float]

    # Per-tongue phases (semantic angle)
    phases: Dict[TongueID, float]

    # Source text
    source_text: str

    # Dominant tongues (those with highest amplitude)
    dominant_tongues: List[TongueID]

    @property
    def amplitude_vector(self) -> np.ndarray:
        """Get 6D amplitude vector."""
        tongues = list(TongueID)
        return np.array([self.amplitudes.get(t, 0.0) for t in tongues])

    @property
    def phase_vector(self) -> np.ndarray:
        """Get 6D phase vector."""
        tongues = list(TongueID)
        return np.array([self.phases.get(t, 0.0) for t in tongues])

    @property
    def complex_vector(self) -> np.ndarray:
        """Get complex representation: amplitude * exp(i * phase)."""
        return self.amplitude_vector * np.exp(1j * self.phase_vector)

    @property
    def total_amplitude(self) -> float:
        """Total semantic strength."""
        return float(np.sum(self.amplitude_vector))


def analyze_text_by_tongue(text: str) -> Dict[TongueID, float]:
    """
    Analyze text and compute amplitude (encoding strength) for each tongue.

    This maps characters to their tongue alphabets and computes
    how much each tongue contributes to the semantic meaning.

    Args:
        text: Input text to analyze

    Returns:
        Dict mapping TongueID to amplitude (0-1 normalized)
    """
    if not POLYGLOT_AVAILABLE:
        # Fallback: uniform distribution
        return {t: 1.0 / 6 for t in TongueID}

    tongue_counts = {t: 0 for t in TongueID}
    total_chars = 0

    for char in text:
        if char.isspace():
            continue
        total_chars += 1

        # Check which tongue(s) contain this character
        for tongue_id, alphabet in TONGUE_ALPHABETS.items():
            if alphabet.contains(char.upper()) or alphabet.contains(char):
                tongue_counts[tongue_id] += 1

    # Normalize to [0, 1]
    if total_chars == 0:
        return {t: 0.0 for t in TongueID}

    return {t: count / total_chars for t, count in tongue_counts.items()}


def compute_semantic_phases(
    text: str,
    base_phases: Optional[Dict[TongueID, float]] = None
) -> Dict[TongueID, float]:
    """
    Compute semantic phase angles for text.

    Phase is influenced by:
    - Base tongue phase (evenly distributed)
    - Hash of text content (adds variation)
    - Signature of dominant tongue (for verification)

    Args:
        text: Input text
        base_phases: Base phase angles (default: TONGUE_PHASES)

    Returns:
        Dict mapping TongueID to phase angle
    """
    if base_phases is None:
        base_phases = TONGUE_PHASES

    # Compute text hash for phase modulation (deterministic)
    text_bytes = text.encode('utf-8')
    # Use 16 hex chars (64 bits) for better distribution and lower collision probability
    text_hash = int(hashlib.sha256(text_bytes).hexdigest()[:16], 16)
    hash_factor = (text_hash / (2 ** 64)) * math.pi / 6  # ±30° variation

    phases = {}
    for tongue in TongueID:
        base = base_phases.get(tongue, 0.0)
        # Add hash-based variation for uniqueness
        variation = hash_factor * (1 + list(TongueID).index(tongue) * 0.1)
        phases[tongue] = (base + variation) % (2 * math.pi)

    return phases


def encode_text_semantic(text: str) -> SemanticVector:
    """
    Encode text into a semantic vector using all Six Tongues.

    Args:
        text: Input text to encode

    Returns:
        SemanticVector with amplitudes and phases
    """
    # Compute amplitudes (encoding strength per tongue)
    amplitudes = analyze_text_by_tongue(text)

    # Compute phases (semantic angles)
    phases = compute_semantic_phases(text)

    # Identify dominant tongues (top 3 by amplitude)
    sorted_tongues = sorted(
        amplitudes.items(),
        key=lambda x: x[1],
        reverse=True
    )
    dominant = [t for t, _ in sorted_tongues[:3] if amplitudes[t] > 0]

    return SemanticVector(
        amplitudes=amplitudes,
        phases=phases,
        source_text=text,
        dominant_tongues=dominant,
    )


# =============================================================================
# LAYER 1: COMPLEX STATE CONSTRUCTION
# =============================================================================

def layer1_complex_state_from_semantic(
    semantic: SemanticVector,
    D: int = 6
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Layer 1: Construct complex state from semantic encoding.

    Input: SemanticVector with amplitudes and phases
    Output: c ∈ ℂ^D

    A1: c = amplitudes × exp(i × phases)

    Args:
        semantic: Semantic vector from text encoding
        D: Dimension (default 6 for Six Tongues)

    Returns:
        Tuple of (real part, imaginary part)
    """
    amplitudes = semantic.amplitude_vector[:D]
    phases = semantic.phase_vector[:D]

    # Pad if needed
    if len(amplitudes) < D:
        amplitudes = np.pad(amplitudes, (0, D - len(amplitudes)))
        phases = np.pad(phases, (0, D - len(phases)))

    # c = amplitude * exp(i * phase) = amplitude * (cos(phase) + i*sin(phase))
    real = amplitudes * np.cos(phases)
    imag = amplitudes * np.sin(phases)

    return real, imag


def layer1_complex_state_from_text(
    text: str,
    D: int = 6
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Layer 1: Construct complex state directly from text.

    Convenience function that combines encoding and Layer 1.

    Args:
        text: Input text
        D: Dimension

    Returns:
        Tuple of (real part, imaginary part)
    """
    semantic = encode_text_semantic(text)
    return layer1_complex_state_from_semantic(semantic, D)


# =============================================================================
# LAYER 2: REALIFICATION
# =============================================================================

def layer2_realification(complex_state: Tuple[np.ndarray, np.ndarray]) -> np.ndarray:
    """
    Layer 2: Realification (Complex → Real).

    Input: c ∈ ℂ^D
    Output: x ∈ ℝ^{2D}

    A2: x = [Re(c), Im(c)]

    Args:
        complex_state: Tuple of (real part, imaginary part)

    Returns:
        Real vector x ∈ ℝ^{2D}
    """
    real, imag = complex_state
    return np.concatenate([real, imag])


# =============================================================================
# COMPLETE PIPELINE
# =============================================================================

@dataclass
class SemanticPipelineResult:
    """
    Result of processing text through Layers 1-2.
    """
    # Input
    source_text: str
    semantic: SemanticVector

    # Layer 1 output
    complex_real: np.ndarray
    complex_imag: np.ndarray

    # Layer 2 output
    realified: np.ndarray

    # Metrics
    semantic_strength: float  # Total amplitude
    dominant_tongues: List[TongueID]
    complexity: float  # Phase variance (semantic complexity)


class PolyglotLayer12Pipeline:
    """
    Complete pipeline: Polyglot Encoding → Layer 1 → Layer 2.

    This enables text/messages to be processed through the 14-layer
    governance pipeline with semantic meaning preserved.

    Usage:
        pipeline = PolyglotLayer12Pipeline()
        result = pipeline.process("Hello World")
        realified = result.realified  # Ready for Layer 3
    """

    def __init__(self, dimension: int = 6):
        """
        Initialize the pipeline.

        Args:
            dimension: Dimension D (default 6 for Six Tongues)
        """
        self.dimension = dimension
        self.history: List[SemanticPipelineResult] = []

    def process(self, text: str) -> SemanticPipelineResult:
        """
        Process text through Layers 1-2.

        Args:
            text: Input text

        Returns:
            SemanticPipelineResult ready for Layer 3
        """
        # Encode semantically
        semantic = encode_text_semantic(text)

        # Layer 1: Complex state
        real, imag = layer1_complex_state_from_semantic(semantic, self.dimension)

        # Layer 2: Realification
        realified = layer2_realification((real, imag))

        # Compute complexity (phase variance)
        phase_variance = float(np.var(semantic.phase_vector))

        result = SemanticPipelineResult(
            source_text=text,
            semantic=semantic,
            complex_real=real,
            complex_imag=imag,
            realified=realified,
            semantic_strength=semantic.total_amplitude,
            dominant_tongues=semantic.dominant_tongues,
            complexity=phase_variance,
        )

        self.history.append(result)
        return result

    def process_batch(self, texts: List[str]) -> List[SemanticPipelineResult]:
        """
        Process multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of SemanticPipelineResults
        """
        return [self.process(text) for text in texts]

    def compare_semantic_similarity(
        self,
        text1: str,
        text2: str
    ) -> float:
        """
        Compare semantic similarity of two texts.

        Uses cosine similarity of realified vectors.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score [0, 1]
        """
        r1 = self.process(text1)
        r2 = self.process(text2)

        # Cosine similarity
        dot = np.dot(r1.realified, r2.realified)
        norm1 = np.linalg.norm(r1.realified)
        norm2 = np.linalg.norm(r2.realified)

        if norm1 < 1e-10 or norm2 < 1e-10:
            return 0.0

        return float(dot / (norm1 * norm2))


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def encode_text_for_pipeline(text: str) -> np.ndarray:
    """
    Simple function to encode text ready for Layer 3.

    Args:
        text: Input text

    Returns:
        Realified vector (ℝ^{12} for 6D semantic space)
    """
    pipeline = PolyglotLayer12Pipeline()
    result = pipeline.process(text)
    return result.realified


def compute_semantic_distance(text1: str, text2: str) -> float:
    """
    Compute semantic distance between two texts.

    Uses L2 distance in realified space.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Euclidean distance
    """
    r1 = encode_text_for_pipeline(text1)
    r2 = encode_text_for_pipeline(text2)
    return float(np.linalg.norm(r1 - r2))


def identify_message_intent(text: str) -> Dict[str, Any]:
    """
    Identify the semantic intent of a message.

    Returns analysis of which tongues dominate and what
    that implies about the message's purpose.

    Args:
        text: Input text

    Returns:
        Intent analysis dict
    """
    semantic = encode_text_semantic(text)

    # Map dominant tongues to intent
    intent_map = {
        TongueID.AXIOM: "command/directive",
        TongueID.FLOW: "transition/process",
        TongueID.GLYPH: "structure/data",
        TongueID.ORACLE: "temporal/async",
        TongueID.CHARM: "harmony/priority",
        TongueID.LEDGER: "authentication/record",
    }

    intents = [intent_map.get(t, "unknown") for t in semantic.dominant_tongues]

    return {
        'dominant_tongues': [t.value for t in semantic.dominant_tongues],
        'intents': intents,
        'primary_intent': intents[0] if intents else "neutral",
        'semantic_strength': semantic.total_amplitude,
        'amplitudes': {t.value: a for t, a in semantic.amplitudes.items()},
        'complexity': float(np.var(semantic.phase_vector)),
    }


# =============================================================================
# INTEGRATION WITH LAYER 3
# =============================================================================

def prepare_for_layer3(
    text: str,
    include_weights: bool = True
) -> Dict[str, Any]:
    """
    Prepare semantic encoding for Layer 3 weighted transform.

    Args:
        text: Input text
        include_weights: Include golden ratio weights

    Returns:
        Dict with realified vector and optional weights
    """
    pipeline = PolyglotLayer12Pipeline()
    result = pipeline.process(text)

    output = {
        'realified': result.realified,
        'dimension': len(result.realified),
        'semantic': result.semantic.amplitudes,
        'dominant_tongues': [t.value for t in result.dominant_tongues],
    }

    if include_weights:
        # Golden ratio weights for 6 tongues
        D = pipeline.dimension
        weights = np.array([PHI ** k for k in range(D)])
        weights = weights / np.sum(weights)
        output['weights'] = weights

    return output
