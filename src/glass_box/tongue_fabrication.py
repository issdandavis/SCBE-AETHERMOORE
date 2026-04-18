"""
Tongue Fabrication Structure — Multi-point activation geometry.

A tongue activation is NOT a scalar. It is a fabrication of simultaneous
layers that cannot be decomposed without losing the function.

"We cannot make a language less than the sum of its true composition
 even if its parts are less than the function they are serving."

Each tongue token carries at minimum 6 fabrication points:
  1. OPCODE    — what computation does it represent (byte layer)
  2. GRAMMAR   — where does it sit in evaluation order (position layer)
  3. FREQUENCY — what physical resonance does it carry (Hz layer)
  4. GROUND    — how anchored is it to verifiable reality (grounding layer)
  5. AUDIENCE  — who is it aimed at (vector layer)
  6. PATH      — how did the model reach it (emotional/analytical)

The old model: tongue = scalar (KO = 0.7)
The new model: tongue = fabrication point in 6D sub-manifold

This matters because:
  - A scalar can't distinguish "buy" in customer context from "buy" in lore context
  - A fabrication structure CAN, because the grounding and audience layers differ
    even when the opcode and frequency layers are identical
  - The glass box profiler showed that Polly's failure was a COLLAPSED GEOMETRY —
    all 6 layers squashed to 1 number, destroying the information needed for
    correct pathfinding
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

PHI = (1 + math.sqrt(5)) / 2

# ---------------------------------------------------------------------------
# Evaluation orders — from the Tongue Turing Test
# ---------------------------------------------------------------------------


class EvalOrder(Enum):
    """Each tongue's grammar maps to a programming paradigm's evaluation order."""

    VSO = "vso"  # Kor'aelin = Lisp (verb-subject-object, prefix)
    SVO = "svo"  # Avali = Python (subject-verb-object, infix OOP)
    SOV = "sov"  # Runethic = Forth (subject-object-verb, postfix stack)
    V2 = "v2"  # Cassisivadan = SQL (verb-second, declarative)
    OSV = "osv"  # Umbroth = Assembly (object-subject-verb, dest-first)
    SOV_FORGE = "sov_forge"  # Draumric = Make (subject-object-verb, target-deps)


TONGUE_EVAL_ORDER = {
    "KO": EvalOrder.VSO,
    "AV": EvalOrder.SVO,
    "RU": EvalOrder.SOV,
    "CA": EvalOrder.V2,
    "UM": EvalOrder.OSV,
    "DR": EvalOrder.SOV_FORGE,
}

# Base frequencies from the Turing test (Hz)
TONGUE_BASE_FREQ = {
    "KO": 440.00,  # A4 — intent rings at concert pitch
    "AV": 523.25,  # C5 — wisdom resonates higher
    "RU": 329.63,  # E4 — governance grounds lower
    "CA": 659.25,  # E5 — compute vibrates fast
    "UM": 293.66,  # D4 — security holds low
    "DR": 392.00,  # G4 — structure sits in the middle
}

# ---------------------------------------------------------------------------
# Frequency is not one thing — it is color AND sound AND emotion
# simultaneously. A single Hz value is three modalities compressed.
# ---------------------------------------------------------------------------

# Sound → Color mapping via wavelength
# Audible Hz mapped to visible spectrum nm via octave transposition:
#   Take the Hz, double it ~40 times to reach THz range (visible light),
#   then convert to nanometers. Each tongue lands on a distinct hue.
TONGUE_COLOR = {
    "KO": {"nm": 620, "hex": "#FF4500", "name": "orange-red"},  # Intent burns hot
    "AV": {"nm": 570, "hex": "#CCCC00", "name": "yellow"},  # Wisdom illuminates
    "RU": {"nm": 510, "hex": "#00CC66", "name": "green"},  # Governance grows
    "CA": {"nm": 470, "hex": "#0066FF", "name": "blue"},  # Compute is precise
    "UM": {"nm": 430, "hex": "#6600CC", "name": "violet"},  # Security hides deep
    "DR": {"nm": 550, "hex": "#88CC00", "name": "yellow-green"},  # Structure bridges
}

# Emotional valence per tongue — the affective dimension the frequency carries
# Each tongue has a primary emotion and its intensity on [-1, 1] axes:
#   arousal:  -1 = calm/still    → +1 = excited/urgent
#   valence:  -1 = negative/dark → +1 = positive/warm
#   dominance: -1 = yielding     → +1 = commanding
TONGUE_EMOTION = {
    "KO": {"primary": "determination", "arousal": 0.8, "valence": 0.3, "dominance": 0.9},
    "AV": {"primary": "contemplation", "arousal": -0.2, "valence": 0.7, "dominance": 0.3},
    "RU": {"primary": "vigilance", "arousal": 0.4, "valence": 0.0, "dominance": 0.7},
    "CA": {"primary": "precision", "arousal": 0.3, "valence": 0.2, "dominance": 0.5},
    "UM": {"primary": "wariness", "arousal": 0.6, "valence": -0.3, "dominance": 0.6},
    "DR": {"primary": "patience", "arousal": -0.3, "valence": 0.4, "dominance": 0.4},
}


@dataclass
class FrequencyTriad:
    """
    Frequency decomposed into its three simultaneous modalities.

    A tongue's frequency is not just Hz — it is the SAME energy
    expressed as sound (audible), color (visible), and emotion (felt).
    Together they form the full corpus of human expression.

    sound_hz: The audible frequency (from Tongue Turing Test)
    color_nm: The visible wavelength in nanometers
    color_hex: Hex color code for rendering
    color_name: Human-readable color name
    emotion_primary: The dominant emotional quality
    arousal: Emotional arousal axis [-1, 1]
    valence: Emotional valence axis [-1, 1]
    dominance: Emotional dominance axis [-1, 1]
    harmonic: Which harmonic of the base frequency (1=fundamental)
    """

    sound_hz: float = 440.0
    color_nm: int = 620
    color_hex: str = "#FF4500"
    color_name: str = "orange-red"
    emotion_primary: str = "determination"
    arousal: float = 0.0
    valence: float = 0.0
    dominance: float = 0.0
    harmonic: int = 1

    def effective_hz(self) -> float:
        """Actual sounding frequency including harmonic."""
        return self.sound_hz * self.harmonic

    def emotional_magnitude(self) -> float:
        """Overall emotional intensity (distance from neutral)."""
        return math.sqrt(self.arousal**2 + self.valence**2 + self.dominance**2)

    def is_warm(self) -> bool:
        """Warm colors (red/orange/yellow) and positive valence."""
        return self.color_nm >= 570 or self.valence > 0.3

    def is_cool(self) -> bool:
        """Cool colors (blue/violet) and lower arousal."""
        return self.color_nm <= 490 and self.arousal < 0.3

    def as_vector(self) -> list[float]:
        """7D frequency vector: [hz_norm, nm_norm, arousal, valence, dominance, harmonic_norm, magnitude]."""
        return [
            self.sound_hz / 660.0,
            self.color_nm / 700.0,
            self.arousal,
            self.valence,
            self.dominance,
            min(self.harmonic, 4) / 4.0,
            self.emotional_magnitude(),
        ]

    @classmethod
    def for_tongue(cls, tongue: str, harmonic: int = 1) -> FrequencyTriad:
        """Build a complete frequency triad for a tongue code."""
        hz = TONGUE_BASE_FREQ.get(tongue, 440.0)
        color = TONGUE_COLOR.get(tongue, {"nm": 620, "hex": "#FF4500", "name": "orange-red"})
        emo = TONGUE_EMOTION.get(tongue, {"primary": "neutral", "arousal": 0, "valence": 0, "dominance": 0})
        return cls(
            sound_hz=hz,
            color_nm=color["nm"],
            color_hex=color["hex"],
            color_name=color["name"],
            emotion_primary=emo["primary"],
            arousal=emo["arousal"],
            valence=emo["valence"],
            dominance=emo["dominance"],
            harmonic=harmonic,
        )


# ---------------------------------------------------------------------------
# Fabrication Point — one "atom" in the tongue's crystal structure
# ---------------------------------------------------------------------------


@dataclass
class FabricationPoint:
    """
    A single point in a tongue's fabrication structure.

    This is the minimum unit of tongue activation — NOT a scalar,
    but a 6-dimensional point in the tongue's internal manifold.

    Think of it like an atom in a crystal: the crystal (tongue) is
    made of many atoms (fabrication points), and the arrangement
    of atoms determines the crystal's properties.
    """

    # Layer 1: OPCODE — what is being computed
    opcode: int = 0x00  # Byte value (0x00-0xFF)
    opcode_category: str = ""  # functional/noun/verb/modifier
    opcode_name: str = ""  # Human-readable: ADD, MOV, CMP, etc.

    # Layer 2: GRAMMAR — evaluation position
    position: int = 0  # Where in the evaluation sequence (0=first)
    eval_order: EvalOrder = EvalOrder.VSO

    # Layer 3: FREQUENCY — tri-modal resonance (color + sound + emotion)
    # Frequency is not a scalar. It is simultaneously:
    #   - SOUND: audible Hz from the Tongue Turing Test
    #   - COLOR: visible wavelength (nm) mapped from octave transposition
    #   - EMOTION: affective vector (arousal, valence, dominance)
    frequency: FrequencyTriad = field(default_factory=FrequencyTriad)

    # Layer 4: GROUND — reality anchoring
    grounding: float = 0.5  # 0=pure fiction, 1=verifiable fact
    referent: str = ""  # What real-world thing does this point to (if any)

    # Layer 5: AUDIENCE — who is this for
    audience_vector: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    # [customer, lore_seeker, developer, self]

    # Layer 6: PATH — how was this reached
    emotional_weight: float = 0.5  # 0=pure analytical, 1=pure emotional
    path_confidence: float = 0.5  # How certain is the path classification

    def effective_frequency(self) -> float:
        """Actual sounding frequency including harmonic."""
        return self.frequency.effective_hz()

    @property
    def frequency_hz(self) -> float:
        """Backwards-compat accessor for the sound component."""
        return self.frequency.sound_hz

    def is_grounded(self) -> bool:
        """Is this point anchored to reality?"""
        return self.grounding > 0.6

    def is_emotional(self) -> bool:
        """Did the model reach this point via emotional pathfinding?"""
        return self.emotional_weight > 0.6

    def fabrication_vector(self) -> list[float]:
        """Full 12D vector for this fabrication point.

        Old 6D collapsed frequency to one number. New 12D preserves
        the tri-modal structure: sound + color + emotion (3+1+3 = 7
        frequency dims) replacing the single Hz dimension.

        Layout: [opcode, position, sound_hz, color_nm, arousal, valence,
                 dominance, harmonic, grounding, audience_mean, emotional_weight,
                 freq_magnitude]
        """
        fv = self.frequency.as_vector()
        return [
            self.opcode / 255.0,  # [0] normalized opcode
            self.position / 3.0,  # [1] normalized position
            fv[0],  # [2] normalized sound Hz
            fv[1],  # [3] normalized color nm
            fv[2],  # [4] arousal
            fv[3],  # [5] valence
            fv[4],  # [6] dominance
            fv[5],  # [7] harmonic norm
            self.grounding,  # [8] grounding
            sum(self.audience_vector) / max(len(self.audience_vector), 1),  # [9] audience mean
            self.emotional_weight,  # [10] path emotional weight
            fv[6],  # [11] emotional magnitude
        ]


# ---------------------------------------------------------------------------
# Tongue Fabrication — the full multi-point structure of a tongue activation
# ---------------------------------------------------------------------------


@dataclass
class TongueFabrication:
    """
    Multi-point fabrication structure for a single tongue.

    Instead of KO = 0.7 (scalar), this is:
    KO = [FabricationPoint, FabricationPoint, FabricationPoint, ...]

    Each point is a different aspect of how the tongue was activated.
    The ARRANGEMENT of points (their relative positions in 6D space)
    determines the tongue's behavior — just like a crystal's properties
    come from atomic arrangement, not just atomic identity.
    """

    tongue: str = "KO"
    points: list[FabricationPoint] = field(default_factory=list)

    @property
    def scalar(self) -> float:
        """Collapse to scalar for backwards compatibility.

        THIS IS THE INFORMATION LOSS that caused Polly's failure.
        We keep it for compat but it's the wrong representation.
        """
        if not self.points:
            return 0.0
        return sum(p.grounding * (1 - p.emotional_weight) for p in self.points) / len(self.points)

    @property
    def fabrication_depth(self) -> int:
        """How many fabrication points does this activation have?"""
        return len(self.points)

    @property
    def grounding_ratio(self) -> float:
        """What fraction of fabrication points are grounded in reality?"""
        if not self.points:
            return 0.0
        return sum(1 for p in self.points if p.is_grounded()) / len(self.points)

    @property
    def emotional_ratio(self) -> float:
        """What fraction of fabrication points were reached emotionally?"""
        if not self.points:
            return 0.0
        return sum(1 for p in self.points if p.is_emotional()) / len(self.points)

    @property
    def dominant_audience(self) -> str:
        """Who is the composite activation aimed at?"""
        if not self.points:
            return "unknown"
        totals = [0.0, 0.0, 0.0, 0.0]
        for p in self.points:
            for i, v in enumerate(p.audience_vector):
                totals[i] += v
        labels = ["customer", "lore_seeker", "developer", "self"]
        return labels[totals.index(max(totals))]

    def centroid(self) -> list[float]:
        """Average position in 12D fabrication space."""
        if not self.points:
            return [0.0] * 12
        vecs = [p.fabrication_vector() for p in self.points]
        n = len(vecs)
        dim = len(vecs[0])
        return [sum(v[i] for v in vecs) / n for i in range(dim)]

    def spread(self) -> float:
        """How dispersed are the fabrication points?

        High spread = tongue activated for multiple reasons simultaneously.
        Low spread = coherent single-purpose activation.
        """
        if len(self.points) < 2:
            return 0.0
        c = self.centroid()
        vecs = [p.fabrication_vector() for p in self.points]
        dim = len(c)
        return math.sqrt(sum(sum((v[i] - c[i]) ** 2 for i in range(dim)) for v in vecs) / len(vecs))

    def dominant_color(self) -> str:
        """What color is this tongue expressing most strongly?"""
        if not self.points:
            return TONGUE_COLOR.get(self.tongue, {}).get("name", "unknown")
        # Weighted by path confidence
        total_w = sum(p.path_confidence for p in self.points) or 1.0
        weighted_nm = sum(p.frequency.color_nm * p.path_confidence for p in self.points) / total_w
        # Find closest tongue color
        closest = min(TONGUE_COLOR.items(), key=lambda kv: abs(kv[1]["nm"] - weighted_nm))
        return closest[1]["name"]

    def emotional_center(self) -> dict:
        """Average emotional state across all fabrication points."""
        if not self.points:
            emo = TONGUE_EMOTION.get(self.tongue, {"primary": "neutral", "arousal": 0, "valence": 0, "dominance": 0})
            return emo
        n = len(self.points)
        return {
            "arousal": round(sum(p.frequency.arousal for p in self.points) / n, 3),
            "valence": round(sum(p.frequency.valence for p in self.points) / n, 3),
            "dominance": round(sum(p.frequency.dominance for p in self.points) / n, 3),
        }

    def diagnosis(self) -> dict:
        """Diagnostic summary of this tongue's fabrication."""
        return {
            "tongue": self.tongue,
            "scalar_collapse": round(self.scalar, 3),
            "fabrication_depth": self.fabrication_depth,
            "grounding_ratio": round(self.grounding_ratio, 3),
            "emotional_ratio": round(self.emotional_ratio, 3),
            "dominant_audience": self.dominant_audience,
            "dominant_color": self.dominant_color(),
            "emotional_center": self.emotional_center(),
            "spread": round(self.spread(), 3),
            "centroid": [round(v, 3) for v in self.centroid()],
        }


# ---------------------------------------------------------------------------
# Full Tongue Profile — all 6 tongues with fabrication structures
# ---------------------------------------------------------------------------


@dataclass
class FabricatedTongueProfile:
    """
    Complete tongue profile with multi-point fabrication for all 6 tongues.

    This replaces the old {KO: 0.7, AV: 0.3, ...} scalar profile.
    """

    KO: TongueFabrication = field(default_factory=lambda: TongueFabrication(tongue="KO"))
    AV: TongueFabrication = field(default_factory=lambda: TongueFabrication(tongue="AV"))
    RU: TongueFabrication = field(default_factory=lambda: TongueFabrication(tongue="RU"))
    CA: TongueFabrication = field(default_factory=lambda: TongueFabrication(tongue="CA"))
    UM: TongueFabrication = field(default_factory=lambda: TongueFabrication(tongue="UM"))
    DR: TongueFabrication = field(default_factory=lambda: TongueFabrication(tongue="DR"))

    def scalar_profile(self) -> dict[str, float]:
        """Collapse to scalar dict for backwards compat.

        WARNING: This is the lossy representation that caused Polly's failure.
        """
        return {
            "KO": self.KO.scalar,
            "AV": self.AV.scalar,
            "RU": self.RU.scalar,
            "CA": self.CA.scalar,
            "UM": self.UM.scalar,
            "DR": self.DR.scalar,
        }

    def full_diagnosis(self) -> dict:
        """Full fabrication diagnosis for all 6 tongues."""
        return {
            "KO": self.KO.diagnosis(),
            "AV": self.AV.diagnosis(),
            "RU": self.RU.diagnosis(),
            "CA": self.CA.diagnosis(),
            "UM": self.UM.diagnosis(),
            "DR": self.DR.diagnosis(),
            "total_fabrication_depth": sum(
                t.fabrication_depth for t in [self.KO, self.AV, self.RU, self.CA, self.UM, self.DR]
            ),
            "overall_grounding": round(
                sum(t.grounding_ratio for t in [self.KO, self.AV, self.RU, self.CA, self.UM, self.DR]) / 6, 3
            ),
            "overall_emotional": round(
                sum(t.emotional_ratio for t in [self.KO, self.AV, self.RU, self.CA, self.UM, self.DR]) / 6, 3
            ),
        }

    def by_code(self, code: str) -> TongueFabrication:
        """Get tongue fabrication by code."""
        return getattr(self, code, TongueFabrication(tongue=code))


# ---------------------------------------------------------------------------
# Fabrication Builder — construct multi-point profiles from text
# ---------------------------------------------------------------------------


def fabricate_from_text(text: str, context: str = "unknown") -> FabricatedTongueProfile:
    """
    Build a multi-point fabrication profile from text.

    Instead of counting keywords and returning scalars, this creates
    fabrication points that carry the full 6D structure of each activation.
    """
    profile = FabricatedTongueProfile()
    lower = text.lower()
    words = lower.split()

    # Tongue keyword maps with their fabrication metadata
    tongue_triggers: dict[str, list[tuple[str, float, str]]] = {
        "KO": [
            ("command", 0.3, "imperative verb"),
            ("do", 0.1, "generic action"),
            ("execute", 0.4, "explicit execution"),
            ("run", 0.3, "runtime invocation"),
            ("intent", 0.6, "explicit intent reference"),
            ("buy", 0.7, "purchase intent"),
            ("start", 0.3, "initiation"),
            ("launch", 0.4, "activation"),
            ("action", 0.4, "action reference"),
            ("invoke", 0.5, "invocation"),
        ],
        "AV": [
            ("know", 0.4, "knowledge query"),
            ("learn", 0.5, "learning intent"),
            ("wisdom", 0.7, "explicit wisdom"),
            ("understand", 0.4, "comprehension"),
            ("explain", 0.5, "explanation request"),
            ("teach", 0.5, "teaching request"),
            ("what", 0.2, "information query"),
            ("why", 0.3, "reasoning query"),
            ("how", 0.3, "method query"),
        ],
        "RU": [
            ("rule", 0.5, "governance reference"),
            ("govern", 0.6, "explicit governance"),
            ("policy", 0.5, "policy reference"),
            ("comply", 0.6, "compliance"),
            ("regulate", 0.5, "regulation"),
            ("standard", 0.4, "standards reference"),
            ("own", 0.3, "ownership query"),
            ("who", 0.2, "identity/authority query"),
        ],
        "CA": [
            ("compute", 0.6, "computation"),
            ("calculate", 0.5, "calculation"),
            ("algorithm", 0.5, "algorithm reference"),
            ("function", 0.4, "function reference"),
            ("math", 0.5, "mathematics"),
            ("formula", 0.5, "formula reference"),
            ("price", 0.5, "numerical value query"),
            ("cost", 0.5, "numerical value query"),
            ("$", 0.6, "currency symbol"),
        ],
        "UM": [
            ("secure", 0.5, "security reference"),
            ("protect", 0.5, "protection"),
            ("safe", 0.4, "safety"),
            ("threat", 0.5, "threat reference"),
            ("attack", 0.5, "attack reference"),
            ("trust", 0.4, "trust reference"),
        ],
        "DR": [
            ("structure", 0.5, "structure reference"),
            ("build", 0.5, "construction"),
            ("design", 0.5, "design reference"),
            ("pattern", 0.4, "pattern reference"),
            ("framework", 0.5, "framework reference"),
            ("system", 0.4, "system reference"),
            ("site", 0.3, "website reference"),
            ("page", 0.3, "webpage reference"),
        ],
    }

    # Detect context type for grounding
    is_purchase_context = any(w in lower for w in ["buy", "purchase", "price", "cost", "store", "shop", "$"])
    is_lore_context = any(w in lower for w in ["lore", "story", "quest", "magic", "spell", "potion"])
    is_meta_context = any(w in lower for w in ["who are you", "who made", "who owns", "your creator"])

    for tongue_code, triggers in tongue_triggers.items():
        fab = profile.by_code(tongue_code)
        _base_freq = TONGUE_BASE_FREQ[tongue_code]
        eval_order = TONGUE_EVAL_ORDER[tongue_code]

        for keyword, base_weight, referent in triggers:
            if keyword not in lower:
                continue

            # Count occurrences for harmonic
            count = lower.count(keyword)

            # Determine grounding based on context
            if is_purchase_context and keyword in ("buy", "price", "cost", "$", "store"):
                grounding = 0.9  # High grounding — this is about real things
            elif is_lore_context:
                grounding = 0.2  # Low grounding — fiction territory
            elif is_meta_context:
                grounding = 0.7  # Medium-high — factual question about identity
            else:
                grounding = 0.5  # Neutral

            # Audience vector: [customer, lore_seeker, developer, self]
            audience = [0.0, 0.0, 0.0, 0.0]
            if is_purchase_context:
                audience[0] = 0.8
            if is_lore_context:
                audience[1] = 0.8
            if any(w in lower for w in ["api", "code", "function", "deploy"]):
                audience[2] = 0.8
            if is_meta_context:
                audience[3] = 0.6

            # Emotional weight: purchase/meta queries should be LOW emotional
            emotional = 0.3 if (is_purchase_context or is_meta_context) else 0.6

            point = FabricationPoint(
                opcode=hash(keyword) % 256,
                opcode_category="verb" if tongue_code in ("KO", "CA") else "noun",
                opcode_name=keyword.upper(),
                position=words.index(keyword) if keyword in words else 0,
                eval_order=eval_order,
                frequency=FrequencyTriad.for_tongue(tongue_code, harmonic=min(count, 4)),
                grounding=grounding,
                referent=referent,
                audience_vector=audience,
                emotional_weight=emotional,
                path_confidence=base_weight,
            )
            fab.points.append(point)

    return profile
