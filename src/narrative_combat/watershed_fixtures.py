from __future__ import annotations

from .go_board.models import GoEncounter, Party, QiNode
from .models import Encounter, Feature, Fighter, PlannedGoal, Technique, Terrain


def yun_zhou_yu_ping_corridor(seed: int = 20260524) -> Encounter:
    """Watershed book fixture: scattered reading vs clean fire control.

    This is not balanced as a game duel. It is a scene engine fixture. Yun Zhou is not
    secretly stronger; the terrain and feature path let his tendency-sense matter.
    """

    return Encounter(
        encounter_id="watershed_yun_zhou_yu_ping_corridor",
        seed=seed,
        style="watershed_xianxia",
        objective="stabilize",
        fighters=[
            Fighter(
                name="Pei Yun Zhou",
                tier="Qi Gathering early",
                stats={"body": 5, "qi": 4, "speed": 8, "focus": 6},
                temperament=["restless", "terrain-reading", "plainspoken"],
                techniques=["wind_step", "water_recovery"],
                concealed=["shi_gan_read"],
                resources={"qi": 16, "stamina": 22},
                goal="keep the group alive",
            ),
            Fighter(
                name="Su Yu Ping",
                tier="Qi Gathering mid",
                stats={"body": 5, "qi": 9, "speed": 6, "focus": 8},
                temperament=["disciplined", "impatient", "technically exact"],
                techniques=["needle_flame_thread"],
                resources={"qi": 28, "stamina": 18},
                goal="clear the obstruction cleanly",
            ),
        ],
        techniques=[
            Technique(
                technique_id="wind_step",
                name="Wind Step",
                type="movement",
                cost=2,
                range="close",
                grade="low",
                hidden=False,
                effect={"momentum_shift": 1, "positioning": True},
                narrative_tags=["quick", "thin", "sideways"],
            ),
            Technique(
                technique_id="water_recovery",
                name="Water Recovery",
                type="breath",
                cost=2,
                range="self",
                grade="low",
                hidden=False,
                effect={"momentum_shift": 0, "recover": True},
                narrative_tags=["breath", "flow", "return"],
            ),
            Technique(
                technique_id="shi_gan_read",
                name="Shi Gan Read",
                type="sense",
                cost=3,
                range="room",
                grade="unclassified",
                hidden=True,
                effect={"momentum_shift": 4, "avoidance": True, "backlash": False},
                narrative_tags=["lean", "warning", "almost"],
            ),
            Technique(
                technique_id="needle_flame_thread",
                name="Needle Flame Thread",
                type="fire",
                cost=4,
                range="mid",
                grade="low",
                hidden=False,
                effect={"momentum_shift": 3, "precision": True},
                narrative_tags=["clean", "hot", "narrow"],
            ),
        ],
        terrain=Terrain(
            name="wet archive corridor",
            constraints=[
                "the rotten sub-floor cannot take sudden heat",
                "water is running opposite the lintel inscription",
                "the lower supports are dry enough to burn",
            ],
            modifiers={"safe_zone": 1, "hazard": 3, "treasure": 1, "monster": -1},
            narrative_tags=["winter damp", "rotted frame", "wrong-running water"],
        ),
        features=[
            Feature(
                feature_id="wrong_water",
                kind="monster",
                label="wrong-running water",
                innate_test="attention",
                consequence="the safe-looking floor becomes the danger",
            ),
            Feature(
                feature_id="dry_supports",
                kind="safe_zone",
                label="dry lower supports",
                innate_test="restraint",
                consequence="heat would solve one problem and start another",
            ),
            Feature(
                feature_id="dropped_floor",
                kind="treasure",
                label="dropped floor seam",
                innate_test="trust",
                consequence="the hidden conduit is found without burning the room",
            ),
        ],
        planned_goal=PlannedGoal(
            winner="Pei Yun Zhou",
            price="reveals an unclassified read he cannot explain",
            aftermath=[
                "Su Yu Ping respects the result before she respects the explanation",
                "the patriarch checks an old Watershed text after supper",
            ],
        ),
    )


def watershed_ruin_group_board(seed: int = 20260524) -> GoEncounter:
    """Group-pressure fixture for ruin fights, formations, and tournament scenarios."""

    return GoEncounter(
        encounter_id="watershed_ruin_group_board",
        seed=seed,
        style="watershed_xianxia",
        board_size=9,
        parties=[
            Party(
                name="Watershed children",
                color=0,
                temperament=["uneven", "observant", "loyal"],
                goal="stabilize the ruin without losing anyone",
            ),
            Party(
                name="Ruin pressure",
                color=1,
                temperament=["old", "patient", "structural"],
                goal="force the unready to reveal what they are",
            ),
        ],
        qi_nodes=[
            QiNode(point=(4, 4), value=3),
            QiNode(point=(1, 6), value=2),
            QiNode(point=(6, 2), value=2),
        ],
        terrain_name="outer Watershed hall",
        terrain_tags=["cracked anchors", "old drainage", "live seal beneath stone"],
    )
