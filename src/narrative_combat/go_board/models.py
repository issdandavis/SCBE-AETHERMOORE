"""Narrative-combat domain types layered on the legality kernel.

The kernel knows only players, points, and stones. These dataclasses give those board atoms
narrative meaning: a player is a Party (with temperament, so prose can vary by personality),
a resource node is a QiNode, and the whole scene is a GoEncounter.
"""

from __future__ import annotations

from dataclasses import dataclass, field

Point = tuple[int, int]


@dataclass(frozen=True)
class Party:
    """A combatant faction — the narrative meaning of a kernel player (color = player index)."""

    name: str
    color: int
    temperament: list[str] = field(default_factory=list)
    goal: str = "prevail"


@dataclass(frozen=True)
class QiNode:
    """A board point that grants qi to the party that first plants a stone on or beside it."""

    point: Point
    value: int = 3


@dataclass(frozen=True)
class GoEncounter:
    """Everything the GoDirector needs to drive one board-fight."""

    encounter_id: str
    seed: int
    style: str
    board_size: int
    parties: list[Party]
    qi_nodes: list[QiNode] = field(default_factory=list)
    terrain_name: str = "open field"
    terrain_tags: list[str] = field(default_factory=list)
