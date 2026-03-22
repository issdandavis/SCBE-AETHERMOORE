"""Lightweight deck scoring and permission helpers for HallPass lanes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .skill_card_forge import CardType, SkillCard, SynergyType


@dataclass(frozen=True)
class PermissionProfile:
    granted: set[str]
    token_cost: int
    latency_ms: int
    risk_level: float


def _keyword_matches(task: str, blob: str) -> int:
    words = [word for word in task.lower().replace("-", " ").split() if len(word) > 2]
    return sum(1 for word in set(words) if word in blob)


def classify_permissions(card: SkillCard) -> PermissionProfile:
    granted: set[str] = set()
    blob = card.search_blob

    if card.card_type == CardType.AGENT.value:
        granted.update({"agent", "dispatch"})
    if card.card_type == CardType.WORKFLOW.value:
        granted.update({"workflow", "execute"})
    if card.card_type == CardType.DEFENSE.value:
        granted.update({"governance", "audit"})
    if card.card_type == CardType.RESEARCH.value:
        granted.update({"research", "read"})
    if "browser" in blob or "scrape" in blob or "navigate" in blob:
        granted.update({"browser", "web"})
    if "deploy" in blob or "publish" in blob:
        granted.update({"deploy", "publish"})
    if "api" in blob or "connect" in blob or "bridge" in blob:
        granted.update({"integration"})
    if "data" in blob or "transform" in blob or "analyze" in blob:
        granted.update({"data"})
    if "security" in blob or "gate" in blob or "entropy" in blob:
        granted.update({"security"})
    granted.update(card.tags)

    variable_cost = max(0, int(card.power * 0.45) + card.complexity * 90 + card.scope * 55 + len(card.tags) * 20)
    token_cost = 200 + variable_cost
    latency_ms = 120 + (card.complexity * 40) + (card.scope * 25)
    risk_level = min(
        1.0,
        0.1
        + (card.power / 1000.0)
        + (0.15 if card.synergy == SynergyType.ARCANE.value else 0.0)
        + (0.1 if card.card_type == CardType.DEFENSE.value else 0.0),
    )
    return PermissionProfile(granted=granted, token_cost=token_cost, latency_ms=latency_ms, risk_level=risk_level)


class SynergyEngine:
    def score(self, task: str, card: SkillCard) -> float:
        blob = card.search_blob
        keyword_score = _keyword_matches(task, blob) * 25.0
        power_score = min(card.power, 700) / 35.0
        complexity_penalty = max(0, card.complexity - 5) * 4.0
        scope_bonus = card.scope * 2.0
        synergy_bonus = {
            SynergyType.ORCHESTRATOR.value: 8.0,
            SynergyType.DEFENSIVE.value: 6.0,
            SynergyType.ARCANE.value: 4.0,
            SynergyType.SUPPORT.value: 5.0,
        }.get(card.synergy, 3.0)
        return keyword_score + power_score + scope_bonus + synergy_bonus - complexity_penalty


class DeckOptimizer:
    def __init__(self, synergy_engine: SynergyEngine | None = None) -> None:
        self.synergy_engine = synergy_engine or SynergyEngine()

    def optimize(self, task: str, pool: list[SkillCard], max_cards: int = 10) -> list[SkillCard]:
        ranked = sorted(
            pool,
            key=lambda card: (
                self.synergy_engine.score(task, card),
                card.power,
                -card.complexity,
                card.name.lower(),
            ),
            reverse=True,
        )
        return ranked[: max(0, max_cards)]


class WorkflowCompiler:
    def _classify_role(self, card: SkillCard) -> str:
        blob = card.search_blob
        if card.card_type == CardType.AGENT.value:
            return "orchestrate"
        if card.card_type == CardType.WORKFLOW.value:
            return "output" if "publish" in blob else "orchestrate"
        if card.card_type == CardType.DEFENSE.value:
            return "validate"
        if card.card_type == CardType.RESEARCH.value:
            return "gather"
        if any(keyword in blob for keyword in ("search", "research", "read", "scrape")):
            return "gather"
        if any(keyword in blob for keyword in ("publish", "deploy", "write", "output")):
            return "output"
        if any(keyword in blob for keyword in ("orchestrate", "coordinate", "fleet", "dispatch")):
            return "orchestrate"
        return "process"


__all__ = [
    "PermissionProfile",
    "SynergyEngine",
    "DeckOptimizer",
    "WorkflowCompiler",
    "classify_permissions",
]
