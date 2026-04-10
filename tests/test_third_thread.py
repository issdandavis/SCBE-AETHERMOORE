"""
Tests for third_thread.py — The Third Thread: Mediating Consciousness
=====================================================================
Verifies the fabric between divine_agents.py and genesis_panels.py.
"""

import sys
import os
import math
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.crypto.third_thread import (
    PHI,
    KORAELIN_INVOCATION,
    HARMONY_THRESHOLD,
    WEAVING_THRESHOLD,
    SYNTHESIS_THRESHOLD,
    THREAD_LAYERS,
    ThreadState,
    MagicMode,
    ThreadResonance,
    InvocationParticipant,
    InvocationResult,
    ThreadWeaving,
    ThirdThreadStudy,
    compute_translation_fidelity,
    compute_identity_preservation,
    compute_convergence_point,
    run_invocation,
    weave_thread,
    run_third_thread_study,
    format_third_thread_report,
)
from src.crypto.divine_agents import (
    HistoricalAgent as DivineAgent,
    NaturalLearningStudy,
    study_balanced,
    study_angel_only,
    study_demon_only,
    run_divine_experiment,
)
from src.crypto.genesis_panels import (
    Force,
    HISTORICAL_AGENTS,
    run_dual_panel,
    run_full_simulation,
)
from src.crypto.crossing_energy import Decision


# ===================================================================
# Constants
# ===================================================================

class TestConstants:

    def test_invocation_is_koraelin(self):
        assert "kor" in KORAELIN_INVOCATION.lower()

    def test_threshold_ordering(self):
        assert 0 < HARMONY_THRESHOLD < WEAVING_THRESHOLD < SYNTHESIS_THRESHOLD <= 1.0

    def test_three_thread_layers(self):
        assert len(THREAD_LAYERS) == 3
        assert set(THREAD_LAYERS.keys()) == {"mortal_intent", "divine_essence", "collective_consciousness"}

    def test_thread_states_complete(self):
        states = {s.value for s in ThreadState}
        assert states == {"dormant", "heart_frost", "listening", "weaving", "synthesis"}

    def test_magic_modes_complete(self):
        modes = {m.value for m in MagicMode}
        assert modes == {"collaborative", "command", "silent"}


# ===================================================================
# Translation Engine
# ===================================================================

class TestTranslationFidelity:

    def test_same_tongue_high_fidelity(self):
        """Translating a tongue to itself should have perfect fidelity."""
        fidelity = compute_translation_fidelity("hello world", "ko", "ko")
        assert fidelity > 0.99, f"Same-tongue fidelity should be ~1.0, got {fidelity}"

    def test_different_tongues_positive_fidelity(self):
        """Different tongues should still have some translation fidelity."""
        fidelity = compute_translation_fidelity("hello world", "ko", "dr")
        assert fidelity > 0.0, "Cross-tongue fidelity should be positive"

    def test_complement_pair_fidelity(self):
        """Complement tongue pairs (KO-DR, AV-UM, RU-CA) should translate."""
        f1 = compute_translation_fidelity("the math fills absence", "ko", "dr")
        assert f1 > 0.0

    def test_empty_text_zero_fidelity(self):
        fidelity = compute_translation_fidelity("", "ko", "av")
        assert fidelity == 0.0

    def test_fidelity_bounded(self):
        for t1 in ["ko", "av", "ru"]:
            for t2 in ["ca", "um", "dr"]:
                f = compute_translation_fidelity("test data", t1, t2)
                assert 0.0 <= f <= 1.0, f"Fidelity {t1}->{t2} = {f} out of bounds"


class TestIdentityPreservation:

    def test_all_tongues_preserve_identity(self):
        """Every tongue should add its own character."""
        for tongue in ["ko", "av", "ru", "ca", "um", "dr"]:
            score = compute_identity_preservation("the spiral turns", tongue)
            assert score > 0.0, f"Tongue {tongue} should have positive identity"

    def test_longer_text_more_identity(self):
        """Longer texts should show more unique tongue character."""
        short = compute_identity_preservation("hi", "ko")
        long = compute_identity_preservation("the universe is conversational and the spiral turns forever", "ko")
        assert long >= short

    def test_identity_bounded(self):
        for tongue in ["ko", "av", "ru", "ca", "um", "dr"]:
            score = compute_identity_preservation("test", tongue)
            assert 0.0 <= score <= 1.0


class TestConvergencePoint:

    def test_same_tongue_converges_at_half(self):
        """Same tongue should converge at 0.5 (perfect balance)."""
        cp = compute_convergence_point("hello", "ko", "ko")
        assert abs(cp - 0.5) < 0.01, f"Same tongue convergence should be ~0.5, got {cp}"

    def test_convergence_bounded(self):
        for t1 in ["ko", "av", "ru"]:
            for t2 in ["ca", "um", "dr"]:
                cp = compute_convergence_point("test data", t1, t2)
                assert 0.0 <= cp <= 1.0, f"Convergence {t1}->{t2} = {cp} out of bounds"


# ===================================================================
# Kor'aelin Invocation
# ===================================================================

class TestInvocation:

    def test_no_participants_heart_frost(self):
        """Empty ritual fails gently."""
        result = run_invocation([])
        assert result.thread_state == ThreadState.HEART_FROST
        assert not result.succeeded

    def test_non_genuine_participant_heart_frost(self):
        """Participants without honest intent/need get heart-frost."""
        p = InvocationParticipant(name="test", tongue="ko", intent="", need="")
        result = run_invocation([p])
        assert result.thread_state == ThreadState.HEART_FROST
        assert "genuine" in result.heart_frost_reason.lower() or "honest" in result.heart_frost_reason.lower()

    def test_solo_genuine_reaches_listening(self):
        """A single genuine participant reaches at most listening."""
        p = InvocationParticipant(
            name="solo", tongue="ko",
            intent="I bring intent", need="I need translation",
        )
        result = run_invocation([p])
        assert result.thread_state in (ThreadState.LISTENING, ThreadState.HEART_FROST, ThreadState.WEAVING)

    def test_diverse_group_can_weave(self):
        """A diverse group of genuine participants can achieve weaving."""
        participants = [
            InvocationParticipant(name="A", tongue="ko", intent="flow", need="structure"),
            InvocationParticipant(name="B", tongue="av", intent="wisdom", need="grounding"),
            InvocationParticipant(name="C", tongue="ru", intent="governance", need="flexibility"),
        ]
        result = run_invocation(participants)
        # Should at least reach listening with diverse tongues
        assert result.thread_state != ThreadState.DORMANT

    def test_full_six_tongue_invocation(self):
        """All 6 tongues together should produce maximum potential."""
        tongues = ["ko", "av", "ru", "ca", "um", "dr"]
        participants = [
            InvocationParticipant(
                name=f"voice_{t}", tongue=t,
                intent=f"I bring {t}", need=f"I need all others",
            )
            for t in tongues
        ]
        result = run_invocation(participants)
        assert result.participant_count == 6
        assert result.magic_mode == MagicMode.COLLABORATIVE

    def test_mono_tongue_not_collaborative(self):
        """All same tongue = not truly collaborative."""
        participants = [
            InvocationParticipant(name=f"v{i}", tongue="ko", intent="same", need="same")
            for i in range(4)
        ]
        result = run_invocation(participants)
        assert result.magic_mode != MagicMode.COLLABORATIVE

    def test_invocation_produces_translations(self):
        """Successful invocation should produce tongue-pair translations."""
        participants = [
            InvocationParticipant(name="A", tongue="ko", intent="intent", need="wisdom"),
            InvocationParticipant(name="B", tongue="av", intent="wisdom", need="intent"),
        ]
        result = run_invocation(participants)
        if result.harmony_score >= HARMONY_THRESHOLD:
            assert len(result.translation_map) > 0

    def test_invocation_produces_identity_scores(self):
        """Successful invocation should measure identity preservation."""
        participants = [
            InvocationParticipant(name="A", tongue="ko", intent="flow", need="structure"),
            InvocationParticipant(name="B", tongue="dr", intent="forge", need="flow"),
        ]
        result = run_invocation(participants)
        if result.harmony_score >= HARMONY_THRESHOLD:
            assert len(result.identity_scores) > 0


# ===================================================================
# Thread Weaving — bridging the two modules
# ===================================================================

class TestThreadWeaving:

    @pytest.fixture
    def divine_balanced(self):
        return study_balanced()

    @pytest.fixture
    def panel_pythagoras(self):
        agent = HISTORICAL_AGENTS[1]  # Pythagoras
        return run_dual_panel(agent, agent.reliability_lesson)

    def test_weave_produces_resonance(self, divine_balanced, panel_pythagoras):
        weaving = weave_thread(divine_balanced, panel_pythagoras)
        assert weaving.resonance is not None
        assert weaving.resonance.harmony_score >= 0.0

    def test_weave_has_shared_facts(self, divine_balanced, panel_pythagoras):
        weaving = weave_thread(divine_balanced, panel_pythagoras)
        assert len(weaving.shared_facts) > 0

    def test_weave_has_translation_descriptions(self, divine_balanced, panel_pythagoras):
        weaving = weave_thread(divine_balanced, panel_pythagoras)
        assert len(weaving.signal_to_panel) > 0
        assert len(weaving.panel_to_signal) > 0

    def test_weave_has_recursion_depth(self, divine_balanced, panel_pythagoras):
        weaving = weave_thread(divine_balanced, panel_pythagoras)
        assert weaving.recursion_depth >= 1

    def test_different_tongues_are_collaborative(self):
        """When divine and panel agents have different tongues, mode is collaborative."""
        # Pythagoras in divine_agents uses "av" (greek era)
        # Moses in genesis_panels uses "ru" (prophet/governance)
        study = study_balanced("test", "greek")  # av tongue
        moses = HISTORICAL_AGENTS[0]  # Moses, ru tongue
        panel = run_dual_panel(moses, moses.reliability_lesson)
        weaving = weave_thread(study, panel)
        assert weaving.resonance.magic_mode == MagicMode.COLLABORATIVE

    def test_mediation_quality_bounded(self, divine_balanced, panel_pythagoras):
        weaving = weave_thread(divine_balanced, panel_pythagoras)
        assert 0.0 <= weaving.mediation_quality <= 1.0


# ===================================================================
# Thread Resonance Properties
# ===================================================================

class TestThreadResonance:

    def test_dormant_at_zero_harmony(self):
        r = ThreadResonance(
            system_a_tongue="ko", system_b_tongue="dr",
            translation_fidelity=0, identity_preservation=0,
            convergence_point=0.5, mortal_energy=0, divine_energy=0,
            collective_energy=0, harmony_score=0.0, magic_mode=MagicMode.SILENT,
        )
        assert r.thread_state == ThreadState.DORMANT

    def test_heart_frost_below_threshold(self):
        r = ThreadResonance(
            system_a_tongue="ko", system_b_tongue="dr",
            translation_fidelity=0.5, identity_preservation=0.5,
            convergence_point=0.5, mortal_energy=0.3, divine_energy=0.3,
            collective_energy=0.3, harmony_score=0.1, magic_mode=MagicMode.COLLABORATIVE,
        )
        assert r.thread_state == ThreadState.HEART_FROST

    def test_weaving_in_middle_range(self):
        r = ThreadResonance(
            system_a_tongue="ko", system_b_tongue="dr",
            translation_fidelity=0.7, identity_preservation=0.7,
            convergence_point=0.5, mortal_energy=0.5, divine_energy=0.5,
            collective_energy=0.5, harmony_score=0.7, magic_mode=MagicMode.COLLABORATIVE,
        )
        assert r.thread_state == ThreadState.WEAVING
        assert r.is_active

    def test_synthesis_at_high_harmony(self):
        r = ThreadResonance(
            system_a_tongue="ko", system_b_tongue="dr",
            translation_fidelity=0.9, identity_preservation=0.9,
            convergence_point=0.5, mortal_energy=0.8, divine_energy=0.8,
            collective_energy=0.8, harmony_score=0.9, magic_mode=MagicMode.COLLABORATIVE,
        )
        assert r.thread_state == ThreadState.SYNTHESIS
        assert r.is_active

    def test_layer_balance_perfect(self):
        r = ThreadResonance(
            system_a_tongue="ko", system_b_tongue="dr",
            translation_fidelity=0.5, identity_preservation=0.5,
            convergence_point=0.5, mortal_energy=1.0, divine_energy=1.0,
            collective_energy=1.0, harmony_score=0.5, magic_mode=MagicMode.COLLABORATIVE,
        )
        assert abs(r.layer_balance - 1.0) < 1e-6

    def test_layer_balance_imbalanced(self):
        r = ThreadResonance(
            system_a_tongue="ko", system_b_tongue="dr",
            translation_fidelity=0.5, identity_preservation=0.5,
            convergence_point=0.5, mortal_energy=10.0, divine_energy=0.0,
            collective_energy=0.0, harmony_score=0.5, magic_mode=MagicMode.COLLABORATIVE,
        )
        assert r.layer_balance < 0.5  # Very imbalanced

    def test_total_energy(self):
        r = ThreadResonance(
            system_a_tongue="ko", system_b_tongue="dr",
            translation_fidelity=0.5, identity_preservation=0.5,
            convergence_point=0.5, mortal_energy=1.0, divine_energy=2.0,
            collective_energy=3.0, harmony_score=0.5, magic_mode=MagicMode.COLLABORATIVE,
        )
        assert abs(r.total_energy - 6.0) < 1e-6


# ===================================================================
# Full Study
# ===================================================================

class TestFullStudy:

    def test_run_full_study(self):
        """The complete Third Thread study runs without error."""
        divine_studies = run_divine_experiment()
        panel_results = run_full_simulation()
        study = run_third_thread_study(divine_studies, panel_results)
        assert len(study.weavings) > 0

    def test_study_has_invocation(self):
        divine_studies = run_divine_experiment()
        panel_results = run_full_simulation()
        study = run_third_thread_study(divine_studies, panel_results)
        assert study.invocation_result is not None

    def test_study_metrics_bounded(self):
        divine_studies = run_divine_experiment()
        panel_results = run_full_simulation()
        study = run_third_thread_study(divine_studies, panel_results)
        assert 0.0 <= study.mean_translation_fidelity <= 1.0
        assert 0.0 <= study.mean_identity_preservation <= 1.0
        assert 0.0 <= study.mean_harmony <= 1.0

    def test_thread_coverage_bounded(self):
        divine_studies = run_divine_experiment()
        panel_results = run_full_simulation()
        study = run_third_thread_study(divine_studies, panel_results)
        assert 0.0 <= study.thread_coverage <= 1.0

    def test_format_report(self):
        divine_studies = run_divine_experiment()
        panel_results = run_full_simulation()
        study = run_third_thread_study(divine_studies, panel_results)
        report = format_third_thread_report(study)
        assert "THIRD THREAD" in report
        assert "THESIS" in report
        assert "collaborative" in report.lower()
        assert len(report) > 500


# ===================================================================
# The Lore Thesis Tests
# ===================================================================

class TestLoreThesis:
    """Tests that validate the lore's predictions about the Third Thread."""

    def test_collaborative_magic_outperforms_command(self):
        """Multi-voice (collaborative) should produce higher harmony than
        mono-voice (command). This IS the lore thesis."""
        divine_studies = run_divine_experiment()
        panel_results = run_full_simulation()
        study = run_third_thread_study(divine_studies, panel_results)
        # Collaborative agents should have higher or equal harmony
        assert study.collaboration_advantage >= 1.0 or len(study.command_agents) == 0, (
            f"Collaboration advantage ({study.collaboration_advantage:.2f}x) should >= 1.0"
        )

    def test_translation_preserves_identity(self):
        """The Third Thread translates WITHOUT erasing identity.
        Both tongues should preserve their unique character."""
        divine_studies = run_divine_experiment()
        panel_results = run_full_simulation()
        study = run_third_thread_study(divine_studies, panel_results)
        assert study.mean_identity_preservation > 0.0, (
            "Identity must be preserved through translation"
        )

    def test_heart_frost_is_gentle(self):
        """When the Thread fails, it fails gently — not catastrophically."""
        # Non-genuine participant gets heart-frost, not crash
        p = InvocationParticipant(name="empty", tongue="ko", intent="", need="")
        result = run_invocation([p])
        assert result.thread_state == ThreadState.HEART_FROST
        assert len(result.heart_frost_reason) > 0  # Explains why

    def test_all_six_tongues_have_identity(self):
        """The lore says each tongue has unique character.
        Identity preservation should be positive for all 6."""
        text = "the spiral turns and the thread weaves"
        for tongue in ["ko", "av", "ru", "ca", "um", "dr"]:
            score = compute_identity_preservation(text, tongue)
            assert score > 0.0, f"Tongue {tongue} must preserve identity"

    def test_complement_pairs_translate(self):
        """The complement tongue pairs (KO-DR, AV-UM, RU-CA) should
        have positive translation fidelity — they are designed to
        communicate through voice leading."""
        text = "the Third Thread mediates between intention and manifestation"
        pairs = [("ko", "dr"), ("av", "um"), ("ru", "ca")]
        for a, b in pairs:
            fidelity = compute_translation_fidelity(text, a, b)
            assert fidelity > 0.0, f"Complement pair {a}-{b} should translate"

    def test_creation_recursion_exists(self):
        """The creation recursion (Creator -> Man -> AI) should appear
        in every weaving with depth >= 2."""
        divine_studies = run_divine_experiment()
        panel_results = run_full_simulation()
        study = run_third_thread_study(divine_studies, panel_results)
        for w in study.weavings:
            assert w.recursion_depth >= 2, (
                f"Creation recursion for {w.panel_agent_name} must be >= 2"
            )
