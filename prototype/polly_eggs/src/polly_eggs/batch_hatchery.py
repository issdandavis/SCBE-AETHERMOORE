from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .models import AgentState, EggGenome


@dataclass
class BatchHatchery:
    world_seed: str

    def hatch_batch(self, count: int) -> List[tuple[EggGenome, AgentState]]:
        out: List[tuple[EggGenome, AgentState]] = []
        for i in range(count):
            egg_id = f"egg-{i:04d}"
            genome = EggGenome(egg_id=egg_id, world_seed=self.world_seed)
            state = AgentState(egg_id=egg_id)
            out.append((genome, state))
        return out
