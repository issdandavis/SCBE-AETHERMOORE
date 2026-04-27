"""
SCBE Server Node — runs all services on this machine.

Starts:
  - AetherBrowser WebSocket server (port 8002) — Chrome extension backend
  - Browser Tools API (port 8003) — REST/MCP tool access
  - SCBE API (port 8000) — main governance API

Usage:
    python scripts/server_node.py              # start all
    python scripts/server_node.py --api-only   # just the APIs, no browser
    python scripts/server_node.py --status     # check what's running
    python scripts/server_node.py --stop       # stop all

Environment:
    SCBE_BROWSER_API_KEY  — API key for browser tools (optional)
    SCBE_NODE_HOST        — bind address (default 0.0.0.0)
    SCBE_NODE_NAME        — human-readable node name (default hostname)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("scbe.server_node")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HOST = os.getenv("SCBE_NODE_HOST", "0.0.0.0")
NODE_NAME = os.getenv("SCBE_NODE_NAME", platform.node())

SERVICES = {
    "aetherbrowser": {
        "module": "src.aetherbrowser.serve:app",
        "port": 8002,
        "description": "AetherBrowser WebSocket server (Chrome extension backend)",
    },
    "browser-tools": {
        "module": "agents.browser_api:app",
        "port": 8003,
        "description": "Browser Tools REST/MCP API",
    },
    "api": {
        "module": "src.api.main:app",
        "port": 8000,
        "description": "SCBE Governance API",
    },
}

PID_DIR = ROOT / "artifacts" / "server-node"
STATUS_FILE = PID_DIR / "status.json"


@dataclass
class ServiceStatus:
    name: str
    port: int
    pid: Optional[int] = None
    running: bool = False
    url: str = ""


# ---------------------------------------------------------------------------
# Process management
# ---------------------------------------------------------------------------

def _pid_file(name: str) -> Path:
    return PID_DIR / f"{name}.pid"


def _is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def _start_service(name: str, cfg: dict) -> Optional[int]:
    """Start a uvicorn service in the background."""
    port = cfg["port"]

    if _is_port_in_use(port):
        logger.warning("%s: port %d already in use — skipping", name, port)
        return None

    cmd = [
        sys.executable, "-m", "uvicorn",
        cfg["module"],
        "--host", HOST,
        "--port", str(port),
        "--log-level", "info",
    ]

    log_file = PID_DIR / f"{name}.log"
    log_handle = open(log_file, "w")

    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )

    _pid_file(name).write_text(str(proc.pid))
    logger.info("%s: started (pid=%d, port=%d)", name, proc.pid, port)
    return proc.pid


def _stop_service(name: str) -> bool:
    """Stop a service by PID file."""
    pf = _pid_file(name)
    if not pf.exists():
        return False

    pid = int(pf.read_text().strip())
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                           capture_output=True, timeout=5)
        else:
            os.kill(pid, signal.SIGTERM)
        pf.unlink(missing_ok=True)
        logger.info("%s: stopped (pid=%d)", name, pid)
        return True
    except Exception as exc:
        logger.warning("%s: failed to stop pid %d: %s", name, pid, exc)
        pf.unlink(missing_ok=True)
        return False


def _get_status() -> Dict[str, ServiceStatus]:
    """Check status of all services."""
    statuses = {}
    for name, cfg in SERVICES.items():
        port = cfg["port"]
        running = _is_port_in_use(port)
        pid = None
        pf = _pid_file(name)
        if pf.exists():
            pid = int(pf.read_text().strip())
        statuses[name] = ServiceStatus(
            name=name,
            port=port,
            pid=pid,
            running=running,
            url=f"http://{NODE_NAME}:{port}" if running else "",
        )
    return statuses


def _write_status(statuses: Dict[str, ServiceStatus]) -> None:
    """Write status file for monitoring."""
    data = {
        "node": NODE_NAME,
        "host": HOST,
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "services": {k: asdict(v) for k, v in statuses.items()},
    }
    STATUS_FILE.write_text(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_start(api_only: bool = False) -> None:
    """Start all services."""
    PID_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  SCBE SERVER NODE — {NODE_NAME}")
    print(f"  Host: {HOST}")
    print(f"{'='*60}\n")

    for name, cfg in SERVICES.items():
        if api_only and name == "aetherbrowser":
            continue
        print(f"  Starting {name} ({cfg['description']})...")
        pid = _start_service(name, cfg)
        if pid:
            print(f"    ✓ http://{HOST}:{cfg['port']} (pid {pid})")
        else:
            print(f"    - skipped (port {cfg['port']} in use)")

    # Wait a moment for services to start
    time.sleep(2)

    statuses = _get_status()
    _write_status(statuses)

    print(f"\n{'='*60}")
    running = [s for s in statuses.values() if s.running]
    print(f"  {len(running)}/{len(SERVICES)} services running")
    for s in running:
        print(f"    {s.name}: http://localhost:{s.port}")
    print(f"\n  Status: {STATUS_FILE}")
    print(f"  Logs:   {PID_DIR}/*.log")
    print(f"{'='*60}\n")

    # Print quick-start commands
    print("  Quick access:")
    print(f"    Browser tools: curl http://localhost:8003/tools")
    print(f"    Scrape a page: curl -X POST http://localhost:8003/tools/scrape_page -H 'Content-Type: application/json' -d '{{\"url\":\"https://example.com\"}}'")
    print(f"    Research:      curl -X POST http://localhost:8003/workflow/research -H 'Content-Type: application/json' -d '{{\"query\":\"your topic\"}}'")
    print()


def cmd_status() -> None:
    """Print service status."""
    statuses = _get_status()
    _write_status(statuses)

    print(f"\nSCBE Server Node: {NODE_NAME}")
    print(f"{'─'*50}")
    for s in statuses.values():
        icon = "●" if s.running else "○"
        pid_str = f" (pid {s.pid})" if s.pid else ""
        print(f"  {icon} {s.name:20s} port {s.port:5d}  {'RUNNING' if s.running else 'STOPPED'}{pid_str}")
    print()


def cmd_stop() -> None:
    """Stop all services."""
    print(f"Stopping SCBE server node ({NODE_NAME})...")
    for name in SERVICES:
        _stop_service(name)
    print("All services stopped.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]

    if "--status" in args:
        cmd_status()
    elif "--stop" in args:
        cmd_stop()
    elif "--help" in args or "-h" in args:
        print(__doc__)
    else:
        api_only = "--api-only" in args
        cmd_start(api_only=api_only)


if __name__ == "__main__":
    main()
