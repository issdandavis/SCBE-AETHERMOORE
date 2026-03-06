"""
ChoiceScript Branching Engine for n8n Workflows
================================================

Maps ChoiceScript branching semantics (*choice, *goto, *if, *set)
to n8n workflow DAG execution, enabling multi-path workflow discovery.

Instead of a linear A->B->C pipeline, workflows become choose-your-own-adventure
graphs where each decision node can fork into parallel exploration paths.

Usage:
    from workflows.n8n.choicescript_branching_engine import BranchingEngine, SceneGraph

    # Define a branching workflow
    graph = SceneGraph("research_pipeline")
    graph.add_scene("start", prompt="Begin research on {topic}")
    graph.add_choice("start", [
        Choice("arxiv_path", condition="topic.domain == 'academic'"),
        Choice("web_path",   condition="topic.domain == 'industry'"),
        Choice("hybrid_path", condition="True"),  # fallback
    ])
    graph.add_scene("arxiv_path", action="scrape_arxiv", params={"max_results": 20})
    graph.add_scene("web_path",   action="scrape_web",   params={"depth": 2})
    graph.add_scene("hybrid_path", action="scrape_both",  params={})

    # Execute with multi-path exploration
    engine = BranchingEngine(bridge_url="http://localhost:8001")
    results = await engine.explore(graph, context={"topic": {"domain": "academic", "query": "chladni modes"}})

Bridge endpoint:
    POST /v1/workflow/branch — Execute a branching workflow scene graph
"""

from __future__ import annotations

import copy
import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
#  Core data model — ChoiceScript semantics mapped to workflow primitives
# ---------------------------------------------------------------------------

class NodeType(str, Enum):
    SCENE = "scene"           # A workflow step (like a *scene_list entry)
    CHOICE = "choice"         # A branching decision point (*choice)
    GOTO = "goto"             # Unconditional jump (*goto)
    GOSUB = "gosub"           # Subroutine call (*gosub / *return)
    FINISH = "finish"         # Terminal node (*finish / *ending)
    CHECKPOINT = "checkpoint" # Save state for backtracking


class ExploreStrategy(str, Enum):
    FIRST_MATCH = "first_match"   # Take first valid branch (like a player)
    ALL_PATHS = "all_paths"       # Fork and explore every valid branch in parallel
    SCORED = "scored"             # Evaluate all, pick highest-scoring path
    BREADTH_FIRST = "breadth_first"  # BFS through the graph
    MONTE_CARLO = "monte_carlo"   # Random path sampling for coverage estimation


@dataclass
class Choice:
    """A single option within a *choice block."""
    target: str                           # Scene label to goto
    label: str = ""                       # Display label
    condition: str = "True"               # Python expression evaluated against context
    weight: float = 1.0                   # Priority weight for scored strategy
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SceneNode:
    """A single scene in the workflow graph — maps to an n8n node."""
    label: str
    node_type: NodeType = NodeType.SCENE
    action: str = ""                      # n8n action: scrape_arxiv, llm_dispatch, governance_scan, etc.
    params: Dict[str, Any] = field(default_factory=dict)
    choices: List[Choice] = field(default_factory=list)
    goto_target: Optional[str] = None     # For GOTO nodes
    set_vars: Dict[str, str] = field(default_factory=dict)  # *set variable expressions
    prompt_template: str = ""             # Template for LLM-driven decisions
    on_enter: str = ""                    # Expression to eval on entering scene
    on_exit: str = ""                     # Expression to eval on leaving scene


@dataclass
class PathTrace:
    """Record of a single exploration path through the graph."""
    path_id: str
    scenes_visited: List[str] = field(default_factory=list)
    actions_taken: List[Dict[str, Any]] = field(default_factory=list)
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    terminal: bool = False
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class ExploreResult:
    """Aggregate result from multi-path exploration."""
    graph_name: str
    strategy: ExploreStrategy
    paths: List[PathTrace] = field(default_factory=list)
    best_path: Optional[PathTrace] = None
    coverage: float = 0.0                 # Fraction of scenes visited across all paths
    total_scenes: int = 0
    timestamp: str = ""


# ---------------------------------------------------------------------------
#  Scene Graph — the workflow blueprint
# ---------------------------------------------------------------------------

class SceneGraph:
    """Directed graph of scenes with ChoiceScript-style branching."""

    def __init__(self, name: str, start_label: str = "start"):
        self.name = name
        self.start_label = start_label
        self.scenes: Dict[str, SceneNode] = {}

    def add_scene(
        self,
        label: str,
        action: str = "",
        params: Optional[Dict[str, Any]] = None,
        prompt_template: str = "",
        set_vars: Optional[Dict[str, str]] = None,
        node_type: NodeType = NodeType.SCENE,
    ) -> SceneNode:
        node = SceneNode(
            label=label,
            node_type=node_type,
            action=action,
            params=params or {},
            prompt_template=prompt_template,
            set_vars=set_vars or {},
        )
        self.scenes[label] = node
        return node

    def add_choice(self, from_label: str, choices: List[Choice]):
        if from_label not in self.scenes:
            raise ValueError(f"Scene '{from_label}' not found")
        self.scenes[from_label].choices = choices
        self.scenes[from_label].node_type = NodeType.CHOICE

    def add_goto(self, from_label: str, target_label: str):
        if from_label not in self.scenes:
            raise ValueError(f"Scene '{from_label}' not found")
        self.scenes[from_label].goto_target = target_label
        self.scenes[from_label].node_type = NodeType.GOTO

    def add_finish(self, label: str, action: str = "", params: Optional[Dict[str, Any]] = None):
        self.add_scene(label, action=action, params=params, node_type=NodeType.FINISH)

    def scene_labels(self) -> Set[str]:
        return set(self.scenes.keys())

    def reachable_from(self, label: str) -> Set[str]:
        """BFS to find all reachable scenes from a starting label."""
        visited: Set[str] = set()
        queue = [label]
        while queue:
            current = queue.pop(0)
            if current in visited or current not in self.scenes:
                continue
            visited.add(current)
            node = self.scenes[current]
            for choice in node.choices:
                queue.append(choice.target)
            if node.goto_target:
                queue.append(node.goto_target)
        return visited

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "start": self.start_label,
            "scenes": {k: asdict(v) for k, v in self.scenes.items()},
        }

    def to_choicescript(self) -> str:
        """Export as ChoiceScript-flavored pseudocode for human readability."""
        lines: List[str] = [f"*title {self.name}", f"*scene_list"]
        for label in self.scenes:
            lines.append(f"  {label}")
        lines.append("")

        for label, node in self.scenes.items():
            lines.append(f"*label {label}")
            if node.action:
                lines.append(f"*comment action: {node.action} {json.dumps(node.params)}")
            if node.prompt_template:
                lines.append(node.prompt_template)
            for var_name, var_expr in node.set_vars.items():
                lines.append(f"*set {var_name} {var_expr}")

            if node.choices:
                lines.append("*choice")
                for choice in node.choices:
                    cond = f"*if ({choice.condition}) " if choice.condition != "True" else ""
                    lines.append(f"  #{cond}{choice.label or choice.target}")
                    lines.append(f"    *goto {choice.target}")
            elif node.goto_target:
                lines.append(f"*goto {node.goto_target}")
            elif node.node_type == NodeType.FINISH:
                lines.append("*finish")
            lines.append("")

        return "\n".join(lines)

    def to_n8n_workflow(self, workflow_name: Optional[str] = None) -> Dict[str, Any]:
        """Export the scene graph as an n8n-compatible workflow JSON."""
        nodes: List[Dict[str, Any]] = []
        connections: Dict[str, Any] = {}
        x_offset, y_offset = 0, 0

        # Entry webhook
        nodes.append({
            "parameters": {
                "httpMethod": "POST",
                "path": f"branch-{self.name}",
                "responseMode": "responseNode",
            },
            "id": f"webhook_{self.name}",
            "name": "Webhook: Branch Entry",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2,
            "position": [x_offset, y_offset],
        })

        scene_positions: Dict[str, Tuple[int, int]] = {}
        for idx, (label, node) in enumerate(self.scenes.items()):
            sx = x_offset + 400 + (idx % 4) * 400
            sy = y_offset + (idx // 4) * 300
            scene_positions[label] = (sx, sy)

            if node.action:
                # Action nodes become HTTP Request nodes calling bridge
                nodes.append({
                    "parameters": {
                        "method": "POST",
                        "url": "http://localhost:8001/v1/workflow/branch/action",
                        "sendHeaders": True,
                        "headerParameters": {
                            "parameters": [
                                {"name": "X-API-Key", "value": "={{ $env.SCBE_API_KEY }}"},
                                {"name": "Content-Type", "value": "application/json"},
                            ]
                        },
                        "sendBody": True,
                        "specifyBody": "json",
                        "jsonBody": json.dumps({
                            "scene": label,
                            "action": node.action,
                            "params": node.params,
                        }),
                    },
                    "id": f"scene_{label}",
                    "name": f"Scene: {label}",
                    "type": "n8n-nodes-base.httpRequest",
                    "typeVersion": 4.2,
                    "position": [sx, sy],
                })
            elif node.choices:
                # Choice nodes become Switch/If nodes
                nodes.append({
                    "parameters": {
                        "mode": "expression",
                        "output": "={{ $json.branch_choice }}",
                    },
                    "id": f"choice_{label}",
                    "name": f"Choice: {label}",
                    "type": "n8n-nodes-base.switch",
                    "typeVersion": 3,
                    "position": [sx, sy],
                })
            else:
                # Pass-through or finish
                nodes.append({
                    "parameters": {},
                    "id": f"node_{label}",
                    "name": f"Node: {label}",
                    "type": "n8n-nodes-base.noOp",
                    "typeVersion": 1,
                    "position": [sx, sy],
                })

            # Build connections
            if node.choices:
                conn_outputs: Dict[str, Any] = {}
                for ci, choice in enumerate(node.choices):
                    target_id = f"scene_{choice.target}" if self.scenes.get(choice.target, SceneNode(label="")).action else f"node_{choice.target}"
                    conn_outputs[f"output_{ci}"] = [{"node": target_id, "type": "main", "index": 0}]
                connections[f"choice_{label}"] = {"main": list(conn_outputs.values())}
            elif node.goto_target and node.goto_target in self.scenes:
                target_node = self.scenes[node.goto_target]
                target_id = f"scene_{node.goto_target}" if target_node.action else f"node_{node.goto_target}"
                node_id = f"scene_{label}" if node.action else f"node_{label}"
                connections[node_id] = {"main": [[{"node": target_id, "type": "main", "index": 0}]]}

        # Response node
        nodes.append({
            "parameters": {"respondWith": "json", "responseBody": "={{ $json }}"},
            "id": f"respond_{self.name}",
            "name": "Respond",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1.1,
            "position": [x_offset + 2000, y_offset],
        })

        return {
            "name": workflow_name or f"SCBE Branch: {self.name}",
            "nodes": nodes,
            "connections": connections,
            "active": False,
            "settings": {"executionOrder": "v1"},
            "tags": [{"name": "scbe"}, {"name": "branching"}],
        }


# ---------------------------------------------------------------------------
#  Context evaluator — safe expression evaluation for *if / *set
# ---------------------------------------------------------------------------

class SafeContextEval:
    """Evaluate ChoiceScript conditions against a workflow context dict.

    Only allows attribute access, comparisons, and basic math — no imports,
    no builtins, no exec/eval abuse.
    """

    ALLOWED_BUILTINS = {"len", "int", "float", "str", "bool", "abs", "min", "max", "sum", "any", "all"}

    @classmethod
    def evaluate(cls, expression: str, context: Dict[str, Any]) -> Any:
        if not expression or expression.strip() == "True":
            return True
        if expression.strip() == "False":
            return False

        # Flatten nested dict access: "topic.domain" -> context["topic"]["domain"]
        safe_globals: Dict[str, Any] = {"__builtins__": {k: __builtins__[k] for k in cls.ALLOWED_BUILTINS if k in __builtins__}} if isinstance(__builtins__, dict) else {"__builtins__": {}}
        # Add allowed builtins
        import builtins as _b
        safe_globals["__builtins__"] = {k: getattr(_b, k) for k in cls.ALLOWED_BUILTINS if hasattr(_b, k)}

        # Create a dotdict wrapper so "topic.domain" works
        class DotDict(dict):
            def __getattr__(self, key):
                val = self.get(key)
                if isinstance(val, dict):
                    return DotDict(val)
                return val

        safe_locals = {k: DotDict(v) if isinstance(v, dict) else v for k, v in context.items()}

        try:
            return eval(expression, safe_globals, safe_locals)  # noqa: S307
        except Exception:
            return False


# ---------------------------------------------------------------------------
#  Action registry — maps scene actions to callables
# ---------------------------------------------------------------------------

# Built-in actions that map to n8n bridge endpoints
_BUILTIN_ACTIONS: Dict[str, str] = {
    "scrape_arxiv": "/v1/workflow/branch/action",
    "scrape_web": "/v1/workflow/branch/action",
    "scrape_both": "/v1/workflow/branch/action",
    "llm_dispatch": "/v1/llm/dispatch",
    "governance_scan": "/v1/governance/scan",
    "tongue_encode": "/v1/tongue/encode",
    "council_deliberate": "/v1/council/deliberate",
    "training_ingest": "/v1/training/ingest",
    "browser_navigate": "/v1/integrations/n8n/browse",
    "noop": "",
}


class ActionRegistry:
    """Registry of callable actions for scene execution."""

    def __init__(self):
        self._actions: Dict[str, Callable] = {}

    def register(self, name: str, handler: Callable):
        self._actions[name] = handler

    def execute(self, name: str, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        if name in self._actions:
            return self._actions[name](params=params, context=context)
        # Default: return params as-is (dry run / stub)
        return {
            "action": name,
            "params": params,
            "status": "stub",
            "message": f"Action '{name}' executed in stub mode",
        }


# ---------------------------------------------------------------------------
#  Branching Engine — the multi-path explorer
# ---------------------------------------------------------------------------

class BranchingEngine:
    """Execute a SceneGraph using ChoiceScript branching with multi-path exploration."""

    def __init__(
        self,
        bridge_url: str = "http://localhost:8001",
        max_depth: int = 50,
        max_paths: int = 20,
    ):
        self.bridge_url = bridge_url.rstrip("/")
        self.max_depth = max_depth
        self.max_paths = max_paths
        self.registry = ActionRegistry()
        self._register_defaults()

    def _register_defaults(self):
        """Register built-in stub actions for local execution."""

        def _stub_scrape(params: Dict, context: Dict) -> Dict:
            query = params.get("query") or context.get("query", "")
            source = params.get("source", "arxiv")
            max_results = params.get("max_results", 10)
            return {
                "action": f"scrape_{source}",
                "query": query,
                "max_results": max_results,
                "chunks": max_results,  # simulated
                "status": "ok",
            }

        def _stub_llm(params: Dict, context: Dict) -> Dict:
            return {
                "action": "llm_dispatch",
                "provider": params.get("provider", "claude"),
                "response": f"[LLM response for: {params.get('prompt', context.get('query', ''))}]",
                "status": "ok",
            }

        def _stub_governance(params: Dict, context: Dict) -> Dict:
            content = params.get("content", "")
            return {
                "action": "governance_scan",
                "verdict": "ALLOW",
                "risk_score": 0.1,
                "content_length": len(content),
                "status": "ok",
            }

        self.registry.register("scrape_arxiv", _stub_scrape)
        self.registry.register("scrape_web", _stub_scrape)
        self.registry.register("scrape_both", _stub_scrape)
        self.registry.register("llm_dispatch", _stub_llm)
        self.registry.register("governance_scan", _stub_governance)
        self.registry.register("noop", lambda params, context: {"status": "ok"})

    def _execute_scene(
        self,
        node: SceneNode,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a single scene's action and return the result."""
        # Apply *set variables
        for var_name, var_expr in node.set_vars.items():
            context[var_name] = SafeContextEval.evaluate(var_expr, context)

        # Execute on_enter
        if node.on_enter:
            SafeContextEval.evaluate(node.on_enter, context)

        # Execute action
        result: Dict[str, Any] = {}
        if node.action:
            merged_params = {**node.params}
            # Template substitution in params
            for k, v in merged_params.items():
                if isinstance(v, str) and "{" in v:
                    try:
                        merged_params[k] = v.format(**context)
                    except (KeyError, IndexError):
                        pass
            result = self.registry.execute(node.action, merged_params, context)

        # Store result in context
        context[f"_result_{node.label}"] = result
        context["_last_result"] = result

        return result

    def _evaluate_choices(
        self,
        choices: List[Choice],
        context: Dict[str, Any],
        strategy: ExploreStrategy,
    ) -> List[Choice]:
        """Evaluate which choices are valid given current context."""
        valid: List[Choice] = []
        for choice in choices:
            if SafeContextEval.evaluate(choice.condition, context):
                valid.append(choice)

        if strategy == ExploreStrategy.FIRST_MATCH:
            return valid[:1]
        elif strategy == ExploreStrategy.SCORED:
            return sorted(valid, key=lambda c: c.weight, reverse=True)
        elif strategy == ExploreStrategy.MONTE_CARLO:
            import random
            if valid:
                weights = [c.weight for c in valid]
                chosen = random.choices(valid, weights=weights, k=1)
                return chosen
            return []
        else:  # ALL_PATHS, BREADTH_FIRST
            return valid

    def explore_sync(
        self,
        graph: SceneGraph,
        context: Optional[Dict[str, Any]] = None,
        strategy: ExploreStrategy = ExploreStrategy.ALL_PATHS,
    ) -> ExploreResult:
        """Synchronous multi-path exploration of a scene graph."""
        t0 = time.time()
        context = dict(context or {})
        all_visited: Set[str] = set()
        paths: List[PathTrace] = []

        # BFS queue: (current_label, context_copy, path_trace)
        queue: List[Tuple[str, Dict[str, Any], PathTrace]] = []
        initial_trace = PathTrace(
            path_id=hashlib.md5(f"{graph.name}-0".encode()).hexdigest()[:8],
        )
        queue.append((graph.start_label, copy.deepcopy(context), initial_trace))

        while queue and len(paths) < self.max_paths:
            current_label, ctx, trace = queue.pop(0)

            # Depth guard
            if len(trace.scenes_visited) >= self.max_depth:
                trace.terminal = True
                trace.error = "max_depth_reached"
                paths.append(trace)
                continue

            # Cycle detection
            if current_label in trace.scenes_visited:
                trace.terminal = True
                trace.error = f"cycle_detected_at_{current_label}"
                paths.append(trace)
                continue

            node = graph.scenes.get(current_label)
            if not node:
                trace.terminal = True
                trace.error = f"scene_not_found_{current_label}"
                paths.append(trace)
                continue

            trace.scenes_visited.append(current_label)
            all_visited.add(current_label)

            # Execute scene action
            try:
                result = self._execute_scene(node, ctx)
                trace.actions_taken.append({
                    "scene": current_label,
                    "action": node.action,
                    "result": result,
                })
                # Accumulate score from results
                trace.score += result.get("score", 0.0)
                if result.get("chunks"):
                    trace.score += float(result["chunks"]) * 0.1
            except Exception as exc:
                trace.error = f"action_error_{current_label}: {exc}"
                trace.terminal = True
                paths.append(trace)
                continue

            # Handle node type
            if node.node_type == NodeType.FINISH:
                trace.terminal = True
                trace.context_snapshot = {k: v for k, v in ctx.items() if not k.startswith("_")}
                trace.duration_ms = (time.time() - t0) * 1000
                paths.append(trace)
                continue

            if node.node_type == NodeType.GOTO and node.goto_target:
                queue.append((node.goto_target, ctx, trace))
                continue

            if node.choices:
                valid_choices = self._evaluate_choices(node.choices, ctx, strategy)
                if not valid_choices:
                    trace.terminal = True
                    trace.error = "no_valid_choices"
                    trace.context_snapshot = {k: v for k, v in ctx.items() if not k.startswith("_")}
                    paths.append(trace)
                    continue

                if strategy == ExploreStrategy.FIRST_MATCH or len(valid_choices) == 1:
                    # Single path — continue on same trace
                    queue.append((valid_choices[0].target, ctx, trace))
                else:
                    # Fork — create new traces for each branch
                    for ci, choice in enumerate(valid_choices):
                        forked_trace = PathTrace(
                            path_id=hashlib.md5(f"{graph.name}-{len(paths)}-{ci}".encode()).hexdigest()[:8],
                            scenes_visited=list(trace.scenes_visited),
                            actions_taken=list(trace.actions_taken),
                            score=trace.score + choice.weight,
                        )
                        queue.append((choice.target, copy.deepcopy(ctx), forked_trace))
            else:
                # No choices, no goto — terminal
                trace.terminal = True
                trace.context_snapshot = {k: v for k, v in ctx.items() if not k.startswith("_")}
                trace.duration_ms = (time.time() - t0) * 1000
                paths.append(trace)

        total_scenes = len(graph.scenes)
        coverage = len(all_visited) / total_scenes if total_scenes > 0 else 0.0
        best = max(paths, key=lambda p: p.score) if paths else None

        return ExploreResult(
            graph_name=graph.name,
            strategy=strategy,
            paths=paths,
            best_path=best,
            coverage=coverage,
            total_scenes=total_scenes,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )


# ---------------------------------------------------------------------------
#  Pre-built scene graphs — reusable workflow templates
# ---------------------------------------------------------------------------

def build_research_pipeline_graph(topic: str = "chladni modes") -> SceneGraph:
    """Multi-path research pipeline: arxiv vs web vs hybrid, with governance gates."""
    g = SceneGraph("research_pipeline")

    # Entry: classify the topic
    g.add_scene("start", action="noop", set_vars={"query": f"'{topic}'"})
    g.add_choice("start", [
        Choice("arxiv_deep", label="Deep academic search", condition="True", weight=2.0),
        Choice("web_scan", label="Web intelligence scan", condition="True", weight=1.5),
        Choice("hybrid_fan", label="Hybrid fan-out", condition="True", weight=3.0),
    ])

    # ArXiv deep path
    g.add_scene("arxiv_deep", action="scrape_arxiv", params={"source": "arxiv", "max_results": 40})
    g.add_choice("arxiv_deep", [
        Choice("arxiv_analyze", label="Analyze results", condition="_last_result.get('chunks', 0) > 0"),
        Choice("fallback_web", label="No results, try web", condition="_last_result.get('chunks', 0) == 0"),
    ])
    g.add_scene("arxiv_analyze", action="llm_dispatch", params={"provider": "claude", "prompt": "Analyze arxiv results for {query}"})
    g.add_goto("arxiv_analyze", "governance_gate")

    # Web scan path
    g.add_scene("web_scan", action="scrape_web", params={"source": "web", "depth": 2})
    g.add_goto("web_scan", "governance_gate")

    # Hybrid fan-out: hit both sources
    g.add_scene("hybrid_fan", action="scrape_both", params={"source": "both", "max_results": 20})
    g.add_choice("hybrid_fan", [
        Choice("council_review", label="Send to AI council", condition="True", weight=2.0),
        Choice("governance_gate", label="Direct to governance", condition="True", weight=1.0),
    ])

    # Fallback
    g.add_scene("fallback_web", action="scrape_web", params={"source": "web", "depth": 1})
    g.add_goto("fallback_web", "governance_gate")

    # AI Council review
    g.add_scene("council_review", action="council_deliberate", params={
        "providers": ["anthropic", "openai"],
        "strategy": "debate",
    })
    g.add_goto("council_review", "governance_gate")

    # Governance gate — all paths converge here
    g.add_scene("governance_gate", action="governance_scan", params={"content": "aggregated results"})
    g.add_choice("governance_gate", [
        Choice("publish", label="Approved — publish", condition="_last_result.get('verdict') == 'ALLOW'"),
        Choice("quarantine", label="Quarantined", condition="_last_result.get('verdict') != 'ALLOW'"),
    ])

    # Terminal nodes
    g.add_finish("publish", action="noop", params={"status": "published"})
    g.add_finish("quarantine", action="noop", params={"status": "quarantined"})

    return g


def build_content_publishing_graph() -> SceneGraph:
    """Multi-platform content publishing with branching per platform."""
    g = SceneGraph("content_publisher")

    g.add_scene("start", action="noop")
    g.add_choice("start", [
        Choice("twitter_path", label="Twitter/X", condition="True", weight=2.0),
        Choice("linkedin_path", label="LinkedIn", condition="True", weight=1.5),
        Choice("github_path", label="GitHub Discussion", condition="True", weight=1.0),
        Choice("medium_path", label="Medium article", condition="True", weight=1.0),
    ])

    for platform in ["twitter", "linkedin", "github", "medium"]:
        g.add_scene(f"{platform}_path", action="tongue_encode", params={"tongue": "KO"})
        g.add_scene(f"{platform}_gov", action="governance_scan", params={"platform": platform})
        g.add_goto(f"{platform}_path", f"{platform}_gov")
        g.add_choice(f"{platform}_gov", [
            Choice(f"{platform}_post", condition="_last_result.get('verdict') == 'ALLOW'"),
            Choice(f"{platform}_blocked", condition="_last_result.get('verdict') != 'ALLOW'"),
        ])
        g.add_finish(f"{platform}_post", action="noop", params={"platform": platform, "status": "posted"})
        g.add_finish(f"{platform}_blocked", action="noop", params={"platform": platform, "status": "blocked"})

    return g


def build_training_funnel_graph() -> SceneGraph:
    """Multi-source training data collection with quality branching."""
    g = SceneGraph("training_funnel")

    g.add_scene("start", action="noop")
    g.add_choice("start", [
        Choice("arxiv_ingest", label="ArXiv papers", condition="True", weight=2.0),
        Choice("notion_ingest", label="Notion pages", condition="True", weight=1.5),
        Choice("game_ingest", label="Game sessions", condition="True", weight=1.0),
    ])

    # ArXiv branch
    g.add_scene("arxiv_ingest", action="scrape_arxiv", params={"max_results": 50})
    g.add_goto("arxiv_ingest", "quality_gate")

    # Notion branch
    g.add_scene("notion_ingest", action="scrape_web", params={"source": "notion"})
    g.add_goto("notion_ingest", "quality_gate")

    # Game session branch
    g.add_scene("game_ingest", action="training_ingest", params={"event_type": "game_session"})
    g.add_goto("game_ingest", "quality_gate")

    # Quality gate
    g.add_scene("quality_gate", action="governance_scan", params={})
    g.add_choice("quality_gate", [
        Choice("merge_and_push", condition="_last_result.get('verdict') == 'ALLOW'"),
        Choice("reject", condition="_last_result.get('verdict') != 'ALLOW'"),
    ])

    g.add_finish("merge_and_push", action="noop", params={"status": "merged"})
    g.add_finish("reject", action="noop", params={"status": "rejected"})

    return g


# ---------------------------------------------------------------------------
#  CLI / test harness
# ---------------------------------------------------------------------------

def _run_demo():
    """Run a demo exploration of the research pipeline graph."""
    graph = build_research_pipeline_graph("signed chladni mode addressing")
    engine = BranchingEngine()

    print(f"=== ChoiceScript Branching Engine Demo ===")
    print(f"Graph: {graph.name} ({len(graph.scenes)} scenes)")
    print()

    # Show ChoiceScript pseudocode
    print("--- ChoiceScript Export ---")
    print(graph.to_choicescript())
    print()

    # Explore all paths
    for strategy in [ExploreStrategy.ALL_PATHS, ExploreStrategy.FIRST_MATCH, ExploreStrategy.SCORED]:
        result = engine.explore_sync(graph, context={"query": "signed chladni modes"}, strategy=strategy)
        print(f"--- Strategy: {strategy.value} ---")
        print(f"  Paths found: {len(result.paths)}")
        print(f"  Coverage: {result.coverage:.0%} ({int(result.coverage * result.total_scenes)}/{result.total_scenes} scenes)")
        if result.best_path:
            print(f"  Best path: {' -> '.join(result.best_path.scenes_visited)} (score: {result.best_path.score:.1f})")
        for path in result.paths:
            status = "OK" if not path.error else path.error
            print(f"    [{path.path_id}] {' -> '.join(path.scenes_visited)} | score={path.score:.1f} | {status}")
        print()

    # Export n8n workflow
    workflow = graph.to_n8n_workflow()
    out_path = Path(__file__).parent / "scbe_branching_research.workflow.json"
    with open(out_path, "w") as f:
        json.dump(workflow, f, indent=2)
    print(f"Exported n8n workflow: {out_path}")


if __name__ == "__main__":
    _run_demo()
