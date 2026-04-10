"""Tests for choral_render.py — multi-voice synthesis with conlang constraints.

Self-contained: no heavy imports.
"""

import math
from dataclasses import dataclass
from typing import Dict, List
from enum import Enum

# ---------------------------------------------------------------------------
# Inline module under test
# ---------------------------------------------------------------------------

PHI = (1 + 5 ** 0.5) / 2


class RenderMode(Enum):
    PLAIN_SPEECH = 1
    SPEECH_SONG = 2
    CHORAL_RITUAL = 3


class VoiceRole(Enum):
    LEAD = "lead"
    SHADOW = "shadow"
    DRONE = "drone"
    HARMONY = "harmony"


@dataclass(frozen=True)
class TongueProfile:
    name: str
    syllable_style: str
    stress_pattern: str
    speech_rate: float
    chant_ratio: float


PROFILES: Dict[str, TongueProfile] = {
    "ko": TongueProfile("ko", "balanced",   "even",       0.95, 0.10),
    "av": TongueProfile("av", "liquid",      "flowing",    1.00, 0.20),
    "ru": TongueProfile("ru", "dense",       "percussive", 0.90, 0.25),
    "ca": TongueProfile("ca", "bright",      "rising",     1.08, 0.30),
    "um": TongueProfile("um", "soft",        "falling",    0.82, 0.35),
    "dr": TongueProfile("dr", "heavy",       "grounded",   0.80, 0.22),
}


@dataclass(frozen=True)
class PhonemeToken:
    text: str
    ipa: str
    duration_ms: int
    stress: float


@dataclass(frozen=True)
class ProsodyPlan:
    rate: float
    pitch_curve: tuple
    pause_points: tuple
    energy: float
    chant_ratio: float


@dataclass(frozen=True)
class VoiceLayer:
    role: VoiceRole
    voice_id: str
    gain: float
    pan: float
    pitch_shift_semitones: float


def build_prosody(tongue, excitation, n_phonemes):
    profile = PROFILES[tongue]
    rate = max(0.5, min(2.0, profile.speech_rate + 0.02 * (excitation - 3.0)))
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
    else:
        curve = tuple(0.5 for _ in range(n_phonemes))
    step = 5 if profile.syllable_style in ("balanced", "liquid") else 4
    pauses = tuple(i for i in range(step, n_phonemes, step))
    energy = max(0.0, min(1.0, 0.4 + 0.06 * excitation))
    return ProsodyPlan(rate=rate, pitch_curve=curve, pause_points=pauses,
                       energy=energy, chant_ratio=profile.chant_ratio)


TONGUE_PAN = {"ko": -0.6, "dr": -0.4, "av": 0.0, "um": 0.0, "ru": 0.4, "ca": 0.6}


def build_voice_layers(tongue, mode):
    pan = TONGUE_PAN.get(tongue, 0.0)
    lead = VoiceLayer(VoiceRole.LEAD, f"{tongue}_lead", 0.9, pan, 0.0)
    if mode == RenderMode.PLAIN_SPEECH:
        return (lead,)
    shadow = VoiceLayer(VoiceRole.SHADOW, f"{tongue}_shadow", 0.3, pan * 0.5, -0.5)
    if mode == RenderMode.SPEECH_SONG:
        return (lead, shadow)
    drone = VoiceLayer(VoiceRole.DRONE, f"{tongue}_drone", 0.2, 0.0, -12.0)
    harmony = VoiceLayer(VoiceRole.HARMONY, f"{tongue}_harmony", 0.25, -pan, 7.0)
    return (lead, shadow, drone, harmony)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTongueProfiles:

    def test_all_tongues_present(self):
        assert set(PROFILES) == {"ko", "av", "ru", "ca", "um", "dr"}

    def test_rates_reasonable(self):
        for p in PROFILES.values():
            assert 0.6 <= p.speech_rate <= 1.3

    def test_chant_ratio_bounded(self):
        for p in PROFILES.values():
            assert 0.0 <= p.chant_ratio <= 1.0

    def test_unique_syllable_styles(self):
        styles = [p.syllable_style for p in PROFILES.values()]
        assert len(set(styles)) == 6

    def test_unique_stress_patterns(self):
        patterns = [p.stress_pattern for p in PROFILES.values()]
        assert len(set(patterns)) == 6


class TestBuildProsody:

    def _phonemes(self, n=8):
        return [PhonemeToken(f"p{i}", f"p{i}", 100, 0.5) for i in range(n)]

    def test_builds_for_all_tongues(self):
        for t in PROFILES:
            p = build_prosody(t, 3.0, 8)
            assert len(p.pitch_curve) == 8
            assert 0.5 <= p.rate <= 2.0

    def test_rising_stress_increases(self):
        p = build_prosody("ca", 3.0, 5)
        assert p.pitch_curve[-1] > p.pitch_curve[0]

    def test_falling_stress_decreases(self):
        p = build_prosody("um", 3.0, 5)
        assert p.pitch_curve[-1] < p.pitch_curve[0]

    def test_percussive_alternates(self):
        p = build_prosody("ru", 3.0, 6)
        assert p.pitch_curve[0] > p.pitch_curve[1]
        assert p.pitch_curve[2] > p.pitch_curve[1]

    def test_even_stress_flat(self):
        p = build_prosody("ko", 3.0, 4)
        assert all(v == 0.5 for v in p.pitch_curve)

    def test_grounded_stress_low(self):
        p = build_prosody("dr", 3.0, 4)
        assert all(v == 0.3 for v in p.pitch_curve)

    def test_energy_increases_with_excitation(self):
        lo = build_prosody("ko", 0.0, 4)
        hi = build_prosody("ko", 10.0, 4)
        assert hi.energy > lo.energy

    def test_energy_clamped(self):
        p = build_prosody("ko", 100.0, 4)
        assert p.energy <= 1.0

    def test_chant_ratio_matches_profile(self):
        for t in PROFILES:
            p = build_prosody(t, 3.0, 4)
            assert p.chant_ratio == PROFILES[t].chant_ratio


class TestBuildVoiceLayers:

    def test_plain_speech_one_voice(self):
        voices = build_voice_layers("ko", RenderMode.PLAIN_SPEECH)
        assert len(voices) == 1
        assert voices[0].role == VoiceRole.LEAD

    def test_speech_song_two_voices(self):
        voices = build_voice_layers("av", RenderMode.SPEECH_SONG)
        assert len(voices) == 2
        roles = {v.role for v in voices}
        assert VoiceRole.LEAD in roles
        assert VoiceRole.SHADOW in roles

    def test_choral_ritual_four_voices(self):
        voices = build_voice_layers("ru", RenderMode.CHORAL_RITUAL)
        assert len(voices) == 4
        roles = {v.role for v in voices}
        assert roles == {VoiceRole.LEAD, VoiceRole.SHADOW, VoiceRole.DRONE, VoiceRole.HARMONY}

    def test_lead_gain_highest(self):
        voices = build_voice_layers("ca", RenderMode.CHORAL_RITUAL)
        lead = [v for v in voices if v.role == VoiceRole.LEAD][0]
        for v in voices:
            assert v.gain <= lead.gain

    def test_drone_octave_below(self):
        voices = build_voice_layers("dr", RenderMode.CHORAL_RITUAL)
        drone = [v for v in voices if v.role == VoiceRole.DRONE][0]
        assert drone.pitch_shift_semitones == -12.0

    def test_harmony_fifth_above(self):
        voices = build_voice_layers("ko", RenderMode.CHORAL_RITUAL)
        harmony = [v for v in voices if v.role == VoiceRole.HARMONY][0]
        assert harmony.pitch_shift_semitones == 7.0

    def test_harmony_opposite_pan(self):
        voices = build_voice_layers("ko", RenderMode.CHORAL_RITUAL)
        lead = [v for v in voices if v.role == VoiceRole.LEAD][0]
        harmony = [v for v in voices if v.role == VoiceRole.HARMONY][0]
        # ko has negative pan, harmony should have positive
        assert lead.pan * harmony.pan <= 0  # opposite signs or zero

    def test_all_gains_bounded(self):
        for t in PROFILES:
            for mode in RenderMode:
                for v in build_voice_layers(t, mode):
                    assert 0.0 <= v.gain <= 1.0
                    assert -1.0 <= v.pan <= 1.0


class TestNegativeExcitation:

    def test_prosody_energy_floor(self):
        p = build_prosody("ko", -100.0, 8)
        assert p.energy >= 0.0

    def test_prosody_energy_floor_all_tongues(self):
        for t in PROFILES:
            p = build_prosody(t, -50.0, 4)
            assert 0.0 <= p.energy <= 1.0
            assert 0.5 <= p.rate <= 2.0


class TestBuildChoralPlan:

    def _phonemes(self, n=6):
        return [PhonemeToken(f"p{i}", f"p{i}", 100, 0.5) for i in range(n)]

    def test_plain_speech_plan(self):
        ph = self._phonemes()
        prosody = build_prosody("ko", 3.0, len(ph))
        voices = build_voice_layers("ko", RenderMode.PLAIN_SPEECH)
        assert len(voices) == 1
        assert len(prosody.pitch_curve) == len(ph)

    def test_choral_ritual_plan(self):
        ph = self._phonemes()
        prosody = build_prosody("ru", 5.0, len(ph))
        voices = build_voice_layers("ru", RenderMode.CHORAL_RITUAL)
        assert len(voices) == 4
        assert prosody.energy > 0.0

    def test_all_tongues_all_modes(self):
        ph = self._phonemes(8)
        for t in PROFILES:
            for mode in RenderMode:
                prosody = build_prosody(t, 3.0, len(ph))
                voices = build_voice_layers(t, mode)
                assert len(prosody.pitch_curve) == 8
                assert len(voices) >= 1
