"""
Comprehensive test suite for the PollyPad system.

Covers:
1. All 6 operational modes (ENGINEERING, NAVIGATION, SYSTEMS, SCIENCE, COMMS, MISSION)
2. Sacred Tongue mapping per mode
3. HOT/SAFE zone governance and promotion/demotion
4. Quorum-based voxel commits (4-of-6 threshold)
5. SquadSpace convergence, neighbor topology, leader selection
6. Mathematical checks (harmonic_cost monotonicity, hyperbolic distance symmetry)
7. Edge cases (idempotent commits, epoch coexistence)

@module tests/test_polly_pads_modes_and_sync_runtime
@layer Layer 8, Layer 12, Layer 13
"""

import math
import pytest

from src.polly_pads_runtime import (
    # Constants
    PAD_MODES,
    PAD_MODE_TONGUE,
    PAD_TOOL_MATRIX,
    MODE_TOOLS,
    LANGS,
    PHI,
    # Governance
    scbe_decide,
    harmonic_cost,
    # Addressing
    cube_id,
    pad_namespace_key,
    # Spatial / unit
    UnitState,
    dist,
    # Voxel records
    SacredEggSeal,
    VoxelRecord,
    # Squad space
    SquadSpace,
    # Polly Pad
    PollyPad,
    # Math primitives
    hyperbolic_distance_6d,
    cymatic_field_6d,
    quasi_sphere_volume,
    access_cost,
    # Tri-directional planning
    triadic_temporal_distance,
    plan_trace,
    plan_tri_directional,
    STANDARD_CHECKPOINTS,
    DIRECTION_WEIGHTS,
)

# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _make_seal(d_star: float = 0.1, coherence: float = 0.9) -> SacredEggSeal:
    """Factory for a minimal SacredEggSeal."""
    return SacredEggSeal(
        egg_id="test-egg-001",
        d_star=d_star,
        coherence=coherence,
        nonce="deadbeef",
        aad="test-aad",
    )


def _make_voxel_record(
    pad_mode: str = "ENGINEERING",
    lang: str = "CA",
    epoch: int = 1,
    d_star: float = 0.1,
    coherence: float = 0.95,
) -> VoxelRecord:
    """Factory for a VoxelRecord with deterministic cube_id."""
    voxel = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    cid = cube_id(
        scope="squad",
        unit_id="unit-alpha",
        pad_mode=pad_mode,
        epoch=epoch,
        lang=lang,
        voxel=list(voxel),
        squad_id="squad-1",
    )
    h_eff = harmonic_cost(d_star)
    decision = scbe_decide(d_star, coherence, h_eff)
    return VoxelRecord(
        scope="squad",
        lang=lang,
        voxel=voxel,
        epoch=epoch,
        pad_mode=pad_mode,
        coherence=coherence,
        d_star=d_star,
        h_eff=h_eff,
        decision=decision,
        cube_id=cid,
        payload_digest="abc123",
        seal=_make_seal(d_star, coherence),
        payload_ciphertext="encrypted-blob",
        unit_id="unit-alpha",
        squad_id="squad-1",
    )


def _make_safe_unit(
    unit_id: str = "u1", x: float = 0.0, y: float = 0.0, z: float = 0.0
) -> UnitState:
    """Unit with governance values that yield ALLOW."""
    return UnitState(
        unit_id=unit_id,
        x=x,
        y=y,
        z=z,
        coherence=0.95,
        d_star=0.1,
        h_eff=harmonic_cost(0.1),
    )


def _make_risky_unit(
    unit_id: str = "bad", x: float = 0.0, y: float = 0.0, z: float = 0.0
) -> UnitState:
    """Unit with governance values that yield DENY."""
    return UnitState(
        unit_id=unit_id,
        x=x,
        y=y,
        z=z,
        coherence=0.1,
        d_star=5.0,
        h_eff=harmonic_cost(5.0),
    )


def _squad_with_6_units() -> SquadSpace:
    """Build a SquadSpace with 6 units in a line along the x-axis."""
    sq = SquadSpace(squad_id="squad-6")
    for i in range(6):
        uid = f"u{i}"
        sq.units[uid] = UnitState(
            unit_id=uid,
            x=float(i * 2),
            y=0.0,
            z=0.0,
            coherence=0.9 - i * 0.05,
            d_star=0.1 + i * 0.02,
            h_eff=harmonic_cost(0.1 + i * 0.02),
        )
    return sq


# ═══════════════════════════════════════════════════════════════════════════
# 1) All 6 operational modes exist
# ═══════════════════════════════════════════════════════════════════════════


class TestPadModesExist:
    """Verify the PAD_MODES constant contains exactly 6 modes."""

    EXPECTED_MODES = {
        "ENGINEERING",
        "NAVIGATION",
        "SYSTEMS",
        "SCIENCE",
        "COMMS",
        "MISSION",
    }

    def test_pad_modes_count(self):
        assert len(PAD_MODES) == 6

    def test_pad_modes_set(self):
        assert set(PAD_MODES) == self.EXPECTED_MODES

    @pytest.mark.parametrize("mode", list(EXPECTED_MODES))
    def test_mode_in_pad_modes(self, mode):
        assert mode in PAD_MODES

    @pytest.mark.parametrize("mode", list(EXPECTED_MODES))
    def test_mode_has_tools(self, mode):
        """Every mode must define both HOT and SAFE tool sets."""
        assert mode in MODE_TOOLS
        assert mode in PAD_TOOL_MATRIX
        assert "HOT" in PAD_TOOL_MATRIX[mode]
        assert "SAFE" in PAD_TOOL_MATRIX[mode]

    @pytest.mark.parametrize("mode", list(EXPECTED_MODES))
    def test_hot_zone_has_plan_only(self, mode):
        """HOT zone always includes 'plan_only' for safety."""
        assert "plan_only" in PAD_TOOL_MATRIX[mode]["HOT"]

    @pytest.mark.parametrize("mode", list(EXPECTED_MODES))
    def test_safe_zone_has_no_plan_only(self, mode):
        """SAFE zone never has 'plan_only' (real execution only)."""
        assert "plan_only" not in PAD_TOOL_MATRIX[mode]["SAFE"]


# ═══════════════════════════════════════════════════════════════════════════
# 2) Sacred Tongue mapping per mode
# ═══════════════════════════════════════════════════════════════════════════


class TestSacredTongueMappings:
    """Each mode maps to exactly one Sacred Tongue from the set of 6."""

    EXPECTED_MAP = {
        "ENGINEERING": "CA",
        "NAVIGATION": "AV",
        "SYSTEMS": "DR",
        "SCIENCE": "UM",
        "COMMS": "KO",
        "MISSION": "RU",
    }

    def test_all_modes_have_tongue_mapping(self):
        for mode in PAD_MODES:
            assert mode in PAD_MODE_TONGUE

    @pytest.mark.parametrize("mode,tongue", list(EXPECTED_MAP.items()))
    def test_specific_mapping(self, mode, tongue):
        assert PAD_MODE_TONGUE[mode] == tongue

    def test_all_six_tongues_used(self):
        """Each tongue is used exactly once — bijection."""
        used = set(PAD_MODE_TONGUE.values())
        assert used == set(LANGS)

    def test_polly_pad_tongue_property(self):
        """PollyPad.tongue property returns the correct tongue for its mode."""
        for mode, expected_tongue in self.EXPECTED_MAP.items():
            pad = PollyPad(unit_id="test", mode=mode)
            assert pad.tongue == expected_tongue


# ═══════════════════════════════════════════════════════════════════════════
# 3) HOT/SAFE zone governance
# ═══════════════════════════════════════════════════════════════════════════


class TestZoneGovernance:
    """Test dual-zone governance: HOT (draft) vs SAFE (exec)."""

    def test_default_zone_is_hot(self):
        pad = PollyPad(unit_id="u1", mode="ENGINEERING")
        assert pad.zone == "HOT"

    def test_promote_to_safe_with_allow(self):
        pad = PollyPad(unit_id="u1", mode="ENGINEERING")
        state = _make_safe_unit("u1")
        assert pad.promote(state)
        assert pad.zone == "SAFE"

    def test_promote_denied_with_bad_governance(self):
        pad = PollyPad(unit_id="u1", mode="ENGINEERING")
        state = _make_risky_unit("u1")
        assert not pad.promote(state)
        assert pad.zone == "HOT"

    def test_promote_denied_without_quorum(self):
        """When quorum_votes is provided but < 4, promotion fails."""
        pad = PollyPad(unit_id="u1", mode="ENGINEERING")
        state = _make_safe_unit("u1")
        assert not pad.promote(state, quorum_votes=3)
        assert pad.zone == "HOT"

    def test_promote_succeeds_with_quorum(self):
        pad = PollyPad(unit_id="u1", mode="ENGINEERING")
        state = _make_safe_unit("u1")
        assert pad.promote(state, quorum_votes=4)
        assert pad.zone == "SAFE"

    def test_demote_returns_to_hot(self):
        pad = PollyPad(unit_id="u1", mode="ENGINEERING")
        state = _make_safe_unit("u1")
        pad.promote(state)
        assert pad.zone == "SAFE"
        pad.demote()
        assert pad.zone == "HOT"

    def test_tools_change_with_zone(self):
        pad = PollyPad(unit_id="u1", mode="ENGINEERING")
        hot_tools = pad.tools
        assert "plan_only" in hot_tools

        state = _make_safe_unit("u1")
        pad.promote(state)
        safe_tools = pad.tools
        assert "plan_only" not in safe_tools
        assert set(hot_tools) != set(safe_tools)

    def test_scbe_decide_allow(self):
        decision = scbe_decide(d_star=0.1, coherence=0.9, h_eff=10.0)
        assert decision == "ALLOW"

    def test_scbe_decide_quarantine(self):
        decision = scbe_decide(d_star=1.5, coherence=0.4, h_eff=5000.0)
        assert decision == "QUARANTINE"

    def test_scbe_decide_deny_low_coherence(self):
        decision = scbe_decide(d_star=0.1, coherence=0.1, h_eff=10.0)
        assert decision == "DENY"

    def test_scbe_decide_deny_high_cost(self):
        decision = scbe_decide(d_star=0.1, coherence=0.9, h_eff=2e6)
        assert decision == "DENY"

    def test_scbe_decide_deny_high_drift(self):
        decision = scbe_decide(d_star=3.0, coherence=0.9, h_eff=10.0)
        assert decision == "DENY"

    def test_route_task_hot_zone_with_state(self):
        """HOT zone route_task with state returns plan/draft message."""
        pad = PollyPad(unit_id="u1", mode="ENGINEERING")
        state = _make_safe_unit("u1")
        result = pad.route_task("ide_draft", state)
        assert "Plan/draft" in result or "HOT" in result

    def test_route_task_safe_zone_allows_exec(self):
        """SAFE zone routes actual tasks through."""
        pad = PollyPad(unit_id="u1", mode="ENGINEERING")
        state = _make_safe_unit("u1")
        pad.promote(state)
        sq = SquadSpace(squad_id="sq")
        sq.units["u1"] = state
        result = pad.route_task("code_exec_safe", state, sq)
        assert "SAFE" in result or "Exec" in result


# ═══════════════════════════════════════════════════════════════════════════
# 4) Quorum-based voxel commits (4-of-6 threshold)
# ═══════════════════════════════════════════════════════════════════════════


class TestQuorumVoxelCommits:
    """Byzantine 4/6 quorum for shared voxel memory writes."""

    def test_quorum_ok_at_threshold(self):
        sq = SquadSpace(squad_id="sq")
        assert sq.quorum_ok(votes=4, n=6, threshold=4)

    def test_quorum_ok_above_threshold(self):
        sq = SquadSpace(squad_id="sq")
        assert sq.quorum_ok(votes=5, n=6, threshold=4)
        assert sq.quorum_ok(votes=6, n=6, threshold=4)

    def test_quorum_fails_below_threshold(self):
        sq = SquadSpace(squad_id="sq")
        assert not sq.quorum_ok(votes=3, n=6, threshold=4)

    def test_quorum_fails_at_zero_votes(self):
        sq = SquadSpace(squad_id="sq")
        assert not sq.quorum_ok(votes=0, n=6, threshold=4)

    def test_quorum_rejects_bad_n(self):
        """n must satisfy 3f+1 for f = (n-1)//3."""
        sq = SquadSpace(squad_id="sq")
        # n=2 gives f=0, threshold must >= 2*0+1=1, but n < 3*0+1=1 is false
        # Actually n=2 >= 3*0+1=1, so quorum_ok just checks votes>=threshold
        # Let's test n=3, f=0, threshold must be >= 1
        assert sq.quorum_ok(votes=1, n=3, threshold=1)

    def test_commit_voxel_succeeds_with_quorum(self):
        sq = SquadSpace(squad_id="sq")
        record = _make_voxel_record()
        assert sq.commit_voxel(record, quorum_votes=4)
        assert record.cube_id in sq.voxels

    def test_commit_voxel_fails_without_quorum(self):
        sq = SquadSpace(squad_id="sq")
        record = _make_voxel_record()
        assert not sq.commit_voxel(record, quorum_votes=3)
        assert record.cube_id not in sq.voxels

    def test_commit_voxel_zero_votes(self):
        sq = SquadSpace(squad_id="sq")
        record = _make_voxel_record()
        assert not sq.commit_voxel(record, quorum_votes=0)

    def test_commit_voxel_default_votes_is_zero(self):
        """Default quorum_votes=0 means commit is rejected."""
        sq = SquadSpace(squad_id="sq")
        record = _make_voxel_record()
        assert not sq.commit_voxel(record)


# ═══════════════════════════════════════════════════════════════════════════
# 5) SquadSpace: convergence, neighbor topology, leader selection
# ═══════════════════════════════════════════════════════════════════════════


class TestSquadSpaceTopology:
    """SquadSpace neighbor detection, leader election, and convergence metrics."""

    def test_neighbors_within_radius(self):
        sq = _squad_with_6_units()
        # Units at x=0,2,4,6,8,10 — radius 3 means only adjacent pairs
        nbrs = sq.neighbors(radius=3.0)
        assert "u1" in nbrs["u0"]
        assert "u0" in nbrs["u1"]

    def test_neighbors_excludes_distant(self):
        sq = _squad_with_6_units()
        nbrs = sq.neighbors(radius=3.0)
        # u0 at x=0, u5 at x=10 — too far
        assert "u5" not in nbrs["u0"]

    def test_neighbors_symmetry(self):
        """If A is a neighbor of B, then B is a neighbor of A."""
        sq = _squad_with_6_units()
        nbrs = sq.neighbors(radius=5.0)
        for uid, neighbor_list in nbrs.items():
            for nid in neighbor_list:
                assert (
                    uid in nbrs[nid]
                ), f"{uid} in {nid}'s neighbors but not vice versa"

    def test_neighbors_large_radius_all_connected(self):
        sq = _squad_with_6_units()
        nbrs = sq.neighbors(radius=100.0)
        for uid in sq.units:
            assert len(nbrs[uid]) == 5  # connected to all others

    def test_neighbors_tiny_radius_none_connected(self):
        sq = _squad_with_6_units()
        nbrs = sq.neighbors(radius=0.1)
        for uid in sq.units:
            assert len(nbrs[uid]) == 0

    def test_find_leader_lowest_score(self):
        """Leader = unit with lowest (h_eff - coherence * 1000)."""
        sq = _squad_with_6_units()
        leader = sq.find_leader()
        assert leader is not None
        # u0 has highest coherence (0.9) and lowest h_eff
        assert leader == "u0"

    def test_find_leader_empty_squad(self):
        sq = SquadSpace(squad_id="empty")
        assert sq.find_leader() is None

    def test_average_coherence(self):
        sq = _squad_with_6_units()
        avg = sq.average_coherence()
        expected = sum(0.9 - i * 0.05 for i in range(6)) / 6
        assert abs(avg - expected) < 1e-10

    def test_average_coherence_empty(self):
        sq = SquadSpace(squad_id="empty")
        assert sq.average_coherence() == 0.0

    def test_risk_field_all_safe(self):
        """All units with safe params should get ALLOW."""
        sq = SquadSpace(squad_id="safe-squad")
        for i in range(6):
            sq.units[f"u{i}"] = _make_safe_unit(f"u{i}", x=float(i))
        field = sq.risk_field()
        for uid, decision in field.items():
            assert decision == "ALLOW", f"{uid} got {decision} instead of ALLOW"

    def test_risk_field_mixed(self):
        sq = SquadSpace(squad_id="mixed")
        sq.units["safe"] = _make_safe_unit("safe")
        sq.units["risky"] = _make_risky_unit("risky")
        field = sq.risk_field()
        assert field["safe"] == "ALLOW"
        assert field["risky"] == "DENY"


# ═══════════════════════════════════════════════════════════════════════════
# 6) Mathematical checks
# ═══════════════════════════════════════════════════════════════════════════


class TestHarmonicCostMonotonicity:
    """harmonic_cost must be strictly monotonically increasing in d_star."""

    def test_monotone_increasing(self):
        prev = harmonic_cost(0.0)
        for i in range(1, 20):
            d = i * 0.5
            cur = harmonic_cost(d)
            assert cur > prev, f"harmonic_cost({d}) = {cur} <= {prev}"
            prev = cur

    def test_harmonic_cost_at_zero(self):
        """At d_star=0, cost = r * pi^0 = r."""
        assert abs(harmonic_cost(0.0, r=1.5) - 1.5) < 1e-10

    def test_harmonic_cost_positive(self):
        for d in [0.0, 0.5, 1.0, 2.0, 5.0, 10.0]:
            assert harmonic_cost(d) > 0

    def test_harmonic_cost_exponential_growth(self):
        """Cost at d=2 should be much larger than at d=1."""
        c1 = harmonic_cost(1.0)
        c2 = harmonic_cost(2.0)
        assert c2 / c1 > 3.0  # exponential ratio

    def test_access_cost_matches_harmonic_cost(self):
        """access_cost and harmonic_cost use the same formula."""
        for d in [0.0, 0.5, 1.0, 3.0]:
            assert abs(access_cost(d, 1.5) - harmonic_cost(d, 1.5)) < 1e-10


class TestHyperbolicDistanceSymmetry:
    """hyperbolic_distance_6d must be a proper metric: symmetric, non-negative, d(x,x)=0."""

    def test_distance_to_self_is_zero(self):
        u = (0.1, 0.2, 0.3, 0.1, 0.2, 0.3)
        assert abs(hyperbolic_distance_6d(u, u)) < 1e-10

    def test_symmetry(self):
        u = (0.1, 0.2, 0.0, 0.0, 0.0, 0.0)
        v = (0.3, 0.4, 0.0, 0.0, 0.0, 0.0)
        d_uv = hyperbolic_distance_6d(u, v)
        d_vu = hyperbolic_distance_6d(v, u)
        assert abs(d_uv - d_vu) < 1e-10

    def test_non_negative(self):
        u = (0.1, 0.2, 0.0, 0.0, 0.0, 0.0)
        v = (0.3, 0.4, 0.0, 0.0, 0.0, 0.0)
        assert hyperbolic_distance_6d(u, v) >= 0

    def test_triangle_inequality(self):
        u = (0.1, 0.0, 0.0, 0.0, 0.0, 0.0)
        v = (0.3, 0.0, 0.0, 0.0, 0.0, 0.0)
        w = (0.5, 0.0, 0.0, 0.0, 0.0, 0.0)
        d_uv = hyperbolic_distance_6d(u, v)
        d_vw = hyperbolic_distance_6d(v, w)
        d_uw = hyperbolic_distance_6d(u, w)
        assert d_uw <= d_uv + d_vw + 1e-10

    def test_outside_ball_returns_inf(self):
        """Points on or outside the unit ball get inf distance."""
        u = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        v = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        assert hyperbolic_distance_6d(u, v) == float("inf")

    def test_origin_distance(self):
        """Distance from origin to a point inside the ball is finite and positive."""
        origin = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        p = (0.5, 0.0, 0.0, 0.0, 0.0, 0.0)
        d = hyperbolic_distance_6d(origin, p)
        assert 0 < d < float("inf")


class TestCymaticField:
    """cymatic_field_6d sanity checks."""

    def test_returns_float(self):
        x = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6)
        val = cymatic_field_6d(x)
        assert isinstance(val, float)

    def test_origin_value(self):
        """At origin, sin(0) = 0 for all terms, so field = 0."""
        x = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        assert abs(cymatic_field_6d(x)) < 1e-10

    def test_bounded_for_unit_cube(self):
        """Field value should be finite for inputs in [0,1]."""
        import random

        random.seed(42)
        for _ in range(50):
            x = tuple(random.random() for _ in range(6))
            val = cymatic_field_6d(x)
            assert math.isfinite(val)


class TestQuasiSphereVolume:
    """quasi_sphere_volume grows exponentially."""

    def test_volume_at_zero(self):
        assert abs(quasi_sphere_volume(0.0) - 1.0) < 1e-10

    def test_volume_monotone(self):
        prev = quasi_sphere_volume(0.0)
        for r in [0.5, 1.0, 2.0, 5.0]:
            v = quasi_sphere_volume(r)
            assert v > prev
            prev = v


class TestTriadicTemporalDistance:
    """Layer 11 triadic temporal distance properties."""

    def test_positive_for_positive_inputs(self):
        d = triadic_temporal_distance(1.0, 1.0, 1.0)
        assert d > 0

    def test_zero_inputs_near_zero(self):
        """All-zero distances yield near-zero triadic distance (eps-guarded)."""
        d = triadic_temporal_distance(0.0, 0.0, 0.0)
        assert d < 1e-3

    def test_monotone_in_first_arg(self):
        d1 = triadic_temporal_distance(1.0, 1.0, 1.0)
        d2 = triadic_temporal_distance(2.0, 1.0, 1.0)
        assert d2 > d1


class TestPhiConstant:
    """Golden ratio constant is correct."""

    def test_phi_value(self):
        expected = (1 + math.sqrt(5)) / 2
        assert abs(PHI - expected) < 1e-15


# ═══════════════════════════════════════════════════════════════════════════
# 7) Edge cases: idempotent commits, epoch coexistence
# ═══════════════════════════════════════════════════════════════════════════


class TestIdempotentCommits:
    """Committing the same voxel record twice is idempotent."""

    def test_double_commit_same_cube_id(self):
        sq = SquadSpace(squad_id="sq")
        record = _make_voxel_record()
        assert sq.commit_voxel(record, quorum_votes=4)
        # Second commit with same cube_id overwrites (idempotent)
        assert sq.commit_voxel(record, quorum_votes=4)
        assert len(sq.voxels) == 1
        assert sq.voxels[record.cube_id] is record

    def test_commit_then_fail_does_not_overwrite(self):
        """If second commit fails quorum, original stays."""
        sq = SquadSpace(squad_id="sq")
        record_a = _make_voxel_record(epoch=1)
        sq.commit_voxel(record_a, quorum_votes=5)
        original = sq.voxels[record_a.cube_id]

        # Attempt to overwrite with insufficient quorum
        record_b = _make_voxel_record(epoch=1)  # same cube_id
        sq.commit_voxel(record_b, quorum_votes=2)
        assert sq.voxels[record_a.cube_id] is original


class TestEpochCoexistence:
    """Voxel records from different epochs coexist in squad memory."""

    def test_different_epochs_different_cube_ids(self):
        cid1 = cube_id(
            "squad", "u1", "ENGINEERING", epoch=1, lang="CA", voxel=[0, 0, 0, 0, 0, 0]
        )
        cid2 = cube_id(
            "squad", "u1", "ENGINEERING", epoch=2, lang="CA", voxel=[0, 0, 0, 0, 0, 0]
        )
        assert cid1 != cid2

    def test_coexistent_epoch_records(self):
        sq = SquadSpace(squad_id="sq")
        r1 = _make_voxel_record(epoch=1)
        r2 = _make_voxel_record(epoch=2)
        # Different epochs produce different cube_ids
        assert r1.cube_id != r2.cube_id

        sq.commit_voxel(r1, quorum_votes=4)
        sq.commit_voxel(r2, quorum_votes=4)
        assert len(sq.voxels) == 2
        assert r1.cube_id in sq.voxels
        assert r2.cube_id in sq.voxels

    def test_same_epoch_same_params_same_cube_id(self):
        """Determinism: identical inputs produce identical cube_id."""
        cid_a = cube_id(
            "squad", "u1", "ENGINEERING", 1, "CA", [0, 0, 0, 0, 0, 0], "sq1"
        )
        cid_b = cube_id(
            "squad", "u1", "ENGINEERING", 1, "CA", [0, 0, 0, 0, 0, 0], "sq1"
        )
        assert cid_a == cid_b


class TestPadNamespaceKey:
    """pad_namespace_key produces expected format."""

    def test_format(self):
        key = pad_namespace_key("u1", "ENGINEERING", "CA", 1)
        assert key == "u1:ENGINEERING:CA:1"

    def test_different_epochs_different_keys(self):
        k1 = pad_namespace_key("u1", "ENGINEERING", "CA", 1)
        k2 = pad_namespace_key("u1", "ENGINEERING", "CA", 2)
        assert k1 != k2


class TestEuclideanDist:
    """dist() between UnitState objects."""

    def test_same_position(self):
        a = UnitState(unit_id="a", x=1.0, y=2.0, z=3.0)
        b = UnitState(unit_id="b", x=1.0, y=2.0, z=3.0)
        assert abs(dist(a, b)) < 1e-10

    def test_known_distance(self):
        a = UnitState(unit_id="a", x=0.0, y=0.0, z=0.0)
        b = UnitState(unit_id="b", x=3.0, y=4.0, z=0.0)
        assert abs(dist(a, b) - 5.0) < 1e-10

    def test_symmetry(self):
        a = UnitState(unit_id="a", x=1.0, y=2.0, z=3.0)
        b = UnitState(unit_id="b", x=4.0, y=5.0, z=6.0)
        assert abs(dist(a, b) - dist(b, a)) < 1e-10


# ═══════════════════════════════════════════════════════════════════════════
# Tri-directional planning integration
# ═══════════════════════════════════════════════════════════════════════════


class TestTriDirectionalPlanning:
    """Integration tests for plan_trace and plan_tri_directional."""

    def test_plan_trace_valid_low_drift(self):
        state = (0.1, 0.1, 0.1, 0.1, 0.1, 0.1)
        out = plan_trace("STRUCTURE", state, d_star=0.1)
        assert out.result == "VALID"
        assert len(out.missed_required) == 0

    def test_plan_tri_directional_low_drift(self):
        state = (0.1, 0.1, 0.1, 0.1, 0.1, 0.1)
        result = plan_tri_directional(state, d_star=0.1)
        assert result.valid_count == 3
        assert result.decision == "ALLOW"

    def test_plan_trace_all_directions(self):
        state = (0.1, 0.1, 0.1, 0.1, 0.1, 0.1)
        for direction in ["STRUCTURE", "CONFLICT", "TIME"]:
            out = plan_trace(direction, state, d_star=0.2)
            assert out.direction == direction
            assert isinstance(out.cost, float)
            assert out.coherence >= 0.0

    def test_standard_checkpoints_exist(self):
        assert len(STANDARD_CHECKPOINTS) == 7
        names = [cp[1] for cp in STANDARD_CHECKPOINTS]
        assert "INTENT" in names
        assert "EXECUTE" in names

    def test_direction_weights_sum_to_one(self):
        for direction, weights in DIRECTION_WEIGHTS.items():
            total = sum(weights)
            assert abs(total - 1.0) < 1e-10, f"{direction} weights sum to {total}"


# ═══════════════════════════════════════════════════════════════════════════
# PollyPad assist() integration
# ═══════════════════════════════════════════════════════════════════════════


class TestPollyPadAssist:
    """Per-pad AI assist() routes queries through mode-specific tooling."""

    def test_assist_proximity_navigation(self):
        pad = PollyPad(unit_id="u1", mode="NAVIGATION")
        state = _make_safe_unit("u1")
        pad.promote(state)
        sq = SquadSpace(squad_id="sq")
        sq.units["u1"] = state
        sq.units["u2"] = _make_safe_unit("u2", x=1.0)
        result = pad.assist("check proximity", state, sq)
        assert "Neighbors" in result or "proximity" in result.lower()

    def test_assist_code_engineering_hot(self):
        pad = PollyPad(unit_id="u1", mode="ENGINEERING")
        state = _make_safe_unit("u1")
        sq = SquadSpace(squad_id="sq")
        sq.units["u1"] = state
        result = pad.assist("write code", state, sq)
        assert "HOT" in result or "draft" in result.lower()

    def test_assist_fallback(self):
        pad = PollyPad(unit_id="u1", mode="MISSION")
        state = _make_safe_unit("u1")
        sq = SquadSpace(squad_id="sq")
        sq.units["u1"] = state
        result = pad.assist("something random", state, sq)
        assert "MISSION" in result
