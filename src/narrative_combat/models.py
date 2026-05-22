from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

FeatureKind = Literal["safe_zone", "treasure", "monster", "friend", "hazard"]
OutcomeBand = Literal[
    "dominating_strike",
    "strong_advantage",
    "minor_success",
    "clash",
    "defensive_loss",
    "severe_opening_exposed",
    "catastrophic_reversal",
]
PhaseName = Literal[
    "objective",
    "first_tactic",
    "true_rule",
    "hidden_problem",
    "cost_unavoidable",
    "strategy_change",
    "understanding_wins",
    "aftermath",
]


@dataclass(frozen=True)
class Fighter:
    name: str
    tier: str
    stats: dict[str, int]
    temperament: list[str]
    techniques: list[str]
    concealed: list[str] = field(default_factory=list)
    resources: dict[str, int] = field(default_factory=dict)
    injuries: list[str] = field(default_factory=list)
    momentum: int = 0
    morale: float = 1.0
    goal: str = "win"


@dataclass(frozen=True)
class Technique:
    technique_id: str
    name: str
    type: str
    cost: int
    range: str
    grade: str
    hidden: bool
    effect: dict[str, int | bool | str]
    narrative_tags: list[str]


@dataclass(frozen=True)
class Terrain:
    name: str
    constraints: list[str]
    modifiers: dict[str, int]
    narrative_tags: list[str]


@dataclass(frozen=True)
class Feature:
    feature_id: str
    kind: FeatureKind
    label: str
    innate_test: str
    consequence: str


@dataclass(frozen=True)
class PlannedGoal:
    winner: str
    price: str
    aftermath: list[str]


@dataclass(frozen=True)
class Encounter:
    encounter_id: str
    seed: int
    style: str
    objective: str
    fighters: list[Fighter]
    techniques: list[Technique]
    terrain: Terrain
    features: list[Feature]
    planned_goal: PlannedGoal


@dataclass(frozen=True)
class ResolveResult:
    roll: int
    margin: int
    band: OutcomeBand
    state_shift: dict[str, object]
