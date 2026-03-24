"""
Agent Squad Orchestration
==========================

Manages the 6 Sacred Tongue agents. KO leads, others specialize.
Task decomposition assigns agents based on task type and content.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.aetherbrowser.ws_feed import WsFeed


class TongueRole(str, Enum):
    KO = "KO"
    AV = "AV"
    RU = "RU"
    CA = "CA"
    UM = "UM"
    DR = "DR"


class AgentState(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    DONE = "done"
    ERROR = "error"


@dataclass
class AgentInfo:
    role: TongueRole
    state: AgentState = AgentState.IDLE
    model: str | None = None
    current_task: str | None = None


_TASK_ROLES: dict[str, list[TongueRole]] = {
    "research": [TongueRole.KO, TongueRole.AV, TongueRole.CA, TongueRole.RU, TongueRole.DR],
    "page":     [TongueRole.KO, TongueRole.CA, TongueRole.DR],
    "default":  [TongueRole.KO, TongueRole.AV, TongueRole.CA],
}

_RESEARCH_KEYWORDS = {"research", "find", "search", "compare", "investigate", "competitors", "analyze"}
_PAGE_KEYWORDS = {"page", "summarize", "extract", "this"}


class AgentSquad:
    def __init__(self, feed: WsFeed):
        self.feed = feed
        self.agents: dict[TongueRole, AgentInfo] = {
            role: AgentInfo(role=role) for role in TongueRole
        }

    def set_state(self, role: TongueRole, state: AgentState, model: str | None = None) -> None:
        self.agents[role].state = state
        if model:
            self.agents[role].model = model

    def status_snapshot(self) -> dict[TongueRole, dict[str, Any]]:
        return {
            role: {"state": info.state.value, "model": info.model, "task": info.current_task}
            for role, info in self.agents.items()
        }

    def decompose(self, text: str, task_type: str | None = None) -> list[dict[str, Any]]:
        if task_type is None:
            task_type = self.infer_task_type(text)
        roles = _TASK_ROLES.get(task_type, _TASK_ROLES["default"])
        assignments = []
        for role in roles:
            assignments.append({
                "role": role,
                "task": self._role_task_description(role, text),
            })
        return assignments

    def infer_task_type(self, text: str) -> str:
        words = set(text.lower().split())
        if words & _RESEARCH_KEYWORDS:
            return "research"
        if words & _PAGE_KEYWORDS:
            return "page"
        return "default"

    def _role_task_description(self, role: TongueRole, text: str) -> str:
        descs = {
            TongueRole.KO: f"Orchestrate and synthesize: {text}",
            TongueRole.AV: f"Scout and discover URLs for: {text}",
            TongueRole.RU: f"Check safety of discovered URLs",
            TongueRole.CA: f"Extract content from approved URLs",
            TongueRole.UM: f"Shadow observation (stealth mode)",
            TongueRole.DR: f"Structure findings into summary",
        }
        return descs.get(role, text)
