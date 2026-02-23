"""
Heart Vault — Emotion Taxonomy & Poincaré Ball Mapping
========================================================

Maps emotions to valence–arousal coordinates and projects them into the
Poincaré Ball model used by SCBE Layers 3–4.  This gives the governance
pipeline *geometric* access to emotional states.

Valence–Arousal Model (Russell's Circumplex):
    valence:  [-1, +1]  negative ← → positive
    arousal:  [-1, +1]  calm     ← → excited

Poincaré Ball Projection:
    The (valence, arousal) pair is mapped to hyperbolic coordinates inside
    the unit disk.  Points near the boundary represent *extreme* emotions;
    the center is neutral.  This aligns with the SCBE Poincaré Ball
    where boundary = high deviation = higher governance scrutiny.

Emotion Categories (Plutchik's wheel extended):
    8 primary emotions × 3 intensity levels = 24 named emotions,
    plus composite emotions from adjacent primaries.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
#  Emotion taxonomy
# ---------------------------------------------------------------------------

class EmotionFamily(str, Enum):
    """Plutchik's 8 primary emotion families."""
    JOY = "joy"
    TRUST = "trust"
    FEAR = "fear"
    SURPRISE = "surprise"
    SADNESS = "sadness"
    DISGUST = "disgust"
    ANGER = "anger"
    ANTICIPATION = "anticipation"


class EmotionIntensity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class EmotionSpec:
    """A named emotion with circumplex coordinates."""
    name: str
    family: EmotionFamily
    intensity: EmotionIntensity
    valence: float   # [-1, +1]
    arousal: float   # [-1, +1]


# ---------------------------------------------------------------------------
#  Canonical emotion library (Plutchik × 3 intensities)
# ---------------------------------------------------------------------------

EMOTION_LIBRARY: Dict[str, EmotionSpec] = {}

_RAW_EMOTIONS: List[Tuple[str, str, str, float, float]] = [
    # --- Joy family ---
    ("serenity",     "joy",           "low",    0.4,  -0.1),
    ("joy",          "joy",           "medium", 0.8,   0.3),
    ("ecstasy",      "joy",           "high",   1.0,   0.7),
    # --- Trust family ---
    ("acceptance",   "trust",         "low",    0.3,  -0.2),
    ("trust",        "trust",         "medium", 0.5,   0.0),
    ("admiration",   "trust",         "high",   0.7,   0.3),
    # --- Fear family ---
    ("apprehension", "fear",          "low",   -0.3,   0.3),
    ("fear",         "fear",          "medium",-0.6,   0.6),
    ("terror",       "fear",          "high",  -0.9,   0.9),
    # --- Surprise family ---
    ("distraction",  "surprise",      "low",    0.0,   0.2),
    ("surprise",     "surprise",      "medium", 0.1,   0.6),
    ("amazement",    "surprise",      "high",   0.2,   0.9),
    # --- Sadness family ---
    ("pensiveness",  "sadness",       "low",   -0.3,  -0.3),
    ("sadness",      "sadness",       "medium",-0.6,  -0.2),
    ("grief",        "sadness",       "high",  -0.9,  -0.1),
    # --- Disgust family ---
    ("boredom",      "disgust",       "low",   -0.2,  -0.4),
    ("disgust",      "disgust",       "medium",-0.5,   0.1),
    ("loathing",     "disgust",       "high",  -0.8,   0.4),
    # --- Anger family ---
    ("annoyance",    "anger",         "low",   -0.3,   0.3),
    ("anger",        "anger",         "medium",-0.6,   0.7),
    ("rage",         "anger",         "high",  -0.9,   1.0),
    # --- Anticipation family ---
    ("interest",     "anticipation",  "low",    0.3,   0.3),
    ("anticipation", "anticipation",  "medium", 0.4,   0.5),
    ("vigilance",    "anticipation",  "high",   0.5,   0.8),
]

for _name, _family, _intensity, _v, _a in _RAW_EMOTIONS:
    EMOTION_LIBRARY[_name] = EmotionSpec(
        name=_name,
        family=EmotionFamily(_family),
        intensity=EmotionIntensity(_intensity),
        valence=_v,
        arousal=_a,
    )

# Composite emotions (adjacent Plutchik primaries)
_COMPOSITES: List[Tuple[str, str, str, float, float]] = [
    ("love",         "joy",     "medium",  0.9,   0.5),
    ("submission",   "trust",   "medium",  0.1,  -0.3),
    ("awe",          "fear",    "medium", -0.1,   0.7),
    ("disapproval",  "sadness", "medium", -0.5,   0.1),
    ("remorse",      "sadness", "medium", -0.7,   0.2),
    ("contempt",     "disgust", "medium", -0.6,   0.3),
    ("aggressiveness","anger",  "medium", -0.4,   0.8),
    ("optimism",     "anticipation","medium", 0.6, 0.4),
    ("nostalgia",    "sadness", "low",    -0.1,  -0.4),
    ("hope",         "anticipation","low",  0.5,  0.2),
    ("anxiety",      "fear",    "low",    -0.4,   0.5),
    ("guilt",        "sadness", "low",    -0.5,   0.3),
]

for _name, _family, _intensity, _v, _a in _COMPOSITES:
    EMOTION_LIBRARY[_name] = EmotionSpec(
        name=_name,
        family=EmotionFamily(_family),
        intensity=EmotionIntensity(_intensity),
        valence=_v,
        arousal=_a,
    )


# ---------------------------------------------------------------------------
#  Poincaré Ball projection
# ---------------------------------------------------------------------------

def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def valence_arousal_to_poincare(
    valence: float,
    arousal: float,
    curvature: float = 1.0,
) -> Tuple[float, float]:
    """
    Project valence–arousal onto the Poincaré disk.

    The emotional intensity (distance from origin) maps to hyperbolic
    distance, so extreme emotions sit near the disk boundary where
    SCBE governance scrutiny is highest.

    Args:
        valence: [-1, +1]
        arousal: [-1, +1]
        curvature: negative curvature magnitude (default 1.0)

    Returns:
        (x, y) inside the unit disk  (||p|| < 1)
    """
    v = _clamp(valence)
    a = _clamp(arousal)

    # Euclidean radius = emotional intensity
    r_euclidean = math.sqrt(v * v + a * a)
    if r_euclidean < 1e-10:
        return (0.0, 0.0)

    # Cap at 0.99 to stay strictly inside the disk
    r_euclidean = min(r_euclidean, math.sqrt(2.0))

    # Map [0, sqrt(2)] → [0, 0.95] via tanh (natural for hyperbolic geometry)
    r_poincare = math.tanh(curvature * r_euclidean / math.sqrt(2.0)) * 0.95

    # Direction from (valence, arousal)
    angle = math.atan2(a, v)
    x = r_poincare * math.cos(angle)
    y = r_poincare * math.sin(angle)
    return (x, y)


def poincare_distance(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
) -> float:
    """
    Compute hyperbolic distance between two points in the Poincaré disk.

    d(p, q) = arcosh(1 + 2 * ||p - q||² / ((1 - ||p||²)(1 - ||q||²)))
    """
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    sq_dist = dx * dx + dy * dy

    norm_p = p1[0] ** 2 + p1[1] ** 2
    norm_q = p2[0] ** 2 + p2[1] ** 2

    denom = (1.0 - norm_p) * (1.0 - norm_q)
    if denom < 1e-10:
        return float("inf")

    arg = 1.0 + 2.0 * sq_dist / denom
    return math.acosh(max(1.0, arg))


def emotion_to_poincare(emotion_name: str) -> Optional[Tuple[float, float]]:
    """Look up an emotion and return its Poincaré disk coordinates."""
    spec = EMOTION_LIBRARY.get(emotion_name)
    if not spec:
        return None
    return valence_arousal_to_poincare(spec.valence, spec.arousal)


def emotional_distance(name1: str, name2: str) -> Optional[float]:
    """Compute the hyperbolic distance between two named emotions."""
    p1 = emotion_to_poincare(name1)
    p2 = emotion_to_poincare(name2)
    if p1 is None or p2 is None:
        return None
    return poincare_distance(p1, p2)


def classify_emotion(valence: float, arousal: float) -> EmotionSpec:
    """Find the closest canonical emotion to a (valence, arousal) point."""
    best: Optional[EmotionSpec] = None
    best_dist = float("inf")
    for spec in EMOTION_LIBRARY.values():
        dv = valence - spec.valence
        da = arousal - spec.arousal
        dist = math.sqrt(dv * dv + da * da)
        if dist < best_dist:
            best_dist = dist
            best = spec
    assert best is not None
    return best
