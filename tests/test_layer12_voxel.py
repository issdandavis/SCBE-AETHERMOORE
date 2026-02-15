"""
Layer 12 + Voxel Addressing regression tests — backend parity.

Validates the math shared between the physics sim frontend and
the backend (Redis/RocksDB/S3). These are the edge-case boundaries
you MUST nail before wiring real storage.

@module tests/test_layer12_voxel
@layer Layer 5, Layer 12, Layer 13
@version 3.2.4
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from scbe_governance_math import (
    DANGER_QUORUM,
    PHI,
    Point3,
    bft_consensus,
    clamp,
    coherence_from_phases,
    drift_star,
    encode_voxel_key,
    inv_metric_factor,
    layer12_cost,
    local_vote,
    poincare_dist_3d,
    quantize,
    wrap_pi,
    _b36,
)


# ═══════════════════════════════════════════════════════════════
# coherence_from_phases
# ═══════════════════════════════════════════════════════════════


class TestCoherence:
    def test_all_equal_is_one(self):
        phases = {k: 0.25 for k in ["KO", "UM", "RU", "AV", "DR", "CA"]}
        c = coherence_from_phases(phases)
        assert abs(c - 1.0) < 1e-12

    def test_range_bounded(self):
        phases = {"KO": 0, "UM": math.pi, "RU": 0, "AV": math.pi, "DR": 0, "CA": math.pi}
        c = coherence_from_phases(phases)
        assert -1.0 <= c <= 1.0

    def test_all_zero_is_one(self):
        phases = {k: 0.0 for k in ["KO", "UM", "RU", "AV", "DR", "CA"]}
        assert coherence_from_phases(phases) == pytest.approx(1.0)

    def test_alternating_phases(self):
        # 3 at 0, 3 at π → lots of negative cosines
        phases = {"KO": 0, "AV": 0, "RU": 0, "CA": math.pi, "UM": math.pi, "DR": math.pi}
        c = coherence_from_phases(phases)
        # 6 same-pair cos(0)=1 + 9 cross-pair cos(π)=-1 → (6-9)/15 = -0.2
        assert c == pytest.approx(-0.2, abs=1e-10)


# ═══════════════════════════════════════════════════════════════
# quantize
# ═══════════════════════════════════════════════════════════════


class TestQuantize:
    def test_endpoints(self):
        assert quantize(-3, -3, 3, 24) == 0
        assert quantize(3, -3, 3, 24) == 23
        assert quantize(999, -3, 3, 24) == 23
        assert quantize(-999, -3, 3, 24) == 0

    def test_monotone_non_decreasing(self):
        last = -1
        for v_int in range(-30, 31):
            v = v_int / 10.0
            q = quantize(v, -3, 3, 24)
            assert q >= last
            last = q

    def test_midpoint(self):
        q = quantize(0, -3, 3, 24)
        # t = 0.5, q = round(0.5 * 23) = round(11.5) = 12
        assert q == 12

    def test_single_bin(self):
        assert quantize(5, 0, 10, 1) == 0

    def test_two_bins(self):
        assert quantize(0, 0, 10, 2) == 0
        assert quantize(10, 0, 10, 2) == 1


# ═══════════════════════════════════════════════════════════════
# drift_star
# ═══════════════════════════════════════════════════════════════


class TestDriftStar:
    def test_increases_with_radius(self):
        w = {"KO": 1, "UM": 1, "RU": 1, "AV": 1, "DR": 1, "CA": 1}
        d1 = drift_star(Point3(0.1, 0.0, 0.0), w)
        d2 = drift_star(Point3(1.0, 0.0, 0.0), w)
        assert d2 > d1

    def test_penalizes_imbalance(self):
        p = Point3(1.0, 0.0, 0.0)
        w_bal = {"KO": 1, "UM": 1, "RU": 1, "AV": 1, "DR": 1, "CA": 1}
        w_imb = {"KO": 6, "UM": 0.1, "RU": 0.1, "AV": 0.1, "DR": 0.1, "CA": 0.1}
        assert drift_star(p, w_imb) > drift_star(p, w_bal)

    def test_origin_is_zero(self):
        w = {"KO": 1, "UM": 1, "RU": 1, "AV": 1, "DR": 1, "CA": 1}
        assert drift_star(Point3(0, 0, 0), w) == 0.0

    def test_balanced_weights_factor(self):
        # balanced: max/sum = 1/6, factor = 1 + 1.5*(1/6) = 1.25
        w = {"KO": 1, "UM": 1, "RU": 1, "AV": 1, "DR": 1, "CA": 1}
        p = Point3(1, 0, 0)
        assert drift_star(p, w) == pytest.approx(1.25)


# ═══════════════════════════════════════════════════════════════
# layer12_cost
# ═══════════════════════════════════════════════════════════════


class TestLayer12Cost:
    def test_monotone_in_dstar(self):
        c = 1.0
        assert layer12_cost(0.1, c) < layer12_cost(0.2, c) < layer12_cost(0.3, c)

    def test_increases_when_coherence_drops(self):
        d = 0.6
        assert layer12_cost(d, 1.0) < layer12_cost(d, 0.5) < layer12_cost(d, 0.0)

    def test_at_origin_with_full_coherence(self):
        # d*=0, C=1: cost = 1 * π^0 * (1 + 0) = 1
        assert layer12_cost(0, 1.0) == pytest.approx(1.0)

    def test_super_exponential_growth(self):
        # d*=3, C=0.5 should be huge
        cost = layer12_cost(3.0, 0.5)
        assert cost > 100  # π^(1.618*3) ≈ π^4.854 ≈ 260; × 1.5 ≈ 390

    def test_coherence_penalty_doubles(self):
        # C=0 → factor 2, C=1 → factor 1
        d = 1.0
        ratio = layer12_cost(d, 0.0) / layer12_cost(d, 1.0)
        assert ratio == pytest.approx(2.0)


# ═══════════════════════════════════════════════════════════════
# Poincaré ball distance
# ═══════════════════════════════════════════════════════════════


class TestPoincareDistance:
    def test_same_point_is_zero(self):
        p = Point3(1, 1, 1)
        assert poincare_dist_3d(p, p) == pytest.approx(0.0, abs=1e-8)

    def test_symmetry(self):
        a = Point3(0.5, 0, 0)
        b = Point3(0, 0.5, 0)
        assert poincare_dist_3d(a, b) == pytest.approx(poincare_dist_3d(b, a))

    def test_increases_with_separation(self):
        o = Point3(0, 0, 0)
        d1 = poincare_dist_3d(o, Point3(0.5, 0, 0))
        d2 = poincare_dist_3d(o, Point3(1.5, 0, 0))
        assert d2 > d1

    def test_origin_to_origin(self):
        o = Point3(0, 0, 0)
        assert poincare_dist_3d(o, o) == pytest.approx(0.0, abs=1e-12)

    def test_triangle_inequality(self):
        a = Point3(0.3, 0, 0)
        b = Point3(0, 0.3, 0)
        c = Point3(0, 0, 0.3)
        dab = poincare_dist_3d(a, b)
        dbc = poincare_dist_3d(b, c)
        dac = poincare_dist_3d(a, c)
        assert dac <= dab + dbc + 1e-10


# ═══════════════════════════════════════════════════════════════
# Inverse metric factor
# ═══════════════════════════════════════════════════════════════


class TestInvMetricFactor:
    def test_at_origin(self):
        # λ(0) = 2/(1-0) = 2, 1/λ² = 0.25
        f = inv_metric_factor(Point3(0, 0, 0))
        assert f == pytest.approx(0.25)

    def test_decreases_away_from_origin(self):
        f0 = inv_metric_factor(Point3(0, 0, 0))
        f1 = inv_metric_factor(Point3(1, 0, 0))
        assert f1 < f0

    def test_always_positive(self):
        for x in [0, 0.5, 1.0, 2.0, 2.8]:
            assert inv_metric_factor(Point3(x, 0, 0)) > 0


# ═══════════════════════════════════════════════════════════════
# BFT consensus
# ═══════════════════════════════════════════════════════════════


class TestBFTConsensus:
    def test_all_allow(self):
        votes = {k: "ALLOW" for k in ["KO", "AV", "RU", "CA", "UM", "DR"]}
        assert bft_consensus(votes) == "ALLOW"

    def test_all_deny(self):
        votes = {k: "DENY" for k in ["KO", "AV", "RU", "CA", "UM", "DR"]}
        assert bft_consensus(votes) == "DENY"

    def test_one_faulty_cant_deny(self):
        votes = {"KO": "DENY", "AV": "ALLOW", "RU": "ALLOW", "CA": "ALLOW", "UM": "ALLOW", "DR": "ALLOW"}
        assert bft_consensus(votes) == "ALLOW"

    def test_threshold_deny(self):
        # Exactly 4 DENY → should trigger DENY
        votes = {"KO": "DENY", "AV": "DENY", "RU": "DENY", "CA": "DENY", "UM": "ALLOW", "DR": "ALLOW"}
        assert bft_consensus(votes) == "DENY"

    def test_three_deny_not_enough(self):
        votes = {"KO": "DENY", "AV": "DENY", "RU": "DENY", "CA": "ALLOW", "UM": "ALLOW", "DR": "ALLOW"}
        assert bft_consensus(votes) == "ALLOW"

    def test_quarantine_threshold(self):
        votes = {"KO": "QUARANTINE", "AV": "QUARANTINE", "RU": "QUARANTINE", "CA": "QUARANTINE", "UM": "ALLOW", "DR": "ALLOW"}
        assert bft_consensus(votes) == "QUARANTINE"

    def test_mixed_deny_quarantine(self):
        # 3 DENY + 2 QUARANTINE + 1 ALLOW → neither DENY nor QUARANTINE reaches 4
        votes = {"KO": "DENY", "AV": "DENY", "RU": "DENY", "CA": "QUARANTINE", "UM": "QUARANTINE", "DR": "ALLOW"}
        assert bft_consensus(votes) == "ALLOW"

    def test_deny_takes_priority_over_quarantine(self):
        # 4 DENY + 2 QUARANTINE → DENY wins
        votes = {"KO": "DENY", "AV": "DENY", "RU": "DENY", "CA": "DENY", "UM": "QUARANTINE", "DR": "QUARANTINE"}
        assert bft_consensus(votes) == "DENY"


# ═══════════════════════════════════════════════════════════════
# Local vote
# ═══════════════════════════════════════════════════════════════


class TestLocalVote:
    def test_low_cost_allows(self):
        phases = {k: 0.0 for k in ["KO", "AV", "RU", "CA", "UM", "DR"]}
        weights = {k: 1.0 for k in phases}
        v = local_vote("KO", 1.0, 1.0, phases, weights)
        assert v == "ALLOW"

    def test_high_cost_denies(self):
        phases = {k: 0.0 for k in ["KO", "AV", "RU", "CA", "UM", "DR"]}
        weights = {k: 1.0 for k in phases}
        v = local_vote("KO", 100.0, 0.0, phases, weights)
        assert v == "DENY"

    def test_low_coherence_increases_risk(self):
        phases = {k: 0.0 for k in ["KO", "AV", "RU", "CA", "UM", "DR"]}
        weights = {k: 1.0 for k in phases}
        # Same cost, different coherence
        v_high = local_vote("KO", 8.0, 1.0, phases, weights)
        v_low = local_vote("KO", 8.0, 0.0, phases, weights)
        # low coherence should escalate decision
        decisions = {"ALLOW": 0, "QUARANTINE": 1, "DENY": 2}
        assert decisions[v_low] >= decisions[v_high]


# ═══════════════════════════════════════════════════════════════
# Voxel key encoding
# ═══════════════════════════════════════════════════════════════


class TestVoxelKey:
    def test_format(self):
        base = {"X": 5, "Y": 10, "Z": 0, "V": 23, "P": 12, "S": 1}
        key = encode_voxel_key(base, "ALLOW")
        assert key.startswith("qr:A:")
        parts = key.split(":")
        assert len(parts) == 8

    def test_decision_prefix(self):
        base = {"X": 0, "Y": 0, "Z": 0, "V": 0, "P": 0, "S": 0}
        assert encode_voxel_key(base, "ALLOW").split(":")[1] == "A"
        assert encode_voxel_key(base, "QUARANTINE").split(":")[1] == "Q"
        assert encode_voxel_key(base, "DENY").split(":")[1] == "D"

    def test_deterministic(self):
        base = {"X": 3, "Y": 7, "Z": 11, "V": 20, "P": 5, "S": 15}
        k1 = encode_voxel_key(base, "QUARANTINE")
        k2 = encode_voxel_key(base, "QUARANTINE")
        assert k1 == k2


# ═══════════════════════════════════════════════════════════════
# wrap_pi
# ═══════════════════════════════════════════════════════════════


class TestWrapPi:
    def test_zero(self):
        assert wrap_pi(0) == pytest.approx(0.0)

    def test_pi(self):
        assert wrap_pi(math.pi) == pytest.approx(math.pi)

    def test_two_pi(self):
        assert wrap_pi(2 * math.pi) == pytest.approx(0.0, abs=1e-10)

    def test_negative(self):
        assert wrap_pi(-math.pi) == pytest.approx(math.pi, abs=1e-10)

    def test_large_angle(self):
        r = wrap_pi(7 * math.pi)
        assert -math.pi < r <= math.pi


# ═══════════════════════════════════════════════════════════════
# b36 encoding
# ═══════════════════════════════════════════════════════════════


class TestB36:
    def test_zero(self):
        assert _b36(0) == "00"

    def test_small(self):
        assert _b36(10) == "0a"

    def test_35(self):
        assert _b36(35) == "0z"

    def test_36(self):
        assert _b36(36) == "10"
