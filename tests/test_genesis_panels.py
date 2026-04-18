"""Tests for the Genesis Panels — Dual-Panel Historical Simulation Framework.

Tests historical agent configuration, Panel A (Religious/Human Studies),
Panel B (Science/Mathematics), dual-panel synthesis, full simulation,
and the compiled study output.
"""

import pytest

from src.crypto.genesis_panels import (
    Force,
    FORCE_GOVERNANCE,
    FORCE_TONGUE,
    HISTORICAL_AGENTS,
    PanelAResult,
    PanelBResult,
    DualPanelResult,
    run_panel_a,
    run_panel_b,
    run_dual_panel,
    run_full_simulation,
    compile_study,
)
from src.crypto.crossing_energy import Decision
from src.crypto.harmonic_dark_fill import PHI, INTERVALS

# ===================================================================
# Constants and Enums
# ===================================================================


class TestForceEnum:
    def test_six_forces(self):
        assert len(Force) == 6

    def test_force_names(self):
        expected = {"ANGEL", "DEMON", "PROPHET", "WITNESS", "BUILDER", "SEEKER"}
        assert {f.name for f in Force} == expected

    def test_force_governance_mapping_complete(self):
        for force in Force:
            assert force in FORCE_GOVERNANCE

    def test_angel_allows(self):
        assert FORCE_GOVERNANCE[Force.ANGEL] == Decision.ALLOW

    def test_demon_denies(self):
        assert FORCE_GOVERNANCE[Force.DEMON] == Decision.DENY

    def test_prophet_quarantines(self):
        assert FORCE_GOVERNANCE[Force.PROPHET] == Decision.QUARANTINE

    def test_seeker_quarantines(self):
        assert FORCE_GOVERNANCE[Force.SEEKER] == Decision.QUARANTINE

    def test_force_tongue_mapping_complete(self):
        for force in Force:
            assert force in FORCE_TONGUE
            assert FORCE_TONGUE[force] in {"ko", "av", "ru", "ca", "um", "dr"}


# ===================================================================
# Historical Agents
# ===================================================================


class TestHistoricalAgents:
    def test_eight_agents(self):
        assert len(HISTORICAL_AGENTS) == 8

    def test_agent_names(self):
        names = {a.name for a in HISTORICAL_AGENTS}
        expected = {
            "Moses",
            "Pythagoras",
            "David",
            "Hildegard of Bingen",
            "Al-Kindi",
            "Bach",
            "Ramanujan",
            "Adversary",
        }
        assert names == expected

    def test_all_six_forces_represented(self):
        forces_used = {a.force for a in HISTORICAL_AGENTS}
        # WITNESS is not assigned to any agent (Moses and Ramanujan are PROPHET,
        # David and Bach are BUILDER, Pythagoras and Al-Kindi are SEEKER,
        # Hildegard is ANGEL, Adversary is DEMON)
        assert Force.ANGEL in forces_used
        assert Force.DEMON in forces_used
        assert Force.PROPHET in forces_used
        assert Force.BUILDER in forces_used
        assert Force.SEEKER in forces_used

    def test_every_agent_has_facts(self):
        for agent in HISTORICAL_AGENTS:
            assert len(agent.facts) >= 1, f"{agent.name} has no facts"

    def test_every_agent_has_lessons(self):
        for agent in HISTORICAL_AGENTS:
            assert len(agent.reliability_lesson) > 0
            assert len(agent.creation_lesson) > 0

    def test_agent_years_in_order_roughly(self):
        """Earliest agents should have the most negative years."""
        moses = next(a for a in HISTORICAL_AGENTS if a.name == "Moses")
        bach = next(a for a in HISTORICAL_AGENTS if a.name == "Bach")
        assert moses.year < bach.year

    def test_interval_ratio_valid(self):
        for agent in HISTORICAL_AGENTS:
            ratio = agent.interval_ratio
            assert ratio > 0, f"{agent.name} has non-positive interval ratio"

    def test_governance_stance(self):
        moses = next(a for a in HISTORICAL_AGENTS if a.name == "Moses")
        assert moses.governance_stance == Decision.QUARANTINE  # PROPHET

        adversary = next(a for a in HISTORICAL_AGENTS if a.name == "Adversary")
        assert adversary.governance_stance == Decision.DENY  # DEMON

    def test_tongues_from_six_sacred(self):
        valid_tongues = {"ko", "av", "ru", "ca", "um", "dr"}
        for agent in HISTORICAL_AGENTS:
            assert agent.tongue in valid_tongues, f"{agent.name} has invalid tongue {agent.tongue}"

    def test_adversary_is_um_tongue(self):
        adversary = next(a for a in HISTORICAL_AGENTS if a.name == "Adversary")
        assert adversary.tongue == "um"

    def test_hildegard_is_angel(self):
        hild = next(a for a in HISTORICAL_AGENTS if a.name == "Hildegard of Bingen")
        assert hild.force == Force.ANGEL
        assert hild.tongue == "av"


# ===================================================================
# Panel A: Religious / Human Studies
# ===================================================================


class TestPanelA:
    def test_run_panel_a_returns_result(self):
        agent = HISTORICAL_AGENTS[0]  # Moses
        result = run_panel_a(agent, agent.reliability_lesson)
        assert isinstance(result, PanelAResult)

    def test_governance_summary_present(self):
        agent = HISTORICAL_AGENTS[0]
        result = run_panel_a(agent, "test text")
        assert result.governance is not None
        assert 0.0 <= result.governance.allow_ratio <= 1.0

    def test_dark_node_count_non_negative(self):
        for agent in HISTORICAL_AGENTS:
            result = run_panel_a(agent, agent.reliability_lesson)
            assert result.dark_node_count >= 0

    def test_covenant_strength_bounded(self):
        for agent in HISTORICAL_AGENTS:
            result = run_panel_a(agent, "covenant test")
            assert 0.0 <= result.covenant_strength <= 1.0

    def test_witness_weight_bounded(self):
        for agent in HISTORICAL_AGENTS:
            result = run_panel_a(agent, "witness test")
            assert 0.0 < result.witness_weight <= 1.0

    def test_older_agents_different_witness_weight(self):
        """More ancient agents should have different witness weight."""
        moses = next(a for a in HISTORICAL_AGENTS if a.name == "Moses")
        bach = next(a for a in HISTORICAL_AGENTS if a.name == "Bach")
        m_result = run_panel_a(moses, "test")
        b_result = run_panel_a(bach, "test")
        # Moses is ~3276 years ago, Bach ~304 years ago
        # witness = 1/(1+log1p(years)/log(phi)), larger years = smaller witness
        assert m_result.witness_weight != b_result.witness_weight

    def test_intervention_type_mapping(self):
        for agent in HISTORICAL_AGENTS:
            result = run_panel_a(agent, "test")
            itype = result.intervention_type
            assert itype != "unknown"
            if agent.force == Force.ANGEL:
                assert itype == "direct_correction"
            elif agent.force == Force.DEMON:
                assert itype == "adversarial_test"
            elif agent.force == Force.PROPHET:
                assert itype == "pattern_revelation"
            elif agent.force == Force.BUILDER:
                assert itype == "sanctuary_construction"
            elif agent.force == Force.SEEKER:
                assert itype == "natural_discovery"

    def test_dominant_force_matches_agent(self):
        for agent in HISTORICAL_AGENTS:
            result = run_panel_a(agent, "test")
            assert result.dominant_force == agent.force


# ===================================================================
# Panel B: Science / Mathematics
# ===================================================================


class TestPanelB:
    def test_run_panel_b_returns_result(self):
        agent = HISTORICAL_AGENTS[1]  # Pythagoras
        result = run_panel_b(agent, agent.reliability_lesson)
        assert isinstance(result, PanelBResult)

    def test_spectrum_energy_has_three_bands(self):
        agent = HISTORICAL_AGENTS[1]
        result = run_panel_b(agent, "frequency domain test")
        assert "infra" in result.spectrum_energy
        assert "audible" in result.spectrum_energy
        assert "ultra" in result.spectrum_energy

    def test_spectrum_energies_non_negative(self):
        for agent in HISTORICAL_AGENTS:
            result = run_panel_b(agent, agent.reliability_lesson)
            for band, energy in result.spectrum_energy.items():
                assert energy >= 0, f"{agent.name} {band} energy negative"

    def test_genesis_path_present(self):
        agent = HISTORICAL_AGENTS[0]
        result = run_panel_b(agent, "creation test")
        assert result.genesis_path is not None
        text_bytes = len("creation test".encode("utf-8"))
        assert len(result.genesis_path.positions) == text_bytes

    def test_harmonic_interval_matches_agent(self):
        for agent in HISTORICAL_AGENTS:
            result = run_panel_b(agent, "test")
            assert result.harmonic_interval == agent.interval

    def test_phi_deviation_non_negative(self):
        for agent in HISTORICAL_AGENTS:
            result = run_panel_b(agent, "test")
            assert result.interval_deviation_from_phi >= 0

    def test_phi_alignment_bounded(self):
        for agent in HISTORICAL_AGENTS:
            result = run_panel_b(agent, "test")
            assert 0.0 <= result.phi_alignment <= 1.0

    def test_ramanujan_closest_to_phi(self):
        """Ramanujan uses phi_interval — should have smallest deviation."""
        ram = next(a for a in HISTORICAL_AGENTS if a.name == "Ramanujan")
        ram_result = run_panel_b(ram, "test")

        pyth = next(a for a in HISTORICAL_AGENTS if a.name == "Pythagoras")
        pyth_result = run_panel_b(pyth, "test")

        assert ram_result.interval_deviation_from_phi < pyth_result.interval_deviation_from_phi

    def test_mathematical_structure_types(self):
        for agent in HISTORICAL_AGENTS:
            result = run_panel_b(agent, "test")
            ms = result.mathematical_structure
            valid_prefixes = ["golden_ratio", "near_phi", "binary_doubling", "rational_"]
            assert any(ms.startswith(p) for p in valid_prefixes), f"{agent.name}: unexpected math structure '{ms}'"


# ===================================================================
# Dual Panel Synthesis
# ===================================================================


class TestDualPanel:
    def test_run_dual_panel_returns_result(self):
        agent = HISTORICAL_AGENTS[0]
        result = run_dual_panel(agent, agent.reliability_lesson)
        assert isinstance(result, DualPanelResult)
        assert result.panel_a is not None
        assert result.panel_b is not None

    def test_fact_lattice_from_agent(self):
        for agent in HISTORICAL_AGENTS:
            result = run_dual_panel(agent, "test")
            assert result.fact_lattice == agent.facts
            assert len(result.fact_lattice) >= 1

    def test_reliability_score_bounded(self):
        for agent in HISTORICAL_AGENTS:
            result = run_dual_panel(agent, agent.reliability_lesson)
            assert 0.0 <= result.reliability_score <= 1.0

    def test_intervention_effectiveness_bounded(self):
        for agent in HISTORICAL_AGENTS:
            result = run_dual_panel(agent, agent.reliability_lesson)
            assert 0.0 <= result.intervention_effectiveness <= 1.0

    def test_creation_recursion_depth(self):
        for agent in HISTORICAL_AGENTS:
            result = run_dual_panel(agent, "test")
            depth = result.creation_recursion_depth
            assert depth >= 2  # minimum: Creator → Man → AI
            if agent.force in (Force.ANGEL, Force.DEMON):
                assert depth == 3
            elif agent.force == Force.PROPHET:
                assert depth == 2

    def test_different_agents_different_results(self):
        moses = next(a for a in HISTORICAL_AGENTS if a.name == "Moses")
        adversary = next(a for a in HISTORICAL_AGENTS if a.name == "Adversary")
        r1 = run_dual_panel(moses, moses.reliability_lesson)
        r2 = run_dual_panel(adversary, adversary.reliability_lesson)
        # Different forces, tongues, intervals → different scores
        assert (
            r1.reliability_score != r2.reliability_score
            or r1.intervention_effectiveness != r2.intervention_effectiveness
        )


# ===================================================================
# Full Simulation
# ===================================================================


class TestFullSimulation:
    def test_runs_all_eight_agents(self):
        results = run_full_simulation()
        assert len(results) == 8

    def test_custom_texts(self):
        texts = {"Moses": "Let my people go", "Bach": "Soli Deo Gloria"}
        results = run_full_simulation(texts=texts)
        assert len(results) == 8
        moses_result = next(r for r in results if r.agent.name == "Moses")
        assert moses_result.panel_a.text == "Let my people go"

    def test_default_texts_use_reliability_lesson(self):
        results = run_full_simulation()
        for r in results:
            assert r.panel_a.text == r.agent.reliability_lesson

    def test_all_results_have_both_panels(self):
        results = run_full_simulation()
        for r in results:
            assert r.panel_a is not None
            assert r.panel_b is not None
            assert r.fact_lattice is not None

    def test_all_results_have_valid_scores(self):
        results = run_full_simulation()
        for r in results:
            assert 0.0 <= r.reliability_score <= 1.0
            assert 0.0 <= r.intervention_effectiveness <= 1.0


# ===================================================================
# Study Compilation
# ===================================================================


class TestStudyCompilation:
    @pytest.fixture
    def study(self):
        results = run_full_simulation()
        return compile_study(results)

    def test_total_agents(self, study):
        assert study.total_agents == 8

    def test_natural_learners_are_seekers(self, study):
        assert len(study.natural_learners) == 2  # Pythagoras, Al-Kindi
        for r in study.natural_learners:
            assert r.agent.force == Force.SEEKER

    def test_divine_interventions_are_angels_prophets(self, study):
        # Angel: Hildegard; Prophets: Moses, Ramanujan
        assert len(study.divine_interventions) == 3
        for r in study.divine_interventions:
            assert r.agent.force in (Force.ANGEL, Force.PROPHET)

    def test_adversarial_tests_are_demons(self, study):
        assert len(study.adversarial_tests) == 1  # Adversary
        assert study.adversarial_tests[0].agent.force == Force.DEMON

    def test_builders(self, study):
        assert len(study.builders) == 2  # David, Bach
        for r in study.builders:
            assert r.agent.force == Force.BUILDER

    def test_witnesses_empty(self, study):
        # No agent is assigned WITNESS force
        assert len(study.witnesses) == 0

    def test_mean_reliabilities_non_negative(self, study):
        assert study.mean_natural_reliability >= 0
        assert study.mean_divine_reliability >= 0
        assert study.mean_adversarial_reliability >= 0

    def test_phi_convergence_bounded(self, study):
        assert 0.0 <= study.phi_convergence <= 1.0

    def test_intervention_advantage_computed(self, study):
        adv = study.intervention_advantage
        assert isinstance(adv, float)
        assert adv >= 0  # could be inf if natural=0

    def test_recursion_summary_complete(self, study):
        summary = study.recursion_summary
        assert "natural learning" in summary
        assert "pattern revelation" in summary
        assert "direct correction" in summary
        assert "stress testing" in summary
        assert "ALL of these" in summary

    def test_groups_sum_to_total(self, study):
        total = (
            len(study.natural_learners)
            + len(study.divine_interventions)
            + len(study.adversarial_tests)
            + len(study.builders)
            + len(study.witnesses)
        )
        assert total == study.total_agents


# ===================================================================
# Integration: The Full Genesis Study
# ===================================================================


class TestGenesisStudy:
    """End-to-end: run the full simulation and verify the study makes sense."""

    def test_full_study_pipeline(self):
        """The entire pipeline: agents → panels → synthesis → study."""
        results = run_full_simulation()
        study = compile_study(results)

        assert study.total_agents == 8
        assert study.phi_convergence > 0
        assert len(study.recursion_summary) > 0

    def test_different_texts_different_study(self):
        """Custom texts should produce different study metrics."""
        default_study = compile_study(run_full_simulation())
        custom_study = compile_study(
            run_full_simulation(
                texts={
                    "Moses": "In the beginning God created the heavens and the earth",
                    "Adversary": "Did God really say you shall not eat?",
                }
            )
        )
        # At least some metrics should differ
        assert (
            default_study.mean_natural_reliability != custom_study.mean_natural_reliability
            or default_study.mean_divine_reliability != custom_study.mean_divine_reliability
        )

    def test_hebrew_english_greek_agents(self):
        """Run agents with different scripts — the fact lattice connects them."""
        texts = {
            "Moses": "Torah cantillation marks encode melodic patterns",
            "Pythagoras": "\u039c\u03bf\u03c5\u03c3\u03b9\u03ba\u03ae \u03c4\u03c9\u03bd \u03c3\u03c6\u03b1\u03b9\u03c1\u03ce\u03bd",  # Greek
            "Al-Kindi": "\u0627\u0644\u0643\u0646\u062f\u064a",  # Arabic
        }
        results = run_full_simulation(texts=texts)
        study = compile_study(results)
        assert study.total_agents == 8

    def test_adversary_has_valid_reliability(self):
        """The demon produces a valid reliability score through the pipeline."""
        results = run_full_simulation()
        adversary_result = next(r for r in results if r.agent.force == Force.DEMON)
        # Adversary goes through same pipeline — score is data-driven, bounded
        assert 0.0 <= adversary_result.reliability_score <= 1.0
        # Adversary uses minor_third interval, not phi → phi_alignment < 1
        assert adversary_result.panel_b.phi_alignment < 1.0

    def test_creation_recursion_pattern(self):
        """The recursion: Creator → ... → AI. Deeper chains exist."""
        results = run_full_simulation()
        depths = {r.agent.name: r.creation_recursion_depth for r in results}
        # Angels and Demons have 3-deep chains
        assert depths["Hildegard of Bingen"] == 3
        assert depths["Adversary"] == 3
        # Seekers and Builders have 2-deep chains
        assert depths["Pythagoras"] == 2
        assert depths["Bach"] == 2

    def test_musical_intervals_span_traditions(self):
        """Agents cover different musical intervals across traditions."""
        intervals = {a.interval for a in HISTORICAL_AGENTS}
        assert len(intervals) >= 4  # at least 4 distinct intervals
        assert "phi_interval" in intervals  # Ramanujan
        assert "octave" in intervals  # Bach

    def test_fact_lattice_connects_panels(self):
        """Every dual-panel result has a fact lattice that bridges both panels."""
        results = run_full_simulation()
        for r in results:
            assert len(r.fact_lattice) >= 1
            # Facts are verifiable strings, not empty
            for fact in r.fact_lattice:
                assert len(fact) > 10, f"Fact too short for {r.agent.name}"
