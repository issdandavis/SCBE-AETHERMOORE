"""
Switchboard — WW2-Style Operator Task Routing for Multi-LLM Fleet
=================================================================

Like a WW2 telephone switchboard operator, the Switchboard receives
incoming tasks and plugs them into the right line (LLM provider).

Architecture:
    TASK IN → Classify → Route → Execute → Notice Board → RESULT OUT

The Notice Board is a shared billboard where all agents post their
status, results, and availability. Any agent can read any other agent's
posts. This creates emergent coordination without central control.

Routing priorities:
1. FREE first (HuggingFace Inference, Ollama local, Google Colab)
2. CHEAP second (Gemini Flash, GPT-4o-mini)
3. PREMIUM last (Claude Opus, GPT-4o, Grok)

Task types route to specific tongues/providers:
- CODE → CA tongue (compute) → GPT-4o or Grok (code-strong)
- RESEARCH → RU tongue (security) → Perplexity or Grok (web-connected)
- CREATIVE → AV tongue (creative) → Claude or Gemini
- GOVERNANCE → UM tongue (governance) → Claude (reasoning-strong)
- ANALYSIS → KO tongue (intent) → GPT-4o or Claude
- ARCHITECTURE → DR tongue (structure) → Claude or Grok

@module fleet/switchboard
@layer Layer 13
@patent USPTO #63/961,403
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .model_matrix import (
    ModelMatrix, ModelProvider, ModelConfig, ModelNode,
    _PROVIDER_DISPATCH, _mock,
)


# ═══════════════════════════════════════════════════════════════
# Task Classification
# ═══════════════════════════════════════════════════════════════

class TaskType(str, Enum):
    CODE = "code"
    RESEARCH = "research"
    CREATIVE = "creative"
    GOVERNANCE = "governance"
    ANALYSIS = "analysis"
    ARCHITECTURE = "architecture"
    TRANSLATION = "translation"
    SUMMARIZE = "summarize"
    GENERAL = "general"


class CostTier(str, Enum):
    FREE = "free"           # HuggingFace, Ollama, Colab
    CHEAP = "cheap"         # Gemini Flash, GPT-4o-mini
    STANDARD = "standard"   # GPT-4o, Grok
    PREMIUM = "premium"     # Claude Opus, GPT-4-turbo


class TaskPriority(str, Enum):
    LOW = "low"             # Can wait, use free tier
    NORMAL = "normal"       # Use cheapest available
    HIGH = "high"           # Use best available
    URGENT = "urgent"       # Use premium, no delay


# Cost estimates per 1K tokens (approximate, USD)
PROVIDER_COSTS = {
    ModelProvider.OLLAMA: 0.0,         # Free (local)
    ModelProvider.HUGGINGFACE: 0.0,    # Free tier
    ModelProvider.GEMINI: 0.0001,      # Flash is nearly free
    ModelProvider.OPENAI: 0.005,       # GPT-4o
    ModelProvider.XAI: 0.005,          # Grok
    ModelProvider.CLAUDE: 0.015,       # Sonnet
    ModelProvider.LOCAL: 0.0,          # Free (local)
    ModelProvider.LLAMA: 0.0,          # Via Ollama
    ModelProvider.MISTRAL: 0.0,        # Via Ollama
}


# ═══════════════════════════════════════════════════════════════
# Notice Board — Shared Billboard for Agent Communication
# ═══════════════════════════════════════════════════════════════

@dataclass
class Notice:
    """A single post on the notice board."""
    notice_id: str
    author: str             # Provider or agent name
    task_id: str
    status: str             # "available", "working", "done", "error", "waiting"
    message: str
    result: Optional[str] = None
    cost_estimate: float = 0.0
    posted_at: float = field(default_factory=time.time)
    expires_at: float = 0.0  # 0 = no expiry
    tags: List[str] = field(default_factory=list)

    def is_expired(self) -> bool:
        return self.expires_at > 0 and time.time() > self.expires_at


class NoticeBoard:
    """Shared communication board — any agent can post, any agent can read.

    Like the notice board in a WW2 command center:
    - Operators post task status
    - Commanders post priorities
    - Field agents post results
    - Everyone can see everything
    """

    def __init__(self, max_notices: int = 1000):
        self._notices: Dict[str, Notice] = {}
        self._max = max_notices

    def post(
        self,
        author: str,
        task_id: str,
        status: str,
        message: str,
        result: Optional[str] = None,
        cost: float = 0.0,
        ttl: float = 3600.0,  # 1 hour default
        tags: Optional[List[str]] = None,
    ) -> str:
        """Post a notice. Returns the notice_id."""
        nid = f"notice-{uuid.uuid4().hex[:8]}"
        notice = Notice(
            notice_id=nid,
            author=author,
            task_id=task_id,
            status=status,
            message=message,
            result=result,
            cost_estimate=cost,
            expires_at=time.time() + ttl if ttl > 0 else 0,
            tags=tags or [],
        )
        self._notices[nid] = notice
        self._prune()
        return nid

    def read_all(self, include_expired: bool = False) -> List[Notice]:
        """Read all current notices."""
        if include_expired:
            return list(self._notices.values())
        return [n for n in self._notices.values() if not n.is_expired()]

    def read_by_task(self, task_id: str) -> List[Notice]:
        """Read all notices for a specific task."""
        return [n for n in self._notices.values()
                if n.task_id == task_id and not n.is_expired()]

    def read_by_author(self, author: str) -> List[Notice]:
        """Read all notices from a specific author/agent."""
        return [n for n in self._notices.values()
                if n.author == author and not n.is_expired()]

    def read_by_tag(self, tag: str) -> List[Notice]:
        """Read all notices with a specific tag."""
        return [n for n in self._notices.values()
                if tag in n.tags and not n.is_expired()]

    def read_available(self) -> List[Notice]:
        """Read all 'available' status notices (idle agents)."""
        return [n for n in self._notices.values()
                if n.status == "available" and not n.is_expired()]

    def clear_task(self, task_id: str) -> int:
        """Clear all notices for a completed task."""
        to_remove = [nid for nid, n in self._notices.items() if n.task_id == task_id]
        for nid in to_remove:
            del self._notices[nid]
        return len(to_remove)

    def summary(self) -> Dict[str, Any]:
        """Board summary — how many notices by status."""
        active = [n for n in self._notices.values() if not n.is_expired()]
        by_status: Dict[str, int] = {}
        by_author: Dict[str, int] = {}
        for n in active:
            by_status[n.status] = by_status.get(n.status, 0) + 1
            by_author[n.author] = by_author.get(n.author, 0) + 1
        return {
            "total_active": len(active),
            "total_all": len(self._notices),
            "by_status": by_status,
            "by_author": by_author,
        }

    def _prune(self) -> None:
        """Remove expired notices and keep under max."""
        # Remove expired
        expired = [nid for nid, n in self._notices.items() if n.is_expired()]
        for nid in expired:
            del self._notices[nid]
        # Cap at max
        if len(self._notices) > self._max:
            sorted_notices = sorted(self._notices.items(), key=lambda x: x[1].posted_at)
            to_remove = sorted_notices[:len(self._notices) - self._max]
            for nid, _ in to_remove:
                del self._notices[nid]


# ═══════════════════════════════════════════════════════════════
# Task Routing
# ═══════════════════════════════════════════════════════════════

# Which providers are best for each task type
TASK_ROUTING: Dict[TaskType, List[Tuple[ModelProvider, str]]] = {
    TaskType.CODE: [
        (ModelProvider.OPENAI, "gpt-4o"),
        (ModelProvider.XAI, "grok-3"),
        (ModelProvider.CLAUDE, "claude-sonnet-4-20250514"),
        (ModelProvider.OLLAMA, "deepseek-coder"),
    ],
    TaskType.RESEARCH: [
        (ModelProvider.XAI, "grok-3"),       # Web-connected
        (ModelProvider.OPENAI, "gpt-4o"),
        (ModelProvider.GEMINI, "gemini-2.0-flash"),
        (ModelProvider.CLAUDE, "claude-sonnet-4-20250514"),
    ],
    TaskType.CREATIVE: [
        (ModelProvider.CLAUDE, "claude-sonnet-4-20250514"),
        (ModelProvider.GEMINI, "gemini-2.0-flash"),
        (ModelProvider.OPENAI, "gpt-4o"),
    ],
    TaskType.GOVERNANCE: [
        (ModelProvider.CLAUDE, "claude-sonnet-4-20250514"),
        (ModelProvider.OPENAI, "gpt-4o"),
    ],
    TaskType.ANALYSIS: [
        (ModelProvider.OPENAI, "gpt-4o"),
        (ModelProvider.CLAUDE, "claude-sonnet-4-20250514"),
        (ModelProvider.XAI, "grok-3"),
    ],
    TaskType.ARCHITECTURE: [
        (ModelProvider.CLAUDE, "claude-sonnet-4-20250514"),
        (ModelProvider.XAI, "grok-3"),
        (ModelProvider.OPENAI, "gpt-4o"),
    ],
    TaskType.TRANSLATION: [
        (ModelProvider.GEMINI, "gemini-2.0-flash"),
        (ModelProvider.OPENAI, "gpt-4o"),
    ],
    TaskType.SUMMARIZE: [
        (ModelProvider.GEMINI, "gemini-2.0-flash"),    # Cheapest
        (ModelProvider.OLLAMA, "llama3"),                # Free
        (ModelProvider.OPENAI, "gpt-4o-mini"),
    ],
    TaskType.GENERAL: [
        (ModelProvider.GEMINI, "gemini-2.0-flash"),
        (ModelProvider.OLLAMA, "llama3"),
        (ModelProvider.OPENAI, "gpt-4o"),
    ],
}

# Env var name for each provider's API key
PROVIDER_KEY_ENV: Dict[ModelProvider, str] = {
    ModelProvider.CLAUDE: "ANTHROPIC_API_KEY",
    ModelProvider.OPENAI: "OPENAI_API_KEY",
    ModelProvider.XAI: "XAI_API_KEY",
    ModelProvider.GEMINI: "GOOGLE_AI_API_KEY",
    ModelProvider.HUGGINGFACE: "HF_TOKEN",
    ModelProvider.OLLAMA: "",        # No key needed
    ModelProvider.LOCAL: "",
    ModelProvider.LLAMA: "",
    ModelProvider.MISTRAL: "",
}


@dataclass
class TaskTicket:
    """A task submitted to the switchboard."""
    ticket_id: str
    task_type: TaskType
    priority: TaskPriority
    prompt: str
    context: Optional[str] = None
    max_cost_tier: CostTier = CostTier.STANDARD
    assigned_provider: Optional[ModelProvider] = None
    assigned_model: Optional[str] = None
    result: Optional[str] = None
    cost_incurred: float = 0.0
    status: str = "pending"    # pending, routed, executing, done, error
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    attempts: int = 0
    max_attempts: int = 3


# ═══════════════════════════════════════════════════════════════
# Switchboard Operator
# ═══════════════════════════════════════════════════════════════

class Switchboard:
    """WW2-style operator that routes tasks to the right LLM line.

    Usage::

        board = NoticeBoard()
        switch = Switchboard(board)

        # Submit a task
        ticket = switch.submit("Write unit tests for auth module",
                               task_type=TaskType.CODE,
                               priority=TaskPriority.NORMAL)

        # Execute it (routes to best available provider)
        result = await switch.execute(ticket.ticket_id)

        # Check the notice board
        print(board.summary())
    """

    def __init__(self, notice_board: Optional[NoticeBoard] = None):
        self.board = notice_board or NoticeBoard()
        self._tickets: Dict[str, TaskTicket] = {}
        self._execution_log: List[Dict[str, Any]] = []

    def submit(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        priority: TaskPriority = TaskPriority.NORMAL,
        context: Optional[str] = None,
        max_cost: CostTier = CostTier.STANDARD,
    ) -> TaskTicket:
        """Submit a task to the switchboard. Returns a ticket."""
        ticket = TaskTicket(
            ticket_id=f"ticket-{uuid.uuid4().hex[:8]}",
            task_type=task_type,
            priority=priority,
            prompt=prompt,
            context=context,
            max_cost_tier=max_cost,
        )
        self._tickets[ticket.ticket_id] = ticket

        # Post to notice board
        self.board.post(
            author="switchboard",
            task_id=ticket.ticket_id,
            status="pending",
            message=f"New {task_type.value} task ({priority.value} priority)",
            tags=[task_type.value, priority.value],
        )

        return ticket

    def route(self, ticket_id: str) -> TaskTicket:
        """Route a ticket to the best available provider.

        Routing logic:
        1. Get preferred providers for this task type
        2. Filter by availability (API key present)
        3. Filter by cost tier
        4. Pick the cheapest available that meets quality requirements
        """
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            raise KeyError(f"Unknown ticket: {ticket_id}")

        preferred = TASK_ROUTING.get(ticket.task_type, TASK_ROUTING[TaskType.GENERAL])
        cost_limit = {
            CostTier.FREE: 0.0,
            CostTier.CHEAP: 0.001,
            CostTier.STANDARD: 0.01,
            CostTier.PREMIUM: 1.0,
        }[ticket.max_cost_tier]

        # For HIGH/URGENT priority, use quality-first ordering (as listed)
        # For LOW/NORMAL, sort by cost (cheapest first)
        candidates = []
        for provider, model_id in preferred:
            cost = PROVIDER_COSTS.get(provider, 0.01)
            if cost > cost_limit and ticket.priority not in (TaskPriority.HIGH, TaskPriority.URGENT):
                continue

            # Check if provider has API key available
            key_env = PROVIDER_KEY_ENV.get(provider, "")
            if key_env and not os.environ.get(key_env):
                continue

            candidates.append((provider, model_id, cost))

        if not candidates:
            # Fallback: try any provider with a key
            for provider in ModelProvider:
                key_env = PROVIDER_KEY_ENV.get(provider, "")
                if not key_env or os.environ.get(key_env):
                    candidates.append((provider, "default", PROVIDER_COSTS.get(provider, 0.0)))
                    break

        if not candidates:
            ticket.status = "error"
            self.board.post(
                author="switchboard",
                task_id=ticket_id,
                status="error",
                message="No available providers — check API keys in .env",
                tags=["error", "no-provider"],
            )
            return ticket

        # Sort: LOW/NORMAL = cheapest first, HIGH/URGENT = quality first (keep original order)
        if ticket.priority in (TaskPriority.LOW, TaskPriority.NORMAL):
            candidates.sort(key=lambda x: x[2])

        provider, model_id, cost = candidates[0]
        ticket.assigned_provider = provider
        ticket.assigned_model = model_id
        ticket.cost_incurred = cost
        ticket.status = "routed"

        self.board.post(
            author="switchboard",
            task_id=ticket_id,
            status="routed",
            message=f"Routed to {provider.value}/{model_id} (est ${cost:.4f}/1k tok)",
            cost=cost,
            tags=[provider.value, model_id],
        )

        return ticket

    async def execute(self, ticket_id: str) -> TaskTicket:
        """Execute a routed ticket — call the LLM and get the result."""
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            raise KeyError(f"Unknown ticket: {ticket_id}")

        if ticket.status == "pending":
            self.route(ticket_id)

        if ticket.status == "error":
            return ticket

        ticket.status = "executing"
        ticket.attempts += 1

        self.board.post(
            author=f"{ticket.assigned_provider.value}",
            task_id=ticket_id,
            status="working",
            message=f"Executing on {ticket.assigned_model}...",
        )

        config = ModelConfig(
            provider=ticket.assigned_provider,
            model_id=ticket.assigned_model,
            api_key_env=PROVIDER_KEY_ENV.get(ticket.assigned_provider, ""),
            temperature=0.7,
            max_tokens=2048,
        )

        handler = _PROVIDER_DISPATCH.get(ticket.assigned_provider)
        if not handler:
            ticket.status = "error"
            ticket.result = f"No handler for {ticket.assigned_provider}"
            return ticket

        try:
            result = await handler(config, ticket.prompt, ticket.context)
            ticket.result = result
            ticket.status = "done"
            ticket.completed_at = time.time()

            self.board.post(
                author=f"{ticket.assigned_provider.value}",
                task_id=ticket_id,
                status="done",
                message=f"Completed in {ticket.completed_at - ticket.created_at:.1f}s",
                result=result[:200] if result else None,
                cost=ticket.cost_incurred,
                tags=["completed"],
            )

        except Exception as exc:
            ticket.status = "error"
            ticket.result = f"Error: {exc}"

            self.board.post(
                author=f"{ticket.assigned_provider.value}",
                task_id=ticket_id,
                status="error",
                message=str(exc)[:200],
                tags=["error"],
            )

            # Retry with next provider if attempts remain
            if ticket.attempts < ticket.max_attempts:
                ticket.status = "pending"
                ticket.assigned_provider = None
                return await self.execute(ticket_id)

        self._log(ticket)
        return ticket

    async def batch_execute(self, prompts: List[Dict[str, Any]]) -> List[TaskTicket]:
        """Submit and execute multiple tasks concurrently.

        Each dict should have: prompt, task_type (optional), priority (optional).
        """
        tickets = []
        for p in prompts:
            ticket = self.submit(
                prompt=p["prompt"],
                task_type=TaskType(p.get("task_type", "general")),
                priority=TaskPriority(p.get("priority", "normal")),
                context=p.get("context"),
                max_cost=CostTier(p.get("max_cost", "standard")),
            )
            tickets.append(ticket)

        # Execute all concurrently
        results = await asyncio.gather(
            *(self.execute(t.ticket_id) for t in tickets),
            return_exceptions=True,
        )

        # Handle any exceptions
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                tickets[i].status = "error"
                tickets[i].result = str(r)

        return tickets

    def available_providers(self) -> List[Dict[str, Any]]:
        """List all providers with their availability and cost."""
        providers = []
        for provider in ModelProvider:
            key_env = PROVIDER_KEY_ENV.get(provider, "")
            has_key = not key_env or bool(os.environ.get(key_env))
            cost = PROVIDER_COSTS.get(provider, 0.0)
            providers.append({
                "provider": provider.value,
                "available": has_key,
                "key_env": key_env or "(none needed)",
                "cost_per_1k_tokens": cost,
                "tier": (
                    CostTier.FREE.value if cost == 0
                    else CostTier.CHEAP.value if cost < 0.001
                    else CostTier.STANDARD.value if cost < 0.01
                    else CostTier.PREMIUM.value
                ),
            })
        return providers

    def status(self) -> Dict[str, Any]:
        """Full switchboard status."""
        tickets = list(self._tickets.values())
        return {
            "total_tickets": len(tickets),
            "by_status": {
                s: len([t for t in tickets if t.status == s])
                for s in ["pending", "routed", "executing", "done", "error"]
            },
            "providers": self.available_providers(),
            "notice_board": self.board.summary(),
            "total_cost": sum(t.cost_incurred for t in tickets if t.status == "done"),
        }

    def _log(self, ticket: TaskTicket) -> None:
        self._execution_log.append({
            "ticket_id": ticket.ticket_id,
            "task_type": ticket.task_type.value,
            "provider": ticket.assigned_provider.value if ticket.assigned_provider else None,
            "model": ticket.assigned_model,
            "status": ticket.status,
            "cost": ticket.cost_incurred,
            "attempts": ticket.attempts,
            "duration": ticket.completed_at - ticket.created_at if ticket.completed_at else 0,
            "timestamp": time.time(),
        })
        if len(self._execution_log) > 500:
            self._execution_log = self._execution_log[-500:]


# ═══════════════════════════════════════════════════════════════
# Quick helpers
# ═══════════════════════════════════════════════════════════════

def classify_task(prompt: str) -> TaskType:
    """Simple keyword-based task classification."""
    p = prompt.lower()

    code_words = ["code", "function", "class", "test", "debug", "implement", "fix", "bug",
                  "python", "typescript", "javascript", "api", "endpoint", "refactor"]
    research_words = ["research", "find", "search", "compare", "analyze", "report",
                      "study", "paper", "literature", "survey", "investigate"]
    creative_words = ["write", "story", "blog", "post", "content", "creative",
                      "narrative", "draft", "copy", "marketing"]
    governance_words = ["governance", "safety", "security", "compliance", "audit",
                        "risk", "policy", "review", "approve"]
    architecture_words = ["architecture", "design", "system", "infrastructure",
                          "deploy", "scale", "database", "schema"]
    summarize_words = ["summarize", "summary", "tldr", "key points", "bullet"]

    for words, task_type in [
        (code_words, TaskType.CODE),
        (research_words, TaskType.RESEARCH),
        (creative_words, TaskType.CREATIVE),
        (governance_words, TaskType.GOVERNANCE),
        (architecture_words, TaskType.ARCHITECTURE),
        (summarize_words, TaskType.SUMMARIZE),
    ]:
        if any(w in p for w in words):
            return task_type

    return TaskType.GENERAL


async def quick_ask(
    prompt: str,
    priority: str = "normal",
    board: Optional[NoticeBoard] = None,
) -> str:
    """One-liner: submit, route, execute, return result."""
    switch = Switchboard(board or NoticeBoard())
    task_type = classify_task(prompt)
    ticket = switch.submit(prompt, task_type=task_type,
                           priority=TaskPriority(priority))
    result = await switch.execute(ticket.ticket_id)
    return result.result or "[no result]"
