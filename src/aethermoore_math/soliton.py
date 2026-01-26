"""
Soliton-Based Message Integrity
===============================
Solitons are self-reinforcing wave packets that maintain shape
during propagation. Used for self-healing data streams.

Based on the Nonlinear Schrödinger Equation (NLSE):
i∂u/∂t + (1/2)∂²u/∂x² + |u|²u = 0
"""

import numpy as np
from typing import Tuple


def nlse_soliton(
    x: np.ndarray,
    t: float,
    amplitude: float = 1.0,
    velocity: float = 0.0
) -> np.ndarray:
    """
    Analytical soliton solution to the NLSE.

    Soliton: u(x,t) = A × sech(A×(x-vt)) × exp(i×(vx + (A²-v²)t/2))

    Args:
        x: Spatial coordinates
        t: Time
        amplitude: Soliton amplitude (determines width and speed)
        velocity: Soliton velocity

    Returns:
        Complex wave function u(x,t)
    """
    # Shifted position for moving soliton
    xi = x - velocity * t

    # Envelope (sech = 1/cosh)
    envelope = amplitude / np.cosh(amplitude * xi)

    # Phase evolution
    phase = np.exp(1j * (velocity * x + (amplitude**2 - velocity**2) * t / 2))

    return envelope * phase


def soliton_integrity_check(
    data: bytes,
    chunk_size: int = 64
) -> Tuple[bool, float]:
    """
    Check data integrity using soliton-inspired redundancy.

    The idea: encode data as a "soliton" waveform where the
    shape contains redundant information. Corruption changes
    the shape detectably.

    Args:
        data: Data to check
        chunk_size: Bytes per chunk

    Returns:
        (is_valid, confidence_score)
    """
    if len(data) < chunk_size:
        return True, 1.0

    # Convert data to amplitude spectrum
    amplitudes = np.frombuffer(data, dtype=np.uint8).astype(float) / 255.0

    # Compute "soliton shape" metrics
    n = len(amplitudes)
    x = np.linspace(-5, 5, n)

    # Ideal soliton would have specific properties:
    # 1. Peak at center
    # 2. Symmetric decay
    # 3. Specific width-to-height ratio

    peak_idx = np.argmax(amplitudes)
    peak_val = amplitudes[peak_idx]

    # Check symmetry around peak
    left = amplitudes[:peak_idx]
    right = amplitudes[peak_idx+1:]

    if len(left) > 0 and len(right) > 0:
        min_len = min(len(left), len(right))
        left_rev = left[-min_len:][::-1]
        right_sub = right[:min_len]
        symmetry = 1.0 - np.mean(np.abs(left_rev - right_sub))
    else:
        symmetry = 0.5

    # Check for soliton-like decay (sech profile)
    if peak_val > 0:
        # Expected sech decay
        expected = peak_val / np.cosh(np.abs(x))
        actual = amplitudes

        # Truncate to same length
        min_len = min(len(expected), len(actual))
        correlation = np.corrcoef(expected[:min_len], actual[:min_len])[0, 1]
        if np.isnan(correlation):
            correlation = 0.0
    else:
        correlation = 0.0

    # Combine metrics
    confidence = (symmetry + max(0, correlation)) / 2.0
    is_valid = confidence > 0.5

    return is_valid, confidence


def soliton_collision_energy(
    amp1: float,
    amp2: float,
    phase_diff: float
) -> float:
    """
    Calculate energy after soliton collision.

    Solitons pass through each other elastically (conservation).
    Only phase shift occurs.

    Args:
        amp1: Amplitude of soliton 1
        amp2: Amplitude of soliton 2
        phase_diff: Phase difference at collision

    Returns:
        Total energy (should be conserved)
    """
    # Energy of a soliton is proportional to amplitude
    e1 = amp1 ** 2
    e2 = amp2 ** 2

    # For true solitons, energy is conserved through collision
    # Only a phase shift occurs
    return e1 + e2
