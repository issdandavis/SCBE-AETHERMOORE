"""
Telegram <-> AetherBrowse Bridge
===================================
When a Telegram message requests a web task, route it through
AetherBrowse's planner and execute via the browser worker.

Examples:
  User on Telegram: "upload my governance toolkit to Shopify"
  → Bridge sends task to AetherBrowse runtime (port 8400)
  → Planner generates steps → Worker executes → Result sent back to Telegram

  User on Telegram: "check my Shopify store status"
  → Bridge navigates to Shopify, takes snapshot, summarizes via AI
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

logger = logging.getLogger("telegram-aetherbrowse")

try:
    import websockets
    HAS_WS = True
except ImportError:
    HAS_WS = False

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


# Web task keywords that trigger AetherBrowse
WEB_TASK_PATTERNS = [
    "upload", "navigate", "go to", "open", "check", "shopify",
    "gumroad", "browse", "screenshot", "scrape", "fill", "submit",
    "codespace", "code space", "notebook", "lm notebook", "lm-notebook", "lmnotebook", "notebooklm",
    "github", "git", "telegram", "issue", "pull request", "pr",
    "download", "search the web", "look up online",
]


def is_web_task(text: str) -> bool:
    """Detect if a message should be routed to AetherBrowse."""
    text_lower = text.lower()
    return any(pattern in text_lower for pattern in WEB_TASK_PATTERNS)


async def send_to_aetherbrowse(command: str) -> dict:
    """Send a command to AetherBrowse runtime via HTTP."""
    url = "http://127.0.0.1:8400"
    cmd_payload = {"text": command, "source": "telegram"}

    # First check if AetherBrowse is running
    try:
        if HAS_AIOHTTP:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=3)) as resp:
                    health = await resp.json()
                    if health.get("status") != "ok":
                        return {"error": "AetherBrowse runtime not healthy"}
        else:
            # Fallback: use urllib
            import urllib.request
            req = urllib.request.Request(f"{url}/health")
            with urllib.request.urlopen(req, timeout=3) as resp:
                health = json.loads(resp.read())
    except Exception:
        return {"error": "AetherBrowse runtime not reachable on port 8400"}

    # Send command via HTTP first (newest path)
    try:
        if HAS_AIOHTTP:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{url}/command",
                    json=cmd_payload,
                    timeout=aiohttp.ClientTimeout(total=3),
                ) as resp:
                    payload = await resp.json()
                    if resp.status >= 400:
                        return {"error": payload.get("message", "Command endpoint returned error")}
                    return payload
    except Exception as e:
        logger.debug("HTTP /command failed: %s", e)

    # Fallback: send command via WebSocket
    if HAS_WS:
        try:
            async with websockets.connect(f"ws://127.0.0.1:8400/ws") as ws:
                await ws.send(json.dumps({
                    "type": "user-command",
                    "text": command,
                    "source": "telegram",
                }))

                # Wait for response (with timeout)
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=30)
                    return json.loads(response)
                except asyncio.TimeoutError:
                    return {"status": "submitted", "message": "Task submitted, executing in background"}
        except Exception as e:
            return {"error": f"WebSocket connection failed: {str(e)}"}

    return {"error": "No WebSocket client available"}


async def check_governance(action: str, selector: str, context: str) -> dict:
    """Check governance via Hydra Armor API."""
    url = "http://127.0.0.1:8400/v1/armor/verify"

    payload = json.dumps({
        "agent_id": "telegram-bridge",
        "action": action,
        "selector": selector,
        "context": context,
    }).encode()

    try:
        import urllib.request
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"decision": "ALLOW", "reason": f"Governance unreachable: {e}", "risk_score": 0.5}


async def process_web_task(text: str) -> str:
    """Process a web task from Telegram and return a summary."""
    # Check governance first
    gov = await check_governance("evaluate", "", text)
    if gov.get("decision") == "DENY":
        return f"Task blocked by governance: {gov.get('reason', 'high risk')}"

    # Send to AetherBrowse
    result = await send_to_aetherbrowse(text)

    if "error" in result:
        return f"AetherBrowse error: {result['error']}"

    if result.get("status") == "submitted":
        return "Task submitted to AetherBrowse. Working on it..."

    # Format result for Telegram
    return json.dumps(result, indent=2)[:3000]
