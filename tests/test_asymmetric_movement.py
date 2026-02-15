"""
Tests for the Asymmetric Movement Model (Human vs AI navigation).

@module tests/test_asymmetric_movement
@layer Layer 5, Layer 8, Layer 13
@version 3.2.4
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "fleet"))
from asymmetric_movement import (
    AXIS_LABELS,
    AUTH_TIER_DEPTH,
    LATERAL_AXES,
    ORIGIN,
    TONGUE_AXIS,
    VERTICAL_AXES,
    AIState,
    FleetUnit,
    HumanState,
    ai_movement_cost,
    blind_spots,
    complementarity_score,
    composite_position,
    human_movement_cost,
    validate_movement,
)


# ═══════════════════════════════════════════════════════════════
# Axis Classification
# ═══════════════════════════════════════════════════════════════


class TestAxisClassification:
    def test_2_lateral_4_vertical(self):
        assert len(LATERAL_AXES) == 2
        assert len(VERTICAL_AXES) == 4

    def test_all_6_covered(self):
        combined = set(LATERAL_AXES) | set(VERTICAL_AXES)
        assert combined == set(AXIS_LABELS)

    def test_tongue_to_axis_mapping(self):
        assert TONGUE_AXIS["KO"] == "X"
        assert TONGUE_AXIS["AV"] == "Y"
        assert TONGUE_AXIS["RU"] == "Z"
        assert TONGUE_AXIS["CA"] == "V"
        assert TONGUE_AXIS["UM"] == "P"
        assert TONGUE_AXIS["DR"] == "S"


# ═══════════════════════════════════════════════════════════════
# AI Movement Cost
# ═══════════════════════════════════════════════════════════════


class TestAIMovementCost:
    def test_origin_cost_is_one(self):
        assert ai_movement_cost(ORIGIN, ORIGIN, 1.0) == pytest.approx(1.0, abs=1e-4)

    def test_cost_decreases_with_distance(self):
        near = ai_movement_cost(ORIGIN, (0.1, 0, 0, 0, 0, 0), 0.8)
        far = ai_movement_cost(ORIGIN, (0.5, 0, 0, 0, 0, 0), 0.8)
        assert near > far

    def test_cost_decreases_with_lower_coherence(self):
        target = (0.3, 0, 0, 0, 0, 0)
        high = ai_movement_cost(ORIGIN, target, 0.9)
        low = ai_movement_cost(ORIGIN, target, 0.2)
        assert high > low

    def test_cost_in_zero_one(self):
        targets = [
            ORIGIN,
            (0.5, 0.5, 0.5, 0.5, 0.5, 0.5),
            (0.9, 0, 0, 0, 0, 0),
            (0, 0, 0, 0, 0, 0.9),
        ]
        for t in targets:
            c = ai_movement_cost(ORIGIN, t, 0.5)
            assert 0 < c <= 1

    def test_lateral_equals_vertical_for_ai(self):
        lat = ai_movement_cost(ORIGIN, (0.3, 0, 0, 0, 0, 0), 0.8)
        vert = ai_movement_cost(ORIGIN, (0, 0, 0.3, 0, 0, 0), 0.8)
        assert abs(lat - vert) < 0.01


# ═══════════════════════════════════════════════════════════════
# Human Movement Cost
# ═══════════════════════════════════════════════════════════════


class TestHumanMovementCost:
    def test_lateral_reachable(self):
        c = human_movement_cost(ORIGIN, (0.3, 0.4, 0, 0, 0, 0))
        assert c["reachable"] is True
        assert c["lateral"] == pytest.approx(0.5, abs=1e-4)
        assert c["vertical"] == 0
        assert c["total"] == pytest.approx(0.5, abs=1e-4)

    def test_vertical_unreachable(self):
        c = human_movement_cost(ORIGIN, (0, 0, 0.1, 0, 0, 0))
        assert c["reachable"] is False
        assert c["vertical"] == float("inf")
        assert c["total"] == float("inf")

    def test_no_movement_zero(self):
        c = human_movement_cost(ORIGIN, ORIGIN)
        assert c["reachable"] is True
        assert c["total"] == 0


# ═══════════════════════════════════════════════════════════════
# Composite Position
# ═══════════════════════════════════════════════════════════════


class TestCompositePosition:
    def test_human_lateral_used(self):
        human = HumanState("h1", lateral=(0.1, 0.2))
        agents = [AIState("a1", position=(0, 0, 0.3, 0.1, 0.05, 0.02))]
        unit = FleetUnit("u1", human, agents)
        pos = composite_position(unit)
        assert pos[0] == pytest.approx(0.1)
        assert pos[1] == pytest.approx(0.2)

    def test_human_alone_vertical_zero(self):
        human = HumanState("h1", lateral=(0.1, 0.2))
        unit = FleetUnit("u1", human, [])
        pos = composite_position(unit)
        assert pos == (0.1, 0.2, 0, 0, 0, 0)

    def test_median_robust_to_outlier(self):
        human = HumanState("h1")
        agents = [
            AIState("a1", position=(0, 0, 0.3, 0, 0, 0)),
            AIState("a2", position=(0, 0, 0.31, 0, 0, 0)),
            AIState("a3", position=(0, 0, 0.9, 0, 0, 0)),
        ]
        unit = FleetUnit("u1", human, agents)
        pos = composite_position(unit)
        assert pos[2] == pytest.approx(0.31)


# ═══════════════════════════════════════════════════════════════
# Complementarity
# ═══════════════════════════════════════════════════════════════


class TestComplementarity:
    def test_zero_without_ai(self):
        unit = FleetUnit("u1", HumanState("h1"), [])
        assert complementarity_score(unit) == 0

    def test_high_with_diverse_probes(self):
        agents = [
            AIState("a1", active_tongue="RU", coherence=0.9),
            AIState("a2", active_tongue="CA", coherence=0.8),
            AIState("a3", active_tongue="UM", coherence=0.85),
            AIState("a4", active_tongue="DR", coherence=0.7),
        ]
        unit = FleetUnit("u1", HumanState("h1", attention=0.95), agents)
        assert complementarity_score(unit) > 0.9

    def test_low_with_inattentive_human(self):
        agents = [AIState("a1", coherence=0.9)]
        unit = FleetUnit("u1", HumanState("h1", attention=0.05), agents)
        assert complementarity_score(unit) < 0.5


# ═══════════════════════════════════════════════════════════════
# Blind Spots
# ═══════════════════════════════════════════════════════════════


class TestBlindSpots:
    def test_human_alone_4_blind_spots(self):
        unit = FleetUnit("u1", HumanState("h1"), [])
        assert blind_spots(unit) == ["Z", "V", "P", "S"]

    def test_full_coverage_no_spots(self):
        agents = [
            AIState("a1", active_tongue="RU", coherence=0.9),
            AIState("a2", active_tongue="CA", coherence=0.8),
            AIState("a3", active_tongue="UM", coherence=0.85),
            AIState("a4", active_tongue="DR", coherence=0.7),
        ]
        unit = FleetUnit("u1", HumanState("h1", attention=0.9), agents)
        assert blind_spots(unit) == []


# ═══════════════════════════════════════════════════════════════
# Auth Tier Depth Limits
# ═══════════════════════════════════════════════════════════════


class TestAuthTierDepth:
    def test_ko_shallowest(self):
        assert AUTH_TIER_DEPTH["KO"] == 0.3

    def test_dr_deepest(self):
        assert AUTH_TIER_DEPTH["DR"] == 0.95

    def test_monotonic(self):
        tiers = ["KO", "AV", "RU", "CA", "UM", "DR"]
        for i in range(1, len(tiers)):
            assert AUTH_TIER_DEPTH[tiers[i]] > AUTH_TIER_DEPTH[tiers[i - 1]]

    def test_all_within_ball(self):
        for v in AUTH_TIER_DEPTH.values():
            assert 0 < v < 1.0


# ═══════════════════════════════════════════════════════════════
# Movement Validation
# ═══════════════════════════════════════════════════════════════


class TestValidateMovement:
    def _make_unit(self):
        human = HumanState("h1", lateral=(0.1, 0.2), auth_tier="CA")
        agents = [
            AIState("a1", position=(0.1, 0.2, 0.3, 0.1, 0.05, 0.02), coherence=0.85),
        ]
        return FleetUnit("u1", human, agents, composite_position=(0.1, 0.2, 0.3, 0.1, 0.05, 0.02))

    def test_human_lateral_allowed(self):
        unit = self._make_unit()
        r = validate_movement(unit, (0.2, 0.3, 0.3, 0.1, 0.05, 0.02), "HUMAN")
        assert r["allowed"] is True

    def test_human_vertical_denied(self):
        unit = self._make_unit()
        r = validate_movement(unit, (0.1, 0.2, 0.5, 0.1, 0.05, 0.02), "HUMAN")
        assert r["allowed"] is False
        assert "cannot move vertical" in r["reason"]

    def test_ai_any_dimension_ok(self):
        unit = self._make_unit()
        r = validate_movement(unit, (0.15, 0.25, 0.35, 0.15, 0.08, 0.05), "AI")
        assert r["allowed"] is True

    def test_depth_limit_enforced(self):
        human = HumanState("h1", lateral=(0.1, 0.2), auth_tier="KO")
        agents = [AIState("a1", position=(0.1, 0.2, 0.1, 0, 0, 0), coherence=0.9)]
        unit = FleetUnit("u1", human, agents, composite_position=(0.1, 0.2, 0.1, 0, 0, 0))
        r = validate_movement(unit, (0.1, 0.2, 0.5, 0.4, 0.3, 0.2), "AI")
        assert r["allowed"] is False
        assert "auth tier" in r["reason"]
