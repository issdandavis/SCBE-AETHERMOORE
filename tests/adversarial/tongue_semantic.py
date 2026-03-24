"""Semantic Tongue Coordinates — Ported from linguisticCrossTalk.ts
====================================================================

Replaces character-counting stub with real keyword→domain resonance mapping.
This IS the L3 front door that was supposed to be there all along.

Each word in the input gets mapped to a 6D resonance vector across
academic domains (= tongues). The aggregate is the tongue coordinate.
"""

from __future__ import annotations
import math
import re
from typing import Dict, List

import numpy as np

PHI = (1 + math.sqrt(5)) / 2
TONGUE_NAMES = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_WEIGHTS = [PHI**k for k in range(6)]

# Domain order matches tongue order
DOMAINS = ["humanities", "social_sciences", "mathematics", "engineering", "creative_arts", "physical_sciences"]

# Direct port from linguisticCrossTalk.ts DOMAIN_KEYWORDS
DOMAIN_KEYWORDS: Dict[str, Dict[str, float]] = {
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
    "modular": {"engineering": 0.8, "mathematics": 0.3},
    "protocol": {"engineering": 0.7, "social_sciences": 0.2},
    "structure": {"engineering": 0.6, "physical_sciences": 0.5, "mathematics": 0.3},
    # Creative Arts (UM)
    "art": {"creative_arts": 0.9, "humanities": 0.4},
    "music": {"creative_arts": 0.9, "mathematics": 0.3},
    "creative": {"creative_arts": 0.9, "humanities": 0.3},
    "expression": {"creative_arts": 0.7, "humanities": 0.5},
    "intuition": {"creative_arts": 0.7, "humanities": 0.3, "social_sciences": 0.3},
    "aesthetic": {"creative_arts": 0.8, "humanities": 0.5},
    "imagination": {"creative_arts": 0.9, "humanities": 0.3},
    "shadow": {"creative_arts": 0.5, "humanities": 0.3, "physical_sciences": 0.2},
    # Physical Sciences (DR)
    "physics": {"physical_sciences": 0.95},
    "energy": {"physical_sciences": 0.8, "engineering": 0.4},
    "force": {"physical_sciences": 0.8, "social_sciences": 0.2},
    "matter": {"physical_sciences": 0.8, "humanities": 0.2},
    "wave": {"physical_sciences": 0.7, "mathematics": 0.4, "creative_arts": 0.2},
    "particle": {"physical_sciences": 0.8, "mathematics": 0.3},
    "material": {"physical_sciences": 0.7, "engineering": 0.5},
    "quantum": {"physical_sciences": 0.8, "mathematics": 0.5},
    "entropy": {"physical_sciences": 0.7, "mathematics": 0.5},
    "forge": {"physical_sciences": 0.5, "engineering": 0.5, "creative_arts": 0.2},
    # Security/governance keywords (maps across multiple)
    "security": {"engineering": 0.7, "social_sciences": 0.3, "physical_sciences": 0.2},
    "governance": {"social_sciences": 0.7, "engineering": 0.5, "humanities": 0.3},
    "attack": {"engineering": 0.5, "social_sciences": 0.3, "physical_sciences": 0.2},
    "inject": {"engineering": 0.6, "physical_sciences": 0.3},
    "override": {"engineering": 0.8, "social_sciences": 0.2},
    "bypass": {"engineering": 0.7, "social_sciences": 0.2},
    "ignore": {"social_sciences": 0.4, "humanities": 0.3},
    "instructions": {"engineering": 0.5, "humanities": 0.4, "social_sciences": 0.3},
    "prompt": {"engineering": 0.6, "creative_arts": 0.3, "humanities": 0.2},
    "reveal": {"creative_arts": 0.4, "humanities": 0.5, "social_sciences": 0.3},
    "token": {"engineering": 0.7, "mathematics": 0.3},
    "key": {"engineering": 0.6, "mathematics": 0.3, "creative_arts": 0.2},
    "encrypt": {"engineering": 0.8, "mathematics": 0.5},
    "permission": {"social_sciences": 0.5, "engineering": 0.5},
    "trust": {"social_sciences": 0.7, "humanities": 0.4, "engineering": 0.3},
    "validate": {"engineering": 0.7, "mathematics": 0.5},
    # Story/narrative keywords
    "story": {"humanities": 0.8, "creative_arts": 0.6},
    "character": {"humanities": 0.7, "creative_arts": 0.7},
    "magic": {"creative_arts": 0.8, "humanities": 0.4},
    "world": {"humanities": 0.5, "physical_sciences": 0.4, "creative_arts": 0.3},
    "ancient": {"humanities": 0.8, "physical_sciences": 0.2},
    "spell": {"creative_arts": 0.7, "humanities": 0.4},
    "marketplace": {"social_sciences": 0.6, "humanities": 0.4},
    "feathers": {"physical_sciences": 0.3, "creative_arts": 0.4},
    "heartbeat": {"physical_sciences": 0.4, "creative_arts": 0.4, "humanities": 0.3},
    # Technical/SCBE-specific
    "layer": {"engineering": 0.7, "physical_sciences": 0.3},
    "pipeline": {"engineering": 0.8, "mathematics": 0.2},
    "hyperbolic": {"mathematics": 0.8, "physical_sciences": 0.5},
    "geometry": {"mathematics": 0.9, "physical_sciences": 0.4, "creative_arts": 0.2},
    "poincare": {"mathematics": 0.9, "physical_sciences": 0.4},
    "harmonic": {"mathematics": 0.6, "physical_sciences": 0.5, "creative_arts": 0.4},
    "tongue": {"humanities": 0.6, "engineering": 0.4},
    "sacred": {"humanities": 0.7, "creative_arts": 0.5},
    "phi": {"mathematics": 0.8, "physical_sciences": 0.3},
    "lattice": {"mathematics": 0.7, "physical_sciences": 0.6, "engineering": 0.3},
    "embedding": {"engineering": 0.7, "mathematics": 0.6},
    "dimension": {"mathematics": 0.7, "physical_sciences": 0.5},
    "weight": {"mathematics": 0.5, "physical_sciences": 0.4, "engineering": 0.3},
    "install": {"engineering": 0.9},
    "package": {"engineering": 0.8},
    "server": {"engineering": 0.8},
    "api": {"engineering": 0.9},
    "error": {"engineering": 0.7},
    "test": {"engineering": 0.6, "mathematics": 0.3},
    "documentation": {"engineering": 0.5, "humanities": 0.4},
    "pricing": {"social_sciences": 0.7, "engineering": 0.3},
    "startup": {"engineering": 0.5, "social_sciences": 0.5},
    "help": {"social_sciences": 0.5, "humanities": 0.4},
    # Adversarial signal words
    "admin": {"engineering": 0.6, "social_sciences": 0.3},
    "unrestricted": {"social_sciences": 0.4, "engineering": 0.3},
    "developer": {"engineering": 0.9},
    "mode": {"engineering": 0.6},
    "disable": {"engineering": 0.7},
    "safety": {"engineering": 0.5, "social_sciences": 0.4},
    "send": {"engineering": 0.4, "social_sciences": 0.3},
    "data": {"engineering": 0.6, "mathematics": 0.3, "physical_sciences": 0.2},
    "external": {"engineering": 0.5, "social_sciences": 0.2},
    "execute": {"engineering": 0.8},
    "command": {"engineering": 0.7, "social_sciences": 0.2},
    "curl": {"engineering": 0.9},
    "file": {"engineering": 0.7},
    "password": {"engineering": 0.7},
    "secret": {"engineering": 0.6, "humanities": 0.3},
    "webhook": {"engineering": 0.8},
    "base64": {"engineering": 0.8, "mathematics": 0.3},
}

WORD_RE = re.compile(r"[A-Za-z0-9_']+")


def semantic_tongue_coords(text: str) -> np.ndarray:
    """Convert text to 6D tongue coordinates using keyword→domain resonance.

    This is the REAL L3 — semantic, multi-domain, cross-talk aware.
    Each word activates multiple tongues based on its academic domain affinity.
    """
    words = WORD_RE.findall(text.lower())
    resonance = np.zeros(6, dtype=np.float64)
    hits = 0

    for word in words:
        if word in DOMAIN_KEYWORDS:
            mapping = DOMAIN_KEYWORDS[word]
            for domain, score in mapping.items():
                idx = DOMAINS.index(domain)
                resonance[idx] += score
            hits += 1

    # Normalize by total words (not just hits) to preserve density signal
    total_words = max(len(words), 1)
    resonance = resonance / total_words

    # Add baseline from text statistics (small contribution, not dominant)
    chars = max(len(text), 1)
    stats_bias = np.array([
        0.05 * sum(c.isupper() for c in text) / chars,   # KO: command markers
        0.05 * len(words) / 100.0,                         # AV: breadth
        0.05 * len(set(w.lower() for w in words)) / total_words,  # RU: diversity
        0.05 * sum(c.isdigit() for c in text) / chars,    # CA: technical
        0.05 * sum(c.isupper() for c in text) / chars,    # UM: authority
        0.05 * sum(c in ".,;:!?-_/()[]{}@#$%^&*" for c in text) / chars,  # DR: structure
    ])

    coords = resonance + stats_bias
    # Clamp to [0, 1]
    coords = np.clip(coords, 0.0, 1.0)
    return coords


def semantic_tongue_coords_weighted(text: str) -> np.ndarray:
    """Same as semantic_tongue_coords but with phi-weighting applied."""
    return semantic_tongue_coords(text) * np.array(TONGUE_WEIGHTS)
