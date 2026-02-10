"""Tests for GeoSeal: Geometric Access Control Kernel."""

import math
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.geoseal import (
    Agent,
    TONGUE_PHASES,
    SUSPICION_THRESHOLD,
    QUARANTINE_CONSENSUS,
    hyperbolic_distance,
    phase_deviation,
    clamp_to_ball,
    compute_repel_force,
    update_suspicion,
    swarm_step,
    run_swarm,
    compute_metrics,
)


def _norm(v):
    return math.sqrt(sum(x * x for x in v))


def make_agent(id, pos, phase, tongue=None, trust=None):
    if trust is None:
        trust = 1.0 if phase is not None else 0.5
    return Agent(id=id, position=list(pos), phase=phase, tongue=tongue, trust_score=trust)


# ---------------------------------------------------------------------------
# Hyperbolic distance
# ---------------------------------------------------------------------------


class TestHyperbolicDistance:
    def test_identical_points(self):
        p = [0.1, 0.2, 0.3]
        assert hyperbolic_distance(p, p) == pytest.approx(0.0, abs=1e-6)

    def test_symmetric(self):
        u = [0.1, 0.2]
        v = [0.3, -0.1]
        assert hyperbolic_distance(u, v) == pytest.approx(
            hyperbolic_distance(v, u), abs=1e-10
        )

    def test_increases_with_separation(self):
        o = [0, 0, 0]
        near = [0.1, 0, 0]
        far = [0.5, 0, 0]
        assert hyperbolic_distance(o, near) < hyperbolic_distance(o, far)

    def test_large_near_boundary(self):
        assert hyperbolic_distance([0, 0], [0.98, 0]) > 3


# ---------------------------------------------------------------------------
# Phase deviation
# ---------------------------------------------------------------------------


class TestPhaseDeviation:
    def test_identical(self):
        assert phase_deviation(0, 0) == pytest.approx(0.0, abs=1e-10)

    def test_null(self):
        assert phase_deviation(None, 0.5) == 1.0
        assert phase_deviation(0.5, None) == 1.0
        assert phase_deviation(None, None) == 1.0

    def test_opposite(self):
        assert phase_deviation(0, math.pi) == pytest.approx(1.0, abs=1e-5)

    def test_wrap_around(self):
        assert phase_deviation(0.01, 2 * math.pi - 0.01) < 0.02

    def test_symmetric(self):
        p1 = math.pi / 4
        p2 = 3 * math.pi / 4
        assert phase_deviation(p1, p2) == pytest.approx(
            phase_deviation(p2, p1), abs=1e-10
        )


# ---------------------------------------------------------------------------
# Clamp to ball
# ---------------------------------------------------------------------------


class TestClampToBall:
    def test_inside_unchanged(self):
        v = [0.1, 0.2, 0.3]
        assert clamp_to_ball(v) == v

    def test_outside_clamped(self):
        v = [1.0, 1.0, 1.0]
        clamped = clamp_to_ball(v, 0.99)
        assert _norm(clamped) == pytest.approx(0.99, abs=1e-6)


# ---------------------------------------------------------------------------
# Repulsion force
# ---------------------------------------------------------------------------


class TestComputeRepelForce:
    def test_nonzero_between_agents(self):
        a = make_agent("a", [0.1, 0.0], TONGUE_PHASES["KO"], "KO")
        b = make_agent("b", [0.3, 0.0], TONGUE_PHASES["KO"], "KO")
        force, amp, anomaly = compute_repel_force(a, b)
        assert any(f != 0 for f in force)
        assert anomaly is False
        assert amp == 1.0

    def test_null_phase_2x(self):
        legit = make_agent("l", [0.1, 0.0], TONGUE_PHASES["KO"], "KO")
        rogue = make_agent("r", [0.15, 0.0], None)
        _, amp, anomaly = compute_repel_force(legit, rogue)
        assert amp == 2.0
        assert anomaly is True

    def test_phase_mismatch_close_range(self):
        a = make_agent("a", [0.1, 0.0], TONGUE_PHASES["KO"], "KO")
        b = make_agent("b", [0.15, 0.0], TONGUE_PHASES["CA"], "CA")
        _, amp, anomaly = compute_repel_force(a, b)
        assert amp > 1.5
        assert anomaly is True

    def test_same_phase_no_flag(self):
        a = make_agent("a", [0.1, 0.0], TONGUE_PHASES["KO"], "KO")
        b = make_agent("b", [0.15, 0.0], TONGUE_PHASES["KO"], "KO")
        _, amp, anomaly = compute_repel_force(a, b)
        assert anomaly is False
        assert amp == 1.0

    def test_quarantine_extra_1_5x(self):
        a = make_agent("a", [0.1, 0.0], TONGUE_PHASES["KO"], "KO")
        rogue = make_agent("r", [0.15, 0.0], None)
        rogue.is_quarantined = True
        _, amp, _ = compute_repel_force(a, rogue)
        assert amp == pytest.approx(3.0, abs=1e-5)


# ---------------------------------------------------------------------------
# Suspicion tracking
# ---------------------------------------------------------------------------


class TestSuspicion:
    def test_increment(self):
        a = make_agent("a", [0, 0], 0.0)
        update_suspicion(a, "b", True)
        assert a.suspicion_count["b"] == 1

    def test_decay(self):
        a = make_agent("a", [0, 0], 0.0)
        a.suspicion_count["b"] = 3.0
        update_suspicion(a, "b", False)
        assert a.suspicion_count["b"] == 2.5

    def test_no_negative(self):
        a = make_agent("a", [0, 0], 0.0)
        update_suspicion(a, "b", False)
        assert a.suspicion_count["b"] == 0

    def test_quarantine_3_neighbors(self):
        a = make_agent("a", [0, 0], 0.0)
        a.suspicion_count["n1"] = SUSPICION_THRESHOLD
        a.suspicion_count["n2"] = SUSPICION_THRESHOLD
        a.suspicion_count["n3"] = SUSPICION_THRESHOLD
        update_suspicion(a, "n4", False)
        assert a.is_quarantined is True

    def test_no_quarantine_2_neighbors(self):
        a = make_agent("a", [0, 0], 0.0)
        a.suspicion_count["n1"] = SUSPICION_THRESHOLD
        a.suspicion_count["n2"] = SUSPICION_THRESHOLD
        update_suspicion(a, "n3", False)
        assert a.is_quarantined is False

    def test_trust_score_update(self):
        a = make_agent("a", [0, 0], 0.0)
        a.suspicion_count["n1"] = 5.0
        a.suspicion_count["n2"] = 5.0
        update_suspicion(a, "n3", False)
        assert a.trust_score == pytest.approx(0.5, abs=0.1)


# ---------------------------------------------------------------------------
# Swarm dynamics
# ---------------------------------------------------------------------------


class TestSwarm:
    def test_rogue_pushed_outward(self):
        agents = [
            make_agent("ko1", [0.1, 0.0], TONGUE_PHASES["KO"], "KO"),
            make_agent("ko2", [-0.1, 0.0], TONGUE_PHASES["KO"], "KO"),
            make_agent("ko3", [0.0, 0.1], TONGUE_PHASES["KO"], "KO"),
            make_agent("ko4", [0.0, -0.1], TONGUE_PHASES["KO"], "KO"),
            make_agent("rogue", [0.05, 0.05], None),
        ]
        initial_norm = _norm(agents[4].position)
        run_swarm(agents, num_steps=50, drift_rate=0.005)
        final_norm = _norm(agents[4].position)
        assert final_norm > initial_norm

    def test_legit_higher_trust_than_rogue(self):
        agents = [
            make_agent("ko1", [0.1, 0.0], TONGUE_PHASES["KO"], "KO"),
            make_agent("ko2", [-0.1, 0.0], TONGUE_PHASES["KO"], "KO"),
            make_agent("rogue", [0.05, 0.05], None),
        ]
        run_swarm(agents, num_steps=20, drift_rate=0.005)
        assert agents[0].trust_score > agents[2].trust_score

    def test_positions_clamped(self):
        agents = [
            make_agent("a", [0.95, 0.0], TONGUE_PHASES["KO"], "KO"),
            make_agent("rogue", [0.96, 0.0], None),
        ]
        run_swarm(agents, num_steps=10, drift_rate=0.01)
        for a in agents:
            assert _norm(a.position) <= 0.99 + 1e-6

    def test_empty_swarm(self):
        run_swarm([], num_steps=5)  # Should not raise


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class TestMetrics:
    def test_basic_metrics(self):
        agents = [
            make_agent("ko1", [0.1, 0.0], TONGUE_PHASES["KO"], "KO"),
            make_agent("ko2", [-0.1, 0.0], TONGUE_PHASES["KO"], "KO"),
            make_agent("ko3", [0.0, 0.1], TONGUE_PHASES["KO"], "KO"),
            make_agent("ko4", [0.0, -0.1], TONGUE_PHASES["KO"], "KO"),
            make_agent("rogue", [0.05, 0.05], None),
        ]
        run_swarm(agents, num_steps=50, drift_rate=0.005)
        metrics = compute_metrics(agents, "rogue")
        assert "rogue" in metrics.final_trust_scores
        assert metrics.final_trust_scores["rogue"] < metrics.final_trust_scores["ko1"]

    def test_unknown_rogue_raises(self):
        agents = [make_agent("a", [0, 0], 0.0)]
        with pytest.raises(ValueError, match="not found"):
            compute_metrics(agents, "nonexistent")


# ---------------------------------------------------------------------------
# TONGUE_PHASES constants
# ---------------------------------------------------------------------------


class TestTonguePhases:
    def test_has_all_6(self):
        assert set(TONGUE_PHASES.keys()) == {"KO", "AV", "RU", "CA", "UM", "DR"}

    def test_evenly_spaced(self):
        phases = list(TONGUE_PHASES.values())
        for i in range(1, len(phases)):
            gap = phases[i] - phases[i - 1]
            assert gap == pytest.approx(math.pi / 3, abs=1e-5)

    def test_range(self):
        for phase in TONGUE_PHASES.values():
            assert 0 <= phase < 2 * math.pi
