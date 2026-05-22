# Narrative Combat Generator Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first deterministic vertical slice of the narrative combat generator: fixture encounter -> director path -> resolver state shifts -> template prose -> JSON fight packet.

**Architecture:** Implement a small standalone Python package at `src/narrative_combat/` with no SCBE governance dependency and no LLM dependency. The engine uses dataclasses for combat domain objects, a seeded resolver for deterministic pivots, a path-director for feature ordering/reversal/price placement, and a template translator for stable prose.

**Tech Stack:** Python 3.11+, dataclasses, `random.Random`, pytest, JSON CLI output.

---

## File Structure

- Create: `src/narrative_combat/__init__.py`
  - Public exports for the vertical slice.
- Create: `src/narrative_combat/models.py`
  - Dataclasses and literal types: fighters, techniques, terrain, features, encounter, beats, fight packet.
- Create: `src/narrative_combat/fixtures.py`
  - One hardcoded boss-duel demo fixture used by CLI and tests.
- Create: `src/narrative_combat/resolver.py`
  - Seeded dice, margin calculation, outcome band mapping, state-shift emission.
- Create: `src/narrative_combat/director.py`
  - Plans shortest/longest/chosen path, enforces phase waypoints, places reversal and price.
- Create: `src/narrative_combat/translator.py`
  - Deterministic `TemplateTranslator`.
- Create: `src/narrative_combat/cli.py`
  - CLI that writes the fight packet to stdout or a file.
- Create: `tests/narrative_combat/test_vertical_slice.py`
  - End-to-end packet, determinism, structural reroll, wall, and translator tests.

---

### Task 1: Domain Models and Fixture Contract

**Files:**
- Create: `src/narrative_combat/__init__.py`
- Create: `src/narrative_combat/models.py`
- Create: `src/narrative_combat/fixtures.py`
- Test: `tests/narrative_combat/test_vertical_slice.py`

- [ ] **Step 1: Write the failing model/fixture test**

Add this to `tests/narrative_combat/test_vertical_slice.py`:

```python
from src.narrative_combat.fixtures import boss_duel_demo


def test_boss_duel_fixture_has_required_vertical_slice_parts():
    encounter = boss_duel_demo(seed=1337)

    assert encounter.encounter_id == "boss_duel_demo"
    assert encounter.seed == 1337
    assert encounter.objective == "choose"
    assert len(encounter.fighters) == 2
    assert len(encounter.techniques) == 4
    assert len(encounter.features) == 3
    assert {feature.kind for feature in encounter.features} == {"safe_zone", "treasure", "monster"}
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/narrative_combat/test_vertical_slice.py::test_boss_duel_fixture_has_required_vertical_slice_parts -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.narrative_combat'`.

- [ ] **Step 3: Create the package exports**

Create `src/narrative_combat/__init__.py`:

```python
"""Standalone narrative combat generator vertical slice."""

from .fixtures import boss_duel_demo
from .models import Encounter, Feature, Fighter, Technique, Terrain

__all__ = [
    "Encounter",
    "Feature",
    "Fighter",
    "Technique",
    "Terrain",
    "boss_duel_demo",
]
```

- [ ] **Step 4: Create domain dataclasses**

Create `src/narrative_combat/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


FeatureKind = Literal["safe_zone", "treasure", "monster", "friend", "hazard"]
OutcomeBand = Literal[
    "dominating_strike",
    "strong_advantage",
    "minor_success",
    "clash",
    "defensive_loss",
    "severe_opening_exposed",
    "catastrophic_reversal",
]
PhaseName = Literal[
    "objective",
    "first_tactic",
    "true_rule",
    "hidden_problem",
    "cost_unavoidable",
    "strategy_change",
    "understanding_wins",
    "aftermath",
]


@dataclass(frozen=True)
class Fighter:
    name: str
    tier: str
    stats: dict[str, int]
    temperament: list[str]
    techniques: list[str]
    concealed: list[str] = field(default_factory=list)
    resources: dict[str, int] = field(default_factory=dict)
    injuries: list[str] = field(default_factory=list)
    momentum: int = 0
    morale: float = 1.0
    goal: str = "win"


@dataclass(frozen=True)
class Technique:
    technique_id: str
    name: str
    type: str
    cost: int
    range: str
    grade: str
    hidden: bool
    effect: dict[str, int | bool | str]
    narrative_tags: list[str]


@dataclass(frozen=True)
class Terrain:
    name: str
    constraints: list[str]
    modifiers: dict[str, int]
    narrative_tags: list[str]


@dataclass(frozen=True)
class Feature:
    feature_id: str
    kind: FeatureKind
    label: str
    innate_test: str
    consequence: str


@dataclass(frozen=True)
class PlannedGoal:
    winner: str
    price: str
    aftermath: list[str]


@dataclass(frozen=True)
class Encounter:
    encounter_id: str
    seed: int
    style: str
    objective: str
    fighters: list[Fighter]
    techniques: list[Technique]
    terrain: Terrain
    features: list[Feature]
    planned_goal: PlannedGoal
```

- [ ] **Step 5: Create the fixture**

Create `src/narrative_combat/fixtures.py`:

```python
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
```

- [ ] **Step 6: Run test to verify it passes**

Run:

```powershell
python -m pytest tests/narrative_combat/test_vertical_slice.py::test_boss_duel_fixture_has_required_vertical_slice_parts -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add src/narrative_combat tests/narrative_combat/test_vertical_slice.py
git commit -m "feat(narrative-combat): add vertical slice fixture"
```

---

### Task 2: Seeded Resolver and State Shifts

**Files:**
- Modify: `src/narrative_combat/models.py`
- Create: `src/narrative_combat/resolver.py`
- Test: `tests/narrative_combat/test_vertical_slice.py`

- [ ] **Step 1: Add failing resolver tests**

Append:

```python
from src.narrative_combat.resolver import Resolver, outcome_band


def test_outcome_band_mapping_uses_narrative_bands_not_damage():
    assert outcome_band(15) == "dominating_strike"
    assert outcome_band(8) == "strong_advantage"
    assert outcome_band(2) == "minor_success"
    assert outcome_band(0) == "clash"
    assert outcome_band(-3) == "defensive_loss"
    assert outcome_band(-8) == "severe_opening_exposed"
    assert outcome_band(-15) == "catastrophic_reversal"


def test_resolver_is_seeded_and_never_emits_damage():
    encounter = boss_duel_demo(seed=1337)
    resolver_a = Resolver(seed=encounter.seed)
    resolver_b = Resolver(seed=encounter.seed)
    attacker = encounter.fighters[0]
    defender = encounter.fighters[1]
    technique = encounter.techniques[0]
    feature = encounter.features[0]

    result_a = resolver_a.resolve(attacker, defender, technique, encounter.terrain, feature, momentum=0)
    result_b = resolver_b.resolve(attacker, defender, technique, encounter.terrain, feature, momentum=0)

    assert result_a == result_b
    assert "damage" not in result_a.state_shift
    assert result_a.roll >= 1
    assert result_a.roll <= 20
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/narrative_combat/test_vertical_slice.py::test_outcome_band_mapping_uses_narrative_bands_not_damage tests/narrative_combat/test_vertical_slice.py::test_resolver_is_seeded_and_never_emits_damage -q
```

Expected: FAIL with missing `src.narrative_combat.resolver`.

- [ ] **Step 3: Add resolver result model**

Append to `src/narrative_combat/models.py`:

```python

@dataclass(frozen=True)
class ResolveResult:
    roll: int
    margin: int
    band: OutcomeBand
    state_shift: dict[str, object]
```

- [ ] **Step 4: Implement resolver**

Create `src/narrative_combat/resolver.py`:

```python
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
            state_shift["continuity_facts"] = [
                f"{attacker.name}'s right arm trembles after meridian backlash."
            ]

        return ResolveResult(roll=roll, margin=margin, band=band, state_shift=state_shift)
```

- [ ] **Step 5: Run resolver tests**

Run:

```powershell
python -m pytest tests/narrative_combat/test_vertical_slice.py::test_outcome_band_mapping_uses_narrative_bands_not_damage tests/narrative_combat/test_vertical_slice.py::test_resolver_is_seeded_and_never_emits_damage -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add src/narrative_combat/models.py src/narrative_combat/resolver.py tests/narrative_combat/test_vertical_slice.py
git commit -m "feat(narrative-combat): add seeded resolver"
```

---

### Task 3: Director Path Planning and Fight Packet

**Files:**
- Modify: `src/narrative_combat/models.py`
- Create: `src/narrative_combat/director.py`
- Test: `tests/narrative_combat/test_vertical_slice.py`

- [ ] **Step 1: Add failing director tests**

Append:

```python
from src.narrative_combat.director import Director, structurally_different


def test_director_emits_required_packet_shape_and_invariants():
    fight = Director(boss_duel_demo(seed=1337)).run()

    assert fight["schema"] == "scbe.narrative_combat.fight.v1"
    assert fight["encounter_id"] == "boss_duel_demo"
    assert fight["seed"] == 1337
    assert fight["path"]["chosen"] != fight["path"]["shortest"]
    assert fight["path"]["chosen"] != fight["path"]["longest"]
    assert fight["path"]["reversal_index"] >= 0
    assert fight["path"]["price_index"] >= 0
    assert fight["aftermath"]["winner"] == "Wu Jin"
    assert fight["aftermath"]["price_paid"]

    for beat in fight["beats"]:
        assert {"beat_id", "phase", "feature", "roll", "margin", "band", "state_shift", "prose"} <= set(beat)


def test_structural_reroll_uses_more_than_different_wording():
    fight_a = Director(boss_duel_demo(seed=1337)).run()
    fight_b = Director(boss_duel_demo(seed=2026)).run()

    assert structurally_different(fight_a, fight_b)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/narrative_combat/test_vertical_slice.py::test_director_emits_required_packet_shape_and_invariants tests/narrative_combat/test_vertical_slice.py::test_structural_reroll_uses_more_than_different_wording -q
```

Expected: FAIL with missing `src.narrative_combat.director`.

- [ ] **Step 3: Implement director**

Create `src/narrative_combat/director.py`:

```python
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
    def __init__(self, encounter: Encounter) -> None:
        self.encounter = encounter
        self._rng = Random(encounter.seed)
        self._resolver = Resolver(encounter.seed)
        self._translator = TemplateTranslator()

    def run(self) -> dict[str, Any]:
        features = list(self.encounter.features)
        feature_by_kind = {feature.kind: feature for feature in features}
        shortest = ["monster", "treasure", "ending"]
        longest = ["safe_zone", "monster", "safe_zone", "treasure", "ending"]
        chosen_features = self._chosen_features(features)
        chosen = [feature.kind for feature in chosen_features] + ["ending"]
        reversal_index = self._pick_reversal_index(chosen_features)
        price_index = self._pick_price_index(chosen_features, reversal_index)

        attacker = self.encounter.fighters[0]
        defender = self.encounter.fighters[1]
        visible_techniques = [tech for tech in self.encounter.techniques if tech.technique_id in attacker.techniques]
        concealed = next(tech for tech in self.encounter.techniques if tech.technique_id in attacker.concealed)

        momentum = 0
        beats: list[dict[str, Any]] = []
        for idx, feature in enumerate(chosen_features):
            phase = PHASES[min(idx + 1, len(PHASES) - 2)]
            technique = concealed if idx == price_index else visible_techniques[idx % len(visible_techniques)]
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

        price_paid = ["concealed technique revealed", "qi backlash"]
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
                "price_paid": price_paid,
                "continuity_facts": continuity_facts,
            },
        }

    def _chosen_features(self, features: list[Feature]) -> list[Feature]:
        ordered = list(features)
        self._rng.shuffle(ordered)
        if [feature.kind for feature in ordered] == ["monster", "treasure"]:
            ordered.insert(0, next(feature for feature in features if feature.kind == "safe_zone"))
        return ordered

    def _pick_reversal_index(self, features: list[Feature]) -> int:
        monster_index = next((idx for idx, feature in enumerate(features) if feature.kind == "monster"), 0)
        return monster_index

    def _pick_price_index(self, features: list[Feature], reversal_index: int) -> int:
        treasure_index = next((idx for idx, feature in enumerate(features) if feature.kind == "treasure"), len(features) - 1)
        if treasure_index == reversal_index and len(features) > 1:
            return min(len(features) - 1, treasure_index + 1)
        return treasure_index
```

- [ ] **Step 4: Run director tests**

Run:

```powershell
python -m pytest tests/narrative_combat/test_vertical_slice.py::test_director_emits_required_packet_shape_and_invariants tests/narrative_combat/test_vertical_slice.py::test_structural_reroll_uses_more_than_different_wording -q
```

Expected: initially FAIL because `TemplateTranslator` does not exist.

- [ ] **Step 5: Commit only after Task 4 creates translator**

Do not commit this task until Task 4 completes because `director.py` imports the translator.

---

### Task 4: Deterministic Template Translator

**Files:**
- Create: `src/narrative_combat/translator.py`
- Test: `tests/narrative_combat/test_vertical_slice.py`

- [ ] **Step 1: Add failing translator test**

Append:

```python
from src.narrative_combat.translator import TemplateTranslator


def test_template_translator_is_deterministic_and_mentions_feature_cost_or_rule():
    encounter = boss_duel_demo(seed=1337)
    feature = encounter.features[0]
    technique = encounter.techniques[0]
    beat = {
        "beat_id": "beat_001",
        "phase": "first_tactic",
        "feature": feature.kind,
        "roll": 17,
        "margin": 8,
        "band": "strong_advantage",
        "state_shift": {"momentum": 2, "resources": {"Wu Jin.qi": -3}, "revealed": [], "injuries": []},
    }
    translator = TemplateTranslator()

    rendered_a = translator.render(beat, feature, technique, encounter)
    rendered_b = translator.render(beat, feature, technique, encounter)

    assert rendered_a == rendered_b
    assert feature.label in rendered_a
    assert technique.name in rendered_a
    assert "strong advantage" in rendered_a
```

- [ ] **Step 2: Run translator test to verify it fails**

Run:

```powershell
python -m pytest tests/narrative_combat/test_vertical_slice.py::test_template_translator_is_deterministic_and_mentions_feature_cost_or_rule -q
```

Expected: FAIL with missing `TemplateTranslator`.

- [ ] **Step 3: Implement translator**

Create `src/narrative_combat/translator.py`:

```python
from __future__ import annotations

from typing import Any

from .models import Encounter, Feature, Technique


class TemplateTranslator:
    def render(self, beat: dict[str, Any], feature: Feature, technique: Technique, encounter: Encounter) -> str:
        band = str(beat["band"]).replace("_", " ")
        actor = encounter.fighters[0].name
        opponent = encounter.fighters[1].name
        cost = technique.cost
        test = feature.innate_test
        consequence = feature.consequence
        return (
            f"{actor} meets the {test} test at the {feature.label}. "
            f"He answers with {technique.name}, spending {cost} qi. "
            f"The exchange lands as {band} against {opponent}: {consequence}."
        )
```

- [ ] **Step 4: Run translator and director tests**

Run:

```powershell
python -m pytest tests/narrative_combat/test_vertical_slice.py::test_template_translator_is_deterministic_and_mentions_feature_cost_or_rule tests/narrative_combat/test_vertical_slice.py::test_director_emits_required_packet_shape_and_invariants tests/narrative_combat/test_vertical_slice.py::test_structural_reroll_uses_more_than_different_wording -q
```

Expected: PASS.

- [ ] **Step 5: Commit Tasks 3 and 4 together**

```powershell
git add src/narrative_combat/director.py src/narrative_combat/translator.py tests/narrative_combat/test_vertical_slice.py
git commit -m "feat(narrative-combat): generate deterministic fight packets"
```

---

### Task 5: Wall and Continuity Invariant Tests

**Files:**
- Modify: `tests/narrative_combat/test_vertical_slice.py`
- Modify: `src/narrative_combat/director.py` if needed

- [ ] **Step 1: Add invariant tests**

Append:

```python
def test_fight_never_spends_negative_qi_and_reveals_hidden_card_once():
    fight = Director(boss_duel_demo(seed=1337)).run()
    qi_spent = 0
    hidden_reveals = []

    for beat in fight["beats"]:
        resources = beat["state_shift"]["resources"]
        qi_spent += abs(sum(resources.values()))
        hidden_reveals.extend(beat["state_shift"].get("revealed", []))

    assert qi_spent <= 30
    assert hidden_reveals == ["hidden_meridian_art"]


def test_aftermath_carries_continuity_fact_from_price():
    fight = Director(boss_duel_demo(seed=1337)).run()

    assert any("right arm trembles" in fact for fact in fight["aftermath"]["continuity_facts"])
```

- [ ] **Step 2: Run invariant tests**

Run:

```powershell
python -m pytest tests/narrative_combat/test_vertical_slice.py::test_fight_never_spends_negative_qi_and_reveals_hidden_card_once tests/narrative_combat/test_vertical_slice.py::test_aftermath_carries_continuity_fact_from_price -q
```

Expected: PASS. If hidden technique reveals more than once, update `Director.run()` to track `concealed_spent = False` and only use the concealed technique when `idx == price_index and not concealed_spent`.

- [ ] **Step 3: Run full vertical slice tests**

Run:

```powershell
python -m pytest tests/narrative_combat/test_vertical_slice.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add src/narrative_combat/director.py tests/narrative_combat/test_vertical_slice.py
git commit -m "test(narrative-combat): lock wall and aftermath invariants"
```

---

### Task 6: CLI Output

**Files:**
- Create: `src/narrative_combat/cli.py`
- Test: `tests/narrative_combat/test_vertical_slice.py`

- [ ] **Step 1: Add CLI test**

Append:

```python
import json
import subprocess
import sys


def test_cli_writes_json_packet_to_stdout():
    result = subprocess.run(
        [sys.executable, "-m", "src.narrative_combat.cli", "--seed", "1337"],
        check=True,
        capture_output=True,
        text=True,
    )
    packet = json.loads(result.stdout)

    assert packet["schema"] == "scbe.narrative_combat.fight.v1"
    assert packet["seed"] == 1337
    assert packet["beats"]
```

- [ ] **Step 2: Run CLI test to verify it fails**

Run:

```powershell
python -m pytest tests/narrative_combat/test_vertical_slice.py::test_cli_writes_json_packet_to_stdout -q
```

Expected: FAIL with missing `src.narrative_combat.cli`.

- [ ] **Step 3: Implement CLI**

Create `src/narrative_combat/cli.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .director import Director
from .fixtures import boss_duel_demo


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a narrative combat fight packet.")
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    packet = Director(boss_duel_demo(seed=args.seed)).run()
    payload = json.dumps(packet, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run CLI test**

Run:

```powershell
python -m pytest tests/narrative_combat/test_vertical_slice.py::test_cli_writes_json_packet_to_stdout -q
```

Expected: PASS.

- [ ] **Step 5: Run a manual CLI output sample**

Run:

```powershell
python -m src.narrative_combat.cli --seed 1337 --out artifacts\narrative_combat\boss_duel_demo.seed1337.json
```

Expected: file exists and contains `scbe.narrative_combat.fight.v1`.

- [ ] **Step 6: Commit**

```powershell
git add src/narrative_combat/cli.py tests/narrative_combat/test_vertical_slice.py artifacts/narrative_combat/boss_duel_demo.seed1337.json
git commit -m "feat(narrative-combat): add fight packet CLI"
```

---

### Task 7: Final Verification

**Files:**
- Modify only if verification finds a real failure.

- [ ] **Step 1: Run focused test suite**

```powershell
python -m pytest tests/narrative_combat/test_vertical_slice.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Compile package**

```powershell
python -m py_compile src\narrative_combat\__init__.py src\narrative_combat\models.py src\narrative_combat\fixtures.py src\narrative_combat\resolver.py src\narrative_combat\director.py src\narrative_combat\translator.py src\narrative_combat\cli.py
```

Expected: command exits 0.

- [ ] **Step 3: Confirm package is isolated from SCBE governance**

```powershell
rg -n "geoseal|governance|harmonic|SCBE_FORCE|liboqs|agentbus|agent-bus" src\narrative_combat tests\narrative_combat
```

Expected: no matches except intentional schema string if added later.

- [ ] **Step 4: Commit any verification fixes**

Only if files changed:

```powershell
git add src/narrative_combat tests/narrative_combat
git commit -m "fix(narrative-combat): stabilize vertical slice verification"
```

---

## Self-Review

Spec coverage:

- Story-first/no-HP model: Tasks 1-5 define state shifts, not damage.
- Maze/pathfinder director: Task 3 implements shortest/longest/chosen path and structural reroll checks.
- Feature graph and innate tests: Task 1 fixture defines safe zone, treasure, monster with tests; Task 3 consumes them.
- Dice as pivots: Task 2 maps margins to narrative bands and state shifts.
- Determinism: Tasks 2, 3, and 6 test seeded repeatability and CLI packet output.
- Translator backend: Task 4 implements deterministic `TemplateTranslator`; LLM translator remains intentionally out of scope.
- Packet compatibility: Task 3 emits `scbe.narrative_combat.fight.v1`.
- Wall/continuity tests: Task 5 locks qi spend, concealed reveal, and aftermath facts.

Placeholder scan:

- No TBD/TODO/fill-in placeholders remain.
- Every code step includes concrete code.
- Every test step includes an exact command and expected result.

Type consistency:

- `Feature.kind`, `Technique.technique_id`, `Encounter.seed`, `ResolveResult.state_shift`, `Director.run()` packet fields are used consistently across tasks.

