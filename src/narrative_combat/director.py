from __future__ import annotations

from random import Random
from typing import Any

from .models import Encounter, Feature, PhaseName
from .resolver import Resolver
from .translator import TemplateTranslator

PHASES: list[PhaseName] = [
    "objective",
    "first_tactic",
    "true_rule",
    "hidden_problem",
    "cost_unavoidable",
    "strategy_change",
    "understanding_wins",
    "aftermath",
]


def structurally_different(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return any(
        [
            left["path"]["chosen"] != right["path"]["chosen"],
            left["path"]["reversal_index"] != right["path"]["reversal_index"],
            left["path"]["price_index"] != right["path"]["price_index"],
            left["aftermath"]["price_paid"] != right["aftermath"]["price_paid"],
        ]
    )


class Director:
    def __init__(self, encounter: Encounter, translator: Any | None = None) -> None:
        self.encounter = encounter
        self._rng = Random(encounter.seed)
        self._resolver = Resolver(encounter.seed)
        # Inject any object with .render(beat, feature, technique, encounter) -> str.
        # Default stays the deterministic template so golden tests are unaffected.
        self._translator = translator if translator is not None else TemplateTranslator()

    def run(self) -> dict[str, Any]:
        chosen_features = self._chosen_features(list(self.encounter.features))
        shortest = ["monster", "treasure", "ending"]
        longest = ["safe_zone", "monster", "safe_zone", "treasure", "ending"]
        chosen = [feature.kind for feature in chosen_features] + ["ending"]
        reversal_index = self._pick_reversal_index(chosen_features)
        price_index = self._pick_price_index(chosen_features, reversal_index)

        attacker = self.encounter.fighters[0]
        defender = self.encounter.fighters[1]
        visible_techniques = [
            technique for technique in self.encounter.techniques if technique.technique_id in attacker.techniques
        ]
        concealed = next(
            technique for technique in self.encounter.techniques if technique.technique_id in attacker.concealed
        )

        momentum = 0
        concealed_spent = False
        beats: list[dict[str, Any]] = []
        for idx, feature in enumerate(chosen_features):
            phase = PHASES[min(idx + 1, len(PHASES) - 2)]
            if idx == price_index and not concealed_spent:
                technique = concealed
                concealed_spent = True
            else:
                technique = visible_techniques[idx % len(visible_techniques)]

            result = self._resolver.resolve(attacker, defender, technique, self.encounter.terrain, feature, momentum)
            momentum = max(-5, min(5, momentum + int(result.state_shift["momentum"])))
            beat = {
                "beat_id": f"beat_{idx + 1:03d}",
                "phase": phase,
                "feature": feature.kind,
                "roll": result.roll,
                "margin": result.margin,
                "band": result.band,
                "state_shift": result.state_shift,
            }
            beat["prose"] = self._translator.render(beat, feature, technique, self.encounter)
            beats.append(beat)

        continuity_facts: list[str] = []
        for beat in beats:
            continuity_facts.extend(beat["state_shift"].get("continuity_facts", []))

        return {
            "schema": "scbe.narrative_combat.fight.v1",
            "encounter_id": self.encounter.encounter_id,
            "seed": self.encounter.seed,
            "style": self.encounter.style,
            "objective": self.encounter.objective,
            "planned_goal": {
                "winner": self.encounter.planned_goal.winner,
                "price": self.encounter.planned_goal.price,
                "aftermath": self.encounter.planned_goal.aftermath,
            },
            "path": {
                "shortest": shortest,
                "longest": longest,
                "chosen": chosen,
                "reversal_index": reversal_index,
                "price_index": price_index,
            },
            "beats": beats,
            "aftermath": {
                "winner": self.encounter.planned_goal.winner,
                "price_paid": ["concealed technique revealed", "qi backlash"],
                "continuity_facts": continuity_facts,
            },
        }

    def _chosen_features(self, features: list[Feature]) -> list[Feature]:
        by_kind = {feature.kind: feature for feature in features}
        orders = [
            ["safe_zone", "treasure", "monster"],
            ["treasure", "safe_zone", "monster"],
            ["monster", "safe_zone", "treasure"],
        ]
        order = orders[self._rng.randrange(len(orders))]
        return [by_kind[kind] for kind in order]

    def _pick_reversal_index(self, features: list[Feature]) -> int:
        return next((idx for idx, feature in enumerate(features) if feature.kind == "monster"), 0)

    def _pick_price_index(self, features: list[Feature], reversal_index: int) -> int:
        treasure_index = next(
            (idx for idx, feature in enumerate(features) if feature.kind == "treasure"), len(features) - 1
        )
        if treasure_index == reversal_index and len(features) > 1:
            return min(len(features) - 1, treasure_index + 1)
        return treasure_index
