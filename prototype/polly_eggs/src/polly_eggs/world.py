from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class WorldCell:
    biome: str
    risk: float
    resources: int


class WorldSim:
    def __init__(self, seed: str, size: int = 16):
        self.seed = seed
        self.size = size
        rnd = random.Random(seed)
        biomes = ["forest", "ruins", "shore", "cavern", "plains"]
        self.grid = [
            [WorldCell(biome=rnd.choice(biomes), risk=rnd.random(), resources=rnd.randint(0, 6)) for _ in range(size)]
            for _ in range(size)
        ]
        self.tick = 0

    def step(self) -> None:
        self.tick += 1
        # Lightweight regeneration: every step, low-risk cells recover resources.
        for row in self.grid:
            for cell in row:
                if cell.risk < 0.35 and cell.resources < 8:
                    cell.resources += 1
