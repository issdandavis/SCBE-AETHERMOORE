#!/usr/bin/env python3
"""SCBE CLI MCP server — exposes the scbe tools as an AI-callable interface.

The "programmatic access for AI" layer: it surfaces the *real* scbe CLI commands
(discovered from `scbe manifest`) as MCP tools over stdio JSON-RPC, and on a tool
call it runs the command and returns the result. Any MCP client — Claude Desktop,
gemini-cli, or the PowerShellSCBE shell's AI — can list and invoke them.

Scope (honest): this implements the MCP **tools** capability over stdio only
(no resources/prompts/progress/cancellation). It negotiates the protocol version
from the client's `initialize`, falling back to the pinned default.

Safety: destructive commands (del/push/move/undo) are **excluded by default** —
an AI caller cannot list or invoke them. Set `SCBE_MCP_ALLOW_DESTRUCTIVE=1` to
expose them; even then the human-confirmation flags (`yes`/`force`/`confirm`) are
never advertised or forwarded, so a destructive command still hits its interactive
confirm (which declines in this non-interactive context). Honors the project's
never-let-AI-delete charter.

No third-party deps: MCP stdio is newline-delimited JSON-RPC, hand-rolled here so
it runs anywhere Python does.

Run as a server:        python tools/mcp/scbe_cli_server.py
Self-test (no client):  python tools/mcp/scbe_cli_server.py --self-test
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCBE = [sys.executable, str(REPO_ROOT / "scbe.py")]
PROTOCOL_VERSION = "2024-11-05"

# Commands that mutate the filesystem / repo: not auto-exposed to AI callers.
_DESTRUCTIVE_TOOLS = {"del", "push", "move", "undo"}
# Human-in-the-loop confirmation flags: never advertised or forwarded over MCP.
_CONFIRM_BYPASS_FLAGS = {"yes", "force", "confirm"}


def _allow_destructive() -> bool:
    return os.environ.get("SCBE_MCP_ALLOW_DESTRUCTIVE", "").strip().lower() in {"1", "true", "yes", "on"}


def _is_destructive(tool: dict) -> bool:
    """A tool is destructive if it's a known mutating command or exposes a confirm-bypass flag."""
    if tool.get("path", "").split(" ")[0] in _DESTRUCTIVE_TOOLS:
        return True
    return any(a.get("name") in _CONFIRM_BYPASS_FLAGS for a in tool.get("args", []))


def _tool_id(tool: dict) -> str:
    return "scbe_" + tool["name"].replace(".", "_").replace("-", "_")


def _load_tools() -> list[dict]:
    """Discover the scbe tool catalog via `scbe manifest`; degrade to [] on failure."""
    try:
        proc = subprocess.run(SCBE + ["manifest"], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60)
        return json.loads(proc.stdout).get("tools", [])
    except Exception as exc:  # noqa: BLE001 - stay up with an empty catalog rather than crash at startup
        print(f"scbe-cli: failed to load tool manifest: {exc}", file=sys.stderr)
        return []


def _exposed_tools(tools: list[dict]) -> list[dict]:
    """The AI-callable subset — destructive commands hidden unless explicitly opted in."""
    if _allow_destructive():
        return tools
    return [t for t in tools if not _is_destructive(t)]


def _to_mcp_tool(tool: dict) -> dict:
    """Render one scbe command as an MCP tool definition (JSON-Schema input).

    Mirrors the canonical `scbe manifest --format mcp` schema: includes `default`
    values and `additionalProperties: false`, and omits confirm-bypass flags.
    """
    props: dict[str, Any] = {}
    required: list[str] = []
    for arg in tool.get("args", []):
        if arg.get("name") in _CONFIRM_BYPASS_FLAGS:
            continue  # never advertise a human-confirmation-bypass flag to an AI
        is_list = arg.get("nargs") in ("*", "+")
        node: dict[str, Any] = {"type": "array", "items": {"type": arg["type"]}} if is_list else {"type": arg["type"]}
        target = node["items"] if is_list else node
        if arg.get("choices"):
            target["enum"] = arg["choices"]
        if arg.get("description"):
            node["description"] = arg["description"]
        if arg.get("default") is not None:
            node["default"] = arg["default"]
        props[arg["name"]] = node
        if arg.get("required"):
            required.append(arg["name"])
    schema: dict[str, Any] = {"type": "object", "properties": props, "additionalProperties": False}
    if required:
        schema["required"] = required
    return {
        "name": _tool_id(tool),
        "description": (tool.get("summary") or tool["path"]),
        "inputSchema": schema,
    }


def _build_argv(tool: dict, arguments: dict) -> list[str]:
    """Turn an MCP tool call (name + JSON args) into a real scbe argv."""
    argv = tool["path"].split(" ")
    for arg in tool.get("args", []):
        name = arg["name"]
        if name in _CONFIRM_BYPASS_FLAGS:
            continue  # never let an AI caller bypass human confirmation
        if name not in arguments:
            continue
        value = arguments[name]
        if arg.get("kind") == "flag":
            flag = (arg.get("flags") or ["--" + name])[0]
            if arg["type"] == "boolean":
                if value:
                    argv.append(flag)
            else:
                argv += [flag, str(value)]
        else:  # positional
            if isinstance(value, list):
                argv += [str(v) for v in value]
            else:
                argv.append(str(value))
    if tool.get("supports_json"):
        argv.append("--json")
    return argv


def _run_tool(tools_by_name: dict, name: str, arguments: dict) -> dict:
    """Execute a tool call; return an MCP tool result (content + isError)."""
    tool = tools_by_name.get(name)
    if tool is None:
        return {"content": [{"type": "text", "text": f"unknown or unavailable tool: {name}"}], "isError": True}
    argv = _build_argv(tool, arguments or {})
    try:
        proc = subprocess.run(SCBE + argv, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=240)
    except Exception as exc:  # noqa: BLE001 - report any spawn failure to the caller
        return {"content": [{"type": "text", "text": f"exec error: {exc}"}], "isError": True}
    out = proc.stdout.strip() or proc.stderr.strip()
    return {"content": [{"type": "text", "text": out}], "isError": proc.returncode != 0}


def _handle(request: dict, tools: list[dict], tools_by_name: dict) -> dict | None:
    method = request.get("method")
    rid = request.get("id")
    if method == "initialize":
        params = request.get("params") or {}
        client_version = params.get("protocolVersion")
        result = {
            "protocolVersion": client_version or PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "scbe-cli", "version": "1.0.0"},
        }
    elif method == "tools/list":
        result = {"tools": [_to_mcp_tool(t) for t in tools]}
    elif method == "tools/call":
        params = request.get("params") or {}
        result = _run_tool(tools_by_name, params.get("name", ""), params.get("arguments") or {})
    elif method in ("notifications/initialized", "initialized"):
        return None  # notification, no response
    else:
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def serve() -> int:
    tools = _exposed_tools(_load_tools())
    tools_by_name = {_tool_id(t): t for t in tools}
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            response = _handle(request, tools, tools_by_name)
        except Exception as exc:  # noqa: BLE001 - one bad request must not drop the server
            rid = request.get("id") if isinstance(request, dict) else None
            response = {"jsonrpc": "2.0", "id": rid, "error": {"code": -32603, "message": f"internal error: {exc}"}}
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
    return 0


def self_test() -> int:
    """Exercise initialize + tools/list + a real tools/call, and assert safety filtering."""
    all_tools = _load_tools()
    tools = _exposed_tools(all_tools)
    by_name = {_tool_id(t): t for t in tools}
    init = _handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"}, tools, by_name)
    listed = _handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, tools, by_name)
    n = len(listed["result"]["tools"])
    hidden = len(all_tools) - len(tools)
    call = _handle(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "scbe_score", "arguments": {"text": "hello world"}},
        },
        tools,
        by_name,
    )
    out = call["result"]["content"][0]["text"]
    destructive_hidden = "scbe_del" not in by_name and "scbe_push" not in by_name
    ok = (
        init["result"]["serverInfo"]["name"] == "scbe-cli"
        and n > 0
        and not call["result"].get("isError")
        and destructive_hidden
    )
    print("initialize: ok")
    print(f"tools/list: {n} SCBE tools exposed ({hidden} destructive hidden by default)")
    print(f"safety: scbe_del / scbe_push excluded = {destructive_hidden}")
    print(f"tools/call scbe_score(text='hello world') -> {out[:120]}")
    print("SELF-TEST PASSED" if ok else "SELF-TEST FAILED")
    return 0 if ok else 1


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
