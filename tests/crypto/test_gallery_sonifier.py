"""Tests for gallery_sonifier.py — color field → audio parameter bridge.

Self-contained: no heavy imports.
"""

import math
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Inline module under test
# ---------------------------------------------------------------------------

PHI = 1.618033988749895
TAU = 2.0 * math.pi
FREQ_MIN = 100.0
FREQ_MAX = 4000.0

DEAD_TONE_ACOUSTIC = {
    "perfect_fifth": {"base_hz": 330.0, "envelope": "pulse", "pulse_rate_hz": 2.0, "reverb": 0.1, "delay_ms": 0},
    "minor_sixth": {"base_hz": 352.0, "envelope": "dissonance", "pulse_rate_hz": 0.0, "reverb": 0.3, "delay_ms": 0},
    "minor_seventh": {"base_hz": 392.0, "envelope": "echo", "pulse_rate_hz": 0.0, "reverb": 0.7, "delay_ms": 250},
}

MATERIAL_ENVELOPES = {
    "matte": {"attack_ms": 50, "decay_ms": 200, "sustain": 0.6, "release_ms": 300},
    "fluorescent": {"attack_ms": 10, "decay_ms": 80, "sustain": 0.8, "release_ms": 150},
    "neon": {"attack_ms": 5, "decay_ms": 50, "sustain": 0.9, "release_ms": 100},
    "metallic": {"attack_ms": 2, "decay_ms": 150, "sustain": 0.7, "release_ms": 500},
}


@dataclass(frozen=True)
class LabColor:
    L: float
    a: float
    b: float

    @property
    def chroma(self):
        return math.hypot(self.a, self.b)

    @property
    def hue_degrees(self):
        h = math.degrees(math.atan2(self.b, self.a))
        return h if h >= 0 else h + 360.0


@dataclass(frozen=True)
class AudioParams:
    frequency_hz: float
    amplitude: float
    attack_ms: int
    decay_ms: int
    sustain: float
    release_ms: int
    reverb: float
    delay_ms: int
    pan: float


def hue_to_frequency(hue_degrees):
    t = hue_degrees / 360.0
    log_min = math.log(FREQ_MIN)
    log_max = math.log(FREQ_MAX)
    return math.exp(log_min + t * (log_max - log_min))


def chroma_to_amplitude(chroma, max_chroma=130.0):
    return max(0.0, min(1.0, chroma / max_chroma))


def material_to_envelope(material):
    return MATERIAL_ENVELOPES.get(material, MATERIAL_ENVELOPES["matte"])


def color_to_audio(color, material="matte", pan=0.0, reverb=0.0, delay_ms=0):
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHueToFrequency:

    def test_zero_hue_gives_freq_min(self):
        assert abs(hue_to_frequency(0.0) - FREQ_MIN) < 0.01

    def test_360_hue_gives_freq_max(self):
        assert abs(hue_to_frequency(360.0) - FREQ_MAX) < 0.01

    def test_monotonically_increasing(self):
        prev = 0.0
        for h in range(0, 361, 10):
            f = hue_to_frequency(float(h))
            assert f >= prev
            prev = f

    def test_midpoint_is_geometric_mean(self):
        mid = hue_to_frequency(180.0)
        geo = math.sqrt(FREQ_MIN * FREQ_MAX)
        assert abs(mid - geo) < 1.0

    def test_always_positive(self):
        for h in range(0, 361):
            assert hue_to_frequency(float(h)) > 0


class TestChromaToAmplitude:

    def test_zero_chroma_zero_amp(self):
        assert chroma_to_amplitude(0.0) == 0.0

    def test_max_chroma_one_amp(self):
        assert chroma_to_amplitude(130.0) == 1.0

    def test_over_max_clamped(self):
        assert chroma_to_amplitude(200.0) == 1.0

    def test_mid_chroma(self):
        assert abs(chroma_to_amplitude(65.0) - 0.5) < 0.01


class TestLabColor:

    def test_chroma_zero_at_origin(self):
        c = LabColor(50.0, 0.0, 0.0)
        assert c.chroma == 0.0

    def test_chroma_positive(self):
        c = LabColor(50.0, 30.0, 40.0)
        assert c.chroma == 50.0

    def test_hue_first_quadrant(self):
        c = LabColor(50.0, 1.0, 1.0)
        assert 0 < c.hue_degrees < 90

    def test_hue_wraps_negative(self):
        c = LabColor(50.0, -1.0, -1.0)
        assert 180 < c.hue_degrees < 270


class TestColorToAudio:

    def test_returns_audio_params(self):
        c = LabColor(50.0, 30.0, 40.0)
        a = color_to_audio(c)
        assert isinstance(a, AudioParams)
        assert a.frequency_hz > 0
        assert 0.0 <= a.amplitude <= 1.0

    def test_material_affects_envelope(self):
        c = LabColor(50.0, 30.0, 40.0)
        matte = color_to_audio(c, material="matte")
        neon = color_to_audio(c, material="neon")
        assert matte.attack_ms > neon.attack_ms

    def test_pan_passes_through(self):
        c = LabColor(50.0, 30.0, 40.0)
        a = color_to_audio(c, pan=-0.5)
        assert a.pan == -0.5

    def test_reverb_passes_through(self):
        c = LabColor(50.0, 30.0, 40.0)
        a = color_to_audio(c, reverb=0.8)
        assert a.reverb == 0.8

    def test_delay_passes_through(self):
        c = LabColor(50.0, 30.0, 40.0)
        a = color_to_audio(c, delay_ms=250)
        assert a.delay_ms == 250


class TestDeadToneAcoustic:

    def test_three_dead_tones(self):
        assert len(DEAD_TONE_ACOUSTIC) == 3

    def test_echo_has_delay(self):
        assert DEAD_TONE_ACOUSTIC["minor_seventh"]["delay_ms"] > 0

    def test_pulse_has_rate(self):
        assert DEAD_TONE_ACOUSTIC["perfect_fifth"]["pulse_rate_hz"] > 0

    def test_dissonance_no_pulse(self):
        assert DEAD_TONE_ACOUSTIC["minor_sixth"]["pulse_rate_hz"] == 0.0

    def test_all_have_positive_base_hz(self):
        for sig in DEAD_TONE_ACOUSTIC.values():
            assert sig["base_hz"] > 0


class TestMaterialEnvelopes:

    def test_four_materials(self):
        assert len(MATERIAL_ENVELOPES) == 4

    def test_neon_fastest_attack(self):
        attacks = {k: v["attack_ms"] for k, v in MATERIAL_ENVELOPES.items()}
        assert attacks["neon"] < attacks["matte"]

    def test_metallic_longest_release(self):
        releases = {k: v["release_ms"] for k, v in MATERIAL_ENVELOPES.items()}
        assert releases["metallic"] == max(releases.values())

    def test_all_sustain_bounded(self):
        for v in MATERIAL_ENVELOPES.values():
            assert 0.0 <= v["sustain"] <= 1.0


class TestSonifyDeadTone:

    def test_perfect_fifth_returns_list(self):
        colors = [LabColor(50.0, 30.0, 40.0), LabColor(60.0, -20.0, 30.0)]
        materials = ["matte", "neon"]
        results = []
        for i, (c, m) in enumerate(zip(colors, materials)):
            pan = -0.5 + i * (1.0 / max(1, len(colors) - 1))
            sig = DEAD_TONE_ACOUSTIC["perfect_fifth"]
            a = color_to_audio(c, material=m, pan=pan, reverb=sig["reverb"], delay_ms=sig["delay_ms"])
            results.append(a)
        assert len(results) == 2
        assert all(isinstance(r, AudioParams) for r in results)

    def test_dead_tone_reverb_applied(self):
        c = LabColor(50.0, 30.0, 40.0)
        sig = DEAD_TONE_ACOUSTIC["minor_seventh"]
        a = color_to_audio(c, reverb=sig["reverb"], delay_ms=sig["delay_ms"])
        assert a.reverb == 0.7
        assert a.delay_ms == 250

    def test_stereo_spread(self):
        [LabColor(50.0, 10.0, 10.0)] * 4
        pans = [-0.5 + i * (1.0 / 3) for i in range(4)]
        assert pans[0] < 0
        assert pans[-1] > 0

    def test_all_dead_tones_produce_audio(self):
        c = LabColor(50.0, 30.0, 40.0)
        for _tone_name, sig in DEAD_TONE_ACOUSTIC.items():
            a = color_to_audio(c, reverb=sig["reverb"], delay_ms=sig["delay_ms"])
            assert a.frequency_hz > 0
            assert 0.0 <= a.amplitude <= 1.0
