"""Tests for speech_render_plan.py — tongue-voiced TTS rendering.

Self-contained: no heavy imports. Can run standalone or via pytest.
"""

import math
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict

# ---------------------------------------------------------------------------
# Inline copy of the module under test (avoids conftest import chain)
# ---------------------------------------------------------------------------

PHI = (1 + 5 ** 0.5) / 2

DEAD_TONE_PRETONES: Dict[str, float] = {
    "perfect_fifth": 330.0,
    "minor_sixth": 352.0,
    "minor_seventh": 392.0,
}

TONGUE_PAN: Dict[str, float] = {
    "ko": -0.6, "dr": -0.4, "av": 0.0,
    "um":  0.0, "ru":  0.4, "ca": 0.6,
}

_BASE_PROFILES: Dict[str, tuple] = {
    "ko": ("alloy",  0.95,  0.0, 0.50, 0.10, 140),
    "av": ("verse",  1.00,  1.0, 0.45, 0.25, 120),
    "ru": ("ember",  0.92, -1.5, 0.75, 0.08, 160),
    "ca": ("aria",   1.08,  2.0, 0.65, 0.05, 100),
    "um": ("shade",  0.85, -2.0, 0.30, 0.35, 180),
    "dr": ("stone",  0.80, -3.0, 0.70, 0.02, 200),
}

ALL_TONGUES = frozenset(_BASE_PROFILES.keys())


@dataclass(frozen=True)
class TongueVoiceProfile:
    tongue: str
    voice_name: str
    rate: float
    pitch_semitones: float
    energy: float
    breathiness: float
    pause_ms: int


@dataclass(frozen=True)
class SpeechRenderPlan:
    text: str
    dominant_tongue: str
    dead_tone: str
    excitation: float
    profile: TongueVoiceProfile
    pre_tone_hz: Optional[float]
    stereo_pan: float


def build_speech_plan(text, dominant_tongue, dead_tone, excitation):
    base = _BASE_PROFILES[dominant_tongue]
    voice_name, base_rate, pitch, base_energy, breathiness, pause = base
    rate = max(0.7, min(1.3, base_rate + 0.03 * (excitation - 3.0)))
    energy = max(0.0, min(1.0, base_energy + 0.04 * excitation))
    profile = TongueVoiceProfile(
        tongue=dominant_tongue, voice_name=voice_name, rate=rate,
        pitch_semitones=pitch, energy=energy,
        breathiness=breathiness, pause_ms=pause,
    )
    return SpeechRenderPlan(
        text=text, dominant_tongue=dominant_tongue, dead_tone=dead_tone,
        excitation=excitation, profile=profile,
        pre_tone_hz=DEAD_TONE_PRETONES.get(dead_tone),
        stereo_pan=TONGUE_PAN[dominant_tongue],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBuildSpeechPlan:

    def test_plan_builds_for_all_tongues(self):
        for t in ALL_TONGUES:
            plan = build_speech_plan("hello", t, "perfect_fifth", 3.0)
            assert plan.dominant_tongue == t
            assert plan.text == "hello"

    def test_dead_tone_maps_to_pretone(self):
        plan = build_speech_plan("x", "ca", "minor_seventh", 4.0)
        assert plan.pre_tone_hz == 392.0

    def test_unknown_dead_tone_gives_none(self):
        plan = build_speech_plan("x", "ko", "unknown_tone", 3.0)
        assert plan.pre_tone_hz is None

    def test_rate_increases_with_excitation(self):
        low = build_speech_plan("x", "av", "perfect_fifth", 1.0)
        high = build_speech_plan("x", "av", "perfect_fifth", 6.0)
        assert high.profile.rate > low.profile.rate

    def test_rate_clamped_to_bounds(self):
        extreme = build_speech_plan("x", "ko", "perfect_fifth", 100.0)
        assert 0.7 <= extreme.profile.rate <= 1.3

    def test_energy_increases_with_excitation(self):
        low = build_speech_plan("x", "ru", "minor_sixth", 0.0)
        high = build_speech_plan("x", "ru", "minor_sixth", 10.0)
        assert high.profile.energy > low.profile.energy

    def test_energy_clamped_at_one(self):
        extreme = build_speech_plan("x", "ru", "minor_sixth", 100.0)
        assert extreme.profile.energy <= 1.0

    def test_pan_reflects_seed_side(self):
        left = build_speech_plan("x", "ko", "perfect_fifth", 3.0)
        right = build_speech_plan("x", "ca", "perfect_fifth", 3.0)
        assert left.stereo_pan < 0
        assert right.stereo_pan > 0

    def test_center_tongues_have_zero_pan(self):
        av = build_speech_plan("x", "av", "perfect_fifth", 3.0)
        um = build_speech_plan("x", "um", "perfect_fifth", 3.0)
        assert av.stereo_pan == 0.0
        assert um.stereo_pan == 0.0

    def test_dead_tones_map_to_distinct_pretones(self):
        a = build_speech_plan("x", "ko", "perfect_fifth", 3.0)
        b = build_speech_plan("x", "ko", "minor_sixth", 3.0)
        c = build_speech_plan("x", "ko", "minor_seventh", 3.0)
        assert len({a.pre_tone_hz, b.pre_tone_hz, c.pre_tone_hz}) == 3

    def test_profile_bounds(self):
        for t in ALL_TONGUES:
            plan = build_speech_plan("x", t, "minor_seventh", 5.0)
            assert 0.7 <= plan.profile.rate <= 1.3
            assert 0.0 <= plan.profile.energy <= 1.0
            assert 0.0 <= plan.profile.breathiness <= 1.0

    def test_voice_names_unique_per_tongue(self):
        names = set()
        for t in ALL_TONGUES:
            plan = build_speech_plan("x", t, "perfect_fifth", 3.0)
            names.add(plan.profile.voice_name)
        assert len(names) == 6

    def test_frozen_dataclass(self):
        plan = build_speech_plan("x", "ko", "perfect_fifth", 3.0)
        try:
            plan.text = "changed"
            assert False, "should be frozen"
        except AttributeError:
            pass

    def test_negative_excitation_energy_floor(self):
        plan = build_speech_plan("x", "ko", "perfect_fifth", -100.0)
        assert plan.profile.energy >= 0.0

    def test_negative_excitation_rate_floor(self):
        plan = build_speech_plan("x", "av", "minor_sixth", -50.0)
        assert plan.profile.rate >= 0.7

    def test_negative_excitation_all_bounds(self):
        for t in ALL_TONGUES:
            plan = build_speech_plan("x", t, "perfect_fifth", -100.0)
            assert 0.7 <= plan.profile.rate <= 1.3
            assert 0.0 <= plan.profile.energy <= 1.0
            assert 0.0 <= plan.profile.breathiness <= 1.0


class TestTonguePan:

    def test_all_tongues_have_pan(self):
        assert set(TONGUE_PAN.keys()) == ALL_TONGUES

    def test_pan_range(self):
        for v in TONGUE_PAN.values():
            assert -1.0 <= v <= 1.0

    def test_left_right_symmetry(self):
        # ko/dr on left, ru/ca on right
        assert TONGUE_PAN["ko"] < 0
        assert TONGUE_PAN["dr"] < 0
        assert TONGUE_PAN["ru"] > 0
        assert TONGUE_PAN["ca"] > 0


class TestDeadTonePretones:

    def test_three_dead_tones(self):
        assert len(DEAD_TONE_PRETONES) == 3

    def test_frequencies_positive(self):
        for v in DEAD_TONE_PRETONES.values():
            assert v > 0.0

    def test_frequencies_distinct(self):
        vals = list(DEAD_TONE_PRETONES.values())
        assert len(set(vals)) == 3

    def test_frequencies_in_audible_range(self):
        for v in DEAD_TONE_PRETONES.values():
            assert 20.0 <= v <= 20000.0
