from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Iterable, List

from .batch_hatchery import BatchHatchery
from .geoseal_hooks import geoseal_governance
from .lesson_engine import apply_lesson
from .semantic_mesh import encode_tokens, governance_signal


class Trainer:
    def __init__(self, world_seed: str):
        self.hatchery = BatchHatchery(world_seed=world_seed)

    def run_batch(self, batch_size: int, lessons: Iterable[str]) -> List[dict]:
        rows: List[dict] = []
        agents = self.hatchery.hatch_batch(batch_size)

        for genome, state in agents:
            for lesson in lessons:
                state = apply_lesson(state, lesson)
                mesh = encode_tokens([lesson, genome.world_seed, genome.egg_id])
                mesh_signal = governance_signal(mesh)

                outcome = geoseal_governance(state, genome)
                if mesh_signal < 0.2 and outcome == "ALLOW":
                    outcome = "QUARANTINE"

                rows.append(
                    {
                        "id": f"{genome.egg_id}-{lesson}",
                        "egg_id": genome.egg_id,
                        "world_seed": genome.world_seed,
                        "lesson": lesson,
                        "state": asdict(state),
                        "outcome": outcome,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "semantic_mesh_230_hex": mesh.to_hex(),
                        "semantic_mesh_signal": mesh_signal,
                    }
                )
        return rows
