"""
Choral Render — Multi-Voice Synthesis with Conlang Grammar Constraints
======================================================================

Layers voice, prosody, and choir structure on top of SpeechRenderPlan.

Three render modes:
    Mode 1  plain speech    — single voice, conlang-informed phrasing
    Mode 2  speech-song     — lead voice + harmonic backing, pitch-guided contour
    Mode 3  choral ritual   — multi-voice layered rendering, grammar-shaped phrases

Each Sacred Tongue contributes acoustic behavior constraints:
    KO  balanced, even stress, clipped phrases
    AV  liquid continuants, flowing stress, smoother cadence
    RU  dense consonants, percussive stress, forceful delivery
    CA  bright vowels, rising stress, upward melodic movement
    UM  breathy, falling stress, low-energy trailing contours
    DR  heavy syllables, grounded stress, deliberate pacing

@layer Layer 14 (Audio Axis)
@component Choral Render
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

PHI = (1 + 5 ** 0.5) / 2


# ============================================================================
# Enums
# ============================================================================

class RenderMode(Enum):
    PLAIN_SPEECH = 1
    SPEECH_SONG = 2
    CHORAL_RITUAL = 3


class VoiceRole(Enum):
    LEAD = "lead"
    SHADOW = "shadow"
    DRONE = "drone"
    HARMONY = "harmony"


# ============================================================================
# Tongue Profiles — acoustic behavior grammars
# ============================================================================

@dataclass(frozen=True)
class TongueProfile:
    """Acoustic behavior grammar for a Sacred Tongue."""

    name: str
    syllable_style: str   # balanced, liquid, dense, bright, soft, heavy
    stress_pattern: str   # even, flowing, percussive, rising, falling, grounded
    speech_rate: float    # 0.6 - 1.3
    chant_ratio: float    # 0.0 - 1.0 (how much chant vs speech)

    def validate(self) -> None:
        assert 0.6 <= self.speech_rate <= 1.3
        assert 0.0 <= self.chant_ratio <= 1.0


PROFILES: Dict[str, TongueProfile] = {
    "ko": TongueProfile("ko", "balanced",   "even",       0.95, 0.10),
    "av": TongueProfile("av", "liquid",      "flowing",    1.00, 0.20),
    "ru": TongueProfile("ru", "dense",       "percussive", 0.90, 0.25),
    "ca": TongueProfile("ca", "bright",      "rising",     1.08, 0.30),
    "um": TongueProfile("um", "soft",        "falling",    0.82, 0.35),
    "dr": TongueProfile("dr", "heavy",       "grounded",   0.80, 0.22),
}


# ============================================================================
# Phoneme + Prosody
# ============================================================================

@dataclass(frozen=True)
class PhonemeToken:
    """One phonemic unit with timing and stress."""

    text: str
    ipa: str
    duration_ms: int
    stress: float         # 0.0 - 1.0

    def validate(self) -> None:
        assert self.text != ""
        assert self.duration_ms > 0
        assert 0.0 <= self.stress <= 1.0


@dataclass(frozen=True)
class ProsodyPlan:
    """Prosodic contour for an utterance."""

    rate: float                 # speech rate multiplier
    pitch_curve: tuple          # sequence of relative pitch values
    pause_points: tuple         # indices where pauses occur
    energy: float               # 0.0 - 1.0
    chant_ratio: float          # 0.0 = pure speech, 1.0 = pure chant

    def validate(self) -> None:
        assert 0.5 <= self.rate <= 2.0
        assert 0.0 <= self.energy <= 1.0
        assert 0.0 <= self.chant_ratio <= 1.0
        assert len(self.pitch_curve) > 0


# ============================================================================
# Voice Layers
# ============================================================================

@dataclass(frozen=True)
class VoiceLayer:
    """One voice in a choral arrangement."""

    role: VoiceRole
    voice_id: str
    gain: float                   # 0.0 - 1.0
    pan: float                    # -1.0 (left) to +1.0 (right)
    pitch_shift_semitones: float  # relative to root

    def validate(self) -> None:
        assert 0.0 <= self.gain <= 1.0
        assert -1.0 <= self.pan <= 1.0


# ============================================================================
# Choral Render Plan
# ============================================================================

@dataclass(frozen=True)
class ChoralRenderPlan:
    """Complete multi-voice rendering instruction."""

    phonemes: tuple               # tuple of PhonemeToken
    prosody: ProsodyPlan
    voices: tuple                 # tuple of VoiceLayer
    tongue: str
    mode: RenderMode

    def validate(self) -> None:
        assert len(self.phonemes) > 0
        assert len(self.voices) > 0
        assert self.tongue in PROFILES
        self.prosody.validate()
        for v in self.voices:
            v.validate()


# ============================================================================
# Builders
# ============================================================================

def build_prosody(
    tongue: str,
    excitation: float,
    n_phonemes: int,
) -> ProsodyPlan:
    """Build prosody from tongue profile and excitation level."""
    profile = PROFILES[tongue]

    # Rate modulated by excitation
    rate = max(0.5, min(2.0, profile.speech_rate + 0.02 * (excitation - 3.0)))

    # Pitch curve shaped by stress pattern
    if profile.stress_pattern == "rising":
        curve = tuple(0.5 + 0.5 * (i / max(1, n_phonemes - 1)) for i in range(n_phonemes))
    elif profile.stress_pattern == "falling":
        curve = tuple(1.0 - 0.5 * (i / max(1, n_phonemes - 1)) for i in range(n_phonemes))
    elif profile.stress_pattern == "percussive":
        curve = tuple(0.8 if i % 2 == 0 else 0.4 for i in range(n_phonemes))
    elif profile.stress_pattern == "flowing":
        curve = tuple(0.5 + 0.3 * math.sin(2 * math.pi * i / max(1, n_phonemes)) for i in range(n_phonemes))
    elif profile.stress_pattern == "grounded":
        curve = tuple(0.3 for _ in range(n_phonemes))
    else:  # even
        curve = tuple(0.5 for _ in range(n_phonemes))

    # Pause every 4-6 phonemes
    step = 5 if profile.syllable_style in ("balanced", "liquid") else 4
    pauses = tuple(i for i in range(step, n_phonemes, step))

    energy = max(0.0, min(1.0, 0.4 + 0.06 * excitation))

    return ProsodyPlan(
        rate=rate,
        pitch_curve=curve,
        pause_points=pauses,
        energy=energy,
        chant_ratio=profile.chant_ratio,
    )


def build_voice_layers(
    tongue: str,
    mode: RenderMode,
) -> tuple:
    """Build voice layer stack for the given render mode."""
    profile = PROFILES[tongue]
    from .speech_render_plan import TONGUE_PAN
    pan = TONGUE_PAN.get(tongue, 0.0)

    lead = VoiceLayer(
        role=VoiceRole.LEAD,
        voice_id=f"{tongue}_lead",
        gain=0.9,
        pan=pan,
        pitch_shift_semitones=0.0,
    )

    if mode == RenderMode.PLAIN_SPEECH:
        return (lead,)

    shadow = VoiceLayer(
        role=VoiceRole.SHADOW,
        voice_id=f"{tongue}_shadow",
        gain=0.3,
        pan=pan * 0.5,
        pitch_shift_semitones=-0.5,
    )

    if mode == RenderMode.SPEECH_SONG:
        return (lead, shadow)

    # Choral ritual: lead + shadow + drone + harmony
    drone = VoiceLayer(
        role=VoiceRole.DRONE,
        voice_id=f"{tongue}_drone",
        gain=0.2,
        pan=0.0,
        pitch_shift_semitones=-12.0,  # octave below
    )
    harmony = VoiceLayer(
        role=VoiceRole.HARMONY,
        voice_id=f"{tongue}_harmony",
        gain=0.25,
        pan=-pan,  # opposite side for width
        pitch_shift_semitones=7.0,  # perfect fifth above
    )

    return (lead, shadow, drone, harmony)


def build_choral_plan(
    phonemes: List[PhonemeToken],
    tongue: str,
    excitation: float,
    mode: RenderMode = RenderMode.PLAIN_SPEECH,
) -> ChoralRenderPlan:
    """Build a complete choral render plan.

    Args:
        phonemes: Tokenized phoneme sequence.
        tongue: Dominant Sacred Tongue.
        excitation: QHO excitation from quantum frequency bundle.
        mode: PLAIN_SPEECH, SPEECH_SONG, or CHORAL_RITUAL.
    """
    prosody = build_prosody(tongue, excitation, len(phonemes))
    voices = build_voice_layers(tongue, mode)

    return ChoralRenderPlan(
        phonemes=tuple(phonemes),
        prosody=prosody,
        voices=voices,
        tongue=tongue,
        mode=mode,
    )
