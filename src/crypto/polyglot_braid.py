"""
Polyglot Cross-Lattice Linguistic Braid
========================================
Maps major world languages to Sacred Tongues, encodes parallel texts
through the tri-bundle polyglot encoder, and finds convergence points
as cross-linguistic invariants — the braid where meaning persists
across scripts, phonologies, and grammars.

The cross-lattice is a 3D structure:
    Axis 1 (horizontal): Natural languages (12+)
    Axis 2 (vertical):   Sacred Tongues (6)
    Axis 3 (depth):      Byte positions in the encoded text

At each intersection, a 27-dimensional tri-bundle cluster exists.
Where clusters from different natural languages converge in the
Sacred Tongue space, we find LINGUISTIC INVARIANTS — the meaning
that survives translation.

Architecture:
    NaturalLanguage  →  6D tongue affinity embedding
    ParallelConcept  →  same idea in 12+ languages
    BraidNode        →  one (language, tongue, position) triple
    BraidStrand      →  one language's full encoding across all tongues
    CrossLattice     →  all strands woven together, convergence detected

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum

from src.crypto.tri_bundle import (
    TONGUE_WEIGHTS,
    encode_polyglot_text,
    find_convergence_points,
    convergence_summary,
    PolyglotCluster,
)
from src.crypto.dark_cloud_mapper import (
    build_dark_energy_map,
    DarkEnergyMap,
)
from src.crypto.crossing_energy import (
    evaluate_sequence,
    summarize_governance,
    GovernanceSummary,
)

# ---------------------------------------------------------------------------
# Natural Language Registry
# ---------------------------------------------------------------------------


class LanguageFamily(Enum):
    """Major language families relevant to the braid."""

    INDO_EUROPEAN = "indo_european"
    SINO_TIBETAN = "sino_tibetan"
    AFRO_ASIATIC = "afro_asiatic"
    JAPONIC = "japonic"
    KOREANIC = "koreanic"
    DRAVIDIAN = "dravidian"
    TURKIC = "turkic"
    AUSTRONESIAN = "austronesian"
    NIGER_CONGO = "niger_congo"
    URALIC = "uralic"


@dataclass(frozen=True)
class NaturalLanguage:
    """A natural language with its Sacred Tongue affinity profile.

    The 6D tongue affinity is based on linguistic properties:
    - KO (intent/flow): verb prominence, action orientation, agglutination
    - AV (wisdom/transport): historical depth, sacred text tradition
    - RU (witness/governance): legal/governance tradition, case systems
    - CA (compute/analysis): tonal precision, logographic density, analytic structure
    - UM (shadow/security): honorific layers, indirection, veiling
    - DR (structure/forge): rigid morphology, agglutinative complexity, SOV order
    """

    code: str  # ISO 639-1
    name: str
    family: LanguageFamily
    script: str  # primary script name
    direction: str  # "ltr" or "rtl"
    tongue_affinity: Dict[str, float]  # 6D: ko/av/ru/ca/um/dr, each 0.0-1.0

    @property
    def primary_tongue(self) -> str:
        """The Sacred Tongue this language most aligns with."""
        return max(self.tongue_affinity, key=self.tongue_affinity.get)

    @property
    def secondary_tongue(self) -> str:
        """Second-strongest tongue affinity."""
        sorted_t = sorted(self.tongue_affinity.items(), key=lambda x: -x[1])
        return sorted_t[1][0]

    @property
    def affinity_vector(self) -> Tuple[float, ...]:
        """6D vector in tongue order: ko, av, ru, ca, um, dr."""
        return tuple(self.tongue_affinity[t] for t in ["ko", "av", "ru", "ca", "um", "dr"])

    @property
    def phi_weighted_affinity(self) -> float:
        """Total affinity weighted by phi-scaled tongue weights."""
        return sum(self.tongue_affinity[t] * TONGUE_WEIGHTS[t] for t in TONGUE_WEIGHTS)


# The world's major languages mapped to Sacred Tongue affinities
LANGUAGES: List[NaturalLanguage] = [
    NaturalLanguage(
        code="en",
        name="English",
        family=LanguageFamily.INDO_EUROPEAN,
        script="Latin",
        direction="ltr",
        tongue_affinity={"ko": 0.7, "av": 0.5, "ru": 0.6, "ca": 0.5, "um": 0.3, "dr": 0.4},
    ),
    NaturalLanguage(
        code="zh",
        name="Chinese (Mandarin)",
        family=LanguageFamily.SINO_TIBETAN,
        script="Han",
        direction="ltr",
        tongue_affinity={"ko": 0.5, "av": 0.8, "ru": 0.4, "ca": 0.9, "um": 0.6, "dr": 0.7},
    ),
    NaturalLanguage(
        code="es",
        name="Spanish",
        family=LanguageFamily.INDO_EUROPEAN,
        script="Latin",
        direction="ltr",
        tongue_affinity={"ko": 0.8, "av": 0.4, "ru": 0.5, "ca": 0.3, "um": 0.2, "dr": 0.4},
    ),
    NaturalLanguage(
        code="ar",
        name="Arabic",
        family=LanguageFamily.AFRO_ASIATIC,
        script="Arabic",
        direction="rtl",
        tongue_affinity={"ko": 0.5, "av": 0.9, "ru": 0.7, "ca": 0.6, "um": 0.8, "dr": 0.5},
    ),
    NaturalLanguage(
        code="hi",
        name="Hindi",
        family=LanguageFamily.INDO_EUROPEAN,
        script="Devanagari",
        direction="ltr",
        tongue_affinity={"ko": 0.6, "av": 0.8, "ru": 0.5, "ca": 0.4, "um": 0.4, "dr": 0.6},
    ),
    NaturalLanguage(
        code="fr",
        name="French",
        family=LanguageFamily.INDO_EUROPEAN,
        script="Latin",
        direction="ltr",
        tongue_affinity={"ko": 0.6, "av": 0.7, "ru": 0.7, "ca": 0.4, "um": 0.5, "dr": 0.3},
    ),
    NaturalLanguage(
        code="ru",
        name="Russian",
        family=LanguageFamily.INDO_EUROPEAN,
        script="Cyrillic",
        direction="ltr",
        tongue_affinity={"ko": 0.5, "av": 0.4, "ru": 0.8, "ca": 0.5, "um": 0.6, "dr": 0.7},
    ),
    NaturalLanguage(
        code="ja",
        name="Japanese",
        family=LanguageFamily.JAPONIC,
        script="Kanji/Kana",
        direction="ltr",
        tongue_affinity={"ko": 0.4, "av": 0.6, "ru": 0.5, "ca": 0.7, "um": 0.9, "dr": 0.8},
    ),
    NaturalLanguage(
        code="ko",
        name="Korean",
        family=LanguageFamily.KOREANIC,
        script="Hangul",
        direction="ltr",
        tongue_affinity={"ko": 0.9, "av": 0.5, "ru": 0.4, "ca": 0.5, "um": 0.7, "dr": 0.8},
    ),
    NaturalLanguage(
        code="de",
        name="German",
        family=LanguageFamily.INDO_EUROPEAN,
        script="Latin",
        direction="ltr",
        tongue_affinity={"ko": 0.5, "av": 0.3, "ru": 0.8, "ca": 0.6, "um": 0.3, "dr": 0.9},
    ),
    NaturalLanguage(
        code="pt",
        name="Portuguese",
        family=LanguageFamily.INDO_EUROPEAN,
        script="Latin",
        direction="ltr",
        tongue_affinity={"ko": 0.7, "av": 0.5, "ru": 0.4, "ca": 0.3, "um": 0.3, "dr": 0.4},
    ),
    NaturalLanguage(
        code="he",
        name="Hebrew",
        family=LanguageFamily.AFRO_ASIATIC,
        script="Hebrew",
        direction="rtl",
        tongue_affinity={"ko": 0.4, "av": 0.9, "ru": 0.9, "ca": 0.5, "um": 0.7, "dr": 0.6},
    ),
    NaturalLanguage(
        code="sa",
        name="Sanskrit",
        family=LanguageFamily.INDO_EUROPEAN,
        script="Devanagari",
        direction="ltr",
        tongue_affinity={"ko": 0.3, "av": 1.0, "ru": 0.7, "ca": 0.8, "um": 0.5, "dr": 0.9},
    ),
    NaturalLanguage(
        code="el",
        name="Greek",
        family=LanguageFamily.INDO_EUROPEAN,
        script="Greek",
        direction="ltr",
        tongue_affinity={"ko": 0.4, "av": 0.7, "ru": 0.6, "ca": 0.9, "um": 0.4, "dr": 0.5},
    ),
    NaturalLanguage(
        code="sw",
        name="Swahili",
        family=LanguageFamily.NIGER_CONGO,
        script="Latin",
        direction="ltr",
        tongue_affinity={"ko": 0.8, "av": 0.4, "ru": 0.5, "ca": 0.3, "um": 0.3, "dr": 0.6},
    ),
    NaturalLanguage(
        code="tr",
        name="Turkish",
        family=LanguageFamily.TURKIC,
        script="Latin",
        direction="ltr",
        tongue_affinity={"ko": 0.7, "av": 0.4, "ru": 0.5, "ca": 0.4, "um": 0.5, "dr": 0.8},
    ),
]

LANGUAGE_BY_CODE: Dict[str, NaturalLanguage] = {lang.code: lang for lang in LANGUAGES}


# ---------------------------------------------------------------------------
# Parallel Concept Corpus
# ---------------------------------------------------------------------------


@dataclass
class ParallelConcept:
    """The same concept expressed in multiple natural languages.

    This is the raw material for the cross-lattice braid. When we
    encode the same meaning in different scripts, the convergence
    points reveal what persists across all human expression.
    """

    concept_id: str
    domain: str  # "greeting", "love", "truth", "creation", etc.
    translations: Dict[str, str]  # lang_code → text

    @property
    def language_count(self) -> int:
        return len(self.translations)

    @property
    def languages(self) -> List[str]:
        return list(self.translations.keys())


# Core parallel concepts — universal ideas across cultures
PARALLEL_CONCEPTS: List[ParallelConcept] = [
    ParallelConcept(
        concept_id="truth",
        domain="philosophy",
        translations={
            "en": "truth",
            "zh": "\u771f\u7406",
            "es": "verdad",
            "ar": "\u062d\u0642\u064a\u0642\u0629",
            "hi": "\u0938\u0924\u094d\u092f",
            "fr": "v\u00e9rit\u00e9",
            "ru": "\u0438\u0441\u0442\u0438\u043d\u0430",
            "ja": "\u771f\u5b9f",
            "ko": "\uc9c4\uc2e4",
            "de": "Wahrheit",
            "pt": "verdade",
            "he": "\u05d0\u05de\u05ea",
            "sa": "\u0938\u0924\u094d\u092f\u092e\u094d",
            "el": "\u03b1\u03bb\u03ae\u03b8\u03b5\u03b9\u03b1",
            "sw": "ukweli",
            "tr": "ger\u00e7ek",
        },
    ),
    ParallelConcept(
        concept_id="love",
        domain="emotion",
        translations={
            "en": "love",
            "zh": "\u7231",
            "es": "amor",
            "ar": "\u062d\u0628",
            "hi": "\u092a\u094d\u0930\u0947\u092e",
            "fr": "amour",
            "ru": "\u043b\u044e\u0431\u043e\u0432\u044c",
            "ja": "\u611b",
            "ko": "\uc0ac\ub791",
            "de": "Liebe",
            "pt": "amor",
            "he": "\u05d0\u05d4\u05d1\u05d4",
            "sa": "\u092a\u094d\u0930\u0947\u092e",
            "el": "\u03b1\u03b3\u03ac\u03c0\u03b7",
            "sw": "upendo",
            "tr": "a\u015fk",
        },
    ),
    ParallelConcept(
        concept_id="light",
        domain="creation",
        translations={
            "en": "light",
            "zh": "\u5149",
            "es": "luz",
            "ar": "\u0646\u0648\u0631",
            "hi": "\u092a\u094d\u0930\u0915\u093e\u0936",
            "fr": "lumi\u00e8re",
            "ru": "\u0441\u0432\u0435\u0442",
            "ja": "\u5149",
            "ko": "\ube5b",
            "de": "Licht",
            "pt": "luz",
            "he": "\u05d0\u05d5\u05e8",
            "sa": "\u092a\u094d\u0930\u0915\u093e\u0936\u0903",
            "el": "\u03c6\u03c9\u03c2",
            "sw": "nuru",
            "tr": "\u0131\u015f\u0131k",
        },
    ),
    ParallelConcept(
        concept_id="water",
        domain="nature",
        translations={
            "en": "water",
            "zh": "\u6c34",
            "es": "agua",
            "ar": "\u0645\u0627\u0621",
            "hi": "\u092a\u093e\u0928\u0940",
            "fr": "eau",
            "ru": "\u0432\u043e\u0434\u0430",
            "ja": "\u6c34",
            "ko": "\ubb3c",
            "de": "Wasser",
            "pt": "\u00e1gua",
            "he": "\u05de\u05d9\u05dd",
            "sa": "\u091c\u0932\u092e\u094d",
            "el": "\u03bd\u03b5\u03c1\u03cc",
            "sw": "maji",
            "tr": "su",
        },
    ),
    ParallelConcept(
        concept_id="peace",
        domain="governance",
        translations={
            "en": "peace",
            "zh": "\u548c\u5e73",
            "es": "paz",
            "ar": "\u0633\u0644\u0627\u0645",
            "hi": "\u0936\u093e\u0902\u0924\u093f",
            "fr": "paix",
            "ru": "\u043c\u0438\u0440",
            "ja": "\u5e73\u548c",
            "ko": "\ud3c9\ud654",
            "de": "Frieden",
            "pt": "paz",
            "he": "\u05e9\u05dc\u05d5\u05dd",
            "sa": "\u0936\u093e\u0928\u094d\u0924\u093f\u0903",
            "el": "\u03b5\u03b9\u03c1\u03ae\u03bd\u03b7",
            "sw": "amani",
            "tr": "bar\u0131\u015f",
        },
    ),
    ParallelConcept(
        concept_id="in_the_beginning",
        domain="creation",
        translations={
            "en": "In the beginning",
            "he": "\u05d1\u05e8\u05d0\u05e9\u05d9\u05ea",
            "el": "\u0395\u03bd \u03b1\u03c1\u03c7\u03ae",
            "ar": "\u0641\u064a \u0627\u0644\u0628\u062f\u0627\u064a\u0629",
            "sa": "\u0906\u0926\u094c",
            "zh": "\u592a\u521d",
            "ja": "\u521d\u3081\u306b",
            "ko": "\ud0dc\ucd08\uc5d0",
            "ru": "\u0412 \u043d\u0430\u0447\u0430\u043b\u0435",
            "de": "Am Anfang",
            "fr": "Au commencement",
            "es": "En el principio",
            "pt": "No princ\u00edpio",
            "sw": "Hapo mwanzo",
            "tr": "Ba\u015flang\u0131\u00e7ta",
            "hi": "\u0906\u0930\u0902\u092d \u092e\u0947\u0902",
        },
    ),
    ParallelConcept(
        concept_id="one",
        domain="mathematics",
        translations={
            "en": "one",
            "zh": "\u4e00",
            "es": "uno",
            "ar": "\u0648\u0627\u062d\u062f",
            "hi": "\u090f\u0915",
            "fr": "un",
            "ru": "\u043e\u0434\u0438\u043d",
            "ja": "\u4e00",
            "ko": "\ud558\ub098",
            "de": "eins",
            "pt": "um",
            "he": "\u05d0\u05d7\u05d3",
            "sa": "\u090f\u0915\u092e\u094d",
            "el": "\u03ad\u03bd\u03b1",
            "sw": "moja",
            "tr": "bir",
        },
    ),
    ParallelConcept(
        concept_id="mother",
        domain="kinship",
        translations={
            "en": "mother",
            "zh": "\u6bcd\u4eb2",
            "es": "madre",
            "ar": "\u0623\u0645",
            "hi": "\u092e\u093e\u0901",
            "fr": "m\u00e8re",
            "ru": "\u043c\u0430\u0442\u044c",
            "ja": "\u6bcd",
            "ko": "\uc5b4\uba38\ub2c8",
            "de": "Mutter",
            "pt": "m\u00e3e",
            "he": "\u05d0\u05dd",
            "sa": "\u092e\u093e\u0924\u093e",
            "el": "\u03bc\u03b7\u03c4\u03ad\u03c1\u03b1",
            "sw": "mama",
            "tr": "anne",
        },
    ),
    ParallelConcept(
        concept_id="fire",
        domain="nature",
        translations={
            "en": "fire",
            "zh": "\u706b",
            "es": "fuego",
            "ar": "\u0646\u0627\u0631",
            "hi": "\u0905\u0917\u094d\u0928\u093f",
            "fr": "feu",
            "ru": "\u043e\u0433\u043e\u043d\u044c",
            "ja": "\u706b",
            "ko": "\ubd88",
            "de": "Feuer",
            "pt": "fogo",
            "he": "\u05d0\u05e9",
            "sa": "\u0905\u0917\u094d\u0928\u093f\u0903",
            "el": "\u03c6\u03c9\u03c4\u03b9\u03ac",
            "sw": "moto",
            "tr": "ate\u015f",
        },
    ),
    ParallelConcept(
        concept_id="knowledge",
        domain="philosophy",
        translations={
            "en": "knowledge",
            "zh": "\u77e5\u8bc6",
            "es": "conocimiento",
            "ar": "\u0645\u0639\u0631\u0641\u0629",
            "hi": "\u091c\u094d\u091e\u093e\u0928",
            "fr": "connaissance",
            "ru": "\u0437\u043d\u0430\u043d\u0438\u0435",
            "ja": "\u77e5\u8b58",
            "ko": "\uc9c0\uc2dd",
            "de": "Wissen",
            "pt": "conhecimento",
            "he": "\u05d3\u05e2\u05ea",
            "sa": "\u091c\u094d\u091e\u093e\u0928\u092e\u094d",
            "el": "\u03b3\u03bd\u03ce\u03c3\u03b7",
            "sw": "maarifa",
            "tr": "bilgi",
        },
    ),
    ParallelConcept(
        concept_id="justice",
        domain="governance",
        translations={
            "en": "justice",
            "zh": "\u6b63\u4e49",
            "es": "justicia",
            "ar": "\u0639\u062f\u0627\u0644\u0629",
            "hi": "\u0928\u094d\u092f\u093e\u092f",
            "fr": "justice",
            "ru": "\u0441\u043f\u0440\u0430\u0432\u0435\u0434\u043b\u0438\u0432\u043e\u0441\u0442\u044c",
            "ja": "\u6b63\u7fa9",
            "ko": "\uc815\uc758",
            "de": "Gerechtigkeit",
            "pt": "justi\u00e7a",
            "he": "\u05e6\u05d3\u05e7",
            "sa": "\u0928\u094d\u092f\u093e\u092f\u0903",
            "el": "\u03b4\u03b9\u03ba\u03b1\u03b9\u03bf\u03c3\u03cd\u03bd\u03b7",
            "sw": "haki",
            "tr": "adalet",
        },
    ),
    ParallelConcept(
        concept_id="song",
        domain="art",
        translations={
            "en": "song",
            "zh": "\u6b4c",
            "es": "canci\u00f3n",
            "ar": "\u0623\u063a\u0646\u064a\u0629",
            "hi": "\u0917\u0940\u0924",
            "fr": "chanson",
            "ru": "\u043f\u0435\u0441\u043d\u044f",
            "ja": "\u6b4c",
            "ko": "\ub178\ub798",
            "de": "Lied",
            "pt": "can\u00e7\u00e3o",
            "he": "\u05e9\u05d9\u05e8",
            "sa": "\u0917\u0940\u0924\u092e\u094d",
            "el": "\u03c4\u03c1\u03b1\u03b3\u03bf\u03cd\u03b4\u03b9",
            "sw": "wimbo",
            "tr": "\u015fark\u0131",
        },
    ),
]


# ---------------------------------------------------------------------------
# Braid Encoding
# ---------------------------------------------------------------------------


@dataclass
class BraidStrand:
    """One natural language's encoding through the Sacred Tongue lattice."""

    language: NaturalLanguage
    text: str
    polyglot_clusters: List[PolyglotCluster]
    convergence_points: List[Tuple[int, float, int]]  # (pos, sync, byte_val)
    summary: Dict

    @property
    def byte_count(self) -> int:
        return len(self.text.encode("utf-8"))

    @property
    def mean_sync(self) -> float:
        return self.summary.get("mean_sync", 0.0)

    @property
    def convergence_ratio(self) -> float:
        if self.byte_count == 0:
            return 0.0
        return len(self.convergence_points) / self.byte_count


@dataclass
class CrossLatticeNode:
    """A point in the cross-lattice where languages intersect."""

    concept_id: str
    lang_code: str
    tongue: str
    position: int
    sync_score: float
    cluster_id_hex: str


@dataclass
class BraidResult:
    """Full cross-lattice braid for one parallel concept."""

    concept: ParallelConcept
    strands: Dict[str, BraidStrand]  # lang_code → strand
    cross_convergence: List[Dict]  # where do different languages converge?
    tongue_distribution: Dict[str, float]  # which tongues dominate overall?
    mean_cross_sync: float
    dark_energy_maps: Dict[str, DarkEnergyMap]

    @property
    def language_count(self) -> int:
        return len(self.strands)

    @property
    def total_dimensions(self) -> int:
        """Total tri-bundle dimensions across all language strands."""
        return sum(s.byte_count * 162 for s in self.strands.values())


def encode_strand(lang: NaturalLanguage, text: str, threshold: float = 0.5) -> BraidStrand:
    """Encode one language's text into a braid strand."""
    clusters = encode_polyglot_text(text)
    conv_points = find_convergence_points(clusters, threshold=threshold)
    summary = convergence_summary(clusters)

    return BraidStrand(
        language=lang,
        text=text,
        polyglot_clusters=clusters,
        convergence_points=conv_points,
        summary=summary,
    )


def weave_concept(
    concept: ParallelConcept,
    threshold: float = 0.5,
    languages: Optional[List[str]] = None,
) -> BraidResult:
    """Weave all translations of a concept into a cross-lattice braid.

    Args:
        concept: The parallel concept with translations
        threshold: Convergence threshold (0.0 = all converge, 1.0 = only perfect)
        languages: Optional subset of language codes to include
    """
    lang_codes = languages or concept.languages
    strands: Dict[str, BraidStrand] = {}
    dark_maps: Dict[str, DarkEnergyMap] = {}

    for code in lang_codes:
        if code not in concept.translations:
            continue
        lang = LANGUAGE_BY_CODE.get(code)
        if lang is None:
            continue

        text = concept.translations[code]
        strand = encode_strand(lang, text, threshold=threshold)
        strands[code] = strand

        # Dark energy map for each language's byte representation
        data = text.encode("utf-8")
        dark_maps[code] = build_dark_energy_map(data)

    # Cross-convergence: find tongue positions where multiple languages sync
    cross_conv = _find_cross_convergence(strands)

    # Tongue distribution: weighted average of all language affinities
    tongue_dist = _compute_tongue_distribution(strands)

    # Mean cross-sync: average sync across all strand pairs
    mean_sync = _compute_mean_cross_sync(strands)

    return BraidResult(
        concept=concept,
        strands=strands,
        cross_convergence=cross_conv,
        tongue_distribution=tongue_dist,
        mean_cross_sync=mean_sync,
        dark_energy_maps=dark_maps,
    )


def _find_cross_convergence(strands: Dict[str, BraidStrand]) -> List[Dict]:
    """Find where different languages converge in tongue space.

    Two languages converge on a concept when their polyglot encodings
    produce similar synchronization patterns despite different byte streams.
    """
    results = []
    codes = list(strands.keys())

    for i in range(len(codes)):
        for j in range(i + 1, len(codes)):
            code_a, code_b = codes[i], codes[j]
            strand_a, strand_b = strands[code_a], strands[code_b]

            # Compare global sync scores
            sync_a = strand_a.mean_sync
            sync_b = strand_b.mean_sync

            # Convergence = how similar are their sync patterns?
            sync_delta = abs(sync_a - sync_b)
            convergence = max(0.0, 1.0 - sync_delta)

            # Tongue affinity correlation
            aff_a = strand_a.language.affinity_vector
            aff_b = strand_b.language.affinity_vector
            dot = sum(a * b for a, b in zip(aff_a, aff_b))
            norm_a = math.sqrt(sum(a**2 for a in aff_a))
            norm_b = math.sqrt(sum(b**2 for b in aff_b))
            affinity_correlation = dot / (norm_a * norm_b) if norm_a > 0 and norm_b > 0 else 0.0

            results.append(
                {
                    "lang_a": code_a,
                    "lang_b": code_b,
                    "sync_convergence": convergence,
                    "affinity_correlation": affinity_correlation,
                    "combined_score": convergence * affinity_correlation,
                    "byte_ratio": strand_a.byte_count / max(strand_b.byte_count, 1),
                }
            )

    return results


def _compute_tongue_distribution(strands: Dict[str, BraidStrand]) -> Dict[str, float]:
    """Weighted tongue distribution across all languages in the braid."""
    totals = {t: 0.0 for t in TONGUE_WEIGHTS}
    for strand in strands.values():
        for tongue, affinity in strand.language.tongue_affinity.items():
            totals[tongue] += affinity

    # Normalize
    total_sum = sum(totals.values()) or 1.0
    return {t: v / total_sum for t, v in totals.items()}


def _compute_mean_cross_sync(strands: Dict[str, BraidStrand]) -> float:
    """Average synchronization across all strands."""
    syncs = [s.mean_sync for s in strands.values()]
    return sum(syncs) / len(syncs) if syncs else 0.0


# ---------------------------------------------------------------------------
# Full Braid: All Concepts
# ---------------------------------------------------------------------------


def weave_all_concepts(
    threshold: float = 0.5,
    concepts: Optional[List[ParallelConcept]] = None,
    languages: Optional[List[str]] = None,
) -> List[BraidResult]:
    """Weave all parallel concepts into cross-lattice braids."""
    concept_list = concepts or PARALLEL_CONCEPTS
    return [weave_concept(concept, threshold=threshold, languages=languages) for concept in concept_list]


def braid_summary(results: List[BraidResult]) -> Dict:
    """Summary statistics across all braided concepts."""
    if not results:
        return {"count": 0}

    total_dims = sum(r.total_dimensions for r in results)
    all_syncs = [r.mean_cross_sync for r in results]
    all_convergences = []
    for r in results:
        for cc in r.cross_convergence:
            all_convergences.append(cc["combined_score"])

    # Which concepts converge most across languages?
    ranked = sorted(results, key=lambda r: r.mean_cross_sync, reverse=True)

    # Tongue dominance across all concepts
    tongue_totals = {t: 0.0 for t in TONGUE_WEIGHTS}
    for r in results:
        for t, v in r.tongue_distribution.items():
            tongue_totals[t] += v
    total_t = sum(tongue_totals.values()) or 1.0
    tongue_totals = {t: v / total_t for t, v in tongue_totals.items()}

    return {
        "count": len(results),
        "total_dimensions": total_dims,
        "mean_cross_sync": sum(all_syncs) / len(all_syncs),
        "mean_convergence": sum(all_convergences) / len(all_convergences) if all_convergences else 0.0,
        "most_convergent_concept": ranked[0].concept.concept_id if ranked else None,
        "least_convergent_concept": ranked[-1].concept.concept_id if ranked else None,
        "tongue_distribution": tongue_totals,
        "languages_covered": list({code for r in results for code in r.strands}),
    }
