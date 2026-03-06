"""HYDRA Branch Orchestrator.

Bridge the ChoiceScript branching engine into a CLI-friendly orchestration
surface with optional multi-model council voting.
"""

from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


GRAPH_NAMES = ("research_pipeline", "content_publisher", "training_funnel")


@dataclass(frozen=True)
class CouncilVote:
    provider: str
    path_id: str
    score: float
    reason: str


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_branching_symbols() -> Dict[str, Any]:
    """Load branching engine symbols with import fallback."""
    try:
        from workflows.n8n.choicescript_branching_engine import (  # type: ignore[import-not-found]
            BranchingEngine,
            ExploreStrategy,
            build_content_publishing_graph,
            build_research_pipeline_graph,
            build_training_funnel_graph,
        )
    except ImportError:
        module_path = _project_root() / "workflows" / "n8n" / "choicescript_branching_engine.py"
        spec = importlib.util.spec_from_file_location("choicescript_branching_engine", module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load branching engine at {module_path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[attr-defined]
        BranchingEngine = mod.BranchingEngine
        ExploreStrategy = mod.ExploreStrategy
        build_content_publishing_graph = mod.build_content_publishing_graph
        build_research_pipeline_graph = mod.build_research_pipeline_graph
        build_training_funnel_graph = mod.build_training_funnel_graph

    return {
        "BranchingEngine": BranchingEngine,
        "ExploreStrategy": ExploreStrategy,
        "build_research_pipeline_graph": build_research_pipeline_graph,
        "build_content_publishing_graph": build_content_publishing_graph,
        "build_training_funnel_graph": build_training_funnel_graph,
    }


def _graph_builders(topic: str) -> Dict[str, Callable[[], Any]]:
    symbols = _load_branching_symbols()
    return {
        "research_pipeline": lambda: symbols["build_research_pipeline_graph"](topic or "general research"),
        "content_publisher": symbols["build_content_publishing_graph"],
        "training_funnel": symbols["build_training_funnel_graph"],
    }


def list_graph_templates(topic: str = "example topic") -> List[Dict[str, Any]]:
    """Return graph template metadata for CLI list views."""
    templates: List[Dict[str, Any]] = []
    for graph_name, build in _graph_builders(topic).items():
        graph = build()
        templates.append(
            {
                "name": graph_name,
                "start": graph.start_label,
                "scene_count": len(graph.scenes),
                "strategies": list_strategies(),
            }
        )
    return templates


def list_strategies() -> List[str]:
    """List valid exploration strategy names."""
    symbols = _load_branching_symbols()
    return sorted(strategy.value for strategy in symbols["ExploreStrategy"])


def graph_choicescript(graph_name: str, topic: str = "") -> str:
    """Render a graph as ChoiceScript-style pseudocode."""
    builders = _graph_builders(topic)
    if graph_name not in builders:
        raise ValueError(f"Unknown graph: {graph_name}. Available: {sorted(builders)}")
    graph = builders[graph_name]()
    return graph.to_choicescript()


def _normalize_provider(raw: str) -> str:
    key = raw.strip().lower()
    aliases = {
        "anthropic": "claude",
        "claude": "claude",
        "openai": "gpt",
        "codex": "gpt",
        "gpt": "gpt",
        "gemini": "gemini",
        "xai": "grok",
        "grok": "grok",
        "hf": "hf",
        "huggingface": "hf",
        "local": "local",
    }
    return aliases.get(key, key)


def _provider_vote_score(provider: str, path: Dict[str, Any]) -> float:
    """Provider-specific heuristic score for a path."""
    base = float(path.get("score", 0.0))
    scenes = path.get("scenes", [])
    if not isinstance(scenes, list):
        scenes = []
    depth = len(scenes)
    joined = " ".join(str(scene) for scene in scenes).lower()
    terminal_bonus = 0.5 if path.get("terminal") else 0.0
    error_penalty = 1.5 if path.get("error") else 0.0
    research_bonus = 0.4 * sum(kw in joined for kw in ("arxiv", "research", "analyze"))
    governance_bonus = 0.4 * sum(kw in joined for kw in ("governance", "council", "review"))
    exploration_bonus = 0.3 * sum(kw in joined for kw in ("hybrid", "fan", "publish"))

    if provider == "claude":
        return base + governance_bonus + depth * 0.2 + terminal_bonus - error_penalty
    if provider == "gpt":
        return base + exploration_bonus + terminal_bonus - (depth * 0.05) - error_penalty
    if provider == "gemini":
        return base + research_bonus + depth * 0.15 + terminal_bonus - error_penalty
    if provider == "grok":
        return base + exploration_bonus + governance_bonus * 0.5 + terminal_bonus - error_penalty
    if provider == "hf":
        return base + research_bonus + (depth * 0.1) - error_penalty
    if provider == "local":
        return base + (depth * 0.1) + terminal_bonus - error_penalty
    return base + terminal_bonus - error_penalty


def _vote_reason(provider: str, path: Dict[str, Any]) -> str:
    scenes = path.get("scenes", [])
    if not isinstance(scenes, list):
        scenes = []
    joined = " ".join(str(scene) for scene in scenes).lower()
    if provider == "gemini" and ("arxiv" in joined or "research" in joined):
        return "research density"
    if provider == "claude" and ("governance" in joined or "council" in joined):
        return "governance coverage"
    if provider == "gpt" and path.get("terminal"):
        return "clear terminal path"
    if provider == "grok" and ("hybrid" in joined or "fan" in joined):
        return "novel hybrid branch"
    return "overall path score"


def _council_deliberate(
    paths: List[Dict[str, Any]],
    providers: List[str],
) -> Dict[str, Any]:
    if not paths:
        return {"winner_path_id": None, "votes": [], "scoreboard": []}

    unique_providers: List[str] = []
    for provider in providers:
        norm = _normalize_provider(provider)
        if norm and norm not in unique_providers:
            unique_providers.append(norm)

    if not unique_providers:
        unique_providers = ["claude", "gpt", "gemini"]

    scoreboard: Dict[str, Dict[str, Any]] = {
        str(path.get("id")): {"path_id": str(path.get("id")), "rank_points": 0.0, "score_sum": 0.0, "votes": 0}
        for path in paths
    }

    votes: List[CouncilVote] = []
    ranking_weight = len(paths)
    for provider in unique_providers:
        scored = sorted(
            ((_provider_vote_score(provider, path), path) for path in paths),
            key=lambda item: (item[0], float(item[1].get("score", 0.0)), len(item[1].get("scenes", []))),
            reverse=True,
        )
        for rank, (score, path) in enumerate(scored):
            path_id = str(path.get("id"))
            points = float(max(1, ranking_weight - rank))
            board = scoreboard[path_id]
            board["rank_points"] += points
            board["score_sum"] += score
            if rank == 0:
                board["votes"] += 1
                votes.append(
                    CouncilVote(
                        provider=provider,
                        path_id=path_id,
                        score=round(score, 3),
                        reason=_vote_reason(provider, path),
                    )
                )

    ordered_scoreboard = sorted(
        scoreboard.values(),
        key=lambda row: (row["rank_points"], row["votes"], row["score_sum"]),
        reverse=True,
    )
    winner = ordered_scoreboard[0]["path_id"] if ordered_scoreboard else None

    return {
        "winner_path_id": winner,
        "votes": [vote.__dict__ for vote in votes],
        "scoreboard": [
            {
                "path_id": row["path_id"],
                "rank_points": round(row["rank_points"], 3),
                "votes": int(row["votes"]),
                "score_sum": round(row["score_sum"], 3),
            }
            for row in ordered_scoreboard
        ],
    }


def _write_json(path: Path, payload: Dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)


def _write_text(path: Path, payload: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return str(path)


def run_branch_workflow(
    graph_name: str,
    topic: str = "",
    strategy: str = "all_paths",
    context: Optional[Dict[str, Any]] = None,
    max_paths: int = 20,
    max_depth: int = 50,
    providers: Optional[List[str]] = None,
    enable_council: bool = True,
    export_n8n_path: Optional[str] = None,
    export_choicescript_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a branch workflow template and return a CLI-ready payload."""
    symbols = _load_branching_symbols()
    builders = _graph_builders(topic)
    if graph_name not in builders:
        raise ValueError(f"Unknown graph: {graph_name}. Available: {sorted(builders)}")

    strategies = {s.value: s for s in symbols["ExploreStrategy"]}
    selected_strategy = strategies.get(strategy)
    if selected_strategy is None:
        raise ValueError(f"Unknown strategy: {strategy}. Available: {sorted(strategies)}")

    graph = builders[graph_name]()
    engine = symbols["BranchingEngine"](
        bridge_url="http://127.0.0.1:8001",
        max_depth=max(1, int(max_depth)),
        max_paths=max(1, int(max_paths)),
    )

    exec_context = dict(context or {})
    if topic and "query" not in exec_context:
        exec_context["query"] = topic

    result = engine.explore_sync(graph, context=exec_context, strategy=selected_strategy)
    all_paths: List[Dict[str, Any]] = []
    id_seen: Dict[str, int] = {}
    unique_by_identity: Dict[int, str] = {}
    for index, path in enumerate(result.paths):
        raw_id = str(path.path_id or f"path_{index}")
        id_seen[raw_id] = id_seen.get(raw_id, 0) + 1
        unique_id = raw_id if id_seen[raw_id] == 1 else f"{raw_id}-{id_seen[raw_id]}"
        unique_by_identity[id(path)] = unique_id
        all_paths.append(
            {
                "id": unique_id,
                "scenes": list(path.scenes_visited),
                "score": round(float(path.score), 3),
                "terminal": bool(path.terminal),
                "error": path.error,
            }
        )
    best_path = None
    if result.best_path is not None:
        best_path = {
            "id": unique_by_identity.get(id(result.best_path), str(result.best_path.path_id)),
            "scenes": list(result.best_path.scenes_visited),
            "score": round(float(result.best_path.score), 3),
            "terminal": bool(result.best_path.terminal),
            "error": result.best_path.error,
        }

    council = None
    if enable_council:
        council = _council_deliberate(all_paths, providers or [])

    exports: Dict[str, str] = {}
    if export_n8n_path:
        exports["n8n_workflow"] = _write_json(Path(export_n8n_path), graph.to_n8n_workflow())
    if export_choicescript_path:
        exports["choicescript"] = _write_text(Path(export_choicescript_path), graph.to_choicescript())

    return {
        "graph_name": graph_name,
        "strategy": selected_strategy.value,
        "coverage": round(float(result.coverage), 3),
        "total_scenes": int(result.total_scenes),
        "paths_explored": len(all_paths),
        "best_path": best_path,
        "all_paths": all_paths,
        "timestamp": result.timestamp,
        "council": council,
        "exports": exports,
    }
