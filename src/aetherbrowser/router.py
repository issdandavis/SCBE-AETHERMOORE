"""
OctoArmor Model Router
=======================

Every model can play any role. Routing is a preference, not a lock.

1. Task arrives -> score complexity (LOW / MEDIUM / HIGH)
2. Pick cheapest model that can handle it
3. Assign tongue role based on task type
4. If rate-limited, cascade to next model
5. Sacred Tongue -> model mapping is configurable
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum


class ModelProvider(str, Enum):
    OPUS = "opus"
    SONNET = "sonnet"
    HAIKU = "haiku"
    FLASH = "flash"
    GROK = "grok"
    LOCAL = "local"


class TaskComplexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


MODEL_COST_TIER: dict[ModelProvider, int] = {
    ModelProvider.LOCAL: 0,
    ModelProvider.HAIKU: 1,
    ModelProvider.FLASH: 1,
    ModelProvider.GROK: 2,
    ModelProvider.SONNET: 3,
    ModelProvider.OPUS: 4,
}

COMPLEXITY_MIN_TIER: dict[TaskComplexity, int] = {
    TaskComplexity.LOW: 0,
    TaskComplexity.MEDIUM: 2,
    TaskComplexity.HIGH: 3,
}

DEFAULT_PREFERENCES: dict[str, ModelProvider] = {
    "KO": ModelProvider.OPUS,
    "AV": ModelProvider.FLASH,
    "RU": ModelProvider.LOCAL,
    "CA": ModelProvider.SONNET,
    "UM": ModelProvider.GROK,
    "DR": ModelProvider.HAIKU,
}

_HIGH_KEYWORDS = {"compare", "analyze", "report", "competitors", "structured", "citations", "comprehensive", "evaluate"}
_LOW_KEYWORDS = {"what", "when", "who", "define", "list", "ping"}


@dataclass
class SelectedModel:
    provider: ModelProvider
    role: str
    complexity: TaskComplexity


class OctoArmorRouter:
    def __init__(self, preferences: dict[str, ModelProvider] | None = None):
        self._prefs = {**DEFAULT_PREFERENCES, **(preferences or {})}
        self._rate_limits: dict[ModelProvider, float] = {}

    def get_preferences(self) -> dict[str, ModelProvider]:
        return dict(self._prefs)

    def score_complexity(self, text: str) -> TaskComplexity:
        words = set(text.lower().split())
        high_hits = len(words & _HIGH_KEYWORDS)
        low_hits = len(words & _LOW_KEYWORDS)
        word_count = len(text.split())
        if high_hits >= 2 or word_count > 50:
            return TaskComplexity.HIGH
        if low_hits >= 1 and word_count < 15:
            return TaskComplexity.LOW
        return TaskComplexity.MEDIUM

    def mark_rate_limited(self, provider: ModelProvider, window_sec: float = 60.0) -> None:
        self._rate_limits[provider] = time.monotonic() + window_sec

    def _is_available(self, provider: ModelProvider) -> bool:
        expiry = self._rate_limits.get(provider)
        if expiry is None:
            return True
        if time.monotonic() >= expiry:
            del self._rate_limits[provider]
            return True
        return False

    def select_model(self, complexity: TaskComplexity, role: str) -> SelectedModel:
        min_tier = COMPLEXITY_MIN_TIER[complexity]
        preferred = self._prefs.get(role, ModelProvider.SONNET)
        if self._is_available(preferred) and MODEL_COST_TIER[preferred] >= min_tier:
            return SelectedModel(provider=preferred, role=role, complexity=complexity)
        candidates = sorted(
            [p for p in ModelProvider if self._is_available(p) and MODEL_COST_TIER[p] >= min_tier],
            key=lambda p: MODEL_COST_TIER[p],
        )
        if not candidates:
            raise RuntimeError("All models rate-limited")
        return SelectedModel(provider=candidates[0], role=role, complexity=complexity)
