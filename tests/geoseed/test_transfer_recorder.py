"""Tests for AtomTransferRecorder stub."""

import math
import pytest

PHI = (1.0 + math.sqrt(5.0)) / 2.0
LN_PHI = math.log(PHI)


@pytest.fixture
def mod():
    from src.geoseed.transfer_recorder import (
        AtomTransferRecorder, transfer_cost, TransferMatrix,
        TONGUE_ORDER, TONGUE_INDEX, LN_PHI as MODEL_LN_PHI,
    )
    return {
        "Recorder": AtomTransferRecorder,
        "cost": transfer_cost,
        "Matrix": TransferMatrix,
        "order": TONGUE_ORDER,
        "index": TONGUE_INDEX,
        "ln_phi": MODEL_LN_PHI,
    }

@pytest.fixture
def rec(mod):
    return mod["Recorder"](session_id="test")


# ── transfer_cost ─────────────────────────────────────────────────────────────

def test_cost_self_is_zero(mod):
    for t in mod["order"]:
        assert mod["cost"](t, t) == 0.0

def test_cost_adjacent_equals_ln_phi(mod):
    pairs = list(zip(mod["order"], mod["order"][1:]))
    for a, b in pairs:
        assert abs(mod["cost"](a, b) - LN_PHI) < 1e-12
        assert abs(mod["cost"](b, a) - LN_PHI) < 1e-12

def test_cost_symmetric(mod):
    assert abs(mod["cost"]("KO", "DR") - mod["cost"]("DR", "KO")) < 1e-12

def test_cost_ko_to_dr_is_5_ln_phi(mod):
    assert abs(mod["cost"]("KO", "DR") - 5 * LN_PHI) < 1e-12

def test_cost_unknown_tongue_raises(mod):
    with pytest.raises(ValueError):
        mod["cost"]("XX", "KO")


# ── record + basic queries ────────────────────────────────────────────────────

def test_empty_recorder(rec):
    assert rec.event_count == 0
    assert rec.total_geodesic_cost() == 0.0
    assert rec.mean_hop_distance() == 0.0

def test_record_single_event(rec):
    evt = rec.record("KO", "AV", "def")
    assert rec.event_count == 1
    assert evt.from_tongue == "KO"
    assert evt.to_tongue == "AV"
    assert evt.token == "def"
    assert abs(evt.geodesic_cost - LN_PHI) < 1e-12
    assert evt.is_self is False
    assert evt.step == 0

def test_record_self_transfer(rec):
    evt = rec.record("CA", "CA", "heapq")
    assert evt.is_self is True
    assert evt.geodesic_cost == 0.0

def test_record_batch(rec):
    rec.record_batch([("KO", "AV", "x"), ("AV", "RU", "y"), ("RU", "CA", "z")])
    assert rec.event_count == 3

def test_steps_increment(rec):
    rec.record("KO", "AV", "a")
    rec.record("AV", "RU", "b")
    steps = [e.step for e in rec.events]
    assert steps == [0, 1]

def test_reset_clears(rec):
    rec.record("KO", "AV", "tok")
    rec.reset()
    assert rec.event_count == 0

def test_events_for_token(rec):
    rec.record("KO", "AV", "import")
    rec.record("CA", "UM", "import")
    rec.record("RU", "RU", "def")
    evts = rec.events_for_token("import")
    assert len(evts) == 2

def test_events_from(rec):
    rec.record("KO", "AV", "a")
    rec.record("KO", "CA", "b")
    rec.record("AV", "RU", "c")
    assert len(rec.events_from("KO")) == 2

def test_events_to(rec):
    rec.record("KO", "AV", "a")
    rec.record("RU", "AV", "b")
    assert len(rec.events_to("AV")) == 2

def test_unknown_tongue_raises(rec):
    with pytest.raises(ValueError):
        rec.record("KO", "ZZ", "tok")


# ── geodesic cost accumulation ────────────────────────────────────────────────

def test_total_geodesic_cost(rec):
    rec.record("KO", "AV", "a")   # 1·ln(φ)
    rec.record("AV", "CA", "b")   # 2·ln(φ)
    rec.record("KO", "KO", "c")   # 0
    expected = 3 * LN_PHI
    assert abs(rec.total_geodesic_cost() - expected) < 1e-12

def test_mean_hop_excludes_self(rec):
    rec.record("KO", "AV", "a")   # 1·ln(φ)
    rec.record("AV", "DR", "b")   # 4·ln(φ)
    rec.record("KO", "KO", "c")   # self — excluded from mean
    expected_mean = (1 + 4) * LN_PHI / 2
    assert abs(rec.mean_hop_distance() - expected_mean) < 1e-12

def test_mean_hop_all_self_returns_zero(rec):
    rec.record("CA", "CA", "x")
    rec.record("DR", "DR", "y")
    assert rec.mean_hop_distance() == 0.0


# ── transfer matrix ───────────────────────────────────────────────────────────

def test_matrix_shape_is_6x6(rec, mod):
    rec.record("KO", "AV", "tok")
    mx = rec.transfer_matrix()
    assert len(mx.counts) == 6
    assert all(len(row) == 6 for row in mx.counts)

def test_matrix_counts_correct(rec):
    rec.record("KO", "AV", "a")
    rec.record("KO", "AV", "b")
    rec.record("AV", "RU", "c")
    mx = rec.transfer_matrix()
    assert mx.counts[0][1] == 2  # KO→AV
    assert mx.counts[1][2] == 1  # AV→RU
    assert mx.counts[1][0] == 0  # AV→KO = 0

def test_matrix_total_events(rec):
    rec.record_batch([("KO", "AV", "a"), ("RU", "CA", "b"), ("DR", "DR", "c")])
    mx = rec.transfer_matrix()
    assert mx.total_events == 3

def test_matrix_self_cross_split(rec):
    rec.record("KO", "KO", "self1")
    rec.record("CA", "CA", "self2")
    rec.record("KO", "AV", "cross1")
    mx = rec.transfer_matrix()
    assert mx.self_transfer_count == 2
    assert mx.cross_transfer_count == 1

def test_matrix_rates_row_normalised(rec):
    rec.record("KO", "AV", "a")
    rec.record("KO", "CA", "b")
    mx = rec.transfer_matrix()
    row_sum = sum(mx.rates[0])  # KO row
    assert abs(row_sum - 1.0) < 1e-9

def test_matrix_costs_are_n_ln_phi(rec, mod):
    rec.record("KO", "AV", "tok")
    mx = rec.transfer_matrix()
    for i in range(6):
        for j in range(6):
            expected = abs(i - j) * LN_PHI
            assert abs(mx.costs[i][j] - expected) < 1e-12

def test_matrix_costs_diagonal_zero(rec, mod):
    rec.record("KO", "AV", "tok")
    mx = rec.transfer_matrix()
    for i in range(6):
        assert mx.costs[i][i] == 0.0

def test_dominant_flow_excludes_self(rec):
    rec.record_batch([
        ("KO", "KO", "s1"), ("KO", "KO", "s2"),  # self — should NOT appear
        ("KO", "AV", "c1"), ("KO", "AV", "c2"), ("KO", "AV", "c3"),
    ])
    mx = rec.transfer_matrix()
    flows = mx.dominant_flow()
    froms = [f for f, t, c in flows]
    tos   = [t for f, t, c in flows]
    for f, t in zip(froms, tos):
        assert f != t

def test_empty_matrix_total_zero(mod):
    rec = mod["Recorder"]()
    mx = rec.transfer_matrix()
    assert mx.total_events == 0
    assert mx.self_transfer_count == 0
    assert mx.cross_transfer_count == 0


# ── serialisation ─────────────────────────────────────────────────────────────

def test_to_dict_schema_version(rec):
    rec.record("KO", "AV", "tok")
    d = rec.to_dict()
    assert d["schema_version"] == "geoseed_transfer_recorder_v1"

def test_to_dict_matrix_schema_version(rec):
    rec.record("KO", "AV", "tok")
    d = rec.to_dict()
    assert d["matrix"]["schema_version"] == "geoseed_transfer_matrix_v1"

def test_summary_string_non_empty(rec):
    rec.record("KO", "AV", "tok")
    s = rec.summary()
    assert len(s) > 50
    assert "KO" in s

def test_summary_empty_recorder(rec):
    s = rec.summary()
    assert "no events" in s
