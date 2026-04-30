"""
Agent harness — SCBE-native bridge hints for external tools.

Maps high-level agent goals to concrete GeoSeal CLI invocations and local
service URLs so coding agents can stay inside SCBE surfaces while reaching
browsers, GitHub, Hugging Face, and other MCP-backed lanes.
"""

from __future__ import annotations

import os
import shlex
import sys
from typing import Any, Optional

from src.ca_lexicon import ALL_LANG_MAP, LANG_MAP, TONGUE_PARENT


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
            "routes": ["code-packet", "explain-route", "history", "backend-registry"],
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
    language_row = next(
        (row for row in matrix if row["language"] == preferred), matrix[0]
    )
    bridge = build_agent_tool_bridge_v1(inline_goal=goal or "inspect harness")
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
        "geoseal_cli": {
            **bridge["geoseal_cli"],
            "agent_harness_json": f"{_exe()} -m src.geoseal_cli agent-harness --goal <goal> --json",
            "language_matrix_json": f"{_exe()} -m src.geoseal_cli agent-harness --language {preferred} --json",
        },
        "service_routes": {
            **bridge["geoseal_service"],
            "agent_harness": f"{bridge['geoseal_service']['env']['GEOSEAL_SERVICE_URL']}/v1/harness/agent-harness",
        },
        "external_router": bridge["vercel_agent_router"],
        "mcp_style_exports": {
            "tools": [row["tool"] for row in _tool_contracts()],
            "resources": ["language_routes", "permission_profiles", "standard_flow"],
            "prompts": ["explain-route", "testing-cli", "project-scaffold"],
        },
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
        file_args = (
            f"--source-file {src} --language python --source-name task_intent.txt"
        )
    else:
        text = (inline_goal or "")[:12000]
        file_args = (
            f"--content {shlex.quote(text)} --language python --source-name agent_goal"
        )

    geoseal_cli = {
        "backend_registry_json": f"{exe} -m src.geoseal_cli backend-registry --json",
        "explain_route_json": f"{exe} -m src.geoseal_cli explain-route {file_args} --json",
        "code_packet_json": f"{exe} -m src.geoseal_cli code-packet {file_args} --json",
        "history_json": f"{exe} -m src.geoseal_cli history --json",
        "testing_cli_json": f"{exe} -m src.geoseal_cli testing-cli {file_args} --json",
    }

    base_url = os.environ.get("GEOSEAL_SERVICE_URL", "http://127.0.0.1:8765").rstrip(
        "/"
    )
    n8n_bridge = os.environ.get("SCBE_N8N_BRIDGE_URL", "http://127.0.0.1:8001").rstrip(
        "/"
    )

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
    }
