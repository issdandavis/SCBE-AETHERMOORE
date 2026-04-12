"""
Gallery Sonifier — Color Field → Audio Parameter Bridge
========================================================

Converts gallery chromatics color field output into audio parameters:
    hue        → frequency
    chroma     → amplitude
    material   → envelope shape

Bridges src/crypto/gallery_chromatics.py to the L14 audio axis so
dead-tone colors become audible.

Dead tone sonification mapping:
    Perfect fifth (3:2)  → Lotka-Volterra oscillation → audible pulse
    Minor sixth (8:5)    → immune response cross-product → tonal dissonance
    Minor seventh (16:9) → perpendicular echo → literal echo (delay+reverb)

@layer Layer 14 (Audio Axis)
@component Gallery Sonifier
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List

from src.crypto.gallery_chromatics import LabColor

# ============================================================================
# Constants
# ============================================================================

PHI = 1.618033988749895
TAU = 2.0 * math.pi

# Hue-to-frequency base: map 0-360 hue degrees to audible range 100-4000 Hz
# Using log scale so equal hue distance = equal perceived pitch distance
FREQ_MIN = 100.0
FREQ_MAX = 4000.0

# Dead tone acoustic signatures
DEAD_TONE_ACOUSTIC: Dict[str, Dict] = {
    "perfect_fifth": {
        "base_hz": 330.0,
        "envelope": "pulse",  # Lotka-Volterra oscillation
        "pulse_rate_hz": 2.0,  # predator-prey rhythm
        "reverb": 0.1,
        "delay_ms": 0,
    },
    "minor_sixth": {
        "base_hz": 352.0,
        "envelope": "dissonance",  # immune response cross-product
        "pulse_rate_hz": 0.0,
        "reverb": 0.3,
        "delay_ms": 0,
    },
    "minor_seventh": {
        "base_hz": 392.0,
        "envelope": "echo",  # perpendicular echo → literal echo
        "pulse_rate_hz": 0.0,
        "reverb": 0.7,
        "delay_ms": 250,  # quarter-second delay
    },
}

# Material → envelope characteristics
MATERIAL_ENVELOPES: Dict[str, Dict] = {
    "matte": {"attack_ms": 50, "decay_ms": 200, "sustain": 0.6, "release_ms": 300},
    "fluorescent": {"attack_ms": 10, "decay_ms": 80, "sustain": 0.8, "release_ms": 150},
    "neon": {"attack_ms": 5, "decay_ms": 50, "sustain": 0.9, "release_ms": 100},
    "metallic": {"attack_ms": 2, "decay_ms": 150, "sustain": 0.7, "release_ms": 500},
}


# ============================================================================
# Data Structures
# ============================================================================

# LabColor imported from gallery_chromatics (single source of truth)
# Has .chroma, .hue_angle (radians), .hue_degrees (degrees), .material


@dataclass(frozen=True)
class AudioParams:
    """Audio parameters derived from a color field point."""

    frequency_hz: float  # from hue
    amplitude: float  # from chroma (0.0-1.0)
    attack_ms: int
    decay_ms: int
    sustain: float  # 0.0-1.0
    release_ms: int
    reverb: float  # 0.0-1.0
    delay_ms: int
    pan: float  # -1.0 to 1.0

    def validate(self) -> None:
        assert self.frequency_hz > 0
        assert 0.0 <= self.amplitude <= 1.0
        assert 0.0 <= self.sustain <= 1.0
        assert 0.0 <= self.reverb <= 1.0
        assert -1.0 <= self.pan <= 1.0


@dataclass(frozen=True)
class DeadToneSonification:
    """Sonification of one dead tone."""

    dead_tone: str
    base_hz: float
    envelope: str
    pulse_rate_hz: float
    reverb: float
    delay_ms: int
    colors: tuple  # tuple of LabColor (the 4-color chord)
    audio_params: tuple  # tuple of AudioParams (one per color)


# ============================================================================
# Core Functions
# ============================================================================


def hue_to_frequency(hue_degrees: float) -> float:
    """Map hue angle (0-360) to log-scaled frequency.

    Equal hue distance → equal perceived pitch distance.
    """
    t = hue_degrees / 360.0  # normalize to 0-1
    # Log interpolation
    log_min = math.log(FREQ_MIN)
    log_max = math.log(FREQ_MAX)
    return math.exp(log_min + t * (log_max - log_min))


def chroma_to_amplitude(chroma: float, max_chroma: float = 130.0) -> float:
    """Map CIELAB chroma to audio amplitude (0.0-1.0).

    Higher chroma → louder signal.
    """
    return max(0.0, min(1.0, chroma / max_chroma))


def material_to_envelope(material: str) -> Dict:
    """Get ADSR envelope parameters for a material band."""
    return MATERIAL_ENVELOPES.get(material, MATERIAL_ENVELOPES["matte"])


def color_to_audio(
    color: LabColor,
    material: str = "matte",
    pan: float = 0.0,
    reverb: float = 0.0,
    delay_ms: int = 0,
) -> AudioParams:
    """Convert a single CIELAB color point to audio parameters.

    Args:
        color: CIELAB color from gallery_chromatics.
        material: Material band (matte/fluorescent/neon/metallic).
        pan: Stereo position (-1 left, +1 right).
        reverb: Reverb amount (0-1).
        delay_ms: Delay in milliseconds.
    """
    freq = hue_to_frequency(color.hue_degrees)
    amp = chroma_to_amplitude(color.chroma)
    env = material_to_envelope(material)

    return AudioParams(
        frequency_hz=freq,
        amplitude=amp,
        attack_ms=env["attack_ms"],
        decay_ms=env["decay_ms"],
        sustain=env["sustain"],
        release_ms=env["release_ms"],
        reverb=reverb,
        delay_ms=delay_ms,
        pan=pan,
    )


def sonify_dead_tone(
    dead_tone: str,
    colors: List[LabColor],
    materials: List[str],
    pan: float = 0.0,
) -> DeadToneSonification:
    """Sonify a dead tone's 4-color chord into audio parameters.

    Args:
        dead_tone: "perfect_fifth", "minor_sixth", or "minor_seventh".
        colors: 4 CIELAB colors from gallery_chromatics (the color chord).
        materials: 4 material band names.
        pan: Base stereo position.
    """
    sig = DEAD_TONE_ACOUSTIC[dead_tone]

    audio_list = []
    for i, (col, mat) in enumerate(zip(colors, materials)):
        # Spread the 4 colors slightly in the stereo field
        color_pan = max(-1.0, min(1.0, pan + 0.15 * (i - 1.5)))
        ap = color_to_audio(
            col,
            material=mat,
            pan=color_pan,
            reverb=sig["reverb"],
            delay_ms=sig["delay_ms"],
        )
        audio_list.append(ap)

    return DeadToneSonification(
        dead_tone=dead_tone,
        base_hz=sig["base_hz"],
        envelope=sig["envelope"],
        pulse_rate_hz=sig["pulse_rate_hz"],
        reverb=sig["reverb"],
        delay_ms=sig["delay_ms"],
        colors=tuple(colors),
        audio_params=tuple(audio_list),
    )
