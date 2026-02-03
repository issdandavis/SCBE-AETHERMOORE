"""
Spiralverse Pipeline Integration

Wires Aethercode execution into the 14-layer pipeline:
- Lattice position → Layer 4 Poincaré embedding
- Chant output → Layer 14 audio axis
- RWP2 envelope → cryptographic audit

@module spiralverse/pipeline_integration
@layer Layer 4, Layer 14
@version 1.0.0
@since 2026-02-03
"""

import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass

# Import Aethercode
from .dsl.aethercode import (
    AethercodeInterpreter,
    LatticePosition,
    ChantComposition,
    RWP2Envelope,
    Langue,
    run_aethercode,
)


# ============================================================================
# Constants
# ============================================================================

PHI = 1.618033988749895  # Golden ratio
POINCARE_ALPHA = 0.99    # Embedding scale (stay within ball)

# Axis weights for 6D → Poincaré embedding (golden ratio sequence)
AXIS_WEIGHTS = {
    "ko": PHI ** 0,  # 1.000 - Intent (primary)
    "av": PHI ** 1,  # 1.618 - Flow
    "ru": PHI ** 2,  # 2.618 - Binding
    "ca": PHI ** 3,  # 4.236 - Computation
    "um": PHI ** 4,  # 6.854 - Veiling
    "dr": PHI ** 5,  # 11.09 - Structure
}


# ============================================================================
# Layer 4 Integration: Lattice → Poincaré
# ============================================================================

def lattice_to_6d_vector(lattice: LatticePosition) -> np.ndarray:
    """
    Convert LatticePosition to 6D numpy vector.

    Args:
        lattice: Aethercode LatticePosition

    Returns:
        6D numpy array [ko, av, ru, ca, um, dr]
    """
    return np.array([
        lattice.ko,
        lattice.av,
        lattice.ru,
        lattice.ca,
        lattice.um,
        lattice.dr,
    ], dtype=np.float64)


def apply_golden_weighting(vec: np.ndarray) -> np.ndarray:
    """
    Apply golden ratio weights to 6D vector.

    Higher-indexed axes (UM, DR) are weighted more heavily
    as they represent more secure/structural concerns.

    Args:
        vec: 6D vector

    Returns:
        Weighted 6D vector
    """
    weights = np.array([
        AXIS_WEIGHTS["ko"],
        AXIS_WEIGHTS["av"],
        AXIS_WEIGHTS["ru"],
        AXIS_WEIGHTS["ca"],
        AXIS_WEIGHTS["um"],
        AXIS_WEIGHTS["dr"],
    ])

    # Normalize weights
    weights = weights / np.sum(weights)

    return vec * weights


def embed_to_poincare_ball(
    vec: np.ndarray,
    alpha: float = POINCARE_ALPHA,
) -> np.ndarray:
    """
    Embed 6D vector into Poincaré ball.

    Uses tanh projection to map unbounded vector to unit ball:
        Ψ_α(x) = α · tanh(||x||) · x/||x||

    Args:
        vec: Input vector (any dimension)
        alpha: Scale factor (< 1 to stay in ball interior)

    Returns:
        Vector in Poincaré ball (||v|| < 1)
    """
    norm = np.linalg.norm(vec)
    if norm < 1e-10:
        return np.zeros_like(vec)

    return alpha * np.tanh(norm) * vec / norm


def lattice_to_poincare(
    lattice: LatticePosition,
    apply_weights: bool = True,
    alpha: float = POINCARE_ALPHA,
) -> np.ndarray:
    """
    Complete conversion: LatticePosition → Poincaré ball point.

    This is the main integration function for Layer 4.

    Args:
        lattice: Aethercode LatticePosition
        apply_weights: Whether to apply golden ratio weighting
        alpha: Poincaré embedding scale

    Returns:
        6D point in Poincaré ball
    """
    vec = lattice_to_6d_vector(lattice)

    if apply_weights:
        vec = apply_golden_weighting(vec)

    return embed_to_poincare_ball(vec, alpha)


# ============================================================================
# Layer 14 Integration: Chant → Audio
# ============================================================================

def chant_to_fft_coefficients(
    chant: ChantComposition,
    n_bins: int = 256,
    sample_rate: float = 44100.0,
) -> np.ndarray:
    """
    Convert Aethercode chant to FFT coefficients for Layer 14.

    Each note in the chant contributes to the frequency spectrum.

    Args:
        chant: ChantComposition from Aethercode execution
        n_bins: Number of FFT bins
        sample_rate: Sample rate for frequency mapping

    Returns:
        Complex FFT coefficients
    """
    fft_coeffs = np.zeros(n_bins, dtype=complex)

    for note in chant.notes:
        # Map frequency to bin
        freq_bin = int(note.frequency * n_bins / (sample_rate / 2))
        if 0 <= freq_bin < n_bins:
            # Add contribution (amplitude and phase)
            fft_coeffs[freq_bin] += note.amplitude * np.exp(1j * note.phase)

    return fft_coeffs


def chant_to_audio_signal(
    chant: ChantComposition,
    duration: float = 1.0,
    sample_rate: int = 44100,
) -> np.ndarray:
    """
    Synthesize audio signal from Aethercode chant.

    Uses additive synthesis with each note contributing a sine wave.

    Args:
        chant: ChantComposition from Aethercode execution
        duration: Signal duration in seconds
        sample_rate: Sample rate in Hz

    Returns:
        Audio signal as numpy array
    """
    n_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, n_samples)
    signal = np.zeros(n_samples)

    for note in chant.notes:
        # Generate sine wave for this note
        wave = note.amplitude * np.sin(2 * np.pi * note.frequency * t + note.phase)

        # Apply simple envelope (attack-decay)
        envelope = np.minimum(t / 0.01, 1.0) * np.exp(-t / note.duration)

        signal += wave * envelope

    # Normalize
    max_amp = np.max(np.abs(signal))
    if max_amp > 0:
        signal = signal / max_amp

    return signal


def compute_audio_stability(chant) -> float:
    """
    Compute audio stability score from chant (Layer 14 S_audio).

    Accepts either ChantComposition object or string description.

    Stability is based on:
    - Harmonic consonance (how well notes align with golden ratio)
    - Amplitude balance (not too loud/quiet)
    - Temporal coherence

    Returns:
        Stability score ∈ [0, 1]
    """
    # Handle string description (from run_aethercode)
    if isinstance(chant, str):
        # Parse duration from string like "Polyphonic Chant (~0.6s)"
        if "~" in chant and "s)" in chant:
            try:
                duration_str = chant.split("~")[1].split("s)")[0]
                duration = float(duration_str)
                # Stability based on duration: longer = more complex = slightly less stable
                stability = 1.0 / (1.0 + duration / 10.0)
                return float(np.clip(stability, 0.5, 1.0))
            except (IndexError, ValueError):
                pass
        # Default for string input
        return 0.9 if chant else 1.0

    # Handle ChantComposition object
    if not hasattr(chant, 'notes') or not chant.notes:
        return 1.0  # Empty chant is stable

    # 1. Harmonic consonance
    frequencies = [n.frequency for n in chant.notes]
    if len(frequencies) >= 2:
        ratios = []
        for i in range(len(frequencies) - 1):
            if frequencies[i] > 0:
                ratio = frequencies[i + 1] / frequencies[i]
                # Check if close to golden ratio or simple ratios
                golden_dist = abs(ratio - PHI) / PHI
                ratios.append(1.0 / (1.0 + golden_dist))
        consonance = np.mean(ratios) if ratios else 1.0
    else:
        consonance = 1.0

    # 2. Amplitude balance
    amplitudes = [n.amplitude for n in chant.notes]
    amp_mean = np.mean(amplitudes)
    amp_std = np.std(amplitudes)
    balance = 1.0 / (1.0 + amp_std / (amp_mean + 0.01))

    # 3. Temporal coherence (uniform duration)
    durations = [n.duration for n in chant.notes]
    dur_std = np.std(durations)
    dur_mean = np.mean(durations)
    coherence = 1.0 / (1.0 + dur_std / (dur_mean + 0.01))

    # Combine with golden ratio weights
    stability = (
        consonance * 0.5 +  # Most important
        balance * 0.3 +
        coherence * 0.2
    )

    return float(np.clip(stability, 0.0, 1.0))


# ============================================================================
# Complete Pipeline Integration
# ============================================================================

@dataclass
class AethercodeIntegrationResult:
    """Result of integrating Aethercode with the pipeline."""
    # Layer 4 outputs
    poincare_point: np.ndarray
    poincare_norm: float

    # Layer 14 outputs
    audio_stability: float
    fft_coefficients: Optional[np.ndarray]

    # Metadata
    langues_used: List[str]
    deviation_cost: float
    envelope_valid: bool


def integrate_aethercode_with_pipeline(
    source: str,
    compute_audio: bool = True,
    fft_bins: int = 256,
) -> AethercodeIntegrationResult:
    """
    Execute Aethercode and prepare outputs for pipeline integration.

    This is the main entry point for using Aethercode with the 14-layer pipeline.

    Args:
        source: Aethercode source code
        compute_audio: Whether to compute audio features
        fft_bins: Number of FFT bins for audio

    Returns:
        AethercodeIntegrationResult with Layer 4 and Layer 14 data
    """
    # Execute Aethercode
    result = run_aethercode(source)

    # Get lattice position
    lattice = result.get("lattice", LatticePosition())

    # Layer 4: Convert to Poincaré point
    poincare_point = lattice_to_poincare(lattice)
    poincare_norm = float(np.linalg.norm(poincare_point))

    # Layer 14: Audio features
    chant = result.get("chant", "")
    audio_stability = compute_audio_stability(chant)

    # FFT coefficients only available if we have a ChantComposition object
    fft_coeffs = None
    if compute_audio and hasattr(chant, 'notes') and chant.notes:
        fft_coeffs = chant_to_fft_coefficients(chant, fft_bins)

    # Metadata
    langues_used = result.get("langues_used", [])
    deviation_cost = result.get("deviation_cost", 0.0)
    envelope = result.get("envelope")
    envelope_valid = envelope is not None and envelope.tier > 0 if envelope else False

    return AethercodeIntegrationResult(
        poincare_point=poincare_point,
        poincare_norm=poincare_norm,
        audio_stability=audio_stability,
        fft_coefficients=fft_coeffs,
        langues_used=langues_used,
        deviation_cost=deviation_cost,
        envelope_valid=envelope_valid,
    )


def prepare_layer4_input(
    aethercode_source: Optional[str] = None,
    fallback_vector: Optional[np.ndarray] = None,
) -> np.ndarray:
    """
    Prepare Layer 4 input from Aethercode or fallback.

    Use this in the pipeline to get a Poincaré point from Aethercode,
    or fall back to a provided vector if no Aethercode is given.

    Args:
        aethercode_source: Optional Aethercode program
        fallback_vector: Fallback vector if no Aethercode

    Returns:
        6D point in Poincaré ball
    """
    if aethercode_source:
        result = integrate_aethercode_with_pipeline(aethercode_source, compute_audio=False)
        return result.poincare_point

    if fallback_vector is not None:
        return embed_to_poincare_ball(fallback_vector)

    # Default: origin (safe center)
    return np.zeros(6)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Layer 4 functions
    "lattice_to_6d_vector",
    "apply_golden_weighting",
    "embed_to_poincare_ball",
    "lattice_to_poincare",
    # Layer 14 functions
    "chant_to_fft_coefficients",
    "chant_to_audio_signal",
    "compute_audio_stability",
    # Integration
    "AethercodeIntegrationResult",
    "integrate_aethercode_with_pipeline",
    "prepare_layer4_input",
    # Constants
    "PHI",
    "POINCARE_ALPHA",
    "AXIS_WEIGHTS",
]
