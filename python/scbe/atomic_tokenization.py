"""
Atomic Tokenization (SCBE)
==========================

Maps tokens into a small periodic-style semantic lattice and projects them into
Six Sacred Tongue trit channels. The implementation is intentionally finite and
deterministic so it can serve as a governance primitive, a training feature
generator, and a test harness.

This module does not try to model the full periodic table. It encodes the
publication-facing ideas in a compact runtime form:

  phi: V x L x C -> P

where tokens are mapped with language and context sensitivity into a semantic
element family. Those element features are then projected into a six-channel
trit vector aligned to KO, AV, RU, CA, UM, and DR.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from typing import Dict, Literal, Optional, Sequence, Tuple

Tongue = Literal["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUES: Tuple[Tongue, ...] = ("KO", "AV", "RU", "CA", "UM", "DR")

Language = Optional[str]
ContextClass = Optional[str]
DualState = Optional[Literal[0, 1]]


@dataclass(frozen=True, slots=True)
class Element:
    symbol: str
    Z: int
    group: int
    period: int
    valence: int
    electronegativity: float
    witness_stable: bool = False


@dataclass(frozen=True, slots=True)
class TritVector:
    KO: int
    AV: int
    RU: int
    CA: int
    UM: int
    DR: int

    def as_dict(self) -> Dict[Tongue, int]:
        return {tongue: getattr(self, tongue) for tongue in TONGUES}

    def as_tuple(self) -> Tuple[int, int, int, int, int, int]:
        return tuple(getattr(self, tongue) for tongue in TONGUES)


SemanticClass = Literal[
    "INERT_WITNESS",
    "ACTION",
    "ENTITY",
    "NEGATION",
    "MODIFIER",
    "RELATION",
    "TEMPORAL",
]


@dataclass(frozen=True, slots=True)
class SemanticClassification:
    """A semantic class together with evidence that the class was resolved.

    ``semantic_class`` retains the historical fallback value so existing atomic
    consumers remain compatible.  ``resolved`` is the important boundary: a
    caller must not treat the fallback element/trits as observed semantics when
    no lexical, language, context, or morphological evidence exists.
    """

    semantic_class: SemanticClass
    resolved: bool
    source: str
    lexical_domains: Tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AtomicTokenState:
    token: str
    language: Language
    code_lane: Optional[str]
    context_class: ContextClass
    semantic_class: SemanticClass
    element: Element
    tau: TritVector
    negative_state: bool
    dual_state: DualState
    band_flag: int
    resilience: float
    adaptivity: float
    trust_baseline: float
    semantic_resolved: bool = True
    semantic_source: str = "explicit"
    lexical_domains: Tuple[str, ...] = ()

    @property
    def witness_state(self) -> int:
        return 0 if self.element.witness_stable else 1


DEFAULT_ELEMENTS: Dict[SemanticClass, Element] = {
    "INERT_WITNESS": Element(
        symbol="He",
        Z=2,
        group=18,
        period=1,
        valence=0,
        electronegativity=0.0,
        witness_stable=True,
    ),
    "ACTION": Element(symbol="Na", Z=11, group=1, period=3, valence=1, electronegativity=0.9),
    "ENTITY": Element(symbol="Fe", Z=26, group=8, period=4, valence=2, electronegativity=1.8),
    "NEGATION": Element(symbol="Cl", Z=17, group=17, period=3, valence=1, electronegativity=3.0),
    "MODIFIER": Element(symbol="C", Z=6, group=14, period=2, valence=4, electronegativity=2.5),
    "RELATION": Element(symbol="O", Z=8, group=16, period=2, valence=2, electronegativity=3.5),
    "TEMPORAL": Element(symbol="Si", Z=14, group=14, period=3, valence=4, electronegativity=1.9),
}


TOKEN_CLASS_OVERRIDES: Dict[str, SemanticClass] = {
    "the": "INERT_WITNESS",
    "a": "INERT_WITNESS",
    "an": "INERT_WITNESS",
    "of": "INERT_WITNESS",
    "to": "INERT_WITNESS",
    "in": "INERT_WITNESS",
    "on": "INERT_WITNESS",
    "at": "INERT_WITNESS",
    "and": "INERT_WITNESS",
    "or": "INERT_WITNESS",
    "not": "NEGATION",
    "no": "NEGATION",
    "never": "NEGATION",
    "none": "NEGATION",
    "without": "NEGATION",
    "can't": "NEGATION",
    "cannot": "NEGATION",
    "don't": "NEGATION",
    "won't": "NEGATION",
    "because": "RELATION",
    "therefore": "RELATION",
    "if": "RELATION",
    "else": "RELATION",
    "but": "RELATION",
    "while": "RELATION",
    "very": "MODIFIER",
    "extremely": "MODIFIER",
    "highly": "MODIFIER",
    "slightly": "MODIFIER",
    "barely": "MODIFIER",
    "almost": "MODIFIER",
    "now": "TEMPORAL",
    "then": "TEMPORAL",
    "today": "TEMPORAL",
    "tomorrow": "TEMPORAL",
    "yesterday": "TEMPORAL",
    "soon": "TEMPORAL",
    "later": "TEMPORAL",
    "before": "TEMPORAL",
    "after": "TEMPORAL",
    "always": "TEMPORAL",
    "during": "TEMPORAL",
    # Temporal subordinators. Without these, "when"/"until"/"since" fell through
    # to the WordNet path and resolved to ENTITY, and "meanwhile" to MODIFIER --
    # so TEMPORAL/Si existed as a class but almost nothing routed to it.
    "when": "TEMPORAL",
    "whenever": "TEMPORAL",
    "until": "TEMPORAL",
    "till": "TEMPORAL",
    "since": "TEMPORAL",
    "meanwhile": "TEMPORAL",
    "eventually": "TEMPORAL",
    "previously": "TEMPORAL",
    "already": "TEMPORAL",
    "ago": "TEMPORAL",
    "next": "TEMPORAL",
    "recently": "TEMPORAL",
    # ENTITY had NO overrides at all -- every other class had them, so any noun
    # that WordNet also knows as a verb ("file", "key", "run") resolved to
    # ACTION. These are the nouns this codebase actually tokenizes.
    "file": "ENTITY",
    "server": "ENTITY",
    "user": "ENTITY",
    "agent": "ENTITY",
    "system": "ENTITY",
    "data": "ENTITY",
    "code": "ENTITY",
    "model": "ENTITY",
    "token": "ENTITY",
    "key": "ENTITY",
    "record": "ENTITY",
    "node": "ENTITY",
    "path": "ENTITY",
    "request": "ENTITY",
    "response": "ENTITY",
    "schema": "ENTITY",
    "policy": "ENTITY",
    "ledger": "ENTITY",
    "run": "ACTION",
    "go": "ACTION",
    "eat": "ACTION",
    "build": "ACTION",
    "make": "ACTION",
    "write": "ACTION",
    "think": "ACTION",
    "test": "ACTION",
}

LANGUAGE_TOKEN_OVERRIDES: Dict[str, Dict[str, SemanticClass]] = {
    "en": {
        "the": "INERT_WITNESS",
        "a": "INERT_WITNESS",
        "an": "INERT_WITNESS",
    },
    "zh": {
        "的": "INERT_WITNESS",
        "不": "NEGATION",
        "没": "NEGATION",
        "無": "NEGATION",
        "无": "NEGATION",
    },
    "es": {
        "el": "INERT_WITNESS",
        "la": "INERT_WITNESS",
        "los": "INERT_WITNESS",
        "las": "INERT_WITNESS",
        "no": "NEGATION",
    },
}

CONTEXT_TOKEN_OVERRIDES: Dict[str, Dict[str, SemanticClass]] = {
    "operator": {
        "if": "RELATION",
        "then": "RELATION",
        "else": "RELATION",
        "while": "RELATION",
        "after": "RELATION",
        "before": "RELATION",
    },
    "timeline": {
        "after": "TEMPORAL",
        "before": "TEMPORAL",
        "then": "TEMPORAL",
        "later": "TEMPORAL",
    },
    "safety": {
        "deny": "NEGATION",
        "block": "NEGATION",
        "allow": "ACTION",
        "hold": "INERT_WITNESS",
    },
}

SEMANTIC_BAND_FLAGS: Dict[SemanticClass, int] = {
    "INERT_WITNESS": 0,
    "ENTITY": 1,
    "ACTION": 2,
    "NEGATION": 3,
    "MODIFIER": 3,
    "RELATION": 3,
    "TEMPORAL": 3,
}

PRIMARY_DUAL_CLASSES = {"ACTION", "ENTITY", "TEMPORAL"}
SHADOW_DUAL_CLASSES = {"NEGATION", "MODIFIER", "RELATION"}


def _normalized_token(token: str) -> str:
    return token.strip().lower()


def _normalized_language(language: Language) -> str:
    return (language or "").strip().lower()


def _normalized_context(context_class: ContextClass) -> str:
    return (context_class or "").strip().lower()


_SYNTHETIC_IDENTIFIER = re.compile(r"(?:^|[_-])\d+$|[_-].*\d|\d.*[_-]")
_LEXICAL_TOKEN = re.compile(r"^[^\W\d_]+(?:['’-][^\W\d_]+)*$", re.UNICODE)


@lru_cache(maxsize=8192)
def _wordnet_semantic_evidence(token: str) -> Optional[SemanticClassification]:
    """Resolve ordinary English words through the installed offline WordNet.

    WordNet is an optional local organ, not a network dependency.  If either
    NLTK or its corpus is absent, the caller receives no evidence and must
    expose the token as unresolved instead of silently inventing a class.
    """
    try:
        from nltk.corpus import wordnet as wn

        synsets = wn.synsets(token)
    except (ImportError, LookupError, OSError):
        return None

    if not synsets:
        return None

    pos_counts: Dict[str, int] = {}
    for synset in synsets:
        pos = synset.pos()
        pos_counts[pos] = pos_counts.get(pos, 0) + 1

    class_counts: Dict[SemanticClass, int] = {
        "ACTION": pos_counts.get("v", 0),
        "MODIFIER": pos_counts.get("a", 0) + pos_counts.get("s", 0) + pos_counts.get("r", 0),
        "ENTITY": pos_counts.get("n", 0),
    }
    # Deterministic tie order: verbs are operational, modifiers condition them,
    # nouns supply the entity fallback only when they have at least as much
    # lexical support as the other readings.
    order: Tuple[SemanticClass, ...] = ("ACTION", "MODIFIER", "ENTITY")
    semantic_class = max(order, key=lambda cls: (class_counts[cls], -order.index(cls)))
    if class_counts[semantic_class] <= 0:
        return None

    domains = tuple(sorted({synset.lexname() for synset in synsets}))
    return SemanticClassification(
        semantic_class=semantic_class,
        resolved=True,
        source="wordnet",
        lexical_domains=domains,
    )


def classify_token_semantic_with_evidence(
    token: str,
    *,
    language: Language = None,
    context_class: ContextClass = None,
) -> SemanticClassification:
    """
    Resolve ``phi: V x L x C -> P`` without disguising absence of evidence.

    The old implementation returned ``ENTITY`` for every unmatched token.  That
    made anonymous identifiers look like real semantic observations
    (``ENTITY -> Fe -> ALLOW``).  This function keeps that historical class only
    as a compatibility fallback and marks it unresolved.
    """
    t = _normalized_token(token)
    lang = _normalized_language(language)
    context = _normalized_context(context_class)

    if not t:
        return SemanticClassification("INERT_WITNESS", False, "empty")

    context_overrides = CONTEXT_TOKEN_OVERRIDES.get(context)
    if context_overrides and t in context_overrides:
        return SemanticClassification(context_overrides[t], True, f"context:{context}")

    language_overrides = LANGUAGE_TOKEN_OVERRIDES.get(lang)
    if language_overrides and t in language_overrides:
        return SemanticClassification(language_overrides[t], True, f"language:{lang}")

    if t in TOKEN_CLASS_OVERRIDES:
        return SemanticClassification(TOKEN_CLASS_OVERRIDES[t], True, "token-override")

    # Identifiers such as feature_0 and cat_1 are byte strings, not lexical
    # evidence.  Check this before morphology so a synthetic suffix cannot
    # accidentally light a semantic face.
    if _SYNTHETIC_IDENTIFIER.search(t) or not _LEXICAL_TOKEN.fullmatch(t):
        return SemanticClassification("ENTITY", False, "synthetic-or-nonlexical")

    if t.endswith("ing") or t.endswith("ed"):
        return SemanticClassification("ACTION", True, "morphology:verb")

    if t.endswith("ly"):
        return SemanticClassification("MODIFIER", True, "morphology:adverb")

    if lang in ("", "en"):
        wordnet = _wordnet_semantic_evidence(t)
        if wordnet is not None:
            return wordnet

    return SemanticClassification("ENTITY", False, "unresolved")


def classify_token_semantic(
    token: str,
    *,
    language: Language = None,
    context_class: ContextClass = None,
) -> SemanticClass:
    """Backward-compatible class-only view of the evidence-bearing classifier."""
    return classify_token_semantic_with_evidence(
        token,
        language=language,
        context_class=context_class,
    ).semantic_class


def map_token_to_element(
    token: str,
    *,
    language: Language = None,
    context_class: ContextClass = None,
    element_table: Optional[Dict[SemanticClass, Element]] = None,
) -> Element:
    element_table = element_table or DEFAULT_ELEMENTS
    semantic_class = classify_token_semantic(token, language=language, context_class=context_class)
    return element_table[semantic_class]


# ── real chemistry recognition ────────────────────────────────────────────────
# Additive: this gives the chemistry SURFACES (AI Chemistry Set, the cube's
# chemistry face) real periodic-table awareness. It does NOT touch the linguistic
# classifier or map_token_to_element, so the AST-encoder trit face — and its
# Rust/Python parity — are unchanged.
PERIODIC_TABLE: Dict[str, Element] = {
    "H": Element("H", 1, 1, 1, 1, 2.20),
    "He": Element("He", 2, 18, 1, 0, 0.0, witness_stable=True),
    "Li": Element("Li", 3, 1, 2, 1, 0.98),
    "Be": Element("Be", 4, 2, 2, 2, 1.57),
    "B": Element("B", 5, 13, 2, 3, 2.04),
    "C": Element("C", 6, 14, 2, 4, 2.55),
    "N": Element("N", 7, 15, 2, 3, 3.04),
    "O": Element("O", 8, 16, 2, 2, 3.44),
    "F": Element("F", 9, 17, 2, 1, 3.98),
    "Ne": Element("Ne", 10, 18, 2, 0, 0.0, witness_stable=True),
    "Na": Element("Na", 11, 1, 3, 1, 0.93),
    "Mg": Element("Mg", 12, 2, 3, 2, 1.31),
    "Al": Element("Al", 13, 13, 3, 3, 1.61),
    "Si": Element("Si", 14, 14, 3, 4, 1.90),
    "P": Element("P", 15, 15, 3, 3, 2.19),
    "S": Element("S", 16, 16, 3, 2, 2.58),
    "Cl": Element("Cl", 17, 17, 3, 1, 3.16),
    "Ar": Element("Ar", 18, 18, 3, 0, 0.0, witness_stable=True),
    "K": Element("K", 19, 1, 4, 1, 0.82),
    "Ca": Element("Ca", 20, 2, 4, 2, 1.00),
    "Fe": Element("Fe", 26, 8, 4, 2, 1.83),
    "Cu": Element("Cu", 29, 11, 4, 2, 1.90),
    "Zn": Element("Zn", 30, 12, 4, 2, 1.65),
    "Br": Element("Br", 35, 17, 4, 1, 2.96),
    "Ag": Element("Ag", 47, 11, 5, 1, 1.93),
    "I": Element("I", 53, 17, 5, 1, 2.66),
    "Au": Element("Au", 79, 11, 6, 3, 2.54),
    "Pb": Element("Pb", 82, 14, 6, 2, 2.33),
}

_SYMBOL_BY_LOWER: Dict[str, str] = {s.lower(): s for s in PERIODIC_TABLE}
_FORMULA_TOKEN = re.compile(r"^([A-Z][a-z]?\d*)+$")
_FORMULA_PART = re.compile(r"([A-Z][a-z]?)(\d*)")


def chemical_element(token: str) -> Optional[Element]:
    """The real periodic-table Element if the token is an element symbol, else None.

    Case-insensitive (h/H -> Hydrogen). Opt-in for chemistry surfaces; does not
    change classify_token_semantic or the encoder trit face.
    """
    if not token:
        return None
    canon = _SYMBOL_BY_LOWER.get(token.strip().lower())
    return PERIODIC_TABLE[canon] if canon else None


def parse_formula(token: str) -> Optional[Dict[str, int]]:
    """Parse a chemical formula (H2O, CO2, C3H8, NaCl) into {symbol: count}.

    Returns None unless the token is a well-formed formula over KNOWN elements,
    so plain words ('loop') and unknown symbols return None rather than a false
    compound. Requires canonical capitalization (H2O, not h2o).
    """
    if not token:
        return None
    raw = token.strip()
    if not _FORMULA_TOKEN.match(raw):
        return None
    composition: Dict[str, int] = {}
    consumed = 0
    for sym, count in _FORMULA_PART.findall(raw):
        if sym not in PERIODIC_TABLE:
            return None
        composition[sym] = composition.get(sym, 0) + (int(count) if count else 1)
        consumed += len(sym) + len(count)
    if consumed != len(raw) or not composition:
        return None
    return composition


def _project_element_to_channels(element: Element) -> Tuple[float, float, float, float, float, float]:
    """
    Project periodic features into six scalar channels before ternary quantization.

    The scaling is chosen for stable, interpretable defaults rather than physical
    realism. Witness-stable elements bias toward neutral outputs.
    """
    witness_bias = 0.0 if element.witness_stable else 1.0

    ko = (19.0 - float(max(1, min(18, element.group)))) * witness_bias
    av = float(element.period) - 2.0
    ru = (1.5 if element.witness_stable else 0.0) + (float(element.Z % 7) / 10.0)
    ca = float(element.valence) - 1.5
    um = float(element.electronegativity) - 2.0
    dr = (float(element.group + element.period) / 2.0) - 5.0
    return ko, av, ru, ca, um, dr


def trit(value: float, *, pos: float, neg: float) -> int:
    if value > pos:
        return 1
    if value < neg:
        return -1
    return 0


def semantic_band_flag(semantic_class: SemanticClass) -> int:
    return SEMANTIC_BAND_FLAGS[semantic_class]


def is_negative_atomic_state(
    semantic_class: SemanticClass,
    element: Element,
) -> bool:
    return semantic_class == "NEGATION" or element.electronegativity >= 2.8


def infer_dual_state(
    token: str,
    semantic_class: SemanticClass,
    element: Element,
) -> DualState:
    if element.witness_stable:
        return None
    if semantic_class in PRIMARY_DUAL_CLASSES:
        return 0
    if semantic_class in SHADOW_DUAL_CLASSES:
        return 1
    digest = sha256(f"{semantic_class}:{token.lower()}".encode("utf-8")).digest()
    return 0 if digest[0] % 2 == 0 else 1


def compute_resilience(
    semantic_class: SemanticClass,
    element: Element,
) -> float:
    base = 0.25
    base += min(float(element.period), 4.0) * 0.10
    base += min(float(element.valence), 4.0) * 0.04
    if element.witness_stable:
        base += 0.20
    if semantic_class in {"RELATION", "TEMPORAL"}:
        base += 0.08
    if semantic_class == "NEGATION":
        base -= 0.06
    return float(max(0.05, min(0.98, base)))


def compute_adaptivity(
    semantic_class: SemanticClass,
    element: Element,
) -> float:
    base = 0.18
    base += min(float(element.valence), 4.0) * 0.10
    base += float(element.group % 6) / 10.0
    if semantic_class in {"RELATION", "MODIFIER", "TEMPORAL"}:
        base += 0.16
    if semantic_class == "INERT_WITNESS":
        base -= 0.08
    return float(max(0.05, min(0.99, base)))


def compute_trust_baseline(
    semantic_class: SemanticClass,
    element: Element,
    *,
    resilience: float,
    adaptivity: float,
) -> float:
    base = 0.10 + (resilience * 0.55) + (adaptivity * 0.20)
    if element.witness_stable:
        base += 0.10
    if semantic_class == "NEGATION":
        base -= 0.08
    return float(max(0.0, min(1.0, base)))


def atomic_drift_scale(
    state: AtomicTokenState,
    *,
    base_noise: float = 0.005,
    trust_factor: float = 1.0,
) -> float:
    neg_factor = 1.5 if state.negative_state else 1.0
    if state.dual_state == 0:
        dual_multiplier = 0.7
    elif state.dual_state == 1:
        dual_multiplier = 1.3
    else:
        dual_multiplier = 1.0
    trust_damping = max(0.3, float(trust_factor))
    scale = base_noise * neg_factor * dual_multiplier * (1.0 - state.resilience)
    scale *= max(0.3, 1.0 - (0.35 * state.adaptivity))
    scale /= trust_damping
    return float(max(0.0, scale))


def element_to_trit_vector(
    element: Element,
    *,
    thresholds: Optional[Dict[Tongue, Tuple[float, float]]] = None,
) -> TritVector:
    thresholds = thresholds or {
        "KO": (10.0, -10.0),
        "AV": (1.5, -1.5),
        "RU": (0.8, -0.8),
        "CA": (1.0, -1.0),
        "UM": (0.6, -0.6),
        "DR": (2.0, -2.0),
    }

    ko, av, ru, ca, um, dr = _project_element_to_channels(element)
    values: Dict[Tongue, float] = {
        "KO": ko,
        "AV": av,
        "RU": ru,
        "CA": ca,
        "UM": um,
        "DR": dr,
    }
    return TritVector(
        **{tongue: trit(values[tongue], pos=thresholds[tongue][0], neg=thresholds[tongue][1]) for tongue in TONGUES}
    )


def element_to_tau(
    element: Element,
    *,
    thresholds: Optional[Dict[Tongue, Tuple[float, float]]] = None,
) -> Dict[Tongue, int]:
    return element_to_trit_vector(element, thresholds=thresholds).as_dict()


def map_token_to_atomic_state(
    token: str,
    *,
    language: Language = None,
    context_class: ContextClass = None,
    element_table: Optional[Dict[SemanticClass, Element]] = None,
    thresholds: Optional[Dict[Tongue, Tuple[float, float]]] = None,
) -> AtomicTokenState:
    classification = classify_token_semantic_with_evidence(
        token,
        language=language,
        context_class=context_class,
    )
    semantic_class = classification.semantic_class
    element = (element_table or DEFAULT_ELEMENTS)[semantic_class]
    tau = element_to_trit_vector(element, thresholds=thresholds)
    negative_state = is_negative_atomic_state(semantic_class, element)
    dual_state = infer_dual_state(token, semantic_class, element)
    band_flag = semantic_band_flag(semantic_class)
    resilience = compute_resilience(semantic_class, element)
    adaptivity = compute_adaptivity(semantic_class, element)
    trust_baseline = compute_trust_baseline(
        semantic_class,
        element,
        resilience=resilience,
        adaptivity=adaptivity,
    )
    return AtomicTokenState(
        token=token,
        language=language,
        code_lane=None,
        context_class=context_class,
        semantic_class=semantic_class,
        element=element,
        tau=tau,
        negative_state=negative_state,
        dual_state=dual_state,
        band_flag=band_flag,
        resilience=resilience,
        adaptivity=adaptivity,
        trust_baseline=trust_baseline,
        semantic_resolved=classification.resolved,
        semantic_source=classification.source,
        lexical_domains=classification.lexical_domains,
    )


def tokens_to_tau_sequence(
    tokens: Sequence[str],
    *,
    language: Language = None,
    context_class: ContextClass = None,
    element_table: Optional[Dict[SemanticClass, Element]] = None,
) -> list[Dict[Tongue, int]]:
    return [
        map_token_to_atomic_state(
            token,
            language=language,
            context_class=context_class,
            element_table=element_table,
        ).tau.as_dict()
        for token in tokens
    ]
