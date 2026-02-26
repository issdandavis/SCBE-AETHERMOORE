from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class EggGenome:
    egg_id: str
    world_seed: str
    language_bias: float = 0.5
    geoseal_sensitivity: float = 0.7
    curiosity: float = 0.5


@dataclass
class AgentState:
    egg_id: str
    learning: float = 0.1
    safety: float = 0.8
    stability: float = 0.6
    drift: float = 0.1
    inventory: Dict[str, int] = field(default_factory=dict)

    def clamp(self) -> None:
        self.learning = min(1.0, max(0.0, self.learning))
        self.safety = min(1.0, max(0.0, self.safety))
        self.stability = min(1.0, max(0.0, self.stability))
        self.drift = min(1.0, max(0.0, self.drift))
