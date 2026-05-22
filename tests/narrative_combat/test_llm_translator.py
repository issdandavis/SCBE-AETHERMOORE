"""LLMTranslator: opt-in renderer must degrade safely and never break the engine."""

from __future__ import annotations

from src.narrative_combat.director import Director
from src.narrative_combat.fixtures import boss_duel_demo
from src.narrative_combat.translator import LLMTranslator, TemplateTranslator


def _beat(feature_kind: str) -> dict:
    return {
        "beat_id": "beat_001",
        "phase": "first_tactic",
        "feature": feature_kind,
        "roll": 17,
        "margin": 8,
        "band": "strong_advantage",
        "state_shift": {"momentum": 2, "resources": {}, "revealed": [], "injuries": []},
    }


def test_llm_translator_falls_back_to_template_when_ollama_unreachable():
    encounter = boss_duel_demo(seed=1337)
    feature = encounter.features[0]
    technique = encounter.techniques[0]
    beat = _beat(feature.kind)

    # Port 9 (discard) is reliably unreachable -> fast failure -> deterministic fallback.
    llm = LLMTranslator(host="http://127.0.0.1:9", timeout=1.0)
    template = TemplateTranslator()

    assert llm.render(beat, feature, technique, encounter) == template.render(beat, feature, technique, encounter)


def test_director_accepts_injected_translator_without_calling_network():
    encounter = boss_duel_demo(seed=1337)
    # An unreachable LLM translator must still yield a full fight (every beat falls back).
    fight = Director(encounter, translator=LLMTranslator(host="http://127.0.0.1:9", timeout=1.0)).run()

    assert fight["schema"] == "scbe.narrative_combat.fight.v1"
    assert fight["beats"]
    for beat in fight["beats"]:
        assert beat["prose"]
