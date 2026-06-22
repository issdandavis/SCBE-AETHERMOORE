"""Tests for cloud_router -- routing through the geometric router's lifted space by probability-cloud flow.

The win over classic argmin: when the geometrically-closest agent is gated/too-far, argmin force-routes into
it, but the cloud reroutes to the next safe well; all-gated -> stuck -> escalate.
"""

from __future__ import annotations

from python.scbe.cloud_router import best_by_cost, route

TASK = {"KO": 0.9, "AV": 0.1}
AGENTS = [
    {"name": "alice", "profile": {"KO": 0.85, "AV": 0.15}},  # closest
    {"name": "bob", "profile": {"KO": 0.5, "AV": 0.5}},  # medium
    {"name": "cara", "profile": {"AV": 0.9, "KO": 0.1}},  # far
]


def _agents(**locks):
    return [{**a, "locked": locks.get(a["name"], False)} for a in AGENTS]


def test_routes_to_closest_when_none_gated():
    r = route(TASK, _agents())
    assert r["agent"] == "alice" and not r["stuck"]
    assert best_by_cost(TASK, _agents()) == "alice"  # agrees with argmin when nothing is gated


def test_reroutes_around_a_gated_closest_agent():
    gated = _agents(alice=True)
    # the classic baseline still force-routes into the gated closest agent...
    assert best_by_cost(TASK, gated) == "alice"
    # ...but the cloud flows around the peak to the next safe well
    assert route(TASK, gated)["agent"] == "bob"


def test_all_gated_escalates():
    r = route(TASK, _agents(alice=True, bob=True, cara=True))
    assert r["agent"] is None and r["stuck"] is True


def test_boundary_cost_treats_far_agents_as_peaks():
    # a tiny boundary_cost makes even moderately-distant agents unreachable peaks; only the closest survives
    r = route(TASK, _agents(), boundary_cost=0.5)
    assert r["agent"] == "alice"  # alice cost ~0.1 < 0.5; bob/cara are past the safe radius -> peaks


def test_costs_are_reported_for_inspection():
    r = route(TASK, _agents())
    assert set(r["costs"]) == {"alice", "bob", "cara"}
    assert r["costs"]["alice"] < r["costs"]["bob"] < r["costs"]["cara"]
