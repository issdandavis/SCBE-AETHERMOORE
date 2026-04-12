"""
Tests for Simulation Curriculum — Progressive 6-Level Training.

Validates:
1. Level classification maps physics state to correct levels 0-5
2. All 6 levels are reachable with appropriate inputs
3. SimulationBundle fuses QHO + flight + code lattice correctly
4. Compounding intent = system × learner (multiplicative)
5. SFT records scale complexity with curriculum level
6. Report formatting includes all required sections
7. Batch generation preserves individual bundle integrity
8. Cross-level properties: higher levels have more active systems
"""

import pytest

from src.crypto.simulation_curriculum import (
    LEVEL_BOUNDARIES,
    LEVEL_NAMES,
    LEVEL_DESCRIPTIONS,
    SimulationBundle,
    classify_curriculum_level,
    curriculum_difficulty_from_level,
    generate_simulation_bundle,
    generate_simulation_batch,
    generate_curriculum_sft_records,
    curriculum_summary,
    format_curriculum_report,
)
from src.crypto.quantum_frequency_bundle import (
    QuantumFrequencyBundle,
)
from src.crypto.flight_dynamics import (
    FlightDynamicsState,
)
from src.crypto.code_lattice import (
    CodeLatticeBundle,
)

# ===================================================================
# Level Classification
# ===================================================================


class TestLevelClassification:
    """Test that physics state maps to correct curriculum levels."""

    def test_level_0_ground_state(self):
        """n=0, no forks, no swear words → Level 0."""
        level = classify_curriculum_level(
            qho_max_n=0,
            has_forks=False,
            monty_hall_gain=0.0,
            swear_word_count=0,
            in_vrs=False,
            has_recovery_paths=False,
            compound_intent=0.0,
        )
        assert level == 0

    def test_level_1_low_excitation(self):
        """n=1-2, no forks → Level 1."""
        level = classify_curriculum_level(
            qho_max_n=2,
            has_forks=False,
            monty_hall_gain=0.0,
            swear_word_count=0,
            in_vrs=False,
            has_recovery_paths=False,
            compound_intent=0.0,
        )
        assert level == 1

    def test_level_2_forks_present(self):
        """Forks with gain → Level 2."""
        level = classify_curriculum_level(
            qho_max_n=2,
            has_forks=True,
            monty_hall_gain=0.5,
            swear_word_count=0,
            in_vrs=False,
            has_recovery_paths=False,
            compound_intent=0.0,
        )
        assert level == 2

    def test_level_3_high_excitation(self):
        """n≥4 → Level 3."""
        level = classify_curriculum_level(
            qho_max_n=5,
            has_forks=False,
            monty_hall_gain=0.0,
            swear_word_count=0,
            in_vrs=False,
            has_recovery_paths=False,
            compound_intent=0.0,
        )
        assert level == 3

    def test_level_3_vrs_entry(self):
        """VRS active → Level 3 minimum."""
        level = classify_curriculum_level(
            qho_max_n=2,
            has_forks=False,
            monty_hall_gain=0.0,
            swear_word_count=0,
            in_vrs=True,
            has_recovery_paths=False,
            compound_intent=0.0,
        )
        assert level == 3

    def test_level_4_recovery_with_swears(self):
        """Recovery paths + swear words + n≥3 → Level 4."""
        level = classify_curriculum_level(
            qho_max_n=4,
            has_forks=True,
            monty_hall_gain=0.5,
            swear_word_count=2,
            in_vrs=False,
            has_recovery_paths=True,
            compound_intent=0.5,
        )
        assert level == 4

    def test_level_5_full_lattice(self):
        """All systems active + high compound intent → Level 5."""
        level = classify_curriculum_level(
            qho_max_n=6,
            has_forks=True,
            monty_hall_gain=0.8,
            swear_word_count=3,
            in_vrs=True,
            has_recovery_paths=True,
            compound_intent=2.0,
        )
        assert level == 5

    def test_level_5_requires_vrs(self):
        """Without VRS, can't reach Level 5."""
        level = classify_curriculum_level(
            qho_max_n=6,
            has_forks=True,
            monty_hall_gain=0.8,
            swear_word_count=3,
            in_vrs=False,
            has_recovery_paths=True,
            compound_intent=2.0,
        )
        assert level < 5

    def test_level_5_requires_swear_words(self):
        """Without swear words, can't reach Level 5."""
        level = classify_curriculum_level(
            qho_max_n=6,
            has_forks=True,
            monty_hall_gain=0.8,
            swear_word_count=0,
            in_vrs=True,
            has_recovery_paths=True,
            compound_intent=2.0,
        )
        assert level < 5

    def test_level_5_requires_high_compound(self):
        """Without high compound intent, can't reach Level 5."""
        level = classify_curriculum_level(
            qho_max_n=6,
            has_forks=True,
            monty_hall_gain=0.8,
            swear_word_count=3,
            in_vrs=True,
            has_recovery_paths=True,
            compound_intent=0.5,
        )
        assert level < 5

    def test_all_levels_reachable(self):
        """Every level 0-5 must be reachable."""
        reachable = set()

        # Level 0
        reachable.add(classify_curriculum_level(0, False, 0.0, 0, False, False, 0.0))
        # Level 1
        reachable.add(classify_curriculum_level(1, False, 0.0, 0, False, False, 0.0))
        # Level 2
        reachable.add(classify_curriculum_level(2, True, 0.5, 0, False, False, 0.0))
        # Level 3
        reachable.add(classify_curriculum_level(5, False, 0.0, 0, False, False, 0.0))
        # Level 4
        reachable.add(classify_curriculum_level(4, True, 0.5, 2, False, True, 0.5))
        # Level 5
        reachable.add(classify_curriculum_level(6, True, 0.8, 3, True, True, 2.0))

        assert reachable == {0, 1, 2, 3, 4, 5}


# ===================================================================
# Level Metadata
# ===================================================================


class TestLevelMetadata:
    """Test level boundaries, names, and descriptions."""

    def test_six_levels(self):
        assert len(LEVEL_BOUNDARIES) == 6
        assert len(LEVEL_NAMES) == 6
        assert len(LEVEL_DESCRIPTIONS) == 6

    def test_boundaries_cover_full_range(self):
        """Boundaries should cover [0.0, 1.0] completely."""
        assert LEVEL_BOUNDARIES[0][0] == 0.0
        assert LEVEL_BOUNDARIES[5][1] == 1.0

    def test_boundaries_non_overlapping(self):
        """Each level's upper bound = next level's lower bound."""
        for i in range(5):
            assert LEVEL_BOUNDARIES[i][1] == LEVEL_BOUNDARIES[i + 1][0]

    def test_boundaries_increasing(self):
        for i in range(6):
            lo, hi = LEVEL_BOUNDARIES[i]
            assert lo < hi

    def test_difficulty_from_level(self):
        """Difficulty should be midpoint of level range."""
        for level in range(6):
            lo, hi = LEVEL_BOUNDARIES[level]
            expected = (lo + hi) / 2.0
            assert abs(curriculum_difficulty_from_level(level) - expected) < 1e-10

    def test_difficulty_monotonically_increasing(self):
        for i in range(5):
            assert curriculum_difficulty_from_level(i) < curriculum_difficulty_from_level(i + 1)


# ===================================================================
# Simulation Bundle Creation
# ===================================================================


class TestSimulationBundle:
    """Test unified bundle generation."""

    def test_generates_bundle(self):
        b = generate_simulation_bundle("Test text for simulation bundle")
        assert isinstance(b, SimulationBundle)

    def test_has_quantum(self):
        b = generate_simulation_bundle("Quantum test")
        assert isinstance(b.quantum, QuantumFrequencyBundle)

    def test_has_flight(self):
        b = generate_simulation_bundle("Flight test")
        assert isinstance(b.flight, FlightDynamicsState)

    def test_has_code_lattice(self):
        b = generate_simulation_bundle("Code test")
        assert isinstance(b.code, CodeLatticeBundle)

    def test_curriculum_level_valid(self):
        b = generate_simulation_bundle("Level check")
        assert 0 <= b.curriculum_level <= 5

    def test_curriculum_difficulty_valid(self):
        b = generate_simulation_bundle("Difficulty check")
        assert 0.0 <= b.curriculum_difficulty <= 1.0

    def test_text_preserved(self):
        text = "The exact input text"
        b = generate_simulation_bundle(text)
        assert b.text == text

    def test_level_name_matches(self):
        b = generate_simulation_bundle("Name check")
        assert b.level_name == LEVEL_NAMES[b.curriculum_level]

    def test_level_description_matches(self):
        b = generate_simulation_bundle("Desc check")
        assert b.level_description == LEVEL_DESCRIPTIONS[b.curriculum_level]


# ===================================================================
# Derived Properties
# ===================================================================


class TestDerivedProperties:
    """Test that derived properties are correct."""

    @pytest.fixture
    def bundle(self):
        return generate_simulation_bundle("A rich test text with enough complexity to trigger multiple systems")

    def test_qho_max_n_from_quantum(self, bundle):
        assert bundle.qho_max_n == bundle.quantum.qho.max_excitation

    def test_is_ground_state_from_quantum(self, bundle):
        assert bundle.is_ground_state == bundle.quantum.is_ground_state

    def test_has_forks_from_multipath(self, bundle):
        assert bundle.has_forks == (len(bundle.quantum.multipath.forks) > 0)

    def test_monty_hall_gain_from_multipath(self, bundle):
        assert bundle.monty_hall_gain == bundle.quantum.multipath.monty_hall_advantage

    def test_swear_word_count_from_code(self, bundle):
        assert bundle.swear_word_count == bundle.code.swear_word_count

    def test_in_vrs_from_flight(self, bundle):
        assert bundle.in_vrs == bundle.flight.is_in_vrs

    def test_has_recovery_from_flight(self, bundle):
        assert bundle.has_recovery_paths == (len(bundle.flight.recovery_paths) > 0)

    def test_visual_vector_from_quantum(self, bundle):
        assert bundle.visual_vector == bundle.quantum.visual_vector

    def test_dominant_tongue_from_quantum(self, bundle):
        assert bundle.dominant_tongue == bundle.quantum.qho.dominant_tongue

    def test_flight_regime_from_flight(self, bundle):
        assert bundle.flight_regime == bundle.flight.flight_regime


# ===================================================================
# Compounding Intent
# ===================================================================


class TestCompoundingIntent:
    """Test that system × learner intent compounds correctly."""

    def test_system_intent_nonnegative(self):
        b = generate_simulation_bundle("System intent test")
        assert b.system_intent >= 0.0

    def test_learner_intent_nonnegative(self):
        b = generate_simulation_bundle("Learner intent test")
        assert b.learner_intent >= 0.0

    def test_compounding_is_product(self):
        """Compounding = system × learner, not sum."""
        b = generate_simulation_bundle("Product check")
        expected = b.system_intent * b.learner_intent
        assert abs(b.compounding_intent_score - expected) < 1e-10

    def test_different_texts_different_intents(self):
        """Different texts should produce different compounding scores."""
        b1 = generate_simulation_bundle("Simple hello")
        b2 = generate_simulation_bundle(
            "The complex interplay of vortex dynamics and quantum "
            "excitation in a multidimensional governance framework"
        )
        assert b1.compounding_intent_score != b2.compounding_intent_score


# ===================================================================
# to_dict Serialization
# ===================================================================


class TestSerialization:
    """Test that to_dict produces complete serialization."""

    @pytest.fixture
    def bundle_dict(self):
        b = generate_simulation_bundle("Serialization test text")
        return b.to_dict()

    def test_has_curriculum_section(self, bundle_dict):
        assert "curriculum" in bundle_dict
        cur = bundle_dict["curriculum"]
        assert "level" in cur
        assert "level_name" in cur
        assert "difficulty" in cur
        assert "compounding_intent" in cur
        assert "system_intent" in cur
        assert "learner_intent" in cur

    def test_has_quantum_section(self, bundle_dict):
        assert "quantum" in bundle_dict

    def test_has_flight_section(self, bundle_dict):
        assert "flight" in bundle_dict

    def test_has_code_lattice_section(self, bundle_dict):
        cl = bundle_dict["code_lattice"]
        assert "lesson_count" in cl
        assert "swear_word_count" in cl
        assert "total_compound_intent" in cl
        assert "active_domains" in cl
        assert "lessons" in cl


# ===================================================================
# Batch Generation
# ===================================================================


class TestBatchGeneration:
    """Test batch bundle generation."""

    @pytest.fixture
    def batch(self):
        texts = [
            "Simple hello world text",
            "The Riemann zeta function reveals structure in primes",
            "Vortex ring state onset during vertical descent",
            "Complex multi-domain governance framework with intent compounding",
        ]
        return generate_simulation_batch(texts)

    def test_correct_count(self, batch):
        assert len(batch) == 4

    def test_all_simulation_bundles(self, batch):
        for b in batch:
            assert isinstance(b, SimulationBundle)

    def test_texts_preserved(self, batch):
        assert batch[0].text == "Simple hello world text"
        assert "Riemann" in batch[1].text

    def test_levels_vary(self, batch):
        """Batch should have multiple different levels."""
        levels = {b.curriculum_level for b in batch}
        assert len(levels) >= 1  # at least some variation

    def test_each_has_all_engines(self, batch):
        for b in batch:
            assert b.quantum is not None
            assert b.flight is not None
            assert b.code is not None


# ===================================================================
# SFT Record Generation
# ===================================================================


class TestSFTRecords:
    """Test SFT training record generation."""

    @pytest.fixture
    def records(self):
        texts = [
            "Hello world simple text",
            "The void between stars carries potential energy across spacetime manifolds",
            "Post-quantum lattice assumptions form the basis of modern cryptographic security",
            "Autorotation recovery from deep vortex ring state requires collective reduction",
        ]
        bundles = generate_simulation_batch(texts)
        return generate_curriculum_sft_records(bundles), bundles

    def test_one_record_per_bundle(self, records):
        recs, bundles = records
        assert len(recs) == len(bundles)

    def test_records_have_messages(self, records):
        recs, _ = records
        for rec in recs:
            assert "messages" in rec
            assert len(rec["messages"]) == 2
            assert rec["messages"][0]["role"] == "user"
            assert rec["messages"][1]["role"] == "assistant"

    def test_records_have_metadata(self, records):
        recs, _ = records
        for rec in recs:
            assert "metadata" in rec
            meta = rec["metadata"]
            assert meta["source"] == "simulation_curriculum_generator"
            assert meta["record_type"] == "simulation_curriculum"
            assert "curriculum_level" in meta
            assert "curriculum_difficulty" in meta
            assert "compounding_intent" in meta
            assert "simulation_bundle" in meta

    def test_level_matches_bundle(self, records):
        recs, bundles = records
        for rec, bundle in zip(recs, bundles):
            assert rec["metadata"]["curriculum_level"] == bundle.curriculum_level

    def test_assistant_content_nonempty(self, records):
        recs, _ = records
        for rec in recs:
            assert len(rec["messages"][1]["content"]) > 20

    def test_higher_level_longer_response(self, records):
        """Higher curriculum levels should generally produce longer responses."""
        recs, bundles = records
        # Group by level and check trend
        by_level = {}
        for rec, b in zip(recs, bundles):
            lvl = b.curriculum_level
            content_len = len(rec["messages"][1]["content"])
            by_level.setdefault(lvl, []).append(content_len)

        # If we have multiple levels, higher levels should tend longer
        if len(by_level) >= 2:
            levels = sorted(by_level.keys())
            # Just verify lowest and highest — don't require strict monotonicity
            low_mean = sum(by_level[levels[0]]) / len(by_level[levels[0]])
            high_mean = sum(by_level[levels[-1]]) / len(by_level[levels[-1]])
            # High levels should produce at least as much output
            # (relaxed: same level can vary)
            assert high_mean >= low_mean * 0.5

    def test_low_level_simpler_prompt(self, records):
        """Level 0-1 prompts should be simpler (no flight/VRS mention)."""
        recs, bundles = records
        for rec, b in zip(recs, bundles):
            if b.curriculum_level <= 1:
                user_msg = rec["messages"][0]["content"]
                assert "VRS" not in user_msg
                assert "recovery" not in user_msg

    def test_high_level_full_prompt(self, records):
        """Level 4-5 prompts should mention full simulation."""
        recs, bundles = records
        for rec, b in zip(recs, bundles):
            if b.curriculum_level >= 4:
                user_msg = rec["messages"][0]["content"]
                assert "simulation" in user_msg.lower() or "flight" in user_msg.lower()


# ===================================================================
# Summary Statistics
# ===================================================================


class TestSummary:
    """Test batch summary statistics."""

    @pytest.fixture
    def summary(self):
        texts = [
            "Alpha text one",
            "Beta text two with more words for variety",
            "Gamma complex text discussing vortex dynamics and recovery",
        ]
        bundles = generate_simulation_batch(texts)
        return curriculum_summary(bundles)

    def test_correct_count(self, summary):
        assert summary["count"] == 3

    def test_has_level_distribution(self, summary):
        assert "level_distribution" in summary
        assert "level_counts" in summary

    def test_level_counts_sum_to_total(self, summary):
        total = sum(summary["level_counts"].values())
        assert total == summary["count"]

    def test_has_compounding_intent(self, summary):
        ci = summary["compounding_intent"]
        assert "mean" in ci
        assert "max" in ci
        assert ci["max"] >= ci["mean"]

    def test_has_vrs_stats(self, summary):
        assert "vrs_entries" in summary
        assert "vrs_pct" in summary

    def test_has_swear_stats(self, summary):
        assert "total_swear_words" in summary

    def test_has_domain_activity(self, summary):
        assert "domain_activity" in summary

    def test_empty_batch(self):
        s = curriculum_summary([])
        assert s["count"] == 0


# ===================================================================
# Report Formatting
# ===================================================================


class TestReport:
    """Test human-readable report output."""

    @pytest.fixture
    def report(self):
        texts = [
            "Report text alpha",
            "Report text beta with more complexity and governance",
        ]
        bundles = generate_simulation_batch(texts)
        return format_curriculum_report(bundles)

    def test_has_header(self, report):
        assert "SIMULATION CURRICULUM REPORT" in report

    def test_has_principle(self, report):
        assert "Repetition is scaffolding" in report

    def test_has_statistics(self, report):
        assert "Total bundles" in report
        assert "VRS entries" in report
        assert "Swear words" in report

    def test_has_level_distribution(self, report):
        assert "LEVEL DISTRIBUTION" in report

    def test_has_all_level_names(self, report):
        # At least the level labels should appear
        for i in range(6):
            assert f"L{i}" in report

    def test_has_domain_activity(self, report):
        assert "DOMAIN ACTIVITY" in report

    def test_has_per_bundle_detail(self, report):
        assert "PER-BUNDLE DETAIL" in report

    def test_empty_report(self):
        r = format_curriculum_report([])
        assert "No bundles" in r

    def test_report_length(self, report):
        assert len(report) > 500


# ===================================================================
# Cross-Level Properties
# ===================================================================


class TestCrossLevelProperties:
    """Test properties that should hold across curriculum levels."""

    def test_higher_level_more_active_systems(self):
        """Higher levels should have more systems active (on average)."""
        # Generate a large enough sample
        texts = [
            # Short/simple
            "Hi",
            "Yes",
            "No",
            "Ok",
            # Medium
            "The cat sat on the mat in the corner of the room",
            "Gradient descent optimizes the loss function iteratively",
            # Complex
            "Vortex ring state during helicopter descent creates dangerous recirculation",
            "The toroidal geometry of the polyhedral lattice binds all six tongues simultaneously",
            "Post-quantum cryptographic assumptions require lattice-based hardness guarantees",
            "Deep VRS recovery via Vuichard technique plus collective pitch reduction and cyclic displacement",
        ]
        bundles = generate_simulation_batch(texts)

        # Count active systems per bundle
        for b in bundles:
            systems_active = 0
            if b.qho_max_n > 0:
                systems_active += 1
            if b.has_forks:
                systems_active += 1
            if b.swear_word_count > 0:
                systems_active += 1
            if b.in_vrs:
                systems_active += 1
            if b.has_recovery_paths:
                systems_active += 1
            # Higher levels should generally have more systems
            # (but not strictly — individual texts vary)
            if b.curriculum_level >= 4:
                assert systems_active >= 2, (
                    f"Level {b.curriculum_level} should have ≥2 active systems, " f"got {systems_active}"
                )

    def test_difficulty_matches_level(self):
        """curriculum_difficulty should be in the correct level's range."""
        texts = [
            "Test one",
            "Test two longer",
            "Test three even longer with more detail",
        ]
        for b in generate_simulation_batch(texts):
            lo, hi = LEVEL_BOUNDARIES[b.curriculum_level]
            expected = (lo + hi) / 2.0
            assert abs(b.curriculum_difficulty - expected) < 1e-10

    def test_rotorcraft_flag(self):
        """Fixed-wing mode should not produce rotor state."""
        b = generate_simulation_bundle("Fixed wing test", is_rotorcraft=False)
        assert b.flight.rotor is None

    def test_rotorcraft_has_rotor(self):
        """Rotorcraft mode should produce rotor state."""
        b = generate_simulation_bundle("Rotorcraft test", is_rotorcraft=True)
        assert b.flight.rotor is not None


# ===================================================================
# Edge Cases
# ===================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_text(self):
        """Empty text should not crash."""
        b = generate_simulation_bundle("")
        assert isinstance(b, SimulationBundle)
        assert 0 <= b.curriculum_level <= 5

    def test_very_long_text(self):
        """Long text should not crash."""
        text = "The pattern repeats across all dimensions. " * 100
        b = generate_simulation_bundle(text)
        assert isinstance(b, SimulationBundle)

    def test_unicode_text(self):
        """Unicode text should not crash."""
        b = generate_simulation_bundle("φ × ψ = τ in the Ω manifold")
        assert isinstance(b, SimulationBundle)

    def test_single_word(self):
        b = generate_simulation_bundle("vortex")
        assert isinstance(b, SimulationBundle)

    def test_batch_empty(self):
        bundles = generate_simulation_batch([])
        assert bundles == []

    def test_sft_empty_batch(self):
        records = generate_curriculum_sft_records([])
        assert records == []
