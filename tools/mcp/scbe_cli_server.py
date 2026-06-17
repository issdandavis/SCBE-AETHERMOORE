#!/usr/bin/env python3
"""SCBE CLI MCP server — nests every `scbe` tool inside an AI-callable interface.

This is the "programmatic access for AI" layer: it exposes the *real* scbe CLI
commands (discovered from `scbe manifest`) as MCP tools over stdio JSON-RPC, and
on a tool call it actually runs the command and returns the result. Any MCP client
— Claude Desktop, gemini-cli, or the PowerShellSCBE shell's AI — can list and
invoke the SCBE toolset programmatically.

No third-party deps: MCP stdio is newline-delimited JSON-RPC, hand-rolled here so
it runs anywhere Python does.

Run as a server:        python tools/mcp/scbe_cli_server.py
Self-test (no client):  python tools/mcp/scbe_cli_server.py --self-test
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCBE = [sys.executable, str(REPO_ROOT / "scbe.py")]
PROTOCOL_VERSION = "2024-11-05"


def _load_tools() -> list[dict]:
    """Discover the scbe tool catalog via `scbe manifest --json`."""
    proc = subprocess.run(
        SCBE + ["manifest"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    data = json.loads(proc.stdout)
    return data.get("tools", [])


def _to_mcp_tool(tool: dict) -> dict:
    """Render one scbe command as an MCP tool definition (JSON-Schema input)."""
    props: dict[str, Any] = {}
    required: list[str] = []
    for arg in tool.get("args", []):
        is_list = arg.get("nargs") in ("*", "+")
        node: dict[str, Any] = {"type": "array", "items": {"type": arg["type"]}} if is_list else {"type": arg["type"]}
        target = node["items"] if is_list else node
        if arg.get("choices"):
            target["enum"] = arg["choices"]
        if arg.get("description"):
            node["description"] = arg["description"]
        props[arg["name"]] = node
        if arg.get("required"):
            required.append(arg["name"])
    schema: dict[str, Any] = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    return {
        "name": "scbe_" + tool["name"].replace(".", "_").replace("-", "_"),
        "description": (tool.get("summary") or tool["path"]),
        "inputSchema": schema,
    }


def _build_argv(tool: dict, arguments: dict) -> list[str]:
    """Turn an MCP tool call (name + JSON args) into a real scbe argv."""
    argv = tool["path"].split(" ")
    for arg in tool.get("args", []):
        name = arg["name"]
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
        return {"content": [{"type": "text", "text": f"unknown tool: {name}"}], "isError": True}
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
        result = {
            "protocolVersion": PROTOCOL_VERSION,
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
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "method": method}}
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def serve() -> int:
    tools = _load_tools()
    tools_by_name = {"scbe_" + t["name"].replace(".", "_").replace("-", "_"): t for t in tools}
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = _handle(request, tools, tools_by_name)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
    return 0


def self_test() -> int:
    """Exercise initialize + tools/list + a real tools/call without a client."""
    tools = _load_tools()
    by_name = {"scbe_" + t["name"].replace(".", "_").replace("-", "_"): t for t in tools}
    init = _handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"}, tools, by_name)
    listed = _handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, tools, by_name)
    n = len(listed["result"]["tools"])
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
    ok = init["result"]["serverInfo"]["name"] == "scbe-cli" and n > 0 and not call["result"].get("isError")
    print("initialize: ok")
    print(f"tools/list: {n} SCBE tools exposed")
    print(f"tools/call scbe_score(text='hello world') -> {out[:120]}")
    print("SELF-TEST PASSED" if ok else "SELF-TEST FAILED")
    return 0 if ok else 1


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
