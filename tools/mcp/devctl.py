#!/usr/bin/env python3
"""devctl -- one command to start / stop / tunnel the SCBE MCP servers, so you never juggle ports and
processes by hand again.

    python tools/mcp/devctl.py start            # launch the SSE servers, record their pids
    python tools/mcp/devctl.py status           # what's up, on which port, is it really ours
    python tools/mcp/devctl.py stop             # stop ONLY what we started (safe)
    python tools/mcp/devctl.py tunnel scbe-verify   # cloudflared quick tunnel + the Grok-ready URL

SAFETY: `stop` never blind-kills a PID. It only terminates a process that is BOTH the pid we recorded
AND the process currently listening on that server's port -- so a reused PID (some unrelated program)
is left alone. State is a json file in your home dir, shared across checkouts (slice-wt and the main
repo). No psutil / no extra deps; port ownership is read from the OS (Get-NetTCPConnection / lsof / ss).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

_REPO = Path(__file__).resolve().parents[2]
_STATE = Path.home() / ".scbe_mcp_devctl.json"
_TRANSPORT_PATH = {"sse": "/sse", "streamable-http": "/mcp"}


@dataclass(frozen=True)
class ServerSpec:
    name: str
    module: str  # path relative to the repo root
    port: int
    transport: str = "sse"


# the registry of HTTP-exposed MCP servers devctl manages (stdio servers are launched per-client by the
# MCP client itself, so they need no hosting). Add a line here to manage another server.
SERVERS: Dict[str, ServerSpec] = {
    "scbe-verify": ServerSpec("scbe-verify", "src/mcp/scbe_verify_mcp.py", 8765, "sse"),
}


# --- OS helpers (no psutil) -------------------------------------------------------------------------


def _port_owner(port: int) -> Optional[int]:
    """The PID currently LISTENING on `port`, or None. This is the safety anchor for stop()."""
    try:
        if os.name == "nt":
            out = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "(Get-NetTCPConnection -LocalPort %d -State Listen -ErrorAction SilentlyContinue"
                    " | Select-Object -First 1).OwningProcess" % port,
                ],
                capture_output=True,
                text=True,
                timeout=15,
            ).stdout.strip()
            return int(out) if out.isdigit() else None
        # POSIX: prefer lsof, fall back to ss
        out = subprocess.run(
            ["lsof", "-ti", "tcp:%d" % port, "-sTCP:LISTEN"], capture_output=True, text=True, timeout=15
        ).stdout.strip()
        if out:
            return int(out.splitlines()[0])
        ss = subprocess.run(["ss", "-ltnHp"], capture_output=True, text=True, timeout=15).stdout
        for line in ss.splitlines():
            if ":%d " % port in line:
                m = re.search(r"pid=(\d+)", line)
                if m:
                    return int(m.group(1))
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        return None
    return None


def _alive(pid: int) -> bool:
    if os.name == "nt":
        out = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid, "/NH"], capture_output=True, text=True).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _terminate(pid: int) -> bool:
    """Stop a process we've already CONFIRMED is ours (it owns our port). Safe to force here."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True)
        else:
            import signal

            os.kill(pid, signal.SIGTERM)
            for _ in range(20):
                if not _alive(pid):
                    break
                time.sleep(0.1)
            if _alive(pid):
                os.kill(pid, signal.SIGKILL)
        return not _alive(pid)
    except (OSError, subprocess.SubprocessError):
        return False


# --- state ------------------------------------------------------------------------------------------


def _log_path(name: str) -> Path:
    return Path.home() / (".scbe_mcp_%s.log" % re.sub(r"[^A-Za-z0-9_.-]", "_", name))


def _tail(path: Path, n: int) -> List[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    except OSError:
        return ["(no log)"]


def _load_state() -> Dict[str, dict]:
    if _STATE.exists():
        try:
            return json.loads(_STATE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_state(state: Dict[str, dict]) -> None:
    _STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# --- commands ---------------------------------------------------------------------------------------


def cmd_start(names: List[str], registry: Dict[str, ServerSpec] = None) -> int:
    registry = registry or SERVERS
    targets = names or list(registry)
    state = _load_state()
    for name in targets:
        spec = registry.get(name)
        if not spec:
            print("  ?? unknown server %r (have %s)" % (name, ", ".join(registry)))
            continue
        owner = _port_owner(spec.port)
        if owner is not None:
            print("  ~~ %s: port %d already in use by pid %d -- skipping (use stop first)" % (name, spec.port, owner))
            continue
        env = {**os.environ, "SCBE_MCP_PORT": str(spec.port)}
        # redirect the child's output to a log file -- it gives the detached process VALID stdio handles
        # (a fully-detached process gets invalid handles and uvicorn crashes writing its startup logs),
        # and it lets us show WHY a start failed instead of a useless "check the server".
        log_path = _log_path(name)
        log = open(log_path, "a", encoding="utf-8")
        flags = 0
        if os.name == "nt":  # own process group + no console window; survives this devctl exiting
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.Popen(
            [sys.executable, str(_REPO / spec.module), "--transport", spec.transport],
            env=env,
            cwd=str(_REPO),
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=flags if os.name == "nt" else 0,
            start_new_session=(os.name != "nt"),
        )
        log.close()  # the child has inherited its own handle
        # readiness: poll the port (~25s; the server's first import is heavy) until it binds or dies
        up = False
        for _ in range(50):
            if _port_owner(spec.port) is not None:
                up = True
                break
            if proc.poll() is not None:
                break
            time.sleep(0.5)
        state[name] = {
            "pid": proc.pid,
            "port": spec.port,
            "transport": spec.transport,
            "module": spec.module,
            "log": str(log_path),
        }
        _save_state(state)
        path = _TRANSPORT_PATH.get(spec.transport, "/sse")
        if up:
            print("  ok %s: pid %d on http://127.0.0.1:%d%s" % (name, proc.pid, spec.port, path))
        else:
            print("  !! %s: pid %d did NOT bind port %d. Last log lines:" % (name, proc.pid, spec.port))
            for ln in _tail(log_path, 8):
                print("       " + ln)
    return 0


def cmd_stop(names: List[str]) -> int:
    state = _load_state()
    targets = names or list(state)
    if not targets:
        print("  nothing recorded as running")
        return 0
    for name in targets:
        rec = state.get(name)
        if not rec:
            print("  -- %s: not in state (already stopped?)" % name)
            continue
        pid, port = rec["pid"], rec["port"]
        owner = _port_owner(port)
        if owner is None and not _alive(pid):
            print("  -- %s: already gone (pid %d, port %d)" % (name, pid, port))
        elif owner == pid:  # the SAFE case: this pid really is the one serving our port
            ok = _terminate(pid)
            print("  %s %s: stopped pid %d (was serving port %d)" % ("ok" if ok else "!!", name, pid, port))
        else:
            # the recorded pid is NOT the owner of the port -> a reused PID. Do not touch it.
            print(
                "  ~~ %s: recorded pid %d does NOT own port %d (owner=%s) -- leaving it ALONE (PID reuse)"
                % (name, pid, port, owner)
            )
        state.pop(name, None)
        _save_state(state)
    return 0


def cmd_status(_names: List[str] = None) -> int:
    state = _load_state()
    if not state:
        print("  no SCBE MCP servers recorded as running")
        return 0
    for name, rec in state.items():
        pid, port = rec["pid"], rec["port"]
        owner = _port_owner(port)
        path = _TRANSPORT_PATH.get(rec.get("transport", "sse"), "/sse")
        if owner == pid:
            print("  UP   %-12s pid %-7d http://127.0.0.1:%d%s" % (name, pid, port, path))
        elif owner is not None:
            print("  STALE %-11s recorded pid %d but port %d is owned by pid %d (not ours)" % (name, pid, port, owner))
        else:
            print("  DOWN %-12s recorded pid %d, nothing on port %d" % (name, pid, port))
    return 0


def cmd_tunnel(names: List[str]) -> int:
    name = names[0] if names else "scbe-verify"
    rec = _load_state().get(name)
    spec = SERVERS.get(name)
    port = rec["port"] if rec else (spec.port if spec else None)
    transport = (rec or {}).get("transport") or (spec.transport if spec else "sse")
    if port is None:
        print("  ?? unknown server %r" % name)
        return 1
    if _port_owner(port) is None:
        print("  !! nothing is serving port %d -- run `devctl start %s` first" % (port, name))
        return 1
    path = _TRANSPORT_PATH.get(transport, "/sse")
    print("  starting cloudflared quick tunnel -> http://localhost:%d (Ctrl+C to stop)" % port)
    print("  when the URL appears, give Grok:  <that-url>%s" % path)
    try:
        proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", "http://localhost:%d" % port],
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        print("  !! cloudflared not found. Install it (Windows: winget install --id Cloudflare.cloudflared),")
        print("     then re-run. Or use stdio locally (no tunnel needed for Claude Code).")
        return 1
    seen = False
    try:
        for line in proc.stdout:  # tee cloudflared output, surface the public URL with the right path
            sys.stdout.write(line)
            m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if m and not seen:
                seen = True
                print("\n  >>> GROK URL:  %s%s\n" % (m.group(0), path))
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        print("\n  tunnel stopped.")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="devctl", description="start/stop/tunnel the SCBE MCP servers")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("start", "stop", "status", "tunnel"):
        p = sub.add_parser(c)
        p.add_argument("names", nargs="*", help="server name(s); default = all (tunnel = scbe-verify)")
    a = ap.parse_args(argv)
    return {"start": cmd_start, "stop": cmd_stop, "status": cmd_status, "tunnel": cmd_tunnel}[a.cmd](a.names)


if __name__ == "__main__":
    raise SystemExit(main())
