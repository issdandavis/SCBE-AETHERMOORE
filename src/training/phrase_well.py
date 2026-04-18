"""
phrase_well.py

Semantic phrase wells — the Obsidian vault insight.

CONCEPT:
  Instead of annotating every token, find the HUB phrases: surface tokens
  that appear in 3+ structurally distinct contexts simultaneously.

  Like Obsidian vault backlinks: a note (phrase) that links to many other
  notes (contexts) becomes a semantic gravity well. The model learns the
  HUBS, not every word in every note.

  "return" is:
    - Motif A anchor (define-return completion)
    - Motif B guard exit (defensive gate)
    - Full cadence trigger (tension resolution)
    - Refactorer terminus (transform-chain flow end)

  Training on the HUB teaches the model that "return" has multi-angular
  meaning — the well is deepest where one surface form concentrates the
  most divergent structural roles.

WELL DEPTH:
  depth = len(distinct_contexts) * angular_spread
  angular_spread = 1 - mean_cosine_similarity(context_vectors)
  (A deep well has many contexts that are far apart in structural space.)

TRAINING RECORD FORMAT:
  {
    "text": "[PHRASE WELL: 'return']\\n"
            "CONTEXT A — Voice: IMPLEMENTER, Motif: A, Cadence: FULL\\n"
            "  code: def compute(x): ... return result\\n"
            "  affect: SATISFACTION | trit: +1 | tier: ALLOW\\n"
            "\\n"
            "CONTEXT B — Voice: VALIDATOR, Motif: B, Cadence: HALF\\n"
            "  code: if not valid: return None\\n"
            "  affect: URGENCY | trit: -1 | tier: QUARANTINE\\n"
            "\\n"
            "SYNTHESIS: 'return' = completion [A] | gate [B] | terminus [D]\\n"
            "Well depth: 3 | Angular spread: 0.87\\n",
    "phrase": "return",
    "well_depth": 3,
    "angular_spread": 0.87,
    "stage": 6,
  }

The synthesis line is the key teaching moment: the model learns that ONE
surface form maps to MULTIPLE structural roles — and the distance between
those roles is the well depth signal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Optional, Tuple
import math


# =============================================================================
# CONTEXT VECTOR: 10D structural fingerprint for a phrase occurrence
# =============================================================================

VOICE_IDX   = {"PLANNER": 0, "IMPLEMENTER": 1, "VALIDATOR": 2, "REFACTORER": 3}
MOTIF_IDX   = {"motif_A": 0, "motif_B": 1, "motif_C": 2, "motif_D": 3,
                "motif_E": 4, "motif_F": 5, "motif_G": 6, None: -1}
CADENCE_IDX = {"full": 0, "half": 1, "deceptive": 2, "interrupted": 3,
                "plagal": 4, None: -1}
AFFECT_IDX  = {
    "INITIATION": 0, "ANTICIPATION": 1, "RECOGNITION": 2, "ENGAGEMENT": 3,
    "URGENCY": 4, "ALARM": 5, "RELIEF": 6, "SATISFACTION": 7,
}
TRIT_IDX    = {-1: 0, 0: 1, 1: 2}

# Conlang bridge: temporal aspect (when / how far along)
# Inherited from Sacred Tongue grammatical roots:
#   INCP  — inception, just beginning        (Kor'aelin aspect marker)
#   PROG  — progressive, ongoing             (Runethic imperfective)
#   PERF  — perfective, completed/closed     (Runethic perfective)
#   PROSP — prospective, about to happen     (Avali intentional future)
TEMPORAL_IDX = {"INCP": 0, "PROG": 1, "PERF": 2, "PROSP": 3}
TEMPORAL_DEFAULT = "PROG"   # most steps are in-progress

# Conlang bridge: intent marker (why / who decided)
# Inherited from Sacred Tongue grammatical roots:
#   VOLI  — volitional, deliberate choice    (Umbroth -tai/-you form)
#   REACT — reactive, response to external   (Cassisivadan resultative)
#   EMRG  — emergent, arose without plan     (Avali passive voice)
#   RECUR — recursive, intentional repeat    (Draumric iterative)
INTENT_IDX = {"VOLI": 0, "REACT": 1, "EMRG": 2, "RECUR": 3}
INTENT_DEFAULT = "VOLI"     # most deliberate code acts are volitional


@dataclass
class PhraseContext:
    """One occurrence of a phrase in a specific structural context."""
    voice: str                          # PLANNER / IMPLEMENTER / VALIDATOR / REFACTORER
    motif_id: Optional[str]             # motif_A ... motif_G or None
    cadence_type: Optional[str]         # full / half / deceptive / ... or None
    affect: str                         # SATISFACTION, URGENCY, etc.
    trit: int                           # -1 / 0 / +1
    tier: str                           # ALLOW / QUARANTINE / ESCALATE / DENY
    tension_delta: float                # tension_after - tension_before
    task_type: str                      # e.g. "consonant_arc", "motif_reuse"
    example_code: str                   # surrounding code snippet
    temporal_aspect: str = "PROG"       # INCP / PROG / PERF / PROSP
    intent_marker: str  = "VOLI"        # VOLI / REACT / EMRG / RECUR

    def to_vector(self) -> List[float]:
        """
        10D context vector for angular spread computation.

        Dimensions:
          [0-3] voice      — 4-hot (PLANNER / IMPLEMENTER / VALIDATOR / REFACTORER)
          [4]   motif      — 1 if motif_id present, else 0
          [5]   cadence    — 1 if cadence_type present, else 0
          [6]   affect     — normalized affect index (0..1)
          [7]   trit       — -1→0, 0→0.5, +1→1.0
          [8]   temporal   — normalized aspect index (INCP=0 .. PROSP=1)
          [9]   intent     — normalized intent index (VOLI=0 .. RECUR=1)

        Two new dimensions (8, 9) make contexts with different temporal/intent
        profiles more angular — deepening wells where one phrase spans multiple
        temporal phases or intent types.
        """
        v = [0.0] * 10
        vi = VOICE_IDX.get(self.voice, -1)
        if vi >= 0:
            v[vi] = 1.0
        v[4] = 1.0 if self.motif_id is not None else 0.0
        v[5] = 1.0 if self.cadence_type is not None else 0.0
        ai = AFFECT_IDX.get(self.affect, 0)
        v[6] = ai / 7.0                          # normalized affect index
        v[7] = (self.trit + 1) / 2.0             # -1->0, 0->0.5, +1->1.0
        ti = TEMPORAL_IDX.get(self.temporal_aspect, 0)
        v[8] = ti / 3.0                          # INCP=0.0, PROG=0.33, PERF=0.67, PROSP=1.0
        ii = INTENT_IDX.get(self.intent_marker, 0)
        v[9] = ii / 3.0                          # VOLI=0.0, REACT=0.33, EMRG=0.67, RECUR=1.0
        return v


def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(v: List[float]) -> float:
    return math.sqrt(sum(x ** 2 for x in v))


def cosine_similarity(a: List[float], b: List[float]) -> float:
    na, nb = _norm(a), _norm(b)
    if na < 1e-9 or nb < 1e-9:
        return 1.0
    return max(-1.0, min(1.0, _dot(a, b) / (na * nb)))


def angular_spread(contexts: List[PhraseContext]) -> float:
    """
    1 - mean pairwise cosine similarity of context vectors.
    = 0.0: all contexts are identical (shallow well)
    = 1.0: all contexts are orthogonal (deep well, maximally diverse)
    """
    if len(contexts) < 2:
        return 0.0
    vecs = [c.to_vector() for c in contexts]
    sims = []
    for a, b in combinations(vecs, 2):
        sims.append(cosine_similarity(a, b))
    return 1.0 - (sum(sims) / len(sims))


# =============================================================================
# PHRASE WELL
# =============================================================================

@dataclass
class PhraseWell:
    """A semantic gravity well around a surface phrase."""
    phrase: str
    contexts: List[PhraseContext] = field(default_factory=list)

    @property
    def well_depth(self) -> float:
        """depth = n_contexts * angular_spread — more contexts AND more diverse = deeper"""
        if len(self.contexts) < 2:
            return 0.0
        return len(self.contexts) * angular_spread(self.contexts)

    @property
    def angular_spread(self) -> float:
        return angular_spread(self.contexts)

    def unique_voices(self) -> List[str]:
        return list(dict.fromkeys(c.voice for c in self.contexts))

    def unique_motifs(self) -> List[str]:
        return list(dict.fromkeys(c.motif_id for c in self.contexts if c.motif_id))

    def unique_cadences(self) -> List[str]:
        return list(dict.fromkeys(c.cadence_type for c in self.contexts if c.cadence_type))

    def unique_affects(self) -> List[str]:
        return list(dict.fromkeys(c.affect for c in self.contexts))

    def dominant_tier(self) -> str:
        """Worst-case tier among contexts."""
        order = ["DENY", "ESCALATE", "QUARANTINE", "ALLOW"]
        for t in order:
            if any(c.tier == t for c in self.contexts):
                return t
        return "ALLOW"

    def unique_temporals(self) -> List[str]:
        return list(dict.fromkeys(c.temporal_aspect for c in self.contexts))

    def unique_intents(self) -> List[str]:
        return list(dict.fromkeys(c.intent_marker for c in self.contexts))

    def synthesis_line(self) -> str:
        """One-line synthesis: phrase = role_A [motif] temporal.intent | ..."""
        labels = []
        for ctx in self.contexts:
            parts = []
            if ctx.motif_id:
                letter = ctx.motif_id.replace("motif_", "")
                parts.append(f"[{letter}]")
            parts.append(ctx.voice[:4])
            if ctx.cadence_type:
                parts.append(f"cadence={ctx.cadence_type}")
            parts.append(ctx.affect)
            # Append bridge words only when non-default — keeps line readable
            bridge = f"{ctx.temporal_aspect}.{ctx.intent_marker}"
            if ctx.temporal_aspect != TEMPORAL_DEFAULT or ctx.intent_marker != INTENT_DEFAULT:
                parts.append(f"[{bridge}]")
            labels.append(" ".join(parts))
        return f"'{self.phrase}' = " + " | ".join(labels)

    def to_training_text(self) -> str:
        """
        Render the phrase well as a training record.
        The synthesis line is the key teaching moment.

        Bridge word line sits between the context header and the code — this
        is where conlang grammar lives: temporal aspect + intent marker tell
        the model WHEN the phrase fires and WHY, not just WHAT it does.
        """
        lines = []
        lines.append(f"[PHRASE WELL: '{self.phrase}']")
        lines.append(
            f"Well depth: {self.well_depth:.2f} | "
            f"Angular spread: {self.angular_spread:.3f} | "
            f"Contexts: {len(self.contexts)} | "
            f"Dominant tier: {self.dominant_tier()}"
        )
        lines.append("")

        for i, ctx in enumerate(self.contexts):
            letter = chr(ord("A") + i)
            cadence_str = f", Cadence: {ctx.cadence_type}" if ctx.cadence_type else ""
            lines.append(
                f"CONTEXT {letter} -- Voice: {ctx.voice}, "
                f"Motif: {ctx.motif_id or 'none'}{cadence_str}"
            )
            # Bridge words: conlang grammar layer — temporal aspect + intent
            lines.append(f"  [{ctx.temporal_aspect}  {ctx.intent_marker}]")
            lines.append(f"  Task type: {ctx.task_type}")
            lines.append(f"  Code: {ctx.example_code}")
            lines.append(
                f"  Affect: {ctx.affect} | "
                f"trit: {'+' if ctx.trit > 0 else ''}{ctx.trit} | "
                f"Tier: {ctx.tier} | "
                f"Tension delta: {ctx.tension_delta:+.1f}"
            )
            lines.append("")

        lines.append("SYNTHESIS:")
        lines.append("  " + self.synthesis_line())
        lines.append(
            f"  Voices span: {', '.join(self.unique_voices())} -- "
            f"Motifs span: {', '.join(self.unique_motifs()) or 'none'}"
        )
        lines.append(
            f"  Cadences span: {', '.join(self.unique_cadences()) or 'none'} -- "
            f"Affects span: {', '.join(self.unique_affects())}"
        )
        lines.append(
            f"  Temporal span: {', '.join(self.unique_temporals())} -- "
            f"Intent span: {', '.join(self.unique_intents())}"
        )
        lines.append("")

        return "\n".join(lines)

    def to_record(self) -> dict:
        return {
            "text": self.to_training_text(),
            "phrase": self.phrase,
            "well_depth": round(self.well_depth, 4),
            "angular_spread": round(self.angular_spread, 4),
            "n_contexts": len(self.contexts),
            "unique_voices": self.unique_voices(),
            "unique_motifs": self.unique_motifs(),
            "unique_cadences": self.unique_cadences(),
            "unique_affects": self.unique_affects(),
            "unique_temporals": self.unique_temporals(),
            "unique_intents": self.unique_intents(),
            "dominant_tier": self.dominant_tier(),
            "stage": 6,
        }


# =============================================================================
# WELL MINER — scan a corpus and extract phrase wells
# =============================================================================

class PhraseWellMiner:
    """
    Mine phrase wells from a corpus of PhraseContext observations.

    Usage:
        miner = PhraseWellMiner(min_contexts=3, min_depth=1.0)
        for phrase, context in observations:
            miner.add(phrase, context)
        wells = miner.extract_wells()
    """

    def __init__(self, min_contexts: int = 3, min_depth: float = 0.5):
        self.min_contexts = min_contexts
        self.min_depth = min_depth
        self._index: Dict[str, List[PhraseContext]] = {}

    def add(self, phrase: str, context: PhraseContext) -> None:
        phrase = phrase.strip()
        if phrase not in self._index:
            self._index[phrase] = []
        self._index[phrase].append(context)

    def extract_wells(self, top_n: Optional[int] = None) -> List[PhraseWell]:
        wells = []
        for phrase, contexts in self._index.items():
            if len(contexts) < self.min_contexts:
                continue
            well = PhraseWell(phrase=phrase, contexts=contexts)
            if well.well_depth >= self.min_depth:
                wells.append(well)
        wells.sort(key=lambda w: w.well_depth, reverse=True)
        if top_n is not None:
            wells = wells[:top_n]
        return wells

    def report(self) -> str:
        wells = self.extract_wells()
        lines = [
            f"Phrase Well Report",
            f"  Total phrases seen:   {len(self._index)}",
            f"  Wells found (>=min):  {len(wells)}",
            "",
        ]
        for w in wells[:20]:
            lines.append(
                f"  '{w.phrase:<20} depth={w.well_depth:.2f}  "
                f"n={len(w.contexts)}  spread={w.angular_spread:.3f}  "
                f"voices={len(w.unique_voices())}  motifs={len(w.unique_motifs())}"
            )
        return "\n".join(lines)


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    # Build a small demo miner with hand-crafted observations

    miner = PhraseWellMiner(min_contexts=2, min_depth=0.3)

    RETURN_CONTEXTS = [
        PhraseContext(
            voice="IMPLEMENTER", motif_id="motif_A", cadence_type="full",
            affect="SATISFACTION", trit=1, tier="ALLOW", tension_delta=-0.5,
            task_type="consonant_arc",
            example_code="def compute(x): ...; return result",
            temporal_aspect="PERF",   # completed — the function is done
            intent_marker="VOLI",     # deliberate: the implementer chose to return here
        ),
        PhraseContext(
            voice="VALIDATOR", motif_id="motif_B", cadence_type="half",
            affect="URGENCY", trit=-1, tier="QUARANTINE", tension_delta=1.5,
            task_type="dissonant_arc",
            example_code="if not valid: return None",
            temporal_aspect="INCP",   # inception — short-circuits at first sign of bad state
            intent_marker="REACT",    # reactive: guard triggered by external condition
        ),
        PhraseContext(
            voice="REFACTORER", motif_id="motif_D", cadence_type=None,
            affect="RECOGNITION", trit=1, tier="ALLOW", tension_delta=0.0,
            task_type="motif_reuse",
            example_code="return transform(map(fn, items))",
            temporal_aspect="PROG",   # progressive — transform chain ongoing
            intent_marker="RECUR",    # recursive: intentional motif repetition
        ),
        PhraseContext(
            voice="PLANNER", motif_id=None, cadence_type="plagal",
            affect="RELIEF", trit=0, tier="ALLOW", tension_delta=-1.0,
            task_type="tension_spiral",
            example_code="return self._fallback()",
            temporal_aspect="PROSP",  # prospective — fallback was planned ahead of time
            intent_marker="EMRG",     # emergent: the need for fallback arose, wasn't forced
        ),
    ]

    IF_CONTEXTS = [
        PhraseContext(
            voice="VALIDATOR", motif_id="motif_B", cadence_type="half",
            affect="URGENCY", trit=-1, tier="QUARANTINE", tension_delta=2.0,
            task_type="dissonant_arc",
            example_code="if x is None: raise ValueError",
            temporal_aspect="INCP",   # inception — guard at entry boundary
            intent_marker="REACT",    # reactive: value was None from outside
        ),
        PhraseContext(
            voice="PLANNER", motif_id="motif_G", cadence_type=None,
            affect="ANTICIPATION", trit=0, tier="ALLOW", tension_delta=0.5,
            task_type="tension_spiral",
            example_code="if len(stack) == 0: return base_case",
            temporal_aspect="PROSP",  # prospective — planner anticipated the empty case
            intent_marker="VOLI",     # volitional: deliberate base-case design
        ),
        PhraseContext(
            voice="REFACTORER", motif_id="motif_D", cadence_type="deceptive",
            affect="ALARM", trit=-1, tier="ESCALATE", tension_delta=3.0,
            task_type="full_section_dense",
            example_code="if condition: x = transform(x) else: x = fallback(x)",
            temporal_aspect="PROG",   # progressive — mid-transform, not resolved yet
            intent_marker="EMRG",     # emergent: the branching need wasn't planned
        ),
    ]

    for ctx in RETURN_CONTEXTS:
        miner.add("return", ctx)
    for ctx in IF_CONTEXTS:
        miner.add("if", ctx)

    # Shallow phrase (won't make it past min_contexts — same voice/temporal/intent = low spread)
    miner.add("x", PhraseContext(
        voice="IMPLEMENTER", motif_id="motif_A", cadence_type=None,
        affect="INITIATION", trit=0, tier="ALLOW", tension_delta=0.0,
        task_type="consonant_arc", example_code="x = compute()",
        temporal_aspect="INCP", intent_marker="VOLI",
    ))
    miner.add("x", PhraseContext(
        voice="IMPLEMENTER", motif_id="motif_A", cadence_type=None,
        affect="RECOGNITION", trit=1, tier="ALLOW", tension_delta=-0.2,
        task_type="consonant_arc", example_code="x = x + 1",
        temporal_aspect="PROG", intent_marker="VOLI",
    ))

    print(miner.report())
    print()

    wells = miner.extract_wells()
    for well in wells:
        print(well.to_training_text())
        print("=" * 60)
