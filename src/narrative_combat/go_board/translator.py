"""Render verified board events as prose. The board decides truth; this only translates it.

`GoTemplateTranslator` is the deterministic default: a literal board-event -> beat-frame dispatch
table, golden-stable, no network. `GoLLMTranslator` is opt-in and mirrors the maze LLMTranslator
exactly (facts dict, party temperament wired in, fallback to the template on any failure). Neither
may invent an outcome the board did not produce.
"""

from __future__ import annotations

from typing import Any

from .models import GoEncounter

# board_event -> deterministic narrative frame (the literal dispatch table the spec calls for)
_FRAMES: dict[str, str] = {
    "presence": "{actor} sets a stone at {point}, taking presence in the {terrain}.",
    "contact": "{actor} presses forward to {point}, and the lines of {actor} and {opponent} finally touch.",
    "liberty_pressure": "{actor} plays {point}; {opponent}'s pressed group now breathes through only "
    "{liberties} ways.",
    "atari": "{actor} seizes {point} — {opponent}'s group is down to a single breath, one move from "
    "being swept away.",
    "qi_claimed": "{actor} plants beside the qi-font at {qi_node}, drawing +{qi_gained} into reserve "
    "({qi_total} held).",
    "study_revealed": "{actor} breaks to read the old records before striking: {study}.",
    "probe": "{actor} feints toward {point}, testing the killing line without committing — "
    "{opponent} would lose {would_capture} there.",
    "treaty_locked": "{actor} and {opponent} cut a treaty across {zone}; inside that ground no stone " "may be taken.",
    "capture": "{actor} takes {point} and severs the last breath; {opponent}'s group of {captured} "
    "stone(s) is swept from the board.",
    "_default": "{actor} acts at {point}.",
}


def _fmt_point(point: Any) -> str:
    if point is None:
        return "an unmarked point"
    r, c = point
    return f"({r}, {c})"


def _context(event: dict[str, Any], encounter: GoEncounter) -> dict[str, Any]:
    color = event["party"]
    actor = encounter.parties[color].name
    opponent = next((p.name for p in encounter.parties if p.color != color), "the opponent")
    mech = event.get("mechanical", {})
    study_results = mech.get("study", ())
    captured = mech.get("captured", [])
    return {
        "actor": actor,
        "opponent": opponent,
        "terrain": encounter.terrain_name,
        "point": _fmt_point(mech.get("point")),
        "liberties": mech.get("target_liberties", ""),
        "qi_node": _fmt_point(mech.get("qi_node")),
        "qi_gained": mech.get("qi_gained", ""),
        "qi_total": mech.get("qi_total", ""),
        "zone": mech.get("zone", "the contested ground"),
        "captured": len(captured) if isinstance(captured, (list, tuple)) else captured,
        "would_capture": len(mech.get("would_capture", [])),
        "study": "; ".join(study_results) if study_results else "the old masters left only silence",
    }


class GoTemplateTranslator:
    """Deterministic prose from the dispatch table. The default renderer: no model, no network."""

    def render(self, event: dict[str, Any], encounter: GoEncounter) -> str:
        frame = _FRAMES.get(event["board_event"], _FRAMES["_default"])
        return frame.format(**_context(event, encounter))


class GoLLMTranslator:
    """Opt-in renderer: turns one verified board event into cultivation-combat prose.

    The board owns truth (board_event + mechanical). This renders that fixed event as a martial
    exchange — stones are fighters and positions, a capture is a defeat — coloring voice by each
    party's temperament, never inventing an outcome. Any failure falls back to the template.
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
        self.fallback = fallback if fallback is not None else GoTemplateTranslator()

    def render(self, event: dict[str, Any], encounter: GoEncounter) -> str:
        try:
            return self._render_llm(event, encounter)
        except Exception:
            return self.fallback.render(event, encounter)

    def _render_llm(self, event: dict[str, Any], encounter: GoEncounter) -> str:
        import json
        import urllib.request

        color = event["party"]
        actor = encounter.parties[color]
        opponent = next((p for p in encounter.parties if p.color != color), actor)
        style = self.style or encounter.style
        facts = {
            "actor": actor.name,
            "actor_temperament": actor.temperament,
            "opponent": opponent.name,
            "opponent_temperament": opponent.temperament,
            "phase": event["phase"],
            "board_event": event["board_event"],
            "mechanical_truth": event.get("mechanical", {}),
            "terrain": encounter.terrain_name,
            "terrain_feel": encounter.terrain_tags,
        }
        system = (
            f"You are a {style} combat-prose stylist. The fight is tracked on a board; render this one "
            "exchange as a martial duel, NOT as a board game: stones are fighters and positions, a "
            "'capture' is a defeat or a position overrun, 'liberties' are escape routes, 'qi' is power "
            "drawn. Render 2-4 vivid sentences. Use ONLY the given facts; the 'board_event' and "
            "'mechanical_truth' are FIXED — convey them through action and image, never invent outcomes, "
            "injuries, winners, or deaths beyond them, and never use board jargon ('stone', 'liberty', "
            "'atari', 'point'). Let each party's temperament shape voice and posture. Output prose only."
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
