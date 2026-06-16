"""Geometric fleet router — tangent-vector routing through the tongue manifold."""
import numpy as np

from python.scbe.geometric_router import (
    Agent, Task, TONGUES, finsler_distance, geodesic, route_fleet, round_robin,
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
