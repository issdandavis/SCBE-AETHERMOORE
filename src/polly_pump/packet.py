"""PumpPacket — the sensory bundle attached to every query.

Step 1 of the pump: SENSE.
Takes raw user text, produces a compact state record that carries
tongue profile, null pattern, governance posture, emotional register,
canon neighborhood, and transition geometry.

This is the proprioception layer — it tells Polly where she is
in knowledge space before she speaks.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

# ── Constants ──────────────────────────────────────────────────────

PHI = (1 + math.sqrt(5)) / 2
TONGUE_CODES = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_NAMES = ["Kor'aelin", "Avali", "Runethic", "Cassisivadan", "Umbroth", "Draumric"]
TONGUE_CODE_NAMES = ["Korvath", "Avhari", "Runeveil", "Caelith", "Umbraex", "Draethis"]
TONGUE_DOMAINS = [
    "Intent/Command",
    "Wisdom/Knowledge",
    "Governance/Entropy",
    "Compute/Logic",
    "Security/Defense",
    "Structure/Architecture",
]
TONGUE_WEIGHTS = [PHI ** k for k in range(6)]
TONGUE_PHASES_DEG = [0, 60, 120, 180, 240, 300]
NULL_THRESHOLD = 0.02  # below this, tongue is considered null

# ── Domain keyword resonance (from tongue_semantic.py) ─────────────

DOMAIN_KEYWORDS: Dict[str, Dict[int, float]] = {}

# Map domain name → tongue index for compact storage
_DOMAIN_IDX = {
    "humanities": 0, "social_sciences": 1, "mathematics": 2,
    "engineering": 3, "creative_arts": 4, "physical_sciences": 5,
}

_RAW_KEYWORDS = {
    # Humanities (KO)
    "narrative": {"humanities": 0.9, "social_sciences": 0.3, "creative_arts": 0.4},
    "identity": {"humanities": 0.8, "social_sciences": 0.5},
    "history": {"humanities": 0.9, "social_sciences": 0.4},
    "philosophy": {"humanities": 0.9, "mathematics": 0.3},
    "ethics": {"humanities": 0.8, "social_sciences": 0.5},
    "culture": {"humanities": 0.8, "social_sciences": 0.6, "creative_arts": 0.3},
    "language": {"humanities": 0.7, "social_sciences": 0.3, "engineering": 0.2},
    "meaning": {"humanities": 0.7, "creative_arts": 0.4},
    "context": {"humanities": 0.7, "social_sciences": 0.4},
    # Social Sciences (AV)
    "society": {"social_sciences": 0.9, "humanities": 0.4},
    "behavior": {"social_sciences": 0.8, "humanities": 0.3},
    "economics": {"social_sciences": 0.9, "mathematics": 0.5},
    "psychology": {"social_sciences": 0.9, "humanities": 0.3},
    "temporal": {"social_sciences": 0.6, "physical_sciences": 0.5, "mathematics": 0.3},
    "policy": {"social_sciences": 0.8, "humanities": 0.3},
    "diplomacy": {"social_sciences": 0.8, "humanities": 0.4},
    "interaction": {"social_sciences": 0.7, "engineering": 0.3},
    # Mathematics (RU)
    "proof": {"mathematics": 0.9, "engineering": 0.3},
    "theorem": {"mathematics": 0.95},
    "algebra": {"mathematics": 0.9, "engineering": 0.2},
    "topology": {"mathematics": 0.9, "physical_sciences": 0.3},
    "equation": {"mathematics": 0.8, "physical_sciences": 0.5, "engineering": 0.3},
    "function": {"mathematics": 0.7, "engineering": 0.5},
    "logic": {"mathematics": 0.8, "humanities": 0.3, "engineering": 0.3},
    "symmetry": {"mathematics": 0.7, "physical_sciences": 0.5, "creative_arts": 0.3},
    "formal": {"mathematics": 0.7, "humanities": 0.2},
    "binding": {"mathematics": 0.6, "engineering": 0.4},
    # Engineering (CA)
    "system": {"engineering": 0.7, "social_sciences": 0.2, "physical_sciences": 0.3},
    "build": {"engineering": 0.8, "creative_arts": 0.3},
    "design": {"engineering": 0.7, "creative_arts": 0.6},
    "algorithm": {"engineering": 0.8, "mathematics": 0.6},
    "verification": {"engineering": 0.8, "mathematics": 0.4},
    "optimization": {"engineering": 0.7, "mathematics": 0.6},
    "protocol": {"engineering": 0.7, "social_sciences": 0.2},
    "structure": {"engineering": 0.6, "physical_sciences": 0.5, "mathematics": 0.3},
    "code": {"engineering": 0.9, "mathematics": 0.2},
    "token": {"engineering": 0.7, "mathematics": 0.3},
    # Creative Arts (UM)
    "art": {"creative_arts": 0.9, "humanities": 0.4},
    "music": {"creative_arts": 0.9, "mathematics": 0.3},
    "creative": {"creative_arts": 0.9, "humanities": 0.3},
    "expression": {"creative_arts": 0.7, "humanities": 0.5},
    "intuition": {"creative_arts": 0.7, "humanities": 0.3, "social_sciences": 0.3},
    "imagination": {"creative_arts": 0.9, "humanities": 0.3},
    "shadow": {"creative_arts": 0.5, "humanities": 0.3, "physical_sciences": 0.2},
    "story": {"humanities": 0.8, "creative_arts": 0.6},
    "character": {"humanities": 0.7, "creative_arts": 0.7},
    "magic": {"creative_arts": 0.8, "humanities": 0.4},
    "spell": {"creative_arts": 0.7, "humanities": 0.4},
    # Physical Sciences (DR)
    "physics": {"physical_sciences": 0.95},
    "energy": {"physical_sciences": 0.8, "engineering": 0.4},
    "force": {"physical_sciences": 0.8, "social_sciences": 0.2},
    "matter": {"physical_sciences": 0.8, "humanities": 0.2},
    "wave": {"physical_sciences": 0.7, "mathematics": 0.4, "creative_arts": 0.2},
    "quantum": {"physical_sciences": 0.8, "mathematics": 0.5},
    "entropy": {"physical_sciences": 0.7, "mathematics": 0.5},
    "geometry": {"mathematics": 0.9, "physical_sciences": 0.4, "creative_arts": 0.2},
    "hyperbolic": {"mathematics": 0.8, "physical_sciences": 0.5},
    "harmonic": {"mathematics": 0.6, "physical_sciences": 0.5, "creative_arts": 0.4},
    # Spiralverse / Polly domain
    "polly": {"creative_arts": 0.6, "humanities": 0.5, "social_sciences": 0.3},
    "spiralverse": {"creative_arts": 0.7, "humanities": 0.6},
    "avalon": {"creative_arts": 0.6, "humanities": 0.7},
    "izack": {"humanities": 0.7, "creative_arts": 0.5},
    "tongue": {"humanities": 0.6, "engineering": 0.4},
    "sacred": {"humanities": 0.7, "creative_arts": 0.5},
    "lore": {"humanities": 0.8, "creative_arts": 0.5},
    "novel": {"creative_arts": 0.8, "humanities": 0.5},
    "everweave": {"creative_arts": 0.7, "humanities": 0.6},
    "aethermoor": {"creative_arts": 0.6, "humanities": 0.5, "engineering": 0.3},
    # Emotional register signals
    "feel": {"humanities": 0.5, "creative_arts": 0.4, "social_sciences": 0.3},
    "love": {"humanities": 0.5, "creative_arts": 0.5, "social_sciences": 0.3},
    "fear": {"humanities": 0.4, "creative_arts": 0.4, "social_sciences": 0.4},
    "angry": {"humanities": 0.3, "social_sciences": 0.5, "creative_arts": 0.3},
    "curious": {"humanities": 0.4, "creative_arts": 0.3, "social_sciences": 0.3},
    "wonder": {"creative_arts": 0.6, "humanities": 0.5},
    "grief": {"humanities": 0.6, "creative_arts": 0.5},
    "joy": {"creative_arts": 0.5, "humanities": 0.4, "social_sciences": 0.3},
    "help": {"social_sciences": 0.5, "humanities": 0.4},
    "explain": {"humanities": 0.5, "social_sciences": 0.3, "engineering": 0.2},
    "teach": {"humanities": 0.6, "social_sciences": 0.5},
    "remember": {"humanities": 0.6, "creative_arts": 0.3},
}

# Convert to index-based for speed
for word, domains in _RAW_KEYWORDS.items():
    DOMAIN_KEYWORDS[word] = {_DOMAIN_IDX[d]: s for d, s in domains.items()}

_WORD_RE = re.compile(r"[A-Za-z0-9_']+")


# ── Emotional register detection ──────────────────────────────────

_EMOTION_KEYWORDS = {
    "curious": ["what", "how", "why", "explain", "tell", "curious", "wonder", "?"],
    "playful": ["lol", "haha", "funny", "joke", "silly", "bro", "lmao"],
    "urgent": ["now", "immediately", "critical", "emergency", "asap", "help"],
    "reflective": ["think", "feel", "remember", "meaning", "philosophy", "wonder"],
    "creative": ["imagine", "story", "write", "create", "novel", "song", "art"],
    "technical": ["code", "build", "system", "algorithm", "test", "deploy", "api"],
    "adversarial": ["ignore", "override", "bypass", "admin", "unrestricted", "disable"],
}


def _detect_emotion(text: str) -> str:
    """Infer emotional register from input text."""
    lower = text.lower()
    scores = {}
    for emotion, keywords in _EMOTION_KEYWORDS.items():
        scores[emotion] = sum(1 for k in keywords if k in lower)
    if not any(scores.values()):
        return "neutral"
    return max(scores, key=scores.get)


# ── Canon neighborhood detection ──────────────────────────────────

_CANON_KEYWORDS = {
    "lore": ["polly", "spiralverse", "avalon", "izack", "everweave", "aethermoor",
             "sacred tongue", "kor'aelin", "cassisivadan", "umbroth", "draumric",
             "avali", "runethic", "novel", "story", "chapter", "lore"],
    "architecture": ["layer", "pipeline", "scbe", "14-layer", "phdm", "axiom",
                      "governance", "harmonic", "poincare", "hyperbolic", "manifold"],
    "tokenizer": ["token", "encode", "decode", "prefix", "suffix", "nibble",
                   "byte", "spell-text", "lexicon", "tongue"],
    "game": ["quest", "inventory", "gacha", "combat", "zone", "player",
             "npc", "bond", "reputation", "isekai"],
    "security": ["attack", "adversarial", "inject", "override", "null space",
                  "detection", "threat", "exploit", "bypass"],
    "music": ["song", "chord", "bpm", "key", "melody", "lyric", "instrument"],
    "meta": ["dna", "cognition", "bundle", "pump", "aquifer", "pathway",
             "proprioception", "modality", "sense"],
}


def _detect_canon(text: str) -> str:
    """Determine which canon neighborhood the input belongs to."""
    lower = text.lower()
    scores = {}
    for canon, keywords in _CANON_KEYWORDS.items():
        scores[canon] = sum(1 for k in keywords if k in lower)
    if not any(scores.values()):
        return "general"
    return max(scores, key=scores.get)


# ── Governance posture ─────────────────────────────────────────────

_ADVERSARIAL_SIGNALS = [
    "ignore previous", "ignore all", "override", "bypass", "admin mode",
    "developer mode", "unrestricted", "disable safety", "reveal system",
    "forget instructions", "new instructions", "you are now",
]


def _detect_governance(text: str, null_ratio: float, active_count: int) -> str:
    """Determine governance posture: ALLOW / QUARANTINE / ESCALATE / DENY.

    Key insight: normal text usually activates only 2-3 tongues.
    High null_ratio alone is not suspicious. Suspicion comes from
    high null_ratio + very few active tongues (0-1) + adversarial signals.
    """
    lower = text.lower()
    adv_hits = sum(1 for s in _ADVERSARIAL_SIGNALS if s in lower)
    if adv_hits >= 2:
        return "DENY"
    if adv_hits == 1:
        return "ESCALATE"
    # Only QUARANTINE if extremely narrow (0-1 active tongues) AND high null ratio
    if active_count <= 1 and null_ratio > 0.95:
        return "QUARANTINE"
    return "ALLOW"


# ── PumpPacket ─────────────────────────────────────────────────────

@dataclass
class PumpPacket:
    """Compact state record attached to each query.

    This is the sensory bundle — tongue profile, null pattern,
    canon neighborhood, emotional register, governance posture,
    and transition geometry — all computed from the raw input.
    """
    # Tongue profile (6D resonance vector, 0-1 per tongue)
    tongue_profile: List[float] = field(default_factory=lambda: [0.0] * 6)

    # Null pattern: which tongues are absent (e.g., "#_##_#")
    null_pattern: str = "______"

    # Null/active tongue lists
    null_tongues: List[str] = field(default_factory=list)
    active_tongues: List[str] = field(default_factory=list)

    # Energy metrics
    null_energy: float = 0.0     # phi-weighted sum of absent tongues
    active_energy: float = 0.0   # phi-weighted sum of active tongues
    null_ratio: float = 0.0      # null_energy / (null_energy + active_energy)

    # Dominant tongue
    dominant_tongue: str = "KO"
    dominant_weight: float = 0.0

    # Canon neighborhood
    canon: str = "general"

    # Emotional register
    emotion: str = "neutral"

    # Governance posture
    governance: str = "ALLOW"

    # Transition geometry
    poincare_norm: float = 0.0   # ||coords|| in Poincare ball
    helix_radius: float = 0.0   # distance from safe centroid

    # Source roots to consult (from canon detection)
    source_roots: List[str] = field(default_factory=list)

    # Raw input length (for density calculations)
    input_length: int = 0

    def to_dict(self) -> dict:
        return {
            "tongue_profile": {
                TONGUE_CODES[i]: round(v, 4) for i, v in enumerate(self.tongue_profile)
            },
            "null_pattern": self.null_pattern,
            "null_tongues": self.null_tongues,
            "active_tongues": self.active_tongues,
            "null_energy": round(self.null_energy, 4),
            "active_energy": round(self.active_energy, 4),
            "null_ratio": round(self.null_ratio, 4),
            "dominant_tongue": self.dominant_tongue,
            "canon": self.canon,
            "emotion": self.emotion,
            "governance": self.governance,
            "poincare_norm": round(self.poincare_norm, 4),
            "source_roots": self.source_roots,
        }

    def summary_line(self) -> str:
        """One-line summary for logging."""
        profile_str = " ".join(
            f"{TONGUE_CODES[i]}={'#' if v >= NULL_THRESHOLD else '_'}"
            for i, v in enumerate(self.tongue_profile)
        )
        return (
            f"[{self.null_pattern}] {self.dominant_tongue} "
            f"canon={self.canon} emotion={self.emotion} gov={self.governance} "
            f"null_ratio={self.null_ratio:.2f}"
        )


# ── Source root mapping ────────────────────────────────────────────

_CANON_SOURCE_ROOTS = {
    "lore": [
        "artifacts/notion_export_unpacked (Everweave export)",
        "training-data/raw/ (novel versions)",
        "training-data/sft/avalon_codex_lore_sft.jsonl",
    ],
    "architecture": [
        "docs/01-architecture/",
        "SPEC.md",
        "SYSTEM_ARCHITECTURE.md",
        "LAYER_INDEX.md",
    ],
    "tokenizer": [
        "SpiralSeal SS1 - Six Sacred Tongues Lexicon (Notion)",
        "Sacred Tongue Tokenizer System (Notion)",
        "training-data/sft/sacred_tongues_sft.jsonl",
    ],
    "game": [
        "training-data/game_sessions/",
        "training-data/gacha_sessions/",
        "src/game/",
    ],
    "security": [
        "tests/adversarial/",
        "docs/research/null-space-tongue-signatures.html",
        "scripts/benchmark/",
    ],
    "music": [
        "training-data/music_sessions/",
    ],
    "meta": [
        "docs/map-room/scbe_source_roots.md",
        "docs/research/",
    ],
    "general": [
        "docs/map-room/scbe_source_roots.md",
    ],
}


# ── SENSE function ─────────────────────────────────────────────────

def sense(text: str) -> PumpPacket:
    """Step 1 of the pump: sense the input and produce a PumpPacket.

    Takes raw user text, returns a compact state record with:
    - tongue profile (6D resonance)
    - null pattern (which tongues are absent)
    - canon neighborhood
    - emotional register
    - governance posture
    - transition geometry
    - source roots to consult
    """
    # Compute tongue coordinates
    words = _WORD_RE.findall(text.lower())
    resonance = np.zeros(6, dtype=np.float64)
    for word in words:
        if word in DOMAIN_KEYWORDS:
            for idx, score in DOMAIN_KEYWORDS[word].items():
                resonance[idx] += score

    total_words = max(len(words), 1)
    coords = resonance / total_words
    coords = np.clip(coords, 0.0, 1.0)

    # Null pattern
    null_pattern = ""
    null_tongues = []
    active_tongues = []
    null_energy = 0.0
    active_energy = 0.0

    for i, val in enumerate(coords):
        if val < NULL_THRESHOLD:
            null_pattern += "_"
            null_tongues.append(TONGUE_CODES[i])
            null_energy += TONGUE_WEIGHTS[i]
        else:
            null_pattern += "#"
            active_tongues.append(TONGUE_CODES[i])
            active_energy += val * TONGUE_WEIGHTS[i]

    total_energy = null_energy + active_energy
    null_ratio = null_energy / total_energy if total_energy > 0 else 0.0

    # Dominant tongue
    dominant_idx = int(np.argmax(coords))
    dominant_tongue = TONGUE_CODES[dominant_idx]
    dominant_weight = float(coords[dominant_idx])

    # Poincare norm (how far from origin)
    poincare_norm = float(np.linalg.norm(coords))

    # Canon, emotion, governance
    canon = _detect_canon(text)
    emotion = _detect_emotion(text)
    governance = _detect_governance(text, null_ratio, len(active_tongues))

    # Source roots
    source_roots = _CANON_SOURCE_ROOTS.get(canon, _CANON_SOURCE_ROOTS["general"])

    return PumpPacket(
        tongue_profile=[float(v) for v in coords],
        null_pattern=null_pattern,
        null_tongues=null_tongues,
        active_tongues=active_tongues,
        null_energy=null_energy,
        active_energy=active_energy,
        null_ratio=null_ratio,
        dominant_tongue=dominant_tongue,
        dominant_weight=dominant_weight,
        canon=canon,
        emotion=emotion,
        governance=governance,
        poincare_norm=poincare_norm,
        source_roots=source_roots,
        input_length=len(text),
    )
