"""
Tests for Speech Render Plan, Choral Render, and World Bundle
==============================================================

Covers:
    - Speech plan builds for all 6 tongues
    - Excitation modulation of rate and energy
    - Dead tone → pre-tone frequency mapping
    - Stereo pan follows dual-iris layout
    - Profile bounds validation
    - Tongue acoustic profiles (all 6 present, rates reasonable, chant bounded)
    - Choral voice layering (plain/song/ritual mode counts)
    - Prosody curve shapes per stress pattern
    - World bundle creation, circulation, alignment score
    - Phonology profiles per tongue
"""

import sys

sys.path.insert(0, ".")

from src.crypto.speech_render_plan import (
    build_speech_plan,
    DEAD_TONE_PRETONES,
    ALL_TONGUES,
)

from src.crypto.choral_render import (
    PROFILES as CHORAL_PROFILES,
    PhonemeToken,
    VoiceRole,
    RenderMode,
    build_prosody,
    build_voice_layers,
    build_choral_plan,
)

from src.crypto.world_bundle import (
    OntologyEntry,
    LexiconEntry,
    GrammarRule,
    create_default_bundle,
    _DEFAULT_PHONOLOGY,
)

# ===========================================================================
# Speech Render Plan
# ===========================================================================


class TestSpeechPlanBuilds:
    """Every tongue produces a valid plan."""

    def test_all_tongues_build(self):
        for tongue in ALL_TONGUES:
            plan = build_speech_plan("test", tongue, "perfect_fifth", 3.0)
            assert plan.dominant_tongue == tongue
            assert plan.text == "test"

    def test_plan_validates(self):
        plan = build_speech_plan("hello", "ko", "minor_sixth", 4.0)
        plan.validate()  # should not raise

    def test_dead_tone_pretones(self):
        for dt, hz in DEAD_TONE_PRETONES.items():
            plan = build_speech_plan("x", "ko", dt, 3.0)
            assert plan.pre_tone_hz == hz

    def test_unknown_dead_tone_no_pretone(self):
        plan = build_speech_plan("x", "ko", "unknown_tone", 3.0)
        assert plan.pre_tone_hz is None


class TestExcitationModulation:
    """Excitation drives rate and energy."""

    def test_rate_increases_with_excitation(self):
        low = build_speech_plan("x", "av", "perfect_fifth", 1.0)
        high = build_speech_plan("x", "av", "perfect_fifth", 8.0)
        assert high.profile.rate > low.profile.rate

    def test_energy_increases_with_excitation(self):
        low = build_speech_plan("x", "ru", "minor_sixth", 0.0)
        high = build_speech_plan("x", "ru", "minor_sixth", 10.0)
        assert high.profile.energy > low.profile.energy

    def test_rate_clamped(self):
        plan = build_speech_plan("x", "ca", "perfect_fifth", 100.0)
        assert 0.7 <= plan.profile.rate <= 1.3

    def test_energy_clamped(self):
        plan = build_speech_plan("x", "um", "minor_seventh", 100.0)
        assert 0.0 <= plan.profile.energy <= 1.0


class TestStereoPan:
    """Pan follows dual-iris seed structure."""

    def test_left_eye_pans_left(self):
        for tongue in ("ko", "dr"):
            plan = build_speech_plan("x", tongue, "perfect_fifth", 3.0)
            assert plan.stereo_pan < 0, f"{tongue} should pan left"

    def test_right_eye_pans_right(self):
        for tongue in ("ru", "ca"):
            plan = build_speech_plan("x", tongue, "perfect_fifth", 3.0)
            assert plan.stereo_pan > 0, f"{tongue} should pan right"

    def test_bridge_centered(self):
        for tongue in ("av", "um"):
            plan = build_speech_plan("x", tongue, "perfect_fifth", 3.0)
            assert plan.stereo_pan == 0.0, f"{tongue} should be center"


class TestDistinctDeadTones:
    """Each dead tone maps to a unique pre-tone."""

    def test_all_pretones_distinct(self):
        plans = [build_speech_plan("x", "ko", dt, 3.0) for dt in DEAD_TONE_PRETONES]
        pretones = {p.pre_tone_hz for p in plans}
        assert len(pretones) == 3


class TestProfileBounds:
    """Voice profile parameters stay in valid ranges across all tongues and excitations."""

    def test_all_profiles_valid(self):
        for tongue in ALL_TONGUES:
            for exc in [0.0, 1.0, 3.0, 6.0, 10.0, 50.0]:
                plan = build_speech_plan("x", tongue, "perfect_fifth", exc)
                assert 0.5 <= plan.profile.rate <= 2.0
                assert 0.0 <= plan.profile.energy <= 1.0
                assert 0.0 <= plan.profile.breathiness <= 1.0
                assert plan.profile.pause_ms >= 0


# ===========================================================================
# Choral Render
# ===========================================================================


class TestTongueAcousticProfiles:
    """All 6 tongues present with valid profiles."""

    def test_all_tongues_present(self):
        assert set(CHORAL_PROFILES.keys()) == {"ko", "av", "ru", "ca", "um", "dr"}

    def test_rates_reasonable(self):
        for profile in CHORAL_PROFILES.values():
            assert 0.6 <= profile.speech_rate <= 1.3

    def test_chant_ratio_bounded(self):
        for profile in CHORAL_PROFILES.values():
            assert 0.0 <= profile.chant_ratio <= 1.0

    def test_unique_styles(self):
        styles = {p.syllable_style for p in CHORAL_PROFILES.values()}
        assert len(styles) == 6, "Each tongue should have a unique syllable style"


class TestProsodyBuilder:
    """Prosody curves shaped by tongue stress patterns."""

    def _phonemes(self, n=10):
        return [PhonemeToken("a", "a", 100, 0.5) for _ in range(n)]

    def test_rising_curve_ascends(self):
        prosody = build_prosody("ca", 3.0, 10)
        assert prosody.pitch_curve[-1] > prosody.pitch_curve[0]

    def test_falling_curve_descends(self):
        prosody = build_prosody("um", 3.0, 10)
        assert prosody.pitch_curve[-1] < prosody.pitch_curve[0]

    def test_percussive_alternates(self):
        prosody = build_prosody("ru", 3.0, 10)
        # Even indices should differ from odd
        assert prosody.pitch_curve[0] != prosody.pitch_curve[1]

    def test_even_is_flat(self):
        prosody = build_prosody("ko", 3.0, 10)
        assert len(set(prosody.pitch_curve)) == 1, "even stress should be flat"

    def test_prosody_validates(self):
        prosody = build_prosody("av", 5.0, 8)
        prosody.validate()

    def test_pause_points_exist(self):
        prosody = build_prosody("dr", 3.0, 20)
        assert len(prosody.pause_points) > 0


class TestVoiceLayers:
    """Render mode determines voice count."""

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

    def test_all_gains_valid(self):
        for tongue in CHORAL_PROFILES:
            for mode in RenderMode:
                voices = build_voice_layers(tongue, mode)
                for v in voices:
                    assert 0.0 <= v.gain <= 1.0
                    assert -1.0 <= v.pan <= 1.0


class TestChoralPlan:
    """Full choral plan assembly."""

    def _phonemes(self, n=6):
        return [PhonemeToken("t", "t", 80, 0.6) for _ in range(n)]

    def test_plain_plan_builds(self):
        plan = build_choral_plan(self._phonemes(), "ko", 3.0, RenderMode.PLAIN_SPEECH)
        assert len(plan.voices) == 1
        assert plan.tongue == "ko"
        assert plan.mode == RenderMode.PLAIN_SPEECH

    def test_choral_plan_builds(self):
        plan = build_choral_plan(self._phonemes(), "ca", 5.0, RenderMode.CHORAL_RITUAL)
        assert len(plan.voices) == 4
        plan.validate()

    def test_prosody_matches_tongue(self):
        plan = build_choral_plan(self._phonemes(), "um", 2.0)
        # UM has falling stress
        assert plan.prosody.pitch_curve[-1] < plan.prosody.pitch_curve[0]


# ===========================================================================
# World Bundle
# ===========================================================================


class TestWorldBundleCreation:
    """Default bundle comes with 6 tongue phonologies and 3 render presets."""

    def test_default_has_all_tongues(self):
        bundle = create_default_bundle()
        assert bundle.tongue_count == 6
        assert set(bundle.phonology.keys()) == {"ko", "av", "ru", "ca", "um", "dr"}

    def test_default_has_render_presets(self):
        bundle = create_default_bundle()
        assert len(bundle.render_presets) == 3
        modes = {p.mode for p in bundle.render_presets}
        assert modes == {"speech", "speech_song", "choral_ritual"}

    def test_empty_vocabulary_and_rules(self):
        bundle = create_default_bundle()
        assert bundle.total_vocabulary == 0
        assert bundle.total_rules == 0

    def test_initial_alignment_zero(self):
        bundle = create_default_bundle()
        assert bundle.alignment_score == 0.0

    def test_to_dict_complete(self):
        bundle = create_default_bundle()
        d = bundle.to_dict()
        assert "bundle_version" in d
        assert "tongue_count" in d
        assert "sections" in d
        assert d["tongue_count"] == 6


class TestPhonologyProfiles:
    """Each tongue has distinct phonological constraints."""

    def test_all_tongues_have_phonology(self):
        for tongue in ("ko", "av", "ru", "ca", "um", "dr"):
            assert tongue in _DEFAULT_PHONOLOGY

    def test_vowel_inventories_differ(self):
        inventories = {t: frozenset(p.vowel_inventory) for t, p in _DEFAULT_PHONOLOGY.items()}
        # At least 4 distinct vowel sets
        unique = len(set(inventories.values()))
        assert unique >= 4, f"Only {unique} distinct vowel sets"

    def test_stress_rules_vary(self):
        rules = {p.stress_rule for p in _DEFAULT_PHONOLOGY.values()}
        assert len(rules) >= 3, "Need variety in stress rules"

    def test_dr_has_heavy_syllables(self):
        assert _DEFAULT_PHONOLOGY["dr"].max_syllable_weight >= 3

    def test_um_allows_null_onset(self):
        assert "" in _DEFAULT_PHONOLOGY["um"].allowed_onsets


class TestCirculation:
    """Chi circulation passes accumulate and track alignment."""

    def test_single_pass(self):
        bundle = create_default_bundle()
        cp = bundle.circulate("grammar", ["grammar", "lexicon"], {"rule": "SOV"}, 0.1)
        assert bundle.circulation_count == 1
        assert cp.method == "grammar"
        assert len(cp.output_hash) == 16

    def test_alignment_accumulates(self):
        bundle = create_default_bundle()
        bundle.circulate("grammar", ["grammar"], {}, 0.2)
        bundle.circulate("prosody", ["prosody"], {}, 0.3)
        bundle.circulate("harmonic", ["harmonic"], {}, 0.1)
        assert bundle.alignment_score > 0

    def test_negative_alignment_possible(self):
        bundle = create_default_bundle()
        bundle.circulate("adversarial", ["all"], {}, -0.5)
        assert bundle.alignment_score < 0

    def test_alignment_clamped(self):
        bundle = create_default_bundle()
        for _ in range(100):
            bundle.circulate("integration", ["all"], {}, 1.0)
        assert bundle.alignment_score <= 1.0

    def test_different_outputs_different_hashes(self):
        bundle = create_default_bundle()
        cp1 = bundle.circulate("grammar", ["grammar"], {"a": 1}, 0.1)
        cp2 = bundle.circulate("grammar", ["grammar"], {"a": 2}, 0.1)
        assert cp1.output_hash != cp2.output_hash

    def test_pass_has_timestamp(self):
        bundle = create_default_bundle()
        import time

        before = time.time()
        cp = bundle.circulate("ritual", ["ritual"], {}, 0.0)
        after = time.time()
        assert before <= cp.timestamp <= after


class TestBundlePopulation:
    """Adding vocabulary, grammar, and ontology."""

    def test_add_lexicon(self):
        bundle = create_default_bundle()
        bundle.lexicon["ko"].append(
            LexiconEntry(
                tongue="ko",
                word="kor",
                ipa="koɹ",
                meaning="intent",
                part_of_speech="noun",
                syllable_count=1,
            )
        )
        assert bundle.total_vocabulary == 1

    def test_add_grammar_rule(self):
        bundle = create_default_bundle()
        bundle.grammar["ru"].append(
            GrammarRule(
                tongue="ru",
                rule_id="ru_001",
                description="Subject-Object-Verb order",
                pattern="SOV",
                example="ru kor drak",
            )
        )
        assert bundle.total_rules == 1

    def test_add_ontology(self):
        bundle = create_default_bundle()
        bundle.ontology.append(
            OntologyEntry(
                concept_id="C001",
                name="governance",
                tongue_affinity="ru",
                description="rules and policy",
            )
        )
        assert len(bundle.ontology) == 1


# ===========================================================================
# Cross-Module Integration
# ===========================================================================


class TestCrossModuleCoherence:
    """Speech, choral, and world bundle share consistent tongue set."""

    def test_same_tongue_set(self):
        speech_tongues = ALL_TONGUES
        choral_tongues = set(CHORAL_PROFILES.keys())
        bundle_tongues = set(_DEFAULT_PHONOLOGY.keys())
        assert speech_tongues == choral_tongues == bundle_tongues

    def test_speech_feeds_choral(self):
        """A speech plan's tongue can drive a choral plan."""
        plan = build_speech_plan("test", "ca", "minor_sixth", 4.0)
        phonemes = [PhonemeToken("t", "t", 100, 0.5) for _ in range(5)]
        choral = build_choral_plan(
            phonemes,
            plan.dominant_tongue,
            plan.excitation,
            RenderMode.CHORAL_RITUAL,
        )
        assert choral.tongue == plan.dominant_tongue
        assert len(choral.voices) == 4
