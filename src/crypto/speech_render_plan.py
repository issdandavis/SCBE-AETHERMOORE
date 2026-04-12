"""
Speech Render Plan — Tongue-Voiced TTS with Dead-Tone Pre-Tones
================================================================

Turns SCBE harmonic state into speech rendering instructions.

Pipeline position:
    text -> tokenizer -> SCBE state -> dead-tone analysis -> SpeechRenderPlan

Each Sacred Tongue gets a base voice profile (rate, pitch, energy, breathiness).
Dead tones map to pre-tone earcons. Stereo panning follows the dual-iris layout.

Excitation from the quantum frequency bundle modulates rate and energy
so the voice breathes with the system state.

@layer Layer 14 (Audio Axis)
@component Speech Render Plan
"""

from dataclasses import dataclass
from typing import Optional, Dict

# ============================================================================
# Constants
# ============================================================================

PHI = (1 + 5 ** 0.5) / 2

# Dead-tone -> pre-tone frequency mapping (Hz)
# These are the 3 phi-unreachable intervals
DEAD_TONE_PRETONES: Dict[str, float] = {
    "perfect_fifth": 330.0,   # 3:2 ratio
    "minor_sixth": 352.0,     # 8:5 ratio
    "minor_seventh": 392.0,   # 16:9 ratio
}

# Stereo pan positions: left-ear tongues negative, right-ear positive
# Mirrors the dual-iris / dual-seed layout
TONGUE_PAN: Dict[str, float] = {
    "ko": -0.6,
    "dr": -0.4,
    "av":  0.0,
    "um":  0.0,
    "ru":  0.4,
    "ca":  0.6,
}

# Base voice profiles: (voice_name, rate, pitch_semitones, energy, breathiness, pause_ms)
_BASE_PROFILES: Dict[str, tuple] = {
    "ko": ("alloy",  0.95,  0.0, 0.50, 0.10, 140),  # clear, centered, stable
    "av": ("verse",  1.00,  1.0, 0.45, 0.25, 120),  # smooth, fluid, airy
    "ru": ("ember",  0.92, -1.5, 0.75, 0.08, 160),  # dense, warm, forceful
    "ca": ("aria",   1.08,  2.0, 0.65, 0.05, 100),  # bright, agile, inventive
    "um": ("shade",  0.85, -2.0, 0.30, 0.35, 180),  # soft, shadowed, low resonance
    "dr": ("stone",  0.80, -3.0, 0.70, 0.02, 200),  # grounded, heavy, deliberate
}

ALL_TONGUES = frozenset(_BASE_PROFILES.keys())


# ============================================================================
# Data Structures
# ============================================================================

@dataclass(frozen=True)
class TongueVoiceProfile:
    """Voice identity for a single Sacred Tongue."""

    tongue: str
    voice_name: str
    rate: float             # 0.5 - 2.0 (1.0 = normal)
    pitch_semitones: float  # relative pitch shift
    energy: float           # 0.0 - 1.0
    breathiness: float      # 0.0 - 1.0
    pause_ms: int           # inter-phrase pause

    def validate(self) -> None:
        assert self.tongue in ALL_TONGUES, f"unknown tongue: {self.tongue}"
        assert 0.5 <= self.rate <= 2.0
        assert 0.0 <= self.energy <= 1.0
        assert 0.0 <= self.breathiness <= 1.0
        assert self.pause_ms >= 0


@dataclass(frozen=True)
class SpeechRenderPlan:
    """Complete rendering instruction for one utterance."""

    text: str
    dominant_tongue: str
    dead_tone: str
    excitation: float
    profile: TongueVoiceProfile
    pre_tone_hz: Optional[float]  # earcon before speech (None if no dead tone)
    stereo_pan: float             # -1.0 (left) to +1.0 (right)

    def validate(self) -> None:
        assert self.text != ""
        assert self.dominant_tongue in ALL_TONGUES
        assert -1.0 <= self.stereo_pan <= 1.0
        if self.pre_tone_hz is not None:
            assert self.pre_tone_hz > 0.0
        self.profile.validate()


# ============================================================================
# Builder
# ============================================================================

def build_speech_plan(
    text: str,
    dominant_tongue: str,
    dead_tone: str,
    excitation: float,
) -> SpeechRenderPlan:
    """Build a speech rendering plan from SCBE state.

    Args:
        text: The utterance to render.
        dominant_tongue: Which Sacred Tongue dominates (ko/av/ru/ca/um/dr).
        dead_tone: Which dead tone is active (perfect_fifth/minor_sixth/minor_seventh).
        excitation: QHO excitation level from the quantum frequency bundle.

    Returns:
        A frozen SpeechRenderPlan ready for a TTS engine.
    """
    base = _BASE_PROFILES[dominant_tongue]
    voice_name, base_rate, pitch, base_energy, breathiness, pause = base

    # Excitation modulates rate: higher excitation -> faster speech (clamped)
    rate = max(0.7, min(1.3, base_rate + 0.03 * (excitation - 3.0)))

    # Excitation modulates energy: higher excitation -> more energy (clamped)
    energy = max(0.0, min(1.0, base_energy + 0.04 * excitation))

    profile = TongueVoiceProfile(
        tongue=dominant_tongue,
        voice_name=voice_name,
        rate=rate,
        pitch_semitones=pitch,
        energy=energy,
        breathiness=breathiness,
        pause_ms=pause,
    )

    return SpeechRenderPlan(
        text=text,
        dominant_tongue=dominant_tongue,
        dead_tone=dead_tone,
        excitation=excitation,
        profile=profile,
        pre_tone_hz=DEAD_TONE_PRETONES.get(dead_tone),
        stereo_pan=TONGUE_PAN[dominant_tongue],
    )
