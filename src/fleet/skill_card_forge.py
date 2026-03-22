"""Minimal skill-card primitives used by HallPass and related tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from typing import Any, Iterable


class CardType(str, Enum):
    SKILL = "Skill"
    AGENT = "Agent"
    WORKFLOW = "Workflow"
    DEFENSE = "Defense"
    RESEARCH = "Research"
    TOOL = "Tool"


class SynergyType(str, Enum):
    OFFENSIVE = "Offensive"
    SUPPORT = "Support"
    DEFENSIVE = "Defensive"
    ORCHESTRATOR = "Orchestrator"
    ARCANE = "Arcane"
    UTILITY = "Utility"


@dataclass(frozen=True)
class SkillCard:
    name: str
    card_id: str
    card_type: str
    synergy: str
    power: int = 100
    complexity: int = 1
    scope: int = 1
    description: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "card_id": self.card_id,
            "card_type": self.card_type,
            "synergy": self.synergy,
            "power": self.power,
            "complexity": self.complexity,
            "scope": self.scope,
            "description": self.description,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SkillCard":
        return cls(
            name=str(payload.get("name", payload.get("card_name", "unnamed-card"))),
            card_id=str(payload.get("card_id", payload.get("id", "card-0"))),
            card_type=str(payload.get("card_type", CardType.SKILL.value)),
            synergy=str(payload.get("synergy", SynergyType.UTILITY.value)),
            power=int(payload.get("power", 100)),
            complexity=int(payload.get("complexity", 1)),
            scope=int(payload.get("scope", 1)),
            description=str(payload.get("description", "")),
            tags=[str(tag) for tag in payload.get("tags", [])],
        )

    @property
    def search_blob(self) -> str:
        return " ".join(
            part
            for part in [
                self.name,
                self.card_type,
                self.synergy,
                self.description,
                " ".join(self.tags),
            ]
            if part
        ).lower()


@dataclass
class Deck:
    cards: list[SkillCard]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "Deck":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(data, dict):
            raw_cards = data.get("cards", [])
            metadata = {k: v for k, v in data.items() if k != "cards"}
        elif isinstance(data, list):
            raw_cards = data
            metadata = {}
        else:
            raise ValueError("Deck file must be a JSON object or list")
        return cls(cards=[SkillCard.from_dict(item) for item in raw_cards], metadata=metadata)

    def save(self, path: str | Path) -> None:
        payload = {"cards": [card.to_dict() for card in self.cards], **self.metadata}
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


class DeckBuilder:
    def __init__(self) -> None:
        self._cards: list[SkillCard] = []
        self._metadata: dict[str, Any] = {}

    def add_card(self, card: SkillCard) -> "DeckBuilder":
        self._cards.append(card)
        return self

    def extend(self, cards: Iterable[SkillCard]) -> "DeckBuilder":
        self._cards.extend(cards)
        return self

    def metadata(self, **kwargs: Any) -> "DeckBuilder":
        self._metadata.update(kwargs)
        return self

    def build(self) -> Deck:
        return Deck(cards=list(self._cards), metadata=dict(self._metadata))
