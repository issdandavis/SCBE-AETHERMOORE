"""
dense_record.py

Multi-coded dense training records — Stage 5.

The same token carries 6 simultaneous codings:
  L0  tongue      Sacred Tongue assignment (KO/AV/RU/CA/UM/DR) + phi weight
  L1  musical     bar / beat / stress / voice / motif
  L2  trit        polarity (-1 / 0 / +1) + R-value contribution
  L3  hyperbolic  d_H position on Poincaré ball + governance tier
  L4  affect      structural emotional salience imitation
  L5  cadence     tension state + cadence event (if at resolution point)

Why multi-coding matters:
  When all 6 layers agree on the same token — e.g.:
    tongue=DR  AND  trit=-1  AND  tier=DENY  AND  affect=ALARM  AND  cadence=dissonance
  the signal is DENSE. The model doesn't need to learn these correlations
  separately across millions of examples. They're fused at the source.

  This is cross-representation: the same event described simultaneously
  in every language the system knows. Like a translation dictionary where
  every entry shows the word in English, French, Japanese, music notation,
  binary, and geometry — all at once.

Emotional relevancy imitation:
  NOT claiming the model feels emotions.
  Encoding STRUCTURAL PATTERNS that correlate with human emotional
  responses when reading or writing code.

  A human feels URGENCY when there are many open dependencies and no closure.
  A human feels SATISFACTION when a bug is resolved and tests pass.
  A human feels RECOGNITION when they see a familiar pattern.
  A human feels ALARM when they see a type error or unreachable code.

  These are ATTENTION WEIGHTS masquerading as emotions.
  Training on them gives the model an implicit salience map:
    INITIATION events  → pay attention, something is starting
    RESOLUTION events  → this matters, an arc just closed
    DISSONANCE events  → this is wrong, structural error
    RECOGNITION events → this is familiar, trust but verify

  The model learns to WEIGHT its attention to structurally important
  tokens, the same way a human reader does.

Affect vocabulary (8 states — maps to 3-bit encoding):
  INITIATION    000  something new begins (define, plan_step, loop_start)
  ANTICIPATION  001  arc open, outcome pending (call, if_branch, try_start)
  RECOGNITION   010  familiar pattern seen again (motif_repeat)
  ENGAGEMENT    011  familiar but modified (motif_variation)
  URGENCY       100  high tension, multiple open arcs
  ALARM         101  dissonance or governance breach
  RELIEF        110  partial resolution (half cadence)
  SATISFACTION  111  full resolution (full/plagal cadence)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
import math

PHI = 1.618033988749895
TONGUE_NAMES = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_FULLNAMES = ["Kor'aelin", "Avali", "Runethic", "Cassisivadan", "Umbroth", "Draumric"]
PHI_WEIGHTS = [1.00, 1.62, 2.62, 4.24, 6.85, 11.09]
MAX_R = 27.42

# Affect 3-bit codes (for compact encoding)
AFFECT_CODES = {
    "INITIATION":   "000",
    "ANTICIPATION": "001",
    "RECOGNITION":  "010",
    "ENGAGEMENT":   "011",
    "URGENCY":      "100",
    "ALARM":        "101",
    "RELIEF":       "110",
    "SATISFACTION": "111",
}

# Governance tier from d_H
def _tier(d: float) -> str:
    if d < 0.30:  return "ALLOW"
    if d < 0.55:  return "QUARANTINE"
    if d < 0.75:  return "ESCALATE"
    return "DENY"

_PHI = 1.6180339887

def _cost(d: float, R: float = 5.0) -> float:
    """H(d,R) = phi^d / (1 + e^-R) — golden ratio exponential, sigmoid-gated."""
    return (_PHI ** d) / (1.0 + math.exp(-R))


# =============================================================================
# DENSE TOKEN
# =============================================================================

@dataclass
class DenseToken:
    """
    A single token with all 6 layers of coding attached.

    This is the atom of Stage 5 training data.
    Each position in the sequence carries the full stack.
    """

    # Identity
    token: str                          # surface token string
    position: int = 0                   # position in sequence

    # L0: Sacred Tongue
    tongue_idx: int = 0                 # 0=KO 1=AV 2=RU 3=CA 4=UM 5=DR
    phi_weight: float = 1.00

    # L1: Musical
    bar: int = 1
    beat: int = 1
    stress: float = 1.0
    voice: str = "IMPLEMENTER"
    motif_id: Optional[str] = None
    motif_instance: int = 1
    is_motif_first: bool = True         # True=new instance, False=repeat

    # L2: Trit
    trit: int = 0                       # -1 / 0 / +1
    r_contribution: float = 0.0        # this token's contribution to R

    # L3: Hyperbolic
    d_H: float = 0.0
    tier: str = "ALLOW"
    h_cost: float = 1.0

    # L4: Affect
    affect: str = "INITIATION"
    salience: str = "MEDIUM"           # HIGH / MEDIUM / LOW

    # L5: Cadence / Tension
    tension_before: float = 0.0
    tension_after: float = 0.0
    is_cadence: bool = False
    cadence_type: Optional[str] = None
    resolution: float = 0.0

    def to_notation(self) -> str:
        """Render as compact multi-layer notation for training."""
        trit_str = {-1: "-1", 0: "0", 1: "+1"}[self.trit]
        affect_bits = AFFECT_CODES.get(self.affect, "???")
        tongue = TONGUE_NAMES[self.tongue_idx]
        tongue_full = TONGUE_FULLNAMES[self.tongue_idx]

        lines = [
            f"[T{self.position}] token={self.token!r}",
            f"  L0: tongue={tongue}({tongue_full}) phi={self.phi_weight:.2f} slot={self.tongue_idx}",
            f"  L1: bar={self.bar} beat={self.beat} stress={self.stress:.1f} "
            f"voice={self.voice}" + (f" motif={self.motif_id}[{self.motif_instance}]{'*' if not self.is_motif_first else ''}" if self.motif_id else ""),
            f"  L2: trit={trit_str} R_contrib={self.r_contribution:.2f}",
            f"  L3: d_H={self.d_H:.3f} tier={self.tier} cost={self.h_cost:.3f}",
            f"  L4: affect={self.affect}({affect_bits}) salience={self.salience}",
        ]

        tension_delta = self.tension_after - self.tension_before
        cadence_str = ""
        if self.is_cadence:
            cadence_str = f" cadence={self.cadence_type} resolution={self.resolution:.2f}"
        lines.append(
            f"  L5: tension={self.tension_before:.1f}->{self.tension_after:.1f}"
            f"(delta={tension_delta:+.1f}){cadence_str}"
        )
        return "\n".join(lines)


# =============================================================================
# DENSE RECORD
# =============================================================================

@dataclass
class DenseRecord:
    """
    A sequence of DenseTokens forming one training example.

    Contains:
    - the original surface sequence (for CLM loss)
    - the full 6-layer annotation at every position
    - a header summarizing the record's aggregate properties
    """

    name: str
    section_type: str = "function"
    tokens: List[DenseToken] = field(default_factory=list)

    def to_notation(self) -> str:
        # Compute aggregate stats
        n = len(self.tokens)
        if n == 0:
            return f"[DENSE_RECORD: {self.name}] (empty)"

        mean_d = sum(t.d_H for t in self.tokens) / n
        peak_tension = max(t.tension_after for t in self.tokens)
        mean_consonance_proxy = sum(
            1.0 if t.trit == 1 else (0.5 if t.trit == 0 else 0.0)
            for t in self.tokens
        ) / n
        cadence_events = [t for t in self.tokens if t.is_cadence]
        affect_counts: Dict[str, int] = {}
        for t in self.tokens:
            affect_counts[t.affect] = affect_counts.get(t.affect, 0) + 1
        dominant_affect = max(affect_counts, key=lambda k: affect_counts[k])

        surface = " ".join(t.token for t in self.tokens)

        header = (
            f"[DENSE_RECORD: {self.name} | type={self.section_type} | n={n}]\n"
            f"surface: {surface}\n"
            f"aggregate: mean_d={mean_d:.3f} peak_tension={peak_tension:.1f} "
            f"consonance={mean_consonance_proxy:.2f} "
            f"cadences={len(cadence_events)} dominant_affect={dominant_affect}\n"
        )
        body = "\n".join(t.to_notation() for t in self.tokens)
        return header + body

    def to_training_text(self) -> str:
        """Compact format for actual training (less verbose than full notation)."""
        n = len(self.tokens)
        surface = " ".join(t.token for t in self.tokens)
        lines = [f"[DENSE:{self.name}] surface={surface!r}"]
        for t in self.tokens:
            trit_str = {-1: "-1", 0: "0", 1: "+1"}[t.trit]
            tongue = TONGUE_NAMES[t.tongue_idx]
            affect_bits = AFFECT_CODES.get(t.affect, "???")
            cadence_str = f" cad={t.cadence_type}" if t.is_cadence else ""
            lines.append(
                f"  {t.position}: {t.token!r} "
                f"T={tongue}(phi={t.phi_weight:.2f}) "
                f"beat={t.beat} stress={t.stress:.1f} "
                f"trit={trit_str} "
                f"d={t.d_H:.3f} tier={t.tier} "
                f"aff={t.affect}({affect_bits})"
                f"{cadence_str}"
            )
        return "\n".join(lines)


# =============================================================================
# AFFECT ASSIGNMENT
# Structural pattern → emotional relevancy imitation
# =============================================================================

# Action type → affect mapping
_ACTION_AFFECT: Dict[str, str] = {
    # INITIATION: something new begins
    "define_func":    "INITIATION",
    "define_class":   "INITIATION",
    "plan_step":      "INITIATION",
    "loop_start":     "INITIATION",
    "try_start":      "INITIATION",
    "import":         "INITIATION",

    # ANTICIPATION: arc open, outcome pending
    "call":           "ANTICIPATION",
    "call_method":    "ANTICIPATION",
    "call_builtin":   "ANTICIPATION",
    "if_branch":      "ANTICIPATION",
    "define_var":     "ANTICIPATION",

    # RELIEF: partial resolution
    "assign":         "RELIEF",
    "augmented_assign": "RELIEF",
    "loop_end":       "RELIEF",

    # SATISFACTION: full resolution
    "return":         "SATISFACTION",
    "validate_step":  "SATISFACTION",
    "assert":         "SATISFACTION",

    # ALARM: structural problems
    "raise":          "ALARM",
    "type_check":     "ANTICIPATION",  # checking = watchful

    # ENGAGEMENT: transformation
    "refactor_step":  "ENGAGEMENT",
    "from_import":    "ENGAGEMENT",

    # RECOGNITION: review/confirm
    "comment_intent": "RECOGNITION",
    "comment_why":    "RECOGNITION",
}

# Dissonance detected → override to ALARM
def affect_for_token(
    action_type: str,
    consonance: float,
    motif_id: Optional[str],
    is_motif_first: bool,
    tension_delta: float,
) -> Tuple[str, str]:
    """
    Return (affect, salience) for a token given its structural context.

    Priority order:
    1. Dissonance (consonance < 0.5) → ALARM / HIGH
    2. High tension spike (+2 or more) → URGENCY / HIGH
    3. Motif repeat → RECOGNITION / MEDIUM
    4. Motif first instance → ENGAGEMENT / MEDIUM
    5. Default from action type
    """
    # 1. Dissonance
    if consonance < 0.5:
        return "ALARM", "HIGH"

    # 2. Urgency
    if tension_delta >= 2.0:
        return "URGENCY", "HIGH"

    # 3-4. Motif events
    if motif_id is not None:
        if not is_motif_first:
            return "RECOGNITION", "MEDIUM"
        return "ENGAGEMENT", "MEDIUM"

    # 5. Default
    affect = _ACTION_AFFECT.get(action_type, "ANTICIPATION")

    # Salience from affect + action
    high_salience = {"INITIATION", "SATISFACTION", "ALARM"}
    salience = "HIGH" if affect in high_salience else "MEDIUM"

    return affect, salience


# =============================================================================
# TOKEN ENCODER
# Map a (token_string, context) to a fully-coded DenseToken
# =============================================================================

def encode_token(
    token: str,
    position: int,
    # Musical context
    bar: int = 1,
    beat: int = 1,
    voice: str = "IMPLEMENTER",
    motif_id: Optional[str] = None,
    motif_instance: int = 1,
    is_motif_first: bool = True,
    consonance: float = 1.0,
    # Tension state
    tension_before: float = 0.0,
    tension_after: float = 0.0,
    is_cadence: bool = False,
    cadence_type: Optional[str] = None,
    resolution: float = 0.0,
    # Action type (for affect)
    action_type: str = "assign",
) -> DenseToken:
    """
    Encode a single token string with full 6-layer dense annotation.

    Tongue assignment: byte_val % 6
    Trit assignment: based on consonance and tension_delta
    d_H: derived from phi_weight of assigned tongue (scaled)
    Affect: structural pattern inference
    """
    # L0: tongue from byte value of first char
    byte_val = ord(token[0]) if token else 0
    tongue_idx = byte_val % 6
    phi_weight = PHI_WEIGHTS[tongue_idx]

    # L1: musical
    stress = {1: 1.0, 2: 0.5, 3: 0.7, 4: 0.3}.get(beat, 0.5)

    # L2: trit from consonance + tension direction
    tension_delta = tension_after - tension_before
    if consonance < 0.5 or tension_delta >= 2.0:
        trit = -1   # dissonant
    elif consonance >= 0.85 and tension_delta <= 0:
        trit = 1    # consonant, resolving or neutral
    else:
        trit = 0    # neutral

    r_contribution = trit * phi_weight if trit != 0 else 0.0

    # L3: d_H from tongue position (scale phi_weight to [0,1] range)
    d_H = phi_weight / (MAX_R + 1.0)  # approximate: ranges from 0.036 to 0.40
    tier = _tier(d_H)
    h_cost = _cost(d_H)

    # L4: affect
    affect, salience = affect_for_token(
        action_type, consonance, motif_id, is_motif_first, tension_delta
    )
    # Override salience for cadence events
    if is_cadence and cadence_type == "full":
        affect = "SATISFACTION"
        salience = "HIGH"
    elif is_cadence and cadence_type == "half":
        affect = "RELIEF"
        salience = "MEDIUM"
    elif is_cadence and cadence_type == "deceptive":
        affect = "ALARM"
        salience = "HIGH"
    elif is_cadence and cadence_type == "plagal":
        affect = "RECOGNITION"
        salience = "MEDIUM"

    return DenseToken(
        token=token,
        position=position,
        tongue_idx=tongue_idx,
        phi_weight=phi_weight,
        bar=bar,
        beat=beat,
        stress=stress,
        voice=voice,
        motif_id=motif_id,
        motif_instance=motif_instance,
        is_motif_first=is_motif_first,
        trit=trit,
        r_contribution=r_contribution,
        d_H=d_H,
        tier=tier,
        h_cost=h_cost,
        affect=affect,
        salience=salience,
        tension_before=tension_before,
        tension_after=tension_after,
        is_cadence=is_cadence,
        cadence_type=cadence_type,
        resolution=resolution,
    )


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    import sys, io
    # Force UTF-8 output on Windows
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    # Encode a simple guard-then-return function (motif_B)
    tokens_data = [
        # (token, bar, beat, voice, action_type, consonance, tension_before, tension_after, motif_id, is_first)
        ("def",         1, 1, "IMPLEMENTER", "define_func",  1.0, 0.0, 0.5, "motif_B", True),
        ("guard_fn",    1, 2, "IMPLEMENTER", "define_func",  0.95, 0.5, 0.5, "motif_B", True),
        ("if",          1, 3, "IMPLEMENTER", "if_branch",    0.90, 0.5, 1.5, "motif_B", True),
        ("not",         1, 3, "IMPLEMENTER", "if_branch",    0.90, 1.5, 1.5, None, True),
        ("lst",         1, 3, "IMPLEMENTER", "define_var",   0.90, 1.5, 1.5, None, True),
        ("return",      1, 4, "IMPLEMENTER", "return",       0.95, 1.5, 0.5, "motif_B", True),
        ("sorted",      2, 1, "IMPLEMENTER", "call_builtin", 0.95, 0.5, 1.0, "motif_D", True),
        ("lst",         2, 2, "IMPLEMENTER", "define_var",   0.95, 1.0, 1.0, None, True),
        ("return",      2, 4, "IMPLEMENTER", "return",       1.0,  1.0, 0.0, "motif_A", True),
    ]

    record = DenseRecord(name="guard_fn", section_type="function")
    for i, (tok, bar, beat, voice, action, consonance, t_before, t_after, motif, is_first) in enumerate(tokens_data):
        is_cad = (i == len(tokens_data) - 1)
        record.tokens.append(encode_token(
            token=tok, position=i,
            bar=bar, beat=beat, voice=voice,
            motif_id=motif, is_motif_first=is_first,
            consonance=consonance,
            tension_before=t_before, tension_after=t_after,
            is_cadence=is_cad, cadence_type="full" if is_cad else None,
            resolution=1.0 if is_cad else 0.0,
            action_type=action,
        ))

    print("=== FULL NOTATION ===")
    print(record.to_notation())
    print()
    print("=== COMPACT TRAINING FORMAT ===")
    print(record.to_training_text())
