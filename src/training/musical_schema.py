"""
musical_schema.py

Musical feature schema for agentic code actions.

NOT a metaphor system — a structural prior.
Music theory provides the ORDERING and RELATIONSHIP layer.
AST/trits/tongue weights are still the semantic layer.
Governance checks whether the arrangement stays coherent.

Schema design principle:
  Every field must answer a question that improves model behavior:
    onset:       "when in the plan does this happen?"
    duration:    "how much of the model's budget does this consume?"
    stress:      "how load-bearing is this step?"
    motif_id:    "have we seen this pattern before?"
    interval:    "how big is the conceptual jump from the last step?"
    consonance:  "does this fit with its neighbors?"
    resolution:  "does this close something that was open?"
    tension:     "what's still unresolved after this?"
    cadence:     "is this a closure point?"

Voice model (4 agent roles = 4 voices):
  PLANNER     — sets meter, announces structure, lays out bars
  IMPLEMENTER — carries the melody, fills in the main content
  VALIDATOR   — counterpoint voice, checks against invariants
  REFACTORER  — inversion/transposition voice, lifts patterns

Motif system:
  A motif is a recurring solution pattern (not a recurring token sequence).
  motif_A: define-then-return (simple function body)
  motif_B: guard-then-execute (early return / validation first)
  motif_C: collect-then-emit (accumulator pattern)
  motif_D: transform-chain (pipe / map / filter sequence)
  motif_E: error-then-recover (try/catch or fallback)
  motif_F: fan-out-then-join (parallel then merge)
  motif_G: recurse-then-base (recursive descent)

Cadence types:
  full:       full resolution — function complete, test passes, state closed
  half:       partial resolution — milestone reached, more work pending
  deceptive:  expected resolution replaced by redirect — error caught → repair
  interrupted: closure interrupted by new dependency or async event
  plagal:     confirmation after resolution (assertion after return)

Tension model:
  tension = count of unresolved open brackets:
    open call with no result yet     → +1
    open loop with no break          → +1
    open dependency (unbound name)   → +1
    open exception handler           → +1
  Resolution events bring tension → 0 (cadence)
  Dissonance = tension delta that spikes without resolution

Consonance model:
  Type-flow consonance:   do neighboring operations agree on types?
  Scope consonance:       are names used in their declared scope?
  Voice consonance:       is this the right voice for this action?
  Motif consonance:       does this action fit the established motif?
  Consonance ∈ [0, 1], below 0.5 = dissonance (training signal)
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
import json


# =============================================================================
# CONSTANTS
# =============================================================================

VOICES = ["PLANNER", "IMPLEMENTER", "VALIDATOR", "REFACTORER"]

MOTIFS = {
    "motif_A": "define-then-return       (simple function body)",
    "motif_B": "guard-then-execute       (early return / validation first)",
    "motif_C": "collect-then-emit        (accumulator pattern)",
    "motif_D": "transform-chain          (pipe / map / filter sequence)",
    "motif_E": "error-then-recover       (try/catch or fallback)",
    "motif_F": "fan-out-then-join        (parallel then merge)",
    "motif_G": "recurse-then-base        (recursive descent)",
}

CADENCES = {
    "full":        "complete resolution — function done, test passes, state closed",
    "half":        "partial resolution — milestone reached, more pending",
    "deceptive":   "expected resolution -> redirect (error caught -> repair)",
    "interrupted": "closure interrupted by new dependency or async event",
    "plagal":      "confirmation after resolution (assert after return)",
}

ACTION_TYPES = [
    "define_func", "define_class", "define_var",
    "call", "call_method", "call_builtin",
    "assign", "augmented_assign",
    "return", "yield", "raise",
    "if_branch", "else_branch",
    "loop_start", "loop_body", "loop_end",
    "try_start", "except_handler", "finally_block",
    "import", "from_import",
    "assert", "type_check",
    "comment_intent", "comment_why",
    "plan_step", "validate_step", "refactor_step",
]

# Beat stress weights (1=downbeat, 2=upbeat, 3=off-beat, 4=weak)
BEAT_STRESS = {1: 1.0, 2: 0.5, 3: 0.7, 4: 0.3}


# =============================================================================
# DATACLASS
# =============================================================================

@dataclass
class MusicalAction:
    """
    One code action annotated with musical features.

    This is the atomic unit of the musical code pretraining schema.
    A sequence of MusicalActions forms a Phrase.
    A sequence of Phrases forms a Section (function, test, class body).
    A sequence of Sections forms a Composition (file, module, agent plan).
    """

    # --- Identity ---
    action_type: str                     # from ACTION_TYPES
    voice: str                           # PLANNER | IMPLEMENTER | VALIDATOR | REFACTORER
    label: str = ""                      # human-readable description (e.g. "define sort_list")

    # --- Temporal ---
    onset: int = 0                       # step index in the sequence
    duration: int = 1                    # token-budget this action consumes (1 = atomic)
    bar: int = 1                         # which phrase bar this falls in
    beat: int = 1                        # beat within bar (1-4 for 4/4 meter)
    stress: float = 1.0                  # importance weight (downbeat=1.0, weak=0.3)

    # --- Relational ---
    motif_id: Optional[str] = None       # None if novel; "motif_A" etc. if recurring
    motif_instance: int = 1              # which instance of this motif (1=first, 2=variation...)
    interval: int = 0                    # conceptual distance from prior action (0=adjacent)

    # --- Harmonic ---
    consonance: float = 1.0             # compatibility with neighbors [0,1]
    resolution: float = 0.0            # how much this closes open dependencies [0,1]
    tension_before: float = 0.0        # unresolved deps before this action
    tension_after: float = 0.0         # unresolved deps after this action (tension delta)

    # --- Cadence ---
    cadence_type: Optional[str] = None  # None | "full" | "half" | "deceptive" | ...
    is_cadence_point: bool = False       # True if this is a resolution point

    def to_notation(self) -> str:
        """
        Render this action as compact structured notation (no prose).
        This is the training format — the model learns to produce
        and predict these fields.
        """
        parts = [
            f"beat={self.beat} stress={self.stress:.1f}",
            f"voice={self.voice}",
            f"action={self.action_type}",
        ]
        if self.label:
            parts.append(f"label={self.label!r}")
        if self.motif_id:
            parts.append(f"motif={self.motif_id}[{self.motif_instance}]")
        if self.interval > 0:
            parts.append(f"interval={self.interval}")
        parts.append(f"consonance={self.consonance:.2f}")
        if self.tension_after > 0:
            parts.append(f"tension={self.tension_after:.1f}")
        if self.is_cadence_point:
            parts.append(f"cadence={self.cadence_type}")
            parts.append(f"resolution={self.resolution:.2f}")
        return "  " + " | ".join(parts)

    def tension_delta(self) -> float:
        return self.tension_after - self.tension_before


@dataclass
class Phrase:
    """
    One bar/measure of code actions.
    Analogous to a musical phrase — a bounded procedural unit.
    """
    bar: int
    meter: str = "4/4"                  # "4/4" standard, "3/4" for tight loops, "6/8" for pipelines
    voice_lead: str = "IMPLEMENTER"     # which voice carries the main action this bar
    actions: List[MusicalAction] = field(default_factory=list)
    motif_id: Optional[str] = None      # if the whole bar instantiates one motif

    def to_notation(self) -> str:
        lines = [f"[BAR {self.bar} | meter={self.meter} | lead={self.voice_lead}]"]
        if self.motif_id:
            lines.append(f"  motif_context: {self.motif_id} — {MOTIFS.get(self.motif_id, '')}")
        for a in self.actions:
            lines.append(a.to_notation())
        # Bar summary
        tensions = [a.tension_after for a in self.actions]
        consonances = [a.consonance for a in self.actions]
        cadences = [a for a in self.actions if a.is_cadence_point]
        mean_c = sum(consonances) / len(consonances) if consonances else 0.0
        peak_t = max(tensions) if tensions else 0.0
        lines.append(f"  bar_summary: consonance={mean_c:.2f} peak_tension={peak_t:.1f} cadences={len(cadences)}")
        return "\n".join(lines)


@dataclass
class Section:
    """
    One logical unit: function body, test, agent task, class method.
    A sequence of Phrases.
    """
    name: str
    section_type: str                   # "function" | "test" | "plan" | "class_method" | "agent_task"
    meter: str = "4/4"
    key_motif: Optional[str] = None     # dominant motif of this section
    phrases: List[Phrase] = field(default_factory=list)

    def to_notation(self) -> str:
        lines = [
            f"[SECTION: {self.name}]",
            f"  type={self.section_type} meter={self.meter}",
        ]
        if self.key_motif:
            lines.append(f"  key_motif={self.key_motif} ({MOTIFS.get(self.key_motif, '')})")
        for phrase in self.phrases:
            lines.append("")
            lines.append(phrase.to_notation())
        return "\n".join(lines)


# =============================================================================
# ANNOTATION HELPERS
# =============================================================================

def stress_for_beat(beat: int) -> float:
    """Standard 4/4 beat stress."""
    return BEAT_STRESS.get(beat, 0.3)


def consonance_for_pair(action_a: str, action_b: str) -> float:
    """
    Heuristic consonance between two adjacent action types.
    Returns [0,1]: 1.0 = perfectly compatible, 0.0 = clash.
    """
    # High consonance: natural sequences
    HIGH = {
        ("define_func", "define_var"),
        ("define_var", "assign"),
        ("call", "assign"),
        ("call_method", "assign"),
        ("if_branch", "return"),
        ("assert", "return"),
        ("loop_start", "loop_body"),
        ("loop_body", "loop_end"),
        ("try_start", "except_handler"),
        ("plan_step", "define_func"),
        ("validate_step", "assert"),
    }
    # Low consonance: problematic sequences
    LOW = {
        ("return", "assign"),        # assigning after return = unreachable
        ("raise", "assign"),         # same
        ("loop_end", "loop_body"),   # body after end = wrong order
        ("except_handler", "try_start"),  # handler before try = wrong order
        ("return", "call"),          # call after return = unreachable
    }

    pair = (action_a, action_b)
    pair_r = (action_b, action_a)
    if pair in HIGH or pair_r in HIGH:
        return 0.95
    if pair in LOW or pair_r in LOW:
        return 0.15
    return 0.75


def detect_motif(actions: List[str]) -> Optional[str]:
    """Heuristic motif detection from a sequence of action types."""
    if "define_func" in actions and "return" in actions and "if_branch" not in actions:
        return "motif_A"   # define-then-return
    if actions and actions[0] in ("if_branch", "assert") and "return" in actions:
        return "motif_B"   # guard-then-execute
    if "loop_start" in actions and "augmented_assign" in actions:
        return "motif_C"   # collect-then-emit
    if actions.count("call_builtin") >= 2 or actions.count("call_method") >= 2:
        return "motif_D"   # transform-chain
    if "try_start" in actions and "except_handler" in actions:
        return "motif_E"   # error-then-recover
    return None


def tension_from_actions(actions: List[MusicalAction]) -> List[float]:
    """
    Compute running tension through a sequence of actions.
    Each "open" event raises tension; each resolution lowers it.
    """
    tension = 0.0
    tensions = []
    OPEN_EVENTS = {"try_start", "loop_start", "if_branch", "call"}
    CLOSE_EVENTS = {"return", "loop_end", "finally_block", "assign"}
    for a in actions:
        if a.action_type in OPEN_EVENTS:
            tension += 1.0
        if a.action_type in CLOSE_EVENTS:
            tension = max(0.0, tension - 1.0)
        if a.is_cadence_point:
            tension = 0.0
        tensions.append(tension)
    return tensions


# =============================================================================
# EXAMPLE: ANNOTATE A SIMPLE SORT FUNCTION
# =============================================================================

def example_sort_section() -> Section:
    """
    Build an annotated Section for a simple sort function.
    Demonstrates the schema in action.
    """
    # Bar 1: PLANNER sets up the structure (meter: plan has 4 beats)
    plan_actions = [
        MusicalAction(
            action_type="plan_step", voice="PLANNER",
            label="announce: sort_list function",
            bar=1, beat=1, stress=1.0, onset=0,
            consonance=1.0, tension_before=0.0, tension_after=0.0,
        ),
        MusicalAction(
            action_type="plan_step", voice="PLANNER",
            label="args: lst, key=None, reverse=False",
            bar=1, beat=2, stress=0.5, onset=1,
            consonance=0.95, tension_before=0.0, tension_after=0.0,
        ),
        MusicalAction(
            action_type="plan_step", voice="PLANNER",
            label="body: guard empty -> return; else sort -> return",
            bar=1, beat=3, stress=0.7, onset=2, interval=1,
            motif_id="motif_B", motif_instance=1,
            consonance=0.9, tension_before=0.0, tension_after=0.5,
        ),
        MusicalAction(
            action_type="plan_step", voice="PLANNER",
            label="cadence: half (plan closed, impl pending)",
            bar=1, beat=4, stress=0.3, onset=3,
            consonance=0.95, tension_before=0.5, tension_after=0.5,
            is_cadence_point=True, cadence_type="half", resolution=0.4,
        ),
    ]
    phrase1 = Phrase(bar=1, meter="4/4", voice_lead="PLANNER",
                     actions=plan_actions, motif_id="motif_B")

    # Bar 2: IMPLEMENTER fills in the body
    impl_actions = [
        MusicalAction(
            action_type="define_func", voice="IMPLEMENTER",
            label="def sort_list(lst, key=None, reverse=False)",
            bar=2, beat=1, stress=1.0, onset=4, interval=2,
            motif_id="motif_B", motif_instance=1,
            consonance=0.95, tension_before=0.5, tension_after=1.0,
        ),
        MusicalAction(
            action_type="if_branch", voice="IMPLEMENTER",
            label="if not lst: return []",
            bar=2, beat=2, stress=0.8, onset=5,
            consonance=0.9, tension_before=1.0, tension_after=1.5,
        ),
        MusicalAction(
            action_type="return", voice="IMPLEMENTER",
            label="return sorted(lst, key=key, reverse=reverse)",
            bar=2, beat=3, stress=0.9, onset=6,
            motif_id="motif_A", motif_instance=1,
            consonance=0.95, tension_before=1.5, tension_after=0.5,
        ),
        MusicalAction(
            action_type="return", voice="IMPLEMENTER",
            label="full cadence: function body complete",
            bar=2, beat=4, stress=1.0, onset=7,
            consonance=1.0, tension_before=0.5, tension_after=0.0,
            is_cadence_point=True, cadence_type="full", resolution=1.0,
        ),
    ]
    phrase2 = Phrase(bar=2, meter="4/4", voice_lead="IMPLEMENTER",
                     actions=impl_actions, motif_id="motif_B")

    # Bar 3: VALIDATOR confirms
    val_actions = [
        MusicalAction(
            action_type="assert", voice="VALIDATOR",
            label="assert sort_list([3,1,2]) == [1,2,3]",
            bar=3, beat=1, stress=1.0, onset=8, interval=1,
            consonance=1.0, tension_before=0.0, tension_after=0.0,
        ),
        MusicalAction(
            action_type="assert", voice="VALIDATOR",
            label="assert sort_list([]) == []   # guard case",
            bar=3, beat=2, stress=0.8, onset=9,
            motif_id="motif_B", motif_instance=2,  # guard pattern again
            consonance=0.95, tension_before=0.0, tension_after=0.0,
        ),
        MusicalAction(
            action_type="assert", voice="VALIDATOR",
            label="assert sort_list([1], reverse=True) == [1]  # singleton",
            bar=3, beat=3, stress=0.7, onset=10,
            consonance=0.9, tension_before=0.0, tension_after=0.0,
        ),
        MusicalAction(
            action_type="validate_step", voice="VALIDATOR",
            label="plagal cadence: all assertions passed",
            bar=3, beat=4, stress=0.5, onset=11,
            consonance=1.0, tension_before=0.0, tension_after=0.0,
            is_cadence_point=True, cadence_type="plagal", resolution=1.0,
        ),
    ]
    phrase3 = Phrase(bar=3, meter="4/4", voice_lead="VALIDATOR",
                     actions=val_actions)

    return Section(
        name="sort_list",
        section_type="function",
        meter="4/4",
        key_motif="motif_B",
        phrases=[phrase1, phrase2, phrase3],
    )


# =============================================================================
# SERIALIZATION
# =============================================================================

def section_to_jsonl_record(section: Section) -> dict:
    """Convert a Section to a JSONL training record (text field)."""
    return {"text": section.to_notation(), "type": "musical_code", "section": section.name}


if __name__ == "__main__":
    # Demo: render the sort_list example
    s = example_sort_section()
    print(s.to_notation())
    print()
    print("JSONL record text length:", len(section_to_jsonl_record(s)["text"]))
    print()
    print("Available motifs:")
    for k, v in MOTIFS.items():
        print(f"  {k}: {v}")
    print()
    print("Available cadences:")
    for k, v in CADENCES.items():
        print(f"  {k}: {v}")
