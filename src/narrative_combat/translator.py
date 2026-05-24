from __future__ import annotations

from typing import Any

from .models import Encounter, Feature, Technique


class TemplateTranslator:
    """Deterministic prose. The default renderer: no model, no network, golden-stable."""

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


class LLMTranslator:
    """Opt-in renderer that turns one engine-authoritative beat into styled prose.

    The engine owns truth (band, technique, cost, feature, outcome). This only
    *renders* those fixed facts as 2-4 sentences of cultivation-genre prose; it is
    forbidden, by prompt, from inventing outcomes/injuries/winners/techniques. Any
    failure (Ollama down, timeout, empty reply) falls back to the deterministic
    TemplateTranslator, so a fight always produces prose. Non-determinism here is
    expected and isolated to the prose layer (cacheable by (seed, beat_id)).
    """

    def __init__(
        self,
        model: str = "glm-5.1:cloud",
        host: str = "http://127.0.0.1:11434",
        style: str = "xianxia",
        timeout: float = 60.0,
        fallback: Any | None = None,
    ) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.style = style
        self.timeout = timeout
        self.fallback = fallback if fallback is not None else TemplateTranslator()

    def render(self, beat: dict[str, Any], feature: Feature, technique: Technique, encounter: Encounter) -> str:
        try:
            return self._render_llm(beat, feature, technique, encounter)
        except Exception:
            return self.fallback.render(beat, feature, technique, encounter)

    def _render_llm(self, beat: dict[str, Any], feature: Feature, technique: Technique, encounter: Encounter) -> str:
        import json
        import urllib.request

        attacker = encounter.fighters[0]
        defender = encounter.fighters[1]
        actor = attacker.name
        opponent = defender.name
        style = self.style or encounter.style
        facts = {
            "actor": actor,
            "actor_temperament": attacker.temperament,
            "opponent": opponent,
            "opponent_temperament": defender.temperament,
            "phase": beat["phase"],
            "outcome_band": str(beat["band"]).replace("_", " "),
            "technique": technique.name,
            "technique_feel": technique.narrative_tags,
            "engages": feature.label,
            "tests": feature.innate_test,
            "consequence": feature.consequence,
            "terrain": encounter.terrain.name,
            "terrain_feel": encounter.terrain.narrative_tags,
        }
        system = (
            f"You are a {style} combat-prose stylist. Render ONE exchange of a duel as 2-4 vivid sentences. "
            "Use ONLY the given facts. Do NOT invent outcomes, injuries, winners, deaths, or techniques. "
            "Let each fighter's temperament shape how they move, carry themselves, and read the moment — "
            "color voice and posture through it, but never let it override the fixed outcome. "
            "The result is fixed by 'outcome_band' — convey it through action and image, never with numbers "
            "or game words (no 'band', no 'qi cost', no stats). Physical specificity over interpretation. "
            "Balance action (what happened), feeling (how it registered), and being (who they are) across beats — "
            "not all three in every sentence. A beat can be pure motion. A beat can be stillness after impact. "
            "Not every exchange is climactic; a clash can settle into dust and repositioning and nothing else. "
            "Each fighter reads the same moment differently through their own nature — same terrain, different person. "
            "Output prose only: no headings, no lists, no preamble."
        )
        user = "Facts (authoritative — render, never change):\n" + json.dumps(facts, ensure_ascii=False, indent=2)
        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
            }
        ).encode("utf-8")
        req = urllib.request.Request(self.host + "/api/chat", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = str((data.get("message") or {}).get("content", "")).strip()
        if not text:
            raise ValueError("empty LLM response")
        return text
