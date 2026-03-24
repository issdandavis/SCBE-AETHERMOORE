#!/usr/bin/env python3
"""SCBE System CLI (unified).

Commands:
- tongues    -> delegates to six-tongues-cli.py (encoding, xlate, blend, GeoSeal)
- gap        -> runs notion_pipeline_gap_review.py
- self-improve -> runs self_improvement_orchestrator.py
- web        -> delegates to agentic_web_tool.py
- antivirus  -> runs agentic_antivirus.py
- status     -> prints a quick system run summary
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import shlex
import shutil
import uuid
import subprocess
import tempfile
from datetime import datetime, timezone
import sys
import urllib.error
from urllib.request import Request, urlopen
from urllib.parse import parse_qs, urlsplit, urlunsplit
from pathlib import Path


DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAD_ROOT = Path(".scbe") / "polly-pads"
DEFAULT_AGENT_REGISTRY = Path(".scbe") / "agent_squad.json"
DEFAULT_CLI_CONTEXT = Path(".scbe") / "cli-context.json"
DEFAULT_NOTEBOOKLM_PAD_ID = "notebooklm-main"
DEFAULT_NOTEBOOKLM_URL = "https://notebooklm.google.com/notebook/bf1e9a1b-b49c-4343-8f0e-8494546e4f24"
SENSITIVE_METADATA_ITERATIONS = 120_000
RUNTIME_FILE_SUFFIXES = {
    "python": ".py",
    "javascript": ".js",
    "typescript": ".ts",
    "powershell": ".ps1",
    "bash": ".sh",
    "cmd": ".cmd",
}
RUNTIME_LANGUAGE_ALIASES = {
    "python": "python",
    "py": "python",
    "javascript": "javascript",
    "js": "javascript",
    "node": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
    "powershell": "powershell",
    "pwsh": "powershell",
    "ps1": "powershell",
    "bash": "bash",
    "sh": "bash",
    "cmd": "cmd",
    "batch": "cmd",
}
RUNTIME_LANGUAGE_CHOICES = tuple(sorted(set(RUNTIME_LANGUAGE_ALIASES.values())))
RUNTIME_TONGUE_BY_LANGUAGE = {
    "python": "CA",
    "javascript": "CA",
    "typescript": "CA",
    "powershell": "KO",
    "bash": "KO",
    "cmd": "KO",
}
RUNTIME_EXTENSION_ALIASES = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".ps1": "powershell",
    ".sh": "bash",
    ".bash": "bash",
    ".cmd": "cmd",
    ".bat": "cmd",
}
_TONGUES_MODULE = None
_ACTION_MAP_MODULE = None
_COLAB_CATALOG_MODULE = None
_REPO_ORDERING_MODULE = None

FLOW_TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
FLOW_SKILLS = [
    "multi-agent-orchestrator",
    "development-flow-loop",
    "scbe-codebase-orienter",
    "scbe-self-improvement-skill-management",
]
FLOW_AGENT_BLUEPRINTS = (
    {
        "tongue": "KO",
        "role": "Integration Coordinator",
        "purpose": "Own intake, route handoffs, and keep the active packet moving.",
        "default_tools": ["scbe-system", "github", "notion"],
    },
    {
        "tongue": "AV",
        "role": "Architecture Curator",
        "purpose": "Validate system shape, interfaces, and cross-layer coherence before expansion.",
        "default_tools": ["docs", "tests", "harmonic"],
    },
    {
        "tongue": "RU",
        "role": "Security Auditor",
        "purpose": "Check attack surface, trust boundaries, and regression risk before promotion.",
        "default_tools": ["antivirus", "aetherauth", "tests"],
    },
    {
        "tongue": "CA",
        "role": "Implementation Engineer",
        "purpose": "Ship the working code path and keep the test lane green.",
        "default_tools": ["runtime", "git", "tests"],
    },
    {
        "tongue": "UM",
        "role": "Documentation Specialist",
        "purpose": "Capture operator guidance, change notes, and public/private explanations.",
        "default_tools": ["docs", "notion", "obsidian"],
    },
    {
        "tongue": "DR",
        "role": "Telemetry Archivist",
        "purpose": "Record action maps, package training rows, and keep replay artifacts structured.",
        "default_tools": ["action-map", "training", "huggingface"],
    },
)
FLOW_WORKFLOW_TEMPLATES = {
    "architecture-enhancement": {
        "summary": "Default SCBE architecture upgrade loop from review through integration.",
        "steps": [
            {
                "id": "review",
                "name": "Architecture Review",
                "owner_role": "Architecture Curator",
                "depends_on": [],
                "deliverables": ["system map", "interface notes", "risk flags"],
                "acceptance": "Component boundaries and failure modes are explicit.",
                "touched_layers": ["control-plane", "governance"],
            },
            {
                "id": "implement",
                "name": "Implementation",
                "owner_role": "Implementation Engineer",
                "depends_on": ["review"],
                "deliverables": ["code diff", "targeted tests"],
                "acceptance": "The minimum correct path works locally with targeted verification.",
                "touched_layers": ["execution", "runtime"],
            },
            {
                "id": "document",
                "name": "Documentation",
                "owner_role": "Documentation Specialist",
                "depends_on": ["implement"],
                "deliverables": ["operator guide", "change summary"],
                "acceptance": "The next operator can run the lane without reverse engineering.",
                "touched_layers": ["docs", "memory"],
            },
            {
                "id": "audit",
                "name": "Security Audit",
                "owner_role": "Security Auditor",
                "depends_on": ["implement"],
                "deliverables": ["risk review", "boundary checks"],
                "acceptance": "Trust boundaries and failure regressions are checked.",
                "touched_layers": ["governance", "security"],
            },
            {
                "id": "integrate",
                "name": "Integration",
                "owner_role": "Integration Coordinator",
                "depends_on": ["document", "audit"],
                "deliverables": ["merged packet", "roll-forward plan"],
                "acceptance": "Outputs reconcile into one lane with no orphan work packets.",
                "touched_layers": ["control-plane", "coordination"],
            },
            {
                "id": "archive",
                "name": "Telemetry Archive",
                "owner_role": "Telemetry Archivist",
                "depends_on": ["integrate"],
                "deliverables": ["action map", "training rows", "run summary"],
                "acceptance": "The workflow can be replayed as training data and operator evidence.",
                "touched_layers": ["training", "storage"],
            },
        ],
    },
    "implementation-loop": {
        "summary": "Implementation-first loop for coding work that still preserves review and telemetry.",
        "steps": [
            {
                "id": "scope",
                "name": "Scope Packet",
                "owner_role": "Integration Coordinator",
                "depends_on": [],
                "deliverables": ["goal", "constraints", "ownership map"],
                "acceptance": "Work packets are bounded before edits start.",
                "touched_layers": ["coordination"],
            },
            {
                "id": "build",
                "name": "Code Build",
                "owner_role": "Implementation Engineer",
                "depends_on": ["scope"],
                "deliverables": ["code change", "local proof"],
                "acceptance": "Working code exists for the scoped path.",
                "touched_layers": ["execution", "runtime"],
            },
            {
                "id": "verify",
                "name": "Security Review",
                "owner_role": "Security Auditor",
                "depends_on": ["build"],
                "deliverables": ["review notes", "regression flags"],
                "acceptance": "The delta is acceptable to promote.",
                "touched_layers": ["security", "governance"],
            },
            {
                "id": "publish",
                "name": "Guide + Telemetry",
                "owner_role": "Telemetry Archivist",
                "depends_on": ["verify"],
                "deliverables": ["action map", "training rows", "operator note"],
                "acceptance": "The build is replayable and documented.",
                "touched_layers": ["training", "docs"],
            },
        ],
    },
    "training-center-loop": {
        "summary": "Research and workflow outputs refined into protected training packets.",
        "steps": [
            {
                "id": "collect",
                "name": "Collect Evidence",
                "owner_role": "Documentation Specialist",
                "depends_on": [],
                "deliverables": ["source notes", "export paths", "metadata"],
                "acceptance": "Inputs are traceable to a source lane.",
                "touched_layers": ["docs", "memory"],
            },
            {
                "id": "shape",
                "name": "Design Training Packet",
                "owner_role": "Architecture Curator",
                "depends_on": ["collect"],
                "deliverables": ["schema mapping", "curriculum tags"],
                "acceptance": "The packet shape matches the target model role.",
                "touched_layers": ["training", "governance"],
            },
            {
                "id": "protect",
                "name": "Privacy + Safety Audit",
                "owner_role": "Security Auditor",
                "depends_on": ["shape"],
                "deliverables": ["leakage check", "quarantine decision"],
                "acceptance": "Only promotable rows survive the gate.",
                "touched_layers": ["security", "training"],
            },
            {
                "id": "emit",
                "name": "Emit Training Rows",
                "owner_role": "Telemetry Archivist",
                "depends_on": ["protect"],
                "deliverables": ["jsonl rows", "ledger metadata"],
                "acceptance": "Rows are ready for HF or local fine-tuning.",
                "touched_layers": ["training", "storage"],
            },
        ],
    },
}
FLOW_ROLE_PATHS = {
    "Architecture Curator": {
        "allowed": ["src", "scripts", "docs", "tests", "package.json", "pyproject.toml"],
        "blocked": ["artifacts", "training/runs", "SCBE-AETHERMOORE-v3.0.0"],
    },
    "Implementation Engineer": {
        "allowed": ["src", "scripts", "tests", "scbe.py", "package.json"],
        "blocked": ["artifacts", "training/runs", "SCBE-AETHERMOORE-v3.0.0"],
    },
    "Documentation Specialist": {
        "allowed": ["docs", "README.md", "notes", "scripts"],
        "blocked": ["node_modules", "SCBE-AETHERMOORE-v3.0.0"],
    },
    "Security Auditor": {
        "allowed": ["src", "scripts", "tests", "docs"],
        "blocked": ["training/runs", "SCBE-AETHERMOORE-v3.0.0"],
    },
    "Integration Coordinator": {
        "allowed": ["scbe.py", "scripts", "docs", "tests", "src"],
        "blocked": ["node_modules", "SCBE-AETHERMOORE-v3.0.0"],
    },
    "Telemetry Archivist": {
        "allowed": ["training", "artifacts", "docs", "scripts"],
        "blocked": ["node_modules", "SCBE-AETHERMOORE-v3.0.0"],
    },
}
CLI_TOOL_CHECKS = (
    ("git", "git"),
    ("node", "node"),
    ("npm", "npm"),
    ("gh", "gh"),
    ("hf", "hf"),
    ("firebase", "firebase"),
    ("docker", "docker"),
    ("n8n", "n8n"),
)
FILE_ACTIVE_ACTIONS = frozenset({"keep-active", "keep-scoped", "keep-and-publish", "curate-before-promote"})
FILE_EXPORT_ACTIONS = frozenset(
    {"export-and-ignore", "archive-or-extract", "remove-from-active-tree", "vendor-or-archive"}
)
FILE_LOCAL_ONLY_ACTIONS = frozenset({"keep-local-only"})


def _run_script(script: Path, args: list[str]) -> int:
    return subprocess.run([sys.executable, str(script), *args], cwd=str(script.parent), check=False).returncode


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _pad_root(repo_root: Path) -> Path:
    return repo_root / DEFAULT_PAD_ROOT


def _pad_dir(repo_root: Path, agent_id: str) -> Path:
    return _pad_root(repo_root) / agent_id


def _manifest_path(pad_dir: Path) -> Path:
    return pad_dir / "manifest.json"


def _ensure_agent_id(agent_id: str) -> bool:
    return bool(re.match(r"^[A-Za-z0-9._-]{2,64}$", agent_id))


def _resolve_pad_root(repo_root: Path, agent_root: str | None = None) -> Path:
    raw = Path(agent_root) if agent_root else DEFAULT_PAD_ROOT
    return raw if raw.is_absolute() else repo_root / raw


def _pad_dir_for_root(repo_root: Path, agent_id: str, agent_root: str | None = None) -> Path:
    return _resolve_pad_root(repo_root, agent_root) / agent_id


def _normalize_runtime_language(language: str | None) -> str | None:
    if not language:
        return None
    return RUNTIME_LANGUAGE_ALIASES.get(language.strip().lower())


def _infer_runtime_language_from_path(path: Path) -> str | None:
    return RUNTIME_EXTENSION_ALIASES.get(path.suffix.lower())


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_controlled_source_path(repo_root: Path, raw_path: str, extra_root: Path | None = None) -> Path:
    candidate = Path(raw_path).expanduser()
    resolved = candidate.resolve() if candidate.is_absolute() else (repo_root / candidate).resolve()
    allowed_roots = [repo_root.resolve()]
    if extra_root is not None:
        allowed_roots.append(extra_root.resolve())
    if any(_is_relative_to(resolved, root) for root in allowed_roots):
        return resolved
    raise ValueError(f"Path is outside the controlled SCBE workspace: {raw_path}")


def _resolve_runtime_argv_prefix(language: str) -> list[str]:
    runtime = _normalize_runtime_language(language)
    if runtime == "python":
        return [sys.executable]
    candidates = {
        "javascript": [["node"]],
        "typescript": [["tsx"], ["npx", "tsx"], ["npx.cmd", "tsx"]],
        "powershell": [["pwsh"], ["powershell"]],
        "bash": [["bash"]],
        "cmd": [["cmd.exe", "/c"], ["cmd", "/c"]],
    }.get(runtime or "", [])
    for candidate in candidates:
        exe = candidate[0]
        if Path(exe).is_file():
            return [exe, *candidate[1:]]
        resolved = shutil.which(exe)
        if resolved:
            return [resolved, *candidate[1:]]
    raise ValueError(f"No runtime executable found for language '{language}'")


def _load_tongues_module(repo_root: Path):
    global _TONGUES_MODULE
    if _TONGUES_MODULE is not None:
        return _TONGUES_MODULE
    module_path = repo_root / "six-tongues-cli.py"
    if not module_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("scbe_six_tongues_runtime", module_path)
    if not spec or not spec.loader:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _TONGUES_MODULE = module
    return module


def _load_action_map_module(repo_root: Path):
    global _ACTION_MAP_MODULE
    if _ACTION_MAP_MODULE is not None:
        return _ACTION_MAP_MODULE
    module_path = repo_root / "src" / "training" / "action_map_protocol.py"
    if not module_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("scbe_action_map_protocol_runtime", module_path)
    if not spec or not spec.loader:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _ACTION_MAP_MODULE = module
    return module


def _load_colab_catalog_module(repo_root: Path):
    global _COLAB_CATALOG_MODULE
    if _COLAB_CATALOG_MODULE is not None:
        return _COLAB_CATALOG_MODULE
    module_path = repo_root / "scripts" / "system" / "colab_workflow_catalog.py"
    if not module_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("scbe_colab_workflow_catalog_runtime", module_path)
    if not spec or not spec.loader:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _COLAB_CATALOG_MODULE = module
    return module


def _load_repo_ordering_module(repo_root: Path):
    global _REPO_ORDERING_MODULE
    if _REPO_ORDERING_MODULE is not None:
        return _REPO_ORDERING_MODULE
    module_path = repo_root / "scripts" / "system" / "repo_ordering.py"
    if not module_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("scbe_repo_ordering_runtime", module_path)
    if not spec or not spec.loader:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _REPO_ORDERING_MODULE = module
    return module


def _tongue_attestation(repo_root: Path, tongue: str, payload: bytes, max_tokens: int = 6) -> str:
    module = _load_tongues_module(repo_root)
    if module is None:
        return ""
    try:
        lex = module.Lexicons()
        tokenizer = module.TongueTokenizer(lex)
        return " ".join(tokenizer.encode_bytes(tongue.upper(), payload)[:max_tokens])
    except Exception:
        return ""


def _source_metadata(path: Path | None = None, text: str | None = None) -> dict[str, object]:
    if path is not None:
        raw = path.read_bytes()
        return {
            "kind": "file",
            "path": str(path),
            "length": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    material = (text or "").encode("utf-8")
    return {
        "kind": "inline",
        "length": len(material),
        "sha256": hashlib.sha256(material).hexdigest(),
    }


_SENSITIVE_ARG_FLAGS = frozenset(
    {
        "--secret",
        "--token",
        "--api-key",
        "--api-key-env",
        "--password",
        "--credential",
        "--auth",
    }
)


def _redact_argv(argv: list[str], limit: int = 8) -> list[str]:
    """Return a preview of argv with sensitive flag values masked."""
    preview: list[str] = []
    redact_next = False
    for arg in argv[:limit]:
        if redact_next:
            preview.append("***REDACTED***")
            redact_next = False
        elif arg.lower() in _SENSITIVE_ARG_FLAGS:
            preview.append(arg)
            redact_next = True
        elif "=" in arg and arg.split("=", 1)[0].lower() in _SENSITIVE_ARG_FLAGS:
            preview.append(arg.split("=", 1)[0] + "=***REDACTED***")
        else:
            preview.append(arg)
    return preview


def _command_metadata(repo_root: Path, tongue: str, argv: list[str]) -> dict[str, object]:
    raw = json.dumps(argv, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    return {
        "argc": len(argv),
        "argv_preview": _redact_argv(argv, limit=8),
        "sha256": digest.hex(),
        "tongue": tongue.upper(),
        "lexicon_attestation": _tongue_attestation(repo_root, tongue, digest[:12]),
    }


def _runtime_output_dir(repo_root: Path, output_dir: str) -> Path:
    path = Path(output_dir)
    return path if path.is_absolute() else repo_root / path


def _repo_path(repo_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else repo_root / path


def _context_config_path(repo_root: Path, raw_path: str | None = None) -> Path:
    path = Path(raw_path) if raw_path else DEFAULT_CLI_CONTEXT
    return path if path.is_absolute() else repo_root / path


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _normalize_extra_args(values: list[str] | None) -> list[str]:
    if not values:
        return []
    if values and values[0] == "--":
        return values[1:]
    return values


def _flow_slug(value: str, *, fallback: str = "flow-plan") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or fallback


def safe_text(value: object) -> str:
    return str(value or "").strip()


def _flow_agent_count() -> int:
    return len(FLOW_AGENT_BLUEPRINTS)


def _flow_fault_tolerance(agent_count: int) -> dict[str, int]:
    f = max(0, (agent_count - 1) // 3)
    return {
        "agent_count": agent_count,
        "byzantine_fault_tolerance": f,
        "minimum_quorum": max(1, 2 * f + 1),
    }


def _quasi_phase_seed(index: int) -> float:
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    return round((index * (phi - 1.0)) % 1.0, 6)


def _quasi_frequency_profile(index: int, total: int) -> dict[str, float]:
    phase_seed = _quasi_phase_seed(index)
    return {
        "phase_seed": phase_seed,
        "cadence_weight": round(0.55 + (phase_seed * 0.45), 6),
        "handoff_bias": round(1.0 + ((index + 1) / max(total, 1)), 6),
    }


def _formation_hexagonal(radius: float = 0.3) -> list[list[float]]:
    positions: list[list[float]] = []
    for i in range(_flow_agent_count()):
        angle = i * (2.0 * math.pi / _flow_agent_count())
        positions.append(
            [
                round(radius * math.cos(angle), 6),
                round(radius * math.sin(angle), 6),
                0.0,
            ]
        )
    return positions


def _formation_tetrahedral(radius: float = 0.3) -> list[list[float]]:
    return [
        [round(radius, 6), 0.0, 0.0],
        [round(-radius / 2.0, 6), round(radius * 0.866025, 6), 0.0],
        [round(-radius / 2.0, 6), round(-radius * 0.866025, 6), 0.0],
        [0.0, 0.0, round(radius * 1.633, 6)],
        [0.1, 0.1, round(-radius * 0.5, 6)],
        [-0.1, -0.1, round(-radius * 0.5, 6)],
    ]


def _formation_concentric(inner_radius: float = 0.2, outer_radius: float = 0.5) -> list[list[float]]:
    angles = [0.0, (2.0 * math.pi) / 3.0, (4.0 * math.pi) / 3.0]
    positions: list[list[float]] = []
    for angle in angles:
        positions.append(
            [
                round(inner_radius * math.cos(angle), 6),
                round(inner_radius * math.sin(angle), 6),
                0.0,
            ]
        )
    for angle in [math.pi / 3.0, math.pi, (5.0 * math.pi) / 3.0]:
        positions.append(
            [
                round(outer_radius * math.cos(angle), 6),
                round(outer_radius * math.sin(angle), 6),
                0.0,
            ]
        )
    return positions


def _formation_adaptive_scatter(task: str, radius: float = 0.45) -> list[list[float]]:
    seed = hashlib.sha256(task.encode("utf-8")).digest()
    positions: list[list[float]] = []
    for i in range(_flow_agent_count()):
        raw_a = seed[i]
        raw_b = seed[i + _flow_agent_count()]
        angle = (raw_a / 255.0) * (2.0 * math.pi)
        norm = 0.18 + (raw_b / 255.0) * radius
        z = round((((seed[i + 12] / 255.0) * 2.0) - 1.0) * 0.18, 6)
        positions.append(
            [
                round(norm * math.cos(angle), 6),
                round(norm * math.sin(angle), 6),
                z,
            ]
        )
    return positions


def _formation_positions(name: str, task: str) -> list[list[float]]:
    if name == "hexagonal":
        return _formation_hexagonal()
    if name == "tetrahedral":
        return _formation_tetrahedral()
    if name == "concentric":
        return _formation_concentric()
    if name == "adaptive-scatter":
        return _formation_adaptive_scatter(task)
    raise ValueError(f"Unsupported formation '{name}'")


def _build_flow_agents(formation: str, task: str) -> list[dict[str, object]]:
    positions = _formation_positions(formation, task)
    agents: list[dict[str, object]] = []
    for index, blueprint in enumerate(FLOW_AGENT_BLUEPRINTS):
        frequency = _quasi_frequency_profile(index, len(FLOW_AGENT_BLUEPRINTS))
        agents.append(
            {
                "slot": index,
                "agent_id": f"{blueprint['tongue'].lower()}-{_flow_slug(blueprint['role'])}",
                "tongue": blueprint["tongue"],
                "role": blueprint["role"],
                "purpose": blueprint["purpose"],
                "default_tools": list(blueprint["default_tools"]),
                "position": positions[index],
                "frequency": frequency,
                "handoff_tag": f"[{blueprint['tongue']}]",
            }
        )
    return agents


def _build_flow_steps(template_name: str, task: str, agents: list[dict[str, object]]) -> list[dict[str, object]]:
    role_index = {str(agent["role"]): agent for agent in agents}
    steps: list[dict[str, object]] = []
    for order, step in enumerate(FLOW_WORKFLOW_TEMPLATES[template_name]["steps"], start=1):
        owner = role_index[step["owner_role"]]
        steps.append(
            {
                "step_index": order,
                "id": step["id"],
                "name": step["name"],
                "task": task,
                "owner_role": step["owner_role"],
                "owner_tongue": owner["tongue"],
                "owner_agent_id": owner["agent_id"],
                "depends_on": list(step["depends_on"]),
                "deliverables": list(step["deliverables"]),
                "acceptance": step["acceptance"],
                "touched_layers": list(step["touched_layers"]),
                "handoff_tag": owner["handoff_tag"],
                "frequency": dict(owner["frequency"]),
            }
        )
    return steps


def _default_flow_output_path(repo_root: Path, task: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return repo_root / "artifacts" / "flow_plans" / f"{stamp}-{_flow_slug(task)}.json"


def _default_flow_packet_output_path(plan_path: Path) -> Path:
    return plan_path.parent.parent / "flow_packets" / f"{plan_path.stem}-packets.json"


def _load_flow_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_flow_plan_packet(payload: dict[str, object]) -> None:
    if payload.get("schema_version") != "scbe_flow_plan_v1":
        raise ValueError("Input file is not an SCBE flow plan packet.")


def _role_paths(owner_role: str) -> dict[str, list[str]]:
    config = FLOW_ROLE_PATHS.get(owner_role, {})
    return {
        "allowed": list(config.get("allowed", ["src", "scripts", "tests", "docs"])),
        "blocked": list(config.get("blocked", ["node_modules", "SCBE-AETHERMOORE-v3.0.0"])),
    }


def _default_cli_context() -> dict[str, object]:
    return {
        "schema_version": "scbe_cli_context_v1",
        "active_context": "",
        "defaults": {
            "workflow_dir": ".github/workflows",
            "n8n_dir": "workflows/n8n",
        },
        "contexts": {},
    }


def _load_cli_context(config_path: Path) -> dict[str, object]:
    if not config_path.exists():
        return _default_cli_context()
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _default_cli_context()
    base = _default_cli_context()
    base["active_context"] = safe_text(payload.get("active_context"))
    defaults = dict(base["defaults"])
    defaults.update(dict(payload.get("defaults") or {}))
    base["defaults"] = defaults
    base["contexts"] = dict(payload.get("contexts") or {})
    return base


def _save_cli_context(config_path: Path, payload: dict[str, object]) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _tool_presence() -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for tool_name, binary in CLI_TOOL_CHECKS:
        resolved = shutil.which(binary)
        result[tool_name] = {"available": bool(resolved), "path": resolved or ""}
    return result


def _json_result(args: argparse.Namespace, payload: dict[str, object], lines: list[str]) -> int:
    if getattr(args, "json_output", False):
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0
    for line in lines:
        print(line)
    return 0


def _count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _colab_catalog_payloads(repo_root: Path) -> list[dict[str, object]]:
    module = _load_colab_catalog_module(repo_root)
    if module is None:
        return []
    return list(module.list_notebook_payloads())


def _colab_notebook_payload(repo_root: Path, name: str) -> dict[str, object]:
    module = _load_colab_catalog_module(repo_root)
    if module is None:
        raise KeyError("colab workflow catalog unavailable")
    return dict(module.resolve_notebook_payload(name))


def _colab_bridge_status(repo_root: Path) -> dict[str, object]:
    bridge_note = repo_root / "notes" / "round-table" / "2026-03-19-colab-bridge-established.md"
    spin_note = repo_root / "notes" / "round-table" / "2026-03-20-spin-conversation-combat-research-mode.md"
    cell_index = repo_root / "artifacts" / "colab_bridge" / "notebook_cell_index.json"
    sft_records = repo_root / "training" / "sft_records" / "colab_bridge_sft.jsonl"
    return {
        "notes": {
            "bridge_note": str(bridge_note) if bridge_note.exists() else "",
            "spin_mode_note": str(spin_note) if spin_note.exists() else "",
        },
        "artifacts": {
            "cell_index": str(cell_index) if cell_index.exists() else "",
            "sft_records": str(sft_records) if sft_records.exists() else "",
        },
        "sft_record_count": _count_jsonl_rows(sft_records),
        "terminal_method_preferred": True,
        "multiline_cell_exec_supported": False,
    }


def _colab_bridge_script(repo_root: Path) -> Path:
    return repo_root / "external" / "codex-skills-live" / "scbe-n8n-colab-bridge" / "scripts" / "colab_n8n_bridge.py"


def _run_colab_bridge(
    repo_root: Path,
    bridge_args: list[str],
    *,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    script = _colab_bridge_script(repo_root)
    if not script.exists():
        raise FileNotFoundError(f"colab bridge script not found: {script}")
    env = os.environ.copy()
    if env_overrides:
        env.update({key: value for key, value in env_overrides.items() if value})
    return subprocess.run(
        [sys.executable, str(script), *bridge_args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _prepare_colab_bridge_secret_inputs(backend_url: str, token: str = "") -> tuple[str, dict[str, str]]:
    raw_url = str(backend_url or "").strip()
    token_value = str(token or "").strip()
    if not raw_url:
        return raw_url, {}
    try:
        parts = urlsplit(raw_url)
    except ValueError:
        return raw_url, {"SCBE_COLAB_BRIDGE_TOKEN": token_value} if token_value else {}
    query_token = "".join(parse_qs(parts.query).get("token", [""])).strip()
    if query_token and not token_value:
        token_value = query_token
    cleaned_url = raw_url
    if query_token:
        cleaned_url = urlunsplit((parts.scheme, parts.netloc, parts.path or "", "", "")).rstrip("/")
    env_overrides = {"SCBE_COLAB_BRIDGE_TOKEN": token_value} if token_value else {}
    return cleaned_url, env_overrides


def _load_notebook_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _colab_notebook_review(repo_root: Path) -> dict[str, object]:
    notebooks = _colab_catalog_payloads(repo_root)
    reviews: list[dict[str, object]] = []
    readiness_counts = {"ready": 0, "partial": 0, "review": 0}
    for row in notebooks:
        local_path = Path(str(row["local_path"]))
        warnings: list[str] = []
        review = {
            "name": row["name"],
            "category": row["category"],
            "path": row["path"],
            "exists": bool(row["exists"]),
            "readiness": "review",
            "cell_count": 0,
            "code_cells": 0,
            "markdown_cells": 0,
            "accelerator": "",
            "colab_name": "",
            "signals": {
                "google_drive_mount": False,
                "huggingface_push": False,
                "canonical_repo_clone": False,
                "demo_repo_clone": False,
            },
            "warnings": warnings,
        }
        if not local_path.exists():
            warnings.append("local notebook missing")
            reviews.append(review)
            readiness_counts["review"] += 1
            continue

        nb = _load_notebook_json(local_path)
        metadata = nb.get("metadata", {}) if isinstance(nb, dict) else {}
        cells = nb.get("cells", []) if isinstance(nb, dict) else []
        accelerator = str(metadata.get("accelerator") or metadata.get("colab", {}).get("gpuType", ""))
        colab_name = str(metadata.get("colab", {}).get("name", ""))
        code_cells = [cell for cell in cells if cell.get("cell_type") == "code"]
        markdown_cells = [cell for cell in cells if cell.get("cell_type") == "markdown"]
        combined_source = "\n".join(
            "".join(cell.get("source", [])) if isinstance(cell.get("source"), list) else str(cell.get("source", ""))
            for cell in cells
        )

        review["cell_count"] = len(cells)
        review["code_cells"] = len(code_cells)
        review["markdown_cells"] = len(markdown_cells)
        review["accelerator"] = accelerator
        review["colab_name"] = colab_name
        review["signals"] = {
            "google_drive_mount": "google.colab import drive" in combined_source or "/content/drive" in combined_source,
            "huggingface_push": "huggingface_hub" in combined_source
            or "push_to_hub" in combined_source
            or "HfApi" in combined_source,
            "canonical_repo_clone": "issdandavis/SCBE-AETHERMOORE" in combined_source,
            "demo_repo_clone": "issdandavis/scbe-aethermoore-demo" in combined_source.lower(),
        }

        if review["signals"]["demo_repo_clone"]:
            warnings.append("clones demo repo instead of canonical SCBE-AETHERMOORE")
        if review["category"] in {"training", "generation", "data"} and not accelerator:
            warnings.append("accelerator metadata missing for compute notebook")
        if not colab_name:
            warnings.append("colab display name missing")
        if review["category"] == "training" and not review["signals"]["huggingface_push"]:
            warnings.append("no explicit Hugging Face push or hub helper detected")

        if not warnings:
            review["readiness"] = "ready"
            readiness_counts["ready"] += 1
        elif len(warnings) <= 2:
            review["readiness"] = "partial"
            readiness_counts["partial"] += 1
        else:
            review["readiness"] = "review"
            readiness_counts["review"] += 1

        reviews.append(review)

    return {
        "schema_version": "scbe_colab_review_v1",
        "notebook_count": len(reviews),
        "readiness_counts": readiness_counts,
        "reviews": reviews,
    }


def _get_nested(payload: dict[str, object], dotted_key: str) -> object:
    current: object = payload
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(dotted_key)
        current = current[part]
    return current


def _set_nested(payload: dict[str, object], dotted_key: str, value: object) -> None:
    parts = dotted_key.split(".")
    current: dict[str, object] = payload
    for part in parts[:-1]:
        next_value = current.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            current[part] = next_value
        current = next_value
    current[parts[-1]] = value


def _parse_key_value(raw: str) -> tuple[str, str]:
    key, sep, value = raw.partition("=")
    if not sep:
        raise ValueError("Expected KEY=VALUE format")
    return safe_text(key), value


def _workflow_output_paths(
    repo_root: Path, config: dict[str, object], workflow_name: str, workflow_path: str, queue_path: str
) -> tuple[Path, Path]:
    defaults = dict(config.get("defaults") or {})
    workflow_dir = workflow_path or str(defaults.get("workflow_dir") or ".github/workflows")
    queue_dir = queue_path or str(defaults.get("n8n_dir") or "workflows/n8n")
    slug = _flow_slug(workflow_name)
    workflow_file = _repo_path(repo_root, workflow_dir)
    if workflow_file.suffix.lower() != ".yml":
        workflow_file = workflow_file / f"{slug}.yml"
    queue_file = _repo_path(repo_root, queue_dir)
    if queue_file.suffix.lower() != ".json":
        queue_file = queue_file / f"{slug}.queue.json"
    return workflow_file, queue_file


def _parse_workflow_steps(raw_steps: list[str]) -> list[dict[str, str]]:
    parsed: list[dict[str, str]] = []
    for index, raw in enumerate(raw_steps, start=1):
        label, sep, command = raw.partition("::")
        if not sep:
            raise ValueError("Workflow steps must use LABEL::COMMAND format")
        parsed.append(
            {
                "id": f"step_{index:02d}_{_flow_slug(label, fallback='step')}",
                "name": safe_text(label),
                "command": command.strip(),
            }
        )
    return parsed


def _yaml_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _render_workflow_yaml(
    name: str,
    triggers: list[str],
    cron: str,
    runs_on: str,
    shell: str,
    node_version: str,
    python_version: str,
    env_vars: dict[str, str],
    steps: list[dict[str, str]],
) -> str:
    lines = [f"name: {_yaml_quote(name)}", "on:"]
    if not triggers:
        triggers = ["workflow_dispatch"]
    for trigger in triggers:
        if trigger == "workflow_dispatch":
            lines.append("  workflow_dispatch:")
        elif trigger == "push":
            lines.append("  push:")
            lines.append("    branches: [main]")
        elif trigger == "pull_request":
            lines.append("  pull_request:")
            lines.append("    branches: [main]")
        elif trigger == "schedule":
            lines.append("  schedule:")
            lines.append(f"    - cron: {_yaml_quote(cron or '0 9 * * *')}")
    lines.extend(
        [
            "jobs:",
            "  orchestrate:",
            f"    runs-on: {runs_on}",
            "    steps:",
            "      - name: Checkout",
            "        uses: actions/checkout@v4",
            "      - name: Setup Node",
            "        uses: actions/setup-node@v4",
            "        with:",
            f"          node-version: {_yaml_quote(node_version)}",
            "      - name: Setup Python",
            "        uses: actions/setup-python@v5",
            "        with:",
            f"          python-version: {_yaml_quote(python_version)}",
        ]
    )
    if env_vars:
        lines.append("    env:")
        for key in sorted(env_vars):
            lines.append(f"      {key}: {_yaml_quote(env_vars[key])}")
    for step in steps:
        lines.extend(
            [
                f"      - name: {_yaml_quote(step['name'])}",
                f"        id: {step['id']}",
                f"        shell: {shell}",
                "        run: |",
            ]
        )
        for command_line in step["command"].splitlines():
            lines.append(f"          {command_line}")
    return "\n".join(lines) + "\n"


def _render_n8n_style_queue(
    name: str, workflow_path: Path, steps: list[dict[str, str]], triggers: list[str], env_vars: dict[str, str]
) -> dict[str, object]:
    items: list[dict[str, object]] = []
    for index, step in enumerate(steps, start=1):
        dependencies = [] if index == 1 else [steps[index - 2]["id"]]
        items.append(
            {
                "id": step["id"],
                "action": "command",
                "label": step["name"],
                "command": step["command"],
                "depends_on": dependencies,
                "metadata": {
                    "order": index,
                    "source": "scbe workflow styleize",
                    "github_workflow": str(workflow_path).replace("\\", "/"),
                },
            }
        )
    return {
        "schema_version": "scbe_n8_style_queue_v1",
        "workflow_name": name,
        "triggers": triggers or ["workflow_dispatch"],
        "env": env_vars,
        "items": items,
    }


def _step_support_cells(step: dict[str, object], count: int) -> list[dict[str, object]]:
    if count <= 0:
        return []
    cells: list[dict[str, object]] = []
    step_id = str(step["id"])
    for idx in range(count):
        tongue = FLOW_TONGUES[(int(step["step_index"]) + idx) % len(FLOW_TONGUES)]
        cells.append(
            {
                "cell_id": f"{step_id}-support-{idx + 1}",
                "tongue": tongue,
                "role": f"{step['owner_role']} Support",
                "purpose": f"Parallel assist cell for {step['name']}",
            }
        )
    return cells


def _build_work_packets(flow_packet: dict[str, object], support_units: int) -> list[dict[str, object]]:
    packets: list[dict[str, object]] = []
    task = str(flow_packet["task"])
    formation = str(flow_packet["formation"]["name"])
    workflow_template = str(flow_packet["workflow_template"])
    for step in flow_packet["steps"]:
        role = str(step["owner_role"])
        path_policy = _role_paths(role)
        packets.append(
            {
                "schema_version": "scbe_work_packet_v1",
                "task_id": f"{_flow_slug(task)}::{step['step_index']:02d}::{step['id']}",
                "step_id": step["id"],
                "step_name": step["name"],
                "task": task,
                "workflow_template": workflow_template,
                "formation": formation,
                "owner_role": role,
                "owner_agent_id": step["owner_agent_id"],
                "owner_tongue": step["owner_tongue"],
                "goal": f"{step['name']} for {task}",
                "inputs": {
                    "mission": task,
                    "deliverables": list(step["deliverables"]),
                    "depends_on": list(step["depends_on"]),
                    "touched_layers": list(step["touched_layers"]),
                    "frequency": dict(step["frequency"]),
                },
                "allowed_paths": path_policy["allowed"],
                "blocked_paths": path_policy["blocked"],
                "dependencies": list(step["depends_on"]),
                "commands_or_tools": [
                    "python scbe.py flow plan ...",
                    "python scripts/scbe-system-cli.py",
                    "haction-start / haction-step / haction-close / haction-build",
                ],
                "done_criteria": step["acceptance"],
                "return_format": {
                    "required": [
                        "summary",
                        "status",
                        "changed_files",
                        "artifacts",
                        "proof",
                        "next_action",
                    ],
                    "status_values": ["completed", "blocked", "needs_review"],
                },
                "support_cells": _step_support_cells(step, support_units),
                "telemetry": {
                    "lane": "system-cli",
                    "tool": "flow-packetize",
                    "skills": FLOW_SKILLS,
                },
            }
        )
    return packets


def _find_pad_app(manifest: dict, app_id: str | None = None, app_name: str | None = None) -> dict | None:
    apps = manifest.get("storage", {}).get("apps", [])
    if app_id:
        for app in apps:
            if app.get("id") == app_id:
                return app
    if app_name:
        needle = app_name.strip().lower()
        for app in apps:
            if str(app.get("name", "")).strip().lower() == needle:
                return app
    return None


def _execute_runtime(args: argparse.Namespace, *, app_entry: dict | None = None) -> int:
    output_dir = _runtime_output_dir(args.repo_root, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:12]
    agent_id = getattr(args, "agent_id", "") or ""
    pad_dir: Path | None = None
    manifest: dict | None = None
    if agent_id:
        if not _ensure_agent_id(agent_id):
            print("Invalid --agent-id. Use 2-64 chars: letters, numbers, . _ -")
            return 2
        pad_dir = _pad_dir_for_root(args.repo_root, agent_id, getattr(args, "agent_root", None))
        manifest_path = _manifest_path(pad_dir)
        if not manifest_path.exists():
            print("Pad not found. Run pollypad init first.")
            return 1
        manifest = _load_manifest(manifest_path)

    runtime_mode = "app" if app_entry is not None else "direct"
    source_path: Path | None = None
    source_text: str | None = None
    keep_source = bool(getattr(args, "keep_source", False))
    cleanup_source = False

    try:
        extra_args = _normalize_extra_args(getattr(args, "extra_args", []))
        if app_entry is not None:
            entrypoint = str(app_entry.get("entrypoint") or "").strip()
            if not entrypoint:
                print("App entrypoint is empty.")
                return 2
            command = shlex.split(entrypoint, posix=os.name != "nt")
            if not command:
                print("App entrypoint could not be parsed.")
                return 2
            if len(command) == 1 and app_entry.get("local_script"):
                local_script = (pad_dir / app_entry["local_script"]).resolve() if pad_dir else None
                if local_script and local_script.exists():
                    command.append(str(local_script))
                    source_path = local_script
            command.extend(extra_args)
            language = _normalize_runtime_language(getattr(args, "language", None))
            if not language and source_path is not None:
                language = _infer_runtime_language_from_path(source_path)
            tongue = (
                getattr(args, "tongue", None) or language and RUNTIME_TONGUE_BY_LANGUAGE.get(language) or "CA"
            ).upper()
            cwd = str(pad_dir or args.repo_root)
        else:
            if bool(getattr(args, "file", "")) == bool(getattr(args, "code", "")):
                print("Use exactly one of --file or --code.")
                return 2
            if getattr(args, "file", ""):
                source_path = _resolve_controlled_source_path(
                    args.repo_root,
                    args.file,
                    extra_root=pad_dir,
                )
                language = _normalize_runtime_language(
                    getattr(args, "language", None)
                ) or _infer_runtime_language_from_path(source_path)
                if not language:
                    print("Unable to infer --language from file extension. Set --language explicitly.")
                    return 2
            else:
                source_text = args.code
                language = _normalize_runtime_language(getattr(args, "language", None))
                if not language:
                    print("--language is required when using --code.")
                    return 2
                suffix = RUNTIME_FILE_SUFFIXES.get(language)
                if not suffix:
                    print(f"Unsupported language '{language}'.")
                    return 2
                temp_root = (pad_dir or output_dir / "inline") / ".scbe-runtime"
                temp_root.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    "w", encoding="utf-8", suffix=suffix, dir=str(temp_root), delete=False
                ) as handle:
                    handle.write(source_text)
                    source_path = Path(handle.name)
                cleanup_source = not keep_source

            prefix = _resolve_runtime_argv_prefix(language)
            command = [*prefix, str(source_path), *extra_args]
            tongue = (getattr(args, "tongue", None) or RUNTIME_TONGUE_BY_LANGUAGE.get(language) or "CA").upper()
            cwd = str((pad_dir if pad_dir else args.repo_root).resolve())

        child_env = os.environ.copy()
        child_env["SCBE_RUN_ID"] = run_id
        child_env["SCBE_RUN_TONGUE"] = tongue
        child_env["SCBE_RUN_MODE"] = runtime_mode
        child_env["SCBE_RUN_AGENT_ID"] = agent_id
        if pad_dir is not None:
            child_env["SCBE_POLLY_PAD_DIR"] = str(pad_dir.resolve())

        completed = subprocess.run(
            command,
            cwd=cwd,
            env=child_env,
            capture_output=True,
            text=True,
            timeout=args.timeout_seconds,
            check=False,
        )

        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)

        artifact = {
            "run_id": run_id,
            "executed_at": _now_iso(),
            "ok": completed.returncode == 0,
            "exit_code": completed.returncode,
            "mode": runtime_mode,
            "runtime_language": _normalize_runtime_language(getattr(args, "language", None))
            or (source_path and _infer_runtime_language_from_path(source_path))
            or "",
            "tongue": tongue,
            "agent_id": agent_id,
            "pad_manifest_path": str(_manifest_path(pad_dir)) if pad_dir is not None else None,
            "app": (
                {
                    "id": app_entry.get("id"),
                    "name": app_entry.get("name"),
                }
                if app_entry is not None
                else None
            ),
            "command_metadata": _command_metadata(args.repo_root, tongue, command),
            "source_metadata": (
                _source_metadata(text=source_text) if source_text is not None else _source_metadata(path=source_path)
            ),
            "stdout_metadata": _text_metadata(completed.stdout),
            "stderr_metadata": _text_metadata(completed.stderr),
            "working_directory": cwd,
        }
        artifact_path = output_dir / f"{run_id}_runtime.json"
        artifact_path.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
        return int(completed.returncode)
    except subprocess.TimeoutExpired as exc:
        artifact_path = output_dir / f"{run_id}_runtime.json"
        artifact_path.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "executed_at": _now_iso(),
                    "ok": False,
                    "exit_code": None,
                    "mode": runtime_mode,
                    "agent_id": agent_id,
                    "timed_out": True,
                    "timeout_seconds": args.timeout_seconds,
                    "stdout_metadata": _text_metadata(getattr(exc, "stdout", None)),
                    "stderr_metadata": _text_metadata(getattr(exc, "stderr", None)),
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        print(f"Runtime timed out after {args.timeout_seconds} seconds.", file=sys.stderr)
        return 124
    except ValueError as exc:
        print(str(exc))
        return 2
    finally:
        if cleanup_source and source_path is not None:
            try:
                source_path.unlink(missing_ok=True)
            except OSError:
                pass


def _load_manifest(manifest_path: Path) -> dict:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing pad manifest: {manifest_path}")
    with manifest_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_manifest(manifest_path: Path, data: dict) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def _agent_registry_path(repo_root: Path) -> Path:
    return repo_root / DEFAULT_AGENT_REGISTRY


def _read_env_file(repo_root: Path) -> dict[str, str]:
    env_path = repo_root / ".env"
    env: dict[str, str] = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def _load_agent_registry(registry_path: Path) -> dict[str, dict]:
    if not registry_path.exists():
        return {
            "version": "1.0.0",
            "agents": {},
        }
    with registry_path.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return {
                "version": "1.0.0",
                "agents": {},
            }
    if "agents" not in data or not isinstance(data["agents"], dict):
        data["agents"] = {}
    if "version" not in data:
        data["version"] = "1.0.0"
    return data


def _save_agent_registry(registry_path: Path, data: dict) -> None:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    clean = json.loads(json.dumps(data))
    for agent in clean.get("agents", {}).values():
        if not isinstance(agent, dict):
            continue
        for key in list(agent.keys()):
            lower = str(key).lower()
            if lower == "api_key_env":
                continue
            if any(fragment in lower for fragment in ("token", "secret", "password", "credential", "authorization")):
                agent.pop(key, None)
    with registry_path.open("w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2, sort_keys=True)


def _new_agent_entry(
    agent_id: str,
    provider: str,
    display_name: str,
    description: str,
    api_key_env: str | None = None,
    model: str | None = None,
    endpoint: str | None = None,
    notebook_url: str | None = None,
) -> dict:
    entry = {
        "agent_id": agent_id,
        "provider": provider,
        "display_name": display_name or agent_id,
        "description": description or "",
        "enabled": True,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "capabilities": [],
    }
    if api_key_env:
        entry["api_key_env"] = api_key_env
    if model:
        entry["model"] = model
    if endpoint:
        entry["endpoint"] = endpoint
    if notebook_url:
        entry["notebook_url"] = notebook_url
    return entry


def _text_metadata(value: str | None) -> dict[str, object]:
    text = str(value or "")
    return {
        "present": bool(text),
        "length": len(text),
        "pbkdf2_sha256": _sensitive_fingerprint(text) if text else "",
    }


_SECRET_RE = re.compile(
    r"(?:ghp_|gho_|ghu_|ghs_|ghr_|hf_|sk-|sk-proj-|xai-|rk_live_|rk_test_|shpat_|AKIA)[A-Za-z0-9_\-]{8,}",
)


def _redact_sensitive_text(text: str | None) -> str:
    if not text:
        return ""
    return _SECRET_RE.sub("[REDACTED]", str(text))


def _sensitive_fingerprint(text: str) -> str:
    salt = os.getenv("SCBE_METADATA_HASH_KEY", "scbe-system-cli-metadata").encode("utf-8")
    return hashlib.pbkdf2_hmac(
        "sha256",
        text.encode("utf-8"),
        salt,
        SENSITIVE_METADATA_ITERATIONS,
    ).hex()


def _sanitize_agent_result_for_storage(result: dict) -> dict:
    clean = {key: value for key, value in result.items() if key not in {"raw", "content", "prompt", "error"}}
    if "content" in result:
        clean["content_metadata"] = _text_metadata(result.get("content"))
    if "error" in result:
        clean["error_metadata"] = _text_metadata(result.get("error"))
    if "prompt" in result:
        clean["prompt_metadata"] = _text_metadata(result.get("prompt"))
    return clean


def _sanitize_agent_result_for_disk(result: dict) -> dict:
    clean = {key: value for key, value in result.items() if key not in {"raw", "content", "prompt", "error"}}
    for field in ("content", "prompt", "error"):
        if field not in result:
            continue
        text = str(result.get(field) or "")
        clean[f"{field}_char_count"] = len(text)
        clean[f"{field}_pbkdf2_sha256"] = _sensitive_fingerprint(text) if text else ""
    return clean


def _resolve_agent_api_key(agent: dict, env_cache: dict[str, str]) -> tuple[str | None, str | None]:
    env_var = agent.get("api_key_env")
    if not env_var:
        provider = (agent.get("provider") or "").lower()
        env_var = (
            "ANTHROPIC_API_KEY"
            if provider == "anthropic"
            else "OPENAI_API_KEY" if provider == "openai" else "GOOGLE_API_KEY" if provider == "gemini" else None
        )
    if not env_var:
        return None, None
    return os.environ.get(env_var) or env_cache.get(env_var), env_var


def _call_openai_agent(agent: dict, prompt: str, output_dir: Path, env_cache: dict[str, str], max_tokens: int) -> dict:
    provider = (agent.get("provider") or "openai").lower()
    if provider != "openai":
        return {
            "ok": False,
            "agent_id": agent.get("agent_id"),
            "provider": provider,
            "error": f"OpenAI REST path is only for openai provider, got {provider}",
        }
    api_key, env_key = _resolve_agent_api_key(agent, env_cache)
    if not api_key:
        return {
            "ok": False,
            "agent_id": agent.get("agent_id"),
            "provider": provider,
            "error": f"Missing API key. Set {env_key or 'OPENAI_API_KEY'} and retry.",
        }
    model = agent.get("model") or "gpt-4o-mini"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an SCBE-AETHERMOORE coordination agent."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
    }
    req = Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
        response_obj = json.loads(raw)
        choices = response_obj.get("choices") or []
        content = ""
        if choices:
            msg = choices[0].get("message") or {}
            content = msg.get("content") or ""
        return {
            "ok": True,
            "agent_id": agent.get("agent_id"),
            "provider": provider,
            "model": model,
            "raw": response_obj,
            "content": content,
            "output_path": str((output_dir / f"{agent.get('agent_id')}_openai.json").resolve()) if output_dir else None,
        }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore") if getattr(exc, "read", None) else ""
        body_summary = _text_metadata(_redact_sensitive_text(body))
        return {
            "ok": False,
            "agent_id": agent.get("agent_id"),
            "provider": provider,
            "error": f"HTTP {exc.code}: upstream_error body_present={body_summary['present']} body_length={body_summary['length']}",
        }
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "ok": False,
            "agent_id": agent.get("agent_id"),
            "provider": provider,
            "error": _redact_sensitive_text(str(exc)),
        }


def _write_agent_call_result(output_dir: Path, agent_id: str, result: dict) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{agent_id}_agent_call.json"
    path.write_text(json.dumps(_sanitize_agent_result_for_storage(result), indent=2, sort_keys=True), encoding="utf-8")
    return str(path)


def _route_agent_call(agent: dict, prompt: str, output_dir: Path, env_cache: dict[str, str], max_tokens: int) -> dict:
    provider = (agent.get("provider") or "").lower()
    if provider in {"openai", "openai-compatible", ""}:
        return _call_openai_agent(agent, prompt, output_dir, env_cache, max_tokens)
    if provider in {"notebooklm", "notebooklm-web", "notebooklm-ui"}:
        return _notebooklm_fallback(agent, prompt, output_dir)
    return {
        "ok": False,
        "agent_id": agent.get("agent_id"),
        "provider": provider or "unknown",
        "error": f"Unsupported provider '{provider}'. Supported providers: openai, notebooklm.",
    }


def _notebooklm_fallback(agent: dict, prompt: str, output_dir: Path) -> dict:
    notebook_url = agent.get("notebook_url") or DEFAULT_NOTEBOOKLM_URL
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{agent.get('agent_id')}_notebooklm.json"
    result = {
        "ok": False,
        "agent_id": agent.get("agent_id"),
        "provider": "notebooklm-web",
        "mode": "manual",
        "message": (
            "NotebookLM has no documented public REST API endpoint in this code path. "
            "Use the web UI with the notebook id and paste this prompt."
        ),
        "prompt_metadata": _text_metadata(prompt),
        "notebook_url": notebook_url,
        "generated_at": _now_iso(),
    }
    path.write_text(json.dumps(_sanitize_agent_result_for_storage(result), indent=2, sort_keys=True), encoding="utf-8")
    result["output_path"] = str(path)
    return result


def _new_manifest(agent_id: str, name: str, role: str, owner: str, max_mb: int) -> dict:
    return {
        "agent_id": agent_id,
        "name": name or agent_id,
        "role": role or "",
        "owner": owner or "",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "storage": {
            "max_bytes": max_mb * 1024 * 1024,
            "notes_count": 0,
            "books_count": 0,
            "apps_count": 0,
            "notes": [],
            "books": [],
            "apps": [],
        },
        "utilities": [],
        "flux_state_hint": "polly",
    }


def _touch_note_file(pad_dir: Path, title: str, content: str) -> Path:
    notes_dir = pad_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    note_id = uuid.uuid4().hex[:10]
    safe_title = re.sub(r"[^A-Za-z0-9._-]+", "-", title.strip().lower())[:35].strip("-") or "note"
    filename = f"{safe_title}-{note_id}.md"
    path = notes_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


def cmd_pollypad_init(args: argparse.Namespace) -> int:
    if not _ensure_agent_id(args.agent_id):
        print("Invalid --agent-id. Use 2-64 chars: letters, numbers, . _ -")
        return 2
    pad_dir = _pad_dir(args.repo_root, args.agent_id)
    manifest_path = _manifest_path(pad_dir)
    if pad_dir.exists() and not args.force:
        print(f"Pad already exists: {pad_dir}")
        return 1

    manifest = _new_manifest(
        args.agent_id,
        args.name,
        args.role,
        args.owner,
        max_mb=args.max_storage_mb,
    )
    _save_manifest(manifest_path, manifest)
    for folder in ["notes", "books", "apps", "assets"]:
        (pad_dir / folder).mkdir(parents=True, exist_ok=True)
    print(f"Created Polly Pad for {args.agent_id}")
    print(f"Path: {pad_dir}")
    print(f"Manifest: {manifest_path}")
    return 0


def cmd_pollypad_list(args: argparse.Namespace) -> int:
    root = _pad_root(args.repo_root)
    if not root.exists():
        print("No polly pads configured yet.")
        return 0
    for path in sorted(root.iterdir()):
        if not path.is_dir():
            continue
        manifest_file = path / "manifest.json"
        if not manifest_file.exists():
            print(f"{path.name}: (missing manifest)")
            continue
        try:
            manifest = _load_manifest(manifest_file)
            print(
                f"{manifest.get('agent_id', path.name)} | "
                f"{manifest.get('name', '')} | role={manifest.get('role', 'unknown')} | "
                f"notes={manifest.get('storage', {}).get('notes_count', 0)} "
                f"books={manifest.get('storage', {}).get('books_count', 0)} "
                f"apps={manifest.get('storage', {}).get('apps_count', 0)}"
            )
        except Exception as exc:  # pragma: no cover - best-effort CLI readability
            print(f"{path.name}: manifest read error ({exc})")
    return 0


def cmd_pollypad_note_add(args: argparse.Namespace) -> int:
    pad_dir = _pad_dir(args.repo_root, args.agent_id)
    manifest_file = _manifest_path(pad_dir)
    if not manifest_file.exists():
        print("Pad not found. Run pollypad init first.")
        return 1
    if args.text is None and args.file is None:
        print("Use --text or --file to add note content.")
        return 2
    if args.text is not None and args.file is not None:
        print("Use only one of --text or --file.")
        return 2
    content = args.text if args.text is not None else Path(args.file).read_text(encoding="utf-8")
    path = _touch_note_file(pad_dir, args.title, content)
    manifest = _load_manifest(manifest_file)
    entry = {
        "id": uuid.uuid4().hex,
        "title": args.title,
        "path": f"notes/{path.name}",
        "updated_at": _now_iso(),
        "tags": args.tags or [],
    }
    manifest["storage"]["notes"].append(entry)
    manifest["storage"]["notes_count"] = len(manifest["storage"]["notes"])
    manifest["updated_at"] = _now_iso()
    _save_manifest(manifest_file, manifest)
    print(f"Saved note: {path}")
    return 0


def cmd_pollypad_note_list(args: argparse.Namespace) -> int:
    pad_dir = _pad_dir(args.repo_root, args.agent_id)
    manifest = _load_manifest(_manifest_path(pad_dir))
    for note in manifest.get("storage", {}).get("notes", []):
        print(f"{note['id']} | {note['title']} | {note['updated_at']} | {note['path']}")
    if not manifest.get("storage", {}).get("notes"):
        print("No notes yet.")
    return 0


def cmd_pollypad_book_add(args: argparse.Namespace) -> int:
    pad_dir = _pad_dir(args.repo_root, args.agent_id)
    manifest_file = _manifest_path(pad_dir)
    if not manifest_file.exists():
        print("Pad not found. Run pollypad init first.")
        return 1
    src = Path(args.path)
    if not src.exists():
        print(f"Missing source: {src}")
        return 2
    books_dir = pad_dir / "books"
    books_dir.mkdir(parents=True, exist_ok=True)
    target = books_dir / f"{uuid.uuid4().hex}_{src.name}"
    shutil.copy2(src, target)
    manifest = _load_manifest(manifest_file)
    manifest["storage"]["books"].append(
        {
            "id": uuid.uuid4().hex,
            "title": args.title or src.name,
            "source_path": str(src),
            "pad_path": str(target.relative_to(pad_dir)),
            "added_at": _now_iso(),
        }
    )
    manifest["storage"]["books_count"] = len(manifest["storage"]["books"])
    manifest["updated_at"] = _now_iso()
    _save_manifest(manifest_file, manifest)
    print(f"Added book: {target}")
    return 0


def cmd_pollypad_book_list(args: argparse.Namespace) -> int:
    manifest = _load_manifest(_manifest_path(_pad_dir(args.repo_root, args.agent_id)))
    for item in manifest.get("storage", {}).get("books", []):
        print(f"{item['id']} | {item['title']} | {item['pad_path']}")
    if not manifest.get("storage", {}).get("books"):
        print("No books yet.")
    return 0


def cmd_pollypad_app_install(args: argparse.Namespace) -> int:
    pad_dir = _pad_dir(args.repo_root, args.agent_id)
    manifest_file = _manifest_path(pad_dir)
    if not manifest_file.exists():
        print("Pad not found. Run pollypad init first.")
        return 1
    apps_dir = pad_dir / "apps"
    apps_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "id": uuid.uuid4().hex,
        "name": args.name,
        "description": args.description or "",
        "entrypoint": args.entrypoint,
        "installed_at": _now_iso(),
    }
    if args.script:
        src = Path(args.script)
        if not src.exists():
            print(f"Missing script: {src}")
            return 2
        target = apps_dir / src.name
        shutil.copy2(src, target)
        entry["local_script"] = str(target.relative_to(pad_dir))
    manifest = _load_manifest(manifest_file)
    manifest["storage"]["apps"].append(entry)
    manifest["storage"]["apps_count"] = len(manifest["storage"]["apps"])
    manifest["updated_at"] = _now_iso()
    _save_manifest(manifest_file, manifest)
    print(f"Installed app: {args.name}")
    return 0


def cmd_pollypad_app_list(args: argparse.Namespace) -> int:
    manifest = _load_manifest(_manifest_path(_pad_dir(args.repo_root, args.agent_id)))
    for item in manifest.get("storage", {}).get("apps", []):
        print(f"{item['id']} | {item['name']} | {item['description']} | {item['entrypoint']}")
    if not manifest.get("storage", {}).get("apps"):
        print("No apps yet.")
    return 0


def cmd_pollypad_app_run(args: argparse.Namespace) -> int:
    pad_dir = _pad_dir_for_root(args.repo_root, args.agent_id, getattr(args, "agent_root", None))
    manifest = _load_manifest(_manifest_path(pad_dir))
    app = _find_pad_app(manifest, getattr(args, "app_id", None), getattr(args, "name", None))
    if app is None:
        print("App not found in Polly Pad.")
        return 2
    runtime_args = argparse.Namespace(**vars(args))
    runtime_args.app_name = app.get("name")
    return _execute_runtime(runtime_args, app_entry=app)


def cmd_pollypad_snapshot(args: argparse.Namespace) -> int:
    pad_path = _pad_dir(args.repo_root, args.agent_id)
    manifest_path = _manifest_path(pad_path)
    if not manifest_path.exists():
        print("Pad not found. Run pollypad init first.")
        return 1
    manifest = _load_manifest(manifest_path)
    output = args.output or str(pad_path / "snapshot.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    print(f"Snapshot saved: {output}")
    return 0


def cmd_tongues(args: argparse.Namespace) -> int:
    script = args.repo_root / "six-tongues-cli.py"
    if not script.exists():
        print(f"Missing tongues CLI: {script}")
        return 1
    if args.tongue_args == ["selftest"]:
        return _run_script(script, [])
    if not args.tongue_args:
        print("No six-tongue subcommand provided. Try:")
        print("  tongues encode --tongue KO --in input.bin")
        print("  tongues xlate --src KO --dst AV")
        return 2
    return _run_script(script, args.tongue_args)


def cmd_runtime_run(args: argparse.Namespace) -> int:
    app_entry = None
    if getattr(args, "app_id", None) or getattr(args, "app_name", None):
        if not getattr(args, "agent_id", None):
            print("--agent-id is required when running a Polly Pad app.")
            return 2
        pad_dir = _pad_dir_for_root(args.repo_root, args.agent_id, getattr(args, "agent_root", None))
        manifest = _load_manifest(_manifest_path(pad_dir))
        app_entry = _find_pad_app(manifest, getattr(args, "app_id", None), getattr(args, "app_name", None))
        if app_entry is None:
            print("App not found in Polly Pad.")
            return 2
    return _execute_runtime(args, app_entry=app_entry)


def cmd_gap_review(args: argparse.Namespace) -> int:
    script = args.repo_root / "scripts" / "notion_pipeline_gap_review.py"
    if not script.exists():
        print(f"Missing gap review script: {script}")
        return 1
    extra = [
        "--repo-root",
        str(args.repo_root),
        "--sync-config",
        str(args.sync_config),
        "--pipeline-config",
        str(args.pipeline_config),
        "--training-data",
        str(args.training_data),
        "--output",
        str(args.output),
        "--summary-path",
        str(args.summary_path),
    ]
    return _run_script(script, extra)


def cmd_self_improve(args: argparse.Namespace) -> int:
    gap_report = args.gap_report
    if args.run_gap:
        gap_script = args.repo_root / "scripts" / "notion_pipeline_gap_review.py"
        if not gap_script.exists():
            print(f"Missing gap review script: {gap_script}")
            return 1
        gap_report = args.output.parent / "self_improvement_notion_gap.json"
        gap_args = [
            "--repo-root",
            str(args.repo_root),
            "--sync-config",
            str(args.sync_config),
            "--pipeline-config",
            str(args.pipeline_config),
            "--training-data",
            str(args.training_data),
            "--output",
            str(gap_report),
            "--summary-path",
            str(gap_report.with_suffix(".md")),
        ]
        rc = _run_script(gap_script, gap_args)
        if rc != 0:
            return rc

    script = args.repo_root / "scripts" / "self_improvement_orchestrator.py"
    if not script.exists():
        print(f"Missing orchestrator script: {script}")
        return 1
    extra = [
        "--mode",
        args.mode,
        "--coherence-report",
        str(args.coherence_report),
        "--training-data",
        str(args.training_data),
        "--pipeline-config",
        str(args.pipeline_config),
        "--output",
        str(args.output),
        "--summary-path",
        str(args.summary),
    ]
    if gap_report:
        extra.extend(["--notion-gap-report", str(gap_report)])
    return _run_script(script, extra)


def cmd_web(args: argparse.Namespace) -> int:
    script = args.repo_root / "scripts" / "agentic_web_tool.py"
    if not script.exists():
        print(f"Missing web tool script: {script}")
        return 1
    base = [
        "--engine",
        args.engine,
        "--output-dir",
        str(args.output_dir),
    ]
    if args.web_cmd == "search":
        if not args.query:
            print("Missing --query")
            return 2
        base.extend(["search", "--query", args.query, "--max-results", str(args.max_results)])
    elif args.web_cmd == "capture":
        if not args.url:
            print("Missing --url")
            return 2
        base.extend(["capture", "--url", args.url])
    else:
        print("Unknown web command")
        return 2
    return _run_script(script, base)


def cmd_antivirus(args: argparse.Namespace) -> int:
    script = args.repo_root / "scripts" / "agentic_antivirus.py"
    if not script.exists():
        print(f"Missing antivirus script: {script}")
        return 1
    return _run_script(
        script,
        [
            "--repo-root",
            str(args.repo_root),
            "--output",
            str(args.output),
            "--summary",
            str(args.summary),
            "--ring-core",
            str(args.ring_core),
            "--ring-outer",
            str(args.ring_outer),
            *(["--geoseal"] if args.geoseal else []),
        ],
    )


def cmd_aetherauth(args: argparse.Namespace) -> int:
    script = args.repo_root / "scripts" / "agentic_aetherauth.py"
    if not script.exists():
        print(f"Missing aetherauth script: {script}")
        return 1

    command = [
        "--action",
        args.action,
        "--core-max",
        str(args.core_max),
        "--outer-max",
        str(args.outer_max),
        "--max-time-skew-ms",
        str(args.max_time_skew_ms),
        "--output",
        str(args.output),
        "--summary",
        str(args.summary),
    ]
    if args.context_json:
        command.extend(["--context-json", args.context_json])
    if args.context_vector:
        command.extend(["--context-vector", args.context_vector])
    if args.reference_vector:
        command.extend(["--reference-vector", args.reference_vector])
    if args.time_ms:
        command.extend(["--time-ms", str(args.time_ms)])
    if args.latitude is not None:
        command.extend(["--latitude", str(args.latitude)])
    if args.longitude is not None:
        command.extend(["--longitude", str(args.longitude)])
    if args.reference_latitude is not None:
        command.extend(["--reference-latitude", str(args.reference_latitude)])
    if args.reference_longitude is not None:
        command.extend(["--reference-longitude", str(args.reference_longitude)])
    if args.trusted_radius_km is not None:
        command.extend(["--trusted-radius-km", str(args.trusted_radius_km)])
    if args.location_core_radius_km is not None:
        command.extend(["--location-core-radius-km", str(args.location_core_radius_km)])
    if args.location_outer_radius_km is not None:
        command.extend(["--location-outer-radius-km", str(args.location_outer_radius_km)])
    if args.location_core_max is not None:
        command.extend(["--location-core-max", str(args.location_core_max)])
    if args.location_outer_max is not None:
        command.extend(["--location-outer-max", str(args.location_outer_max)])
    if args.enforce_location:
        command.extend(["--enforce-location"])
    if args.cpu is not None:
        command.extend(["--cpu", str(args.cpu)])
    if args.memory is not None:
        command.extend(["--memory", str(args.memory)])
    if args.intent is not None:
        command.extend(["--intent", str(args.intent)])
    if args.history is not None:
        command.extend(["--history", str(args.history)])
    if args.secret:
        command.extend(["--secret", args.secret])
    if args.signature:
        command.extend(["--signature", args.signature])
    return _run_script(script, command)


def cmd_agent_bootstrap(args: argparse.Namespace) -> int:
    registry_path = _agent_registry_path(args.repo_root)
    registry = _load_agent_registry(registry_path)
    current_agents = registry.get("agents", {})

    if current_agents and not args.append and not args.force:
        print(f"Agent registry already exists with {len(current_agents)} agent(s): {', '.join(sorted(current_agents))}")
        print("Use --append to add defaults or --force to replace.")
        return 2

    seed_agents: dict[str, dict] = {}
    seed_agents["codex"] = _new_agent_entry(
        agent_id="codex",
        provider="openai",
        display_name="Codex",
        description=("General-purpose coding and architecture agent using OpenAI Chat Completions API."),
        api_key_env="OPENAI_API_KEY",
        model=args.codex_model or "gpt-4o-mini",
    )
    if args.include_notebooklm:
        seed_agents["notebooklm-main"] = _new_agent_entry(
            agent_id="notebooklm-main",
            provider="notebooklm",
            display_name="NotebookLM",
            description="Research and reflection assistant through NotebookLM.",
            notebook_url=DEFAULT_NOTEBOOKLM_URL,
        )

    if args.force and not args.append:
        registry["agents"] = {}
        current_agents = {}

    for aid, entry in seed_agents.items():
        if not args.force and not args.append and not current_agents.get(aid):
            current_agents[aid] = entry
        elif args.force or args.append or aid not in current_agents:
            current_agents[aid] = entry
        else:
            print(f"Skipping existing agent '{aid}' (use --force to overwrite).")

    registry["agents"] = current_agents
    registry["version"] = "1.0.0"
    _save_agent_registry(registry_path, registry)
    print(f"Agent registry written: {registry_path}")
    for aid, entry in sorted(current_agents.items()):
        print(f" - {aid}: {entry.get('provider')} ({entry.get('display_name')})")
    return 0


def cmd_agent_list(args: argparse.Namespace) -> int:
    registry = _load_agent_registry(_agent_registry_path(args.repo_root))
    agents = registry.get("agents", {})
    if not agents:
        print("No agents registered. Run: scbe-system agent bootstrap")
        return 0
    print(f"Agent registry: {len(agents)} entries")
    for aid in sorted(agents):
        entry = agents[aid]
        status = "enabled" if entry.get("enabled", True) else "disabled"
        print(f"{aid:24} | {entry.get('provider', 'unknown'):<12} | " f"{entry.get('display_name', ''):<18} | {status}")
    return 0


def cmd_agent_remove(args: argparse.Namespace) -> int:
    registry_path = _agent_registry_path(args.repo_root)
    registry = _load_agent_registry(registry_path)
    if args.agent_id not in registry.get("agents", {}):
        print(f"Agent '{args.agent_id}' not found")
        return 2
    registry["agents"].pop(args.agent_id, None)
    _save_agent_registry(registry_path, registry)
    print(f"Removed agent '{args.agent_id}' from {registry_path}")
    return 0


def cmd_agent_register(args: argparse.Namespace) -> int:
    if not _ensure_agent_id(args.agent_id):
        print("Invalid agent_id. Use 2-64 chars [A-Za-z0-9._-]")
        return 2

    registry_path = _agent_registry_path(args.repo_root)
    registry = _load_agent_registry(registry_path)
    providers = {"openai", "notebooklm"}
    if args.provider not in providers:
        print(f"Unsupported provider '{args.provider}'. Use {', '.join(sorted(providers))}")
        return 2

    capabilities = [c.strip() for c in args.capabilities.split(",")] if args.capabilities else []
    if args.provider == "openai" and not args.api_key_env:
        args.api_key_env = "OPENAI_API_KEY"

    entry = _new_agent_entry(
        agent_id=args.agent_id,
        provider=args.provider,
        display_name=args.display_name,
        description=args.description,
        api_key_env=args.api_key_env,
        model=args.model,
        endpoint=args.endpoint,
        notebook_url=args.notebook_url,
    )
    if capabilities:
        entry["capabilities"] = capabilities

    registry.setdefault("agents", {})[args.agent_id] = entry
    registry["version"] = "1.0.0"
    _save_agent_registry(registry_path, registry)
    print(f"Registered agent '{args.agent_id}' ({args.provider})")
    return 0


def cmd_agent_ping(args: argparse.Namespace) -> int:
    env_cache = _read_env_file(args.repo_root)
    registry = _load_agent_registry(_agent_registry_path(args.repo_root))
    agent_id = args.agent_id
    if agent_id == "__all__":
        candidates = [a for a, entry in registry.get("agents", {}).items() if entry.get("enabled", True)]
    else:
        entry = registry.get("agents", {}).get(agent_id)
        if not entry:
            print(f"Unknown agent '{agent_id}'")
            return 2
        candidates = [agent_id]

    if not candidates:
        print("No enabled agents available.")
        return 0

    print("Pinging agents...")
    out_dir = Path(args.output_dir)
    for aid in candidates:
        entry = registry["agents"][aid]
        result = _route_agent_call(
            entry,
            "Reply with one line: 'SCBE ping OK'.",
            out_dir,
            env_cache,
            args.max_tokens,
        )
        output_path = _write_agent_call_result(out_dir, f"{aid}_ping", result)
        result["output_path"] = output_path
        print(f"{aid:20} -> {'OK' if result.get('ok') else 'FAILED'}")
    return 0


def cmd_agent_call(args: argparse.Namespace) -> int:
    registry = _load_agent_registry(_agent_registry_path(args.repo_root))
    env_cache = _read_env_file(args.repo_root)
    out_dir = Path(args.output_dir)

    if args.all:
        agent_ids = [a for a, entry in registry.get("agents", {}).items() if entry.get("enabled", True)]
    else:
        agent_ids = [s.strip() for s in args.agent_id.split(",") if s.strip()]

    if not agent_ids:
        print("No agents specified. Use --all or --agent-id.")
        return 2

    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    else:
        prompt = args.prompt

    if not prompt:
        print("Missing prompt. Provide --prompt or --prompt-file.")
        return 2

    summary = {
        "called_at": _now_iso(),
        "prompt_metadata": _text_metadata(prompt),
        "agents": {},
        "succeeded": 0,
        "failed": 0,
    }
    for aid in agent_ids:
        entry = registry.get("agents", {}).get(aid)
        if not entry:
            summary["agents"][aid] = {"ok": False, "error": "agent not found"}
            summary["failed"] += 1
            continue
        if not entry.get("enabled", True):
            summary["agents"][aid] = {"ok": False, "error": "agent disabled"}
            summary["failed"] += 1
            continue
        result = _route_agent_call(entry, prompt, out_dir, env_cache, args.max_tokens)
        result["agent_id"] = aid
        result_path = _write_agent_call_result(out_dir, aid, result)
        result["output_path"] = result_path
        summary["agents"][aid] = {"ok": result.get("ok", False), "output_path": result_path}
        if result.get("ok"):
            summary["succeeded"] += 1
            if args.show_output:
                print(f"\n[{aid}]")
                print(json.dumps({"content_metadata": _text_metadata(result.get("content", ""))}, indent=2))
        else:
            summary["failed"] += 1
            if args.show_output:
                print(f"[{aid}] FAIL")
                print(json.dumps({"error_metadata": _text_metadata(result.get("error", ""))}, indent=2))

    summary_path = out_dir / "agent_call_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(_sanitize_agent_result_for_storage(summary), indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"Summary: {summary['succeeded']} ok, {summary['failed']} failed")
    print(f"Saved: {summary_path}")
    return 0 if summary["failed"] == 0 else 1


def cmd_flow_plan(args: argparse.Namespace) -> int:
    repo_root = args.repo_root
    template_name = args.workflow_template
    if template_name not in FLOW_WORKFLOW_TEMPLATES:
        print(f"Unknown workflow template '{template_name}'")
        return 2

    agents = _build_flow_agents(args.formation, args.task)
    steps = _build_flow_steps(template_name, args.task, agents)
    fault_tolerance = _flow_fault_tolerance(len(agents))
    quasi_mesh = {
        "mode": "golden-weave",
        "formation": args.formation,
        "routing_basis": "six-tongue + quasi-phase cadence",
        "phase_seeds": [agent["frequency"]["phase_seed"] for agent in agents],
    }

    output_path = _repo_path(repo_root, args.output) if args.output else _default_flow_output_path(repo_root, args.task)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    flow_packet: dict[str, object] = {
        "schema_version": "scbe_flow_plan_v1",
        "generated_at": _now_iso(),
        "task": args.task,
        "workflow_template": template_name,
        "workflow_summary": FLOW_WORKFLOW_TEMPLATES[template_name]["summary"],
        "formation": {
            "name": args.formation,
            "agent_count": len(agents),
            "fault_tolerance": fault_tolerance,
        },
        "quasi_mesh": quasi_mesh,
        "agents": agents,
        "steps": steps,
        "action_map": {},
    }

    if args.emit_action_map:
        action_map = _load_action_map_module(repo_root)
        if action_map is None:
            print("Action-map protocol is unavailable.")
            return 2
        action_root = _repo_path(repo_root, args.action_root)
        action_root.mkdir(parents=True, exist_ok=True)
        start = action_map.start_run(
            action_root,
            task=args.task,
            summary=f"Planned {template_name} flow in {args.formation} formation.",
            operator="agent.codex",
            lane="system-cli",
            tool="flow-plan",
            command=f"scbe-system flow plan --task {args.task}",
            next_action="validate packet, then assign live work packets",
            tags=["flow-plan", args.formation, template_name],
            skills=FLOW_SKILLS,
            touched_layers=["control-plane", "coordination", "training"],
            artifacts=[_display_path(output_path, repo_root)],
            outputs={
                "formation": args.formation,
                "workflow_template": template_name,
                "agent_count": len(agents),
            },
            metrics={
                "agent_count": len(agents),
                "step_count": len(steps),
                "quorum": fault_tolerance["minimum_quorum"],
            },
            decisions=[
                {"key": "formation", "value": args.formation, "rationale": "Doctrine-backed swarm geometry."},
                {
                    "key": "workflow_template",
                    "value": template_name,
                    "rationale": "Maps Notion role doctrine into one deterministic packet.",
                },
            ],
        )
        run_id = start["run_id"]
        action_map.append_step(
            action_root,
            run_id=run_id,
            summary="Assigned six sacred tongues to ordered roles and quasi-phase cadence.",
            operator="agent.codex",
            lane="system-cli",
            tool="flow-plan",
            next_action="compile action map",
            tags=["agents", "formation"],
            skills=FLOW_SKILLS,
            touched_layers=["coordination", "governance"],
            outputs={
                "agent_roles": [agent["role"] for agent in agents],
                "phase_seeds": quasi_mesh["phase_seeds"],
            },
            metrics={"agent_count": len(agents)},
        )
        action_map.close_run(
            action_root,
            run_id=run_id,
            summary="Closed flow-planning run after writing operator packet.",
            operator="agent.codex",
            lane="system-cli",
            tool="flow-plan",
            next_action="dispatch work to the selected formation",
            tags=["completed", "flow-plan"],
            skills=FLOW_SKILLS,
            touched_layers=["training", "coordination"],
            artifacts=[_display_path(output_path, repo_root)],
            outputs={"output_path": _display_path(output_path, repo_root)},
        )
        compiled = action_map.build_action_map(action_root, run_id)
        flow_packet["action_map"] = {
            "enabled": True,
            "run_id": run_id,
            "run_root": _display_path(action_root, repo_root),
            "summary": compiled,
        }
    else:
        flow_packet["action_map"] = {"enabled": False}

    output_path.write_text(json.dumps(flow_packet, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    payload = {
        "schema_version": "scbe_flow_plan_result_v1",
        "output_path": _display_path(output_path, repo_root),
        "formation": args.formation,
        "workflow_template": template_name,
        "agent_count": len(agents),
        "step_count": len(steps),
        "action_map": flow_packet["action_map"],
    }
    lines = [
        f"Saved flow plan: {output_path}",
        f"Formation: {args.formation} | template: {template_name} | agents: {len(agents)} | steps: {len(steps)}",
    ]
    if flow_packet["action_map"].get("enabled"):
        lines.append(f"Action map: {flow_packet['action_map']['run_id']}")
    return _json_result(args, payload, lines)


def cmd_flow_packetize(args: argparse.Namespace) -> int:
    repo_root = args.repo_root
    plan_path = _repo_path(repo_root, args.plan)
    if not plan_path.exists():
        print(f"Flow plan not found: {plan_path}")
        return 2

    try:
        flow_packet = _load_flow_json(plan_path)
        _ensure_flow_plan_packet(flow_packet)
    except (json.JSONDecodeError, ValueError) as exc:
        print(str(exc))
        return 2

    support_units = max(0, int(args.support_units))
    work_packets = _build_work_packets(flow_packet, support_units)
    output_path = _repo_path(repo_root, args.output) if args.output else _default_flow_packet_output_path(plan_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    packet_manifest: dict[str, object] = {
        "schema_version": "scbe_work_packet_bundle_v1",
        "generated_at": _now_iso(),
        "source_plan": _display_path(plan_path, repo_root),
        "task": flow_packet["task"],
        "workflow_template": flow_packet["workflow_template"],
        "formation": flow_packet["formation"],
        "support_units_per_step": support_units,
        "packet_count": len(work_packets),
        "packets": work_packets,
        "action_map": {},
    }

    if args.emit_action_map:
        action_map = _load_action_map_module(repo_root)
        if action_map is None:
            print("Action-map protocol is unavailable.")
            return 2
        action_root = _repo_path(repo_root, args.action_root)
        action_root.mkdir(parents=True, exist_ok=True)
        run_task = f"{flow_packet['task']} packetize"
        start = action_map.start_run(
            action_root,
            task=run_task,
            summary=f"Generated bounded work packets from {_display_path(plan_path, repo_root)}.",
            operator="agent.codex",
            lane="system-cli",
            tool="flow-packetize",
            command=f"scbe-system flow packetize --plan {_display_path(plan_path, repo_root)}",
            next_action="dispatch packets to registered agents or external swarm lanes",
            tags=["flow-packetize", str(flow_packet["workflow_template"])],
            skills=FLOW_SKILLS,
            touched_layers=["coordination", "training"],
            artifacts=[_display_path(output_path, repo_root)],
            outputs={"packet_count": len(work_packets), "support_units_per_step": support_units},
            metrics={"packet_count": len(work_packets), "support_units_per_step": support_units},
        )
        run_id = start["run_id"]
        action_map.append_step(
            action_root,
            run_id=run_id,
            summary="Bounded work packets now include path policy, dependencies, and return contract.",
            operator="agent.codex",
            lane="system-cli",
            tool="flow-packetize",
            next_action="compile action map",
            tags=["work-packets", "execution"],
            skills=FLOW_SKILLS,
            touched_layers=["coordination", "governance"],
            outputs={
                "packet_ids": [packet["task_id"] for packet in work_packets],
                "support_units_per_step": support_units,
            },
            metrics={"packet_count": len(work_packets)},
        )
        action_map.close_run(
            action_root,
            run_id=run_id,
            summary="Closed packetization run after writing bundle manifest.",
            operator="agent.codex",
            lane="system-cli",
            tool="flow-packetize",
            next_action="execute packets across the swarm",
            tags=["completed", "flow-packetize"],
            skills=FLOW_SKILLS,
            touched_layers=["training", "coordination"],
            artifacts=[_display_path(output_path, repo_root)],
            outputs={"output_path": _display_path(output_path, repo_root)},
        )
        compiled = action_map.build_action_map(action_root, run_id)
        packet_manifest["action_map"] = {
            "enabled": True,
            "run_id": run_id,
            "run_root": _display_path(action_root, repo_root),
            "summary": compiled,
        }
    else:
        packet_manifest["action_map"] = {"enabled": False}

    output_path.write_text(json.dumps(packet_manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    payload = {
        "schema_version": "scbe_flow_packetize_result_v1",
        "output_path": _display_path(output_path, repo_root),
        "packet_count": len(work_packets),
        "support_units_per_step": support_units,
        "action_map": packet_manifest["action_map"],
    }
    lines = [
        f"Saved flow packets: {output_path}",
        f"Packets: {len(work_packets)} | support units per step: {support_units}",
    ]
    if packet_manifest["action_map"].get("enabled"):
        lines.append(f"Action map: {packet_manifest['action_map']['run_id']}")
    return _json_result(args, payload, lines)


def cmd_colab_list(args: argparse.Namespace) -> int:
    repo_root = args.repo_root
    notebooks = _colab_catalog_payloads(repo_root)
    payload = {
        "schema_version": "scbe_colab_catalog_v1",
        "count": len(notebooks),
        "notebooks": notebooks,
    }
    lines = ["SCBE Colab notebooks"]
    for row in notebooks:
        lines.append(f"{row['name']} [{row['category']}] -> {row['path']}")
    return _json_result(args, payload, lines)


def cmd_colab_show(args: argparse.Namespace) -> int:
    try:
        payload = _colab_notebook_payload(args.repo_root, args.name)
    except KeyError as exc:
        print(str(exc))
        return 2
    result = {
        "schema_version": "scbe_colab_notebook_v1",
        "notebook": payload,
    }
    lines = [
        f"name: {payload['name']}",
        f"category: {payload['category']}",
        f"path: {payload['path']}",
        f"exists: {'yes' if payload['exists'] else 'no'}",
        f"colab_url: {payload['colab_url']}",
    ]
    return _json_result(args, result, lines)


def cmd_colab_url(args: argparse.Namespace) -> int:
    try:
        payload = _colab_notebook_payload(args.repo_root, args.name)
    except KeyError as exc:
        print(str(exc))
        return 2
    result = {
        "schema_version": "scbe_colab_url_v1",
        "name": payload["name"],
        "colab_url": payload["colab_url"],
    }
    return _json_result(args, result, [payload["colab_url"]])


def cmd_colab_status(args: argparse.Namespace) -> int:
    repo_root = args.repo_root
    notebooks = _colab_catalog_payloads(repo_root)
    bridge = _colab_bridge_status(repo_root)
    payload = {
        "schema_version": "scbe_colab_status_v1",
        "repo_root": str(repo_root),
        "notebook_count": len(notebooks),
        "existing_notebook_count": sum(1 for row in notebooks if row.get("exists")),
        "bridge": bridge,
    }
    lines = [
        "SCBE Colab status",
        f"notebooks: {payload['existing_notebook_count']}/{payload['notebook_count']} present locally",
        f"colab bridge SFT rows: {bridge['sft_record_count']}",
        f"terminal method preferred: {'yes' if bridge['terminal_method_preferred'] else 'no'}",
        f"multiline cell exec supported: {'yes' if bridge['multiline_cell_exec_supported'] else 'no'}",
    ]
    if bridge["notes"].get("bridge_note"):
        lines.append(f"bridge note: {bridge['notes']['bridge_note']}")
    if bridge["notes"].get("spin_mode_note"):
        lines.append(f"spin note: {bridge['notes']['spin_mode_note']}")
    return _json_result(args, payload, lines)


def cmd_colab_review(args: argparse.Namespace) -> int:
    payload = _colab_notebook_review(args.repo_root)
    lines = [
        "SCBE Colab notebook review",
        f"notebooks: {payload['notebook_count']}",
        (
            "readiness: "
            f"ready={payload['readiness_counts']['ready']} "
            f"partial={payload['readiness_counts']['partial']} "
            f"review={payload['readiness_counts']['review']}"
        ),
    ]
    for row in payload["reviews"]:
        warning_text = "; ".join(row["warnings"][:2]) if row["warnings"] else "clean"
        lines.append(f"{row['name']}: {row['readiness']} [{row['category']}] - {warning_text}")
    return _json_result(args, payload, lines)


def cmd_colab_bridge_status(args: argparse.Namespace) -> int:
    try:
        result = _run_colab_bridge(args.repo_root, ["--status", "--name", args.name])
    except FileNotFoundError as exc:
        print(str(exc))
        return 2
    stdout = result.stdout.strip()
    if getattr(args, "json_output", False) and stdout:
        print(stdout)
        return result.returncode
    if stdout:
        print(stdout)
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode


def cmd_colab_bridge_env(args: argparse.Namespace) -> int:
    try:
        result = _run_colab_bridge(args.repo_root, ["--env", "--name", args.name])
    except FileNotFoundError as exc:
        print(str(exc))
        return 2
    stdout = result.stdout.strip()
    if stdout:
        print(stdout)
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode


def cmd_colab_bridge_probe(args: argparse.Namespace) -> int:
    try:
        result = _run_colab_bridge(args.repo_root, ["--probe", "--name", args.name])
    except FileNotFoundError as exc:
        print(str(exc))
        return 2
    stdout = result.stdout.strip()
    if stdout:
        print(stdout)
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode


def cmd_colab_bridge_set(args: argparse.Namespace) -> int:
    backend_url, env_overrides = _prepare_colab_bridge_secret_inputs(args.backend_url, args.token)
    bridge_args = ["--set", "--name", args.name, "--backend-url", backend_url or args.backend_url]
    if env_overrides.get("SCBE_COLAB_BRIDGE_TOKEN"):
        bridge_args += ["--token-env", "SCBE_COLAB_BRIDGE_TOKEN"]
    if args.n8n_webhook:
        bridge_args += ["--n8n-webhook", args.n8n_webhook]
    if args.probe:
        bridge_args.append("--probe")
    try:
        result = _run_colab_bridge(args.repo_root, bridge_args, env_overrides=env_overrides)
    except FileNotFoundError as exc:
        print(str(exc))
        return 2
    stdout = result.stdout.strip()
    if stdout:
        print(stdout)
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode


def cmd_doctor(args: argparse.Namespace) -> int:
    repo_root = args.repo_root
    config_path = _context_config_path(repo_root, getattr(args, "config_path", None))
    config = _load_cli_context(config_path)
    action_map = _load_action_map_module(repo_root)
    workflows_dir = repo_root / ".github" / "workflows"
    n8n_dir = repo_root / "workflows" / "n8n"
    payload = {
        "schema_version": "scbe_doctor_v1",
        "repo_root": str(repo_root),
        "python": sys.executable,
        "config_path": str(config_path),
        "active_context": safe_text(config.get("active_context")),
        "tooling": _tool_presence(),
        "modules": {
            "action_map": {"available": action_map is not None},
        },
        "paths": {
            "github_workflows": str(workflows_dir),
            "github_workflow_count": len(list(workflows_dir.glob("*.yml"))) if workflows_dir.exists() else 0,
            "n8n_workflows": str(n8n_dir),
            "n8n_file_count": len(list(n8n_dir.glob("*.json"))) if n8n_dir.exists() else 0,
        },
        "context_defaults": dict(config.get("defaults") or {}),
    }
    lines = [
        "SCBE doctor",
        f"repo_root: {repo_root}",
        f"config: {config_path}",
        f"active_context: {payload['active_context'] or 'none'}",
        f"action_map: {'available' if payload['modules']['action_map']['available'] else 'missing'}",
        f"github workflows: {payload['paths']['github_workflow_count']}",
        f"n8n files: {payload['paths']['n8n_file_count']}",
    ]
    for tool_name, info in payload["tooling"].items():
        lines.append(f"{tool_name:10} {'OK' if info['available'] else 'missing'} {info['path']}")
    return _json_result(args, payload, lines)


def cmd_use(args: argparse.Namespace) -> int:
    repo_root = args.repo_root
    config_path = _context_config_path(repo_root, getattr(args, "config_path", None))
    config = _load_cli_context(config_path)
    contexts = dict(config.get("contexts") or {})
    current = dict(contexts.get(args.context) or {})

    updates = {
        "firebase_project": safe_text(args.firebase_project),
        "github_repo": safe_text(args.github_repo),
        "hf_entity": safe_text(args.hf_entity),
        "notion_workspace": safe_text(args.notion_workspace),
        "workflow_dir": safe_text(args.workflow_dir),
        "n8n_dir": safe_text(args.n8n_dir),
    }
    for key, value in updates.items():
        if value:
            current[key] = value
    contexts[args.context] = current
    config["contexts"] = contexts
    config["active_context"] = args.context
    _save_cli_context(config_path, config)

    payload = {
        "schema_version": "scbe_context_use_v1",
        "config_path": str(config_path),
        "active_context": args.context,
        "context": current,
    }
    lines = [
        f"Active context: {args.context}",
        f"Saved: {config_path}",
    ]
    for key in sorted(current):
        lines.append(f"{key}: {current[key]}")
    return _json_result(args, payload, lines)


def cmd_config_list(args: argparse.Namespace) -> int:
    config_path = _context_config_path(args.repo_root, getattr(args, "config_path", None))
    config = _load_cli_context(config_path)
    payload = {
        "schema_version": "scbe_cli_context_v1",
        "config_path": str(config_path),
        "config": config,
    }
    lines = [f"Config: {config_path}", json.dumps(config, indent=2, ensure_ascii=True)]
    return _json_result(args, payload, lines)


def cmd_config_get(args: argparse.Namespace) -> int:
    config_path = _context_config_path(args.repo_root, getattr(args, "config_path", None))
    config = _load_cli_context(config_path)
    try:
        value = _get_nested(config, args.key)
    except KeyError:
        print(f"Config key not found: {args.key}")
        return 2
    payload = {
        "schema_version": "scbe_cli_config_get_v1",
        "config_path": str(config_path),
        "key": args.key,
        "value": value,
    }
    return _json_result(args, payload, [f"{args.key}={value}"])


def cmd_config_set(args: argparse.Namespace) -> int:
    config_path = _context_config_path(args.repo_root, getattr(args, "config_path", None))
    config = _load_cli_context(config_path)
    value_text = args.value
    try:
        value: object = json.loads(value_text)
    except json.JSONDecodeError:
        value = value_text
    _set_nested(config, args.key, value)
    _save_cli_context(config_path, config)
    payload = {
        "schema_version": "scbe_cli_config_set_v1",
        "config_path": str(config_path),
        "key": args.key,
        "value": value,
    }
    return _json_result(args, payload, [f"Set {args.key}", f"Saved: {config_path}"])


def cmd_workflow_styleize(args: argparse.Namespace) -> int:
    repo_root = args.repo_root
    config_path = _context_config_path(repo_root, getattr(args, "config_path", None))
    config = _load_cli_context(config_path)
    try:
        steps = _parse_workflow_steps(args.step)
    except ValueError as exc:
        print(str(exc))
        return 2

    env_vars: dict[str, str] = {}
    for raw in args.env or []:
        try:
            key, value = _parse_key_value(raw)
        except ValueError as exc:
            print(str(exc))
            return 2
        env_vars[key] = value

    workflow_path, queue_path = _workflow_output_paths(
        repo_root,
        config,
        args.name,
        args.workflow_path,
        args.queue_path,
    )
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.parent.mkdir(parents=True, exist_ok=True)

    yaml_text = _render_workflow_yaml(
        name=args.name,
        triggers=args.trigger or [],
        cron=args.cron,
        runs_on=args.runs_on,
        shell=args.shell,
        node_version=args.node_version,
        python_version=args.python_version,
        env_vars=env_vars,
        steps=steps,
    )
    queue_payload = _render_n8n_style_queue(args.name, workflow_path, steps, args.trigger or [], env_vars)

    workflow_path.write_text(yaml_text, encoding="utf-8")
    queue_path.write_text(json.dumps(queue_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    payload = {
        "schema_version": "scbe_workflow_styleize_v1",
        "name": args.name,
        "workflow_path": _display_path(workflow_path, repo_root),
        "queue_path": _display_path(queue_path, repo_root),
        "step_count": len(steps),
        "triggers": args.trigger or ["workflow_dispatch"],
        "runs_on": args.runs_on,
    }
    lines = [
        f"Saved workflow: {workflow_path}",
        f"Saved n8n queue: {queue_path}",
        f"Steps: {len(steps)}",
    ]
    return _json_result(args, payload, lines)


def cmd_status(args: argparse.Namespace) -> int:
    paths = [
        "artifacts/self_improvement_manifest.json",
        "artifacts/notion_pipeline_gap_review.json",
        "artifacts/aetherauth_decision.json",
        "artifacts/aetherauth_decision.md",
        "artifacts/agentic_antivirus_report.md",
        "artifacts/agentic_antivirus_report.json",
        "artifacts/self_improvement_summary.md",
    ]
    entries: list[dict[str, str]] = []
    for path in paths:
        file_path = args.repo_root / path
        status = "present" if file_path.exists() else "missing"
        entries.append({"path": path, "status": status})
    payload = {
        "schema_version": "scbe_status_v1",
        "repo_root": str(args.repo_root),
        "artifacts": entries,
        "notes": [
            "docs/SELF_IMPROVEMENT_AGENTS.md",
            ".scbe/next-coder-marker.md",
            "scripts/notion_pipeline_gap_review.py",
        ],
    }
    lines = ["SCBE Runbook status check", "-" * 28]
    lines.extend(f"{entry['status']:8} {entry['path']}" for entry in entries)
    lines.append("")
    lines.append("Tip: run `status` after each cycle and open `artifacts/*.md` files for human review.")
    lines.append("Notion/AI notes reference points:")
    lines.extend(f"- {note}" for note in payload["notes"])
    return _json_result(args, payload, lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scbe-system",
        description="SCBE-AETHERMOORE unified CLI for system operations",
    )
    parser.add_argument(
        "--repo-root",
        default=str(DEFAULT_REPO_ROOT),
        help="Repository root (default: current checkout)",
    )
    parser.add_argument("--json", dest="json_output", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument(
        "--config-path",
        default="",
        help="Override the repo-local CLI context file (default: .scbe/cli-context.json)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    def add_runtime_cli_flags(p: argparse.ArgumentParser) -> None:
        p.add_argument("--json", dest="json_output", action="store_true", help=argparse.SUPPRESS)
        p.add_argument("--config-path", default="", help=argparse.SUPPRESS)

    tongues = sub.add_parser("tongues", help="Six-Tongues toolkit passthrough")
    add_runtime_cli_flags(tongues)
    tongues.add_argument("tongue_args", nargs=argparse.REMAINDER, help="Args for six-tongues-cli.py")
    tongues.set_defaults(func=cmd_tongues)

    gap = sub.add_parser("notion-gap", help="Run notion-to-pipeline gap review")
    add_runtime_cli_flags(gap)
    gap.add_argument("--sync-config", default="scripts/sync-config.json")
    gap.add_argument("--pipeline-config", default="training/vertex_pipeline_config.yaml")
    gap.add_argument("--training-data", default="training-data")
    gap.add_argument("--output", default="artifacts/notion_pipeline_gap_review.json")
    gap.add_argument("--summary-path", default="artifacts/notion_pipeline_gap_review.md")
    gap.set_defaults(func=cmd_gap_review)

    improve = sub.add_parser("self-improve", help="Run self-improvement orchestrator")
    add_runtime_cli_flags(improve)
    improve.add_argument(
        "--mode", default="all", choices=("all", "code-assistant", "ai-nodal-dev-specialist", "fine-tune-funnel")
    )
    improve.add_argument("--coherence-report", default="coherence-report.json")
    improve.add_argument("--training-data", default="training-data")
    improve.add_argument("--pipeline-config", default="training/vertex_pipeline_config.yaml")
    improve.add_argument("--notion-gap-report", default="")
    improve.add_argument("--run-gap", action="store_true", help="Run notion gap review before orchestration")
    improve.add_argument("--sync-config", default="scripts/sync-config.json")
    improve.add_argument("--output", default="artifacts/self_improvement_manifest.json")
    improve.add_argument("--summary", default="artifacts/self_improvement_summary.md")
    improve.set_defaults(func=cmd_self_improve)

    web = sub.add_parser("web", help="Run web lookup/capture helpers")
    add_runtime_cli_flags(web)
    web.add_argument("--engine", choices=("auto", "playwright", "http"), default="auto")
    web.add_argument("--output-dir", default="artifacts/web_tool")
    web_sub = web.add_subparsers(dest="web_cmd", required=True)
    web_search = web_sub.add_parser("search", help="DuckDuckGo search capture")
    web_search.add_argument("--query", required=True)
    web_search.add_argument("--max-results", type=int, default=8)
    web_capture = web_sub.add_parser("capture", help="Capture URL using browser/http")
    web_capture.add_argument("--url", required=True)
    web.set_defaults(func=cmd_web)

    av = sub.add_parser("antivirus", help="Run lightweight static safety scan")
    add_runtime_cli_flags(av)
    av.add_argument("--output", default="artifacts/agentic_antivirus_report.json")
    av.add_argument("--summary", default="artifacts/agentic_antivirus_report.md")
    av.add_argument("--geoseal", action="store_true", help="Enable GeoSeal trust ring scoring")
    av.add_argument("--ring-core", type=float, default=0.70, help="Trust threshold for CORE ring")
    av.add_argument("--ring-outer", type=float, default=0.45, help="Trust threshold for OUTER ring")
    av.set_defaults(func=cmd_antivirus)

    auth = sub.add_parser("aetherauth", help="Run context-bound AetherAuth-style access decision")
    add_runtime_cli_flags(auth)
    auth.add_argument("--action", default="read", help="Requested action")
    auth.add_argument("--core-max", type=float, default=0.30, help="Core ring cutoff")
    auth.add_argument("--outer-max", type=float, default=0.70, help="Outer ring cutoff")
    auth.add_argument("--max-time-skew-ms", type=int, default=15 * 60 * 1000, help="Maximum acceptable clock skew")
    auth.add_argument("--context-json", default="", help="Context JSON object/list")
    auth.add_argument("--context-vector", default="", help="CSV 6D context vector")
    auth.add_argument("--reference-vector", default="", help="CSV expected reference vector")
    auth.add_argument("--time-ms", type=int, default=None, help="Event time in unix milliseconds")
    auth.add_argument("--latitude", type=float, default=None, help="Geospatial latitude")
    auth.add_argument("--longitude", type=float, default=None, help="Geospatial longitude")
    auth.add_argument("--cpu", type=float, default=None, help="CPU utilization metric")
    auth.add_argument("--memory", type=float, default=None, help="Memory utilization metric")
    auth.add_argument("--intent", type=float, default=None, help="Intent score")
    auth.add_argument("--history", type=float, default=None, help="History score")
    auth.add_argument(
        "--reference-latitude", type=float, default=None, help="Reference latitude for geospatial matching"
    )
    auth.add_argument(
        "--reference-longitude", type=float, default=None, help="Reference longitude for geospatial matching"
    )
    auth.add_argument("--trusted-radius-km", type=float, default=50.0, help="GeoSeal trusted radius in km")
    auth.add_argument("--location-core-radius-km", type=float, default=5.0, help="GeoSeal location core radius in km")
    auth.add_argument(
        "--location-outer-radius-km", type=float, default=80.0, help="GeoSeal location outer radius in km"
    )
    auth.add_argument("--location-core-max", type=float, default=None, help="Location core ring max risk")
    auth.add_argument("--location-outer-max", type=float, default=None, help="Location outer ring max risk")
    auth.add_argument("--enforce-location", action="store_true", help="Reject when location is missing/unresolvable")
    auth.add_argument("--secret", default="", help="Optional shared secret for envelope signature")
    auth.add_argument("--signature", default="", help="Optional request signature")
    auth.add_argument("--output", default="artifacts/aetherauth_decision.json")
    auth.add_argument("--summary", default="artifacts/aetherauth_decision.md")
    auth.set_defaults(func=cmd_aetherauth)

    agent = sub.add_parser("agent", help="Manage and call Squad AI agents")
    add_runtime_cli_flags(agent)
    agent_sub = agent.add_subparsers(dest="agent_cmd", required=True)
    a_boot = agent_sub.add_parser("bootstrap", help="Create or refresh default agent registry")
    a_boot.add_argument("--append", action="store_true", help="Add defaults while keeping existing agents")
    a_boot.add_argument("--force", action="store_true", help="Replace existing registry before bootstrapping")
    a_boot.add_argument(
        "--include-notebooklm", action="store_true", default=True, help="Include NotebookLM default entry"
    )
    a_boot.add_argument(
        "--no-include-notebooklm", dest="include_notebooklm", action="store_false", help="Skip NotebookLM default entry"
    )
    a_boot.add_argument("--codex-model", default="gpt-4o-mini")
    a_boot.set_defaults(func=cmd_agent_bootstrap)

    a_list = agent_sub.add_parser("list", help="List registered squad agents")
    a_list.set_defaults(func=cmd_agent_list)

    a_reg = agent_sub.add_parser("register", help="Register or update one squad agent")
    a_reg.add_argument("--agent-id", required=True)
    a_reg.add_argument("--provider", required=True, choices=("openai", "notebooklm"))
    a_reg.add_argument("--display-name")
    a_reg.add_argument("--description")
    a_reg.add_argument("--api-key-env", default="")
    a_reg.add_argument("--model", default="gpt-4o-mini")
    a_reg.add_argument("--endpoint", default="")
    a_reg.add_argument("--notebook-url", default=DEFAULT_NOTEBOOKLM_URL)
    a_reg.add_argument("--capabilities", default="")
    a_reg.set_defaults(func=cmd_agent_register)

    a_rm = agent_sub.add_parser("remove", help="Remove a squad agent")
    a_rm.add_argument("--agent-id", required=True)
    a_rm.set_defaults(func=cmd_agent_remove)

    a_ping = agent_sub.add_parser("ping", help="Send a simple ping prompt to one or all agents")
    a_ping.add_argument("--agent-id", default="__all__")
    a_ping.add_argument("--output-dir", default="artifacts/agent_calls")
    a_ping.add_argument("--max-tokens", type=int, default=64)
    a_ping.set_defaults(func=cmd_agent_ping)

    a_call = agent_sub.add_parser("call", help="Call one or more squad agents")
    a_call.add_argument("--agent-id", default="")
    a_call.add_argument("--all", action="store_true", help="Call every enabled agent")
    a_call.add_argument("--prompt", default="")
    a_call.add_argument("--prompt-file")
    a_call.add_argument("--output-dir", default="artifacts/agent_calls")
    a_call.add_argument("--max-tokens", type=int, default=420)
    a_call.add_argument("--show-output", action="store_true", help="Print successful model output")
    a_call.set_defaults(func=cmd_agent_call)

    doctor = sub.add_parser("doctor", help="Check local CLI/operator environment")
    add_runtime_cli_flags(doctor)
    doctor.set_defaults(func=cmd_doctor)

    use = sub.add_parser("use", help="Set the active SCBE operator context")
    add_runtime_cli_flags(use)
    use.add_argument("context", help="Context name to activate or update")
    use.add_argument("--firebase-project", default="")
    use.add_argument("--github-repo", default="")
    use.add_argument("--hf-entity", default="")
    use.add_argument("--notion-workspace", default="")
    use.add_argument("--workflow-dir", default="")
    use.add_argument("--n8n-dir", default="")
    use.set_defaults(func=cmd_use)

    config = sub.add_parser("config", help="Inspect or update repo-local CLI context")
    add_runtime_cli_flags(config)
    config_sub = config.add_subparsers(dest="config_cmd", required=True)
    config_list = config_sub.add_parser("list", help="Show the full CLI context config")
    add_runtime_cli_flags(config_list)
    config_list.set_defaults(func=cmd_config_list)
    config_get = config_sub.add_parser("get", help="Get one config value via dotted key")
    add_runtime_cli_flags(config_get)
    config_get.add_argument("key")
    config_get.set_defaults(func=cmd_config_get)
    config_set = config_sub.add_parser("set", help="Set one config value via dotted key")
    add_runtime_cli_flags(config_set)
    config_set.add_argument("key")
    config_set.add_argument("value")
    config_set.set_defaults(func=cmd_config_set)

    workflow = sub.add_parser("workflow", help="Generate GitHub + n8-style multistep workflow assets")
    add_runtime_cli_flags(workflow)
    workflow_sub = workflow.add_subparsers(dest="workflow_cmd", required=True)
    workflow_styleize = workflow_sub.add_parser("styleize", help="Emit GitHub Actions YAML and n8n-style queue JSON")
    add_runtime_cli_flags(workflow_styleize)
    workflow_styleize.add_argument("--name", required=True, help="Workflow name")
    workflow_styleize.add_argument(
        "--step",
        action="append",
        required=True,
        help="Workflow step in LABEL::COMMAND format; repeat for multiple steps",
    )
    workflow_styleize.add_argument(
        "--trigger",
        action="append",
        choices=("workflow_dispatch", "push", "pull_request", "schedule"),
        default=[],
        help="Workflow trigger; repeat to add more than one",
    )
    workflow_styleize.add_argument("--cron", default="0 9 * * *", help="Cron expression for schedule trigger")
    workflow_styleize.add_argument("--workflow-path", default="", help="Workflow file path or directory")
    workflow_styleize.add_argument("--queue-path", default="", help="n8-style queue file path or directory")
    workflow_styleize.add_argument("--runs-on", default="ubuntu-latest")
    workflow_styleize.add_argument("--shell", default="bash")
    workflow_styleize.add_argument("--node-version", default="20")
    workflow_styleize.add_argument("--python-version", default="3.11")
    workflow_styleize.add_argument("--env", action="append", default=[], help="KEY=VALUE environment binding")
    workflow_styleize.set_defaults(func=cmd_workflow_styleize)

    colab = sub.add_parser("colab", help="Inspect and route the SCBE Colab notebook lane")
    add_runtime_cli_flags(colab)
    colab_sub = colab.add_subparsers(dest="colab_cmd", required=True)
    colab_list = colab_sub.add_parser("list", help="List known SCBE Colab notebooks")
    add_runtime_cli_flags(colab_list)
    colab_list.set_defaults(func=cmd_colab_list)
    colab_show = colab_sub.add_parser("show", help="Show one Colab notebook record")
    add_runtime_cli_flags(colab_show)
    colab_show.add_argument("name", help="Notebook name or alias")
    colab_show.set_defaults(func=cmd_colab_show)
    colab_url = colab_sub.add_parser("url", help="Print the GitHub-backed Colab URL for one notebook")
    add_runtime_cli_flags(colab_url)
    colab_url.add_argument("name", help="Notebook name or alias")
    colab_url.set_defaults(func=cmd_colab_url)
    colab_status = colab_sub.add_parser("status", help="Show local bridge/training readiness for Colab")
    add_runtime_cli_flags(colab_status)
    colab_status.set_defaults(func=cmd_colab_status)
    colab_review = colab_sub.add_parser("review", help="Audit local Colab notebooks for readiness and drift")
    add_runtime_cli_flags(colab_review)
    colab_review.set_defaults(func=cmd_colab_review)
    colab_bridge_status = colab_sub.add_parser("bridge-status", help="Show saved Colab bridge profile")
    add_runtime_cli_flags(colab_bridge_status)
    colab_bridge_status.add_argument("--name", default="pivot")
    colab_bridge_status.set_defaults(func=cmd_colab_bridge_status)
    colab_bridge_env = colab_sub.add_parser("bridge-env", help="Emit env exports for a saved Colab bridge profile")
    add_runtime_cli_flags(colab_bridge_env)
    colab_bridge_env.add_argument("--name", default="pivot")
    colab_bridge_env.set_defaults(func=cmd_colab_bridge_env)
    colab_bridge_probe = colab_sub.add_parser("bridge-probe", help="Probe the saved Colab bridge backend")
    add_runtime_cli_flags(colab_bridge_probe)
    colab_bridge_probe.add_argument("--name", default="pivot")
    colab_bridge_probe.set_defaults(func=cmd_colab_bridge_probe)
    colab_bridge_set = colab_sub.add_parser("bridge-set", help="Save or update a Colab bridge profile")
    add_runtime_cli_flags(colab_bridge_set)
    colab_bridge_set.add_argument("--name", default="pivot")
    colab_bridge_set.add_argument("--backend-url", required=True)
    colab_bridge_set.add_argument("--token", default="")
    colab_bridge_set.add_argument("--n8n-webhook", default="")
    colab_bridge_set.add_argument("--probe", action="store_true")
    colab_bridge_set.set_defaults(func=cmd_colab_bridge_set)

    flow = sub.add_parser("flow", help="Doctrine-backed multi-agent flow planner")
    add_runtime_cli_flags(flow)
    flow_sub = flow.add_subparsers(dest="flow_cmd", required=True)
    flow_plan = flow_sub.add_parser("plan", help="Build a multi-agent plan packet with action-map telemetry")
    add_runtime_cli_flags(flow_plan)
    flow_plan.add_argument("--task", required=True, help="Mission or objective to route through the swarm")
    flow_plan.add_argument(
        "--formation",
        default="hexagonal",
        choices=("hexagonal", "tetrahedral", "concentric", "adaptive-scatter"),
        help="Swarm geometry to use for packet ordering",
    )
    flow_plan.add_argument(
        "--workflow-template",
        default="architecture-enhancement",
        choices=tuple(sorted(FLOW_WORKFLOW_TEMPLATES)),
        help="Doctrine template that determines ordered role handoffs",
    )
    flow_plan.add_argument(
        "--output", default="", help="Output JSON path (default: artifacts/flow_plans/<timestamp>-<task>.json)"
    )
    flow_plan.add_argument(
        "--action-root",
        default="training/runs/action_maps",
        help="Action-map run root for telemetry/training rows",
    )
    flow_plan.add_argument(
        "--no-action-map",
        dest="emit_action_map",
        action="store_false",
        help="Skip action-map emission and only write the flow packet",
    )
    flow_plan.set_defaults(func=cmd_flow_plan, emit_action_map=True)

    flow_packetize = flow_sub.add_parser("packetize", help="Convert a flow plan into bounded swarm work packets")
    add_runtime_cli_flags(flow_packetize)
    flow_packetize.add_argument("--plan", required=True, help="Path to an SCBE flow plan JSON")
    flow_packetize.add_argument(
        "--support-units",
        type=int,
        default=0,
        help="Extra support cells to assign per step for swarms larger than the six core lanes",
    )
    flow_packetize.add_argument("--output", default="", help="Output JSON path for the packet bundle")
    flow_packetize.add_argument(
        "--action-root",
        default="training/runs/action_maps",
        help="Action-map run root for packetization telemetry",
    )
    flow_packetize.add_argument(
        "--no-action-map",
        dest="emit_action_map",
        action="store_false",
        help="Skip action-map emission and only write the packet bundle",
    )
    flow_packetize.set_defaults(func=cmd_flow_packetize, emit_action_map=True)

    status = sub.add_parser("status", help="Show artifact presence for last cycle")
    add_runtime_cli_flags(status)
    status.set_defaults(func=cmd_status)

    pollypad = sub.add_parser("pollypad", help="Agent personal storage capsule (Kindle-style)")
    add_runtime_cli_flags(pollypad)
    pollypad.add_argument("--agent-root", default=str(DEFAULT_PAD_ROOT), help="Optional root path for polly pads")
    pollypad_sub = pollypad.add_subparsers(dest="pollypad_cmd", required=True)

    pp_init = pollypad_sub.add_parser("init", help="Create a new Polly Pad")
    pp_init.add_argument("--agent-id", required=True)
    pp_init.add_argument("--name", default="")
    pp_init.add_argument("--role", default="")
    pp_init.add_argument("--owner", default="")
    pp_init.add_argument("--max-storage-mb", type=int, default=256)
    pp_init.add_argument("--force", action="store_true", help="Overwrite existing pad")
    pp_init.set_defaults(func=cmd_pollypad_init)

    pollypad_sub.add_parser("list", help="List all Polly Pads").set_defaults(func=cmd_pollypad_list)

    pp_note = pollypad_sub.add_parser("note", help="Manage pad notes")
    pp_note_sub = pp_note.add_subparsers(dest="note_cmd", required=True)
    pp_note_add = pp_note_sub.add_parser("add", help="Add a note")
    pp_note_add.add_argument("--agent-id", required=True)
    pp_note_add.add_argument("--title", required=True)
    pp_note_add.add_argument("--text")
    pp_note_add.add_argument("--file")
    pp_note_add.add_argument("--tags", nargs="*")
    pp_note_add.set_defaults(func=cmd_pollypad_note_add)
    pp_note_list = pp_note_sub.add_parser("list", help="List notes")
    pp_note_list.add_argument("--agent-id", required=True)
    pp_note_list.set_defaults(func=cmd_pollypad_note_list)

    pp_book = pollypad_sub.add_parser("book", help="Manage pad books")
    pp_book_sub = pp_book.add_subparsers(dest="book_cmd", required=True)
    pp_book_add = pp_book_sub.add_parser("add", help="Add a book file")
    pp_book_add.add_argument("--agent-id", required=True)
    pp_book_add.add_argument("--title")
    pp_book_add.add_argument("--path", required=True)
    pp_book_add.set_defaults(func=cmd_pollypad_book_add)
    pp_book_list = pp_book_sub.add_parser("list", help="List books")
    pp_book_list.add_argument("--agent-id", required=True)
    pp_book_list.set_defaults(func=cmd_pollypad_book_list)

    pp_app = pollypad_sub.add_parser("app", help="Manage pad apps/utilities")
    pp_app_sub = pp_app.add_subparsers(dest="app_cmd", required=True)
    pp_app_install = pp_app_sub.add_parser("install", help="Install utility/app entry")
    pp_app_install.add_argument("--agent-id", required=True)
    pp_app_install.add_argument("--name", required=True)
    pp_app_install.add_argument("--entrypoint", required=True, help="Run command or path reference")
    pp_app_install.add_argument("--description")
    pp_app_install.add_argument("--script", help="Optional script to copy into this pad")
    pp_app_install.set_defaults(func=cmd_pollypad_app_install)
    pp_app_list = pp_app_sub.add_parser("list", help="List apps/utilities")
    pp_app_list.add_argument("--agent-id", required=True)
    pp_app_list.set_defaults(func=cmd_pollypad_app_list)
    pp_app_run = pp_app_sub.add_parser("run", help="Run one installed Polly Pad app in the governed runtime")
    pp_app_run.add_argument("--agent-id", required=True)
    pp_app_run.add_argument("--app-id", default="")
    pp_app_run.add_argument("--name", default="")
    pp_app_run.add_argument("--language", choices=RUNTIME_LANGUAGE_CHOICES, default="")
    pp_app_run.add_argument("--tongue", choices=("KO", "AV", "RU", "CA", "UM", "DR"), default="")
    pp_app_run.add_argument("--output-dir", default="artifacts/runtime_runs")
    pp_app_run.add_argument("--timeout-seconds", type=int, default=60)
    pp_app_run.add_argument("--keep-source", action="store_true", help="Keep generated runtime source files")
    pp_app_run.add_argument("extra_args", nargs=argparse.REMAINDER, help="Args passed to the installed app after --")
    pp_app_run.set_defaults(func=cmd_pollypad_app_run)

    pp_snapshot = pollypad_sub.add_parser("snapshot", help="Export current pad snapshot JSON")
    pp_snapshot.add_argument("--agent-id", required=True)
    pp_snapshot.add_argument("--output")
    pp_snapshot.set_defaults(func=cmd_pollypad_snapshot)

    runtime = sub.add_parser("runtime", help="Governed polyglot execution runtime")
    add_runtime_cli_flags(runtime)
    runtime_sub = runtime.add_subparsers(dest="runtime_cmd", required=True)
    rt_run = runtime_sub.add_parser("run", help="Run code or a Polly Pad app inside the controlled runtime")
    rt_run.add_argument("--agent-id", default="", help="Optional Polly Pad agent id for scoped execution")
    rt_run.add_argument("--agent-root", default=str(DEFAULT_PAD_ROOT), help="Optional root path for polly pads")
    rt_run.add_argument("--app-id", default="", help="Installed Polly Pad app id to run")
    rt_run.add_argument("--app-name", default="", help="Installed Polly Pad app name to run")
    rt_run.add_argument(
        "--language", choices=RUNTIME_LANGUAGE_CHOICES, default="", help="Runtime language for direct execution"
    )
    rt_run.add_argument(
        "--tongue",
        choices=("KO", "AV", "RU", "CA", "UM", "DR"),
        default="",
        help="Attach a Sacred Tongue execution label",
    )
    rt_run.add_argument("--file", default="", help="Controlled source file path to run")
    rt_run.add_argument("--code", default="", help="Inline source code to run")
    rt_run.add_argument("--output-dir", default="artifacts/runtime_runs")
    rt_run.add_argument("--timeout-seconds", type=int, default=60)
    rt_run.add_argument(
        "--keep-source", action="store_true", help="Keep generated runtime source files for inline code"
    )
    rt_run.add_argument("extra_args", nargs=argparse.REMAINDER, help="Args passed to the runtime after --")
    rt_run.set_defaults(func=cmd_runtime_run)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.repo_root = Path(args.repo_root).resolve()
    if args.command == "pollypad":
        pad_root = args.agent_root
        # Keep root consistent with any provided override.
        global DEFAULT_PAD_ROOT
        if isinstance(pad_root, str):
            DEFAULT_PAD_ROOT = Path(pad_root)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
