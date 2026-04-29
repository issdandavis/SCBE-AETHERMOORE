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


def _exe() -> str:
    return shlex.quote(sys.executable)


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
