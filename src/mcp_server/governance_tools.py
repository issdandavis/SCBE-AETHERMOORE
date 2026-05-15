"""SCBE Governance MCP Tools.

Exposes trap_dispatch, workspace_new, and governance_check as MCP tools so
Claude Code, Cursor, Windsurf, and any MCP-compatible orchestrator can use
SCBE governance natively.

Run alongside semantic_mesh:
    python -m src.mcp_server.governance_tools

Or add to your MCP config:
    {
      "mcpServers": {
        "scbe-governance": {
          "command": "python",
          "args": ["-m", "src.mcp_server.governance_tools"],
          "cwd": "C:/Users/issda/SCBE-AETHERMOORE"
        }
      }
    }
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types as mcp_types

    _HAS_MCP = True
except ImportError:
    _HAS_MCP = False


# ---------------------------------------------------------------------------
# Tool implementations (callable without MCP runtime for testing)
# ---------------------------------------------------------------------------


def _tool_trap_dispatch(input_text: str, provider: str = "offline") -> dict:
    """Run input through the trap-in-good-loops gate.

    Returns scbe.trap_dispatch.v1 envelope with gate_decision (ALLOW/DENY),
    redirect_emitted, and for ALLOW: dispatched_prompt_sha256.
    """
    try:
        from scbe_agent_bus import trap_dispatch

        return trap_dispatch(input_text, provider=provider)
    except ImportError:
        pass

    # Inline fallback: shell to the CLI directly
    import shutil
    import subprocess

    bin_path = os.environ.get("SCBE_CLI_BIN", "")
    if not bin_path:
        found = shutil.which("scbe") or shutil.which("scbe.cmd")
        if not found:
            return {
                "schema_version": "scbe.trap_dispatch.v1",
                "gate_decision": "ERROR",
                "error": "scbe CLI not found — install via npm i -g scbe-aethermoore-cli or set SCBE_CLI_BIN",
            }
        bin_path = found

    argv = [bin_path, "trap-dispatch", "--provider", provider, "--input", input_text, "--json"]
    node = shutil.which("node") or "node"
    if bin_path.endswith((".js", ".cjs", ".mjs")):
        argv = [node] + argv

    result = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=False)
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return {"schema_version": "scbe.trap_dispatch.v1", "gate_decision": "ERROR", "raw": result.stdout[:200]}


def _tool_workspace_new(hint: str = "", root: str = "") -> dict:
    """Form a new governed workspace and return its audit-chain receipt."""
    try:
        from scbe_agent_bus import workspace_new

        return workspace_new(hint=hint or None, root=root or None)
    except ImportError:
        pass

    import shutil
    import subprocess

    bin_path = os.environ.get("SCBE_AGENT_BUS_BIN", "")
    if not bin_path:
        found = shutil.which("scbe-agent-bus") or shutil.which("scbe-agent-bus.cmd")
        if not found:
            return {"receipt": "ERROR", "error": "scbe-agent-bus CLI not found"}
        bin_path = found

    argv = [bin_path, "workspace", "new", "--json"]
    if hint:
        argv += ["--hint", hint]
    if root:
        argv += ["--root", root]
    node = shutil.which("node") or "node"
    if bin_path.endswith((".js", ".cjs", ".mjs")):
        argv = [node] + argv

    result = subprocess.run(argv, capture_output=True, text=True, timeout=30, check=False)
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return {"receipt": "ERROR", "raw": result.stdout[:200]}


def _tool_governance_check(text: str) -> dict:
    """Score a text against the 14-layer SCBE pipeline.

    Returns decision (ALLOW/QUARANTINE/ESCALATE/DENY), risk_score, and
    harmonic_factor without dispatching to any LLM.
    """
    import hashlib
    import numpy as np

    try:
        from src.scbe_14layer_reference import scbe_14layer_pipeline

        hash_bytes = hashlib.sha256(text.encode()).digest()
        position = [int(b) % 100 for b in hash_bytes[:6]]
        result = scbe_14layer_pipeline(t=np.array(position, dtype=float), D=6)
        return {
            "decision": result["decision"],
            "risk_score": float(result["risk_base"]),
            "harmonic_factor": float(result["H"]),
            "d_star": float(result["d_star"]),
            "input_sha256": hashlib.sha256(text.encode()).hexdigest(),
        }
    except Exception as exc:
        return {"decision": "ERROR", "error": str(exc)}


# ---------------------------------------------------------------------------
# MCP server wiring
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "scbe_trap_dispatch",
        "description": (
            "Run a prompt through the SCBE trap-in-good-loops governance gate. "
            "Returns gate_decision=ALLOW or DENY with a redirect prompt for adversarial inputs. "
            "Use before dispatching any user-supplied text to an LLM."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "input_text": {"type": "string", "description": "The prompt or text to gate"},
                "provider": {
                    "type": "string",
                    "enum": ["offline", "ollama"],
                    "default": "offline",
                    "description": "Provider to use for ALLOW path. 'offline' is zero-cost echo.",
                },
            },
            "required": ["input_text"],
        },
    },
    {
        "name": "scbe_workspace_new",
        "description": (
            "Create a new governed workspace with a sha256 audit chain. "
            "Returns workspace_root, workspace_id, and created_at. "
            "Use before ingesting files or dispatching prompts you want auditable."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "hint": {"type": "string", "description": "Short label for the workspace (e.g. 'code-review')"},
                "root": {"type": "string", "description": "Parent directory for the workspace (optional)"},
            },
        },
    },
    {
        "name": "scbe_governance_check",
        "description": (
            "Score any text through the 14-layer SCBE pipeline and return a governance decision "
            "(ALLOW/QUARANTINE/ESCALATE/DENY) with risk_score and harmonic_factor. "
            "No LLM call is made — pure geometric scoring."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to score"},
            },
            "required": ["text"],
        },
    },
]


def _dispatch(tool_name: str, args: dict) -> Any:
    if tool_name == "scbe_trap_dispatch":
        return _tool_trap_dispatch(
            input_text=args["input_text"],
            provider=args.get("provider", "offline"),
        )
    if tool_name == "scbe_workspace_new":
        return _tool_workspace_new(
            hint=args.get("hint", ""),
            root=args.get("root", ""),
        )
    if tool_name == "scbe_governance_check":
        return _tool_governance_check(text=args["text"])
    return {"error": f"unknown tool: {tool_name}"}


async def _run_server() -> None:
    if not _HAS_MCP:
        print(
            "ERROR: mcp package not installed. Run: pip install mcp",
            file=sys.stderr,
        )
        sys.exit(1)

    server = Server("scbe-governance")

    @server.list_tools()
    async def list_tools():
        return [
            mcp_types.Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"],
            )
            for t in TOOLS
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        result = _dispatch(name, arguments)
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]

    async with stdio_server() as streams:
        await server.run(*streams, server.create_initialization_options())


def main() -> None:
    import asyncio

    asyncio.run(_run_server())


if __name__ == "__main__":
    main()
