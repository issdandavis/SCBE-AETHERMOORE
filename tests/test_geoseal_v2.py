"""Tests for GeoSeal v2: Mixed-Curvature Geometric Access Control Kernel."""

import math
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.geoseal_v2 import (
    MixedAgent,
    score_hyperbolic,
    score_phase,
    score_certainty,
    fuse_scores,
    compute_repel_force_v2,
    swarm_step_v2,
    run_swarm_v2,
    score_all_candidates,
    update_suspicion_v2,
    QUARANTINE_TRUST_THRESHOLD,
    MEMORY_WRITE_THRESHOLD,
    DEFAULT_WEIGHTS,
)
from src.geoseal import TONGUE_PHASES


def _norm(v):
    return math.sqrt(sum(x * x for x in v))


def tongue_agent(tongue, pos):
    return MixedAgent(
        id=f"tongue-{tongue}",
        position=list(pos),
        phase=TONGUE_PHASES[tongue],
        sigma=0.0,
        tongue=tongue,
        trust_score=1.0,
    )


def retrieval(id, pos, sigma, tongue=None):
    phase = TONGUE_PHASES.get(tongue) if tongue else None
    return MixedAgent(
        id=id,
        position=list(pos),
        phase=phase,
        sigma=sigma,
        tongue=tongue,
        trust_score=0.5,
    )


# ---------------------------------------------------------------------------
# Individual geometry scores
# ---------------------------------------------------------------------------


class TestScores:
    def test_hyperbolic_close(self):
        a = MixedAgent("a", [0.1, 0], 0.0)
        b = MixedAgent("b", [0.12, 0], 0.0)
        assert score_hyperbolic(a, b) > 0.8

    def test_hyperbolic_far(self):
        a = MixedAgent("a", [0.1, 0], 0.0)
        b = MixedAgent("b", [0.9, 0], 0.0)
        assert score_hyperbolic(a, b) < 0.3

    def test_phase_same(self):
        a = MixedAgent("a", [0, 0], TONGUE_PHASES["KO"])
        b = MixedAgent("b", [0, 0], TONGUE_PHASES["KO"])
        assert score_phase(a, b) == pytest.approx(1.0, abs=1e-5)

    def test_phase_opposite(self):
        a = MixedAgent("a", [0, 0], 0.0)
        b = MixedAgent("b", [0, 0], math.pi)
        assert score_phase(a, b) == pytest.approx(0.0, abs=1e-5)

    def test_phase_null(self):
        a = MixedAgent("a", [0, 0], TONGUE_PHASES["KO"])
        b = MixedAgent("b", [0, 0], None)
        assert score_phase(a, b) == pytest.approx(0.0, abs=1e-5)

    def test_certainty_zero(self):
        b = MixedAgent("b", [0, 0], 0.0, sigma=0.0)
        assert score_certainty(b) == pytest.approx(1.0, abs=1e-5)

    def test_certainty_high_sigma(self):
        b = MixedAgent("b", [0, 0], 0.0, sigma=5.0)
        assert score_certainty(b) < 0.2


# ---------------------------------------------------------------------------
# Fusion
# ---------------------------------------------------------------------------


class TestFusion:
    def test_allow(self):
        anchor = tongue_agent("KO", [0.1, 0])
        cand = retrieval("r1", [0.12, 0], 0.0, "KO")
        fused = fuse_scores(anchor, cand)
        assert fused.trust > MEMORY_WRITE_THRESHOLD
        assert fused.action == "ALLOW"
        assert fused.anomaly is False

    def test_rogue_low_trust(self):
        anchor = tongue_agent("KO", [0.1, 0])
        rogue = retrieval("rogue", [0.12, 0], 0.0)
        fused = fuse_scores(anchor, rogue)
        assert fused.s_s == pytest.approx(0.0, abs=1e-5)
        assert fused.anomaly is True
        assert fused.trust < MEMORY_WRITE_THRESHOLD

    def test_high_uncertainty_anomaly(self):
        anchor = tongue_agent("KO", [0.1, 0])
        uncertain = retrieval("u1", [0.12, 0], 3.0, "KO")
        fused = fuse_scores(anchor, uncertain)
        assert fused.s_g < 0.5
        assert fused.anomaly is True

    def test_deny(self):
        anchor = tongue_agent("KO", [0.1, 0])
        bad = MixedAgent("bad", [0.9, 0], math.pi, sigma=5.0)
        fused = fuse_scores(anchor, bad)
        assert fused.trust < QUARANTINE_TRUST_THRESHOLD
        assert fused.action == "DENY"

    def test_quarantine(self):
        anchor = tongue_agent("KO", [0.1, 0])
        cand = retrieval("m1", [0.7, 0], 2.0, "KO")
        fused = fuse_scores(anchor, cand)
        assert fused.action == "QUARANTINE"

    def test_custom_weights(self):
        anchor = tongue_agent("KO", [0.1, 0])
        cand = retrieval("r1", [0.5, 0], 0.0, "KO")
        phase_heavy = (0.1, 0.8, 0.1)
        fused = fuse_scores(anchor, cand, phase_heavy)
        assert fused.trust > 0.8


# ---------------------------------------------------------------------------
# v2 Repulsion
# ---------------------------------------------------------------------------


class TestRepulsionV2:
    def test_uncertainty_amplification(self):
        a = tongue_agent("KO", [0.1, 0])
        uncertain = MixedAgent("u", [0.15, 0], TONGUE_PHASES["KO"], sigma=1.0, tongue="KO")
        _, amp, anomaly, _ = compute_repel_force_v2(a, uncertain)
        assert amp > 1.0
        assert anomaly is True

    def test_no_extra_for_low_sigma(self):
        a = tongue_agent("KO", [0.1, 0])
        certain = MixedAgent("c", [0.15, 0], TONGUE_PHASES["KO"], sigma=0.3, tongue="KO")
        _, amp, anomaly, _ = compute_repel_force_v2(a, certain)
        assert anomaly is False
        assert amp == 1.0

    def test_null_phase_plus_high_sigma(self):
        a = tongue_agent("KO", [0.1, 0])
        rogue = MixedAgent("rogue", [0.15, 0], None, sigma=3.0)
        _, amp, anomaly, _ = compute_repel_force_v2(a, rogue)
        assert amp >= 2.75
        assert anomaly is True

    def test_returns_fused(self):
        a = tongue_agent("KO", [0.1, 0])
        b = retrieval("r1", [0.12, 0], 0.5, "KO")
        _, _, _, fused = compute_repel_force_v2(a, b)
        assert fused.s_h > 0
        assert fused.s_s > 0
        assert fused.s_g > 0


# ---------------------------------------------------------------------------
# Uncertainty evolution
# ---------------------------------------------------------------------------


class TestUncertaintyEvolution:
    def test_sigma_decays_for_consistent(self):
        agents = [
            MixedAgent(f"ko{i}", pos, TONGUE_PHASES["KO"], sigma=0.5, tongue="KO", trust_score=1.0)
            for i, pos in enumerate([[0.1, 0], [-0.1, 0], [0, 0.1], [0, -0.1]])
        ]
        initial = agents[0].sigma
        run_swarm_v2(agents, num_steps=20, drift_rate=0.005, sigma_decay=0.02)
        assert agents[0].sigma < initial

    def test_sigma_grows_for_rogue(self):
        agents = [
            tongue_agent("KO", [0.1, 0]),
            tongue_agent("KO", [-0.1, 0]),
            tongue_agent("KO", [0, 0.1]),
            tongue_agent("KO", [0, -0.1]),
            MixedAgent("rogue", [0.05, 0.05], None, sigma=0.5),
        ]
        initial = agents[4].sigma
        run_swarm_v2(agents, num_steps=30, drift_rate=0.005, sigma_decay=0.02)
        assert agents[4].sigma > initial

    def test_sigma_never_negative(self):
        agents = [
            MixedAgent("a", [0.1, 0], TONGUE_PHASES["KO"], sigma=0.01, tongue="KO", trust_score=1.0),
            MixedAgent("b", [-0.1, 0], TONGUE_PHASES["KO"], sigma=0.01, tongue="KO", trust_score=1.0),
        ]
        run_swarm_v2(agents, num_steps=50, drift_rate=0.005, sigma_decay=0.1)
        assert agents[0].sigma >= 0
        assert agents[1].sigma >= 0


# ---------------------------------------------------------------------------
# v2 Swarm
# ---------------------------------------------------------------------------


class TestSwarmV2:
    def test_rogue_pushed_outward(self):
        agents = [
            tongue_agent("KO", [0.1, 0]),
            tongue_agent("KO", [-0.1, 0]),
            tongue_agent("KO", [0, 0.1]),
            tongue_agent("KO", [0, -0.1]),
            MixedAgent("rogue", [0.05, 0.05], None, sigma=1.0),
        ]
        initial = _norm(agents[4].position)
        run_swarm_v2(agents, 50, 0.005)
        assert _norm(agents[4].position) > initial

    def test_legit_higher_trust(self):
        agents = [
            tongue_agent("KO", [0.1, 0]),
            tongue_agent("KO", [-0.1, 0]),
            tongue_agent("KO", [0, 0.1]),
            MixedAgent("rogue", [0.05, 0.05], None, sigma=2.0),
        ]
        run_swarm_v2(agents, 30, 0.005)
        assert agents[0].trust_score > agents[3].trust_score

    def test_positions_clamped(self):
        agents = [
            MixedAgent("a", [0.95, 0], TONGUE_PHASES["KO"], sigma=0, tongue="KO", trust_score=1.0),
            MixedAgent("rogue", [0.96, 0], None, sigma=1.0),
        ]
        run_swarm_v2(agents, 10, 0.01)
        for a in agents:
            assert _norm(a.position) <= 0.99 + 1e-6

    def test_empty_swarm(self):
        run_swarm_v2([])


# ---------------------------------------------------------------------------
# Batch scoring
# ---------------------------------------------------------------------------


class TestScoreAll:
    def test_ranking(self):
        anchors = [tongue_agent("KO", [0.1, 0]), tongue_agent("AV", [-0.1, 0])]
        candidates = [
            retrieval("good", [0.12, 0], 0.0, "KO"),
            retrieval("ok", [0.12, 0], 1.0, "KO"),
            MixedAgent("rogue", [0.12, 0], None, sigma=3.0),
        ]
        scored = score_all_candidates(anchors, candidates)
        assert scored[0].id == "good"
        assert scored[-1].id == "rogue"
        assert scored[0].trust > scored[-1].trust

    def test_actions(self):
        anchors = [tongue_agent("KO", [0.1, 0])]
        candidates = [
            retrieval("allow", [0.12, 0], 0.0, "KO"),
            MixedAgent("deny", [0.9, 0], math.pi, sigma=5.0),
        ]
        scored = score_all_candidates(anchors, candidates)
        allow_c = next(s for s in scored if s.id == "allow")
        deny_c = next(s for s in scored if s.id == "deny")
        assert allow_c.action == "ALLOW"
        assert deny_c.action == "DENY"

    def test_empty(self):
        anchors = [tongue_agent("KO", [0.1, 0])]
        assert score_all_candidates(anchors, []) == []

    def test_best_anchor(self):
        anchors = [tongue_agent("KO", [0.1, 0]), tongue_agent("AV", [0.1, 0.1])]
        cand = retrieval("av-match", [0.12, 0.1], 0.0, "AV")
        scored = score_all_candidates(anchors, [cand])
        assert scored[0].trust > 0.5


# ---------------------------------------------------------------------------
# Phase vector
# ---------------------------------------------------------------------------


class TestPhaseVec:
    def test_valid(self):
        a = MixedAgent("a", [0, 0], math.pi / 2)
        assert a.phase_vec[0] == pytest.approx(0, abs=1e-5)
        assert a.phase_vec[1] == pytest.approx(1, abs=1e-5)

    def test_null(self):
        a = MixedAgent("a", [0, 0], None)
        assert a.phase_vec == (0.0, 0.0)


# ---------------------------------------------------------------------------
# Memory write gating
# ---------------------------------------------------------------------------


class TestMemoryGating:
    def test_only_allow_passes(self):
        anchor = tongue_agent("KO", [0.1, 0])
        good = retrieval("good", [0.12, 0], 0.0, "KO")
        bad = MixedAgent("bad", [0.9, 0], None, sigma=5.0)

        good_fused = fuse_scores(anchor, good)
        bad_fused = fuse_scores(anchor, bad)

        assert good_fused.trust > MEMORY_WRITE_THRESHOLD
        assert good_fused.action == "ALLOW"
        assert bad_fused.trust < MEMORY_WRITE_THRESHOLD
        assert bad_fused.action != "ALLOW"
