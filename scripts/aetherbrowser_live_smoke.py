#!/usr/bin/env python3
"""Live smoke runner for the AetherBrowser backend WebSocket flow."""

from __future__ import annotations

import argparse
import asyncio
import json
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import websockets


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8002


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ws_message(seq: int, msg_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": msg_type,
        "agent": "user",
        "payload": payload,
        "ts": datetime.now(timezone.utc).isoformat(),
        "seq": seq,
    }


def port_in_use(host: str, port: int) -> bool:
    sock = socket.socket()
    try:
        sock.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def start_server(host: str, port: int, python_executable: str) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [
            python_executable,
            "-m",
            "uvicorn",
            "src.aetherbrowser.serve:app",
            "--host",
            host,
            "--port",
            str(port),
        ],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def wait_for_health(host: str, port: int, timeout_seconds: float = 20.0) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    url = f"http://{host}:{port}/health"
    last_error = "unknown"
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=2.0)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # pragma: no cover - timing dependent
            last_error = str(exc)
            time.sleep(0.3)
    raise RuntimeError(f"AetherBrowser health never became ready at {url}: {last_error}")


async def read_messages(ws: Any, count: int) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for _ in range(count):
        raw = await ws.recv()
        messages.append(json.loads(raw))
    return messages


def summarize_research_flow(messages: list[dict[str, Any]]) -> dict[str, Any]:
    execution = next(
        (
            msg["payload"]["execution"]
            for msg in messages
            if msg.get("type") == "chat" and isinstance(msg.get("payload"), dict) and "execution" in msg["payload"]
        ),
        {},
    )
    plan = next(
        (
            msg["payload"]["plan"]
            for msg in messages
            if msg.get("type") == "chat" and isinstance(msg.get("payload"), dict) and "plan" in msg["payload"]
        ),
        {},
    )
    return {
        "message_count": len(messages),
        "execution_provider": execution.get("provider"),
        "execution_model": execution.get("model_id"),
        "fallback_used": execution.get("fallback_used"),
        "plan_provider": plan.get("provider"),
        "plan_risk_tier": plan.get("risk_tier"),
        "status_sequence": [
            msg.get("payload", {}).get("state") for msg in messages if msg.get("type") == "agent_status"
        ],
    }


def summarize_zone_gate(
    initial_messages: list[dict[str, Any]], resumed_messages: list[dict[str, Any]]
) -> dict[str, Any]:
    zone_request = next((msg for msg in initial_messages if msg.get("type") == "zone_request"), {})
    resumed_execution = next(
        (
            msg["payload"]["execution"]
            for msg in resumed_messages
            if msg.get("type") == "chat" and isinstance(msg.get("payload"), dict) and "execution" in msg["payload"]
        ),
        {},
    )
    return {
        "zone": zone_request.get("zone"),
        "request_seq": zone_request.get("seq"),
        "initial_states": [
            msg.get("payload", {}).get("state") for msg in initial_messages if msg.get("type") == "agent_status"
        ],
        "resumed_states": [
            msg.get("payload", {}).get("state") for msg in resumed_messages if msg.get("type") == "agent_status"
        ],
        "execution_provider": resumed_execution.get("provider"),
        "execution_model": resumed_execution.get("model_id"),
    }


def summarize_page_flow(messages: list[dict[str, Any]]) -> dict[str, Any]:
    analysis = next(
        (
            msg["payload"]["page_analysis"]
            for msg in messages
            if msg.get("type") == "chat" and isinstance(msg.get("payload"), dict) and "page_analysis" in msg["payload"]
        ),
        {},
    )
    return {
        "message_count": len(messages),
        "title": analysis.get("title"),
        "risk_tier": analysis.get("risk_tier"),
        "intent": analysis.get("intent"),
        "topics": analysis.get("topics", []),
        "next_actions": [
            action.get("label") for action in analysis.get("next_actions", []) if isinstance(action, dict)
        ],
    }


async def run_ws_smoke(host: str, port: int) -> dict[str, Any]:
    ws_url = f"ws://{host}:{port}/ws"
    async with websockets.connect(ws_url) as ws:
        seq = 1

        await ws.send(
            json.dumps(
                ws_message(
                    seq,
                    "command",
                    {
                        "text": "Research hyperbolic competitors",
                        "routing": {
                            "preferences": {"KO": "local"},
                            "auto_cascade": True,
                        },
                    },
                )
            )
        )
        research_messages = await read_messages(ws, 9)

        seq += 1
        await ws.send(
            json.dumps(
                ws_message(
                    seq,
                    "command",
                    {
                        "text": "Open the browser tab, fill the login form, and submit it",
                        "routing": {
                            "preferences": {"KO": "local"},
                            "auto_cascade": True,
                        },
                    },
                )
            )
        )
        zone_initial = await read_messages(ws, 4)
        zone_request = next(msg for msg in zone_initial if msg.get("type") == "zone_request")

        seq += 1
        await ws.send(
            json.dumps(
                ws_message(
                    seq,
                    "zone_response",
                    {
                        "request_seq": zone_request["seq"],
                        "decision": "allow_once",
                    },
                )
            )
        )
        zone_resumed = await read_messages(ws, 6)

        seq += 1
        await ws.send(
            json.dumps(
                ws_message(
                    seq,
                    "page_context",
                    {
                        "url": "https://example.com/ai-safety",
                        "title": "AI Safety Research",
                        "text": (
                            "Machine learning security requires governance frameworks. "
                            "Neural networks need adversarial defense mechanisms. "
                            "Hyperbolic geometry provides exponential cost scaling."
                        ),
                        "headings": ["AI Safety Research"],
                        "links": [{"text": "Example", "href": "https://example.com"}],
                        "buttons": [{"text": "Submit"}],
                        "forms": [{"action": "/submit", "method": "post"}],
                        "selection": "Hyperbolic geometry provides exponential cost scaling.",
                        "page_type": "article",
                        "tabs": [{"title": "AI Safety Research", "url": "https://example.com/ai-safety"}],
                        "screenshot": "",
                    },
                )
            )
        )
        page_messages = await read_messages(ws, 4)

    return {
        "research_flow": summarize_research_flow(research_messages),
        "zone_gate_flow": summarize_zone_gate(zone_initial, zone_resumed),
        "page_flow": summarize_page_flow(page_messages),
    }


def write_report(output_dir: Path, report: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "live_smoke_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a live AetherBrowser backend smoke flow.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--python", dest="python_executable", default=sys.executable)
    parser.add_argument("--reuse-running-server", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    timestamp = utc_stamp()
    output_dir = PROJECT_ROOT / "artifacts" / "smokes" / f"aetherbrowser-live-{timestamp}"

    server_proc: subprocess.Popen[str] | None = None
    started_server = False
    startup_tail = ""

    try:
        if port_in_use(args.host, args.port):
            if not args.reuse_running_server:
                raise RuntimeError(
                    f"Port {args.port} is already in use. Re-run with --reuse-running-server to attach to it."
                )
        else:
            server_proc = start_server(args.host, args.port, args.python_executable)
            started_server = True

        health = wait_for_health(args.host, args.port)
        smoke = asyncio.run(run_ws_smoke(args.host, args.port))
        report = {
            "timestamp_utc": timestamp,
            "host": args.host,
            "port": args.port,
            "started_server": started_server,
            "health": health,
            "smoke": smoke,
        }

        report_path = write_report(output_dir, report)
        if args.json:
            print(json.dumps({"report_path": str(report_path), **report}, indent=2))
        else:
            print(f"AetherBrowser live smoke passed. Report: {report_path}")
        return 0
    finally:
        if server_proc is not None:
            server_proc.terminate()
            try:
                stdout, _ = server_proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                server_proc.kill()
                stdout, _ = server_proc.communicate()
            startup_tail = (stdout or "")[-4000:]
            try:
                server_proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
        if startup_tail:
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "server_output.log").write_text(startup_tail, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
