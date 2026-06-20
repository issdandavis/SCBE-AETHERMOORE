"""Geometric fleet router — tangent-vector routing through the tongue manifold."""

import numpy as np

from python.scbe.geometric_router import (
    Agent,
    Stream,
    Task,
    TONGUES,
    bind_streams,
    curved,
    depth,
    finsler_distance,
    geodesic,
    route_fleet,
    round_robin,
    route_streams,
    straight,
)


def _fleet():
    return [Agent(f"{t}-agent", {t: 1.0}) for t in TONGUES]


def test_finsler_is_agent_dependent():
    # a KO-flavored node is closer to the KO agent than to the UM agent
    node = {"KO": 1.0}
    d_ko = finsler_distance({"KO": 1.0}, node, {"KO": 1.0})
    d_um = finsler_distance({"UM": 1.0}, node, {"UM": 1.0})
    assert d_ko < d_um


def test_affinity_routing():
    fleet = _fleet()
    tasks = [Task(f"t{t}", {t: 1.0}) for t in TONGUES]
    routes = route_fleet(fleet, tasks, pressure=0.0)
    owner = {name: r.agent for r in routes for name in r.tasks}
    for t in TONGUES:
        assert owner[f"t{t}"] == f"{t}-agent"


def test_geometric_beats_round_robin():
    rng = np.random.default_rng(3)
    fleet = _fleet()
    tasks = [Task(f"task{i}", {t: float(rng.random()) for t in TONGUES}) for i in range(40)]
    geo = sum(r.total_cost for r in route_fleet(fleet, tasks))
    rr = round_robin(fleet, tasks)
    assert geo < rr


def test_fluid_pressure_spreads_load():
    # 12 identical KO tasks: with pressure they don't all pile on one agent's tour
    fleet = _fleet()
    tasks = [Task(f"k{i}", {"KO": 1.0}) for i in range(12)]
    routes = {r.agent: len(r.tasks) for r in route_fleet(fleet, tasks, pressure=2.0)}
    # KO-agent still wins most, but pressure forces some onto neighbors
    assert max(routes.values()) < 12


def test_geodesic_samples_and_endpoints():
    g = geodesic({"KO": 1.0}, {"DR": 1.0}, steps=10)
    assert len(g) == 11
    assert all(np.linalg.norm(p) < 1.0 for p in g)  # stays inside the ball


# --- instruction-stream routing: shapes that intersect ------------------------

import math  # noqa: E402


def test_two_straight_edges_intersect_once():
    # A runs along x at y=0; B is a vertical line at x=2 -- they cross at exactly one point
    a = Stream("A", ["a0", "a1", "a2", "a3"], [straight(1.0), depth(0.0)])
    b = Stream("B", ["b0", "b1", "b2", "b3"], [depth(2.0), straight(1.0, -2.0)])
    binds = bind_streams(a, b, eps=0.4)
    assert len(binds) == 1
    assert (binds[0]["a"], binds[0]["b"]) == ("a2", "b2")


def test_curved_edge_meets_rail_at_predicted_steps():
    # a straight rail at y=0; a sine edge dips to y~0 at even steps -> binds there, not at odd steps
    rail = Stream("rail", [f"r{i}" for i in range(6)], [straight(1.0), depth(0.0)])
    wave = Stream("wave", [f"w{i}" for i in range(6)], [straight(1.0), curved(2.0, math.pi / 2)])
    binds = bind_streams(rail, wave, eps=0.25)
    assert sorted(x["a_i"] for x in binds) == [0, 2, 4]  # the curve touches the line at even steps


def test_depth_gates_binding():
    # the SAME crossing curve binds at depth 0 but NOT when parked at a different depth
    rail = Stream("rail", [f"r{i}" for i in range(6)], [straight(1.0), depth(0.0), depth(0.0)])
    near = Stream("near", [f"n{i}" for i in range(6)], [straight(1.0), curved(2.0, math.pi / 2), depth(0.0)])
    far = Stream("far", [f"f{i}" for i in range(6)], [straight(1.0), curved(2.0, math.pi / 2), depth(5.0)])
    assert len(bind_streams(rail, near, eps=0.25)) > 0
    assert len(bind_streams(rail, far, eps=0.25)) == 0  # crosses in x,y but depth gates it out


def test_route_schedule_is_deterministic_and_well_shaped():
    rail = Stream("rail", ["inspect", "validate", "encode", "compare"], [straight(1.0), depth(0.0)])
    safety = Stream("safety", ["s0", "s1", "s2", "s3"], [straight(1.0), curved(2.0, math.pi / 2)])
    r1 = route_streams(rail, [safety], eps=0.25)
    r2 = route_streams(rail, [safety], eps=0.25)
    assert r1 == r2  # deterministic (parameter is the step index; no time, no randomness)
    assert [row["step"] for row in r1] == ["inspect", "validate", "encode", "compare"]
    assert r1[0]["bind"] and not r1[1]["bind"]  # binds at step 0, not at step 1
