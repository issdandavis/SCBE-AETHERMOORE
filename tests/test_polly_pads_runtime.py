"""Tests for Polly Pads Runtime — Python reference implementation.

Covers:
- SCBE decision thresholds (Layer 13)
- Harmonic cost scaling (Layer 12)
- Proximity / neighbor detection
- Byzantine quorum validation
- Voxel commit with quorum gating
- Squad leadership election
- Dual-zone (HOT/SAFE) promotion with optional quorum
- Tool gating per PadMode x Zone
- Per-pad AI code assistance
- Sacred Tongue mapping
- CubeId determinism
- Namespace key generation
- Tri-directional planning (Layer 11)
- CHSFN cymatic field + hyperbolic distance + quasi-sphere volume
- Euclidean distance utility
"""

import os
import sys

# Ensure src/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402

from src.polly_pads_runtime import (  # noqa: E402
    MODE_TOOLS,
    PAD_MODE_TONGUE,
    PAD_MODES,
    PAD_TOOL_MATRIX,
    PHI,
    PollyPad,
    SacredEggSeal,
    SquadSpace,
    Thresholds,
    UnitState,
    VoxelRecord,
    access_cost,
    cube_id,
    cymatic_field_6d,
    dist,
    harmonic_cost,
    hyperbolic_distance_6d,
    pad_namespace_key,
    plan_trace,
    plan_tri_directional,
    quasi_sphere_volume,
    scbe_decide,
    triadic_temporal_distance,
)

# ---------------------------------------------------------------------------
# SCBE Decision Tests (Layer 13)
# ---------------------------------------------------------------------------


class TestSCBEDecision:
    """Verify three-tier SCBE risk decision logic."""

    def test_allow_safe_state(self) -> None:
        assert scbe_decide(0.2, 0.9, 10.0) == "ALLOW"

    def test_allow_with_explicit_thresholds(self) -> None:
        thr = Thresholds()
        assert scbe_decide(0.2, 0.9, 10.0, thr) == "ALLOW"

    def test_deny_high_drift(self) -> None:
        assert scbe_decide(5.0, 0.9, 10.0) == "DENY"

    def test_deny_low_coherence(self) -> None:
        assert scbe_decide(0.2, 0.1, 10.0) == "DENY"

    def test_deny_high_cost(self) -> None:
        assert scbe_decide(0.2, 0.9, 2e6) == "DENY"

    def test_quarantine_medium_coherence(self) -> None:
        assert scbe_decide(0.5, 0.4, 500.0) == "QUARANTINE"

    def test_quarantine_medium_drift(self) -> None:
        assert scbe_decide(1.5, 0.7, 100.0) == "QUARANTINE"

    def test_quarantine_borderline_coherence(self) -> None:
        thr = Thresholds()
        assert scbe_decide(0.5, 0.35, 500.0, thr) == "QUARANTINE"

    def test_quarantine_moderate_cost(self) -> None:
        thr = Thresholds()
        assert scbe_decide(0.5, 0.8, 5e4, thr) == "QUARANTINE"

    def test_custom_thresholds_allow(self) -> None:
        strict = Thresholds(
            allow_max_cost=100,
            quarantine_max_cost=1000,
            allow_min_coherence=0.9,
            quarantine_min_coherence=0.5,
            allow_max_drift=0.5,
            quarantine_max_drift=1.0,
        )
        assert scbe_decide(0.1, 0.95, 50.0, strict) == "ALLOW"

    def test_custom_thresholds_quarantine(self) -> None:
        strict = Thresholds(
            allow_max_cost=100,
            quarantine_max_cost=1000,
            allow_min_coherence=0.9,
            quarantine_min_coherence=0.5,
            allow_max_drift=0.5,
            quarantine_max_drift=1.0,
        )
        assert scbe_decide(0.3, 0.7, 50.0, strict) == "QUARANTINE"

    def test_custom_thresholds_deny(self) -> None:
        strict = Thresholds(
            allow_max_cost=100,
            quarantine_max_cost=1000,
            allow_min_coherence=0.9,
            quarantine_min_coherence=0.5,
            allow_max_drift=0.5,
            quarantine_max_drift=1.0,
        )
        assert scbe_decide(0.3, 0.3, 50.0, strict) == "DENY"


# ---------------------------------------------------------------------------
# Harmonic Cost Tests (Layer 12)
# ---------------------------------------------------------------------------


class TestHarmonicCost:
    """Verify Layer-12 event horizon cost function."""

    def test_zero_distance_is_base(self) -> None:
        assert harmonic_cost(0.0) == pytest.approx(1.5, abs=0.01)

    def test_cost_grows_with_distance(self) -> None:
        c1 = harmonic_cost(1.0)
        c2 = harmonic_cost(2.0)
        assert c2 > c1 > 1.5

    def test_cost_is_exponential(self) -> None:
        c1 = harmonic_cost(1.0)
        c10 = harmonic_cost(10.0)
        assert c10 > c1 * 1000


# ---------------------------------------------------------------------------
# Squad Space Tests
# ---------------------------------------------------------------------------


class TestSquadSpace:
    """Verify squad proximity, quorum, leadership, and coherence."""

    def test_neighbors_within_radius(self) -> None:
        s = SquadSpace("squad-1")
        s.units["a"] = UnitState("a", 0, 0, 0)
        s.units["b"] = UnitState("b", 1, 0, 0)
        s.units["c"] = UnitState("c", 10, 0, 0)
        nb = s.neighbors(radius=2.0)
        assert "b" in nb["a"]
        assert "a" in nb["b"]
        assert nb["c"] == []

    def test_neighbors_empty_squad(self) -> None:
        s = SquadSpace("empty")
        nb = s.neighbors(radius=5.0)
        assert nb == {}

    def test_neighbors_all_close(self) -> None:
        s = SquadSpace("squad-close")
        s.units["a"] = UnitState("a", 0, 0, 0)
        s.units["b"] = UnitState("b", 0.5, 0, 0)
        s.units["c"] = UnitState("c", 0.3, 0.3, 0)
        nb = s.neighbors(radius=1.0)
        assert len(nb["a"]) == 2
        assert len(nb["b"]) == 2
        assert len(nb["c"]) == 2

    def test_quorum_ok_passes(self) -> None:
        s = SquadSpace("q")
        assert s.quorum_ok(4) is True
        assert s.quorum_ok(5) is True
        assert s.quorum_ok(6) is True

    def test_quorum_ok_fails(self) -> None:
        s = SquadSpace("q")
        assert s.quorum_ok(3) is False

    def test_commit_voxel_requires_quorum(self) -> None:
        s = SquadSpace("squad-1")
        seal = SacredEggSeal(
            egg_id="egg-1",
            d_star=0.1,
            coherence=0.9,
            nonce="nonce1",
            aad="aad1",
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

    def test_find_leader(self) -> None:
        s = SquadSpace("lead")
        s.units["a"] = UnitState("a", 0, 0, 0, coherence=0.5, h_eff=100)
        s.units["b"] = UnitState("b", 0, 0, 0, coherence=0.9, h_eff=10)
        leader = s.find_leader()
        assert leader == "b"

    def test_average_coherence(self) -> None:
        s = SquadSpace("coh")
        s.units["a"] = UnitState("a", 0, 0, 0, coherence=0.6)
        s.units["b"] = UnitState("b", 0, 0, 0, coherence=0.8)
        assert s.average_coherence() == pytest.approx(0.7)

    def test_average_coherence_empty(self) -> None:
        s = SquadSpace("empty")
        assert s.average_coherence() == 0.0

    def test_risk_field(self) -> None:
        s = SquadSpace("risk")
        s.units["safe"] = UnitState(
            "safe", 0, 0, 0, coherence=0.9, d_star=0.1, h_eff=10
        )
        s.units["danger"] = UnitState(
            "danger", 0, 0, 0, coherence=0.1, d_star=5.0, h_eff=1e7
        )
        rf = s.risk_field()
        assert rf["safe"] == "ALLOW"
        assert rf["danger"] == "DENY"


# ---------------------------------------------------------------------------
# Polly Pad Dual-Zone Promotion Tests
# ---------------------------------------------------------------------------


class TestPollyPadZones:
    """Verify HOT/SAFE zone promotion with SCBE governance."""

    def test_hot_to_safe_requires_allow(self) -> None:
        pad = PollyPad(unit_id="u1", mode="ENGINEERING", zone="HOT")
        state = UnitState("u1", 0, 0, 0, coherence=0.9, d_star=0.2, h_eff=100.0)
        assert pad.can_promote_to_safe(state) is True

    def test_hot_to_safe_fails_on_deny(self) -> None:
        pad = PollyPad(unit_id="u1", mode="ENGINEERING", zone="HOT")
        state = UnitState("u1", 0, 0, 0, coherence=0.1, d_star=5.0, h_eff=1e7)
        assert pad.can_promote_to_safe(state) is False

    def test_hot_to_safe_denied_low_coherence(self) -> None:
        pad = PollyPad(unit_id="u1", mode="ENGINEERING", zone="HOT")
        state = UnitState("u1", 0, 0, 0, coherence=0.1, d_star=0.2, h_eff=100.0)
        assert pad.can_promote_to_safe(state) is False

    def test_hot_to_safe_denied_high_drift(self) -> None:
        pad = PollyPad(unit_id="u1", mode="ENGINEERING", zone="HOT")
        state = UnitState("u1", 0, 0, 0, coherence=0.9, d_star=5.0, h_eff=100.0)
        assert pad.can_promote_to_safe(state) is False

    def test_hot_to_safe_with_quorum(self) -> None:
        pad = PollyPad(unit_id="u1", mode="ENGINEERING", zone="HOT")
        state = UnitState("u1", 0, 0, 0, coherence=0.9, d_star=0.2, h_eff=100.0)
        assert pad.can_promote_to_safe(state, quorum_votes=3) is False
        assert pad.can_promote_to_safe(state, quorum_votes=4) is True

    def test_promote_changes_zone(self) -> None:
        pad = PollyPad(unit_id="u1", mode="ENGINEERING", zone="HOT")
        state = UnitState("u1", 0, 0, 0, coherence=0.9, d_star=0.2, h_eff=100.0)
        assert pad.promote(state) is True
        assert pad.zone == "SAFE"

    def test_demote_returns_to_hot(self) -> None:
        pad = PollyPad(unit_id="u1", mode="ENGINEERING", zone="SAFE")
        pad.demote()
        assert pad.zone == "HOT"


# ---------------------------------------------------------------------------
# Tool Gating Tests
# ---------------------------------------------------------------------------


class TestToolGating:
    """Verify mode x zone tool access control."""

    def test_engineering_safe_has_deploy(self) -> None:
        pad = PollyPad("u1", "ENGINEERING", "SAFE")
        assert "deploy" in pad.tools

    def test_engineering_hot_no_deploy(self) -> None:
        pad = PollyPad("u1", "ENGINEERING", "HOT")
        assert "deploy" not in pad.tools
        assert "plan_only" in pad.tools

    def test_navigation_has_proximity(self) -> None:
        pad = PollyPad("u1", "NAVIGATION", "SAFE")
        assert "proximity" in pad.tools

    def test_comms_has_encrypt(self) -> None:
        pad = PollyPad("u1", "COMMS", "SAFE")
        assert "encrypt" in pad.tools

    def test_route_task_simple_format(self) -> None:
        pad = PollyPad("u1", "NAVIGATION", "HOT")
        route = pad.route_task("anything")
        assert "tools:" in route

    def test_all_modes_have_both_zones(self) -> None:
        for mode in PAD_MODES:
            assert "SAFE" in PAD_TOOL_MATRIX[mode]
            assert "HOT" in PAD_TOOL_MATRIX[mode]

    def test_all_modes_have_tools(self) -> None:
        for mode in PAD_MODES:
            pad = PollyPad("u1", mode)
            assert len(pad.tools) > 0
            assert len(pad.all_mode_tools) > 0

    def test_hot_zone_returns_plan_only(self) -> None:
        pad = PollyPad("u1", "ENGINEERING", "HOT")
        state = UnitState("u1", 0, 0, 0)
        squad = SquadSpace("test")
        result = pad.route_task("code_exec_safe", state, squad)
        assert "HOT" in result
        assert "Plan" in result or "draft" in result

    def test_safe_zone_allows_tools(self) -> None:
        pad = PollyPad("u1", "ENGINEERING", "SAFE")
        state = UnitState("u1", 0, 0, 0)
        squad = SquadSpace("test")
        result = pad.route_task("build_deploy", state, squad)
        assert "SAFE" in result or "deploy" in result.lower()

    def test_wrong_tool_denied(self) -> None:
        pad = PollyPad("u1", "NAVIGATION", "SAFE")
        state = UnitState("u1", 0, 0, 0)
        squad = SquadSpace("test")
        result = pad.route_task("code_exec_safe", state, squad)
        assert "DENY" in result

    def test_navigation_proximity(self) -> None:
        pad = PollyPad("u1", "NAVIGATION", "SAFE")
        state = UnitState("u1", 0, 0, 0)
        squad = SquadSpace("test")
        squad.units["u1"] = state
        squad.units["u2"] = UnitState("u2", 5, 0, 0)
        result = pad.route_task("proximity_track", state, squad)
        assert "Neighbors" in result


# ---------------------------------------------------------------------------
# Per-Pad AI Assist Tests
# ---------------------------------------------------------------------------


class TestPadAssist:
    """Verify per-pad AI code assistance routing."""

    def test_engineering_code_assist_hot(self) -> None:
        pad = PollyPad("drone1", "ENGINEERING", "HOT")
        state = UnitState("drone1", 0, 0, 0)
        squad = SquadSpace("test")
        result = pad.assist("Draft code for feature", state, squad)
        assert "HOT" in result

    def test_engineering_code_assist_safe(self) -> None:
        pad = PollyPad("drone1", "ENGINEERING", "SAFE")
        state = UnitState("drone1", 0, 0, 0)
        squad = SquadSpace("test")
        result = pad.assist("Run code tests", state, squad)
        assert "SAFE" in result or "Exec" in result

    def test_navigation_proximity_assist(self) -> None:
        pad = PollyPad("drone1", "NAVIGATION", "SAFE")
        state = UnitState("drone1", 0, 0, 0)
        squad = SquadSpace("test")
        squad.units["drone1"] = state
        result = pad.assist("Check proximity", state, squad)
        assert "Neighbors" in result

    def test_fallback_includes_mode(self) -> None:
        pad = PollyPad("drone1", "SCIENCE", "SAFE")
        state = UnitState("drone1", 0, 0, 0)
        squad = SquadSpace("test")
        result = pad.assist("Unrelated query", state, squad)
        assert "SCIENCE" in result

    def test_systems_telemetry_assist(self) -> None:
        pad = PollyPad("drone1", "SYSTEMS", "SAFE")
        state = UnitState("drone1", 0, 0, 0)
        squad = SquadSpace("test")
        result = pad.assist("Read telemetry data", state, squad)
        assert "ALLOW" in result or "Task routed" in result


# ---------------------------------------------------------------------------
# Sacred Tongue Mapping Tests
# ---------------------------------------------------------------------------


class TestPadTongueMapping:
    """Verify mode-to-tongue mapping integrity."""

    def test_all_modes_mapped(self) -> None:
        for mode in PAD_MODES:
            assert mode in PAD_MODE_TONGUE

    def test_engineering_is_ca(self) -> None:
        assert PAD_MODE_TONGUE["ENGINEERING"] == "CA"

    def test_pad_tongue_property(self) -> None:
        pad = PollyPad("u1", "NAVIGATION")
        assert pad.tongue == "AV"


# ---------------------------------------------------------------------------
# CubeId & Namespace Tests
# ---------------------------------------------------------------------------


class TestCubeId:
    """Verify deterministic CubeId generation."""

    def test_deterministic(self) -> None:
        id1 = cube_id("s1", "u1", "ENGINEERING", 0, "KO", [1, 2, 3, 4, 5, 6])
        id2 = cube_id("s1", "u1", "ENGINEERING", 0, "KO", [1, 2, 3, 4, 5, 6])
        assert id1 == id2

    def test_different_inputs_different_id(self) -> None:
        id1 = cube_id("s1", "u1", "ENGINEERING", 0, "KO", [1, 2, 3, 4, 5, 6])
        id2 = cube_id("s1", "u1", "ENGINEERING", 1, "KO", [1, 2, 3, 4, 5, 6])
        assert id1 != id2

    def test_is_sha256_hex(self) -> None:
        cid = cube_id("s1", "u1", "NAVIGATION", 0, "AV", [0, 0, 0, 0, 0, 0])
        assert len(cid) == 64
        assert all(c in "0123456789abcdef" for c in cid)

    def test_different_lang_different_id(self) -> None:
        cid1 = cube_id("unit", "u1", "ENGINEERING", 1, "KO", [0, 0, 0, 0, 0, 0])
        cid2 = cube_id("unit", "u1", "ENGINEERING", 1, "AV", [0, 0, 0, 0, 0, 0])
        assert cid1 != cid2

    def test_squad_id_included(self) -> None:
        cid1 = cube_id(
            "squad",
            "u1",
            "NAVIGATION",
            42,
            "RU",
            [1, 2, 3, 4, 5, 6],
            squad_id="s1",
        )
        cid2 = cube_id(
            "squad",
            "u1",
            "NAVIGATION",
            42,
            "RU",
            [1, 2, 3, 4, 5, 6],
            squad_id="s2",
        )
        assert cid1 != cid2


class TestNamespaceKey:
    """Verify pad namespace key generation."""

    def test_format(self) -> None:
        key = pad_namespace_key("u1", "ENGINEERING", "CA", 0)
        assert key == "u1:ENGINEERING:CA:0"

    def test_uniqueness(self) -> None:
        k1 = pad_namespace_key("u1", "ENGINEERING", "CA", 0)
        k2 = pad_namespace_key("u1", "NAVIGATION", "AV", 0)
        assert k1 != k2


# ---------------------------------------------------------------------------
# Tri-Directional Planning Tests (Layer 11)
# ---------------------------------------------------------------------------


class TestTriadicDistance:
    """Verify triadic temporal distance computation."""

    def test_zero_distances(self) -> None:
        d = triadic_temporal_distance(0.0, 0.0, 0.0)
        assert d >= 0

    def test_positive_distances(self) -> None:
        d = triadic_temporal_distance(1.0, 2.0, 1.5)
        assert d > 0

    def test_symmetry_in_equal_weights(self) -> None:
        d1 = triadic_temporal_distance(1.0, 2.0, 3.0, 1 / 3, 1 / 3, 1 / 3)
        d2 = triadic_temporal_distance(3.0, 1.0, 2.0, 1 / 3, 1 / 3, 1 / 3)
        assert d1 == pytest.approx(d2, rel=1e-6)


class TestPlanTrace:
    """Verify single directional trace planning."""

    def test_valid_trace_with_safe_state(self) -> None:
        state = (0.1, 0.1, 0.1, 0.1, 0.1, 0.1)
        trace = plan_trace("STRUCTURE", state, d_star=0.1)
        assert trace.result == "VALID"
        assert len(trace.path) > 0

    def test_blocked_with_extreme_cost(self) -> None:
        state = (100.0, 100.0, 100.0, 100.0, 100.0, 100.0)
        trace = plan_trace("STRUCTURE", state, d_star=10.0, max_cost=0.001)
        assert trace.result == "BLOCKED"

    def test_all_directions_work(self) -> None:
        state = (0.1, 0.1, 0.1, 0.1, 0.1, 0.1)
        for direction in ("STRUCTURE", "CONFLICT", "TIME"):
            trace = plan_trace(direction, state, d_star=0.1)
            assert trace.direction == direction


class TestTriDirectional:
    """Verify tri-directional planning integration."""

    def test_allow_with_safe_state(self) -> None:
        state = (0.1, 0.1, 0.1, 0.1, 0.1, 0.1)
        result = plan_tri_directional(state, d_star=0.1)
        assert result.valid_count == 3
        assert result.decision == "ALLOW"

    def test_deny_with_extreme_state(self) -> None:
        state = (1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 1000.0)
        result = plan_tri_directional(state, d_star=100.0)
        assert result.decision in ("QUARANTINE", "DENY")


# ---------------------------------------------------------------------------
# CHSFN Primitive Tests
# ---------------------------------------------------------------------------


class TestCymaticField:
    """Verify 6D Chladni-style cymatic field computation."""

    def test_returns_float(self) -> None:
        val = cymatic_field_6d((0.5, 0.5, 0.5, 0.5, 0.5, 0.5))
        assert isinstance(val, float)

    def test_origin_value(self) -> None:
        val = cymatic_field_6d((0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        assert val == pytest.approx(0.0, abs=1e-10)

    def test_nonzero_at_midpoint(self) -> None:
        val = cymatic_field_6d((0.25, 0.25, 0.25, 0.25, 0.25, 0.25))
        assert val != 0.0


class TestHyperbolicDistance:
    """Verify 6D Poincare ball hyperbolic distance."""

    def test_self_distance_zero(self) -> None:
        p = (0.1, 0.2, 0.1, 0.1, 0.1, 0.1)
        assert hyperbolic_distance_6d(p, p) == pytest.approx(0.0, abs=1e-10)

    def test_symmetry(self) -> None:
        u = (0.1, 0.2, 0.0, 0.1, 0.0, 0.1)
        v = (0.3, 0.1, 0.2, 0.0, 0.1, 0.0)
        assert hyperbolic_distance_6d(u, v) == pytest.approx(
            hyperbolic_distance_6d(v, u), rel=1e-10
        )

    def test_grows_with_position(self) -> None:
        origin = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        near = (0.1, 0.0, 0.0, 0.0, 0.0, 0.0)
        far = (0.5, 0.0, 0.0, 0.0, 0.0, 0.0)
        d_near = hyperbolic_distance_6d(origin, near)
        d_far = hyperbolic_distance_6d(origin, far)
        assert d_far > d_near


class TestQuasiSphere:
    """Verify hyperbolic volume and access cost."""

    def test_volume_grows_exponentially(self) -> None:
        v1 = quasi_sphere_volume(1.0)
        v2 = quasi_sphere_volume(2.0)
        assert v2 > v1 * 100

    def test_access_cost_zero_distance(self) -> None:
        c = access_cost(0.0)
        assert c == pytest.approx(1.5, abs=0.01)

    def test_access_cost_grows(self) -> None:
        c1 = access_cost(1.0)
        c10 = access_cost(10.0)
        assert c10 > c1 * 100


# ---------------------------------------------------------------------------
# Euclidean Distance Utility Tests
# ---------------------------------------------------------------------------


class TestDist:
    """Verify 3D Euclidean distance between units."""

    def test_zero_distance(self) -> None:
        a = UnitState("a", 0, 0, 0)
        b = UnitState("b", 0, 0, 0)
        assert dist(a, b) == 0.0

    def test_self_distance(self) -> None:
        a = UnitState("a", 0, 0, 0)
        assert dist(a, a) == 0.0

    def test_unit_distance(self) -> None:
        a = UnitState("a", 0, 0, 0)
        b = UnitState("b", 1, 0, 0)
        assert dist(a, b) == pytest.approx(1.0)

    def test_3d_distance(self) -> None:
        a = UnitState("a", 1, 2, 3)
        b = UnitState("b", 4, 6, 3)
        assert dist(a, b) == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Constants Validation Tests
# ---------------------------------------------------------------------------


class TestConstants:
    """Verify mathematical constants and data structure integrity."""

    def test_phi_value(self) -> None:
        assert PHI == pytest.approx(1.618033988749895, rel=1e-12)

    def test_pad_modes_count(self) -> None:
        assert len(PAD_MODES) == 6

    def test_mode_tools_keys_match_modes(self) -> None:
        for mode in PAD_MODES:
            assert mode in MODE_TOOLS

    def test_tool_matrix_keys_match_modes(self) -> None:
        for mode in PAD_MODES:
            assert mode in PAD_TOOL_MATRIX
            assert "HOT" in PAD_TOOL_MATRIX[mode]
            assert "SAFE" in PAD_TOOL_MATRIX[mode]
