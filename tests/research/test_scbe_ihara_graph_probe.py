from __future__ import annotations

from pathlib import Path

from scripts.research.scbe_ihara_graph_probe import (
    ToolNode,
    build_undirected_edges,
    graph_metrics_for_edges,
    nonbacktracking_transitions,
    oriented_arcs,
    run_probe,
    spectral_radius_from_transitions,
)


def test_path_graph_has_no_cycle_pressure() -> None:
    nodes = ["a", "b", "c"]
    edges = {("a", "b"), ("b", "c")}
    metrics = graph_metrics_for_edges(nodes, edges)

    assert metrics.cyclomatic_number == 0
    assert metrics.hashimoto_rho == 0.0
    assert metrics.ihara_first_pole_radius is None


def test_triangle_graph_has_nonbacktracking_cycle_pressure() -> None:
    arcs = oriented_arcs({("a", "b"), ("b", "c"), ("a", "c")})
    rho = spectral_radius_from_transitions(nonbacktracking_transitions(arcs))
    metrics = graph_metrics_for_edges(
        ["a", "b", "c"], {("a", "b"), ("b", "c"), ("a", "c")}
    )

    assert metrics.cyclomatic_number == 1
    assert 0.99 <= rho <= 1.01
    assert 0.99 <= metrics.ihara_first_pole_radius <= 1.01


def test_star_path_edge_rules_connect_same_runtime_and_hubs() -> None:
    nodes = [
        ToolNode("node-a", "KO", "node", False, 0),
        ToolNode("node-b", "KO", "node", False, 0),
        ToolNode("py-a", "AV", "python", False, 0),
        ToolNode("hub", "DR", "python", True, 0),
    ]
    edges = build_undirected_edges(nodes)

    assert ("node-a", "node-b") in edges
    assert ("hub", "node-a") in edges
    assert ("hub", "py-a") in edges


def test_real_registry_probe_reports_quarantine_metrics() -> None:
    result = run_probe(
        tools_json=Path("packages/agent-bus/tools.json"),
        null_trials=5,
        seed=5,
    )
    metrics = result["metrics"]

    assert metrics["node_count"] > 10
    assert metrics["edge_count"] > metrics["node_count"]
    assert metrics["hashimoto_rho"] > 0.0
    assert result["decision_record"]["promotion"] == "QUARANTINE_RESEARCH_ONLY"
