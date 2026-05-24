import json
import subprocess
import sys

from src.narrative_combat.fixtures import boss_duel_demo
from src.narrative_combat.director import Director, structurally_different
from src.narrative_combat.resolver import Resolver, hidden_price, outcome_band
from src.narrative_combat.translator import TemplateTranslator


def test_boss_duel_fixture_has_required_vertical_slice_parts():
    encounter = boss_duel_demo(seed=1337)

    assert encounter.encounter_id == "boss_duel_demo"
    assert encounter.seed == 1337
    assert encounter.objective == "choose"
    assert len(encounter.fighters) == 2
    assert len(encounter.techniques) == 4
    assert len(encounter.features) == 3
    assert {feature.kind for feature in encounter.features} == {"safe_zone", "treasure", "monster"}


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
    assert 1 <= result_a.roll <= 20


def test_hidden_meridian_art_keeps_body_backlash_price():
    encounter = boss_duel_demo(seed=1337)
    attacker = encounter.fighters[0]
    technique = next(t for t in encounter.techniques if t.technique_id == "hidden_meridian_art")

    price = hidden_price(attacker, technique)

    assert price["price_paid"] == ["qi backlash"]
    assert any("meridian backlash" in injury for injury in price["injuries"])


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
