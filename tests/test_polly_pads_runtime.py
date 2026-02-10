"""Tests for Polly Pads runtime - per-pad AI code assistance."""

import pytest
import sys
import os

# Ensure src/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.polly_pads_runtime import (
    SquadSpace,
    UnitState,
    PollyPad,
    scbe_decide,
    cube_id,
    dist,
    Thresholds,
    PAD_MODES,
    MODE_TOOLS,
    VoxelRecord,
    QuorumProof,
    SacredEggSeal,
)


# ---------------------------------------------------------------------------
# SCBE decision tests
# ---------------------------------------------------------------------------


class TestSCBEDecision:
    def test_allow_within_thresholds(self):
        thr = Thresholds()
        assert scbe_decide(0.2, 0.9, 10.0, thr) == "ALLOW"

    def test_deny_high_drift(self):
        thr = Thresholds()
        assert scbe_decide(5.0, 0.9, 10.0, thr) == "DENY"

    def test_deny_low_coherence(self):
        thr = Thresholds()
        assert scbe_decide(0.2, 0.1, 10.0, thr) == "DENY"

    def test_deny_high_cost(self):
        thr = Thresholds()
        assert scbe_decide(0.2, 0.9, 2e6, thr) == "DENY"

    def test_quarantine_borderline(self):
        thr = Thresholds()
        # Coherence above quarantine min but below allow min
        assert scbe_decide(0.5, 0.35, 500.0, thr) == "QUARANTINE"

    def test_quarantine_moderate_drift(self):
        thr = Thresholds()
        # Drift above allow max but below quarantine max
        assert scbe_decide(1.8, 0.8, 100.0, thr) == "QUARANTINE"

    def test_quarantine_moderate_cost(self):
        thr = Thresholds()
        # Cost above allow max but below quarantine max
        assert scbe_decide(0.5, 0.8, 5e4, thr) == "QUARANTINE"


# ---------------------------------------------------------------------------
# Proximity / neighbour tests
# ---------------------------------------------------------------------------


class TestSquadSpace:
    def test_neighbors_radius(self):
        s = SquadSpace("squad-1")
        s.units["a"] = UnitState("a", 0, 0, 0)
        s.units["b"] = UnitState("b", 1, 0, 0)
        s.units["c"] = UnitState("c", 10, 0, 0)
        nb = s.neighbors(radius=2.0)
        assert "b" in nb["a"]
        assert "a" in nb["b"]
        assert nb["c"] == []

    def test_neighbors_empty(self):
        s = SquadSpace("squad-empty")
        assert s.neighbors(radius=5.0) == {}

    def test_neighbors_all_close(self):
        s = SquadSpace("squad-close")
        s.units["a"] = UnitState("a", 0, 0, 0)
        s.units["b"] = UnitState("b", 0.5, 0, 0)
        s.units["c"] = UnitState("c", 0.3, 0.3, 0)
        nb = s.neighbors(radius=1.0)
        assert len(nb["a"]) == 2
        assert len(nb["b"]) == 2
        assert len(nb["c"]) == 2

    def test_quorum_ok(self):
        s = SquadSpace("squad-1")
        assert s.quorum_ok(4) is True
        assert s.quorum_ok(5) is True
        assert s.quorum_ok(6) is True
        assert s.quorum_ok(3) is False

    def test_commit_voxel_requires_quorum(self):
        s = SquadSpace("squad-1")
        seal = SacredEggSeal(
            egg_id="egg-1", d_star=0.1, coherence=0.9, nonce="nonce1", aad="aad1"
        )
        record = VoxelRecord(
            scope="squad",
            lang="KO",
            voxel=(0, 0, 0, 0, 0, 0),
            epoch=1,
            pad_mode="ENGINEERING",
            coherence=0.9,
            d_star=0.1,
            h_eff=10.0,
            decision="ALLOW",
            cube_id="abc123",
            payload_digest="def456",
            seal=seal,
            payload_ciphertext="encrypted",
            squad_id="squad-1",
        )
        assert s.commit_voxel(record, quorum_votes=3) is False
        assert len(s.voxels) == 0
        assert s.commit_voxel(record, quorum_votes=4) is True
        assert "abc123" in s.voxels


# ---------------------------------------------------------------------------
# Dual zone promotion tests
# ---------------------------------------------------------------------------


class TestPollyPadZones:
    def test_hot_to_safe_requires_allow(self):
        pad = PollyPad(unit_id="u1", mode="ENGINEERING", zone="HOT")
        state = UnitState("u1", 0, 0, 0, coherence=0.9, d_star=0.2, h_eff=100.0)
        assert pad.can_promote_to_safe(state) is True

    def test_hot_to_safe_denied_low_coherence(self):
        pad = PollyPad(unit_id="u1", mode="ENGINEERING", zone="HOT")
        state = UnitState("u1", 0, 0, 0, coherence=0.1, d_star=0.2, h_eff=100.0)
        assert pad.can_promote_to_safe(state) is False

    def test_hot_to_safe_with_quorum(self):
        pad = PollyPad(unit_id="u1", mode="ENGINEERING", zone="HOT")
        state = UnitState("u1", 0, 0, 0, coherence=0.9, d_star=0.2, h_eff=100.0)
        assert pad.can_promote_to_safe(state, quorum_votes=3) is False
        assert pad.can_promote_to_safe(state, quorum_votes=4) is True

    def test_hot_to_safe_denied_high_drift(self):
        pad = PollyPad(unit_id="u1", mode="ENGINEERING", zone="HOT")
        state = UnitState("u1", 0, 0, 0, coherence=0.9, d_star=5.0, h_eff=100.0)
        assert pad.can_promote_to_safe(state) is False


# ---------------------------------------------------------------------------
# Tool gating tests
# ---------------------------------------------------------------------------


class TestToolGating:
    def test_hot_zone_returns_plan_only(self):
        pad = PollyPad("u1", "ENGINEERING", "HOT")
        state = UnitState("u1", 0, 0, 0)
        squad = SquadSpace("test")
        result = pad.route_task("code_exec_safe", state, squad)
        assert "HOT" in result
        assert "Plan" in result or "draft" in result

    def test_safe_zone_allows_tools(self):
        pad = PollyPad("u1", "ENGINEERING", "SAFE")
        state = UnitState("u1", 0, 0, 0)
        squad = SquadSpace("test")
        result = pad.route_task("build_deploy", state, squad)
        assert "SAFE" in result or "deploy" in result.lower()

    def test_wrong_tool_denied(self):
        pad = PollyPad("u1", "NAVIGATION", "SAFE")
        state = UnitState("u1", 0, 0, 0)
        squad = SquadSpace("test")
        result = pad.route_task("code_exec_safe", state, squad)
        assert "DENY" in result

    def test_navigation_proximity(self):
        pad = PollyPad("u1", "NAVIGATION", "SAFE")
        state = UnitState("u1", 0, 0, 0)
        squad = SquadSpace("test")
        squad.units["u1"] = state
        squad.units["u2"] = UnitState("u2", 5, 0, 0)
        result = pad.route_task("proximity_track", state, squad)
        assert "Neighbors" in result

    def test_mode_specific_toolsets(self):
        for mode in PAD_MODES:
            pad = PollyPad("u1", mode)
            assert len(pad.tools) > 0
            assert pad.tools == MODE_TOOLS[mode]


# ---------------------------------------------------------------------------
# Per-pad AI assist tests
# ---------------------------------------------------------------------------


class TestPadAssist:
    def test_engineering_code_assist_hot(self):
        pad = PollyPad("drone1", "ENGINEERING", "HOT")
        state = UnitState("drone1", 0, 0, 0)
        squad = SquadSpace("test")
        result = pad.assist("Draft code for feature", state, squad)
        assert "HOT" in result

    def test_engineering_code_assist_safe(self):
        pad = PollyPad("drone1", "ENGINEERING", "SAFE")
        state = UnitState("drone1", 0, 0, 0)
        squad = SquadSpace("test")
        result = pad.assist("Run code tests", state, squad)
        assert "SAFE" in result or "Exec" in result

    def test_navigation_proximity_assist(self):
        pad = PollyPad("drone1", "NAVIGATION", "SAFE")
        state = UnitState("drone1", 0, 0, 0)
        squad = SquadSpace("test")
        squad.units["drone1"] = state
        result = pad.assist("Check proximity", state, squad)
        assert "Neighbors" in result

    def test_fallback_includes_mode(self):
        pad = PollyPad("drone1", "SCIENCE", "SAFE")
        state = UnitState("drone1", 0, 0, 0)
        squad = SquadSpace("test")
        result = pad.assist("Unrelated query", state, squad)
        assert "SCIENCE" in result

    def test_systems_telemetry_assist(self):
        pad = PollyPad("drone1", "SYSTEMS", "SAFE")
        state = UnitState("drone1", 0, 0, 0)
        squad = SquadSpace("test")
        result = pad.assist("Read telemetry data", state, squad)
        assert "ALLOW" in result or "Task routed" in result


# ---------------------------------------------------------------------------
# CubeId determinism tests
# ---------------------------------------------------------------------------


class TestCubeId:
    def test_deterministic(self):
        cid1 = cube_id("unit", "u1", None, "KO", (0, 0, 0, 0, 0, 0), 1, "ENGINEERING")
        cid2 = cube_id("unit", "u1", None, "KO", (0, 0, 0, 0, 0, 0), 1, "ENGINEERING")
        assert cid1 == cid2

    def test_different_inputs_different_ids(self):
        cid1 = cube_id("unit", "u1", None, "KO", (0, 0, 0, 0, 0, 0), 1, "ENGINEERING")
        cid2 = cube_id("unit", "u1", None, "AV", (0, 0, 0, 0, 0, 0), 1, "ENGINEERING")
        assert cid1 != cid2

    def test_is_sha256_hex(self):
        cid = cube_id("squad", None, "s1", "RU", (1, 2, 3, 4, 5, 6), 42, "NAVIGATION")
        assert len(cid) == 64
        assert all(c in "0123456789abcdef" for c in cid)


# ---------------------------------------------------------------------------
# Distance utility test
# ---------------------------------------------------------------------------


class TestDist:
    def test_zero_distance(self):
        a = UnitState("a", 0, 0, 0)
        b = UnitState("b", 0, 0, 0)
        assert dist(a, b) == 0.0

    def test_unit_distance(self):
        a = UnitState("a", 0, 0, 0)
        b = UnitState("b", 1, 0, 0)
        assert abs(dist(a, b) - 1.0) < 1e-10

    def test_3d_distance(self):
        a = UnitState("a", 1, 2, 3)
        b = UnitState("b", 4, 6, 3)
        assert abs(dist(a, b) - 5.0) < 1e-10
