"""Tests for the polylinear-recursive-mountain runtime packet."""
from __future__ import annotations

from python.scbe.poly_mountain import build_packet, route_satisfiability


def test_packet_has_all_section11_fields():
    pkt = build_packet("fix the failing GeoSeal route test")
    for key in (
        "goal", "context_views", "tongue_views", "dh_sector_labels",
        "assigned_lanes", "checkpoint_policy", "route_satisfiability",
        "apply_gate", "may_proceed",
    ):
        assert key in pkt, key


def test_six_tongue_views():
    pkt = build_packet("anything")
    assert set(pkt["tongue_views"]) == {"KO", "AV", "RU", "CA", "UM", "DR"}
    for view in pkt["tongue_views"].values():
        assert "role" in view and "lens" in view


def test_default_route_is_satisfiable_and_may_proceed():
    pkt = build_packet("implement and verify a small helper")
    rs = pkt["route_satisfiability"]
    assert rs["available"] is True       # z3 installed
    assert rs["satisfiable"] is True     # distinct lane writes, bounded budgets
    assert pkt["may_proceed"] is True


def test_safety_goal_labels_safety_sector():
    pkt = build_packet("delete old build artifacts and verify cleanup")
    assert "safety" in pkt["dh_sector_labels"]


def test_z3_catches_write_collision():
    # Two lanes declaring the SAME write target must be UNSAT (collision).
    lanes = [
        {"name": "Builder", "writes": "impl.py", "token_budget": 10, "tool_budget": 1},
        {"name": "Verifier", "writes": "impl.py", "token_budget": 10, "tool_budget": 1},
    ]
    rs = route_satisfiability(lanes)
    assert rs["available"] is True
    assert rs["satisfiable"] is False
    assert "impl.py" in rs["violations"]["write_collisions"]


def test_z3_catches_budget_over_cap():
    lanes = [
        {"name": "A", "writes": "a", "token_budget": 80_000, "tool_budget": 1},
        {"name": "B", "writes": "b", "token_budget": 80_000, "tool_budget": 1},
    ]
    rs = route_satisfiability(lanes, token_cap=100_000)
    assert rs["satisfiable"] is False
    assert rs["violations"]["token_over"] is True


def test_distinct_writes_are_satisfiable():
    lanes = [
        {"name": "Builder", "writes": "impl.py", "token_budget": 10, "tool_budget": 1},
        {"name": "Verifier", "writes": "tests.py", "token_budget": 10, "tool_budget": 1},
    ]
    rs = route_satisfiability(lanes)
    assert rs["satisfiable"] is True


def test_apply_gate_is_the_blocks_engine():
    pkt = build_packet("anything")
    assert pkt["apply_gate"]["engine"] == "scbe.blocks"
    assert pkt["apply_gate"]["verified"] is True
