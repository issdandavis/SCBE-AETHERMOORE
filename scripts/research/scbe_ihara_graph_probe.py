"""SCBE agent-bus Ihara-style graph-cycle probe.

Hurwitz zeta is the control that shows shape alone is not enough. The applied
SCBE version asks whether the real tool graph has cycle pressure. Ihara zeta for
graphs is governed by the non-backtracking edge adjacency (Hashimoto) operator:

    Z_G(u)^-1 = det(I - u B)

The smallest positive pole is at roughly u = 1 / rho(B), where rho(B) is the
spectral radius of the non-backtracking matrix. In practical terms:

    higher rho(B)  -> more closed non-backtracking routing pressure
    smaller 1/rho  -> earlier zeta pole, less tree-like routing surface

This is a read-side research probe. It does not alter routing.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TOOLS_JSON = REPO_ROOT / "packages" / "agent-bus" / "tools.json"
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "scbe_ihara_graph_probe"
TONGUE_ORDER = ("KO", "AV", "RU", "CA", "UM", "DR")
HUB_NAMES = {"scbe-agentbus", "scbe-compass"}
RU_NAMES = {
    "scbe-antivirus",
    "scbe-governance-fuse",
    "scbe-runtime",
    "scbe-flow",
    "scbe-tongues",
    "tokenizer-atomic-selfcheck",
}
DR_NAMES = {
    "scbe-agentbus",
    "ai-router-health",
    "ai-router-call",
    "agentic-pazaak-board",
    "coding-board-trial",
    "chessboard-dev-stack",
}
UM_NAMES = {
    "video-pocket-director",
    "youtube-video-review",
    "youtube-article-dry-run",
    "youtube-upload-unlisted",
    "writing-roundtable-review",
}


@dataclass(frozen=True)
class ToolNode:
    name: str
    tongue: str
    command: str
    is_hub: bool
    governance_cost: int


@dataclass(frozen=True)
class GraphMetrics:
    node_count: int
    edge_count: int
    component_count: int
    cyclomatic_number: int
    avg_degree: float
    max_degree: int
    nonbacktracking_arc_count: int
    hashimoto_rho: float
    ihara_first_pole_radius: float | None
    random_null_rho_p50: float
    random_null_rho_p95: float
    rho_minus_null_p50: float


def classify_tool(raw: dict[str, object]) -> ToolNode:
    name = str(raw["name"])
    command = "node" if raw.get("command") == "node" else "python"
    is_hub = name in HUB_NAMES

    if command == "node":
        tongue = "KO"
    elif name.startswith("geoseal-"):
        tongue = "CA"
    elif name.startswith("research-"):
        tongue = "AV"
    elif name in RU_NAMES:
        tongue = "RU"
    elif name in DR_NAMES:
        tongue = "DR"
    elif name in UM_NAMES:
        tongue = "UM"
    else:
        tongue = "RU"

    governance_cost = 0
    if name.startswith("geoseal-"):
        governance_cost = 2
    elif name.startswith("scbe-governance") or name.startswith("scbe-antivirus"):
        governance_cost = 1
    elif "upload" in name or "youtube-upload" in name:
        governance_cost = 1

    return ToolNode(
        name=name,
        tongue=tongue,
        command=command,
        is_hub=is_hub,
        governance_cost=governance_cost,
    )


def base_edge_allowed(left: ToolNode, right: ToolNode) -> bool:
    return (
        left.tongue == right.tongue
        or left.is_hub
        or right.is_hub
        or left.command == right.command
    )


def load_tool_nodes(tools_json: Path = DEFAULT_TOOLS_JSON) -> list[ToolNode]:
    raw_tools = json.loads(tools_json.read_text(encoding="utf-8"))
    return [classify_tool(raw) for raw in raw_tools]


def build_undirected_edges(nodes: Sequence[ToolNode]) -> set[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for idx, left in enumerate(nodes):
        for right in nodes[idx + 1 :]:
            if base_edge_allowed(left, right):
                edges.add(tuple(sorted((left.name, right.name))))
    return edges


def adjacency_from_edges(
    nodes: Sequence[str], edges: Iterable[tuple[str, str]]
) -> dict[str, set[str]]:
    adjacency = {node: set() for node in nodes}
    for left, right in edges:
        adjacency[left].add(right)
        adjacency[right].add(left)
    return adjacency


def connected_components(adjacency: dict[str, set[str]]) -> list[set[str]]:
    seen: set[str] = set()
    components: list[set[str]] = []
    for start in adjacency:
        if start in seen:
            continue
        component: set[str] = set()
        queue = deque([start])
        seen.add(start)
        while queue:
            node = queue.popleft()
            component.add(node)
            for nxt in adjacency[node]:
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        components.append(component)
    return components


def oriented_arcs(edges: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    arcs: list[tuple[str, str]] = []
    for left, right in sorted(edges):
        arcs.append((left, right))
        arcs.append((right, left))
    return arcs


def nonbacktracking_transitions(arcs: Sequence[tuple[str, str]]) -> list[list[int]]:
    by_source: dict[str, list[int]] = {}
    for idx, (source, _target) in enumerate(arcs):
        by_source.setdefault(source, []).append(idx)

    transitions: list[list[int]] = []
    for source, target in arcs:
        next_indices = [
            idx for idx in by_source.get(target, []) if arcs[idx][1] != source
        ]
        transitions.append(next_indices)
    return transitions


def spectral_radius_from_transitions(
    transitions: Sequence[Sequence[int]],
    iterations: int = 80,
    tolerance: float = 1e-10,
) -> float:
    size = len(transitions)
    if size == 0:
        return 0.0
    vector = [1.0 / size] * size
    last_lambda = 0.0
    for _ in range(iterations):
        nxt = [0.0] * size
        for idx, value in enumerate(vector):
            if value == 0.0:
                continue
            for target in transitions[idx]:
                nxt[target] += value
        norm = sum(nxt)
        if norm == 0.0:
            return 0.0
        current_lambda = norm / max(sum(vector), 1e-12)
        nxt = [value / norm for value in nxt]
        if abs(current_lambda - last_lambda) < tolerance:
            return current_lambda
        vector = nxt
        last_lambda = current_lambda
    return last_lambda


def graph_metrics_for_edges(
    node_names: Sequence[str],
    edges: set[tuple[str, str]],
    null_rhos: Sequence[float] | None = None,
) -> GraphMetrics:
    adjacency = adjacency_from_edges(node_names, edges)
    degrees = [len(adjacency[node]) for node in node_names]
    components = connected_components(adjacency)
    arcs = oriented_arcs(edges)
    transitions = nonbacktracking_transitions(arcs)
    rho = spectral_radius_from_transitions(transitions)
    pole = None if rho == 0.0 else 1.0 / rho
    random_p50 = statistics.median(null_rhos) if null_rhos else 0.0
    random_p95 = (
        sorted(null_rhos)[int(math.ceil(0.95 * len(null_rhos))) - 1]
        if null_rhos
        else 0.0
    )
    return GraphMetrics(
        node_count=len(node_names),
        edge_count=len(edges),
        component_count=len(components),
        cyclomatic_number=len(edges) - len(node_names) + len(components),
        avg_degree=statistics.fmean(degrees) if degrees else 0.0,
        max_degree=max(degrees) if degrees else 0,
        nonbacktracking_arc_count=len(arcs),
        hashimoto_rho=rho,
        ihara_first_pole_radius=pole,
        random_null_rho_p50=random_p50,
        random_null_rho_p95=random_p95,
        rho_minus_null_p50=rho - random_p50,
    )


def random_edges_same_density(
    node_names: Sequence[str],
    edge_count: int,
    rng: random.Random,
) -> set[tuple[str, str]]:
    possible = [
        (node_names[i], node_names[j])
        for i in range(len(node_names))
        for j in range(i + 1, len(node_names))
    ]
    if edge_count > len(possible):
        raise ValueError("edge_count exceeds complete graph")
    return {tuple(sorted(edge)) for edge in rng.sample(possible, edge_count)}


def null_rhos_same_density(
    node_names: Sequence[str],
    edge_count: int,
    trials: int = 100,
    seed: int = 31,
) -> list[float]:
    rng = random.Random(seed)
    rhos: list[float] = []
    for _trial in range(trials):
        edges = random_edges_same_density(node_names, edge_count, rng)
        arcs = oriented_arcs(edges)
        rhos.append(spectral_radius_from_transitions(nonbacktracking_transitions(arcs)))
    return rhos


def tongue_counts(nodes: Sequence[ToolNode]) -> dict[str, int]:
    counts = {tongue: 0 for tongue in TONGUE_ORDER}
    for node in nodes:
        counts[node.tongue] = counts.get(node.tongue, 0) + 1
    return counts


def high_degree_nodes(
    nodes: Sequence[ToolNode],
    adjacency: dict[str, set[str]],
    limit: int = 10,
) -> list[dict[str, object]]:
    by_name = {node.name: node for node in nodes}
    ranked = sorted(adjacency, key=lambda name: (-len(adjacency[name]), name))[:limit]
    return [
        {
            "name": name,
            "degree": len(adjacency[name]),
            "tongue": by_name[name].tongue,
            "is_hub": by_name[name].is_hub,
            "governance_cost": by_name[name].governance_cost,
        }
        for name in ranked
    ]


def run_probe(
    tools_json: Path = DEFAULT_TOOLS_JSON,
    null_trials: int = 100,
    seed: int = 31,
    out_dir: Path | None = None,
) -> dict[str, object]:
    nodes = load_tool_nodes(tools_json)
    node_names = sorted(node.name for node in nodes)
    edges = build_undirected_edges(nodes)
    null_rhos = null_rhos_same_density(
        node_names, len(edges), trials=null_trials, seed=seed
    )
    metrics = graph_metrics_for_edges(node_names, edges, null_rhos=null_rhos)
    adjacency = adjacency_from_edges(node_names, edges)

    cycle_heavy = metrics.cyclomatic_number > metrics.node_count
    above_random = metrics.hashimoto_rho > metrics.random_null_rho_p95
    verdict = (
        "CYCLE_HEAVY_STRUCTURED_GRAPH"
        if cycle_heavy
        else "TREE_LIKE_OR_LOW_CYCLE_GRAPH"
    )
    if cycle_heavy and not above_random:
        verdict = "CYCLE_HEAVY_DENSITY_EXPLAINED"

    summary: dict[str, object] = {
        "tools_json": str(tools_json),
        "metrics": asdict(metrics),
        "tongue_counts": tongue_counts(nodes),
        "hub_nodes": [node.name for node in nodes if node.is_hub],
        "high_degree_nodes": high_degree_nodes(nodes, adjacency),
        "decision_record": {
            "promotion": "QUARANTINE_RESEARCH_ONLY",
            "verdict": verdict,
            "cycle_heavy": cycle_heavy,
            "rho_above_density_null95": above_random,
            "claim_boundary": (
                "Ihara-style read-side graph pressure for the current agent-bus tool registry. "
                "This is not a runtime policy and not a proof of security."
            ),
        },
    }
    if out_dir is not None:
        write_artifacts(summary, edges, out_dir)
    return summary


def write_artifacts(
    summary: dict[str, object], edges: set[tuple[str, str]], out_dir: Path
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    edge_rows = [{"from": left, "to": right} for left, right in sorted(edges)]
    (out_dir / "undirected_edges.json").write_text(
        json.dumps(edge_rows, indent=2), encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools-json", type=Path, default=DEFAULT_TOOLS_JSON)
    parser.add_argument("--null-trials", type=int, default=100)
    parser.add_argument("--seed", type=int, default=31)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_probe(
        tools_json=args.tools_json,
        null_trials=args.null_trials,
        seed=args.seed,
        out_dir=args.out_dir,
    )
    print(json.dumps(summary["metrics"], indent=2, sort_keys=True))
    print(json.dumps(summary["decision_record"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
