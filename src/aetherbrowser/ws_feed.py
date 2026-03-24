"""
WebSocket message protocol for the AetherBrowser sidebar.

All messages follow a single schema:
  { type, agent, model, zone, payload, ts, seq }
"""

from __future__ import annotations

import json
import time
from enum import Enum
from typing import Any

MAX_MESSAGE_SIZE = 1_048_576  # 1 MB


class MsgType(str, Enum):
    COMMAND = "command"
    CHAT = "chat"
    AGENT_STATUS = "agent_status"
    PROGRESS = "progress"
    ZONE_REQUEST = "zone_request"
    ZONE_RESPONSE = "zone_response"
    PAGE_CONTEXT = "page_context"
    TOPOLOGY = "topology"
    ERROR = "error"


class Agent(str, Enum):
    KO = "KO"
    AV = "AV"
    RU = "RU"
    CA = "CA"
    UM = "UM"
    DR = "DR"
    USER = "user"
    SYSTEM = "system"


class Zone(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class WsFeed:
    """Factory for creating and parsing WebSocket messages."""

    def __init__(self):
        self._seq = 0

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _base(self, msg_type: MsgType, agent: Agent, **kwargs) -> dict[str, Any]:
        return {
            "type": msg_type.value,
            "agent": agent.value,
            "model": kwargs.get("model"),
            "zone": kwargs.get("zone"),
            "payload": kwargs.get("payload", {}),
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "seq": self._next_seq(),
        }

    def chat(
        self,
        agent: Agent,
        text: str,
        model: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict:
        merged_payload = {"text": text}
        if payload:
            merged_payload.update(payload)
        return self._base(MsgType.CHAT, agent, model=model, payload=merged_payload)

    def agent_status(self, agent: Agent, state: str, model: str | None = None) -> dict:
        return self._base(MsgType.AGENT_STATUS, agent, model=model, payload={"state": state})

    def zone_request(self, agent: Agent, zone: Zone, *, url: str, action: str, description: str) -> dict:
        return self._base(
            MsgType.ZONE_REQUEST,
            agent,
            zone=zone.value,
            payload={"url": url, "action": action, "description": description},
        )

    def progress(self, agent: Agent, *, current: int, total: int, label: str = "") -> dict:
        return self._base(MsgType.PROGRESS, agent, payload={"current": current, "total": total, "label": label})

    def error(self, reason: str, agent: Agent = Agent.SYSTEM) -> dict:
        return self._base(MsgType.ERROR, agent, payload={"reason": reason})

    @staticmethod
    def parse(raw: str) -> dict:
        if len(raw) > MAX_MESSAGE_SIZE:
            raise ValueError("Message oversized")
        msg = json.loads(raw)
        valid_types = {t.value for t in MsgType}
        if msg.get("type") not in valid_types:
            raise ValueError(f"Invalid message type: {msg.get('type')}")
        return msg
