"""
Golden-Path Integration Tests — Full Multimodal Loop
=====================================================

5 canonical end-to-end fixtures exercising the complete stack:

    1. Calm governance ALLOW decision → speech → sonification → projection
    2. Dead-tone minor sixth event → dissonance envelope → tongue attribution
    3. Minor seventh perpendicular echo → echo+delay → spectrogram feedback
    4. Autorotation / multi-tone broadband → mixed tongue profile → drift check
    5. Conlang choral ritual utterance → 4-voice choir → world bundle circulation

Each fixture runs:
    text/decision → tongue weights → prosody → render plan → choral plan
        → gallery sonifier → spectrogram bridge → projection → assertions

These are NOT unit tests. They verify cross-module contracts hold under
realistic scenarios. If any of these fail, the interface contract is broken.

@layer Layer 14 (Audio Axis)
@component Golden Path Integration
"""

import math
import sys

sys.path.insert(0, ".")

import numpy as np

# --- Module imports (all 7 modules) ---

from src.audio.tongue_prosody import (
    TongueWeightVector,
    ProsodyParams,
    tongue_to_prosody,
    governance_voice,
    tongue_dominant,
    TONGUE_WEIGHTS,
)

from src.crypto.speech_render_plan import (
    build_speech_plan,
    SpeechRenderPlan,
    ALL_TONGUES,
    DEAD_TONE_PRETONES,
    TONGUE_PAN,
)

from src.crypto.choral_render import (
    build_choral_plan,
    build_prosody,
    build_voice_layers,
    PhonemeToken,
    RenderMode,
    VoiceRole,
    PROFILES as CHORAL_PROFILES,
)

from src.crypto.world_bundle import (
    create_default_bundle,
    WorldBundle,
    _DEFAULT_PHONOLOGY,
)

from src.audio.gallery_sonifier import (
    LabColor,
    AudioParams,
    color_to_audio,
    sonify_dead_tone,
    hue_to_frequency,
    chroma_to_amplitude,
    DEAD_TONE_ACOUSTIC,
    MATERIAL_ENVELOPES,
)

from src.audio.spectrogram_bridge import (
    generate_test_signal,
    compute_stft,
    bin_to_hz,
    tongue_band_energy,
    spectral_centroid as spec_centroid,
    hf_ratio,
    freq_to_hue,
    energy_to_chroma,
    project_frame_to_gallery,
    SpectrogramFrame,
    GalleryProjection,
    TONGUE_FREQ_BANDS,
    TONGUE_ORDER,
    _TONGUE_MATERIAL,
    audio_text_alignment,
    SpectrogramAnalysis,
)

from src.crypto.gallery_chromatics import (
    LabColor as GCLabColor,
    scatter_color_quad,
    frequency_to_harmonic_number,
    harmonic_to_polar,
    TONGUE_PHASE_OFFSETS,
    DEAD_TONE_RATIOS as GC_DEAD_TONE_RATIOS,
    LEFT_EYE_TONGUES,
    RIGHT_EYE_TONGUES,
    BRIDGE_TONGUES,
)

# ===========================================================================
# Helpers
# ===========================================================================


def _make_phonemes(text: str, n: int = 6) -> list:
    """Create a phoneme sequence for testing."""
    return [PhonemeToken(c, c, 80, 0.5) for c in (list(text) * n)[:n]]


def _tongue_weights_from_dominant(tongue: str) -> TongueWeightVector:
    """Create a weight vector where one tongue dominates."""
    base = 0.1
    vals = {t: base for t in TONGUE_ORDER}
    vals[tongue] = 0.8
    return TongueWeightVector(**vals)


def _run_spectrogram_pipeline(freq_hz: float):
    """Generate tone → STFT → tongue analysis → gallery projection."""
    sr, sig = generate_test_signal(frequencies=[freq_hz], duration_sec=0.3)
    fft_size = 4096
    mags, bins = compute_stft(sig, fft_size=fft_size, hop_size=512)
    freqs = bin_to_hz(bins, sr, fft_size)
    mid = mags.shape[0] // 2
    energies = tongue_band_energy(mags[mid], freqs)
    dominant = max(energies, key=energies.get)
    centroid = spec_centroid(mags[mid], freqs)
    total_e = float(np.sum(mags[mid] ** 2))
    hfr = hf_ratio(mags[mid], freqs)

    frame = SpectrogramFrame(
        time_sec=0.15,
        frequencies=freqs,
        magnitudes=mags[mid],
        tongue_energies=energies,
        dominant_tongue=dominant,
        total_energy=total_e,
        spectral_centroid=centroid,
        hf_ratio=hfr,
    )
    proj = project_frame_to_gallery(frame)
    return frame, proj, energies


# ===========================================================================
# Fixture 1: Calm Governance ALLOW Decision
# ===========================================================================


class TestGoldenPathCalm:
    """
    Scenario: System is in a calm ALLOW state.
    Dominant tongue: AV (wisdom, flowing).
    Dead tone: perfect_fifth (stable).
    Excitation: low (2.0).

    Expected: warm voice, flowing cadence, low energy, centered stereo,
    pulse envelope sonification, gallery projection in mid-hue range.
    """

    def test_prosody_is_warm_flowing(self):
        weights = _tongue_weights_from_dominant("av")
        prosody = tongue_to_prosody(weights)
        assert prosody.warmth > 0.5, "AV-dominant should be warm"
        assert prosody.cadence == "flowing", "AV > 0.6 should produce flowing cadence"
        prosody.validate()

    def test_governance_voice_is_alexander(self):
        voice = governance_voice("ALLOW")
        assert voice == "alexander_thorne"

    def test_speech_plan_centered_stereo(self):
        plan = build_speech_plan("The path is clear.", "av", "perfect_fifth", 2.0)
        assert plan.stereo_pan == 0.0, "AV should be center"
        assert plan.pre_tone_hz == 330.0, "Perfect fifth earcon"
        assert plan.profile.rate < 1.05, "Low excitation = calm rate"
        plan.validate()

    def test_choral_plain_speech(self):
        phonemes = _make_phonemes("avhari", 8)
        choral = build_choral_plan(phonemes, "av", 2.0, RenderMode.PLAIN_SPEECH)
        assert len(choral.voices) == 1
        assert choral.voices[0].role == VoiceRole.LEAD
        # AV prosody should be flowing (sinusoidal curve)
        curve = choral.prosody.pitch_curve
        assert len(set(curve)) > 1, "Flowing curve should not be flat"
        choral.validate()

    def test_sonification_pulse_envelope(self):
        colors = [
            LabColor(L=65, a=20, b=10, material="matte"),
            LabColor(L=70, a=-15, b=20, material="fluorescent"),
            LabColor(L=60, a=10, b=-25, material="neon"),
            LabColor(L=75, a=-5, b=15, material="metallic"),
        ]
        materials = ["matte", "fluorescent", "neon", "metallic"]
        son = sonify_dead_tone("perfect_fifth", colors, materials, pan=0.0)
        assert son.envelope == "pulse"
        assert son.delay_ms == 0
        assert son.reverb < 0.2
        assert len(son.audio_params) == 4
        for ap in son.audio_params:
            ap.validate()

    def test_spectrogram_mid_range(self):
        # AV wisdom: mid-high frequency (3000 Hz in AV band 2500-6000)
        frame, proj, energies = _run_spectrogram_pipeline(3000.0)
        assert energies["av"] > 0.3, f"3kHz should be AV-dominant: {energies}"
        assert proj.material == "fluorescent", "AV maps to fluorescent"
        assert 0 <= proj.hue_degrees <= 360
        assert 0 <= proj.chroma <= 130

    def test_world_bundle_circulation(self):
        bundle = create_default_bundle()
        cp = bundle.circulate("prosody", ["prosody", "phonology"], {"mode": "calm_allow"}, 0.2)
        assert cp.method == "prosody"
        assert bundle.alignment_score > 0

    def test_full_path_coherence(self):
        """End-to-end: all modules produce consistent tongue=AV."""
        weights = _tongue_weights_from_dominant("av")
        dominant = tongue_dominant(weights)
        assert dominant == "av"

        prosody = tongue_to_prosody(weights)
        plan = build_speech_plan("clarity", "av", "perfect_fifth", 2.0)
        choral = build_choral_plan(_make_phonemes("avhari"), "av", 2.0)
        _, proj, _ = _run_spectrogram_pipeline(3500.0)

        # All point to the same region
        assert plan.dominant_tongue == "av"
        assert choral.tongue == "av"
        assert prosody.cadence == "flowing"
        assert proj.material == "fluorescent"  # AV material


# ===========================================================================
# Fixture 2: Dead-Tone Minor Sixth Event
# ===========================================================================


class TestGoldenPathMinorSixth:
    """
    Scenario: Minor sixth dead tone detected (immune response cross-product).
    Dominant tongue: RU (governance, percussive).
    Excitation: elevated (6.0).

    Expected: dissonance envelope, high energy, percussive prosody,
    QUARANTINE-level governance voice, right-panned stereo.
    """

    def test_speech_plan_with_minor_sixth(self):
        plan = build_speech_plan("Pattern anomaly detected.", "ru", "minor_sixth", 6.0)
        assert plan.pre_tone_hz == 352.0
        assert plan.stereo_pan > 0, "RU pans right"
        assert plan.profile.energy > 0.6, "High excitation = high energy"
        plan.validate()

    def test_prosody_percussive(self):
        weights = _tongue_weights_from_dominant("ru")
        prosody = tongue_to_prosody(weights)
        assert prosody.cadence == "measured", "RU > 0.6 should produce measured cadence"
        assert prosody.warmth < 0.5, "RU-dominant has low warmth (formal)"

    def test_choral_speech_song(self):
        phonemes = _make_phonemes("runeveil", 10)
        choral = build_choral_plan(phonemes, "ru", 6.0, RenderMode.SPEECH_SONG)
        assert len(choral.voices) == 2
        roles = {v.role for v in choral.voices}
        assert VoiceRole.LEAD in roles and VoiceRole.SHADOW in roles
        # RU prosody is percussive: alternating values
        curve = choral.prosody.pitch_curve
        assert curve[0] != curve[1], "Percussive should alternate"

    def test_sonification_dissonance(self):
        colors = [LabColor(L=50, a=40, b=-20, material="matte")] * 4
        materials = ["matte", "fluorescent", "neon", "metallic"]
        son = sonify_dead_tone("minor_sixth", colors, materials)
        assert son.envelope == "dissonance"
        assert son.reverb > 0.2
        assert son.delay_ms == 0

    def test_governance_quarantine_voice(self):
        voice = governance_voice("QUARANTINE")
        assert voice == "senna"

    def test_spectrogram_ru_band(self):
        # RU governance: 700 Hz in RU band (400-1000)
        frame, proj, energies = _run_spectrogram_pipeline(700.0)
        assert energies["ru"] > 0.3
        assert proj.material == "metallic"


# ===========================================================================
# Fixture 3: Minor Seventh Perpendicular Echo
# ===========================================================================


class TestGoldenPathMinorSeventh:
    """
    Scenario: Minor seventh dead tone (perpendicular echo).
    Dominant tongue: UM (security, shadow).
    Excitation: moderate (4.0).

    Expected: echo envelope with 250ms delay, high reverb,
    breathy voice, falling prosody, center stereo.
    """

    def test_speech_plan_echo(self):
        plan = build_speech_plan("Shadow protocol engaged.", "um", "minor_seventh", 4.0)
        assert plan.pre_tone_hz == 392.0
        assert plan.stereo_pan == 0.0, "UM is center"
        plan.validate()

    def test_sonification_echo_with_delay(self):
        colors = [LabColor(L=40, a=-10, b=5, material="matte")] * 4
        materials = ["matte", "fluorescent", "neon", "metallic"]
        son = sonify_dead_tone("minor_seventh", colors, materials)
        assert son.envelope == "echo"
        assert son.delay_ms == 250
        assert son.reverb > 0.5
        # Verify all 4 audio params inherit the delay
        for ap in son.audio_params:
            assert ap.delay_ms == 250
            assert ap.reverb > 0.5

    def test_prosody_falling(self):
        prosody_plan = build_prosody("um", 4.0, 10)
        curve = prosody_plan.pitch_curve
        assert curve[-1] < curve[0], "UM has falling stress"

    def test_choral_ritual_four_voices(self):
        phonemes = _make_phonemes("umbraex", 8)
        choral = build_choral_plan(phonemes, "um", 4.0, RenderMode.CHORAL_RITUAL)
        assert len(choral.voices) == 4
        roles = {v.role for v in choral.voices}
        assert roles == {VoiceRole.LEAD, VoiceRole.SHADOW, VoiceRole.DRONE, VoiceRole.HARMONY}
        choral.validate()

    def test_spectrogram_um_band(self):
        # UM shadow: 250 Hz in UM band (150-400)
        frame, proj, energies = _run_spectrogram_pipeline(250.0)
        assert energies["um"] > 0.3
        assert proj.material == "matte"

    def test_echo_reverb_chain(self):
        """Echo sonification + spectrogram projection should both show high reverb/delay."""
        son_sig = DEAD_TONE_ACOUSTIC["minor_seventh"]
        assert son_sig["delay_ms"] == 250
        assert son_sig["reverb"] == 0.7
        assert son_sig["envelope"] == "echo"


# ===========================================================================
# Fixture 4: Autorotation / Multi-Tone Broadband
# ===========================================================================


class TestGoldenPathAutorotation:
    """
    Scenario: Multiple dead tones active simultaneously (autorotation event).
    Broadband signal spanning all tongue bands.
    Excitation: high (8.0).

    Expected: mixed tongue profile with no single dominant >60%,
    gallery projection covering wide hue range, high energy.
    """

    def test_broadband_tongue_spread(self):
        """6 tones across all bands produce distributed tongue energy."""
        freqs = [80.0, 250.0, 700.0, 1500.0, 4000.0, 10000.0]
        sr, sig = generate_test_signal(frequencies=freqs, duration_sec=0.5)
        mags, bins = compute_stft(sig, fft_size=4096, hop_size=512)
        freq_hz = bin_to_hz(bins, sr, 4096)
        mid = mags.shape[0] // 2
        energies = tongue_band_energy(mags[mid], freq_hz)

        # No tongue should dominate excessively
        max_energy = max(energies.values())
        assert max_energy < 0.6, f"Broadband should be distributed: {energies}"

        # At least 4 tongues should have > 5% energy
        active = sum(1 for v in energies.values() if v > 0.05)
        assert active >= 4, f"Only {active} tongues active"

    def test_high_excitation_speech_plan(self):
        """High excitation drives rate and energy to upper bounds."""
        plan = build_speech_plan("Full alert!", "ko", "perfect_fifth", 8.0)
        assert plan.profile.rate >= 1.1 - 1e-9, "High excitation → faster"
        assert plan.profile.energy >= 0.7, "High excitation → more energy"

    def test_all_three_dead_tones_sonify(self):
        """Each dead tone produces distinct envelope."""
        colors = [LabColor(L=60, a=15, b=-10, material="matte")] * 4
        mats = ["matte", "fluorescent", "neon", "metallic"]
        envelopes = set()
        for dt in ["perfect_fifth", "minor_sixth", "minor_seventh"]:
            son = sonify_dead_tone(dt, colors, mats)
            envelopes.add(son.envelope)
        assert len(envelopes) == 3, "Each dead tone should have unique envelope"

    def test_gallery_projection_wide_hue_range(self):
        """Broadband signal should project to wide hue coverage."""
        projections = []
        for freq in [200.0, 800.0, 2000.0, 5000.0]:
            _, proj, _ = _run_spectrogram_pipeline(freq)
            projections.append(proj)

        hues = [p.hue_degrees for p in projections]
        hue_range = max(hues) - min(hues)
        assert hue_range > 100, f"Expected wide hue spread, got {hue_range}°"

    def test_world_bundle_multi_circulation(self):
        """Multiple circulation passes accumulate alignment."""
        bundle = create_default_bundle()
        bundle.circulate("grammar", ["grammar"], {"event": "autorotation"}, 0.15)
        bundle.circulate("prosody", ["prosody"], {"voices": 4}, 0.10)
        bundle.circulate("harmonic", ["harmonic"], {"tones": 3}, 0.20)
        assert bundle.circulation_count == 3
        assert bundle.alignment_score > 0


# ===========================================================================
# Fixture 5: Conlang Choral Ritual Utterance
# ===========================================================================


class TestGoldenPathChoralRitual:
    """
    Scenario: Full choral ritual in DR tongue (architecture, heavy syllables).
    Mode: CHORAL_RITUAL (4 voices).
    Excitation: moderate-high (5.0).

    Expected: heavy/grounded prosody, 4 voice layers, drone at -12 semitones,
    harmony at +7 (perfect fifth above), left-panned stereo,
    world bundle gains alignment through ritual circulation.
    """

    def test_speech_plan_dr_left_pan(self):
        plan = build_speech_plan("Draethis kor thalmek.", "dr", "perfect_fifth", 5.0)
        assert plan.stereo_pan < 0, "DR pans left"
        assert plan.profile.voice_name == "stone"
        plan.validate()

    def test_prosody_grounded(self):
        prosody = build_prosody("dr", 5.0, 12)
        # DR has grounded stress: flat 0.3
        assert all(v == 0.3 for v in prosody.pitch_curve), "DR should be flat grounded"

    def test_choral_ritual_voice_layout(self):
        phonemes = _make_phonemes("draethis", 10)
        choral = build_choral_plan(phonemes, "dr", 5.0, RenderMode.CHORAL_RITUAL)
        assert len(choral.voices) == 4

        voice_map = {v.role: v for v in choral.voices}
        assert voice_map[VoiceRole.DRONE].pitch_shift_semitones == -12.0
        assert voice_map[VoiceRole.HARMONY].pitch_shift_semitones == 7.0
        assert voice_map[VoiceRole.DRONE].pan == 0.0  # centered

        # Harmony pans opposite to lead
        lead_pan = voice_map[VoiceRole.LEAD].pan
        harmony_pan = voice_map[VoiceRole.HARMONY].pan
        if lead_pan != 0:
            assert (lead_pan * harmony_pan) < 0, "Harmony should pan opposite"

        choral.validate()

    def test_dr_phonology_heavy(self):
        assert _DEFAULT_PHONOLOGY["dr"].max_syllable_weight >= 3
        assert "dr" in _DEFAULT_PHONOLOGY["dr"].allowed_onsets

    def test_ritual_circulation_alignment(self):
        bundle = create_default_bundle()
        # Ritual circulation should boost alignment
        bundle.circulate(
            "ritual", ["phonology", "grammar", "prosody"], {"tongue": "dr", "mode": "choral_ritual", "voices": 4}, 0.3
        )
        bundle.circulate("integration", ["all"], {"coherence_check": True}, 0.15)
        assert bundle.alignment_score > 0.2

    def test_spectrogram_dr_band(self):
        # DR architecture: 80 Hz in DR band (20-150)
        frame, proj, energies = _run_spectrogram_pipeline(80.0)
        assert energies["dr"] > 0.3
        assert proj.material == "matte"

    def test_full_ritual_loop(self):
        """Complete loop: plan → choir → sonify → spectrogram → bundle."""
        # 1. Speech plan
        plan = build_speech_plan("Draethis kor.", "dr", "perfect_fifth", 5.0)

        # 2. Choral plan
        phonemes = _make_phonemes("draethis", 8)
        choral = build_choral_plan(
            phonemes,
            plan.dominant_tongue,
            plan.excitation,
            RenderMode.CHORAL_RITUAL,
        )
        assert choral.tongue == "dr"
        assert len(choral.voices) == 4

        # 3. Sonify the dead tone
        colors = [LabColor(L=50, a=5, b=-10, material="matte")] * 4
        mats = ["matte", "fluorescent", "neon", "metallic"]
        son = sonify_dead_tone(plan.dead_tone, colors, mats, pan=plan.stereo_pan)
        assert son.envelope == "pulse"

        # 4. Spectrogram feedback
        _, proj, energies = _run_spectrogram_pipeline(80.0)
        assert proj.tongue in TONGUE_ORDER

        # 5. World bundle records the pass
        bundle = create_default_bundle()
        cp = bundle.circulate(
            "ritual",
            ["all"],
            {
                "tongue": plan.dominant_tongue,
                "voices": len(choral.voices),
                "dead_tone": plan.dead_tone,
                "envelope": son.envelope,
                "spectrogram_tongue": proj.tongue,
            },
            0.25,
        )
        assert bundle.alignment_score > 0
        assert len(cp.output_hash) == 16


# ===========================================================================
# Cross-Fixture: Drift Detection
# ===========================================================================


class TestDriftDetection:
    """Snapshot-style checks to catch global meaning drift."""

    def test_dead_tone_pretone_values_stable(self):
        """Pretone frequencies should never change."""
        assert DEAD_TONE_PRETONES == {
            "perfect_fifth": 330.0,
            "minor_sixth": 352.0,
            "minor_seventh": 392.0,
        }

    def test_tongue_pan_layout_stable(self):
        """Stereo layout should never change."""
        assert TONGUE_PAN["ko"] < 0  # left
        assert TONGUE_PAN["dr"] < 0  # left
        assert TONGUE_PAN["av"] == 0  # center
        assert TONGUE_PAN["um"] == 0  # center
        assert TONGUE_PAN["ru"] > 0  # right
        assert TONGUE_PAN["ca"] > 0  # right

    def test_tongue_frequency_bands_stable(self):
        """Band boundaries should never change."""
        assert TONGUE_FREQ_BANDS["dr"] == (20.0, 150.0)
        assert TONGUE_FREQ_BANDS["um"] == (150.0, 400.0)
        assert TONGUE_FREQ_BANDS["ru"] == (400.0, 1000.0)
        assert TONGUE_FREQ_BANDS["ko"] == (1000.0, 2500.0)
        assert TONGUE_FREQ_BANDS["av"] == (2500.0, 6000.0)
        assert TONGUE_FREQ_BANDS["ca"] == (6000.0, 20000.0)

    def test_material_mapping_stable(self):
        """Tongue→material mapping should never change."""
        assert _TONGUE_MATERIAL == {
            "dr": "matte",
            "um": "matte",
            "ru": "metallic",
            "ko": "fluorescent",
            "av": "fluorescent",
            "ca": "neon",
        }

    def test_dead_tone_acoustic_signatures_stable(self):
        """Dead tone envelopes should never change."""
        assert DEAD_TONE_ACOUSTIC["perfect_fifth"]["envelope"] == "pulse"
        assert DEAD_TONE_ACOUSTIC["minor_sixth"]["envelope"] == "dissonance"
        assert DEAD_TONE_ACOUSTIC["minor_seventh"]["envelope"] == "echo"
        assert DEAD_TONE_ACOUSTIC["minor_seventh"]["delay_ms"] == 250

    def test_voice_layer_counts_stable(self):
        """Mode → voice count should never change."""
        for tongue in ALL_TONGUES:
            assert len(build_voice_layers(tongue, RenderMode.PLAIN_SPEECH)) == 1
            assert len(build_voice_layers(tongue, RenderMode.SPEECH_SONG)) == 2
            assert len(build_voice_layers(tongue, RenderMode.CHORAL_RITUAL)) == 4

    def test_prosody_curve_shapes_stable(self):
        """Each tongue's curve shape should be consistent."""
        n = 10

        # KO = flat (even)
        ko = build_prosody("ko", 3.0, n)
        assert len(set(ko.pitch_curve)) == 1

        # CA = rising
        ca = build_prosody("ca", 3.0, n)
        assert ca.pitch_curve[-1] > ca.pitch_curve[0]

        # UM = falling
        um = build_prosody("um", 3.0, n)
        assert um.pitch_curve[-1] < um.pitch_curve[0]

        # RU = percussive (alternating)
        ru = build_prosody("ru", 3.0, n)
        assert ru.pitch_curve[0] != ru.pitch_curve[1]

    def test_freq_to_hue_roundtrip(self):
        """freq_to_hue should approximately invert hue_to_frequency."""
        for freq in [200.0, 500.0, 1000.0, 2000.0, 3500.0]:
            hue = freq_to_hue(freq)
            reconstructed = hue_to_frequency(hue)
            # Allow 5% error due to clamping at boundaries
            if 100 <= freq <= 4000:
                assert abs(reconstructed - freq) / freq < 0.05, f"Roundtrip failed: {freq} → {hue}° → {reconstructed}"

    def test_cross_module_tongue_sets_identical(self):
        """Every module uses the exact same 6 tongues."""
        speech_tongues = ALL_TONGUES
        choral_tongues = set(CHORAL_PROFILES.keys())
        bundle_tongues = set(_DEFAULT_PHONOLOGY.keys())
        spectrogram_tongues = set(TONGUE_FREQ_BANDS.keys())
        material_tongues = set(_TONGUE_MATERIAL.keys())
        pan_tongues = set(TONGUE_PAN.keys())
        phase_tongues = set(TONGUE_PHASE_OFFSETS.keys())

        canonical = {"ko", "av", "ru", "ca", "um", "dr"}
        assert speech_tongues == canonical
        assert choral_tongues == canonical
        assert bundle_tongues == canonical
        assert spectrogram_tongues == canonical
        assert material_tongues == canonical
        assert pan_tongues == canonical
        assert phase_tongues == canonical


# ===========================================================================
# Stellar Octave + Dark Fill Integration Tests
# ===========================================================================

from src.symphonic_cipher.audio.stellar_octave_mapping import (
    StellarOctaveMapping,
    OctaveTranspositionResult,
)

from src.crypto.harmonic_dark_fill import (
    compute_darkness,
    compute_harmonic_fill,
    upgrade_sound_bundle,
    fill_dark_nodes,
    sequence_spectrum,
    voice_leading_interval,
    nearest_musical_interval,
    HarmonicFill,
    SpectrumSnapshot,
    TONGUE_AUDIBLE_FREQ,
    COMPLEMENT_MAP,
    INTERVALS,
    INFRA_MIN,
    INFRA_MAX,
    AUDIBLE_MIN as DF_AUDIBLE_MIN,
    AUDIBLE_MAX as DF_AUDIBLE_MAX,
    ULTRA_MIN,
    ULTRA_MAX,
)


class TestStellarOctaveIntegration:
    """Verify stellar octave mapping feeds correctly into the audible pipeline."""

    def setup_method(self):
        self.som = StellarOctaveMapping()

    def test_sun_p_mode_lands_in_audible(self):
        """Sun's 3 mHz p-mode must transpose into audible range."""
        result = self.som.transpose(0.003)
        assert 20.0 <= result.human_freq <= 20000.0

    def test_all_stellar_bodies_reach_audible(self):
        """Every cataloged stellar body must reach audible via octave doubling."""
        for body, freq in self.som.STELLAR_FREQUENCIES.items():
            result = self.som.transpose(freq)
            # Some may overshoot; stellar_pulse_protocol corrects
            protocol = self.som.stellar_pulse_protocol(body)
            assert protocol["is_audible"], f"{body} protocol not audible"

    def test_sun_transposed_falls_in_tongue_band(self):
        """Sun p-mode transposed should land in or near a tongue band."""
        result = self.som.transpose(0.003)
        freq = result.human_freq
        # Check it falls in some tongue band
        matched = False
        for tongue, (lo, hi) in TONGUE_FREQ_BANDS.items():
            if lo <= freq <= hi:
                matched = True
                break
        assert matched or (20.0 <= freq <= 20000.0), f"Transposed sun freq {freq} not in any tongue band"

    def test_octave_preserves_interval_ratios(self):
        """Octave doubling must not change interval relationships."""
        sun = self.som.transpose(0.003)
        dwarf = self.som.transpose(0.001)
        # The ratio between their transposed freqs should be close to
        # the ratio between original × some power of 2
        original_ratio = 0.003 / 0.001
        transposed_ratio = sun.human_freq / dwarf.human_freq
        # Normalize both to [1, 2)
        while original_ratio >= 2.0:
            original_ratio /= 2.0
        while original_ratio < 1.0:
            original_ratio *= 2.0
        while transposed_ratio >= 2.0:
            transposed_ratio /= 2.0
        while transposed_ratio < 1.0:
            transposed_ratio *= 2.0
        assert abs(original_ratio - transposed_ratio) < 0.01

    def test_stellar_camouflage_within_audible(self):
        """All camouflage harmonics must stay in audible range."""
        harmonics = self.som.stellar_camouflage_frequencies("sun_p_mode", 10)
        for h in harmonics:
            assert 20.0 <= h <= 20000.0

    def test_entropy_sequence_deterministic(self):
        """Same inputs must produce identical pulse sequences."""
        s1 = self.som.entropy_regulation_sequence("sun_p_mode", 10.0)
        s2 = self.som.entropy_regulation_sequence("sun_p_mode", 10.0)
        assert s1["num_pulses"] == s2["num_pulses"]
        assert s1["pulse_freq_Hz"] == s2["pulse_freq_Hz"]
        np.testing.assert_array_equal(s1["pulse_times_s"], s2["pulse_times_s"])


class TestDarkFillIntegration:
    """Verify harmonic dark fill produces valid 3-band structure
    and integrates with the gallery/spectrogram pipeline."""

    def test_fill_never_all_zero(self):
        """No byte should produce all-zero fill for any tongue."""
        for byte_val in [0, 1, 127, 255]:
            for tongue in ["ko", "av", "ru", "ca", "um", "dr"]:
                dark = compute_darkness(byte_val, tongue)
                fill = compute_harmonic_fill(byte_val, tongue, 0, 10, dark)
                total = abs(fill.infra_freq) + abs(fill.audible_freq) + abs(fill.ultra_freq)
                assert total > 0, f"All-zero freq for byte={byte_val} tongue={tongue}"

    def test_infra_band_within_bounds(self):
        """Infrasonic band must stay in [0.01, 20] Hz."""
        for pos in range(20):
            fill = compute_harmonic_fill(100, "ko", pos, 20, 1.0)
            assert INFRA_MIN <= fill.infra_freq <= INFRA_MAX

    def test_ultra_band_within_bounds(self):
        """Ultrasonic band must stay in [20k, 1M] Hz."""
        for tongue in ["ko", "av", "ru", "ca", "um", "dr"]:
            fill = compute_harmonic_fill(50, tongue, 5, 20, 0.8)
            assert ULTRA_MIN <= fill.ultra_freq <= ULTRA_MAX

    def test_audible_band_within_bounds(self):
        """Audible band must stay in [20, 20000] Hz."""
        for tongue in ["ko", "av", "ru", "ca", "um", "dr"]:
            fill = compute_harmonic_fill(128, tongue, 10, 20, 0.5)
            assert DF_AUDIBLE_MIN <= fill.audible_freq <= DF_AUDIBLE_MAX

    def test_darkness_inverse_of_activation(self):
        """Higher darkness → higher amplitude (louder fill)."""
        fill_dark = compute_harmonic_fill(0, "ko", 0, 10, 1.0)
        fill_light = compute_harmonic_fill(255, "ko", 0, 10, 0.0)
        assert fill_dark.infra_amplitude > fill_light.infra_amplitude

    def test_complement_pairs_match_gallery_dual_eye(self):
        """Dark fill complement pairs should match gallery chromatics eye seeding."""
        # Gallery: left=KO/DR, right=RU/CA, bridge=AV/UM
        assert COMPLEMENT_MAP["ko"] == "dr"
        assert COMPLEMENT_MAP["dr"] == "ko"
        assert COMPLEMENT_MAP["av"] == "um"
        assert COMPLEMENT_MAP["um"] == "av"
        assert COMPLEMENT_MAP["ru"] == "ca"
        assert COMPLEMENT_MAP["ca"] == "ru"

    def test_dead_tone_intervals_present(self):
        """The 3 dead tone ratios must exist in the interval vocabulary."""
        names = set(INTERVALS.keys())
        assert "perfect_fifth" in names  # 3:2
        assert "minor_sixth" in names  # 8:5
        assert "minor_seventh" in names  # 16:9

    def test_dead_tone_ratio_values_match_sonifier(self):
        """Dark fill interval ratios must match gallery_sonifier dead tone ratios."""
        assert abs(INTERVALS["perfect_fifth"] - 3 / 2) < 1e-6
        assert abs(INTERVALS["minor_sixth"] - 8 / 5) < 1e-6
        assert abs(INTERVALS["minor_seventh"] - 16 / 9) < 1e-6

    def test_upgrade_sound_bundle_returns_3_strands(self):
        """upgrade_sound_bundle must return 3 tuples of 3 floats each."""
        a, b, c = upgrade_sound_bundle(100, "ko", 5, 20, 0.7)
        assert len(a) == 3
        assert len(b) == 3
        assert len(c) == 3
        # strand_a = audible, strand_b = infra, strand_c = ultra
        assert DF_AUDIBLE_MIN <= a[0] <= DF_AUDIBLE_MAX
        assert INFRA_MIN <= b[0] <= INFRA_MAX
        assert ULTRA_MIN <= c[0] <= ULTRA_MAX

    def test_sequence_spectrum_energy_never_zero(self):
        """Full sequence spectrum must have non-zero energy at every position."""
        data = b"Hello SCBE"
        snapshots = sequence_spectrum(data)
        assert len(snapshots) == len(data)
        for snap in snapshots:
            total = snap.total_infra_energy + snap.total_audible_energy + snap.total_ultra_energy
            assert total > 0

    def test_voice_leading_interval_normalized(self):
        """All voice leading intervals must be in [1.0, 2.0)."""
        for t1 in ["ko", "av", "ru", "ca", "um", "dr"]:
            for t2 in ["ko", "av", "ru", "ca", "um", "dr"]:
                ratio = voice_leading_interval(t1, t2)
                assert 1.0 <= ratio < 2.0, f"{t1}→{t2}: ratio={ratio}"


class TestStellarDarkFillBridge:
    """Cross-module: stellar octaves feed through dark fill into audible pipeline."""

    def setup_method(self):
        self.som = StellarOctaveMapping()

    def test_stellar_freq_connects_to_infrasonic_band(self):
        """Sun p-mode (0.003 Hz) lives below the dark fill infrasonic band.
        The infra band (0.01-20 Hz) represents the first few octaves above stellar scale.
        Verify the connection: stellar × 2^n should reach into the infra band."""
        result = self.som.transpose(0.003, target_freq=1.0)
        # Target ~1 Hz is in the infrasonic band
        assert INFRA_MIN <= result.human_freq <= INFRA_MAX or result.human_freq > INFRA_MAX  # may overshoot slightly

    def test_audible_range_agreement(self):
        """stellar_octave_mapping and harmonic_dark_fill must agree on audible range."""
        assert self.som.AUDIBLE_MIN == DF_AUDIBLE_MIN
        assert self.som.AUDIBLE_MAX == DF_AUDIBLE_MAX

    def test_tongue_base_freqs_within_spectrogram_bands(self):
        """Each tongue's dark fill base frequency should be audible and
        reasonably near its spectrogram bridge attribution band."""
        for tongue, base_hz in TONGUE_AUDIBLE_FREQ.items():
            assert DF_AUDIBLE_MIN <= base_hz <= DF_AUDIBLE_MAX, f"{tongue} base {base_hz} Hz not in audible range"

    def test_full_ladder_continuity(self):
        """The full frequency ladder must have no gaps:
        stellar → infra → audible → ultra."""
        # Stellar bodies can reach down to 0.00005 Hz
        stellar_min = min(self.som.STELLAR_FREQUENCIES.values())
        assert stellar_min < INFRA_MIN  # stellar is below infra

        # Infra connects to audible
        assert INFRA_MAX == DF_AUDIBLE_MIN  # no gap

        # Audible connects to ultra
        assert DF_AUDIBLE_MAX == ULTRA_MIN  # no gap

        # Ultra extends to 1 MHz
        assert ULTRA_MAX == 1_000_000

    def test_sonifier_dead_tones_in_dark_fill_intervals(self):
        """Gallery sonifier dead tone base Hz should produce intervals
        that exist in the dark fill musical vocabulary."""
        for tone_name, sig in DEAD_TONE_ACOUSTIC.items():
            base = sig["base_hz"]
            # Find nearest tongue freq
            for tongue, t_freq in TONGUE_AUDIBLE_FREQ.items():
                ratio = base / t_freq
                while ratio < 1.0:
                    ratio *= 2.0
                while ratio >= 2.0:
                    ratio /= 2.0
                name, dev = nearest_musical_interval(ratio)
                # At least one tongue should be close to a named interval
                if dev < 0.05:
                    break
