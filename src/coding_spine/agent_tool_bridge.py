"""
Agent harness — SCBE-native bridge hints for external tools.

Maps high-level agent goals to concrete GeoSeal CLI invocations and local
service URLs so coding agents can stay inside SCBE surfaces while reaching
browsers, GitHub, Hugging Face, and other MCP-backed lanes.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import hashlib
from pathlib import Path
from typing import Any, Optional

from src.ca_lexicon import ALL_LANG_MAP, LANG_MAP, TONGUE_PARENT
from src.coding_spine.agent_temporal_reliance import build_agent_execution_stack_v1
from src.coding_spine.skill_harness_tools import build_harness_skill_tools_v1
from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER


def _exe() -> str:
    return shlex.quote(sys.executable)


def _language_matrix() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for tongue, language in ALL_LANG_MAP.items():
        parent = TONGUE_PARENT.get(tongue)
        rows.append(
            {
                "tongue": tongue,
                "language": language,
                "primary": tongue in LANG_MAP,
                "parent_tongue": parent,
                "route_class": "native" if tongue in LANG_MAP else "extended",
                "cli": {
                    "code_packet": f"{_exe()} -m src.geoseal_cli code-packet --language {language} --source-file <file> --json",
                    "explain_route": f"{_exe()} -m src.geoseal_cli explain-route --language {language} --source-file <file> --json",
                    "testing_cli": f"{_exe()} -m src.geoseal_cli testing-cli --language {language} --source-file <file> --json",
                },
            }
        )
    return rows


def _tool_contracts() -> list[dict[str, Any]]:
    return [
        {
            "tool": "read",
            "risk": "low",
            "approval": "auto",
            "purpose": "Inspect repository files, manifests, docs, and generated reports.",
            "routes": [
                "code-packet",
                "explain-route",
                "history",
                "backend-registry",
                "call-switchboard",
                "lightning-indexer",
            ],
        },
        {
            "tool": "write_workspace",
            "risk": "medium",
            "approval": "ask_or_policy_allow",
            "purpose": "Create or patch files inside the active workspace only.",
            "routes": ["project-scaffold", "agent:task", "workflow run"],
        },
        {
            "tool": "execute_tests",
            "risk": "medium",
            "approval": "ask_or_policy_allow",
            "purpose": "Run bounded tests, syntax checks, and replayable verification commands.",
            "routes": ["testing-cli", "agentic_ladder", "benchmark:cli"],
        },
        {
            "tool": "network_or_cloud",
            "risk": "high",
            "approval": "explicit",
            "purpose": "Use Hugging Face, GitHub Actions, Vercel, Kaggle, Colab, or browser-backed retrieval.",
            "routes": ["vercel_agent_router", "hf_jobs", "training:surfaces"],
        },
        {
            "tool": "secrets_or_credentials",
            "risk": "critical",
            "approval": "deny_by_default",
            "purpose": "Secrets are never routed through free model prompts; tools receive only named env requirements.",
            "routes": ["connector_env_check", "redacted_evidence_only"],
        },
        {
            "tool": "destructive_filesystem",
            "risk": "critical",
            "approval": "human_explicit_only",
            "purpose": "Delete, reset, clean, uninstall, or move large data only after manifest/offload proof.",
            "routes": ["plan_only", "verified_cleanup"],
        },
    ]


def _permission_profiles() -> list[dict[str, Any]]:
    return [
        {
            "mode": "observe",
            "default": True,
            "allows": ["read", "route_explain", "packetize", "history"],
            "blocks": [
                "write_workspace",
                "network_or_cloud",
                "secrets_or_credentials",
                "destructive_filesystem",
            ],
        },
        {
            "mode": "workspace-write",
            "allows": [
                "read",
                "route_explain",
                "packetize",
                "write_workspace",
                "execute_tests",
            ],
            "blocks": ["secrets_or_credentials", "destructive_filesystem"],
            "requires_approval": ["network_or_cloud"],
        },
        {
            "mode": "cloud-dispatch",
            "allows": [
                "read",
                "route_explain",
                "packetize",
                "execute_tests",
                "network_or_cloud",
            ],
            "requires_approval": ["write_workspace"],
            "blocks": ["secrets_or_credentials", "destructive_filesystem"],
        },
        {
            "mode": "maintenance",
            "allows": [
                "read",
                "route_explain",
                "packetize",
                "write_workspace",
                "execute_tests",
            ],
            "requires_approval": ["network_or_cloud", "destructive_filesystem"],
            "blocks": ["secrets_or_credentials"],
        },
    ]


def _agentic_training_extensions() -> dict[str, Any]:
    exe = _exe()
    return {
        "schema_version": "scbe_agentic_training_extensions_v1",
        "github": {
            "lane": "agentic_training_loop",
            "required_tools": ["gh", "git"],
            "commands": {
                "list_recent_runs": "gh run list --limit 10 --json databaseId,headSha,status,conclusion,name",
                "trigger_router_coding": (
                    'gh workflow run "agent-router.yml" ' "--ref <branch> -f task=coding -f query=<task_goal>"
                ),
                "watch_run": "gh run watch <run-id> --exit-status",
            },
        },
        "huggingface": {
            "lane": "agentic_training_loop",
            "required_tools": ["python", "HF_TOKEN"],
            "commands": {
                "dispatch_bijective_gate_job": (
                    f"{exe} scripts/hf_jobs/run_bijective_tongue_gate_hf.py "
                    "--model <hf_model> --dataset <hf_dataset>"
                ),
                "dispatch_paired_coding_job": (
                    f"{exe} scripts/hf_jobs/run_paired_coding_gate_hf.py " "--model <hf_model> --dataset <hf_dataset>"
                ),
                "dispatch_train_and_gate": (
                    f"{exe} scripts/hf_jobs/run_bijective_v4_train_and_gate.py "
                    "--base-model <hf_model> --train-dataset <hf_dataset>"
                ),
            },
        },
        "safety": {
            "principles": [
                "branch scoped only; do not force-push protected branches",
                "no secrets in prompts, packets, or logs",
                "training dispatch is cloud-risk: explicit approval required",
                "gate on eval metrics before promote/merge",
            ]
        },
    }


_DEFAULT_HF_MODEL = "issdandavis/scbe-coding-agent-qwen-merged-coding-model-v1"
_DEFAULT_HF_DATASET_REPO = "issdandavis/scbe-coding-agent-sft"

_GITHUB_LOOP_TASK_ALIASES: dict[str, str] = {
    "list_runs": "list_recent_runs",
    "list_recent_runs": "list_recent_runs",
    "runs": "list_recent_runs",
    "coding": "trigger_router_coding",
    "router_coding": "trigger_router_coding",
    "trigger_router_coding": "trigger_router_coding",
    "watch": "watch_run",
    "watch_run": "watch_run",
}

_HF_LOOP_TASK_ALIASES: dict[str, str] = {
    "bijective_gate": "dispatch_bijective_gate_job",
    "gate": "dispatch_bijective_gate_job",
    "dispatch_bijective_gate_job": "dispatch_bijective_gate_job",
    "paired": "dispatch_paired_coding_job",
    "paired_coding": "dispatch_paired_coding_job",
    "dispatch_paired_coding_job": "dispatch_paired_coding_job",
    "train_and_gate": "dispatch_train_and_gate",
    "train": "dispatch_train_and_gate",
    "dispatch_train_and_gate": "dispatch_train_and_gate",
}


def _repo_root_for_dispatch() -> Path:
    return Path(__file__).resolve().parents[2]


def _format_shell_line(argv: list[str], execute_env: dict[str, str]) -> str:
    """Best-effort single-line shell for logs (POSIX-oriented)."""

    if not execute_env:
        return " ".join(shlex.quote(a) for a in argv)
    prefixes = [f"{k}={shlex.quote(v)}" for k, v in sorted(execute_env.items())]
    return " ".join(prefixes + [shlex.quote(a) for a in argv])


def build_hydra_tokenizer_bridge_v1(
    *,
    goal: str = "",
    preferred_language: str = "python",
    permission_mode: str = "observe",
) -> dict[str, Any]:
    """Return the HYDRA-to-GeoSeal tokenizer routing packet.

    HYDRA is the multi-agent orchestration layer. GeoSeal is the governance and
    route envelope. The Sacred Tongues tokenizer is the deterministic transport
    layer. This packet keeps those roles separate so agents can learn the
    wiring without treating tokenizer output as permission or security.
    """

    text = (goal or "hydra agent task").strip()[:12000]
    preferred = (preferred_language or "python").strip().lower()
    language_matrix = _language_matrix()
    selected = next((row for row in language_matrix if row["language"] == preferred), language_matrix[0])
    selected_tongue = str(selected["tongue"]).lower()
    payload = text.encode("utf-8", errors="replace")
    token_rows: list[dict[str, Any]] = []
    for tongue in ("ko", "av", "ru", "ca", "um", "dr"):
        tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(tongue, payload)
        token_rows.append(
            {
                "tongue": tongue.upper(),
                "tokenizer_tongue": tongue,
                "byte_count": len(payload),
                "token_count": len(tokens),
                "token_sha256": hashlib.sha256(" ".join(tokens).encode("utf-8")).hexdigest(),
                "harmonic_fingerprint": round(
                    float(SACRED_TONGUE_TOKENIZER.compute_harmonic_fingerprint(tongue, tokens)), 6
                ),
                "sample_tokens": tokens[:8],
            }
        )
    hydra_heads = [
        {"head": "spine", "tongue": "KO", "role": "route goal, task graph, and consensus order"},
        {"head": "builder", "tongue": "AV", "role": "generate code patches and automation plans"},
        {"head": "repair", "tongue": "RU", "role": "debug failures, stabilize faults, and verify fixes"},
        {"head": "navigator", "tongue": "CA", "role": "track return paths, budgets, and bounded execution"},
        {"head": "analyst", "tongue": "UM", "role": "score evidence, sampling value, and optimization choices"},
        {"head": "scribe", "tongue": "DR", "role": "compress handoff, archive state, and replay history"},
    ]
    exe = _exe()
    return {
        "schema_version": "geoseal_hydra_tokenizer_bridge_v1",
        "goal_excerpt": text[:500],
        "permission_mode": permission_mode,
        "selected_language": selected,
        "separation_of_concerns": {
            "hydra": "multi-agent orchestration and division of labor",
            "geoseal": "route envelope, policy surface, replay, and audit",
            "tokenizer": "deterministic cross-tongue transport and training substrate",
            "governance": "permission, execution policy, and verification gates",
        },
        "hydra_heads": hydra_heads,
        "tokenizer_packet": {
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "selected_tongue": selected_tongue.upper(),
            "rows": token_rows,
            "transport_boundary": "Tokenizer rows are routeable evidence, not authorization.",
        },
        "geoseal_cli": {
            "hydra_bridge_json": (
                f"{exe} -m src.geoseal_cli hydra-bridge --goal <goal> "
                f"--language {preferred} --permission-mode {permission_mode} --json"
            ),
            "agent_harness_json": (
                f"{exe} -m src.geoseal_cli agent-harness --goal <goal> "
                f"--language {preferred} --permission-mode {permission_mode} --json"
            ),
            "code_packet_json": f"{exe} -m src.geoseal_cli code-packet --content <goal_or_source> --language {preferred} --json",
            "testing_cli_json": f"{exe} -m src.geoseal_cli testing-cli --content <source> --language {preferred} --json",
        },
        "training_hooks": [
            "goal -> hydra head assignment",
            "goal -> GeoSeal command selection",
            "goal bytes -> Sacred Tongues tokenizer rows",
            "command output -> next safe action",
            "permission mode -> allowed tool class",
        ],
    }


def resolve_agentic_loop_dispatch_v1(
    *,
    provider: str,
    task: str,
    query: str = "",
    branch: str = "",
    run_id: str = "",
    hf_model: str = "",
    hf_dataset: str = "",
    repo_root: Optional[Path] = None,
) -> dict[str, Any]:
    """Resolve a training-loop extension into argv + env for agents and gated runners.

    HF job scripts in ``scripts/hf_jobs/`` read configuration from environment
    variables (not CLI flags). The returned ``resolved_shell`` uses env-prefix
    form so operators see the real contract.
    """

    root = repo_root or _repo_root_for_dispatch()
    prov = (provider or "").strip().lower()
    raw_task = (task or "").strip().lower()
    goal = (query or "").strip()
    br = (branch or "").strip()
    rid = (run_id or "").strip()
    model = (hf_model or "").strip() or os.environ.get("SCBE_GATE_MODEL", "").strip()
    model = model or os.environ.get("SCBE_HF_MODEL", "").strip() or _DEFAULT_HF_MODEL
    ds = (hf_dataset or "").strip() or os.environ.get("SCBE_V4_DATASET_REPO", "").strip()
    ds = ds or _DEFAULT_HF_DATASET_REPO
    if not br:
        br = os.environ.get("GITHUB_REF_NAME", "").strip() or os.environ.get("SCBE_LOOP_BRANCH", "").strip() or "main"

    base: dict[str, Any] = {
        "schema_version": "geoseal-loop-dispatch-v1",
        "gate_env_var": "SCBE_AGENTIC_LOOP_EXECUTE",
        "cwd": str(root.resolve()),
    }

    if prov == "github":
        key = _GITHUB_LOOP_TASK_ALIASES.get(raw_task)
        if not key:
            return {
                **base,
                "ok": False,
                "error": f"unknown github task {task!r}; try: list_runs | coding | watch",
            }
        if key == "list_recent_runs":
            argv = [
                "gh",
                "run",
                "list",
                "--limit",
                "10",
                "--json",
                "databaseId,headSha,status,conclusion,name",
            ]
            return {
                **base,
                "ok": True,
                "provider": "github",
                "task": key,
                "argv": argv,
                "execute_env": {},
                "resolved_shell": _format_shell_line(argv, {}),
            }
        if key == "trigger_router_coding":
            if not br:
                return {**base, "ok": False, "error": "branch/ref required for coding dispatch"}
            argv = [
                "gh",
                "workflow",
                "run",
                "agent-router.yml",
                "--ref",
                br,
                "-f",
                "task=coding",
                "-f",
                f"query={goal or 'scbe agentic loop'}",
            ]
            return {
                **base,
                "ok": True,
                "provider": "github",
                "task": key,
                "argv": argv,
                "execute_env": {},
                "resolved_shell": _format_shell_line(argv, {}),
            }
        if key == "watch_run":
            if not rid:
                return {**base, "ok": False, "error": "run id required (--run-id) for watch"}
            argv = ["gh", "run", "watch", rid, "--exit-status"]
            return {
                **base,
                "ok": True,
                "provider": "github",
                "task": key,
                "argv": argv,
                "execute_env": {},
                "resolved_shell": _format_shell_line(argv, {}),
            }

    if prov == "huggingface":
        key = _HF_LOOP_TASK_ALIASES.get(raw_task)
        if not key:
            return {
                **base,
                "ok": False,
                "error": f"unknown huggingface task {task!r}; try: bijective_gate | paired_coding | train_and_gate",
            }
        py = sys.executable
        if key == "dispatch_bijective_gate_job":
            script = root / "scripts" / "hf_jobs" / "run_bijective_tongue_gate_hf.py"
            env = {"SCBE_GATE_MODEL": model}
            argv = [py, str(script)]
            return {
                **base,
                "ok": True,
                "provider": "huggingface",
                "task": key,
                "argv": argv,
                "execute_env": env,
                "resolved_shell": _format_shell_line(argv, env),
                "notes": [
                    "HF gate script reads SCBE_GATE_MODEL (and optional SCBE_GATE_TONGUES); "
                    "dataset placeholder from harness templates is not used by this script.",
                ],
            }
        if key == "dispatch_paired_coding_job":
            script = root / "scripts" / "hf_jobs" / "run_paired_coding_gate_hf.py"
            env = {"SCBE_GATE_MODEL_A": model, "SCBE_GATE_MODEL_B": model}
            argv = [py, str(script)]
            return {
                **base,
                "ok": True,
                "provider": "huggingface",
                "task": key,
                "argv": argv,
                "execute_env": env,
                "resolved_shell": _format_shell_line(argv, env),
            }
        if key == "dispatch_train_and_gate":
            script = root / "scripts" / "hf_jobs" / "run_bijective_v4_train_and_gate.py"
            env = {"SCBE_V4_BASE_MODEL": model, "SCBE_V4_DATASET_REPO": ds}
            argv = [py, str(script)]
            return {
                **base,
                "ok": True,
                "provider": "huggingface",
                "task": key,
                "argv": argv,
                "execute_env": env,
                "resolved_shell": _format_shell_line(argv, env),
            }

    return {**base, "ok": False, "error": f"unknown provider {provider!r}"}


def run_agentic_loop_dispatch_resolved(
    payload: dict[str, Any],
) -> subprocess.CompletedProcess[str]:
    """Run a successful resolve payload under merged env (for tests and CLI)."""

    if not payload.get("ok"):
        raise ValueError("refusing to run failed resolve payload")
    argv = payload.get("argv")
    if not isinstance(argv, list) or not argv:
        raise ValueError("payload missing argv")
    cwd = payload.get("cwd")
    env = os.environ.copy()
    for k, v in (payload.get("execute_env") or {}).items():
        env[str(k)] = str(v)
    return subprocess.run(
        [str(x) for x in argv],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def build_agent_harness_manifest_v1(
    *,
    inline_goal: str = "",
    preferred_language: str = "python",
    permission_mode: str = "observe",
) -> dict[str, Any]:
    """Return the full agent-facing GeoSeal harness contract.

    This is intentionally model-neutral JSON. A small/free model can read it,
    choose a bounded tool route, and hand the exact command back to a runner
    without needing hidden local context.
    """

    goal = (inline_goal or "").strip()[:12000]
    preferred = (preferred_language or "python").strip().lower()
    matrix = _language_matrix()
    language_row = next((row for row in matrix if row["language"] == preferred), matrix[0])
    bridge = build_agent_tool_bridge_v1(inline_goal=goal or "inspect harness")
    hydra_bridge = build_hydra_tokenizer_bridge_v1(
        goal=goal or "inspect harness",
        preferred_language=preferred,
        permission_mode=permission_mode,
    )
    repo_root = Path(__file__).resolve().parents[2]
    harness_skills = build_harness_skill_tools_v1(repo_root=repo_root)
    return {
        "schema_version": "scbe_agent_harness_manifest_v1",
        "goal_excerpt": goal[:500],
        "design_basis": {
            "agent_cli_patterns": [
                "repo context file",
                "permission and sandbox profiles",
                "tool schema manifest",
                "hookable pre-tool policy",
                "replayable trajectory and evidence artifacts",
                "language-agnostic routing matrix",
            ],
            "scbe_boundary": "GeoSeal routes and explains; governance permits; separate tools execute.",
        },
        "language_routes": matrix,
        "selected_language": language_row,
        "permission_mode": permission_mode,
        "permission_profiles": _permission_profiles(),
        "tool_contracts": _tool_contracts(),
        "standard_flow": [
            "agent reads manifest",
            "agent chooses language/tongue route",
            "agent emits code-packet or explain-route",
            "policy gate checks requested tool class",
            "runner executes only approved command",
            "testing-cli or benchmark validates result",
            "history/replay records trajectory",
        ],
        "hydra_tokenizer_bridge_v1": hydra_bridge,
        "agent_execution_stack_v1": build_agent_execution_stack_v1(),
        "geoseal_cli": {
            **bridge["geoseal_cli"],
            "hydra_bridge_json": f"{_exe()} -m src.geoseal_cli hydra-bridge --goal <goal> --json",
            "agent_harness_json": f"{_exe()} -m src.geoseal_cli agent-harness --goal <goal> --json",
            "language_matrix_json": f"{_exe()} -m src.geoseal_cli agent-harness --language {preferred} --json",
            "call_switchboard_json": (
                f"{_exe()} -m src.geoseal_cli call-switchboard "
                "--request '<call_request_json>' --json"
            ),
            "lightning_indexer_json": (
                f"{_exe()} -m src.geoseal_cli lightning-indexer --goal <goal> --json"
            ),
        },
        "service_routes": {
            **bridge["geoseal_service"],
            "agent_harness": f"{bridge['geoseal_service']['env']['GEOSEAL_SERVICE_URL']}/v1/harness/agent-harness",
        },
        "external_router": bridge["vercel_agent_router"],
        "harness_skill_tools_v1": harness_skills,
        "mcp_style_exports": {
            "tools": [row["tool"] for row in _tool_contracts()],
            "skill_tool_names": [
                s["tool_name"] for s in harness_skills.get("skills", []) if s.get("invocation_kind") == "tool_call"
            ],
            "skill_lookup_names": [
                s["route_name"] for s in harness_skills.get("skills", []) if s.get("invocation_kind") == "skill_lookup"
            ],
            "skill_write_names": [
                s["route_name"] for s in harness_skills.get("skills", []) if s.get("invocation_kind") == "skill_write"
            ],
            "skill_route_names": [s["route_name"] for s in harness_skills.get("skills", [])],
            "resources": [
                "language_routes",
                "permission_profiles",
                "standard_flow",
                "hydra_tokenizer_bridge_v1",
                "agent_execution_stack_v1",
                "call_switchboard",
                "lightning_indexer",
                "inbuilt_agentic_training_extensions",
                "harness_skill_tools_v1",
            ],
            "prompts": ["explain-route", "testing-cli", "project-scaffold"],
        },
        "inbuilt_agentic_training_extensions": _agentic_training_extensions(),
    }


def build_agent_tool_bridge_v1(
    *,
    intent_relative_posix: Optional[str] = None,
    inline_goal: Optional[str] = None,
) -> dict[str, Any]:
    """Return command templates and connector hints.

    Exactly one of ``intent_relative_posix`` (repo-relative path to intent file)
    or ``inline_goal`` (raw goal text) must be provided.
    """
    if (intent_relative_posix is None) == (inline_goal is None):
        raise ValueError("provide exactly one of intent_relative_posix or inline_goal")

    exe = _exe()
    if intent_relative_posix:
        src = shlex.quote(intent_relative_posix)
        file_args = f"--source-file {src} --language python --source-name task_intent.txt"
    else:
        text = (inline_goal or "")[:12000]
        file_args = f"--content {shlex.quote(text)} --language python --source-name agent_goal"

    geoseal_cli = {
        "backend_registry_json": f"{exe} -m src.geoseal_cli backend-registry --json",
        "explain_route_json": f"{exe} -m src.geoseal_cli explain-route {file_args} --json",
        "code_packet_json": f"{exe} -m src.geoseal_cli code-packet {file_args} --json",
        "history_json": f"{exe} -m src.geoseal_cli history --json",
        "testing_cli_json": f"{exe} -m src.geoseal_cli testing-cli {file_args} --json",
        "agentic_training_loop_json": f"{exe} -m src.geoseal_cli agentic-training-loop --provider both --json",
        "loop_dispatch_github_coding_json": (
            f"{exe} -m src.geoseal_cli loop-dispatch --provider github --task coding "
            "--branch <branch> --query <task_goal> --json"
        ),
        "loop_dispatch_hf_bijective_json": (
            f"{exe} -m src.geoseal_cli loop-dispatch --provider huggingface "
            "--task bijective_gate --hf-model <hf_model_id> --json"
        ),
    }

    base_url = os.environ.get("GEOSEAL_SERVICE_URL", "http://127.0.0.1:8765").rstrip("/")
    n8n_bridge = os.environ.get("SCBE_N8N_BRIDGE_URL", "http://127.0.0.1:8001").rstrip("/")

    return {
        "schema_version": "scbe_agent_tool_bridge_v1",
        "intent_mode": "file" if intent_relative_posix else "inline",
        "intent_artifact": intent_relative_posix,
        "language_routes": _language_matrix(),
        "permission_profiles": _permission_profiles(),
        "tool_contracts": _tool_contracts(),
        "geoseal_cli": geoseal_cli,
        "geoseal_service": {
            "health": f"{base_url}/health",
            "spaceport_status": f"{base_url}/v1/spaceport/status",
            "tool_bridge": f"{base_url}/v1/harness/tool-bridge",
            "runtime_inspect": f"{base_url}/runtime/inspect",
            "env": {"GEOSEAL_SERVICE_URL": base_url},
        },
        "n8n_workflow_bridge": {
            "base_url": n8n_bridge,
            "routes": [
                "/health",
                "/v1/governance/scan",
                "/v1/tongue/encode",
                "/v1/agent/task",
                "/v1/training/ingest",
            ],
        },
        "cursor_mcp_lane": {
            "policy": "Prefer MCP tools registered in the host IDE; do not paste secrets into model chats.",
            "typical_servers": [
                "plugin-playwright-playwright",
                "plugin-github-github",
                "plugin-huggingface-skills-huggingface-skills",
                "plugin-render-render",
            ],
        },
        "vercel_agent_router": {
            "note": "Optional GitHub Actions dispatch via serverless bridge (configure AGENT_DISPATCH_SECRET).",
            "allowed_tasks": [
                "research",
                "monitor",
                "ask",
                "scrape",
                "web_search",
                "coding",
                "system_build",
                "agentic_ladder",
            ],
        },
        "inbuilt_agentic_training_extensions": _agentic_training_extensions(),
    }
