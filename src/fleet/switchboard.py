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
import math
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .model_matrix import (
    ModelMatrix, ModelProvider, ModelConfig, ModelNode,
    _PROVIDER_DISPATCH, _mock,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VALUE_PROFILE_PATH = REPO_ROOT / "config" / "governance" / "value_execution_profiles.json"
DEFAULT_DUTY_PROFILE_PATH = REPO_ROOT / "config" / "governance" / "model_duty_profiles.json"

FALLBACK_VALUE_PROFILE: Dict[str, Any] = {
    "intent_value_weights": {
        "lead_generation": 0.92,
        "publish_content": 0.84,
        "release_ops": 0.78,
        "research_intel": 0.70,
        "maintenance": 0.55,
        "generic": 0.50,
    },
}

FALLBACK_DUTY_PROFILE: Dict[str, Any] = {
    "version": "1.0.0",
    "profiles": [],
}

TONGUE_AXES: Tuple[str, ...] = ("ko", "av", "ru", "ca", "um", "dr")

# Task seeds in Sacred Tongue space. Values stay in [0, 1] and are normalized.
TASK_SPECTRUM_SEEDS: Dict[str, Dict[str, float]] = {
    "code": {"ko": 0.28, "av": 0.08, "ru": 0.20, "ca": 0.95, "um": 0.26, "dr": 0.88},
    "research": {"ko": 0.62, "av": 0.22, "ru": 0.72, "ca": 0.34, "um": 0.42, "dr": 0.50},
    "creative": {"ko": 0.36, "av": 0.95, "ru": 0.14, "ca": 0.24, "um": 0.20, "dr": 0.38},
    "governance": {"ko": 0.42, "av": 0.16, "ru": 0.86, "ca": 0.26, "um": 0.95, "dr": 0.64},
    "analysis": {"ko": 0.64, "av": 0.24, "ru": 0.50, "ca": 0.56, "um": 0.46, "dr": 0.62},
    "architecture": {"ko": 0.54, "av": 0.18, "ru": 0.40, "ca": 0.70, "um": 0.42, "dr": 0.94},
    "translation": {"ko": 0.30, "av": 0.58, "ru": 0.36, "ca": 0.22, "um": 0.24, "dr": 0.38},
    "summarize": {"ko": 0.48, "av": 0.34, "ru": 0.42, "ca": 0.24, "um": 0.26, "dr": 0.36},
    "general": {"ko": 0.40, "av": 0.32, "ru": 0.34, "ca": 0.40, "um": 0.34, "dr": 0.42},
}

PROMPT_AXIS_HINTS: Dict[str, Tuple[str, float]] = {
    "security": ("ru", 0.24),
    "risk": ("ru", 0.20),
    "policy": ("um", 0.24),
    "audit": ("um", 0.22),
    "governance": ("um", 0.25),
    "code": ("ca", 0.20),
    "refactor": ("ca", 0.20),
    "build": ("ca", 0.16),
    "architecture": ("dr", 0.24),
    "schema": ("dr", 0.18),
    "design": ("dr", 0.20),
    "creative": ("av", 0.22),
    "story": ("av", 0.20),
    "marketing": ("av", 0.18),
    "research": ("ko", 0.20),
    "summarize": ("ko", 0.16),
    "classify": ("ko", 0.14),
}


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

# Value-route priors for M4 auto-routing (quality/speed in [0,1]).
PROVIDER_ROUTE_PRIORS: Dict[ModelProvider, Dict[str, float]] = {
    ModelProvider.CLAUDE: {"quality": 0.95, "speed": 0.68},
    ModelProvider.OPENAI: {"quality": 0.90, "speed": 0.82},
    ModelProvider.XAI: {"quality": 0.88, "speed": 0.79},
    ModelProvider.GEMINI: {"quality": 0.84, "speed": 0.93},
    ModelProvider.HUGGINGFACE: {"quality": 0.62, "speed": 0.64},
    ModelProvider.OLLAMA: {"quality": 0.70, "speed": 0.73},
    ModelProvider.LOCAL: {"quality": 0.66, "speed": 0.71},
    ModelProvider.LLAMA: {"quality": 0.68, "speed": 0.72},
    ModelProvider.MISTRAL: {"quality": 0.76, "speed": 0.78},
}


def _load_value_profile(path: Path = DEFAULT_VALUE_PROFILE_PATH) -> Dict[str, Any]:
    if not path.exists():
        return FALLBACK_VALUE_PROFILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return FALLBACK_VALUE_PROFILE
        return data
    except Exception:
        return FALLBACK_VALUE_PROFILE


def _load_duty_profile(path: Path = DEFAULT_DUTY_PROFILE_PATH) -> Dict[str, Any]:
    if not path.exists():
        return FALLBACK_DUTY_PROFILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return FALLBACK_DUTY_PROFILE
        if not isinstance(data.get("profiles", []), list):
            data["profiles"] = []
        return data
    except Exception:
        return FALLBACK_DUTY_PROFILE


def _infer_value_intent(task_type: TaskType) -> str:
    mapping = {
        TaskType.RESEARCH: "research_intel",
        TaskType.CODE: "release_ops",
        TaskType.ARCHITECTURE: "release_ops",
        TaskType.CREATIVE: "publish_content",
        TaskType.GOVERNANCE: "maintenance",
        TaskType.ANALYSIS: "maintenance",
        TaskType.SUMMARIZE: "maintenance",
        TaskType.TRANSLATION: "maintenance",
        TaskType.GENERAL: "generic",
    }
    return mapping.get(task_type, "generic")


def _route_score_for_candidate(
    provider: ModelProvider,
    task_type: TaskType,
    priority: TaskPriority,
    profile: Dict[str, Any],
) -> float:
    intent_key = _infer_value_intent(task_type)
    objective_value = float(profile.get("intent_value_weights", {}).get(intent_key, 0.5))
    prior = PROVIDER_ROUTE_PRIORS.get(provider, {"quality": 0.7, "speed": 0.7})
    quality = float(prior.get("quality", 0.7))
    speed = float(prior.get("speed", 0.7))
    utility = objective_value * 0.68 + quality * 0.20 + speed * 0.12
    if priority in (TaskPriority.HIGH, TaskPriority.URGENT):
        utility *= 1.08
    # Convert USD/1k tokens to cents/1k tokens.
    cost_cents = max(0.05, float(PROVIDER_COSTS.get(provider, 0.01)) * 100.0)
    return (utility * 100.0) / cost_cents


def _prompt_tags(prompt: str) -> List[str]:
    text = (prompt or "").lower()
    tag_keywords = {
        "flagging": ["flag", "risk", "gate", "guard", "moderate"],
        "summarize": ["summarize", "summary", "digest", "tldr"],
        "classify": ["classify", "label", "categorize", "tag"],
        "triage": ["triage", "queue", "backlog", "cleanup"],
        "research": ["research", "investigate", "scan", "find"],
        "code": ["code", "fix", "test", "refactor", "implement"],
        "creative": ["write", "story", "narrative", "content", "marketing"],
    }
    tags: List[str] = []
    for tag, words in tag_keywords.items():
        if any(word in text for word in words):
            tags.append(tag)
    return tags


def _normalize_axis_vector(vector: Dict[str, float]) -> Dict[str, float]:
    ordered = [max(0.0, float(vector.get(axis, 0.0))) for axis in TONGUE_AXES]
    norm = math.sqrt(sum(v * v for v in ordered))
    if norm <= 1e-9:
        return {axis: 0.0 for axis in TONGUE_AXES}
    return {axis: ordered[i] / norm for i, axis in enumerate(TONGUE_AXES)}


def _task_spectrum_vector(task_type: TaskType, prompt: str) -> Dict[str, float]:
    seed = dict(TASK_SPECTRUM_SEEDS.get(task_type.value, TASK_SPECTRUM_SEEDS[TaskType.GENERAL.value]))
    text = (prompt or "").lower()
    for word, (axis, delta) in PROMPT_AXIS_HINTS.items():
        if word in text:
            seed[axis] = max(0.0, min(1.0, float(seed.get(axis, 0.0)) + delta))
    return _normalize_axis_vector(seed)


def _profile_spectrum_vector(profile: Dict[str, Any]) -> Dict[str, float]:
    raw = profile.get("tongue_vector", {})
    if isinstance(raw, dict):
        projected: Dict[str, float] = {}
        for axis in TONGUE_AXES:
            value = raw.get(axis, raw.get(axis.upper(), 0.0))
            try:
                projected[axis] = float(value)
            except Exception:
                projected[axis] = 0.0
        return _normalize_axis_vector(projected)
    return {axis: 0.0 for axis in TONGUE_AXES}


def _cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
    return sum(float(a.get(axis, 0.0)) * float(b.get(axis, 0.0)) for axis in TONGUE_AXES)


def _spectrum_fit_for_candidate(
    provider: ModelProvider,
    model_id: str,
    task_type: TaskType,
    prompt: str,
    duty_profile: Dict[str, Any],
) -> Tuple[float, float, str]:
    """Return (alignment, bonus_pct, profile_id) for 6-axis spectrum fit."""
    profiles = duty_profile.get("profiles", [])
    if not isinstance(profiles, list):
        return 0.0, 0.0, ""

    task_vector = _task_spectrum_vector(task_type, prompt)
    best_alignment = -1.0
    best_bonus = 0.0
    best_profile_id = ""

    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        if str(profile.get("provider", "")).strip().lower() != provider.value:
            continue
        profile_model = str(profile.get("model_id", "")).strip()
        if profile_model and profile_model != "*" and profile_model != model_id:
            continue

        profile_vec = _profile_spectrum_vector(profile)
        alignment = _cosine_similarity(task_vector, profile_vec)
        if alignment > best_alignment:
            best_alignment = alignment
            spectrum_bonus = float(profile.get("spectrum_bonus_pct", 0.12))
            # Non-linear boost: square positive alignment to favor high-coherence routes.
            best_bonus = spectrum_bonus * max(0.0, alignment) ** 2
            best_profile_id = str(profile.get("id", "")).strip()

    if best_alignment < 0:
        return 0.0, 0.0, ""
    return best_alignment, best_bonus, best_profile_id


def _duty_fit_for_candidate(
    provider: ModelProvider,
    model_id: str,
    task_type: TaskType,
    prompt: str,
    duty_profile: Dict[str, Any],
) -> Tuple[str, float, str]:
    """Return (role, bonus_pct, profile_id) for primary/secondary duty fit."""
    profiles = duty_profile.get("profiles", [])
    if not isinstance(profiles, list):
        return "none", 0.0, ""

    prompt_tags = set(_prompt_tags(prompt))
    task_name = task_type.value
    best_role = "none"
    best_bonus = 0.0
    best_profile_id = ""

    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        if str(profile.get("provider", "")).strip().lower() != provider.value:
            continue
        profile_model = str(profile.get("model_id", "")).strip()
        if profile_model and profile_model != "*" and profile_model != model_id:
            continue

        primary_tasks = {str(x).strip().lower() for x in profile.get("primary_task_types", []) if str(x).strip()}
        secondary_tasks = {str(x).strip().lower() for x in profile.get("secondary_task_types", []) if str(x).strip()}
        primary_tags = {str(x).strip().lower() for x in profile.get("primary_tags", []) if str(x).strip()}
        secondary_tags = {str(x).strip().lower() for x in profile.get("secondary_tags", []) if str(x).strip()}

        role = "none"
        bonus = 0.0
        if (task_name in primary_tasks) or bool(prompt_tags.intersection(primary_tags)):
            role = "primary"
            bonus = float(profile.get("primary_bonus_pct", 0.24))
        elif (task_name in secondary_tasks) or bool(prompt_tags.intersection(secondary_tags)):
            role = "secondary"
            bonus = float(profile.get("secondary_bonus_pct", 0.09))

        if role == "primary" and (best_role != "primary" or bonus > best_bonus):
            best_role = role
            best_bonus = bonus
            best_profile_id = str(profile.get("id", ""))
        elif role == "secondary" and best_role == "none" and bonus > best_bonus:
            best_role = role
            best_bonus = bonus
            best_profile_id = str(profile.get("id", ""))

    return best_role, best_bonus, best_profile_id


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
        (ModelProvider.GEMINI, "gemini-2.5-flash"),
        (ModelProvider.CLAUDE, "claude-sonnet-4-20250514"),
    ],
    TaskType.CREATIVE: [
        (ModelProvider.CLAUDE, "claude-sonnet-4-20250514"),
        (ModelProvider.GEMINI, "gemini-2.5-flash"),
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
        (ModelProvider.GEMINI, "gemini-2.5-flash"),
        (ModelProvider.OPENAI, "gpt-4o"),
    ],
    TaskType.SUMMARIZE: [
        (ModelProvider.GEMINI, "gemini-2.5-flash"),    # Cheapest
        (ModelProvider.OLLAMA, "llama3"),                # Free
        (ModelProvider.OPENAI, "gpt-4o-mini"),
    ],
    TaskType.GENERAL: [
        (ModelProvider.GEMINI, "gemini-2.5-flash"),
        (ModelProvider.OLLAMA, "llama3"),
        (ModelProvider.OPENAI, "gpt-4o"),
    ],
}

# Env var name for each provider's API key
PROVIDER_KEY_ENV: Dict[ModelProvider, str] = {
    ModelProvider.CLAUDE: "ANTHROPIC_API_KEY",
    ModelProvider.OPENAI: "OPENAI_API_KEY",
    ModelProvider.XAI: "XAI_API_KEY",
    ModelProvider.GEMINI: "GOOGLE_API_KEY",
    ModelProvider.HUGGINGFACE: "HF_TOKEN",
    ModelProvider.OLLAMA: "",        # No key needed
    ModelProvider.LOCAL: "",
    ModelProvider.LLAMA: "",
    ModelProvider.MISTRAL: "",
}

PROVIDER_DEFAULT_MODEL: Dict[ModelProvider, str] = {
    ModelProvider.CLAUDE: "claude-sonnet-4-20250514",
    ModelProvider.OPENAI: "gpt-4o",
    ModelProvider.XAI: "grok-3",
    ModelProvider.GEMINI: "gemini-2.5-flash",
    ModelProvider.HUGGINGFACE: "mistralai/Mistral-7B-Instruct-v0.2",
    ModelProvider.OLLAMA: "llama3",
    ModelProvider.LOCAL: "local-default",
    ModelProvider.LLAMA: "llama3",
    ModelProvider.MISTRAL: "mistral-small",
}


def _provider_has_key(provider: ModelProvider) -> bool:
    key_env = PROVIDER_KEY_ENV.get(provider, "")
    if provider == ModelProvider.GEMINI:
        return bool(
            os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("GOOGLE_AI_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
        )
    if not key_env:
        return True
    return bool(os.environ.get(key_env))


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
    assigned_duty_role: str = "none"  # none | primary | secondary
    assigned_duty_profile: str = ""
    spectrum_alignment: float = 0.0
    result: Optional[str] = None
    cost_incurred: float = 0.0
    route_score: float = 0.0
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
        self.value_profile: Dict[str, Any] = _load_value_profile()
        self.duty_profile: Dict[str, Any] = _load_duty_profile()

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
        4. Score candidates with value/cost routing formula
        5. Pick highest-scoring candidate
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

        candidates: List[Dict[str, Any]] = []
        for provider, model_id in preferred:
            cost = PROVIDER_COSTS.get(provider, 0.01)
            if cost > cost_limit and ticket.priority not in (TaskPriority.HIGH, TaskPriority.URGENT):
                continue

            if not _provider_has_key(provider):
                continue

            base_score = _route_score_for_candidate(
                provider=provider,
                task_type=ticket.task_type,
                priority=ticket.priority,
                profile=self.value_profile,
            )
            duty_role, duty_bonus_pct, duty_profile_id = _duty_fit_for_candidate(
                provider=provider,
                model_id=model_id,
                task_type=ticket.task_type,
                prompt=ticket.prompt,
                duty_profile=self.duty_profile,
            )
            spectrum_alignment, spectrum_bonus_pct, spectrum_profile_id = _spectrum_fit_for_candidate(
                provider=provider,
                model_id=model_id,
                task_type=ticket.task_type,
                prompt=ticket.prompt,
                duty_profile=self.duty_profile,
            )
            route_score = base_score * (1.0 + duty_bonus_pct) * (1.0 + spectrum_bonus_pct)
            candidates.append(
                {
                    "provider": provider,
                    "model_id": model_id,
                    "cost": cost,
                    "base_score": base_score,
                    "score": route_score,
                    "duty_role": duty_role,
                    "duty_bonus_pct": duty_bonus_pct,
                    "duty_profile_id": duty_profile_id,
                    "spectrum_alignment": spectrum_alignment,
                    "spectrum_bonus_pct": spectrum_bonus_pct,
                    "spectrum_profile_id": spectrum_profile_id,
                }
            )

        if not candidates:
            # Fallback: try any provider with a key
            for provider in ModelProvider:
                if _provider_has_key(provider):
                    model_id = PROVIDER_DEFAULT_MODEL.get(provider, "default")
                    base_score = _route_score_for_candidate(
                        provider=provider,
                        task_type=ticket.task_type,
                        priority=ticket.priority,
                        profile=self.value_profile,
                    )
                    duty_role, duty_bonus_pct, duty_profile_id = _duty_fit_for_candidate(
                        provider=provider,
                        model_id=model_id,
                        task_type=ticket.task_type,
                        prompt=ticket.prompt,
                        duty_profile=self.duty_profile,
                    )
                    spectrum_alignment, spectrum_bonus_pct, spectrum_profile_id = _spectrum_fit_for_candidate(
                        provider=provider,
                        model_id=model_id,
                        task_type=ticket.task_type,
                        prompt=ticket.prompt,
                        duty_profile=self.duty_profile,
                    )
                    candidates.append(
                        {
                            "provider": provider,
                            "model_id": model_id,
                            "cost": PROVIDER_COSTS.get(provider, 0.0),
                            "base_score": base_score,
                            "score": base_score * (1.0 + duty_bonus_pct) * (1.0 + spectrum_bonus_pct),
                            "duty_role": duty_role,
                            "duty_bonus_pct": duty_bonus_pct,
                            "duty_profile_id": duty_profile_id,
                            "spectrum_alignment": spectrum_alignment,
                            "spectrum_bonus_pct": spectrum_bonus_pct,
                            "spectrum_profile_id": spectrum_profile_id,
                        }
                    )
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

        candidates.sort(key=lambda x: (x["score"], -x["cost"]), reverse=True)
        best = candidates[0]
        provider = best["provider"]
        model_id = best["model_id"]
        cost = float(best["cost"])
        score = float(best["score"])
        duty_role = str(best.get("duty_role", "none") or "none")
        duty_profile_id = str(best.get("duty_profile_id", "") or "")
        spectrum_alignment = float(best.get("spectrum_alignment", 0.0))
        ticket.assigned_provider = provider
        ticket.assigned_model = model_id
        ticket.assigned_duty_role = duty_role
        ticket.assigned_duty_profile = duty_profile_id
        ticket.spectrum_alignment = spectrum_alignment
        ticket.cost_incurred = cost
        ticket.route_score = score
        ticket.status = "routed"

        duty_suffix = ""
        if duty_role != "none":
            duty_suffix = f", duty={duty_role}"
            if duty_profile_id:
                duty_suffix += f":{duty_profile_id}"

        self.board.post(
            author="switchboard",
            task_id=ticket_id,
            status="routed",
            message=f"Routed to {provider.value}/{model_id} (est ${cost:.4f}/1k tok, score={score:.2f}, spec={spectrum_alignment:.2f}{duty_suffix})",
            cost=cost,
            tags=[provider.value, model_id, duty_role],
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
            message=f"Executing on {ticket.assigned_model} (duty={ticket.assigned_duty_role})...",
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
            has_key = _provider_has_key(provider)
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

    def suggest_idle_secondary_jobs(self, limit: int = 8) -> List[Dict[str, Any]]:
        """Suggest low-priority secondary duties for currently available specialists."""
        jobs: List[Dict[str, Any]] = []
        profiles = self.duty_profile.get("profiles", [])
        if not isinstance(profiles, list):
            return jobs

        for profile in profiles:
            if not isinstance(profile, dict):
                continue
            provider_name = str(profile.get("provider", "")).strip().lower()
            model_id = str(profile.get("model_id", "")).strip() or "*"
            profile_id = str(profile.get("id", "")).strip() or "unknown"

            try:
                provider = ModelProvider(provider_name)
            except Exception:
                continue

            if not _provider_has_key(provider):
                continue

            for job in profile.get("idle_jobs", []):
                if not isinstance(job, dict):
                    continue
                jobs.append(
                    {
                        "profile_id": profile_id,
                        "provider": provider.value,
                        "model_id": model_id,
                        "job_id": str(job.get("id", "")).strip() or "idle",
                        "prompt": str(job.get("prompt", "")).strip(),
                        "task_type": str(job.get("task_type", "general")).strip() or "general",
                        "max_cost": str(job.get("max_cost", "cheap")).strip() or "cheap",
                    }
                )
                if len(jobs) >= max(1, limit):
                    return jobs
        return jobs

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
            "duty_profiles_loaded": len(self.duty_profile.get("profiles", []))
            if isinstance(self.duty_profile.get("profiles", []), list)
            else 0,
            "idle_secondary_jobs": self.suggest_idle_secondary_jobs(limit=5),
        }

    def _log(self, ticket: TaskTicket) -> None:
        self._execution_log.append({
            "ticket_id": ticket.ticket_id,
            "task_type": ticket.task_type.value,
            "provider": ticket.assigned_provider.value if ticket.assigned_provider else None,
            "model": ticket.assigned_model,
            "duty_role": ticket.assigned_duty_role,
            "duty_profile": ticket.assigned_duty_profile,
            "route_score": ticket.route_score,
            "spectrum_alignment": ticket.spectrum_alignment,
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
