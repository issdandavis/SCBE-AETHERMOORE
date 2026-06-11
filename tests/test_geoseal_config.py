"""GeoSeal hardening tests: GeoSealConfig tuning, dimension validation,
empty-anchor guard, and v2 parameter contracts.

Companion to tests/test_geoseal.py / test_geoseal_v2.py — covers the gaps
those suites left: parametrized thresholds, mismatched vector dimensions,
and silent-failure edges in batch scoring.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.geoseal import (  # noqa: E402
    DEFAULT_CONFIG,
    Agent,
    GeoSealConfig,
    compute_metrics,
    hyperbolic_distance,
    run_swarm,
    swarm_step,
    update_suspicion,
)
from src.geoseal_v2 import (  # noqa: E402
    MixedAgent,
    fuse_scores,
    score_all_candidates,
    swarm_step_v2,
)


def _agent(aid: str, pos, phase=0.0) -> Agent:
    return Agent(id=aid, position=list(pos), phase=phase)


class TestGeoSealConfig:
    def test_defaults_match_historical_constants(self):
        cfg = GeoSealConfig()
        assert cfg.suspicion_decay == 0.5
        assert cfg.suspicion_threshold == 3
        assert cfg.quarantine_consensus == 3
        assert cfg.trust_denominator == 20.0
        assert cfg.ball_radius == 0.99
        assert cfg == DEFAULT_CONFIG

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"suspicion_decay": -0.1},
            {"suspicion_threshold": 0},
            {"quarantine_consensus": 0},
            {"trust_denominator": 0.0},
            {"ball_radius": 0.0},
            {"ball_radius": 1.0},
        ],
    )
    def test_invalid_values_rejected(self, kwargs):
        with pytest.raises(ValueError):
            GeoSealConfig(**kwargs)

    def test_custom_decay_changes_suspicion_dynamics(self):
        fast_forgive = GeoSealConfig(suspicion_decay=5.0)
        a_default = _agent("a", [0.1, 0.1])
        a_custom = _agent("b", [0.1, 0.1])
        for agent, cfg in ((a_default, None), (a_custom, fast_forgive)):
            update_suspicion(agent, "n", True, cfg)
            update_suspicion(agent, "n", True, cfg)
            update_suspicion(agent, "n", False, cfg)
        # default decay 0.5: 2 - 0.5 = 1.5; custom decay 5.0 floors at 0
        assert a_default.suspicion_count["n"] == pytest.approx(1.5)
        assert a_custom.suspicion_count["n"] == 0

    def test_custom_consensus_quarantines_earlier(self):
        eager = GeoSealConfig(suspicion_threshold=1, quarantine_consensus=1)
        agent = _agent("a", [0.1, 0.1])
        update_suspicion(agent, "n", True, eager)
        assert agent.is_quarantined
        # same single flag under defaults would NOT quarantine
        strict = _agent("b", [0.1, 0.1])
        update_suspicion(strict, "n", True)
        assert not strict.is_quarantined

    def test_swarm_respects_custom_ball_radius(self):
        cfg = GeoSealConfig(ball_radius=0.5)
        agents = [
            _agent("a", [0.49, 0.0]),
            Agent(id="rogue", position=[0.48, 0.01], phase=None),
        ]
        run_swarm(agents, num_steps=5, config=cfg)
        for a in agents:
            norm = sum(x * x for x in a.position) ** 0.5
            assert norm <= 0.5 + 1e-9

    def test_compute_metrics_uses_config_threshold(self):
        agent = _agent("rogue", [0.1, 0.1])
        agent.suspicion_count = {"n1": 1.0, "n2": 1.0}
        loose = GeoSealConfig(suspicion_threshold=1)
        m_default = compute_metrics([agent], "rogue")
        m_loose = compute_metrics([agent], "rogue", loose)
        assert m_default.suspicion_consensus == 0.0  # nothing reaches 3
        assert m_loose.suspicion_consensus == 1.0  # everything reaches 1


class TestDimensionValidation:
    def test_hyperbolic_distance_rejects_mismatch(self):
        with pytest.raises(ValueError, match="dimension mismatch"):
            hyperbolic_distance([0.1, 0.2], [0.1, 0.2, 0.3])

    def test_swarm_step_rejects_mixed_dimensions(self):
        agents = [_agent("a", [0.1, 0.1]), _agent("b", [0.1, 0.1, 0.1])]
        with pytest.raises(ValueError, match="dimension"):
            swarm_step(agents)

    def test_swarm_step_accepts_uniform_dimensions(self):
        agents = [_agent("a", [0.1, 0.1]), _agent("b", [-0.1, 0.2])]
        swarm_step(agents)  # must not raise

    def test_empty_swarm_is_noop(self):
        assert swarm_step([]) == []


class TestV2Guards:
    def _mixed(self, aid: str, sigma=0.0) -> MixedAgent:
        return MixedAgent(id=aid, position=[0.1, 0.1], phase=0.0, sigma=sigma)

    def test_empty_anchors_with_candidates_raises(self):
        with pytest.raises(ValueError, match="anchors list is empty"):
            score_all_candidates([], [self._mixed("c1")])

    def test_empty_candidates_returns_empty_regardless(self):
        assert score_all_candidates([], []) == []
        assert score_all_candidates([self._mixed("a1")], []) == []

    def test_negative_sigma_decay_rejected(self):
        with pytest.raises(ValueError, match="sigma_decay"):
            swarm_step_v2([self._mixed("a")], sigma_decay=-0.01)

    def test_fuse_scores_custom_thresholds(self):
        anchor = self._mixed("anchor")
        candidate = self._mixed("cand")  # identical -> trust 1.0
        default = fuse_scores(anchor, candidate)
        assert default.action == "ALLOW"
        # raise the bar above attainable trust -> same pair now quarantines
        strict = fuse_scores(anchor, candidate, allow_threshold=1.5, quarantine_threshold=0.3)
        assert strict.action == "QUARANTINE"

    def test_fuse_scores_inverted_thresholds_rejected(self):
        with pytest.raises(ValueError, match="allow_threshold"):
            fuse_scores(self._mixed("a"), self._mixed("b"), allow_threshold=0.2, quarantine_threshold=0.5)
