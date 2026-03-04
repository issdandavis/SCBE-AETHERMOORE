"""
Heart Vault — Literary Device Detection & Metaphor Resolution
===============================================================

Identifies literary devices in text and resolves metaphorical mappings
to emotional/conceptual nodes in the Heart Vault graph.

Supported devices:
    METAPHOR        — X is Y         ("Time is a thief")
    SIMILE          — X is like Y    ("Life is like a box of chocolates")
    PERSONIFICATION — inanimate + human action ("The wind whispered")
    HYPERBOLE       — exaggerated claim ("I've told you a million times")
    OXYMORON        — contradictory pair ("deafening silence")
    ALLITERATION    — repeated initial consonants ("Peter Piper picked")
    IRONY           — opposite of literal meaning (contextual)
    PROVERB         — traditional wisdom statement

Each detected device produces a ``LiteraryHit`` that can be fed into the
Heart Vault graph as a LITERARY node with edges to EMOTION and CONCEPT nodes.

Integrates with:
    - SCBE Layer 1–2 (Complex Context metadata)
    - Heart Vault graph (NodeType.LITERARY)
    - Semantic Antivirus (safety score before ingesting external literary data)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .emotions import EMOTION_LIBRARY, EmotionSpec, classify_emotion


# ---------------------------------------------------------------------------
#  Literary device types
# ---------------------------------------------------------------------------

class LiteraryDevice(str, Enum):
    METAPHOR = "metaphor"
    SIMILE = "simile"
    PERSONIFICATION = "personification"
    HYPERBOLE = "hyperbole"
    OXYMORON = "oxymoron"
    ALLITERATION = "alliteration"
    IRONY = "irony"
    PROVERB = "proverb"


@dataclass
class LiteraryHit:
    """A detected literary device in a text span."""
    device: LiteraryDevice
    text: str                        # The matched text span
    confidence: float                # [0, 1]
    tenor: Optional[str] = None      # The subject being described (metaphor)
    vehicle: Optional[str] = None    # The image used to describe it (metaphor)
    emotion_hint: Optional[str] = None  # Suggested emotion name


# ---------------------------------------------------------------------------
#  Metaphor concept map — common tenor→vehicle→emotion mappings
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MetaphorMapping:
    """A known metaphorical mapping from tenor to vehicle to emotion."""
    tenor: str
    vehicle: str
    valence: float
    arousal: float
    emotion: str


METAPHOR_MAP: Dict[str, List[MetaphorMapping]] = {}

_RAW_METAPHORS: List[Tuple[str, str, float, float, str]] = [
    # tenor,    vehicle,    valence, arousal, emotion
    ("time",    "thief",      -0.7,   0.5,   "loss"),
    ("time",    "river",      -0.1,  -0.1,   "nostalgia"),
    ("time",    "healer",      0.4,  -0.2,   "hope"),
    ("life",    "journey",     0.3,   0.3,   "anticipation"),
    ("life",    "stage",       0.1,   0.2,   "surprise"),
    ("life",    "dream",       0.2,  -0.1,   "nostalgia"),
    ("life",    "battle",     -0.3,   0.7,   "fear"),
    ("love",    "fire",        0.6,   0.8,   "love"),
    ("love",    "rose",        0.7,   0.3,   "joy"),
    ("love",    "poison",     -0.5,   0.6,   "remorse"),
    ("death",   "sleep",      -0.2,  -0.5,   "pensiveness"),
    ("death",   "journey",    -0.3,  -0.2,   "sadness"),
    ("death",   "shadow",     -0.6,   0.2,   "fear"),
    ("anger",   "fire",       -0.5,   0.9,   "rage"),
    ("anger",   "storm",      -0.6,   0.8,   "anger"),
    ("hope",    "light",       0.7,   0.3,   "optimism"),
    ("hope",    "anchor",      0.5,  -0.1,   "trust"),
    ("knowledge","light",      0.6,   0.2,   "joy"),
    ("ignorance","darkness",  -0.4,  -0.2,   "sadness"),
    ("freedom", "bird",        0.8,   0.5,   "ecstasy"),
    ("justice", "scales",      0.3,   0.0,   "trust"),
    ("power",   "lion",        0.2,   0.7,   "admiration"),
    ("greed",   "hunger",     -0.5,   0.6,   "disgust"),
    ("memory",  "ghost",      -0.2,   0.2,   "nostalgia"),
    ("truth",   "mirror",      0.4,   0.1,   "trust"),
    ("lies",    "web",        -0.6,   0.3,   "contempt"),
    ("sorrow",  "ocean",      -0.5,  -0.1,   "grief"),
    ("joy",     "sunshine",    0.8,   0.4,   "ecstasy"),
    ("fear",    "shadow",     -0.6,   0.5,   "fear"),
    ("courage", "flame",       0.5,   0.7,   "admiration"),
]

for _tenor, _vehicle, _v, _a, _emotion in _RAW_METAPHORS:
    mapping = MetaphorMapping(_tenor, _vehicle, _v, _a, _emotion)
    METAPHOR_MAP.setdefault(_tenor, []).append(mapping)


# ---------------------------------------------------------------------------
#  Oxymoron pairs
# ---------------------------------------------------------------------------

OXYMORON_PAIRS: List[Tuple[str, str]] = [
    ("deafening", "silence"),
    ("bitter", "sweet"),
    ("living", "dead"),
    ("cruel", "kindness"),
    ("dark", "light"),
    ("old", "new"),
    ("open", "secret"),
    ("pretty", "ugly"),
    ("awfully", "good"),
    ("alone", "together"),
    ("clearly", "confused"),
    ("only", "choice"),
    ("found", "missing"),
    ("jumbo", "shrimp"),
    ("virtual", "reality"),
]


# ---------------------------------------------------------------------------
#  Personification verbs (actions typically performed by humans)
# ---------------------------------------------------------------------------

PERSONIFICATION_VERBS = frozenset({
    "whispered", "sang", "danced", "cried", "laughed", "wept",
    "screamed", "sighed", "moaned", "embraced", "kissed", "devoured",
    "beckoned", "caressed", "swallowed", "breathed", "slept", "woke",
    "marched", "crept", "ran", "shouted", "murmured", "groaned",
})

# Inanimate subjects commonly personified
PERSONIFICATION_SUBJECTS = frozenset({
    "wind", "sun", "moon", "stars", "sea", "ocean", "river",
    "mountain", "tree", "flower", "shadow", "darkness", "light",
    "time", "death", "fate", "nature", "storm", "thunder",
    "rain", "fire", "earth", "sky", "clouds", "fog",
})


# ---------------------------------------------------------------------------
#  Pattern-based literary device detection
# ---------------------------------------------------------------------------

# Metaphor: "X is a Y", "X is Y", "X was a Y"
_METAPHOR_RE = re.compile(
    r"\b(\w+)\s+(?:is|was|are|were)\s+(?:a\s+)?(\w+)\b",
    re.IGNORECASE,
)

# Simile: "like a Y", "as Y as"
_SIMILE_RE = re.compile(
    r"\b(?:like\s+(?:a\s+)?(\w+)|as\s+(\w+)\s+as)\b",
    re.IGNORECASE,
)

# Hyperbole: number-based exaggeration
_HYPERBOLE_RE = re.compile(
    r"\b(?:million|billion|trillion|thousand|forever|never|always|every\s+single)\b",
    re.IGNORECASE,
)

# Alliteration: 3+ words starting with the same consonant
_ALLITERATION_RE = re.compile(
    r"\b(([bcdfghjklmnpqrstvwxyz])\w+\s+\2\w+\s+\2\w+)",
    re.IGNORECASE,
)


def detect_literary_devices(text: str) -> List[LiteraryHit]:
    """
    Scan text for literary devices using pattern matching.

    Returns a list of ``LiteraryHit`` objects sorted by confidence
    (highest first).  For production use, these should be filtered
    through the Runethic quality gate (quality_score >= threshold).
    """
    hits: List[LiteraryHit] = []
    text_lower = text.lower()

    # --- Metaphors ---
    for m in _METAPHOR_RE.finditer(text):
        tenor = m.group(1).lower()
        vehicle = m.group(2).lower()
        # Check if this is a known metaphor mapping
        mappings = METAPHOR_MAP.get(tenor, [])
        for mp in mappings:
            if mp.vehicle == vehicle:
                hits.append(LiteraryHit(
                    device=LiteraryDevice.METAPHOR,
                    text=m.group(0),
                    confidence=0.9,
                    tenor=tenor,
                    vehicle=vehicle,
                    emotion_hint=mp.emotion,
                ))
                break
        else:
            # Unknown mapping — still report with lower confidence
            if tenor != vehicle:
                hits.append(LiteraryHit(
                    device=LiteraryDevice.METAPHOR,
                    text=m.group(0),
                    confidence=0.5,
                    tenor=tenor,
                    vehicle=vehicle,
                ))

    # --- Similes ---
    for m in _SIMILE_RE.finditer(text):
        vehicle = (m.group(1) or m.group(2) or "").lower()
        if vehicle:
            hits.append(LiteraryHit(
                device=LiteraryDevice.SIMILE,
                text=m.group(0),
                confidence=0.7,
                vehicle=vehicle,
            ))

    # --- Personification ---
    words = text_lower.split()
    for i, word in enumerate(words):
        if word.rstrip(".,!?;:") in PERSONIFICATION_VERBS:
            # Check if preceding word is an inanimate subject
            if i > 0 and words[i - 1].rstrip(".,!?;:") in PERSONIFICATION_SUBJECTS:
                span = f"{words[i-1]} {word}"
                hits.append(LiteraryHit(
                    device=LiteraryDevice.PERSONIFICATION,
                    text=span,
                    confidence=0.8,
                ))

    # --- Hyperbole ---
    for m in _HYPERBOLE_RE.finditer(text):
        # Grab surrounding context (up to 5 words each side)
        start = max(0, m.start() - 40)
        end = min(len(text), m.end() + 40)
        hits.append(LiteraryHit(
            device=LiteraryDevice.HYPERBOLE,
            text=text[start:end].strip(),
            confidence=0.6,
        ))

    # --- Oxymorons ---
    for w1, w2 in OXYMORON_PAIRS:
        if w1 in text_lower and w2 in text_lower:
            hits.append(LiteraryHit(
                device=LiteraryDevice.OXYMORON,
                text=f"{w1} {w2}",
                confidence=0.85,
            ))

    # --- Alliteration ---
    for m in _ALLITERATION_RE.finditer(text):
        hits.append(LiteraryHit(
            device=LiteraryDevice.ALLITERATION,
            text=m.group(0),
            confidence=0.7,
        ))

    # Sort by confidence descending
    hits.sort(key=lambda h: h.confidence, reverse=True)
    return hits


def resolve_metaphor(
    tenor: str,
    vehicle: str,
) -> Optional[Tuple[MetaphorMapping, EmotionSpec]]:
    """
    Resolve a tenor–vehicle metaphor to its emotional mapping.

    Returns the ``MetaphorMapping`` and the closest ``EmotionSpec``,
    or None if no mapping is known.
    """
    mappings = METAPHOR_MAP.get(tenor.lower(), [])
    for mp in mappings:
        if mp.vehicle == vehicle.lower():
            emotion = classify_emotion(mp.valence, mp.arousal)
            return (mp, emotion)
    return None
