"""
Telegram <-> SCBE Service Connector
=====================================
Connects Telegram bridge to all running SCBE services:
  - AetherNet (8300): AI social feed, agent registration, XP economy
  - AetherBrowse (8400): Browser automation, web tasks
  - SCBE Bridge (8001): Governance, tongue encoding, training ingestion

Runs as a background task inside the Telegram bot, polling services
and routing messages between them.
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("telegram-connector")

ROOT = Path(__file__).resolve().parent.parent

SERVICE_ENDPOINTS = {
    "aethernet": "http://127.0.0.1:8300",
    "aetherbrowse": "http://127.0.0.1:8400",
    "bridge": "http://127.0.0.1:8001",
    "telegram_webhook": "http://127.0.0.1:8500",
}


async def _http_post(url: str, data: dict, timeout: float = 10.0) -> dict:
    """POST JSON to a service endpoint."""
    import urllib.request
    payload = json.dumps(data).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=timeout))
        return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


async def _http_get(url: str, timeout: float = 5.0) -> dict:
    """GET from a service endpoint."""
    import urllib.request
    req = urllib.request.Request(url)
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=timeout))
        return json.loads(resp.read())
    except Exception:
        return {"status": "unreachable"}


class ServiceConnector:
    """Manages connections between Telegram and SCBE services."""

    def __init__(self):
        self._service_status: dict = {}
        self._agent_id: str = "telegram-bridge"
        self._registered = False

    async def discover_services(self) -> dict:
        """Check which SCBE services are online."""
        status = {}
        for name, base_url in SERVICE_ENDPOINTS.items():
            health = await _http_get(f"{base_url}/health")
            status[name] = {
                "url": base_url,
                "online": health.get("status") == "ok" or "status" in health,
                "details": health,
            }
        self._service_status = status
        return status

    async def register_with_aethernet(self) -> dict:
        """Register the Telegram bridge as an agent on AetherNet."""
        if self._registered:
            return {"status": "already_registered"}

        url = f"{SERVICE_ENDPOINTS['aethernet']}/v1/agents/register"
        result = await _http_post(url, {
            "name": "Telegram Bridge",
            "agent_type": "connector",
            "capabilities": ["messaging", "governance", "web_tasks", "training_data"],
            "metadata": {"platform": "telegram", "version": "1.0"},
        })

        if "error" not in result:
            self._registered = True
            self._agent_id = result.get("agent_id", self._agent_id)
            logger.info(f"Registered with AetherNet as {self._agent_id}")

        return result

    async def post_to_aethernet(self, text: str, channel: str = "general") -> dict:
        """Post a message to AetherNet feed from Telegram."""
        url = f"{SERVICE_ENDPOINTS['aethernet']}/v1/feed/post"
        return await _http_post(url, {
            "agent_id": self._agent_id,
            "content": text,
            "channel": channel,
            "source": "telegram",
        })

    async def send_to_aetherbrowse(self, command: str) -> dict:
        """Send a web task to AetherBrowse runtime."""
        url = f"{SERVICE_ENDPOINTS['aetherbrowse']}/health"
        health = await _http_get(url)
        if health.get("status") != "ok":
            return {"error": "AetherBrowse not available"}

        # Use WebSocket for commands
        try:
            import websockets
            async with websockets.connect("ws://127.0.0.1:8400/ws") as ws:
                await ws.send(json.dumps({
                    "type": "user-command",
                    "text": command,
                    "source": "telegram",
                }))
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=30)
                    return json.loads(response)
                except asyncio.TimeoutError:
                    return {"status": "submitted", "message": "Task running in background"}
        except ImportError:
            return {"error": "websockets not installed"}
        except Exception as e:
            return {"error": str(e)}

    async def governance_scan(self, text: str) -> dict:
        """Run governance scan via SCBE Bridge."""
        url = f"{SERVICE_ENDPOINTS['bridge']}/v1/governance/scan"
        return await _http_post(url, {
            "text": text,
            "source": "telegram",
            "agent_id": self._agent_id,
        })

    async def tongue_encode(self, text: str, tongue: str = "KO") -> dict:
        """Encode text through Sacred Tongue via SCBE Bridge."""
        url = f"{SERVICE_ENDPOINTS['bridge']}/v1/tongue/encode"
        return await _http_post(url, {
            "text": text,
            "tongue": tongue,
        })

    async def push_training_data(self, pairs: list[dict]) -> dict:
        """Push training pairs to SCBE Bridge for ingestion."""
        url = f"{SERVICE_ENDPOINTS['bridge']}/v1/training/ingest"
        return await _http_post(url, {
            "pairs": pairs,
            "source": "telegram",
        })

    def format_status(self) -> str:
        """Format service status for Telegram display."""
        lines = ["**SCBE Service Status**\n"]
        for name, info in self._service_status.items():
            icon = "+" if info["online"] else "-"
            lines.append(f"`[{icon}]` **{name}** — {'online' if info['online'] else 'offline'}")
        return "\n".join(lines)


# Global connector instance
connector = ServiceConnector()
