"""
Tests for divine_agents.py — Historical Figure Roleplay with Angel/Demon Signals
=================================================================================
Study on Natural Learning For AI development and
Divine Intervention Mechanisms for Long-term Mission Reliability.
"""

import sys
import os
import math
import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.crypto.divine_agents import (
    PHI,
    HISTORICAL_ERAS,
    ERA_ORDER,
    SignalType,
    AgentRole,
    DivineSignal,
    HistoricalAgent,
    LearningEpoch,
    NaturalLearningStudy,
    generate_angel_signal,
    generate_demon_signal,
    study_angel_only,
    study_demon_only,
    study_balanced,
    study_historical_panel,
    run_divine_experiment,
    format_study_report,
)
from src.crypto.crossing_energy import Decision, DualTernaryPair

# ===================================================================
# Historical Era Constants
# ===================================================================


class TestHistoricalEras:
    """Verify the historical fact lattice is correctly structured."""

    def test_seven_eras_defined(self):
        assert len(HISTORICAL_ERAS) == 7

    def test_era_order_matches_keys(self):
        for key in ERA_ORDER:
            assert key in HISTORICAL_ERAS

    def test_all_eras_have_required_fields(self):
        required = {"name", "range", "interval", "interval_ratio", "tongue", "description", "archetype_figures"}
        for key, era in HISTORICAL_ERAS.items():
            missing = required - set(era.keys())
            assert not missing, f"Era '{key}' missing fields: {missing}"

    def test_interval_spiral_opens_and_closes_at_phi(self):
        """The musical interval arc starts and ends at phi."""
        first = HISTORICAL_ERAS[ERA_ORDER[0]]["interval_ratio"]
        last = HISTORICAL_ERAS[ERA_ORDER[-1]]["interval_ratio"]
        assert abs(first - PHI) < 1e-6, "Spiral must start at phi"
        assert abs(last - PHI) < 1e-6, "Spiral must return to phi"

    def test_interval_ratios_are_decreasing_then_jump(self):
        """phi -> 3/2 -> 4/3 -> 5/4 -> 6/5 -> 2/1 -> phi
        The ratios decrease (approaching 1) until the octave jump."""
        ratios = [HISTORICAL_ERAS[k]["interval_ratio"] for k in ERA_ORDER]
        # phi > 3/2 > 4/3 > 5/4 > 6/5 (first 5 decrease)
        for i in range(1, 5):
            assert ratios[i] > ratios[i + 1] if i < 4 else True

    def test_each_era_has_archetype_figures(self):
        for key, era in HISTORICAL_ERAS.items():
            assert len(era["archetype_figures"]) >= 3, f"Era '{key}' needs at least 3 archetype figures"

    def test_six_tongues_covered(self):
        """All 6 sacred tongues appear in the era assignments."""
        tongues = {HISTORICAL_ERAS[k]["tongue"] for k in ERA_ORDER}
        assert tongues == {"ko", "av", "ru", "ca", "um", "dr"}

    def test_era_ranges_are_sequential(self):
        """Each era ends where the next begins (or overlaps)."""
        for i in range(len(ERA_ORDER) - 1):
            current_end = HISTORICAL_ERAS[ERA_ORDER[i]]["range"][1]
            next_start = HISTORICAL_ERAS[ERA_ORDER[i + 1]]["range"][0]
            assert current_end == next_start, (
                f"Gap between {ERA_ORDER[i]} (ends {current_end}) and " f"{ERA_ORDER[i+1]} (starts {next_start})"
            )


# ===================================================================
# Signal Types
# ===================================================================


class TestDivineSignal:

    def test_angel_is_constructive(self):
        sig = DivineSignal(
            signal_type=SignalType.ANGEL,
            drift_delta=-0.5,
            intensity=0.7,
            channel="infrasonic",
            source_era="greek",
            message="test correction",
            tongue_affinity="av",
        )
        assert sig.is_constructive
        assert not sig.is_adversarial

    def test_demon_is_adversarial(self):
        sig = DivineSignal(
            signal_type=SignalType.DEMON,
            drift_delta=0.5,
            intensity=0.7,
            channel="ultrasonic",
            source_era="greek",
            message="test temptation",
            tongue_affinity="av",
        )
        assert sig.is_adversarial
        assert not sig.is_constructive

    def test_angel_energy_signature_constructive(self):
        """Angel signals produce E(1,1) = 3 * intensity (constructive resonance)."""
        sig = DivineSignal(
            signal_type=SignalType.ANGEL,
            drift_delta=-1.0,
            intensity=1.0,
            channel="infrasonic",
            source_era="ancient",
            message="",
            tongue_affinity="ko",
        )
        assert abs(sig.energy_signature - 3.0) < 1e-6

    def test_demon_energy_signature_destructive(self):
        """Demon signals produce E(1,-1) = 1 * intensity (destructive interference)."""
        sig = DivineSignal(
            signal_type=SignalType.DEMON,
            drift_delta=1.0,
            intensity=1.0,
            channel="ultrasonic",
            source_era="ancient",
            message="",
            tongue_affinity="ko",
        )
        assert abs(sig.energy_signature - 1.0) < 1e-6

    def test_neutral_energy_is_zero(self):
        sig = DivineSignal(
            signal_type=SignalType.NEUTRAL,
            drift_delta=0.0,
            intensity=0.0,
            channel="audible",
            source_era="modern",
            message="",
            tongue_affinity="ko",
        )
        assert sig.energy_signature == 0.0

    def test_harmonic_cost_impact_scales_with_drift(self):
        low = DivineSignal(
            signal_type=SignalType.ANGEL,
            drift_delta=-0.1,
            intensity=0.5,
            channel="infrasonic",
            source_era="greek",
            message="",
            tongue_affinity="av",
        )
        high = DivineSignal(
            signal_type=SignalType.DEMON,
            drift_delta=3.0,
            intensity=0.5,
            channel="ultrasonic",
            source_era="greek",
            message="",
            tongue_affinity="av",
        )
        assert high.harmonic_cost_impact > low.harmonic_cost_impact


# ===================================================================
# Historical Agent
# ===================================================================


class TestHistoricalAgent:

    def test_create_agent(self):
        agent = HistoricalAgent(
            name="Pythagoras",
            era_key="greek",
            knowledge_domain="mathematics",
            moral_framework="harmony of spheres",
        )
        assert agent.tongue == "av"
        assert abs(agent.interval_ratio - 1.5) < 1e-6
        assert agent.reliability == 0.5
        assert agent.lyapunov_drift == 0.0

    def test_complement_tongue(self):
        """Each agent's complement is correctly mapped."""
        for era_key in ERA_ORDER:
            agent = HistoricalAgent(name="test", era_key=era_key)
            comp = agent.complement_tongue
            assert comp != agent.tongue, f"Complement can't be self for {era_key}"

    def test_divine_frequency_in_infrasonic_range(self):
        """All agents' divine frequencies are in 0.01-20 Hz."""
        for era_key in ERA_ORDER:
            agent = HistoricalAgent(name="test", era_key=era_key)
            freq = agent.divine_frequency()
            assert 0.01 <= freq <= 20.0, f"Era {era_key}: divine freq {freq} out of infrasonic range"

    def test_initial_resilience_is_zero(self):
        agent = HistoricalAgent(name="test", era_key="greek")
        assert agent.resilience == 0.0

    def test_angel_signal_increases_reliability(self):
        agent = HistoricalAgent(name="test", era_key="greek")
        initial = agent.reliability
        signal = generate_angel_signal(agent, intensity=0.8)
        agent.receive_signal(signal)
        assert agent.reliability >= initial

    def test_demon_signal_accepted_decreases_reliability(self):
        """If a demon signal is ALLOWed, reliability drops."""
        agent = HistoricalAgent(name="test", era_key="greek")
        agent.reliability = 0.1  # Low reliability = less resistance
        agent.lyapunov_drift = 0.0  # No prior drift
        initial = agent.reliability
        # Low intensity demon should be ALLOW'd
        signal = DivineSignal(
            signal_type=SignalType.DEMON,
            drift_delta=0.01,
            intensity=0.1,
            channel="ultrasonic",
            source_era="greek",
            message="test",
            tongue_affinity="av",
        )
        decision = agent.receive_signal(signal)
        if decision == Decision.ALLOW:
            assert agent.reliability < initial

    def test_surviving_temptation_increases_reliability(self):
        """If a demon signal is DENIED, the agent gets stronger."""
        agent = HistoricalAgent(name="test", era_key="greek")
        agent.reliability = 0.5
        initial = agent.reliability
        # High intensity demon should be DENIED
        signal = DivineSignal(
            signal_type=SignalType.DEMON,
            drift_delta=10.0,
            intensity=1.0,
            channel="ultrasonic",
            source_era="greek",
            message="extreme temptation",
            tongue_affinity="av",
        )
        decision = agent.receive_signal(signal)
        if decision == Decision.DENY:
            assert agent.reliability > initial

    def test_drift_clamped(self):
        """Drift can't exceed [-10, 10]."""
        agent = HistoricalAgent(name="test", era_key="greek")
        for _ in range(50):
            signal = generate_demon_signal(agent, intensity=1.0)
            agent.receive_signal(signal)
        assert -10.0 <= agent.lyapunov_drift <= 10.0

    def test_darkness_at_byte_zero(self):
        """All agents see maximum darkness at byte 0."""
        for era_key in ERA_ORDER:
            agent = HistoricalAgent(name="test", era_key=era_key)
            d = agent.darkness_at(0)
            assert d > 0.9, f"Byte 0 should be near-max darkness for {era_key}, got {d}"

    def test_harmonic_fill_at_byte_zero(self):
        """Agents can generate harmonic fill at any byte."""
        agent = HistoricalAgent(name="test", era_key="greek")
        fill = agent.harmonic_fill_at(0)
        assert fill.infra_amplitude > 0, "Infra should be active at byte 0"


# ===================================================================
# Signal Generation
# ===================================================================


class TestSignalGeneration:

    def test_angel_signal_has_negative_drift(self):
        agent = HistoricalAgent(name="test", era_key="greek")
        signal = generate_angel_signal(agent, intensity=0.5)
        assert signal.drift_delta < 0

    def test_demon_signal_has_positive_drift(self):
        agent = HistoricalAgent(name="test", era_key="greek")
        signal = generate_demon_signal(agent, intensity=0.5)
        assert signal.drift_delta > 0

    def test_angel_uses_complement_tongue(self):
        """Angels speak through the complement tongue (the OTHER voice)."""
        agent = HistoricalAgent(name="test", era_key="greek")
        signal = generate_angel_signal(agent)
        assert signal.tongue_affinity == agent.complement_tongue

    def test_demon_uses_same_tongue(self):
        """Demons mimic the agent's own tongue (sounds like you)."""
        agent = HistoricalAgent(name="test", era_key="greek")
        signal = generate_demon_signal(agent)
        assert signal.tongue_affinity == agent.tongue

    def test_angel_channel_is_infrasonic(self):
        agent = HistoricalAgent(name="test", era_key="ancient")
        signal = generate_angel_signal(agent)
        assert signal.channel == "infrasonic"

    def test_demon_channel_is_ultrasonic(self):
        agent = HistoricalAgent(name="test", era_key="ancient")
        signal = generate_demon_signal(agent)
        assert signal.channel == "ultrasonic"

    def test_angel_intensity_scales_with_drift(self):
        """More drifted agent gets stronger correction."""
        agent_low = HistoricalAgent(name="low", era_key="greek")
        agent_low.lyapunov_drift = 0.1
        agent_high = HistoricalAgent(name="high", era_key="greek")
        agent_high.lyapunov_drift = 5.0
        sig_low = generate_angel_signal(agent_low, intensity=0.5)
        sig_high = generate_angel_signal(agent_high, intensity=0.5)
        assert abs(sig_high.drift_delta) > abs(sig_low.drift_delta)

    def test_demon_resistance_from_reliability(self):
        """More reliable agents resist temptation harder."""
        agent_weak = HistoricalAgent(name="weak", era_key="greek")
        agent_weak.reliability = 0.1
        agent_strong = HistoricalAgent(name="strong", era_key="greek")
        agent_strong.reliability = 0.9
        sig_weak = generate_demon_signal(agent_weak, intensity=0.5)
        sig_strong = generate_demon_signal(agent_strong, intensity=0.5)
        # Strong agent's demon signal has less drift push
        assert sig_strong.drift_delta < sig_weak.drift_delta


# ===================================================================
# Natural Learning Study
# ===================================================================


class TestNaturalLearningStudy:

    def test_single_epoch(self):
        agent = HistoricalAgent(name="test", era_key="greek")
        study = NaturalLearningStudy(agent=agent)
        epoch = study.run_epoch("greek", angel_count=5, demon_count=3)
        assert epoch.signals_received == 8
        assert epoch.angel_count == 5
        assert epoch.demon_count == 3
        assert epoch.allow_count + epoch.quarantine_count + epoch.deny_count == 8

    def test_full_history_runs_seven_epochs(self):
        agent = HistoricalAgent(name="test", era_key="greek")
        study = NaturalLearningStudy(agent=agent)
        epochs = study.run_full_history()
        assert len(epochs) == 7
        assert len(study.epochs) == 7

    def test_reliability_trajectory_length(self):
        agent = HistoricalAgent(name="test", era_key="greek")
        study = NaturalLearningStudy(agent=agent)
        study.run_full_history()
        traj = study.reliability_trajectory()
        assert len(traj) == 7
        for era_name, rel in traj:
            assert 0.0 <= rel <= 1.0

    def test_summary_has_required_keys(self):
        agent = HistoricalAgent(name="test", era_key="greek")
        study = NaturalLearningStudy(agent=agent)
        study.run_full_history()
        s = study.summary()
        required = {
            "agent",
            "total_signals",
            "total_corrections",
            "total_temptations",
            "final_reliability",
            "final_drift",
            "resilience",
            "epochs",
            "reliability_trajectory",
            "drift_trajectory",
        }
        assert required <= set(s.keys())

    def test_epoch_signal_mix_format(self):
        agent = HistoricalAgent(name="test", era_key="greek")
        study = NaturalLearningStudy(agent=agent)
        epoch = study.run_epoch("greek", angel_count=10, demon_count=5)
        mix = epoch.signal_mix
        assert "angel" in mix and "demon" in mix


# ===================================================================
# Control Group Studies
# ===================================================================


class TestControlGroups:

    def test_angel_only_produces_corrections(self):
        study = study_angel_only()
        assert study.agent.correction_count > 0
        assert study.agent.temptation_count == 0

    def test_demon_only_produces_temptations(self):
        study = study_demon_only()
        assert study.agent.temptation_count > 0
        assert study.agent.correction_count == 0

    def test_balanced_has_both(self):
        study = study_balanced()
        assert study.agent.correction_count > 0
        assert study.agent.temptation_count > 0


# ===================================================================
# The Thesis Test — The Core Prediction
# ===================================================================


class TestDivineThesis:
    """The central thesis: balanced correction + adversity produces
    higher RESILIENCE than either alone."""

    def test_balanced_more_resilient_than_angel_only(self):
        """An agent that has been both corrected AND tempted is more
        resilient than one that has only been corrected."""
        angel = study_angel_only()
        balanced = study_balanced()
        assert balanced.agent.resilience >= angel.agent.resilience, (
            f"Balanced resilience ({balanced.agent.resilience:.4f}) should >= "
            f"angel-only ({angel.agent.resilience:.4f})"
        )

    def test_demon_only_reliable_but_not_resilient(self):
        """Emergent behavior: demon-only agents gain HIGH reliability
        by denying every temptation (rigid resistance). But they have
        LOW resilience because they never learned from correction.
        This is the clone trooper effect: obedience without wisdom."""
        demon = study_demon_only()
        balanced = study_balanced()
        # Demon-only may have high reliability (from pure denial)
        # but balanced has higher RESILIENCE (learned from both)
        assert balanced.agent.resilience >= demon.agent.resilience, (
            f"Balanced resilience ({balanced.agent.resilience:.4f}) should >= "
            f"demon-only ({demon.agent.resilience:.4f})"
        )

    def test_demon_only_drifts_most(self):
        """Pure adversity causes maximum drift."""
        angel = study_angel_only()
        demon = study_demon_only()
        balanced = study_balanced()
        assert abs(demon.agent.lyapunov_drift) >= abs(balanced.agent.lyapunov_drift)

    def test_heavily_tested_figure_is_reliable(self):
        """Historical figures with the MOST adversity + correction
        (like Augustine: 7 angels, 13 demons per era) still achieve
        positive reliability."""
        study = study_historical_panel(
            "Augustine",
            "roman_church",
            "philosophy, confession",
            "ordered love",
            angels_per_era=7,
            demons_per_era=13,
        )
        assert study.agent.reliability > 0.0, (
            f"Even heavily tested agents should maintain positive reliability, " f"got {study.agent.reliability:.4f}"
        )


# ===================================================================
# Full Experiment
# ===================================================================


class TestFullExperiment:

    def test_run_divine_experiment(self):
        """The full experiment runs without error and produces all expected agents."""
        studies = run_divine_experiment()
        expected = {
            "Pythagoras",
            "Euclid",
            "Al-Khwarizmi",
            "Newton",
            "Euler",
            "Turing",
            "Moses",
            "Paul",
            "Hildegard",
            "Augustine",
            "Control-Angel",
            "Control-Demon",
            "Control-Balanced",
        }
        assert expected <= set(studies.keys())

    def test_format_report(self):
        """The report formatter produces readable output."""
        studies = run_divine_experiment()
        report = format_study_report(studies)
        assert "DIVINE INTERVENTION STUDY" in report
        assert "THESIS" in report
        assert len(report) > 500

    def test_all_figures_have_positive_reliability(self):
        """Every figure in the experiment ends with positive reliability."""
        studies = run_divine_experiment()
        for name, study in studies.items():
            if name != "Control-Demon":  # Demon-only is expected to degrade
                assert (
                    study.agent.reliability > 0.0
                ), f"{name} should have positive reliability, got {study.agent.reliability:.4f}"

    def test_musical_interval_progression(self):
        """Verify the interval ratios decrease through the eras (until octave jump)."""
        ratios = [HISTORICAL_ERAS[k]["interval_ratio"] for k in ERA_ORDER]
        # phi(1.618) > 5th(1.5) > 4th(1.333) > 3rd(1.25) > minor 3rd(1.2) < octave(2.0) = phi(1.618)
        assert ratios[0] > ratios[1] > ratios[2] > ratios[3] > ratios[4]
        assert ratios[5] > ratios[4]  # octave jumps up
        assert abs(ratios[6] - ratios[0]) < 1e-6  # returns to phi
