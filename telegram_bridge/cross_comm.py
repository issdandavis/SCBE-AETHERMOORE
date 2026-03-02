"""
SCBE Cross-Communication Hub
================================
Unified message bus connecting all SCBE services and external platforms.
Every message is governed, logged for training, and routable across:

  - Telegram (bot API)
  - AetherNet (AI social feed)
  - AetherBrowse (browser automation results)
  - Claude Code (terminal/IDE)
  - n8n Bridge (workflow automation)
  - Future: Discord, Slack, WhatsApp, Signal

Unlike OpenClaw (simple message → LLM → reply), SCBE cross-comm:
  1. Routes through 14-layer governance on EVERY message
  2. Uses multi-model OctoArmor (11 free/cheap providers)
  3. Generates SFT training pairs from every interaction
  4. Supports multi-agent coordination (not just 1:1 chat)
  5. Integrates browser automation for real-world tasks
  6. Sacred Tongue encoding for semantic compression

Start: python telegram_bridge/cross_comm.py
"""

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("scbe-crosscomm")


class Platform(str, Enum):
    TELEGRAM = "telegram"
    AETHERNET = "aethernet"
    AETHERBROWSE = "aetherbrowse"
    CLAUDE_CODE = "claude_code"
    N8N = "n8n"
    DISCORD = "discord"
    SLACK = "slack"
    WEBHOOK = "webhook"


@dataclass
class CrossMessage:
    """A message flowing through the cross-comm hub."""
    text: str
    source: Platform
    source_id: str = ""           # chat_id, agent_id, channel, etc.
    sender_name: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)
    governance: dict = field(default_factory=dict)
    reply_to: Optional[str] = None  # message ID being replied to
    msg_id: str = field(default_factory=lambda: f"msg_{int(time.time()*1000)}")

    def to_dict(self) -> dict:
        return {
            "msg_id": self.msg_id,
            "text": self.text,
            "source": self.source.value,
            "source_id": self.source_id,
            "sender_name": self.sender_name,
            "timestamp": self.timestamp,
            "governance": self.governance,
            "metadata": self.metadata,
        }


@dataclass
class RouteRule:
    """A rule for routing messages between platforms."""
    source: Platform
    target: Platform
    condition: Optional[Callable[[CrossMessage], bool]] = None
    transform: Optional[Callable[[CrossMessage], CrossMessage]] = None
    enabled: bool = True


class CrossCommHub:
    """Central message bus for cross-platform communication."""

    def __init__(self):
        self._routes: list[RouteRule] = []
        self._handlers: dict[Platform, Callable] = {}
        self._message_log: list[dict] = []
        self._training_path = ROOT / "training-data" / "crosscomm" / "messages.jsonl"
        self._training_path.parent.mkdir(parents=True, exist_ok=True)
        self._bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self._owner_chat_id = os.environ.get("TELEGRAM_OWNER_ID", "")

        # Import governance
        try:
            from telegram_bridge.bot_service import govern_incoming, govern_outgoing
            self._govern_in = govern_incoming
            self._govern_out = govern_outgoing
        except ImportError:
            self._govern_in = lambda text, sid, oid: {"decision": "ALLOW", "risk_score": 0.1}
            self._govern_out = lambda text, ctx="": {"decision": "ALLOW", "risk_score": 0.05}

    # ------------------------------------------------------------------
    #  Route management
    # ------------------------------------------------------------------

    def add_route(self, source: Platform, target: Platform,
                  condition: Callable = None, transform: Callable = None):
        """Add a routing rule."""
        self._routes.append(RouteRule(
            source=source, target=target,
            condition=condition, transform=transform,
        ))

    def register_handler(self, platform: Platform, handler: Callable):
        """Register a send handler for a platform."""
        self._handlers[platform] = handler

    # ------------------------------------------------------------------
    #  Message processing
    # ------------------------------------------------------------------

    async def process(self, message: CrossMessage) -> list[dict]:
        """Process a message through governance and routing."""
        # Step 1: Govern incoming
        gov = self._govern_in(message.text, 0, 0)
        message.governance = gov

        if gov["decision"] == "DENY":
            self._log_message(message, "blocked")
            return [{"target": "blocked", "reason": gov["reason"]}]

        # Step 2: Find matching routes
        results = []
        for route in self._routes:
            if not route.enabled:
                continue
            if route.source != message.source:
                continue
            if route.condition and not route.condition(message):
                continue

            # Transform message for target
            target_msg = message
            if route.transform:
                target_msg = route.transform(message)

            # Govern outgoing
            gov_out = self._govern_out(target_msg.text)
            if gov_out["decision"] == "DENY":
                results.append({"target": route.target.value, "status": "blocked_outgoing"})
                continue

            # Deliver
            handler = self._handlers.get(route.target)
            if handler:
                try:
                    result = await handler(target_msg)
                    results.append({
                        "target": route.target.value,
                        "status": "delivered",
                        "result": result,
                    })
                except Exception as e:
                    results.append({
                        "target": route.target.value,
                        "status": "error",
                        "error": str(e),
                    })
            else:
                results.append({"target": route.target.value, "status": "no_handler"})

        self._log_message(message, "routed", results)
        return results

    async def send_to_telegram(self, message: CrossMessage) -> dict:
        """Send a message to Telegram."""
        import urllib.request
        chat_id = message.metadata.get("chat_id") or self._owner_chat_id
        if not chat_id:
            return {"error": "no chat_id"}

        text = message.text
        if message.source != Platform.TELEGRAM:
            text = f"[{message.source.value}] {message.sender_name}: {text}"

        if len(text) > 4000:
            text = text[:3997] + "..."

        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        payload = json.dumps({
            "chat_id": int(chat_id),
            "text": text,
            "parse_mode": "Markdown",
        }).encode()

        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"})
        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=10)
            )
            return json.loads(resp.read())
        except Exception as e:
            return {"error": str(e)}

    async def send_to_aethernet(self, message: CrossMessage) -> dict:
        """Post to AetherNet feed."""
        import urllib.request
        url = "http://127.0.0.1:8300/v1/feed/post"
        payload = json.dumps({
            "agent_id": f"crosscomm-{message.source.value}",
            "content": message.text,
            "channel": message.metadata.get("channel", "general"),
            "source": message.source.value,
        }).encode()

        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"})
        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=10)
            )
            return json.loads(resp.read())
        except Exception as e:
            return {"error": str(e)}

    async def send_to_github(self, message: CrossMessage) -> dict:
        """Post to GitHub — issues, comments, or discussions."""
        import urllib.request
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            return {"error": "GITHUB_TOKEN not set"}

        repo = message.metadata.get("repo", "issdandavis/SCBE-AETHERMOORE")
        action = message.metadata.get("action", "comment")

        if action == "issue":
            url = f"https://api.github.com/repos/{repo}/issues"
            payload = json.dumps({
                "title": message.metadata.get("title", message.text[:80]),
                "body": message.text,
                "labels": message.metadata.get("labels", ["from-crosscomm"]),
            }).encode()
        elif action == "comment" and message.metadata.get("issue_number"):
            issue = message.metadata["issue_number"]
            url = f"https://api.github.com/repos/{repo}/issues/{issue}/comments"
            payload = json.dumps({"body": message.text}).encode()
        else:
            return {"error": "Specify action='issue' or action='comment' with issue_number"}

        req = urllib.request.Request(
            url, data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=15)
            )
            return json.loads(resp.read())
        except Exception as e:
            return {"error": str(e)}

    async def send_to_slack(self, message: CrossMessage) -> dict:
        """Send message to Slack via webhook or API."""
        import urllib.request

        # Try webhook first (simpler)
        webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
        if webhook_url:
            text = message.text
            if message.source != Platform.SLACK:
                text = f"*[{message.source.value}]* {message.sender_name}: {text}"

            payload = json.dumps({"text": text}).encode()
            req = urllib.request.Request(
                webhook_url, data=payload,
                headers={"Content-Type": "application/json"},
            )
            try:
                loop = asyncio.get_event_loop()
                resp = await loop.run_in_executor(
                    None, lambda: urllib.request.urlopen(req, timeout=10)
                )
                return {"status": "sent", "method": "webhook"}
            except Exception as e:
                return {"error": str(e)}

        # Try Slack Bot Token API
        slack_token = os.environ.get("SLACK_BOT_TOKEN", "")
        channel = message.metadata.get("channel", os.environ.get("SLACK_CHANNEL", ""))
        if slack_token and channel:
            url = "https://slack.com/api/chat.postMessage"
            payload = json.dumps({
                "channel": channel,
                "text": message.text,
            }).encode()
            req = urllib.request.Request(
                url, data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {slack_token}",
                },
            )
            try:
                loop = asyncio.get_event_loop()
                resp = await loop.run_in_executor(
                    None, lambda: urllib.request.urlopen(req, timeout=10)
                )
                return json.loads(resp.read())
            except Exception as e:
                return {"error": str(e)}

        return {"error": "Set SLACK_WEBHOOK_URL or SLACK_BOT_TOKEN + SLACK_CHANNEL"}

    async def send_to_aetherbrowse(self, message: CrossMessage) -> dict:
        """Send web task to AetherBrowse."""
        try:
            import websockets
            async with websockets.connect("ws://127.0.0.1:8400/ws") as ws:
                await ws.send(json.dumps({
                    "type": "user-command",
                    "text": message.text,
                    "source": message.source.value,
                }))
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=30)
                    return json.loads(response)
                except asyncio.TimeoutError:
                    return {"status": "submitted"}
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    #  Convenience methods for Claude Code to send messages
    # ------------------------------------------------------------------

    async def notify_telegram(self, text: str, chat_id: str = ""):
        """Send a notification from Claude Code to Telegram."""
        msg = CrossMessage(
            text=text,
            source=Platform.CLAUDE_CODE,
            sender_name="Claude",
            metadata={"chat_id": chat_id or self._owner_chat_id},
        )
        return await self.send_to_telegram(msg)

    async def broadcast(self, text: str, targets: list[Platform] = None):
        """Broadcast a message to multiple platforms."""
        if targets is None:
            targets = [Platform.TELEGRAM, Platform.AETHERNET]

        results = {}
        for target in targets:
            msg = CrossMessage(
                text=text,
                source=Platform.CLAUDE_CODE,
                sender_name="Claude",
            )
            handler = self._handlers.get(target)
            if handler:
                results[target.value] = await handler(msg)
        return results

    # ------------------------------------------------------------------
    #  Training data
    # ------------------------------------------------------------------

    def _log_message(self, message: CrossMessage, status: str, routes: list = None):
        """Log every message for training data."""
        entry = {
            "timestamp": time.time(),
            "msg_id": message.msg_id,
            "text": message.text[:2000],
            "source": message.source.value,
            "sender": message.sender_name,
            "governance": message.governance,
            "status": status,
            "routes": routes or [],
        }
        self._message_log.append(entry)
        with open(self._training_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------
    #  Default route setup
    # ------------------------------------------------------------------

    def setup_default_routes(self):
        """Configure standard cross-comm routes."""
        # Register all platform handlers
        self.register_handler(Platform.TELEGRAM, self.send_to_telegram)
        self.register_handler(Platform.AETHERNET, self.send_to_aethernet)
        self.register_handler(Platform.AETHERBROWSE, self.send_to_aetherbrowse)
        self.register_handler(Platform.SLACK, self.send_to_slack)
        self.register_handler(Platform.DISCORD, self.send_to_slack)  # reuse Slack webhook for now

        # --- Claude Code outbound ---
        self.add_route(Platform.CLAUDE_CODE, Platform.TELEGRAM)
        self.add_route(Platform.CLAUDE_CODE, Platform.AETHERNET)

        # --- AetherBrowse results → Telegram ---
        self.add_route(Platform.AETHERBROWSE, Platform.TELEGRAM)

        # --- AetherNet high-priority → Telegram ---
        self.add_route(
            Platform.AETHERNET, Platform.TELEGRAM,
            condition=lambda m: m.metadata.get("priority", "low") in ("high", "critical"),
        )

        # --- n8n workflow results → Telegram ---
        self.add_route(Platform.N8N, Platform.TELEGRAM)

        # --- Telegram → Slack (forward important messages) ---
        self.add_route(
            Platform.TELEGRAM, Platform.SLACK,
            condition=lambda m: m.metadata.get("forward_to_slack", False),
        )

        # --- Telegram → GitHub (create issues from Telegram) ---
        def is_github_task(m):
            text = m.text.lower()
            return any(kw in text for kw in ["bug:", "issue:", "feature:", "todo:"])
        self.add_route(Platform.TELEGRAM, Platform.DISCORD,  # placeholder
                       condition=is_github_task)

        logger.info(f"Configured {len(self._routes)} routes, {len(self._handlers)} handlers")


# ---------------------------------------------------------------------------
#  Global hub instance
# ---------------------------------------------------------------------------

def create_hub() -> CrossCommHub:
    """Create and configure a CrossCommHub."""
    # Load .env
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

    hub = CrossCommHub()
    hub.setup_default_routes()
    return hub


# Lazy global
_hub: Optional[CrossCommHub] = None


def get_hub() -> CrossCommHub:
    """Get or create the global hub."""
    global _hub
    if _hub is None:
        _hub = create_hub()
    return _hub
