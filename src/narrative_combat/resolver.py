from __future__ import annotations

from random import Random

from .models import Feature, Fighter, OutcomeBand, ResolveResult, Technique, Terrain


def outcome_band(margin: int) -> OutcomeBand:
    if margin >= 15:
        return "dominating_strike"
    if margin >= 5:
        return "strong_advantage"
    if margin >= 1:
        return "minor_success"
    if margin == 0:
        return "clash"
    if margin >= -5:
        return "defensive_loss"
    if margin >= -10:
        return "severe_opening_exposed"
    return "catastrophic_reversal"


class Resolver:
    def __init__(self, seed: int) -> None:
        self._rng = Random(seed)

    def resolve(
        self,
        attacker: Fighter,
        defender: Fighter,
        technique: Technique,
        terrain: Terrain,
        feature: Feature,
        momentum: int,
    ) -> ResolveResult:
        roll = self._rng.randint(1, 20)
        combat_stat = attacker.stats.get("qi", 0)
        technique_mod = int(technique.effect.get("momentum_shift", 0))
        terrain_mod = terrain.modifiers.get(feature.kind, 0)
        defender_state = defender.stats.get("focus", 0)
        margin = roll + combat_stat + technique_mod + momentum + terrain_mod - defender_state
        band = outcome_band(margin)

        momentum_delta = max(-3, min(3, margin // 5))
        qi_key = f"{attacker.name}.qi"
        state_shift: dict[str, object] = {
            "momentum": momentum_delta,
            "resources": {qi_key: -technique.cost},
            "revealed": [technique.technique_id] if technique.hidden else [],
            "injuries": [],
            "continuity_facts": [],
        }
        if technique.hidden:
            state_shift["injuries"] = [f"{attacker.name} suffers meridian backlash"]
            state_shift["continuity_facts"] = [f"{attacker.name}'s right arm trembles after meridian backlash."]

        return ResolveResult(roll=roll, margin=margin, band=band, state_shift=state_shift)
