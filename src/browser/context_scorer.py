"""
Context Scorer — Multi-Dimensional Reference Evaluation Engine
==============================================================

Maps every piece of information through a multi-dimensional scoring tensor
that evaluates along these axes:

DIMENSION 1: AUTHOR CONTEXT
  - author_era: historical period weight (ancient=deep, modern=fresh)
  - target_audience: who was this written FOR (academic, general, child, expert)

DIMENSION 2: INFORMATION STATE (what role does this info play?)
  - in_use: actively being applied right now
  - referenced: cited but not directly applied
  - inferred: deduced from context, not explicitly stated
  - not_used: available but dormant

DIMENSION 3: DEPTH SPECTRUM (how deep does this go?)
  - principles: foundational axioms (deepest)
  - facts: verified data points
  - thoughts: reasoned conclusions
  - emotions: affective content/tone
  - theories: explanatory frameworks
  - implications: downstream consequences

DIMENSION 4: SOURCE + CREDIBILITY
  - source_type: peer-reviewed, official, community, personal, AI-generated
  - independence: how many independent sources confirm this?
  - tangential_range: how far does this connect to other domains?

DIMENSION 5: MAGNETISM FIELD (attraction/repulsion in multi-field)
  - wants_toward: what does this information pull you TOWARD?
  - wants_away: what does it push you AWAY from?
  - field_stability: how stable is this magnetic configuration?
  - This creates a multi-magnetic stabilized zone where information
    finds its natural resting position based on competing forces.

DIMENSION 6: 5W COVERAGE
  - who, what, when, where, why: each scored 0.0-1.0
  - 5w_completeness: geometric mean of all 5

DIMENSION 7: CONTEXT (historical peripheral vision)
  - temporal_context: what was happening at the time?
  - cultural_context: what cultural frame does this sit in?
  - peripheral_facts: what adjacent information exists?

When mapped into the OctoTree, each dimension becomes a spiral arm axis.
Where arms intersect, a TERNARY REACTION occurs:
  - REINFORCE: two contexts agree → amplify signal
  - CONFLICT: two contexts disagree → flag for review
  - NOVEL: two contexts combine to produce new insight → high-value output

Biology source: Octopus RNA editing (60%+ brain transcripts recoded at runtime)
means our scoring adapts dynamically — same information scores differently
depending on the context it's evaluated in.

Usage:
    scorer = ContextScorer()
    ref = ContextReference(
        content="The octopus has 500 million neurons",
        url="https://en.wikipedia.org/wiki/Octopus",
        author_era="modern",
        target_audience="general",
    )
    score = scorer.score(ref)
    print(score.total, score.breakdown)

    # Score a batch through octotree
    results = await scorer.score_batch(references, spiral_mode=True)
"""

from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
SCORER_LOG = REPO_ROOT / "artifacts" / "agent_comm" / "context_scores.jsonl"


# ---------------------------------------------------------------------------
#  Enums
# ---------------------------------------------------------------------------

class InfoState(Enum):
    IN_USE = "in_use"
    REFERENCED = "referenced"
    INFERRED = "inferred"
    NOT_USED = "not_used"


class DepthLevel(Enum):
    PRINCIPLES = "principles"
    FACTS = "facts"
    THOUGHTS = "thoughts"
    EMOTIONS = "emotions"
    THEORIES = "theories"
    IMPLICATIONS = "implications"


class SourceType(Enum):
    PEER_REVIEWED = "peer_reviewed"
    OFFICIAL = "official"
    COMMUNITY = "community"
    PERSONAL = "personal"
    AI_GENERATED = "ai_generated"


class TernaryReaction(Enum):
    REINFORCE = "reinforce"
    CONFLICT = "conflict"
    NOVEL = "novel"


# ---------------------------------------------------------------------------
#  Phi weights (Sacred Tongue scaling)
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2  # 1.618...

# Depth weights — deeper = more foundational = higher phi power
DEPTH_WEIGHTS: Dict[DepthLevel, float] = {
    DepthLevel.PRINCIPLES: PHI ** 5,     # 11.09 — deepest
    DepthLevel.FACTS: PHI ** 4,          # 6.85
    DepthLevel.THEORIES: PHI ** 3,       # 4.24
    DepthLevel.THOUGHTS: PHI ** 2,       # 2.62
    DepthLevel.IMPLICATIONS: PHI ** 1,   # 1.62
    DepthLevel.EMOTIONS: PHI ** 0,       # 1.00 — shallowest (but still 1, not 0)
}

# Info state weights — in-use is most valuable
INFO_STATE_WEIGHTS: Dict[InfoState, float] = {
    InfoState.IN_USE: 1.0,
    InfoState.REFERENCED: 0.7,
    InfoState.INFERRED: 0.5,
    InfoState.NOT_USED: 0.1,
}

# Source credibility weights
SOURCE_WEIGHTS: Dict[SourceType, float] = {
    SourceType.PEER_REVIEWED: 1.0,
    SourceType.OFFICIAL: 0.85,
    SourceType.COMMUNITY: 0.6,
    SourceType.PERSONAL: 0.4,
    SourceType.AI_GENERATED: 0.5,
}

# Era scaling — not quality, just temporal distance weighting
ERA_SCALE = {
    "ancient": 0.3,     # >500 years — deep roots, lower immediacy
    "classical": 0.5,   # 100-500 years
    "modern": 0.8,      # 20-100 years
    "contemporary": 1.0, # <20 years — highest immediacy
}

AUDIENCE_SCALE = {
    "child": 0.4,
    "general": 0.6,
    "professional": 0.8,
    "expert": 1.0,
    "academic": 0.9,
}


# ---------------------------------------------------------------------------
#  Data structures
# ---------------------------------------------------------------------------

@dataclass
class MagnetismField:
    """Multi-magnetic field for attraction/repulsion scoring."""
    toward: List[str] = field(default_factory=list)    # what it pulls toward
    away: List[str] = field(default_factory=list)      # what it pushes from
    stability: float = 0.5  # 0.0 = chaotic, 1.0 = stable equilibrium

    def net_force(self) -> float:
        """Net magnetism: positive = attractive, negative = repulsive."""
        t = len(self.toward)
        a = len(self.away)
        if t + a == 0:
            return 0.0
        return ((t - a) / (t + a)) * self.stability

    def to_dict(self) -> Dict[str, Any]:
        return {
            "toward": self.toward,
            "away": self.away,
            "stability": self.stability,
            "net_force": round(self.net_force(), 4),
        }


@dataclass
class FiveW:
    """5W coverage: who, what, when, where, why — each 0.0 to 1.0."""
    who: float = 0.0
    what: float = 0.0
    when: float = 0.0
    where: float = 0.0
    why: float = 0.0

    def completeness(self) -> float:
        """Geometric mean — all 5 must be nonzero for high score."""
        vals = [max(v, 0.01) for v in [self.who, self.what, self.when, self.where, self.why]]
        product = 1.0
        for v in vals:
            product *= v
        return product ** (1.0 / 5.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "who": self.who, "what": self.what, "when": self.when,
            "where": self.where, "why": self.why,
            "completeness": round(self.completeness(), 4),
        }


@dataclass
class ContextReference:
    """A piece of information to be scored."""
    content: str
    url: str = ""
    author_era: str = "contemporary"
    target_audience: str = "general"
    info_state: InfoState = InfoState.REFERENCED
    depth_levels: List[DepthLevel] = field(default_factory=lambda: [DepthLevel.FACTS])
    source_type: SourceType = SourceType.COMMUNITY
    independent_sources: int = 1
    tangential_range: int = 0  # how many other domains does this connect to?
    magnetism: MagnetismField = field(default_factory=MagnetismField)
    five_w: FiveW = field(default_factory=FiveW)
    temporal_context: str = ""
    cultural_context: str = ""
    peripheral_facts: List[str] = field(default_factory=list)
    ref_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


@dataclass
class ContextScore:
    """Scored result with full breakdown."""
    ref_id: str
    total: float
    breakdown: Dict[str, float]
    ternary_reactions: List[Dict[str, Any]]
    spiral_position: Tuple[float, float, float, float]  # 4D position

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ref_id": self.ref_id,
            "total": round(self.total, 4),
            "breakdown": {k: round(v, 4) for k, v in self.breakdown.items()},
            "ternary_reactions": self.ternary_reactions,
            "spiral_position": tuple(round(x, 4) for x in self.spiral_position),
        }


# ---------------------------------------------------------------------------
#  Context Scorer
# ---------------------------------------------------------------------------

class ContextScorer:
    """Multi-dimensional context evaluation engine."""

    def __init__(self) -> None:
        self._scored: List[ContextScore] = []

    def score(self, ref: ContextReference) -> ContextScore:
        """Score a single reference across all dimensions."""
        b: Dict[str, float] = {}

        # D1: Author context
        era_w = ERA_SCALE.get(ref.author_era, 0.6)
        aud_w = AUDIENCE_SCALE.get(ref.target_audience, 0.6)
        b["author_context"] = (era_w + aud_w) / 2.0

        # D2: Information state
        b["info_state"] = INFO_STATE_WEIGHTS.get(ref.info_state, 0.3)

        # D3: Depth spectrum — average phi-weight of claimed depth levels
        if ref.depth_levels:
            depth_sum = sum(DEPTH_WEIGHTS.get(d, 1.0) for d in ref.depth_levels)
            # Normalize to 0-1 range (max possible is PRINCIPLES = 11.09)
            b["depth"] = min(depth_sum / (len(ref.depth_levels) * 11.09), 1.0)
        else:
            b["depth"] = 0.1

        # D4: Source + credibility
        src_w = SOURCE_WEIGHTS.get(ref.source_type, 0.4)
        # Independence bonus: log scale, caps at ~5 independent sources
        indep_bonus = min(math.log2(max(ref.independent_sources, 1) + 1) / 3.0, 1.0)
        # Tangential range bonus: more connections = more valuable
        tangent_bonus = min(ref.tangential_range / 10.0, 1.0)
        b["source_credibility"] = (src_w * 0.5) + (indep_bonus * 0.3) + (tangent_bonus * 0.2)

        # D5: Magnetism field
        b["magnetism"] = (ref.magnetism.net_force() + 1.0) / 2.0  # normalize -1..1 to 0..1

        # D6: 5W coverage
        b["five_w"] = ref.five_w.completeness()

        # D7: Context (peripheral vision)
        context_score = 0.0
        if ref.temporal_context:
            context_score += 0.33
        if ref.cultural_context:
            context_score += 0.33
        if ref.peripheral_facts:
            context_score += min(len(ref.peripheral_facts) / 5.0, 0.34)
        b["context_richness"] = context_score

        # --- Total: weighted combination ---
        # Weights reflect the user's priority ordering
        weights = {
            "depth": 0.22,              # principles matter most
            "source_credibility": 0.18, # trust the source
            "five_w": 0.16,             # completeness matters
            "context_richness": 0.14,   # peripheral vision
            "info_state": 0.12,         # is it being used?
            "magnetism": 0.10,          # attraction/repulsion field
            "author_context": 0.08,     # era and audience
        }
        total = sum(b[k] * weights[k] for k in weights)

        # --- 4D Spiral Position ---
        # Map the 7 dimensions into a 4D spiral arm coordinate
        # Using spherical-like embedding: (r, theta, phi_angle, psi)
        r = total  # radial distance = overall quality
        theta = math.atan2(b["depth"], b["source_credibility"])  # depth vs source plane
        phi_angle = math.atan2(b["magnetism"], b["five_w"])  # force vs completeness plane
        psi = b["context_richness"] * math.pi  # context as 4th dimension rotation
        spiral_pos = (r, theta, phi_angle, psi)

        # --- Ternary reactions (computed when scoring batch) ---
        result = ContextScore(
            ref_id=ref.ref_id,
            total=total,
            breakdown=b,
            ternary_reactions=[],
            spiral_position=spiral_pos,
        )
        self._scored.append(result)
        self._log(ref, result)
        return result

    def score_batch(self, refs: List[ContextReference]) -> List[ContextScore]:
        """Score a batch and compute ternary reactions between all pairs."""
        scores = [self.score(ref) for ref in refs]

        # Compute ternary reactions between all pairs
        for i, sa in enumerate(scores):
            for j, sb in enumerate(scores):
                if j <= i:
                    continue
                reaction = self._ternary_reaction(sa, sb)
                sa.ternary_reactions.append({
                    "with": sb.ref_id,
                    "reaction": reaction.value,
                    "detail": self._reaction_detail(sa, sb, reaction),
                })
                sb.ternary_reactions.append({
                    "with": sa.ref_id,
                    "reaction": reaction.value,
                    "detail": self._reaction_detail(sb, sa, reaction),
                })
        return scores

    def _ternary_reaction(self, a: ContextScore, b: ContextScore) -> TernaryReaction:
        """Determine ternary reaction when two spiral arms intersect.

        Based on 4D distance between spiral positions:
        - Close + similar direction → REINFORCE
        - Close + opposite direction → CONFLICT
        - Far apart → NOVEL (unexpected intersection)
        """
        # 4D Euclidean distance
        dist = math.sqrt(sum((x - y) ** 2 for x, y in zip(a.spiral_position, b.spiral_position)))

        # Cosine similarity of breakdown vectors
        a_vec = list(a.breakdown.values())
        b_vec = list(b.breakdown.values())
        dot = sum(x * y for x, y in zip(a_vec, b_vec))
        mag_a = math.sqrt(sum(x ** 2 for x in a_vec))
        mag_b = math.sqrt(sum(x ** 2 for x in b_vec))
        cosine = dot / (mag_a * mag_b) if (mag_a * mag_b) > 0 else 0.0

        if dist < 0.5 and cosine > 0.8:
            return TernaryReaction.REINFORCE
        elif dist < 0.5 and cosine < 0.3:
            return TernaryReaction.CONFLICT
        else:
            return TernaryReaction.NOVEL

    def _reaction_detail(self, a: ContextScore, b: ContextScore, reaction: TernaryReaction) -> str:
        if reaction == TernaryReaction.REINFORCE:
            return f"Contexts align (scores {a.total:.2f} + {b.total:.2f}): amplify signal"
        elif reaction == TernaryReaction.CONFLICT:
            return f"Contexts disagree (scores {a.total:.2f} vs {b.total:.2f}): flag for review"
        else:
            return f"Novel intersection (scores {a.total:.2f} x {b.total:.2f}): potential new insight"

    def get_scored(self) -> List[ContextScore]:
        return list(self._scored)

    def summary(self) -> Dict[str, Any]:
        if not self._scored:
            return {"count": 0}
        totals = [s.total for s in self._scored]
        reactions = {}
        for s in self._scored:
            for r in s.ternary_reactions:
                reactions[r["reaction"]] = reactions.get(r["reaction"], 0) + 1
        return {
            "count": len(self._scored),
            "avg_score": round(sum(totals) / len(totals), 4),
            "min_score": round(min(totals), 4),
            "max_score": round(max(totals), 4),
            "ternary_reactions": reactions,
        }

    def _log(self, ref: ContextReference, score: ContextScore) -> None:
        SCORER_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ref_id": ref.ref_id,
            "url": ref.url,
            "content_preview": ref.content[:100],
            "total_score": round(score.total, 4),
            "spiral_position": [round(x, 4) for x in score.spiral_position],
            "breakdown": {k: round(v, 4) for k, v in score.breakdown.items()},
        }
        with SCORER_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=True) + "\n")


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Score contextual references")
    parser.add_argument("--demo", action="store_true", help="Run demo scoring")
    args = parser.parse_args()

    if args.demo:
        scorer = ContextScorer()
        refs = [
            ContextReference(
                content="Octopus has 500M neurons, 70% in arms",
                url="https://www.nature.com/articles/nature14668",
                author_era="contemporary",
                target_audience="academic",
                info_state=InfoState.IN_USE,
                depth_levels=[DepthLevel.FACTS, DepthLevel.PRINCIPLES],
                source_type=SourceType.PEER_REVIEWED,
                independent_sources=5,
                tangential_range=4,
                magnetism=MagnetismField(toward=["distributed_AI", "bio_inspired"], away=["centralized"], stability=0.9),
                five_w=FiveW(who=0.9, what=1.0, when=0.8, where=0.7, why=0.9),
                temporal_context="2015 Nature genome paper",
                cultural_context="cephalopod neuroscience renaissance",
                peripheral_facts=["RNA editing", "protocadherins", "chromatophores"],
            ),
            ContextReference(
                content="Sacred geometry uses phi ratio for natural patterns",
                url="https://en.wikipedia.org/wiki/Sacred_geometry",
                author_era="ancient",
                target_audience="general",
                info_state=InfoState.REFERENCED,
                depth_levels=[DepthLevel.PRINCIPLES, DepthLevel.THEORIES],
                source_type=SourceType.COMMUNITY,
                independent_sources=3,
                tangential_range=6,
                magnetism=MagnetismField(toward=["architecture", "nature", "math"], away=[], stability=0.95),
                five_w=FiveW(who=0.3, what=0.9, when=0.4, where=0.5, why=0.8),
                temporal_context="Pythagorean through modern",
                cultural_context="cross-cultural mathematical tradition",
                peripheral_facts=["golden ratio", "Fibonacci", "icosahedron"],
            ),
            ContextReference(
                content="SCBE 14-layer pipeline uses hyperbolic cost scaling",
                url="https://github.com/issdandavis/SCBE-AETHERMOORE",
                author_era="contemporary",
                target_audience="expert",
                info_state=InfoState.IN_USE,
                depth_levels=[DepthLevel.PRINCIPLES, DepthLevel.THEORIES, DepthLevel.IMPLICATIONS],
                source_type=SourceType.PERSONAL,
                independent_sources=1,
                tangential_range=3,
                magnetism=MagnetismField(toward=["AI_safety", "governance"], away=["adversarial"], stability=0.85),
                five_w=FiveW(who=0.8, what=1.0, when=0.9, where=0.6, why=1.0),
                temporal_context="2026 patent pending",
                cultural_context="AI safety research boom",
                peripheral_facts=["Poincare ball", "post-quantum crypto", "Sacred Tongues"],
            ),
        ]

        scores = scorer.score_batch(refs)
        for s in scores:
            print(json.dumps(s.to_dict(), indent=2))
        print("\n--- Summary ---")
        print(json.dumps(scorer.summary(), indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
