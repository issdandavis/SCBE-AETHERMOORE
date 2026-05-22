"""A demo encounter for the Go-board engine: two cultivation factions over a drained shrine."""

from __future__ import annotations

from .models import GoEncounter, Party, QiNode


def boss_board_demo(seed: int = 1337) -> GoEncounter:
    return GoEncounter(
        encounter_id="boss_board_demo",
        seed=seed,
        style="xianxia",
        board_size=9,
        parties=[
            Party(
                name="Iron Lotus Sect",
                color=0,
                temperament=["relentless", "disciplined"],
                goal="break the magistrate's hold on the shrine",
            ),
            Party(
                name="Ash-Crowned Bailiff",
                color=1,
                temperament=["punitive", "certain"],
                goal="enforce the old law to the letter",
            ),
        ],
        qi_nodes=[QiNode(point=(4, 4), value=3), QiNode(point=(7, 1), value=2)],
        terrain_name="drained river shrine",
        terrain_tags=["dry riverbed", "broken shrine", "ash haze"],
    )
