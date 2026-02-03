"""
Polyglot Pipeline Integration

Wires the Polyglot alphabet system into Layers 1-2 of the 14-layer pipeline:
- Layer 1: Complex context → domain-encoded representation
- Layer 2: Realification with alphabet awareness

@module tokenizer/pipeline_integration
@layer Layer 1, Layer 2
@version 1.0.0
@since 2026-02-03
"""

import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass

from .polyglot import (
    AlphabetType,
    SacredTonguePolyglot,
    TONGUE_TO_ALPHABET,
    AXIS_TO_ALPHABET,
    ALPHABETS,
    encode_with_alphabet,
    decode_with_alphabet,
    PHI,
)


# ============================================================================
# Constants
# ============================================================================

# Domain weights for encoding (golden ratio sequence)
DOMAIN_WEIGHTS = {
    AlphabetType.AXIOM: PHI ** 0,   # 1.000 - Logic (primary)
    AlphabetType.FLOW: PHI ** 1,    # 1.618 - Data flow
    AlphabetType.GLYPH: PHI ** 2,   # 2.618 - Visual
    AlphabetType.ORACLE: PHI ** 3,  # 4.236 - Query/uncertainty
    AlphabetType.CHARM: PHI ** 4,   # 6.854 - Social/trust
    AlphabetType.LEDGER: PHI ** 5,  # 11.09 - Audit (highest)
}


# ============================================================================
# Context Encoding (Layer 1)
# ============================================================================

@dataclass
class EncodedContext:
    """Encoded context with domain-specific representations."""
    identity_encoded: str       # AXIOM alphabet
    intent_encoded: str         # FLOW alphabet
    trajectory_encoded: str     # GLYPH alphabet
    timing_encoded: str         # ORACLE alphabet
    commitment_encoded: str     # CHARM alphabet
    signature_encoded: str      # LEDGER alphabet

    # Metadata
    total_symbols: int = 0
    domain_weights: Dict[str, float] = None
    complexity_score: float = 0.0


def encode_context_value(
    value: Any,
    alphabet: AlphabetType,
) -> str:
    """
    Encode a single context value using the specified alphabet.

    Args:
        value: Value to encode (converted to bytes)
        alphabet: Target alphabet

    Returns:
        Encoded string using alphabet symbols
    """
    # Convert value to bytes
    if isinstance(value, bytes):
        data = value
    elif isinstance(value, str):
        data = value.encode('utf-8')
    elif isinstance(value, (int, float)):
        # Pack as 8-byte float
        data = np.array([float(value)]).tobytes()
    elif isinstance(value, complex):
        # Pack as two 8-byte floats (real, imag)
        data = np.array([value.real, value.imag]).tobytes()
    else:
        data = str(value).encode('utf-8')

    return encode_with_alphabet(data, alphabet)


def encode_layer1_context(
    identity: float,
    intent: complex,
    trajectory: float,
    timing: float,
    commitment: float,
    signature: float,
) -> EncodedContext:
    """
    Encode Layer 1 context using domain-specific polyglot alphabets.

    Each context component maps to a Sacred Tongue → Alphabet:
    - identity   → KO → AXIOM  (formal identity proof)
    - intent     → AV → FLOW   (intent data flow)
    - trajectory → RU → GLYPH  (visual trajectory state)
    - timing     → CA → ORACLE (temporal uncertainty)
    - commitment → UM → CHARM  (social commitment)
    - signature  → DR → LEDGER (audit trail)

    Args:
        identity: Identity metric
        intent: Complex intent vector
        trajectory: Trajectory coherence
        timing: Temporal timestamp
        commitment: Cryptographic commitment
        signature: Signature validity

    Returns:
        EncodedContext with all encoded values
    """
    # Encode each component with its domain alphabet
    identity_enc = encode_context_value(identity, AlphabetType.AXIOM)
    intent_enc = encode_context_value(intent, AlphabetType.FLOW)
    trajectory_enc = encode_context_value(trajectory, AlphabetType.GLYPH)
    timing_enc = encode_context_value(timing, AlphabetType.ORACLE)
    commitment_enc = encode_context_value(commitment, AlphabetType.CHARM)
    signature_enc = encode_context_value(signature, AlphabetType.LEDGER)

    # Calculate total symbols
    total_symbols = sum(len(s) for s in [
        identity_enc, intent_enc, trajectory_enc,
        timing_enc, commitment_enc, signature_enc
    ])

    # Calculate domain weights
    domain_weights = {
        "axiom": len(identity_enc) * DOMAIN_WEIGHTS[AlphabetType.AXIOM],
        "flow": len(intent_enc) * DOMAIN_WEIGHTS[AlphabetType.FLOW],
        "glyph": len(trajectory_enc) * DOMAIN_WEIGHTS[AlphabetType.GLYPH],
        "oracle": len(timing_enc) * DOMAIN_WEIGHTS[AlphabetType.ORACLE],
        "charm": len(commitment_enc) * DOMAIN_WEIGHTS[AlphabetType.CHARM],
        "ledger": len(signature_enc) * DOMAIN_WEIGHTS[AlphabetType.LEDGER],
    }

    # Complexity score: weighted sum of domain contributions
    total_weight = sum(domain_weights.values())
    complexity = total_weight / (total_symbols + 1)  # Normalize

    return EncodedContext(
        identity_encoded=identity_enc,
        intent_encoded=intent_enc,
        trajectory_encoded=trajectory_enc,
        timing_encoded=timing_enc,
        commitment_encoded=commitment_enc,
        signature_encoded=signature_enc,
        total_symbols=total_symbols,
        domain_weights=domain_weights,
        complexity_score=complexity,
    )


# ============================================================================
# Realification (Layer 2)
# ============================================================================

def encoded_to_complex_vector(encoded: EncodedContext) -> np.ndarray:
    """
    Convert encoded context to complex vector for Layer 2 realification.

    Each encoded string is converted to a complex number by:
    - Real part: hash of the encoded string (normalized)
    - Imag part: alphabet-weighted length

    Returns:
        Complex 6D vector
    """
    def str_to_complex(s: str, weight: float) -> complex:
        # Real: normalized hash
        hash_val = int(hashlib.sha256(s.encode()).hexdigest()[:8], 16)
        real = (hash_val / (2**32)) - 0.5  # Center around 0

        # Imag: weighted length (normalized)
        imag = len(s) * weight / 100.0

        return complex(real, imag)

    import hashlib

    return np.array([
        str_to_complex(encoded.identity_encoded, DOMAIN_WEIGHTS[AlphabetType.AXIOM]),
        str_to_complex(encoded.intent_encoded, DOMAIN_WEIGHTS[AlphabetType.FLOW]),
        str_to_complex(encoded.trajectory_encoded, DOMAIN_WEIGHTS[AlphabetType.GLYPH]),
        str_to_complex(encoded.timing_encoded, DOMAIN_WEIGHTS[AlphabetType.ORACLE]),
        str_to_complex(encoded.commitment_encoded, DOMAIN_WEIGHTS[AlphabetType.CHARM]),
        str_to_complex(encoded.signature_encoded, DOMAIN_WEIGHTS[AlphabetType.LEDGER]),
    ], dtype=complex)


def realify_encoded_context(encoded: EncodedContext) -> np.ndarray:
    """
    Realify encoded context for pipeline Layer 2.

    Converts 6D complex vector to 12D real vector:
        Φ₁(c) = [Re(c₁), Im(c₁), ..., Re(c₆), Im(c₆)]

    Returns:
        12D real vector
    """
    complex_vec = encoded_to_complex_vector(encoded)

    # Realify: interleave real and imaginary parts
    real_vec = []
    for z in complex_vec:
        real_vec.append(np.real(z))
        real_vec.append(np.imag(z))

    return np.array(real_vec, dtype=np.float64)


# ============================================================================
# Complete Pipeline Integration
# ============================================================================

@dataclass
class PolyglotPipelineInput:
    """Input prepared for the 14-layer pipeline using polyglot encoding."""
    # Raw inputs
    identity: float
    intent: complex
    trajectory: float
    timing: float
    commitment: float
    signature: float

    # Encoded context (Layer 1)
    encoded: EncodedContext = None

    # Realified vector (Layer 2)
    realified: np.ndarray = None

    # Metadata
    encoding_complete: bool = False


def prepare_pipeline_input(
    identity: float,
    intent: complex,
    trajectory: float,
    timing: float,
    commitment: float,
    signature: float,
) -> PolyglotPipelineInput:
    """
    Prepare input for the 14-layer pipeline using polyglot encoding.

    This is the main entry point for using polyglot alphabets with the pipeline.

    Args:
        identity: Identity metric
        intent: Complex intent vector
        trajectory: Trajectory coherence
        timing: Temporal timestamp
        commitment: Cryptographic commitment
        signature: Signature validity

    Returns:
        PolyglotPipelineInput ready for pipeline processing
    """
    # Layer 1: Encode context
    encoded = encode_layer1_context(
        identity=identity,
        intent=intent,
        trajectory=trajectory,
        timing=timing,
        commitment=commitment,
        signature=signature,
    )

    # Layer 2: Realify
    realified = realify_encoded_context(encoded)

    return PolyglotPipelineInput(
        identity=identity,
        intent=intent,
        trajectory=trajectory,
        timing=timing,
        commitment=commitment,
        signature=signature,
        encoded=encoded,
        realified=realified,
        encoding_complete=True,
    )


def get_domain_distribution(encoded: EncodedContext) -> Dict[str, float]:
    """
    Get the distribution of encoding across domains.

    Returns normalized weights showing which domains
    dominate the encoded context.
    """
    if encoded.domain_weights is None:
        return {}

    total = sum(encoded.domain_weights.values())
    if total == 0:
        return {k: 0.0 for k in encoded.domain_weights}

    return {k: v / total for k, v in encoded.domain_weights.items()}


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Data classes
    "EncodedContext",
    "PolyglotPipelineInput",
    # Layer 1 functions
    "encode_context_value",
    "encode_layer1_context",
    # Layer 2 functions
    "encoded_to_complex_vector",
    "realify_encoded_context",
    # Integration
    "prepare_pipeline_input",
    "get_domain_distribution",
    # Constants
    "DOMAIN_WEIGHTS",
]
