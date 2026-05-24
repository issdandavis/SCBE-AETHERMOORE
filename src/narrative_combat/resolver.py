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


def hidden_price(attacker: Fighter, technique: Technique) -> dict[str, list[str]]:
    """Return the non-damage cost of revealing a hidden technique.

    Hidden is a social/mechanical state, not a synonym for forbidden backlash.
    A concealed meridian art can harm the body; an unclassified read should
    usually expose the cultivator to scrutiny instead.
    """

    if not technique.hidden:
        return {"injuries": [], "continuity_facts": [], "price_paid": []}

    if bool(technique.effect.get("backlash", False)):
        return {
            "injuries": [f"{attacker.name} suffers meridian backlash"],
            "continuity_facts": [f"{attacker.name}'s right arm trembles after meridian backlash."],
            "price_paid": ["qi backlash"],
        }

    if bool(technique.effect.get("classification_break", False)):
        return {
            "injuries": [],
            "continuity_facts": [f"{attacker.name}'s method is recorded as irregular rather than ranked."],
            "price_paid": ["classification pressure"],
        }

    if technique.type == "sense":
        return {
            "injuries": [],
            "continuity_facts": [f"{attacker.name}'s read is exposed before anyone can name it."],
            "price_paid": ["social exposure"],
        }

    return {"injuries": [], "continuity_facts": [], "price_paid": ["hidden method exposed"]}


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
            "price_paid": ["concealed technique revealed"] if technique.hidden else [],
        }
        price = hidden_price(attacker, technique)
        state_shift["injuries"] = price["injuries"]
        state_shift["continuity_facts"] = price["continuity_facts"]
        state_shift["price_paid"] = list(state_shift["price_paid"]) + price["price_paid"]

        return ResolveResult(roll=roll, margin=margin, band=band, state_shift=state_shift)
