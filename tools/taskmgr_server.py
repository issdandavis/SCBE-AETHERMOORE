"""HTTP intermediary for the Task Manager backend.

Exposes `tools.taskmgr_core` over HTTP/JSON so multiple AI models
(Claude, GPT, local Ollama models, the SCBE agent fleet, n8n) can
all call the same endpoints without each needing direct psutil access.

Stdlib only -- no FastAPI, no Flask. Single file, ~200 lines.

Endpoints:
    GET  /health                 -- liveness probe
    GET  /tools                  -- OpenAI-style function descriptors,
                                    so any function-calling model can
                                    introspect the available actions
    GET  /procs?filter=&top=     -- list_processes (read-only)
    GET  /agents                 -- list_agents (read-only)
    GET  /system                 -- system_info (read-only)
    GET  /scbe                   -- scbe_state (read-only)
    GET  /sample?seconds=1.0     -- sample_cpu_mem_net (read-only)
    POST /kill {pid, tree, dry_run} -- terminate (REQUIRES write token)

Auth model:
    Read endpoints: open by default, optional --read-token tightens.
    Write endpoints (/kill): always require --write-token, refuses
    if no token configured.

Bind:
    127.0.0.1:8765 by default. Pass --host 0.0.0.0 for LAN exposure
    (use a write-token if you do).

Usage:
    python -m tools.taskmgr_server                       # localhost, read-open
    python -m tools.taskmgr_server --write-token SECRET
    python -m tools.taskmgr_server --port 9000 --read-token READSEC --write-token WRITESEC

Client examples are in `tools/taskmgr_client_examples.md`.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlsplit

from tools import taskmgr_core as core

# ============================================================
# Tool manifest -- what an AI agent gets when calling /tools.
# Shape matches OpenAI function-calling so most function-calling
# models (Claude tool_use, OpenAI tools, local function-calling
# wrappers) can consume it directly.
# ============================================================
TOOL_MANIFEST = [
    {
        "name": "list_processes",
        "description": "List all running processes on the machine, with PID, name, user, CPU%, and memory usage. Optionally filter by substring.",
        "endpoint": {"method": "GET", "path": "/procs"},
        "parameters": {
            "type": "object",
            "properties": {
                "filter": {"type": "string", "description": "case-insensitive substring filter against name/pid/user"},
                "top": {"type": "integer", "description": "return only the top N processes by CPU%"},
            },
            "required": [],
        },
    },
    {
        "name": "list_agents",
        "description": "List AI agent processes (Ollama, Claude Code, SCBE agents, n8n bridge) with their cmdlines and open files.",
        "endpoint": {"method": "GET", "path": "/agents"},
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "system_info",
        "description": "Return architecture: OS, machine, processor, Python, CPU phys/logical/freq, memory, disks, network interfaces.",
        "endpoint": {"method": "GET", "path": "/system"},
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "scbe_state",
        "description": "Return SCBE-specific state: package version, current git branch, available local Ollama models.",
        "endpoint": {"method": "GET", "path": "/scbe"},
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "sample_cpu_mem_net",
        "description": "Take a single CPU+memory+network sample over the given duration in seconds.",
        "endpoint": {"method": "GET", "path": "/sample"},
        "parameters": {
            "type": "object",
            "properties": {
                "seconds": {"type": "number", "description": "sampling window, default 1.0", "default": 1.0},
            },
            "required": [],
        },
    },
    {
        "name": "kill_process",
        "description": "Terminate a process by PID, optionally including its children. REQUIRES a write token. Use dry_run=true to preview.",
        "endpoint": {"method": "POST", "path": "/kill"},
        "parameters": {
            "type": "object",
            "properties": {
                "pid": {"type": "integer", "description": "process id to terminate"},
                "tree": {"type": "boolean", "description": "also terminate descendant processes", "default": False},
                "dry_run": {
                    "type": "boolean",
                    "description": "report what would be killed without doing it",
                    "default": False,
                },
            },
            "required": ["pid"],
        },
    },
]


# ============================================================
# Handler.
# ============================================================
def _to_jsonable(obj: Any) -> Any:
    """Coerce dataclasses + nested structures to JSON-friendly dicts."""
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    if isinstance(obj, list):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    return obj


class TaskMgrHandler(BaseHTTPRequestHandler):
    # Set by the server factory; per-request access via self.server.
    server_version = "scbe-taskmgr/1.0"

    # Quiet down the default request logging spam.
    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write(f"[taskmgr_server] {self.address_string()} {format % args}\n")

    # --- helpers ----------------------------------------------------
    def _check_token(self, *, write: bool) -> bool:
        cfg = self.server.taskmgr_config  # type: ignore[attr-defined]
        required = cfg["write_token"] if write else cfg["read_token"]
        if not required:
            return True  # no token configured -> open
        got = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if got == required:
            return True
        self._send_json(401, {"error": "missing or invalid bearer token"})
        return False

    def _send_json(self, status: int, body: Any) -> None:
        payload = json.dumps(_to_jsonable(body), indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("X-Server", self.server_version)
        self.end_headers()
        self.wfile.write(payload)

    def _read_json(self) -> Optional[Dict[str, Any]]:
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            n = 0
        if n <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._send_json(400, {"error": f"invalid JSON: {exc}"})
            return None

    # --- routing ----------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        u = urlsplit(self.path)
        params = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path == "/health":
            return self._send_json(200, {"ok": True, "version": self.server_version})
        if u.path == "/tools":
            return self._send_json(200, {"tools": TOOL_MANIFEST})
        if not self._check_token(write=False):
            return
        if u.path == "/procs":
            top = int(params.get("top", 0)) if params.get("top") else 0
            rows = core.list_processes(filter=params.get("filter", ""))
            rows.sort(key=lambda p: -p.cpu_percent)
            if top:
                rows = rows[:top]
            return self._send_json(200, rows)
        if u.path == "/agents":
            return self._send_json(200, core.list_agents())
        if u.path == "/system":
            return self._send_json(200, core.system_info())
        if u.path == "/scbe":
            return self._send_json(200, dict(core.scbe_state()))
        if u.path == "/sample":
            secs = float(params.get("seconds", "1.0") or "1.0")
            return self._send_json(200, core.sample_cpu_mem_net(seconds=secs))
        return self._send_json(404, {"error": f"unknown route: {u.path}"})

    def do_POST(self) -> None:  # noqa: N802
        u = urlsplit(self.path)
        if u.path != "/kill":
            return self._send_json(404, {"error": f"unknown POST route: {u.path}"})
        # /kill always requires write-token; refuses if none configured.
        cfg = self.server.taskmgr_config  # type: ignore[attr-defined]
        if not cfg["write_token"]:
            return self._send_json(
                403,
                {"error": "/kill is disabled: server has no write_token configured. Restart with --write-token."},
            )
        if not self._check_token(write=True):
            return
        body = self._read_json()
        if body is None:
            return  # _read_json already replied
        pid = body.get("pid")
        if not isinstance(pid, int):
            return self._send_json(400, {"error": "body must contain integer pid"})
        result = core.kill_process(pid, tree=bool(body.get("tree", False)), dry_run=bool(body.get("dry_run", False)))
        return self._send_json(200, result)


# ============================================================
# Server factory + CLI.
# ============================================================
def serve(*, host: str = "127.0.0.1", port: int = 8765, read_token: str = "", write_token: str = "") -> None:
    httpd = ThreadingHTTPServer((host, port), TaskMgrHandler)
    httpd.taskmgr_config = {  # type: ignore[attr-defined]
        "read_token": read_token,
        "write_token": write_token,
    }
    auth_summary = (
        f"read={'token' if read_token else 'open'} "
        f"write={'token' if write_token else 'DISABLED (no token configured)'}"
    )
    print(f"[taskmgr_server] listening on http://{host}:{port}  ({auth_summary})", file=sys.stderr)
    print(f"[taskmgr_server] manifest at http://{host}:{port}/tools", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[taskmgr_server] shutting down", file=sys.stderr)
    finally:
        httpd.server_close()


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(prog="taskmgr_server", description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--read-token", default="", help="bearer token required for read endpoints (empty = open)")
    ap.add_argument(
        "--write-token",
        default="",
        help="bearer token required for /kill. If empty, /kill is disabled (returns 403).",
    )
    args = ap.parse_args(argv)
    serve(host=args.host, port=args.port, read_token=args.read_token, write_token=args.write_token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
