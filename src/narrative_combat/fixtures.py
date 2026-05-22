from __future__ import annotations

from .models import Encounter, Feature, Fighter, PlannedGoal, Technique, Terrain


def boss_duel_demo(seed: int = 1337) -> Encounter:
    return Encounter(
        encounter_id="boss_duel_demo",
        seed=seed,
        style="xianxia",
        objective="choose",
        fighters=[
            Fighter(
                name="Wu Jin",
                tier="Iron Body",
                stats={"body": 8, "qi": 7, "speed": 9, "focus": 6},
                temperament=["prideful", "patient"],
                techniques=["falling_river_cleave", "stone_breath_guard"],
                concealed=["hidden_meridian_art"],
                resources={"qi": 30, "stamina": 20},
                goal="protect",
            ),
            Fighter(
                name="Ash-Crowned Bailiff",
                tier="Bronze Vein",
                stats={"body": 9, "qi": 8, "speed": 5, "focus": 7},
                temperament=["punitive", "certain"],
                techniques=["ash_seal_brand"],
                concealed=[],
                resources={"qi": 24, "stamina": 24},
                goal="humiliate",
            ),
        ],
        techniques=[
            Technique(
                technique_id="falling_river_cleave",
                name="Falling River Cleave",
                type="saber",
                cost=3,
                range="mid",
                grade="low",
                hidden=False,
                effect={"momentum_shift": 2, "guard_break": True},
                narrative_tags=["flood", "weight", "pressure"],
            ),
            Technique(
                technique_id="stone_breath_guard",
                name="Stone Breath Guard",
                type="body",
                cost=2,
                range="close",
                grade="low",
                hidden=False,
                effect={"momentum_shift": 1, "guard": True},
                narrative_tags=["stillness", "breath", "root"],
            ),
            Technique(
                technique_id="hidden_meridian_art",
                name="Hidden Meridian Art",
                type="qi",
                cost=9,
                range="self",
                grade="forbidden",
                hidden=True,
                effect={"momentum_shift": 4, "backlash": True},
                narrative_tags=["secret", "vein", "backlash"],
            ),
            Technique(
                technique_id="ash_seal_brand",
                name="Ash Seal Brand",
                type="curse",
                cost=4,
                range="mid",
                grade="middle",
                hidden=False,
                effect={"momentum_shift": -2, "bind": True},
                narrative_tags=["ash", "law", "brand"],
            ),
        ],
        terrain=Terrain(
            name="drained river shrine",
            constraints=["the cracked shrine floor cannot flood", "ash clouds reduce sight"],
            modifiers={"safe_zone": 1, "monster": -2, "treasure": 2},
            narrative_tags=["dry riverbed", "broken shrine", "ash haze"],
        ),
        features=[
            Feature(
                feature_id="breathing_pillar",
                kind="safe_zone",
                label="fallen shrine pillar",
                innate_test="patience",
                consequence="regroup without ceding the whole tempo",
            ),
            Feature(
                feature_id="buried_bell",
                kind="treasure",
                label="buried bronze bell",
                innate_test="restraint",
                consequence="unlock the old rhythm at the cost of an opening",
            ),
            Feature(
                feature_id="ash_officer",
                kind="monster",
                label="ash-bound officer",
                innate_test="resolve",
                consequence="face the hidden phase instead of retreating",
            ),
        ],
        planned_goal=PlannedGoal(
            winner="Wu Jin",
            price="spends the concealed meridian art and carries qi backlash",
            aftermath=["right arm tremor", "enemy ideology disproven but not erased"],
        ),
    )
