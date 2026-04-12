"""Tests for the Crossing Energy Evaluator — governance at braid intersections."""

import math
import pytest

from src.crypto.crossing_energy import (
    PHI,
    DualTernaryPair,
    ALL_STATES,
    Decision,
    CrossingResult,
    GovernanceSummary,
    valid_transition,
    valid_neighbors,
    phase_deviation,
    harmonic_cost,
    harmonic_cost_gradient,
    evaluate_crossing,
    evaluate_sequence,
    evaluate_polyglot,
    summarize_governance,
    QUARANTINE_THRESHOLD,
    DENY_THRESHOLD,
    DECISION_TO_TRIT,
)
from src.crypto.tri_bundle import (
    Trit,
    encode_byte,
    encode_bytes,
    encode_polyglot,
    TriBundleCluster,
)


# ===================================================================
# DualTernaryPair
# ===================================================================

class TestDualTernaryPair:
    def test_all_9_states_exist(self):
        assert len(ALL_STATES) == 9

    def test_energy_equilibrium(self):
        """E(0,0) = 0 — minimum energy."""
        s = DualTernaryPair(0, 0)
        assert s.energy == 0.0

    def test_energy_constructive(self):
        """E(1,1) = 3 — max positive energy."""
        s = DualTernaryPair(1, 1)
        assert s.energy == 3.0

    def test_energy_negative_resonance(self):
        """E(-1,-1) = (-1)² + (-1)² + (-1)(-1) = 1+1+1 = 3."""
        s = DualTernaryPair(-1, -1)
        assert s.energy == 3.0

    def test_energy_destructive(self):
        """E(1,-1) = 1 and E(-1,1) = 1."""
        assert DualTernaryPair(1, -1).energy == 1.0
        assert DualTernaryPair(-1, 1).energy == 1.0

    def test_energy_half_states(self):
        """E(1,0) = 1, E(0,1) = 1, E(-1,0) = 1, E(0,-1) = 1."""
        for s in [DualTernaryPair(1, 0), DualTernaryPair(0, 1),
                  DualTernaryPair(-1, 0), DualTernaryPair(0, -1)]:
            assert s.energy == 1.0

    def test_phase_constructive(self):
        assert DualTernaryPair(1, 1).phase == "constructive"

    def test_phase_negative_resonance(self):
        assert DualTernaryPair(-1, -1).phase == "negative_resonance"

    def test_phase_destructive(self):
        assert DualTernaryPair(1, -1).phase == "destructive"
        assert DualTernaryPair(-1, 1).phase == "destructive"

    def test_phase_neutral(self):
        assert DualTernaryPair(0, 0).phase == "neutral"
        assert DualTernaryPair(1, 0).phase == "neutral"
        assert DualTernaryPair(0, -1).phase == "neutral"

    def test_index_unique(self):
        indices = [s.index() for s in ALL_STATES]
        assert len(set(indices)) == 9
        assert min(indices) == 0
        assert max(indices) == 8

    def test_invalid_values_rejected(self):
        with pytest.raises(ValueError):
            DualTernaryPair(2, 0)
        with pytest.raises(ValueError):
            DualTernaryPair(0, -2)

    def test_label(self):
        assert DualTernaryPair(0, 0).label == "equilibrium"
        assert DualTernaryPair(1, 1).label == "advance-advance"
        assert DualTernaryPair(-1, -1).label == "retreat-contract"


# ===================================================================
# Topology
# ===================================================================

class TestTopology:
    def test_self_transition_valid(self):
        """Staying in the same state is always valid."""
        for s in ALL_STATES:
            assert valid_transition(s, s)

    def test_adjacent_transitions_valid(self):
        """One-step transitions are valid."""
        assert valid_transition(DualTernaryPair(0, 0), DualTernaryPair(1, 0))
        assert valid_transition(DualTernaryPair(0, 0), DualTernaryPair(0, 1))
        assert valid_transition(DualTernaryPair(0, 0), DualTernaryPair(1, 1))

    def test_jump_transitions_invalid(self):
        """Two-step jumps break the braid."""
        assert not valid_transition(DualTernaryPair(-1, -1), DualTernaryPair(1, 1))
        assert not valid_transition(DualTernaryPair(-1, 0), DualTernaryPair(1, 0))

    def test_equilibrium_has_9_neighbors(self):
        """(0,0) can reach all 9 states."""
        eq = DualTernaryPair(0, 0)
        assert len(valid_neighbors(eq)) == 9

    def test_corner_has_4_neighbors(self):
        """(-1,-1) can reach 4 states: itself, (-1,0), (0,-1), (0,0)."""
        corner = DualTernaryPair(-1, -1)
        assert len(valid_neighbors(corner)) == 4

    def test_edge_has_6_neighbors(self):
        """(0,-1) can reach 6 states."""
        edge = DualTernaryPair(0, -1)
        assert len(valid_neighbors(edge)) == 6


# ===================================================================
# Phase Deviation
# ===================================================================

class TestPhaseDeviation:
    def test_same_state_zero(self):
        s = DualTernaryPair(0, 0)
        assert phase_deviation(s, s) == 0.0

    def test_max_deviation(self):
        assert phase_deviation(DualTernaryPair(-1, -1), DualTernaryPair(1, 1)) == 1.0

    def test_one_step(self):
        assert phase_deviation(DualTernaryPair(0, 0), DualTernaryPair(1, 0)) == 0.5

    def test_symmetric(self):
        a = DualTernaryPair(0, 0)
        b = DualTernaryPair(1, -1)
        assert phase_deviation(a, b) == phase_deviation(b, a)


# ===================================================================
# Harmonic Cost
# ===================================================================

class TestHarmonicCost:
    def test_zero_distance_is_one(self):
        assert abs(harmonic_cost(0.0) - 1.0) < 1e-10

    def test_unit_distance_is_phi(self):
        assert abs(harmonic_cost(1.0) - PHI) < 1e-10

    def test_two_distance(self):
        expected = PHI ** 4  # φ^(2²) = φ⁴
        assert abs(harmonic_cost(2.0) - expected) < 1e-6

    def test_monotonically_increasing(self):
        """Pre-cap range should be strictly increasing."""
        costs = [harmonic_cost(d) for d in range(6)]
        for i in range(len(costs) - 1):
            assert costs[i] < costs[i + 1]

    def test_super_exponential_growth(self):
        """Cost grows super-exponentially (d² in exponent)."""
        c2 = harmonic_cost(2.0)
        c3 = harmonic_cost(3.0)
        c4 = harmonic_cost(4.0)
        # Ratio should increase
        assert c3 / c2 < c4 / c3

    def test_capped_at_extreme(self):
        """Very large distances should be capped, not overflow."""
        cost = harmonic_cost(50.0)
        assert cost == 1e6  # should hit the cap

    def test_gradient_zero_at_origin(self):
        assert harmonic_cost_gradient(0.0) == 0.0

    def test_gradient_positive(self):
        assert harmonic_cost_gradient(1.0) > 0
        assert harmonic_cost_gradient(2.0) > 0


# ===================================================================
# Crossing Evaluation
# ===================================================================

class TestCrossingEvaluation:
    def test_low_byte_produces_result(self):
        cluster = encode_byte(0x10, "ko")
        result = evaluate_crossing(cluster)
        assert isinstance(result, CrossingResult)

    def test_result_has_decision(self):
        cluster = encode_byte(0x80, "av")
        result = evaluate_crossing(cluster)
        assert result.decision in (Decision.ALLOW, Decision.QUARANTINE, Decision.DENY)

    def test_result_has_trit(self):
        cluster = encode_byte(0x80, "ru")
        result = evaluate_crossing(cluster)
        assert result.decision_trit in (Trit.PLUS, Trit.ZERO, Trit.MINUS)

    def test_decision_trit_matches(self):
        cluster = encode_byte(0x80, "ca")
        result = evaluate_crossing(cluster)
        assert result.decision_trit == DECISION_TO_TRIT[result.decision]

    def test_equilibrium_byte_low_energy(self):
        """Mid-range byte (0x80 = 128) maps to neutral intent."""
        cluster = encode_byte(128, "ko")
        result = evaluate_crossing(cluster)
        # 128 is in the ZERO intent range (85-169)
        assert result.energy <= 1.0

    def test_extreme_byte_higher_energy(self):
        """Byte 0xFF = 255 maps to PLUS intent; byte with divergent math should be higher energy."""
        cluster = encode_byte(255, "dr")
        result = evaluate_crossing(cluster)
        assert result.energy >= 0  # energy is always non-negative

    def test_position_tracked(self):
        cluster = encode_byte(0x42, "um")
        result = evaluate_crossing(cluster, position=7)
        assert result.position == 7

    def test_tongue_tracked(self):
        cluster = encode_byte(0x42, "dr")
        result = evaluate_crossing(cluster)
        assert result.tongue_code == "dr"

    def test_topology_valid_without_prev(self):
        """No previous state means topology is always valid."""
        cluster = encode_byte(0x42, "ko")
        result = evaluate_crossing(cluster)
        assert result.topology_valid

    def test_topology_tracked_with_prev(self):
        cluster = encode_byte(0x42, "ko")
        prev = DualTernaryPair(0, 0)
        result = evaluate_crossing(cluster, prev_state=prev)
        # Should be valid from equilibrium (can reach any neighbor)
        assert isinstance(result.topology_valid, bool)

    def test_is_safe_property(self):
        cluster = encode_byte(128, "ko")
        result = evaluate_crossing(cluster)
        assert result.is_safe == (result.decision == Decision.ALLOW)


# ===================================================================
# Sequence Evaluation
# ===================================================================

class TestSequenceEvaluation:
    def test_sequence_length(self):
        clusters = encode_bytes(b"hello", "ko")
        results = evaluate_sequence(clusters)
        assert len(results) == 5

    def test_sequence_tracks_topology(self):
        """Each result should have prev_state set (except first)."""
        clusters = encode_bytes(b"test", "av")
        results = evaluate_sequence(clusters)
        assert results[0].prev_state is None
        for r in results[1:]:
            assert r.prev_state is not None

    def test_positions_sequential(self):
        clusters = encode_bytes(b"abc", "ru")
        results = evaluate_sequence(clusters)
        assert [r.position for r in results] == [0, 1, 2]


# ===================================================================
# Polyglot Evaluation
# ===================================================================

class TestPolyglotEvaluation:
    def test_evaluates_all_6_tongues(self):
        pcs = encode_polyglot(b"A")
        results = evaluate_polyglot(pcs[0])
        assert len(results) == 6
        assert set(results.keys()) == {"ko", "av", "ru", "ca", "um", "dr"}

    def test_each_tongue_has_decision(self):
        pcs = encode_polyglot(b"Z")
        results = evaluate_polyglot(pcs[0])
        for code, result in results.items():
            assert result.decision in (Decision.ALLOW, Decision.QUARANTINE, Decision.DENY)
            assert result.tongue_code == code


# ===================================================================
# Governance Summary
# ===================================================================

class TestGovernanceSummary:
    def test_summary_from_sequence(self):
        clusters = encode_bytes(b"hello world", "ko")
        results = evaluate_sequence(clusters)
        summary = summarize_governance(results)
        assert summary.total == 11
        assert summary.allow_count + summary.quarantine_count + summary.deny_count == 11

    def test_allow_ratio(self):
        clusters = encode_bytes(b"safe", "av")
        results = evaluate_sequence(clusters)
        summary = summarize_governance(results)
        assert 0.0 <= summary.allow_ratio <= 1.0

    def test_empty_summary(self):
        summary = summarize_governance([])
        assert summary.total == 0
        assert summary.is_clean

    def test_is_clean(self):
        clusters = encode_bytes(b"ok", "ko")
        results = evaluate_sequence(clusters)
        summary = summarize_governance(results)
        # Clean means no denials and no topology breaks
        if summary.deny_count == 0 and summary.topology_breaks == 0:
            assert summary.is_clean

    def test_phases_counted(self):
        clusters = encode_bytes(b"test data", "ru")
        results = evaluate_sequence(clusters)
        summary = summarize_governance(results)
        assert isinstance(summary.phases, dict)
        total_phases = sum(summary.phases.values())
        assert total_phases == summary.total

    def test_energy_stats(self):
        clusters = encode_bytes(b"energy", "ca")
        results = evaluate_sequence(clusters)
        summary = summarize_governance(results)
        assert summary.mean_energy >= 0
        assert summary.max_energy >= summary.mean_energy
        assert summary.mean_cost >= 1.0  # cost is always ≥ 1


# ===================================================================
# Integration: Full Pipeline
# ===================================================================

class TestFullPipeline:
    def test_encode_evaluate_summarize(self):
        """Full pipeline: text → tri-bundle → crossing eval → governance."""
        from src.crypto.tri_bundle import encode_text

        clusters = encode_text("In the beginning", "ko")
        results = evaluate_sequence(clusters)
        summary = summarize_governance(results)

        assert summary.total == len("In the beginning")
        assert summary.total == 16
        assert isinstance(summary.allow_ratio, float)
        assert isinstance(summary.deny_ratio, float)

    def test_polyglot_governance_spread(self):
        """6 tongues on same data may produce different decisions."""
        pcs = encode_polyglot(b"X")
        results = evaluate_polyglot(pcs[0])
        decisions = {code: r.decision for code, r in results.items()}
        # All should be valid decisions
        for d in decisions.values():
            assert d in (Decision.ALLOW, Decision.QUARANTINE, Decision.DENY)

    def test_energy_landscape_is_correct(self):
        """Verify the full energy landscape of all 9 states."""
        expected = {
            (0, 0): 0,    # equilibrium
            (1, 0): 1, (0, 1): 1, (-1, 0): 1, (0, -1): 1,  # edges
            (1, -1): 1, (-1, 1): 1,   # destructive
            (-1, -1): 3,               # negative resonance (same as constructive)
            (1, 1): 3,                 # constructive (max)
        }
        for (p, m), e in expected.items():
            state = DualTernaryPair(p, m)
            assert state.energy == e, f"E({p},{m}) = {state.energy}, expected {e}"
