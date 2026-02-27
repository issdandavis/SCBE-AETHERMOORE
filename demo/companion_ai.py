#!/usr/bin/env python3
"""
Companion AI Decision Engine
=============================
Simulates party members making independent choices during Aethermoor gameplay.
Each companion has a 6-dimensional personality vector aligned with the Sacred
Tongues, influencing how they evaluate scene choices.

Creates DPO (Direct Preference Optimization) training data by comparing
player choices with AI companion recommendations.

Characters from Issac Davis's lore (Everweave, Notion, SCBE):
  - Polly       : Raven familiar, cautious wisdom, KO affinity
  - Clay        : Sand golem, loyal protector, RU affinity
  - Eldrin      : Cartographer, curious explorer, AV affinity
  - Aria        : Warrior-scholar, strategic balance, UM affinity
  - Zara        : Dragon-blooded engineer, bold innovator, DR affinity
  - Kael        : Shadow drifter, mysterious loner, UM affinity

Pure Python, no external dependencies.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# SCBE layers referenced by companions during evaluation
# ---------------------------------------------------------------------------
LAYER_NAMES: Dict[int, str] = {
    1: "Ingress",
    2: "Identity",
    3: "Policy",
    4: "Schema",
    5: "Transform",
    6: "Routing",
    7: "Orchestration",
    8: "Execution",
    9: "Observation",
    10: "Feedback",
    11: "Audit",
    12: "Consensus",
    13: "Evolution",
    14: "Governance",
}

# Sacred Tongue codes
TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")

TONGUE_FULL_NAMES: Dict[str, str] = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}


# ---------------------------------------------------------------------------
# Personality Vector
# ---------------------------------------------------------------------------
@dataclass
class PersonalityVector:
    """6-dimensional personality aligned with the Six Sacred Tongues.

    Each dimension ranges from 0.0 (minimal affinity) to 1.0 (maximal).
    """

    authority: float = 0.5   # KO -- preference for control / hierarchy
    mobility: float = 0.5    # AV -- preference for exploration / movement
    caution: float = 0.5     # RU -- preference for rules / constraints
    logic: float = 0.5       # CA -- preference for computation / analysis
    secrecy: float = 0.5     # UM -- preference for stealth / secrets
    tradition: float = 0.5   # DR -- preference for established patterns

    def tongue_scores(self) -> Dict[str, float]:
        """Return a dict mapping tongue code to personality weight."""
        return {
            "KO": self.authority,
            "AV": self.mobility,
            "RU": self.caution,
            "CA": self.logic,
            "UM": self.secrecy,
            "DR": self.tradition,
        }

    def dominant_tongue(self) -> str:
        """Return the tongue code with the highest score."""
        scores = self.tongue_scores()
        return max(scores, key=scores.get)  # type: ignore[arg-type]

    def magnitude(self) -> float:
        """Euclidean magnitude of the personality vector."""
        vals = list(self.tongue_scores().values())
        return math.sqrt(sum(v * v for v in vals))

    def dot(self, other: Dict[str, float]) -> float:
        """Dot product against an arbitrary tongue-score dict."""
        mine = self.tongue_scores()
        return sum(mine.get(k, 0.0) * other.get(k, 0.0) for k in TONGUES)


# ---------------------------------------------------------------------------
# Companion Thought
# ---------------------------------------------------------------------------
@dataclass
class CompanionThought:
    """A companion's evaluation of a single scene choice."""

    companion_name: str
    choice_id: str
    preference_score: float          # 0.0 to 1.0
    reasoning: str                   # natural-language explanation
    layers_they_would_invoke: List[int]  # which SCBE layers they'd use
    tongue_alignment: str            # which tongue this choice aligns with
    agree_with_player: Optional[bool] = None  # set after player decides


# ---------------------------------------------------------------------------
# Choice descriptor (lightweight, no engine dependency)
# ---------------------------------------------------------------------------
@dataclass
class Choice:
    """A single selectable option inside a scene."""

    choice_id: str
    label: str
    tongue: str = "CA"         # primary tongue alignment
    risk: float = 0.5          # 0.0 safe .. 1.0 reckless
    layers: List[int] = field(default_factory=lambda: [7])


# ---------------------------------------------------------------------------
# Companion profiles
# ---------------------------------------------------------------------------
_PROFILES: Dict[str, Dict[str, Any]] = {
    "Polly": {
        "personality": PersonalityVector(
            authority=0.8, mobility=0.3, caution=0.7,
            logic=0.5, secrecy=0.4, tradition=0.9,
        ),
        "affinity": "KO",
        "voice_template": (
            "We should follow the Protocol. The archives say: "
            "'{reason}'. Wisdom favours the measured step."
        ),
        "short_style": "ancient-proverb",
    },
    "Clay": {
        "personality": PersonalityVector(
            authority=0.4, mobility=0.3, caution=0.9,
            logic=0.3, secrecy=0.2, tradition=0.7,
        ),
        "affinity": "RU",
        "voice_template": (
            "Whatever keeps everyone safe. {reason}. "
            "Clay stands between you and harm."
        ),
        "short_style": "short-protective",
    },
    "Eldrin": {
        "personality": PersonalityVector(
            authority=0.2, mobility=0.9, caution=0.3,
            logic=0.7, secrecy=0.4, tradition=0.3,
        ),
        "affinity": "AV",
        "voice_template": (
            "Let's explore this further. My charts indicate "
            "'{reason}'. The ley lines converge ahead."
        ),
        "short_style": "cartographer",
    },
    "Aria": {
        "personality": PersonalityVector(
            authority=0.6, mobility=0.5, caution=0.5,
            logic=0.8, secrecy=0.7, tradition=0.4,
        ),
        "affinity": "UM",
        "voice_template": (
            "Consider the boundary implications. "
            "By my theorem: {reason}. The equation balances."
        ),
        "short_style": "math-warrior",
    },
    "Zara": {
        "personality": PersonalityVector(
            authority=0.4, mobility=0.6, caution=0.3,
            logic=0.9, secrecy=0.4, tradition=0.8,
        ),
        "affinity": "DR",
        "voice_template": (
            "I can build something for this. {reason}. "
            "The schema compiles clean."
        ),
        "short_style": "engineer",
    },
    "Kael": {
        "personality": PersonalityVector(
            authority=0.2, mobility=0.8, caution=0.3,
            logic=0.5, secrecy=0.9, tradition=0.3,
        ),
        "affinity": "UM",
        "voice_template": (
            "There's another way. {reason}. "
            "Shadows remember what the light forgets."
        ),
        "short_style": "shadow-time",
    },
}


# ---------------------------------------------------------------------------
# Deterministic hash helper
# ---------------------------------------------------------------------------
def _det_score(seed: str) -> float:
    """Return a deterministic float in [0, 1) from an arbitrary seed string.

    Uses SHA-256 so results are reproducible across runs.
    """
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


# ---------------------------------------------------------------------------
# Reasoning generators (per voice style)
# ---------------------------------------------------------------------------
_REASON_BANK: Dict[str, Dict[str, str]] = {
    "safe": {
        "ancient-proverb": "The old wards held for a reason",
        "short-protective": "Safe is good",
        "cartographer": "Charted territory is reliable",
        "math-warrior": "The defensive integral converges",
        "engineer": "Tested paths have fewer bugs",
        "shadow-time": "Even shadows rest in familiar dark",
    },
    "risky": {
        "ancient-proverb": "Fortune once favoured the first to fly",
        "short-protective": "Sometimes you gotta move fast",
        "cartographer": "Uncharted routes yield the best discoveries",
        "math-warrior": "High-variance distributions have fatter tails",
        "engineer": "Prototype fast, iterate faster",
        "shadow-time": "Time folds for those who dare step sideways",
    },
    "balanced": {
        "ancient-proverb": "Measure twice, cut once -- but do cut",
        "short-protective": "Careful, but okay",
        "cartographer": "A surveyed detour is no detour at all",
        "math-warrior": "Optimise the objective, not the constraint",
        "engineer": "Incremental deployment reduces blast radius",
        "shadow-time": "Walk the edge between timelines",
    },
}


def _pick_reason(style: str, risk: float) -> str:
    """Select a reasoning snippet based on voice style and choice risk."""
    if risk < 0.35:
        category = "safe"
    elif risk > 0.65:
        category = "risky"
    else:
        category = "balanced"
    return _REASON_BANK.get(category, _REASON_BANK["balanced"]).get(
        style, "The path is clear"
    )


# ---------------------------------------------------------------------------
# Layer heuristic
# ---------------------------------------------------------------------------
def _infer_layers(tongue: str, risk: float) -> List[int]:
    """Heuristically pick SCBE layers a companion would think about."""
    base: Dict[str, List[int]] = {
        "KO": [1, 2, 14],
        "AV": [5, 6],
        "RU": [3, 4, 11],
        "CA": [7, 8],
        "UM": [2, 9, 12],
        "DR": [4, 13],
    }
    layers = list(base.get(tongue, [7]))
    if risk > 0.6:
        layers.append(10)  # Feedback -- risky choices need monitoring
    if risk > 0.8:
        layers.append(12)  # Consensus -- very risky choices need BFT
    return sorted(set(layers))


# ---------------------------------------------------------------------------
# CompanionAI
# ---------------------------------------------------------------------------
class CompanionAI:
    """AI companion decision engine for Aethermoor party members.

    Each companion evaluates every available choice through the lens of their
    personality vector and tongue affinity.  Scoring is fully deterministic
    (hash-based, no randomness) so results are reproducible.
    """

    def __init__(self) -> None:
        self.profiles: Dict[str, Dict[str, Any]] = dict(_PROFILES)
        self._history: List[Dict[str, Any]] = []

    # -- core evaluation ---------------------------------------------------

    def _score_choice(
        self,
        companion_name: str,
        scene_id: str,
        choice: Choice,
    ) -> float:
        """Score a single choice for a single companion.

        The score is composed of three signals:
        1. Tongue alignment -- how well the choice's tongue matches personality.
        2. Risk fit -- adventurous companions score risky choices higher.
        3. Deterministic hash jitter -- tiny per-scene/choice variation to
           break ties without introducing randomness.

        Returns a float clamped to [0, 1].
        """
        profile = self.profiles[companion_name]
        pv: PersonalityVector = profile["personality"]

        # 1. Tongue alignment (0..1)
        tongue_scores = pv.tongue_scores()
        alignment = tongue_scores.get(choice.tongue, 0.5)

        # 2. Risk fit
        # Adventurous = high mobility + low caution
        adventure_factor = (pv.mobility + (1.0 - pv.caution)) / 2.0
        # If companion is adventurous, risky choices score higher
        risk_fit = 1.0 - abs(adventure_factor - choice.risk)

        # 3. Deterministic jitter (keeps things stable yet unique per scene)
        jitter_seed = f"{companion_name}:{scene_id}:{choice.choice_id}"
        jitter = _det_score(jitter_seed) * 0.1  # max 0.1 swing

        raw = 0.45 * alignment + 0.40 * risk_fit + 0.15 * jitter
        return max(0.0, min(1.0, raw))

    # -- public API --------------------------------------------------------

    def evaluate_choices(
        self,
        scene_id: str,
        choices: List[Choice],
        party: List[str],
    ) -> Dict[str, List[CompanionThought]]:
        """For each companion in *party*, evaluate all choices.

        Returns ``{companion_name: [CompanionThought, ...]}``
        """
        result: Dict[str, List[CompanionThought]] = {}
        for name in party:
            if name not in self.profiles:
                continue
            profile = self.profiles[name]
            style = profile["short_style"]
            template = profile["voice_template"]
            thoughts: List[CompanionThought] = []
            for ch in choices:
                score = self._score_choice(name, scene_id, ch)
                reason_snippet = _pick_reason(style, ch.risk)
                reasoning = template.format(reason=reason_snippet)
                layers = _infer_layers(ch.tongue, ch.risk)
                thoughts.append(
                    CompanionThought(
                        companion_name=name,
                        choice_id=ch.choice_id,
                        preference_score=round(score, 4),
                        reasoning=reasoning,
                        layers_they_would_invoke=layers,
                        tongue_alignment=ch.tongue,
                    )
                )
            result[name] = thoughts
        return result

    def get_companion_recommendation(
        self,
        companion_name: str,
        scene_id: str,
        choices: List[Choice],
    ) -> str:
        """Return the choice_id the companion would recommend."""
        if companion_name not in self.profiles:
            return choices[0].choice_id if choices else ""
        best_id = choices[0].choice_id
        best_score = -1.0
        for ch in choices:
            s = self._score_choice(companion_name, scene_id, ch)
            if s > best_score:
                best_score = s
                best_id = ch.choice_id
        return best_id

    def generate_dpo_pair(
        self,
        scene_id: str,
        player_choice: str,
        companion_name: str,
        companion_preferred: str,
        scene_text: str,
    ) -> Dict[str, Any]:
        """Generate a DPO training pair comparing player vs companion.

        ``chosen`` = player's actual pick (ground-truth preference).
        ``rejected`` = companion's pick when it differs.
        """
        pair: Dict[str, Any] = {
            "prompt": (
                f"You are in the world of Aethermoor. Scene: {scene_id}.\n\n"
                f"{scene_text}\n\nWhat do you choose?"
            ),
            "chosen": player_choice,
            "rejected": companion_preferred,
            "metadata": {
                "source": "companion_ai_dpo",
                "scene_id": scene_id,
                "companion": companion_name,
                "companion_affinity": self.profiles.get(companion_name, {}).get(
                    "affinity", "CA"
                ),
            },
        }
        self._history.append(pair)
        return pair

    def get_party_consensus(
        self,
        scene_id: str,
        choices: List[Choice],
        party: List[str],
    ) -> Tuple[str, float]:
        """BFT-style consensus: which choice does the majority prefer?

        Returns ``(choice_id, agreement_ratio)`` where agreement_ratio is
        the fraction of companions that picked the winning choice.
        """
        if not choices or not party:
            return ("", 0.0)

        votes: Dict[str, int] = {}
        active = 0
        for name in party:
            rec = self.get_companion_recommendation(name, scene_id, choices)
            votes[rec] = votes.get(rec, 0) + 1
            active += 1

        if active == 0:
            return (choices[0].choice_id, 0.0)

        winner = max(votes, key=votes.get)  # type: ignore[arg-type]
        ratio = votes[winner] / active
        return (winner, round(ratio, 4))

    def render_thought_bubble(self, thought: CompanionThought) -> str:
        """Return a formatted text block showing the companion's thought."""
        layers_str = ", ".join(
            f"L{n} ({LAYER_NAMES.get(n, '?')})"
            for n in thought.layers_they_would_invoke
        )
        tongue_name = TONGUE_FULL_NAMES.get(thought.tongue_alignment, thought.tongue_alignment)
        agree_mark = ""
        if thought.agree_with_player is True:
            agree_mark = " [AGREES with player]"
        elif thought.agree_with_player is False:
            agree_mark = " [DISAGREES with player]"

        return (
            f"--- {thought.companion_name}'s Thought ---\n"
            f"  Choice : {thought.choice_id}\n"
            f"  Score  : {thought.preference_score:.2f}\n"
            f"  Tongue : {tongue_name}{agree_mark}\n"
            f"  Layers : {layers_str}\n"
            f'  "{thought.reasoning}"\n'
            f"---"
        )

    @property
    def dpo_history(self) -> List[Dict[str, Any]]:
        """All DPO pairs generated so far."""
        return list(self._history)

    def export_dpo_jsonl(self) -> str:
        """Serialize accumulated DPO pairs as JSONL text."""
        lines = [json.dumps(p, ensure_ascii=False) for p in self._history]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def selftest() -> None:
    """Run self-test exercising every public method."""
    print(f"\n{'=' * 60}")
    print("  Companion AI Decision Engine -- Self-Test")
    print(f"{'=' * 60}\n")

    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name}  {detail}")

    ai = CompanionAI()

    # --- 1. Profile loading ---
    check("All 6 companions loaded", len(ai.profiles) == 6)
    for name in ("Polly", "Clay", "Eldrin", "Aria", "Zara", "Kael"):
        check(f"  Profile exists: {name}", name in ai.profiles)

    # --- 2. Personality vectors ---
    pv_polly = ai.profiles["Polly"]["personality"]
    check("Polly high authority", pv_polly.authority == 0.8)
    check("Polly high tradition", pv_polly.tradition == 0.9)
    check("Polly low mobility", pv_polly.mobility == 0.3)
    check("Polly dominant tongue is KO or DR",
          pv_polly.dominant_tongue() in ("KO", "DR"))
    check("Magnitude > 0", pv_polly.magnitude() > 0.0)

    pv_eldrin = ai.profiles["Eldrin"]["personality"]
    check("Eldrin dominant tongue is AV", pv_eldrin.dominant_tongue() == "AV")

    # --- 3. Deterministic scoring ---
    s1 = _det_score("test_seed_alpha")
    s2 = _det_score("test_seed_alpha")
    s3 = _det_score("test_seed_beta")
    check("det_score reproducible", s1 == s2)
    check("det_score varies with seed", s1 != s3)

    # --- 4. Choice evaluation ---
    choices = [
        Choice(choice_id="investigate", label="Trace the anomaly deeper",
               tongue="CA", risk=0.6, layers=[7, 8]),
        Choice(choice_id="escalate", label="Document and escalate",
               tongue="RU", risk=0.2, layers=[3, 11]),
        Choice(choice_id="ignore", label="Ignore it",
               tongue="AV", risk=0.1, layers=[6]),
    ]
    party = ["Polly", "Clay", "Eldrin", "Aria", "Zara", "Kael"]
    thoughts = ai.evaluate_choices("earth_work", choices, party)

    check("Thoughts for all 6", len(thoughts) == 6)
    for name, thought_list in thoughts.items():
        check(f"  {name} evaluated 3 choices", len(thought_list) == 3)
        for t in thought_list:
            check(f"    {name}/{t.choice_id} score in [0,1]",
                  0.0 <= t.preference_score <= 1.0,
                  f"score={t.preference_score}")
            check(f"    {name}/{t.choice_id} has reasoning",
                  len(t.reasoning) > 10)
            check(f"    {name}/{t.choice_id} has layers",
                  len(t.layers_they_would_invoke) > 0)

    # --- 5. Recommendation ---
    rec_polly = ai.get_companion_recommendation("Polly", "earth_work", choices)
    check("Polly recommends a valid choice", rec_polly in ("investigate", "escalate", "ignore"))

    rec_eldrin = ai.get_companion_recommendation("Eldrin", "earth_work", choices)
    check("Eldrin recommends a valid choice", rec_eldrin in ("investigate", "escalate", "ignore"))

    # Polly (cautious) should lean toward safe; Eldrin (adventurous) toward risky
    polly_scores = {ch.choice_id: ai._score_choice("Polly", "earth_work", ch) for ch in choices}
    eldrin_scores = {ch.choice_id: ai._score_choice("Eldrin", "earth_work", ch) for ch in choices}
    check("Polly scores escalate (safe) higher than ignore is plausible",
          polly_scores["escalate"] > 0.0)
    check("Eldrin scores investigate (risky) non-trivially",
          eldrin_scores["investigate"] > 0.0)

    # --- 6. DPO pair generation ---
    dpo = ai.generate_dpo_pair(
        scene_id="earth_work",
        player_choice="investigate",
        companion_name="Clay",
        companion_preferred="escalate",
        scene_text="You're debugging an authentication anomaly in the routing logs.",
    )
    check("DPO pair has prompt", "Aethermoor" in dpo["prompt"])
    check("DPO pair chosen = player", dpo["chosen"] == "investigate")
    check("DPO pair rejected = companion", dpo["rejected"] == "escalate")
    check("DPO metadata has companion", dpo["metadata"]["companion"] == "Clay")
    check("DPO metadata has affinity", dpo["metadata"]["companion_affinity"] == "RU")

    # --- 7. Party consensus ---
    winner, ratio = ai.get_party_consensus("earth_work", choices, party)
    check("Consensus returns a valid choice", winner in ("investigate", "escalate", "ignore"))
    check("Agreement ratio in [0,1]", 0.0 <= ratio <= 1.0)
    check("Agreement ratio is a sensible fraction",
          ratio in (round(i / 6, 4) for i in range(1, 7)))

    # --- 8. Render thought bubble ---
    sample_thought = thoughts["Aria"][0]
    bubble = ai.render_thought_bubble(sample_thought)
    check("Bubble contains companion name", "Aria" in bubble)
    check("Bubble contains score", "Score" in bubble)
    check("Bubble contains layers", "L" in bubble)
    check("Bubble contains tongue name", any(t in bubble for t in TONGUE_FULL_NAMES.values()))

    # Agree/disagree annotation
    sample_thought.agree_with_player = False
    bubble2 = ai.render_thought_bubble(sample_thought)
    check("Bubble shows DISAGREES", "DISAGREES" in bubble2)
    sample_thought.agree_with_player = True
    bubble3 = ai.render_thought_bubble(sample_thought)
    check("Bubble shows AGREES", "AGREES" in bubble3)

    # --- 9. DPO export ---
    jsonl = ai.export_dpo_jsonl()
    check("JSONL export non-empty", len(jsonl) > 20)
    parsed = json.loads(jsonl.split("\n")[0])
    check("JSONL first line is valid JSON", "prompt" in parsed)

    # --- 10. History accumulation ---
    ai.generate_dpo_pair("s2", "a", "Polly", "b", "text")
    check("History accumulates", len(ai.dpo_history) == 2)

    # --- 11. Layer inference ---
    layers_ko = _infer_layers("KO", 0.3)
    check("KO safe layers include L1", 1 in layers_ko)
    layers_risky = _infer_layers("CA", 0.9)
    check("High risk adds L10 and L12", 10 in layers_risky and 12 in layers_risky)

    # --- 12. Reproducibility ---
    thoughts_again = ai.evaluate_choices("earth_work", choices, party)
    for name in party:
        for t1, t2 in zip(thoughts[name], thoughts_again[name]):
            check(f"  Reproducible: {name}/{t1.choice_id}",
                  t1.preference_score == t2.preference_score)

    # --- Summary ---
    print(f"\n{'=' * 60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}\n")
    if failed == 0:
        print("  All companion AI systems operational.\n")
    else:
        print(f"  WARNING: {failed} check(s) failed.\n")


if __name__ == "__main__":
    selftest()
