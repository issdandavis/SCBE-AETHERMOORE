"""
Symphonic Cipher - Audio Frequency Mapping with Extended Vocabulary
===================================================================

Core provision 1: Negative token IDs map to frequencies below the 440 Hz base.
Positive IDs map above. Zero is exactly A4 (440 Hz).

Design:
- Base frequency: 440.0 Hz
- Step: 30 Hz per ID unit (matches documented example: ID -1 -> 410 Hz)
- Extended vocabulary tokens (e.g., "shadow") explicitly use negative IDs

Integration with Dual Lattice:
- Shadow tokens (negative) create counter-phase patterns in cross-stitch
- Light/shadow duality maps to Sacred Tongue KO/UM opposition
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class TonguePolarity(str, Enum):
    """Polarity of a token - light (positive) or shadow (negative)."""
    LIGHT = "light"      # Positive ID, above base frequency
    NEUTRAL = "neutral"  # Zero ID, exactly base frequency
    SHADOW = "shadow"    # Negative ID, below base frequency


# Known sacred tongue mappings (positive IDs = light/realms, negative = shadow/opposing)
SACRED_TONGUE_VOCAB: Dict[str, int] = {
    # Light vocabulary (positive IDs)
    "light": 1,
    "fire": 2,
    "truth": 3,
    "wisdom": 4,
    "harmony": 5,
    "creation": 6,
    "guardian": 7,
    "sacred": 8,
    "divine": 9,
    "eternal": 10,
    # Neutral (zero)
    "balance": 0,
    "center": 0,
    "origin": 0,
    # Shadow vocabulary (negative IDs)
    "shadow": -1,
    "void": -2,
    "echo": -3,
    "whisper": -4,
    "mist": -5,
    "abyss": -6,
    "phantom": -7,
    "veil": -8,
    "drift": -9,
    "forgotten": -10,
}

# Symphonic parameters
BASE_FREQ = 440.0       # A4 = 440 Hz
FREQ_STEP = 30.0        # 30 Hz per ID unit
SAMPLE_RATE = 44100     # CD quality


@dataclass
class SymphonicToken:
    """A token mapped to its symphonic frequency."""
    token: str
    token_id: int
    frequency: float
    polarity: TonguePolarity

    @classmethod
    def from_token(cls, token: str) -> 'SymphonicToken':
        """Create from vocabulary token."""
        token_lower = token.lower()
        if token_lower not in SACRED_TONGUE_VOCAB:
            raise ValueError(f"Unknown token: {token}")

        token_id = SACRED_TONGUE_VOCAB[token_lower]
        frequency = BASE_FREQ + FREQ_STEP * token_id

        if token_id > 0:
            polarity = TonguePolarity.LIGHT
        elif token_id < 0:
            polarity = TonguePolarity.SHADOW
        else:
            polarity = TonguePolarity.NEUTRAL

        return cls(
            token=token_lower,
            token_id=token_id,
            frequency=frequency,
            polarity=polarity
        )

    @classmethod
    def from_id(cls, token_id: int, name: str = None) -> 'SymphonicToken':
        """Create from arbitrary signed ID."""
        frequency = BASE_FREQ + FREQ_STEP * token_id

        if token_id > 0:
            polarity = TonguePolarity.LIGHT
        elif token_id < 0:
            polarity = TonguePolarity.SHADOW
        else:
            polarity = TonguePolarity.NEUTRAL

        return cls(
            token=name or f"id_{token_id}",
            token_id=token_id,
            frequency=frequency,
            polarity=polarity
        )


def token_to_frequency(token: str) -> float:
    """Map a sacred tongue token to its symphonic frequency."""
    token_id = SACRED_TONGUE_VOCAB.get(token.lower())
    if token_id is None:
        raise ValueError(f"Unknown token: {token}")
    return BASE_FREQ + FREQ_STEP * token_id


def id_to_frequency(token_id: int) -> float:
    """Direct ID -> frequency (supports arbitrary signed integers)."""
    return BASE_FREQ + FREQ_STEP * token_id


def generate_tone(frequency: float, duration: float = 0.5, amplitude: float = 0.5) -> np.ndarray:
    """
    Generate a pure sine wave tone at the given frequency.

    Args:
        frequency: Frequency in Hz
        duration: Duration in seconds
        amplitude: Amplitude (0-1)

    Returns:
        Audio samples as float32 array
    """
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), dtype=np.float32)
    return amplitude * np.sin(2 * np.pi * frequency * t)


def generate_symphonic_sequence(
    tokens: List[str],
    tone_duration: float = 0.3,
    fade_duration: float = 0.02
) -> np.ndarray:
    """
    Generate audio waveform from a sequence of sacred tongue tokens.

    Creates a symphonic representation where:
    - Light tokens produce rising frequencies (above 440 Hz)
    - Shadow tokens produce falling frequencies (below 440 Hz)
    - Neutral tokens anchor at 440 Hz

    Args:
        tokens: List of token strings
        tone_duration: Duration of each tone in seconds
        fade_duration: Fade in/out duration for smooth transitions

    Returns:
        Audio samples as float32 array
    """
    samples = []
    fade_samples = int(SAMPLE_RATE * fade_duration)

    for token in tokens:
        st = SymphonicToken.from_token(token)

        # Generate base tone
        tone = generate_tone(st.frequency, tone_duration)

        # Apply polarity-based amplitude modulation
        if st.polarity == TonguePolarity.SHADOW:
            # Shadow tokens have slightly lower amplitude (hidden/subtle)
            tone *= 0.7
        elif st.polarity == TonguePolarity.LIGHT:
            # Light tokens have full amplitude
            tone *= 1.0
        else:
            # Neutral has medium amplitude
            tone *= 0.85

        # Apply fade envelope
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)

        tone[:fade_samples] *= fade_in
        tone[-fade_samples:] *= fade_out

        samples.append(tone)

    return np.concatenate(samples)


def analyze_polarity_balance(tokens: List[str]) -> Dict[str, any]:
    """
    Analyze the light/shadow balance of a token sequence.

    Returns metrics for dual-lattice integration:
    - polarity_sum: Net polarity (positive = light-dominant)
    - balance_ratio: -1 (all shadow) to +1 (all light)
    - shadow_count, light_count, neutral_count
    """
    light_count = 0
    shadow_count = 0
    neutral_count = 0
    id_sum = 0

    for token in tokens:
        st = SymphonicToken.from_token(token)
        id_sum += st.token_id

        if st.polarity == TonguePolarity.LIGHT:
            light_count += 1
        elif st.polarity == TonguePolarity.SHADOW:
            shadow_count += 1
        else:
            neutral_count += 1

    total = len(tokens)
    balance_ratio = (light_count - shadow_count) / total if total > 0 else 0

    return {
        "polarity_sum": id_sum,
        "balance_ratio": balance_ratio,
        "light_count": light_count,
        "shadow_count": shadow_count,
        "neutral_count": neutral_count,
        "dominant_polarity": (
            "light" if balance_ratio > 0.1 else
            "shadow" if balance_ratio < -0.1 else
            "balanced"
        )
    }


# =============================================================================
# Tests (from documentation)
# =============================================================================

if __name__ == "__main__":
    # Verify documented behavior
    assert token_to_frequency("shadow") == 410.0
    assert id_to_frequency(-1) == 410.0
    assert id_to_frequency(0) == 440.0
    assert id_to_frequency(1) == 470.0

    print(f"[SYMPHONIC] 'shadow' -> {token_to_frequency('shadow')} Hz")
    print(f"[SYMPHONIC] 'light' -> {token_to_frequency('light')} Hz")
    print(f"[SYMPHONIC] 'balance' -> {token_to_frequency('balance')} Hz")
    print(f"[SYMPHONIC] 'abyss' -> {token_to_frequency('abyss')} Hz")

    # Test sequence
    sequence = ["light", "shadow", "balance", "fire", "void", "truth"]
    analysis = analyze_polarity_balance(sequence)
    print(f"\n[SYMPHONIC] Sequence analysis: {analysis}")

    # Generate waveform
    waveform = generate_symphonic_sequence(sequence)
    print(f"[SYMPHONIC] Generated {len(waveform)} samples ({len(waveform)/SAMPLE_RATE:.2f}s)")
