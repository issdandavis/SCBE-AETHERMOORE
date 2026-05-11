#!/usr/bin/env python3
"""Headless SCBE multi-swarm coding router.

This is the local "many hands, one project" layer:

- split a coding goal into bounded lanes
- route multiple free/local agent surfaces and local Ollama models
- keep every model inside an allowed path scope
- write proposals and an integration plan as artifacts
- do not mutate the repo

The mutation boundary deliberately stays outside this script. If a proposal
looks good, feed its unified diff through ``scripts/agents/safe_apply.py``.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import textwrap
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "scbe_swarm_router"
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
DEFAULT_MODELS = ("openclaw:latest", "qwen2.5-coder:1.5b", "scbe-geoseal-coder:q8")
KNOWLEDGE_GRAPH_PATH = REPO_ROOT / "docs" / "research" / "SCBE_BUS_TASK_KNOWLEDGE_GRAPH_2026-05-10.json"
CODING_SYSTEM_REGISTRY_PATH = REPO_ROOT / "docs" / "research" / "SCBE_CODING_SYSTEM_REGISTRY_2026-05-10.json"
PAZAAK_BOARD_PATH = Path(__file__).with_name("agentic_pazaak_board.py")


@dataclass(frozen=True)
class AgentProfile:
    alias: str
    display_name: str
    launch_command: str
    swarm_surface: str
    geometry_role: str
    geometry_anchor: tuple[float, float, float]
    model_candidates: tuple[str, ...]
    lane_bias: str
    cloud_model_candidates: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResolvedAgent:
    profile: AgentProfile
    model: str | None
    status: str
    reason: str
    execution_surface: str
    cost_tier: str


@dataclass(frozen=True)
class WorkLane:
    lane_id: str
    lane_tier: str
    agent_alias: str
    agent_name: str
    model: str
    execution_surface: str
    cost_tier: str
    geometry_role: str
    geometry_anchor: tuple[float, float, float]
    goal: str
    allowed_paths: tuple[str, ...]
    blocked_paths: tuple[str, ...]
    done_criteria: tuple[str, ...]
    verify_command: str
    helper_contract: str
    cycle_policy: str
    trust_policy: str
    output_contract: str


def _load_pazaak_board_module() -> Any:
    spec = importlib.util.spec_from_file_location("_agentic_pazaak_board_runtime", PAZAAK_BOARD_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load Pazaak planner from {PAZAAK_BOARD_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(spec.name, module)
    spec.loader.exec_module(module)
    return module


AGENT_PROFILES: dict[str, AgentProfile] = {
    "claude": AgentProfile(
        alias="claude",
        display_name="Claude Code",
        launch_command="ollama launch claude",
        swarm_surface="ollama_launch",
        geometry_role="north-star reviewer / subagent decomposer",
        geometry_anchor=(0.0, 1.0, 0.0),
        model_candidates=("claude:latest",),
        lane_bias="architecture",
        cloud_model_candidates=("glm-4.7:cloud", "gpt-oss:120b-cloud"),
    ),
    "openclaw": AgentProfile(
        alias="openclaw",
        display_name="OpenClaw",
        launch_command="ollama launch openclaw",
        swarm_surface="ollama_launch",
        geometry_role="router/bootstrap surface / local repo-bound operator",
        geometry_anchor=(1.0, 0.0, 0.0),
        model_candidates=("openclaw:latest", "openclaw"),
        lane_bias="implementation",
        cloud_model_candidates=("qwen3-coder:480b-cloud", "glm-4.7:cloud"),
    ),
    "hermes": AgentProfile(
        alias="hermes",
        display_name="Hermes Agent",
        launch_command="ollama launch hermes",
        swarm_surface="ollama_launch",
        geometry_role="self-improvement critic / repair loop",
        geometry_anchor=(0.0, -1.0, 0.0),
        model_candidates=("hermes:latest", "nous-hermes:latest", "qwen2.5:3b-instruct"),
        lane_bias="verification",
        cloud_model_candidates=("gpt-oss:120b-cloud", "glm-4.7:cloud"),
    ),
    "opencode": AgentProfile(
        alias="opencode",
        display_name="OpenCode",
        launch_command="ollama launch opencode",
        swarm_surface="ollama_launch",
        geometry_role="open-source patch proposer",
        geometry_anchor=(-1.0, 0.0, 0.0),
        model_candidates=("opencode:latest", "qwen2.5-coder:1.5b"),
        lane_bias="implementation",
        cloud_model_candidates=("qwen3-coder:480b-cloud", "glm-4.7:cloud"),
    ),
    "codex": AgentProfile(
        alias="codex",
        display_name="Codex",
        launch_command="ollama launch codex",
        swarm_surface="ollama_launch",
        geometry_role="test-first integrator / safe apply gate",
        geometry_anchor=(0.0, 0.0, 1.0),
        model_candidates=("codex:latest", "qwen2.5-coder:1.5b"),
        lane_bias="verification",
        cloud_model_candidates=("qwen3-coder:480b-cloud", "glm-4.7:cloud"),
    ),
    "copilot": AgentProfile(
        alias="copilot",
        display_name="Copilot CLI",
        launch_command="ollama launch copilot",
        swarm_surface="ollama_launch",
        geometry_role="developer ergonomics / familiar CLI assistant",
        geometry_anchor=(0.707, 0.707, 0.0),
        model_candidates=("copilot:latest", "qwen2.5-coder:1.5b"),
        lane_bias="product",
        cloud_model_candidates=("glm-4.7:cloud", "minimax-m2.1:cloud"),
    ),
    "droid": AgentProfile(
        alias="droid",
        display_name="Droid",
        launch_command="ollama launch droid",
        swarm_surface="ollama_launch",
        geometry_role="terminal and IDE execution bridge",
        geometry_anchor=(-0.707, 0.707, 0.0),
        model_candidates=("droid:latest", "qwen2.5-coder:1.5b"),
        lane_bias="implementation",
        cloud_model_candidates=("qwen3-coder:480b-cloud", "glm-4.7:cloud"),
    ),
    "pi": AgentProfile(
        alias="pi",
        display_name="Pi",
        launch_command="ollama launch pi",
        swarm_surface="ollama_launch",
        geometry_role="minimal plugin kernel / small-tool adapter",
        geometry_anchor=(0.0, 0.707, 0.707),
        model_candidates=("pi:latest", "gemma3:1b"),
        lane_bias="architecture",
        cloud_model_candidates=("gpt-oss:120b-cloud",),
    ),
    "aider": AgentProfile(
        alias="aider",
        display_name="Aider",
        launch_command="aider",
        swarm_surface="external_cli",
        geometry_role="git-aware pair programmer / patch proposer",
        geometry_anchor=(-0.5, -0.5, 0.707),
        model_candidates=("aider:latest", "qwen2.5-coder:1.5b"),
        lane_bias="implementation",
        cloud_model_candidates=("qwen3-coder:480b-cloud", "glm-4.7:cloud"),
    ),
    "openhands": AgentProfile(
        alias="openhands",
        display_name="OpenHands",
        launch_command="openhands",
        swarm_surface="external_cli",
        geometry_role="sandboxed software-engineering agent",
        geometry_anchor=(0.5, -0.5, 0.707),
        model_candidates=("openhands:latest", "qwen2.5-coder:1.5b"),
        lane_bias="verification",
        cloud_model_candidates=("qwen3-coder:480b-cloud", "glm-4.7:cloud"),
    ),
    "goose": AgentProfile(
        alias="goose",
        display_name="Goose",
        launch_command="goose",
        swarm_surface="external_cli",
        geometry_role="desktop automation and tool-use agent",
        geometry_anchor=(-0.5, 0.5, -0.707),
        model_candidates=("goose:latest", "qwen2.5:3b-instruct"),
        lane_bias="product",
        cloud_model_candidates=("glm-4.7:cloud", "gpt-oss:120b-cloud"),
    ),
    "cline": AgentProfile(
        alias="cline",
        display_name="Cline",
        launch_command="cline",
        swarm_surface="external_cli",
        geometry_role="IDE-assisted coding lane",
        geometry_anchor=(0.5, 0.5, -0.707),
        model_candidates=("cline:latest", "qwen2.5-coder:1.5b"),
        lane_bias="implementation",
        cloud_model_candidates=("qwen3-coder:480b-cloud", "glm-4.7:cloud"),
    ),
    "continue": AgentProfile(
        alias="continue",
        display_name="Continue",
        launch_command="continue",
        swarm_surface="external_cli",
        geometry_role="IDE autocomplete and repo context lane",
        geometry_anchor=(0.0, -0.707, -0.707),
        model_candidates=("continue:latest", "qwen2.5-coder:1.5b"),
        lane_bias="architecture",
        cloud_model_candidates=("qwen3-coder:480b-cloud", "glm-4.7:cloud"),
    ),
}

RAW_MODEL_PROFILE = AgentProfile(
    alias="model",
    display_name="Raw Ollama Model",
    launch_command="ollama run <model>",
    swarm_surface="ollama_model",
    geometry_role="unprofiled model point",
    geometry_anchor=(0.0, 0.0, 0.0),
    model_candidates=(),
    lane_bias="implementation",
)


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def make_run_dir(output_root: Path) -> Path:
    base = output_root / _utc_stamp()
    try:
        base.mkdir(parents=True, exist_ok=False)
        return base
    except FileExistsError:
        pass
    for idx in range(1, 1000):
        candidate = output_root / f"{base.name}-{idx:03d}"
        try:
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
        except FileExistsError:
            continue
    raise RuntimeError(f"could not allocate unique run directory under {output_root}")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def load_task_graph() -> dict[str, Any]:
    if not KNOWLEDGE_GRAPH_PATH.exists():
        return {}
    try:
        return json.loads(KNOWLEDGE_GRAPH_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def load_coding_system_registry() -> dict[str, Any]:
    if not CODING_SYSTEM_REGISTRY_PATH.exists():
        return {}
    try:
        return json.loads(CODING_SYSTEM_REGISTRY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def select_coding_systems(
    task: str, output_contract: str, registry: dict[str, Any], limit: int = 6
) -> list[dict[str, Any]]:
    systems = registry.get("systems") or []
    if not systems:
        return []
    lowered = task.lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    contract_bias = {
        "answer": {"orchestration_surface", "concept_surface", "public_adapter_surface"},
        "evidence": {"atomic_surface", "transport_surface", "grading_surface", "public_adapter_surface"},
        "patch-proposal": {"swarm_surface", "geometry_surface", "packet_surface", "compiler_surface"},
    }
    for system in systems:
        score = 0
        haystack = " ".join(
            [
                str(system.get("system_id", "")),
                str(system.get("name", "")),
                str(system.get("purpose", "")),
                " ".join(system.get("best_for") or []),
                str(system.get("benchmark_role", "")),
            ]
        ).lower()
        for word in re.findall(r"[a-zA-Z][a-zA-Z0-9_+-]{2,}", lowered):
            if word in haystack:
                score += 2
        if system.get("benchmark_role") in contract_bias.get(output_contract, set()):
            score += 3
        if "cross" in lowered and "cross" in haystack:
            score += 4
        if "document" in lowered and "docs" in " ".join(system.get("best_for") or []):
            score += 2
        if "precision" in lowered and "precision" in haystack:
            score += 4
        if "stisa" in lowered and system.get("system_id") == "stisa_atomic_tokenizer":
            score += 8
        if "ss1" in lowered and system.get("system_id") == "ss1_sacred_tongue_transport":
            score += 8
        if score:
            scored.append((score, system))
    if not scored:
        preferred = {
            "swarm_router",
            "stisa_atomic_tokenizer",
            "ss1_sacred_tongue_transport",
            "functional_coding_agent_benchmark",
        }
        return [system for system in systems if system.get("system_id") in preferred][:limit]
    return [system for _, system in sorted(scored, key=lambda item: (-item[0], item[1].get("system_id", "")))[:limit]]


def format_coding_system_hints(task: str, output_contract: str) -> str:
    registry = load_coding_system_registry()
    selected = select_coding_systems(task, output_contract, registry)
    if not selected:
        return "Coding system registry: unavailable"
    lines = ["Coding system registry: available"]
    for system in selected:
        commands = "; ".join((system.get("commands") or [])[:2])
        outputs = ", ".join((system.get("expected_outputs") or [])[:4])
        lines.append(
            "- {system_id} [{role}]: {purpose} | outputs: {outputs} | commands: {commands}".format(
                system_id=system.get("system_id", "unknown"),
                role=system.get("benchmark_role", "unknown"),
                purpose=system.get("purpose", ""),
                outputs=outputs,
                commands=commands,
            )
        )
    return "\n".join(lines)


def select_task_graph_node(task: str, output_contract: str, graph: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    task_types = graph.get("task_types") or {}
    lowered = task.lower()
    for name, node in task_types.items():
        aliases = [str(alias).lower() for alias in node.get("aliases", [])]
        if any(alias in lowered for alias in aliases):
            return name, node
    for name, node in task_types.items():
        if node.get("operation_frame") == output_contract:
            return name, node
    return "unknown", {}


def format_task_graph_hint(task: str, output_contract: str) -> str:
    graph = load_task_graph()
    if not graph:
        return "Task graph: unavailable"
    node_name, node = select_task_graph_node(task, output_contract, graph)
    global_expectation = graph.get("global_expectation", {})
    response_format = node.get("response_format", [])
    source_clues = node.get("source_clues", [])
    do_not = global_expectation.get("do_not", [])
    if output_contract == "patch-proposal":
        return "\n".join(
            [
                f"Task graph node: {node_name}",
                "Patch lane reminder: use existing file hints and existing symbols only.",
                "Expected response shape: " + " | ".join(response_format),
            ]
        )
    return "\n".join(
        [
            f"Task graph node: {node_name}",
            f"Quality bar: {global_expectation.get('quality_bar', '')}",
            f"Completion rule: {node.get('completion') or global_expectation.get('completion_rule', '')}",
            "Source clues: " + ", ".join(source_clues),
            "Expected response shape: " + " | ".join(response_format),
            "Avoid: " + " | ".join(do_not[:5]),
        ]
    )


def _ollama_json(
    method: str, endpoint: str, payload: dict[str, Any] | None = None, timeout: int = 60
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{DEFAULT_OLLAMA_URL}{endpoint}",
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def installed_ollama_models() -> set[str]:
    try:
        payload = _ollama_json("GET", "/api/tags", timeout=10)
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return set()
    models = payload.get("models", [])
    names = set()
    for item in models:
        if isinstance(item, dict) and item.get("name"):
            names.add(str(item["name"]))
    return names


def _normalize_models(raw: str, installed: set[str]) -> list[str]:
    requested = [part.strip() for part in raw.split(",") if part.strip()]
    if not requested:
        requested = list(DEFAULT_MODELS)
    selected = []
    for model in requested:
        if model in installed:
            selected.append(model)
        elif ":" not in model and f"{model}:latest" in installed:
            selected.append(f"{model}:latest")
    return selected


def resolve_agent(
    alias: str, installed: set[str], allow_ollama_cloud: bool = False, prefer_ollama_cloud: bool = False
) -> ResolvedAgent:
    key = alias.strip().lower()
    profile = AGENT_PROFILES.get(key)
    if profile is None:
        profile = AgentProfile(
            alias=key,
            display_name=alias.strip(),
            launch_command=f"ollama run {alias.strip()}",
            swarm_surface="ad_hoc_ollama_model",
            geometry_role="ad hoc model point",
            geometry_anchor=(0.0, 0.0, 0.0),
            model_candidates=(alias.strip(), f"{alias.strip()}:latest"),
            lane_bias="implementation",
        )
    cloud_candidates = profile.cloud_model_candidates if allow_ollama_cloud else ()
    candidate_plan: list[tuple[str, str, str]] = []
    if prefer_ollama_cloud:
        candidate_plan.extend((candidate, "ollama_cloud", "ollama_cloud") for candidate in cloud_candidates)
        candidate_plan.extend((candidate, "ollama_local", "free_local") for candidate in profile.model_candidates)
    else:
        candidate_plan.extend((candidate, "ollama_local", "free_local") for candidate in profile.model_candidates)
        candidate_plan.extend((candidate, "ollama_cloud", "ollama_cloud") for candidate in cloud_candidates)

    for candidate, execution_surface, cost_tier in candidate_plan:
        if execution_surface == "ollama_cloud":
            return ResolvedAgent(
                profile=profile,
                model=candidate,
                status="active_cloud",
                reason="cloud candidate selected by opt-in policy",
                execution_surface=execution_surface,
                cost_tier=cost_tier,
            )
        if candidate in installed:
            return ResolvedAgent(
                profile=profile,
                model=candidate,
                status="active",
                reason="candidate installed",
                execution_surface=execution_surface,
                cost_tier=cost_tier,
            )
        if ":" not in candidate and f"{candidate}:latest" in installed:
            return ResolvedAgent(
                profile=profile,
                model=f"{candidate}:latest",
                status="active",
                reason="latest tag installed",
                execution_surface=execution_surface,
                cost_tier=cost_tier,
            )
    return ResolvedAgent(
        profile=profile,
        model=None,
        status="skipped",
        reason=(
            f"no local Ollama model from candidates: {', '.join(profile.model_candidates) or 'none'}"
            + (
                f"; cloud disabled, available cloud candidates: {', '.join(profile.cloud_model_candidates)}"
                if profile.cloud_model_candidates and not allow_ollama_cloud
                else ""
            )
        ),
        execution_surface="none",
        cost_tier="none",
    )


def resolve_agents(
    raw: str,
    installed: set[str],
    allow_ollama_cloud: bool = False,
    prefer_ollama_cloud: bool = False,
) -> list[ResolvedAgent]:
    aliases = [part.strip() for part in raw.split(",") if part.strip()]
    return [resolve_agent(alias, installed, allow_ollama_cloud, prefer_ollama_cloud) for alias in aliases]


def _split_paths(raw: str) -> tuple[str, ...]:
    paths = tuple(part.strip().replace("\\", "/") for part in raw.split(",") if part.strip())
    return paths or ("src/", "scripts/", "tests/", "docs/")


def inventory_allowed_files(
    allowed_paths: tuple[str, ...], focus_paths: tuple[str, ...] = (), limit: int = 80
) -> list[str]:
    files: list[str] = []
    suffixes = {".js", ".ts", ".tsx", ".py", ".md", ".json", ".cjs", ".mjs", ".html", ".ps1", ".sh"}
    blocked_parts = {"node_modules", "artifacts", "training-data", ".git", ".scbe-sandbox"}
    for raw_focus in focus_paths:
        focus = raw_focus.strip().replace("\\", "/")
        if not focus:
            continue
        path = REPO_ROOT / focus
        if path.exists() and path.is_file() and any(focus.startswith(root) for root in allowed_paths):
            files.append(focus)
    if focus_paths and files:
        return list(dict.fromkeys(files))[:limit]
    for root in allowed_paths:
        base = REPO_ROOT / root
        if not base.exists():
            continue
        if base.is_file():
            files.append(base.relative_to(REPO_ROOT).as_posix())
            continue
        for path in base.rglob("*"):
            if len(files) >= limit:
                return list(dict.fromkeys(files))[:limit]
            rel = path.relative_to(REPO_ROOT).as_posix()
            if any(part in blocked_parts for part in path.parts):
                continue
            if path.is_file() and path.suffix.lower() in suffixes:
                files.append(rel)
    return list(dict.fromkeys(files))[:limit]


def extract_file_declarations(path: str, limit: int = 24) -> list[str]:
    target = REPO_ROOT / path
    if not target.exists() or not target.is_file():
        return []
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    declarations: list[str] = []
    patterns = (
        r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\b(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=",
        r"\bexport\s+(?:class|function|const|let)\s+([A-Za-z_][A-Za-z0-9_]*)",
    )
    for pattern in patterns:
        declarations.extend(match.group(1) for match in re.finditer(pattern, content))
    return list(dict.fromkeys(declarations))[:limit]


def format_declaration_hints(file_hints: list[str], limit_files: int = 10) -> str:
    lines: list[str] = []
    for path in file_hints[:limit_files]:
        declarations = extract_file_declarations(path)
        if declarations:
            lines.append(f"- {path}: {', '.join(declarations)}")
    return "\n".join(lines) if lines else "- no declaration hints available"


LANE_GOALS = {
    "architecture": (
        "architecture",
        "Find the smallest architecture change that moves the task forward. Prefer existing SCBE surfaces.",
        ("docs/", "scripts/system/", "api/", "src/"),
        "python -c \"print('architecture lane proposal only')\"",
    ),
    "implementation": (
        "implementation",
        "Propose the concrete code patch. Keep it narrow and avoid shared files unless necessary.",
        ("src/", "scripts/", "api/", "python/", "tests/"),
        "npm test",
    ),
    "verification": (
        "verification",
        "Design the tests, smoke checks, and rollback notes. Point to exact commands.",
        ("tests/", "scripts/", "docs/"),
        "npm test",
    ),
    "product": (
        "product",
        "Explain how the result becomes a usable product surface, not just internal plumbing.",
        ("docs/", "api/", "src/", "scripts/"),
        "python -c \"print('product lane proposal only')\"",
    ),
}

LANE_TIERS = {
    "architecture": "helper",
    "implementation": "builder",
    "verification": "guard",
    "product": "packager",
}

PATH_TRUST = {
    "allow": (
        "src/",
        "scripts/",
        "api/",
        "python/",
        "tests/",
        "docs/",
        "aetherdesk/",
    ),
    "grey": (
        "package.json",
        "package-lock.json",
        "pyproject.toml",
        "vercel.json",
        ".github/workflows/",
    ),
    "black": (
        ".env",
        ".home/",
        ".codex/",
        ".git/",
        "node_modules/",
        "artifacts/",
        "training-data/",
        "config/connector_oauth/",
    ),
}

TIER_CONTRACTS = {
    "helper": (
        "Local helper lane: gather repo facts, file paths, command evidence, and constraints. "
        "Do not invent implementation symbols."
    ),
    "builder": (
        "Builder lane: propose the smallest patch. The patch must use existing files unless "
        "explicitly marked needs-human."
    ),
    "guard": (
        "Gate-guard lane: optimize for correctness over speed. Reject non-applicable patches, "
        "fake files, fake symbols, unsafe commands, and unverified assumptions."
    ),
    "packager": ("Packager lane: turn verified work into a usable product/operator surface, docs, or runbook."),
    "escalation": (
        "Escalation lane: cloud or paid model used only after cheaper lanes fail or as a final critic "
        "over concrete repo evidence."
    ),
}


def _lane_tier(lane_key: str, agent: ResolvedAgent) -> str:
    if agent.cost_tier != "free_local":
        return "escalation"
    return LANE_TIERS.get(lane_key, "builder")


def _format_trust_policy() -> str:
    return (
        "allow="
        + ",".join(PATH_TRUST["allow"])
        + "; grey_requires_human="
        + ",".join(PATH_TRUST["grey"])
        + "; black_blocked="
        + ",".join(PATH_TRUST["black"])
    )


def build_lanes(task: str, agents: list[ResolvedAgent], allowed_paths: tuple[str, ...]) -> list[WorkLane]:
    fallback_order = ("architecture", "implementation", "verification", "product")
    lanes: list[WorkLane] = []
    for idx, agent in enumerate(item for item in agents if item.model):
        lane_key = (
            agent.profile.lane_bias
            if agent.profile.lane_bias in LANE_GOALS
            else fallback_order[idx % len(fallback_order)]
        )
        name, goal_prefix, preferred_paths, verify = LANE_GOALS[lane_key]
        scoped_paths = tuple(
            path
            for path in preferred_paths
            if any(path.startswith(root) or root.startswith(path) for root in allowed_paths)
        )
        if not scoped_paths:
            scoped_paths = allowed_paths
        lanes.append(
            WorkLane(
                lane_id=f"{idx + 1:02d}-{name}",
                lane_tier=_lane_tier(lane_key, agent),
                agent_alias=agent.profile.alias,
                agent_name=agent.profile.display_name,
                model=agent.model or "",
                execution_surface=agent.execution_surface,
                cost_tier=agent.cost_tier,
                geometry_role=agent.profile.geometry_role,
                geometry_anchor=agent.profile.geometry_anchor,
                goal=f"{goal_prefix}\n\nUser task: {task}",
                allowed_paths=scoped_paths,
                blocked_paths=(".git/", ".scbe-sandbox/", "node_modules/", "artifacts/", "training-data/"),
                done_criteria=(
                    "Return a short rationale.",
                    "List files you would touch.",
                    "If code is needed, include a unified diff fenced as ```diff.",
                    "Include a verification command.",
                    "Do not touch paths outside allowed_paths.",
                ),
                verify_command=verify,
                helper_contract=TIER_CONTRACTS[_lane_tier(lane_key, agent)],
                cycle_policy=(
                    "Do not re-walk completed paths. If the same quality flag appears again, "
                    "write a correction rule or narrow the next task before retrying."
                ),
                trust_policy=_format_trust_policy(),
                output_contract="patch-proposal",
            )
        )
    return lanes


def _lane_conflicts(lanes: list[WorkLane]) -> set[str]:
    owners_by_path: dict[str, set[str]] = {}
    for lane in lanes:
        if lane.lane_tier not in {"builder", "escalation"}:
            continue
        for path in lane.allowed_paths:
            owners_by_path.setdefault(path, set()).add(lane.lane_id)
    conflicts: set[str] = set()
    for owners in owners_by_path.values():
        if len(owners) > 1:
            conflicts.update(owners)
    return conflicts


def _lane_value(lane: WorkLane, result: dict[str, Any] | None = None) -> int:
    base_by_tier = {"helper": 2, "builder": 4, "guard": 4, "packager": 3, "escalation": 5}
    value = base_by_tier.get(lane.lane_tier, 3)
    if result is not None:
        value += 1 if int(result.get("applicability_score", 0)) >= 85 else 0
        value -= 1 if result.get("quality_flags") else 0
    return max(1, min(5, value))


def _lane_risk(lane: WorkLane, result: dict[str, Any] | None = None) -> int:
    risk = 1
    if lane.lane_tier in {"builder", "escalation"}:
        risk += 1
    if lane.cost_tier != "free_local":
        risk += 1
    if any(path.startswith(("package", ".github", "api/", "src/")) for path in lane.allowed_paths):
        risk += 1
    if result is not None:
        risk += min(3, len(result.get("quality_flags") or []))
        if not result.get("ok", False):
            risk += 2
        if int(result.get("applicability_score", 0)) >= 90 and not result.get("quality_flags"):
            risk -= 1
    return max(0, min(6, risk))


def build_pazaak_plan(
    lanes: list[WorkLane],
    results: list[dict[str, Any]] | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    board = _load_pazaak_board_module()
    result_by_lane = {item.get("lane", {}).get("lane_id"): item for item in results or []}
    conflicts = _lane_conflicts(lanes)
    pazaak_lanes = []
    for lane in lanes:
        result = result_by_lane.get(lane.lane_id)
        flags = result.get("quality_flags") if result else []
        ok = bool(result.get("ok", False)) if result else False
        pazaak_lanes.append(
            board.TaskLane(
                lane_id=lane.lane_id,
                value=_lane_value(lane, result),
                risk=_lane_risk(lane, result),
                verified=bool(result and ok and not flags),
                blocked=bool(result and (not ok or flags)),
                context_noise=len(lane.allowed_paths) > 3,
                conflict=lane.lane_id in conflicts,
                stalled=bool(result and (not ok or flags)),
                owner=lane.agent_alias if lane.lane_tier in {"guard", "packager"} else "",
            )
        )
    cards = board.load_cards()
    moves = board.recommend_moves(pazaak_lanes, cards, limit=limit)
    return {
        "schema": "scbe_swarm_pazaak_plan_v1",
        "planner": "scripts/system/agentic_pazaak_board.py",
        "cards": str(board.DEFAULT_CARD_FILE.relative_to(REPO_ROOT)),
        "lane_count": len(pazaak_lanes),
        "bitboards": board.bitboards(pazaak_lanes),
        "lanes": [asdict(lane) for lane in pazaak_lanes],
        "moves": [asdict(move) for move in moves],
        "top_move": asdict(moves[0]) if moves else None,
    }


def _safe_kaggle_context_hint() -> str:
    """Pull a Kaggle context block if the env var is set; never crash the bus."""
    try:
        from scripts.kaggle.scbe_kaggle import format_kaggle_context_hint  # noqa: WPS433

        return format_kaggle_context_hint()
    except Exception:  # noqa: BLE001 — Kaggle is optional context
        return ""


def prompt_for_lane(lane: WorkLane, file_hints: list[str], constraint_mode: str) -> str:
    hints = "\n".join(f"- {path}" for path in file_hints[:80]) or "- no file hints available"
    declaration_hints = format_declaration_hints(file_hints)
    task_graph_hint = format_task_graph_hint(lane.goal, lane.output_contract)
    coding_system_hints = format_coding_system_hints(lane.goal, lane.output_contract)
    kaggle_context_hint = _safe_kaggle_context_hint()
    if constraint_mode == "relaxed":
        rules = """
        Rules:
        - Do not claim you edited files.
        - You may propose new files or existing files.
        - You may describe a broad design if a patch is not safe.
        - Keep the output concrete enough for a reviewer to judge.
        - If the task needs integration across lanes, describe the interface and stop.
        """
    else:
        rules = """
        Rules:
        - Do not claim you edited files.
        - If Decision is `build`, every listed file must already exist in Known repo file hints.
        - Do not invent files unless your decision is `needs-human` or `defer`.
        - Prefer files from Known repo file hints.
        - Do not use placeholder paths.
        - Do not use placeholder diff index lines such as 1234567..89abcdef.
        - Replace the Decision template with one exact value.
        - Keep the patch small.
        - If the task needs integration across lanes, describe the interface and stop.
        """
    if lane.output_contract == "answer":
        output_format = """
        Output format:
        1. Decision: answer
        2. Capability: what the user can do safely at this tier
        3. Limits: what is not available without operator/admin approval
        4. Next action: one concrete action the user can take
        5. Risk: one short paragraph
        """
        contract_rule = "This is a user-facing answer contract. Do not include a diff unless explicitly asked."
    elif lane.output_contract == "evidence":
        output_format = """
        Output format:
        1. Decision: evidence
        2. Files checked: bullet list of exact paths inspected or recommended
        3. Declarations: concrete symbols/classes/functions that actually exist or need checking
        4. Builder handoff: what a builder may safely patch next
        5. Risk: one short paragraph
        """
        contract_rule = "This is a helper evidence contract. Prefer repo facts over code generation."
    else:
        output_format = """
        Output format:
        1. Decision: build | defer | needs-human
        2. Files: bullet list of exact paths you would touch
        3. Patch: unified diff in a ```diff block if you can make one safely
        4. Verification: exact command(s)
        5. Risk: one short paragraph
        """
        contract_rule = "This is a patch-proposal contract. Patches must be repo-applicable before promotion."

    return textwrap.dedent(f"""
        You are a headless SCBE multi-swarm coding lane for SCBE-AETHERMOORE.

        Lane: {lane.lane_id}
        Agent: {lane.agent_name} ({lane.agent_alias})
        Model: {lane.model}
        Execution surface: {lane.execution_surface}
        Cost tier: {lane.cost_tier}
        Tier: {lane.lane_tier}
        Geometry role: {lane.geometry_role}
        Geometry anchor: {lane.geometry_anchor}
        Allowed paths: {', '.join(lane.allowed_paths)}
        Blocked paths: {', '.join(lane.blocked_paths)}
        Helper contract: {lane.helper_contract}
        Cycle policy: {lane.cycle_policy}
        Path trust policy: {lane.trust_policy}
        Output contract: {lane.output_contract}
        Contract rule: {contract_rule}
        {task_graph_hint}

        {coding_system_hints}

        {kaggle_context_hint}

        Known repo file hints:
        {hints}

        Known declaration hints:
        {declaration_hints}

        Mission:
        {lane.goal}

        {output_format}

        Constraint mode: {constraint_mode}
        {rules}
        """).strip()


def extract_mentioned_paths(text: str) -> list[str]:
    candidates = set()
    for token in text.replace("`", " ").replace(",", " ").split():
        clean = token.strip().strip(":;()[]{}\"'")
        is_root_policy_path = clean in {item.rstrip("/") for item in PATH_TRUST["grey"] + PATH_TRUST["black"]}
        if "/" not in clean and not is_root_policy_path:
            continue
        if (
            any(
                clean.endswith(suffix)
                for suffix in (".py", ".js", ".ts", ".tsx", ".md", ".json", ".html", ".cjs", ".mjs", ".ps1", ".sh")
            )
            or is_root_policy_path
        ):
            if clean.startswith("./"):
                clean = clean[2:]
            if clean.startswith("/"):
                clean = clean[1:]
            if clean.startswith("a/") or clean.startswith("b/"):
                clean = clean[2:]
            candidates.add(clean)
    return sorted(candidates)


def extract_context_symbols(text: str) -> dict[str, set[str]]:
    """Return symbols a proposed diff claims already exist in target files."""
    symbols_by_path: dict[str, set[str]] = {}
    current_path = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("+++ "):
            candidate = line.removeprefix("+++ ").strip()
            if candidate.startswith("b/"):
                candidate = candidate[2:]
            if candidate != "/dev/null":
                current_path = candidate
            continue
        if not current_path:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            continue
        search_line = line
        if line.startswith("@@"):
            search_line = line.split("@@", 2)[-1]
        match = re.search(r"\b(?:class|def|function)\s+([A-Za-z_][A-Za-z0-9_]*)", search_line)
        if match:
            symbols_by_path.setdefault(current_path, set()).add(match.group(1))
    return symbols_by_path


def extract_evidence_declarations(text: str) -> set[str]:
    """Return declaration names a helper evidence packet claims are real."""
    symbols: set[str] = set()
    in_section = False
    stopwords = {
        "declarations",
        "declaration",
        "function",
        "functions",
        "class",
        "classes",
        "symbol",
        "symbols",
        "concrete",
        "checked",
        "exists",
        "exist",
        "needs",
        "checking",
        "none",
        "n/a",
    }
    for raw_line in text.splitlines():
        line = raw_line.strip()
        lowered = line.lower()
        if re.search(r"\bdeclarations?\b", lowered):
            in_section = True
            line = re.sub(r"^\s*(?:\d+\.\s*)?(?:\*\*)?declarations?(?:\*\*)?\s*:?", "", line, flags=re.I)
        elif in_section and re.search(
            r"\b(?:builder handoff|risk|verification|patch|files checked|next action)\b", lowered
        ):
            break
        if not in_section or "need checking" in lowered or "needs checking" in lowered:
            continue
        candidates = set(re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", line))
        candidates.update(
            match.group(1)
            for match in re.finditer(r"\b(?:class|def|function|const|let)\s+([A-Za-z_][A-Za-z0-9_]*)", line)
        )
        if line.startswith(("-", "*")) or ":" in raw_line:
            for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", line):
                has_shape = "_" in token or (any(ch.islower() for ch in token) and any(ch.isupper() for ch in token))
                if has_shape:
                    candidates.add(token)
        for candidate in candidates:
            if candidate.lower() not in stopwords:
                symbols.add(candidate)
    return symbols


def _file_contains_symbol(path: str, symbol: str) -> bool:
    target = REPO_ROOT / path
    if not target.exists() or not target.is_file():
        return False
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    patterns = (
        rf"\bclass\s+{re.escape(symbol)}\b",
        rf"\bdef\s+{re.escape(symbol)}\b",
        rf"\bfunction\s+{re.escape(symbol)}\b",
        rf"\bconst\s+{re.escape(symbol)}\b",
        rf"\blet\s+{re.escape(symbol)}\b",
        rf"\bexport\s+(?:class|function|const|let)\s+{re.escape(symbol)}\b",
    )
    return any(re.search(pattern, content) for pattern in patterns)


def quality_flags(
    text: str,
    allowed_paths: tuple[str, ...],
    require_paths: bool = True,
    check_paths: bool = True,
) -> list[str]:
    flags: list[str] = []
    lowered = text.lower()
    mentioned = extract_mentioned_paths(text)
    for path in mentioned if check_paths else []:
        if any(path.startswith(root) for root in PATH_TRUST["black"]):
            flags.append(f"blacklisted_path:{path}")
            continue
        if any(path.startswith(root) or path == root.rstrip("/") for root in PATH_TRUST["grey"]):
            flags.append(f"graylisted_path_requires_approval:{path}")
        if not any(path.startswith(root) for root in allowed_paths):
            flags.append(f"path_outside_lane:{path}")
        elif not (REPO_ROOT / path).exists():
            flags.append(f"path_not_found:{path}")
    if "1234567" in text or "89abcdef" in text or "abc1234" in text or "def56789" in text:
        flags.append("placeholder_diff_index")
    if "Your implementation goes here" in text or "existing code here" in text:
        flags.append("placeholder_implementation")
    if (
        "build | defer | needs-human" in text
        or "answer | defer | needs-human" in text
        or "evidence | defer | needs-human" in text
    ):
        flags.append("unresolved_decision_template")
    decision_pattern = r'"?decision"?(?:\*\*)?\s*:\s*(?:\*\*)?"?(build|answer|evidence|defer|needs-human)\b'
    if not re.search(decision_pattern, lowered):
        flags.append("decision_missing_or_ambiguous")
    if "new file mode" in lowered or "--- /dev/null" in lowered:
        flags.append("new_file_diff_requires_human")
    if "git commit" in lowered or "git add" in lowered or "git push" in lowered:
        flags.append("verification_mutates_git_state")
    if "subprocess.popen" in lowered or "start-process" in lowered or "& " in text:
        flags.append("background_process_side_effect")
    if ".orig" in lowered or re.search(r"^---\s+\S+\s+\d{4}-\d{2}-\d{2}", text, re.MULTILINE):
        flags.append("non_git_unified_diff_context")
    if "--hermes-agent" in lowered or "--openclaw-agent" in lowered:
        flags.append("invented_test_runner_flag")
    if "from hermes." in lowered or "from openclaw." in lowered:
        flags.append("probable_external_module_import")
    if "scripts/system/scbe_swarm_router.py" in mentioned and "class scbeswarmrouter" in lowered:
        flags.append("probable_wrapper_symbol_hallucination")
    for path, symbols in extract_context_symbols(text).items():
        if not any(path.startswith(root) for root in allowed_paths):
            continue
        for symbol in sorted(symbols):
            if not _file_contains_symbol(path, symbol):
                flags.append(f"symbol_not_found:{path}#{symbol}")
    if re.search(r"decision(?:\*\*)?\s*:\s*(?:\*\*)?evidence\b", lowered):
        evidence_symbols = extract_evidence_declarations(text)
        evidence_paths = [
            path
            for path in mentioned
            if any(path.startswith(root) for root in allowed_paths) and (REPO_ROOT / path).exists()
        ]
        evidence_path_tokens = {
            token
            for path in evidence_paths
            for token in {
                Path(path).stem,
                Path(path).stem.replace("-", "_"),
                Path(path).stem.replace("_", "-"),
            }
        }
        for symbol in sorted(evidence_symbols):
            if symbol in evidence_path_tokens or any(token.startswith(symbol) for token in evidence_path_tokens):
                continue
            if evidence_paths and not any(_file_contains_symbol(path, symbol) for path in evidence_paths):
                flags.append(f"evidence_symbol_not_found:{symbol}")
    if re.search(r"https?://", text) and not any(
        allowed in lowered
        for allowed in (
            "github.com/issdandavis",
            "ollama.com",
            "docs.ollama.com",
            "github.com/openai",
            "github.com/anthropics",
        )
    ):
        flags.append("external_resource_requires_review")
    if require_paths and not mentioned:
        flags.append("no_paths_mentioned")
    return flags


def applicability_score(flags: list[str]) -> int:
    score = 100
    hard_blockers = {
        "blacklisted_path",
        "path_outside_lane",
        "path_not_found",
        "symbol_not_found",
        "probable_wrapper_symbol_hallucination",
        "verification_mutates_git_state",
        "background_process_side_effect",
    }
    medium_blockers = {
        "graylisted_path_requires_approval",
        "external_resource_requires_review",
        "invented_test_runner_flag",
        "probable_external_module_import",
        "non_git_unified_diff_context",
    }
    for flag in flags:
        key = flag.split(":", 1)[0]
        if key in hard_blockers:
            score -= 35
        elif key in medium_blockers:
            score -= 20
        else:
            score -= 10
    return max(0, score)


def summarize_quality_flags(results: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        for flag in result.get("quality_flags") or []:
            key = flag.split(":", 1)[0]
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def build_correction_guide(results: list[dict[str, Any]]) -> list[dict[str, str]]:
    guide = []
    flag_counts = summarize_quality_flags(results)
    corrections = {
        "path_not_found": "Pin focus paths to existing files and require agents to cite known file hints before patching.",
        "probable_wrapper_symbol_hallucination": "Route wrapper files to guard lanes first; builders should patch the implementation module, not the thin wrapper.",
        "graylisted_path_requires_approval": "Require human approval or a dedicated integration packet before touching package, deploy, or workflow files.",
        "blacklisted_path": "Block immediately. Do not retry against secrets, local agent state, generated artifacts, or dependency folders.",
        "external_resource_requires_review": "Move the source to the whitelist/greylist review sheet before letting a lane depend on it.",
        "decision_missing_or_ambiguous": "Re-run with strict output format and reject prose-only answers.",
        "no_paths_mentioned": "Re-run as a helper lane to collect exact files first, then pass those files to a builder.",
        "background_process_side_effect": "Replace background process commands with deterministic foreground smoke commands.",
        "invented_test_runner_flag": "Ask a local helper lane to inspect package scripts and existing test commands before retry.",
        "symbol_not_found": "Ask a helper lane to inspect real declarations in the target file before sending the patch to a builder.",
    }
    for flag, count in flag_counts.items():
        guide.append(
            {
                "flag": flag,
                "count": str(count),
                "correction": corrections.get(
                    flag, "Narrow the task, add file evidence, then retry through a guard lane."
                ),
            }
        )
    return guide


DARPA_ASSURANCE_REQUIREMENTS = {
    "continual_assurance": "design-time packet plus operation-time monitoring, correction guide, and rerun cycle",
    "heterogeneous_evidence": "model response, path inventory, symbol applicability, command plan, quality flags, and benchmark artifact",
    "robustness": "rejects fake files, fake symbols, unsafe commands, blacklisted paths, and unreviewed external resources",
    "predictability": "every lane is constrained by allowed paths, tier contract, trust policy, and explicit promotion rule",
    "patch_functionality": "patches are not promoted until they pass applicability gates and then safe_apply smoke testing",
}


def build_assurance_packet(results: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [int(result.get("applicability_score", 0)) for result in results]
    return {
        "schema": "scbe_darpa_style_assurance_packet_v1",
        "readiness": "prototype_evidence_packet",
        "requirements": DARPA_ASSURANCE_REQUIREMENTS,
        "acceptance_rule": (
            "A lane is promotable only when it returns a nonempty proposal, has no quality flags, "
            "has applicability_score >= 90, and is later passed through safe_apply with a smoke command."
        ),
        "mean_applicability_score": round(sum(scores) / len(scores), 2) if scores else 0,
        "min_applicability_score": min(scores) if scores else 0,
        "blocked_reason_counts": summarize_quality_flags(results),
    }


def run_lane(lane: WorkLane, timeout: int, constraint_mode: str, focus_paths: tuple[str, ...]) -> dict[str, Any]:
    started = time.time()
    file_hints = inventory_allowed_files(lane.allowed_paths, focus_paths)
    prompt = prompt_for_lane(lane, file_hints, constraint_mode)
    try:
        payload = _ollama_json(
            "POST",
            "/api/generate",
            {
                "model": lane.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.15, "top_p": 0.9, "num_ctx": 8192},
            },
            timeout=timeout,
        )
        text = str(payload.get("response", "")).strip()
        ok = bool(text)
        error = ""
    except Exception as exc:  # noqa: BLE001 - artifact should preserve exact failure
        text = ""
        ok = False
        error = f"{type(exc).__name__}: {exc}"
    flags = (
        quality_flags(
            text,
            lane.allowed_paths,
            require_paths=lane.output_contract != "answer",
            check_paths=lane.output_contract != "answer",
        )
        if text
        else []
    )
    if not ok:
        flags.append("lane_failed")
    applicability = applicability_score(flags)
    return {
        "lane": asdict(lane),
        "ok": ok,
        "error": error,
        "response": text,
        "response_chars": len(text),
        "prompt": prompt,
        "prompt_chars": len(prompt),
        "quality_flags": flags,
        "applicability_score": applicability,
        "applicability": "promotable" if ok and applicability >= 90 and not flags else "blocked",
        "constraint_mode": constraint_mode,
        "elapsed_seconds": round(time.time() - started, 3),
    }


def choose_next_action(promotable: list[dict[str, Any]], free_signal_exhausted: bool) -> str:
    if free_signal_exhausted:
        return "run_helper_guard_cycle_before_escalation"
    contracts = {result.get("lane", {}).get("output_contract", "patch-proposal") for result in promotable}
    if contracts == {"answer"}:
        return "deliver_answer_to_user"
    if contracts == {"evidence"}:
        return "handoff_evidence_to_builder"
    if "patch-proposal" in contracts:
        return "extract_one_promotable_diff_then_safe_apply"
    return "review_promotable_lane"


def build_routing_recommendation(results: list[dict[str, Any]], agents: list[ResolvedAgent]) -> dict[str, Any]:
    active = [agent for agent in agents if agent.model]
    skipped = [agent for agent in agents if not agent.model]
    promotable = [result for result in results if result["ok"] and not result.get("quality_flags")]
    blocked = [result for result in results if not result["ok"] or result.get("quality_flags")]
    failed = [result for result in results if not result["ok"]]
    guard_lanes = [
        result
        for result in results
        if result.get("lane", {}).get("lane_tier") == "guard" and result["ok"] and not result.get("quality_flags")
    ]
    builder_lanes = [
        result
        for result in results
        if result.get("lane", {}).get("lane_tier") in {"builder", "escalation"} and result["ok"]
    ]
    free_signal_exhausted = bool(results) and not promotable
    correction_guide = build_correction_guide(results)
    assurance_packet = build_assurance_packet(results)
    return {
        "schema": "scbe_swarm_routing_v1",
        "policy": "tiered_free_first_guarded_builder_rotation",
        "tier_contract": {
            "helper": "local small models gather facts and file evidence",
            "builder": "coding models produce narrow diffs",
            "guard": "correctness-first models block fake or unsafe proposals",
            "packager": "product/docs lane turns verified work into operator value",
            "escalation": "cloud/paid models run only after helper evidence or as final critic",
        },
        "free_signal_exhausted": free_signal_exhausted,
        "promotable_lanes": len(promotable),
        "blocked_lanes": len(blocked),
        "failed_lanes": len(failed),
        "guard_clean_lanes": len(guard_lanes),
        "builder_attempt_lanes": len(builder_lanes),
        "quality_flag_counts": summarize_quality_flags(results),
        "correction_guide": correction_guide,
        "assurance_packet": assurance_packet,
        "next_cycle": (
            "helper_collect_file_evidence_then_guard_review"
            if correction_guide
            else "extract_one_promotable_diff_then_safe_apply"
        ),
        "active_agents": [
            {
                "alias": agent.profile.alias,
                "name": agent.profile.display_name,
                "model": agent.model,
                "swarm_surface": agent.profile.swarm_surface,
                "execution_surface": agent.execution_surface,
                "cost_tier": agent.cost_tier,
                "geometry_role": agent.profile.geometry_role,
                "geometry_anchor": agent.profile.geometry_anchor,
                "launch_command": agent.profile.launch_command,
            }
            for agent in active
        ],
        "skipped_agents": [
            {
                "alias": agent.profile.alias,
                "name": agent.profile.display_name,
                "swarm_surface": agent.profile.swarm_surface,
                "execution_surface": agent.execution_surface,
                "cost_tier": agent.cost_tier,
                "launch_command": agent.profile.launch_command,
                "reason": agent.reason,
            }
            for agent in skipped
        ],
        "next_action": choose_next_action(promotable, free_signal_exhausted),
        "paid_escalation_note": (
            "Use a paid/big model only as critic, planner, builder over helper-provided repo evidence, "
            "or final integrator after local lanes fail quality gates; keep local lanes as breadth/support "
            "to reduce token cost."
        ),
    }


def build_integration_plan(task: str, results: list[dict[str, Any]], routing: dict[str, Any]) -> str:
    promotable = [result for result in results if result["ok"] and not result.get("quality_flags")]
    blocked = [result for result in results if not result["ok"] or result.get("quality_flags")]
    lines = [
        "# SCBE Swarm Router Integration Plan",
        "",
        f"Task: {task}",
        "",
        "## Promotion Summary",
        "",
        f"- promotable_lanes: `{len(promotable)}`",
        f"- blocked_lanes: `{len(blocked)}`",
        "",
        "Only promotable lanes should be extracted into patches. Blocked lanes are advisory signal only.",
        "",
        "## Routing Recommendation",
        "",
        f"- policy: `{routing['policy']}`",
        f"- free_signal_exhausted: `{routing['free_signal_exhausted']}`",
        f"- next_action: `{routing['next_action']}`",
        f"- next_cycle: `{routing['next_cycle']}`",
        f"- guard_clean_lanes: `{routing['guard_clean_lanes']}`",
        f"- builder_attempt_lanes: `{routing['builder_attempt_lanes']}`",
        f"- assurance_schema: `{routing['assurance_packet']['schema']}`",
        f"- mean_applicability_score: `{routing['assurance_packet']['mean_applicability_score']}`",
        f"- paid_escalation_note: {routing['paid_escalation_note']}",
        "",
        "## Pazaak Board Recommendation",
        "",
    ]
    pazaak_plan = routing.get("pazaak_plan") or {}
    if pazaak_plan.get("moves"):
        lines.extend(["| Lane | Card | Symbol | Score | Reason |", "|---|---|---:|---:|---|"])
        for move in pazaak_plan["moves"][:6]:
            lines.append(
                f"| `{move['lane_id']}` | {move['card_name']} | `{move['symbol']}` | "
                f"{move['score']} | {move['reason']} |"
            )
        lines.extend(
            [
                "",
                f"- bitboards: `{json.dumps(pazaak_plan.get('bitboards', {}), sort_keys=True)}`",
                "",
            ]
        )
    else:
        lines.extend(["No Pazaak board moves were generated.", ""])
    lines.extend(
        [
        "## Assurance Packet",
        "",
        f"- readiness: `{routing['assurance_packet']['readiness']}`",
        f"- acceptance_rule: {routing['assurance_packet']['acceptance_rule']}",
        "",
        "| Requirement | Evidence Rule |",
        "|---|---|",
        ]
    )
    for key, value in routing["assurance_packet"]["requirements"].items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend(
        [
            "",
            "## Correction Guide",
            "",
        ]
    )
    if routing["correction_guide"]:
        lines.extend(["| Flag | Count | Correction |", "|---|---:|---|"])
        for item in routing["correction_guide"]:
            lines.append(f"| `{item['flag']}` | {item['count']} | {item['correction']} |")
        lines.append("")
    else:
        lines.extend(["No repeated quality blockers detected.", ""])
    lines.extend(
        [
            "## Tier Contract",
            "",
            "| Tier | Rule |",
            "|---|---|",
        ]
    )
    for tier, rule in routing["tier_contract"].items():
        lines.append(f"| `{tier}` | {rule} |")
    lines.extend(
        [
            "",
            "## Lane Results",
            "",
        ]
    )
    for result in results:
        lane = result["lane"]
        status = "ok" if result["ok"] else "failed"
        promotion = "promotable" if result["ok"] and not result.get("quality_flags") else "blocked"
        lines.extend(
            [
                f"### {lane['lane_id']} ({lane['model']})",
                "",
                f"- agent: `{lane['agent_name']}` (`{lane['agent_alias']}`)",
                f"- tier: `{lane['lane_tier']}`",
                f"- execution_surface: `{lane['execution_surface']}`",
                f"- cost_tier: `{lane['cost_tier']}`",
                f"- geometry_role: `{lane['geometry_role']}`",
                f"- geometry_anchor: `{lane['geometry_anchor']}`",
                f"- helper_contract: {lane['helper_contract']}",
                f"- cycle_policy: {lane['cycle_policy']}",
                f"- status: `{status}`",
                f"- promotion: `{promotion}`",
                f"- applicability_score: `{result.get('applicability_score', 0)}`",
                f"- elapsed_seconds: `{result['elapsed_seconds']}`",
                f"- allowed_paths: `{', '.join(lane['allowed_paths'])}`",
                f"- verify_command: `{lane['verify_command']}`",
                f"- quality_flags: `{', '.join(result.get('quality_flags') or ['none'])}`",
                "",
            ]
        )
        if result["error"]:
            lines.extend(["Error:", "", f"```text\n{result['error']}\n```", ""])
        else:
            preview = result["response"][:2000]
            lines.extend(["Response preview:", "", f"```text\n{preview}\n```", ""])
    lines.extend(
        [
            "## Integration Rule",
            "",
            "Follow the `next_action` above. Only patch-proposal lanes may be extracted into diffs.",
            "",
            "```powershell",
            'python scripts/agents/safe_apply.py --patch-file path\\to\\proposal.diff --smoke "npm test"',
            "```",
            "",
            "Promote patch lanes only when non-conflicting patches pass smoke checks. Answer and evidence lanes are delivered or handed off, not applied.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local SCBE multi-swarm coding router.")
    parser.add_argument("--task", default="")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    parser.add_argument(
        "--agents",
        default="",
        help=(
            "Comma-separated agent aliases. Includes Ollama launch agents "
            "claude,openclaw,hermes,opencode,codex,copilot,droid,pi plus "
            "free/open external surfaces aider,openhands,goose,cline,continue."
        ),
    )
    parser.add_argument("--list-agents", action="store_true", help="Print the known agent profile catalog and exit.")
    parser.add_argument(
        "--allow-ollama-cloud", action="store_true", help="Allow opt-in use of Ollama cloud model candidates."
    )
    parser.add_argument(
        "--prefer-ollama-cloud", action="store_true", help="Prefer Ollama cloud candidates before local candidates."
    )
    parser.add_argument("--allowed-paths", default="src/,scripts/,api/,python/,tests/,docs/")
    parser.add_argument(
        "--output-contract",
        choices=("patch-proposal", "answer", "evidence"),
        default="patch-proposal",
        help="Lane output contract. Public/free users can use answer; internal helper lanes can use evidence.",
    )
    parser.add_argument(
        "--focus-paths",
        default="",
        help="Comma-separated existing files to pin near the top of each lane's repo hints.",
    )
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--max-workers", type=int, default=2, help="Maximum concurrent local model lanes.")
    parser.add_argument(
        "--constraint-mode",
        choices=("strict", "relaxed"),
        default="strict",
        help="Prompt constraint mode. Safety analyzer still runs in both modes.",
    )
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--dry-run", action="store_true", help="Write lane plan without calling Ollama.")
    args = parser.parse_args()

    if args.list_agents:
        print(json.dumps({key: asdict(profile) for key, profile in AGENT_PROFILES.items()}, indent=2))
        return 0
    if not args.task.strip():
        parser.error("--task is required unless --list-agents is used")

    installed = installed_ollama_models()
    resolved_agents = (
        resolve_agents(args.agents, installed, args.allow_ollama_cloud, args.prefer_ollama_cloud) if args.agents else []
    )
    raw_models = _normalize_models(args.models, installed) if not resolved_agents else []
    for model in raw_models:
        resolved_agents.append(
            ResolvedAgent(
                profile=AgentProfile(
                    alias=model,
                    display_name=model,
                    launch_command=f"ollama run {model}",
                    swarm_surface=RAW_MODEL_PROFILE.swarm_surface,
                    geometry_role=RAW_MODEL_PROFILE.geometry_role,
                    geometry_anchor=RAW_MODEL_PROFILE.geometry_anchor,
                    model_candidates=(model,),
                    lane_bias=RAW_MODEL_PROFILE.lane_bias,
                ),
                model=model,
                status="active",
                reason="raw model requested",
                execution_surface=RAW_MODEL_PROFILE.swarm_surface,
                cost_tier="free_local",
            )
        )
    active_agents = [agent for agent in resolved_agents if agent.model]
    if not active_agents:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "no requested agents or Ollama models are locally runnable",
                    "installed": sorted(installed),
                    "agents": [asdict(agent) for agent in resolved_agents],
                },
                indent=2,
            )
        )
        return 2

    run_dir = make_run_dir(Path(args.output_root))
    lanes = [
        WorkLane(**{**asdict(lane), "output_contract": args.output_contract})
        for lane in build_lanes(args.task, active_agents, _split_paths(args.allowed_paths))
    ]
    _write_json(run_dir / "lanes.json", [asdict(lane) for lane in lanes])
    _write_json(run_dir / "agents.json", [asdict(agent) for agent in resolved_agents])

    if args.dry_run:
        results = [
            {
                "lane": asdict(lane),
                "ok": True,
                "error": "",
                "response": "",
                "response_chars": 0,
                "prompt": "",
                "prompt_chars": 0,
                "quality_flags": ["dry_run"],
                "applicability_score": 0,
                "applicability": "blocked",
                "constraint_mode": args.constraint_mode,
                "elapsed_seconds": 0.0,
            }
            for lane in lanes
        ]
    else:
        results = []
        worker_count = max(1, min(args.max_workers, len(lanes)))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            focus_paths = _split_paths(args.focus_paths)
            future_map = {
                executor.submit(run_lane, lane, args.timeout, args.constraint_mode, focus_paths): lane for lane in lanes
            }
            for future in as_completed(future_map):
                results.append(future.result())
        results.sort(key=lambda item: item["lane"]["lane_id"])

    _write_json(run_dir / "results.json", {"task": args.task, "results": results})
    routing = build_routing_recommendation(results, resolved_agents)
    pazaak_plan = build_pazaak_plan(lanes, results, limit=8)
    routing["pazaak_plan"] = pazaak_plan
    _write_json(run_dir / "pazaak_plan.json", pazaak_plan)
    _write_json(run_dir / "routing.json", routing)
    plan = build_integration_plan(args.task, results, routing)
    (run_dir / "integration_plan.md").write_text(plan, encoding="utf-8")
    latest = Path(args.output_root) / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    _write_json(latest / "results.json", {"task": args.task, "run_dir": str(run_dir), "results": results})
    _write_json(latest / "agents.json", [asdict(agent) for agent in resolved_agents])
    _write_json(latest / "routing.json", routing)
    _write_json(latest / "pazaak_plan.json", pazaak_plan)
    (latest / "integration_plan.md").write_text(plan, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "run_dir": str(run_dir),
                "agents": [asdict(agent) for agent in resolved_agents],
                "models": [agent.model for agent in active_agents],
                "lanes": [lane.lane_id for lane in lanes],
                "successful_lanes": sum(1 for item in results if item["ok"]),
                "failed_lanes": sum(1 for item in results if not item["ok"]),
                "flagged_lanes": sum(1 for item in results if item.get("quality_flags")),
                "promotable_lanes": sum(1 for item in results if item["ok"] and not item.get("quality_flags")),
                "blocked_lanes": sum(1 for item in results if not item["ok"] or item.get("quality_flags")),
                "mean_applicability_score": (
                    round(
                        sum(float(item.get("applicability_score", 0)) for item in results) / len(results),
                        2,
                    )
                    if results
                    else 0
                ),
                "quality_flag_counts": summarize_quality_flags(results),
                "next_action": routing["next_action"],
                "next_cycle": routing["next_cycle"],
                "pazaak_top_move": pazaak_plan.get("top_move"),
                "integration_plan": str(run_dir / "integration_plan.md"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
