"""
World Bundle — Compact Canonical Training Bundle with Chi Circulation
=====================================================================

Compresses the full SCBE world state into a structured, recirculating
bundle. This is NOT a flat data dump — it's a living artifact that
gets re-read through different "methods" (circulation passes), and
each pass strengthens internal alignment.

The key insight from Issac: "the methods of the system IS the chi,
and the AI will grow up in that sort of world."

Formal model:
    B_{t+1} = C(B_t, M_t, O_t)

Where:
    B_t = bundle state at time t
    M_t = active method/mode at time t
    O_t = generated output at time t
    C   = circulation operator

Bundle sections:
    - ontology: world concepts and relationships
    - lexicon: vocabulary per tongue
    - grammar: conlang grammar rules per tongue
    - phonology: allowed sounds, syllable shapes
    - prosody: voice behavior profiles
    - harmonic: harmonic mappings from gallery/dead-tone
    - chromatic: color field mappings
    - ritual: ritual forms and state transitions
    - examples: canonical utterances per tongue
    - render: TTS/choral preset configurations

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

PHI = 1.618033988749895


# ---------------------------------------------------------------------------
# Bundle Sections
# ---------------------------------------------------------------------------


@dataclass
class OntologyEntry:
    """One concept in the world ontology."""

    concept_id: str
    name: str
    tongue_affinity: str  # primary tongue
    description: str
    relations: List[str] = field(default_factory=list)  # related concept_ids


@dataclass
class LexiconEntry:
    """One word in a tongue's vocabulary."""

    tongue: str
    word: str
    ipa: str
    meaning: str
    part_of_speech: str  # "noun" | "verb" | "adj" | "particle" | "ritual"
    syllable_count: int


@dataclass
class GrammarRule:
    """One grammar rule for a tongue."""

    tongue: str
    rule_id: str
    description: str
    pattern: str  # structural pattern (e.g., "SOV", "VSO")
    example: str


@dataclass
class PhonologyProfile:
    """Phonological constraints for a tongue."""

    tongue: str
    allowed_onsets: List[str]  # consonant clusters that can start syllables
    allowed_codas: List[str]  # consonant clusters that can end syllables
    vowel_inventory: List[str]  # available vowels
    max_syllable_weight: int  # max morae per syllable
    stress_rule: str  # "initial" | "penultimate" | "final" | "weight-based"


@dataclass
class RenderPreset:
    """Pre-configured TTS/choral render settings."""

    name: str
    mode: str  # "speech" | "speech_song" | "choral_ritual"
    voice_count: int
    chant_ratio: float
    base_rate: float
    description: str


# ---------------------------------------------------------------------------
# Circulation Pass
# ---------------------------------------------------------------------------


@dataclass
class CirculationPass:
    """One pass through the bundle with a specific method.

    Each pass reads the bundle through a different lens:
      - "grammar": focus on structural rules
      - "prosody": focus on acoustic behavior
      - "harmonic": focus on frequency/color mappings
      - "adversarial": focus on edge cases and traps
      - "ritual": focus on state transitions and ceremonies
      - "integration": cross-section coherence check
    """

    method: str
    timestamp: float
    sections_touched: List[str]
    output_hash: str  # hash of what was generated
    alignment_delta: float  # how much alignment improved [-1, 1]

    @property
    def age_seconds(self) -> float:
        return time.time() - self.timestamp


# ---------------------------------------------------------------------------
# World Bundle
# ---------------------------------------------------------------------------


@dataclass
class WorldBundle:
    """The compact canonical training bundle.

    This is the single artifact that contains everything the model
    needs to grow up inside the SCBE world. It's designed to be
    re-read through different circulation methods, with each pass
    strengthening internal alignment.
    """

    version: str = "1.0.0"

    # Core sections
    ontology: List[OntologyEntry] = field(default_factory=list)
    lexicon: Dict[str, List[LexiconEntry]] = field(default_factory=dict)
    grammar: Dict[str, List[GrammarRule]] = field(default_factory=dict)
    phonology: Dict[str, PhonologyProfile] = field(default_factory=dict)
    render_presets: List[RenderPreset] = field(default_factory=list)

    # Circulation history
    passes: List[CirculationPass] = field(default_factory=list)

    @property
    def tongue_count(self) -> int:
        return len(self.phonology)

    @property
    def total_vocabulary(self) -> int:
        return sum(len(words) for words in self.lexicon.values())

    @property
    def total_rules(self) -> int:
        return sum(len(rules) for rules in self.grammar.values())

    @property
    def circulation_count(self) -> int:
        return len(self.passes)

    @property
    def alignment_score(self) -> float:
        """Cumulative alignment from all circulation passes."""
        if not self.passes:
            return 0.0
        # Exponential moving average with phi decay
        score = 0.0
        weight = 1.0
        for p in reversed(self.passes):
            score += p.alignment_delta * weight
            weight /= PHI
        return max(-1.0, min(1.0, score))

    def circulate(
        self,
        method: str,
        sections: List[str],
        output: Any,
        alignment_delta: float,
    ) -> CirculationPass:
        """Record one circulation pass through the bundle.

        Args:
            method: which method was used (grammar/prosody/harmonic/etc.)
            sections: which sections were read
            output: what was generated (will be hashed)
            alignment_delta: how much alignment improved

        Returns:
            The recorded CirculationPass
        """
        output_str = json.dumps(output, default=str, sort_keys=True)
        output_hash = hashlib.sha256(output_str.encode()).hexdigest()[:16]

        cp = CirculationPass(
            method=method,
            timestamp=time.time(),
            sections_touched=sections,
            output_hash=output_hash,
            alignment_delta=max(-1.0, min(1.0, alignment_delta)),
        )
        self.passes.append(cp)
        return cp

    def to_dict(self) -> dict:
        return {
            "bundle_version": self.version,
            "tongue_count": self.tongue_count,
            "total_vocabulary": self.total_vocabulary,
            "total_rules": self.total_rules,
            "circulation_count": self.circulation_count,
            "alignment_score": round(self.alignment_score, 4),
            "render_presets": [{"name": p.name, "mode": p.mode, "voices": p.voice_count} for p in self.render_presets],
            "sections": {
                "ontology": len(self.ontology),
                "lexicon": {k: len(v) for k, v in self.lexicon.items()},
                "grammar": {k: len(v) for k, v in self.grammar.items()},
                "phonology": list(self.phonology.keys()),
            },
        }


# ---------------------------------------------------------------------------
# Bundle Factory
# ---------------------------------------------------------------------------

# Default phonology per tongue — these are the acoustic behavior grammars
_DEFAULT_PHONOLOGY: Dict[str, PhonologyProfile] = {
    "ko": PhonologyProfile(
        tongue="ko",
        allowed_onsets=["k", "g", "t", "d", "s", "n", "m"],
        allowed_codas=["k", "t", "n", "s"],
        vowel_inventory=["a", "e", "i", "o", "u"],
        max_syllable_weight=2,
        stress_rule="initial",
    ),
    "av": PhonologyProfile(
        tongue="av",
        allowed_onsets=["v", "l", "r", "n", "m", "h", "w"],
        allowed_codas=["l", "r", "n", "m"],
        vowel_inventory=["a", "aa", "e", "i", "o", "u", "ai"],
        max_syllable_weight=3,
        stress_rule="penultimate",
    ),
    "ru": PhonologyProfile(
        tongue="ru",
        allowed_onsets=["r", "gr", "kr", "dr", "br", "str", "tr"],
        allowed_codas=["r", "rk", "rt", "rd", "rn"],
        vowel_inventory=["a", "e", "u", "o"],
        max_syllable_weight=3,
        stress_rule="weight-based",
    ),
    "ca": PhonologyProfile(
        tongue="ca",
        allowed_onsets=["k", "s", "ts", "tch", "sh", "l"],
        allowed_codas=["l", "th", "s"],
        vowel_inventory=["a", "ae", "e", "i", "ai", "o"],
        max_syllable_weight=2,
        stress_rule="final",
    ),
    "um": PhonologyProfile(
        tongue="um",
        allowed_onsets=["m", "n", "w", "h", ""],
        allowed_codas=["m", "n", ""],
        vowel_inventory=["u", "uu", "o", "a", "e"],
        max_syllable_weight=2,
        stress_rule="penultimate",
    ),
    "dr": PhonologyProfile(
        tongue="dr",
        allowed_onsets=["dr", "d", "g", "b", "th", "kr"],
        allowed_codas=["th", "d", "g", "n", "rk"],
        vowel_inventory=["a", "ae", "o", "u"],
        max_syllable_weight=4,
        stress_rule="initial",
    ),
}

_DEFAULT_RENDER_PRESETS = [
    RenderPreset("speech", "speech", 1, 0.0, 1.0, "Plain spoken TTS"),
    RenderPreset("speech_song", "speech_song", 2, 0.4, 0.9, "Speech with harmonic backing"),
    RenderPreset("choral_ritual", "choral_ritual", 4, 0.8, 0.75, "Full multi-voice choral render"),
]


def create_default_bundle() -> WorldBundle:
    """Create a world bundle with default tongue phonology and render presets.

    This is the starting point — the bundle gets richer through
    circulation passes that add vocabulary, grammar rules, and examples.
    """
    return WorldBundle(
        phonology=dict(_DEFAULT_PHONOLOGY),
        render_presets=list(_DEFAULT_RENDER_PRESETS),
        lexicon={tongue: [] for tongue in _DEFAULT_PHONOLOGY},
        grammar={tongue: [] for tongue in _DEFAULT_PHONOLOGY},
    )
