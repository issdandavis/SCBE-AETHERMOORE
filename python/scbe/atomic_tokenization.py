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

from dataclasses import dataclass
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

# Chemistry-aware element table: maps token strings to real periodic-table elements.
# Used when language="chemistry" or context_class="molecular".
CHEMISTRY_ELEMENTS: Dict[str, Element] = {
    "c": Element(symbol="C", Z=6, group=14, period=2, valence=4, electronegativity=2.55),
    "carbon_aromatic": Element(symbol="C", Z=6, group=14, period=2, valence=4, electronegativity=2.55),
    "n": Element(symbol="N", Z=7, group=15, period=2, valence=3, electronegativity=3.04),
    "nitrogen_aromatic": Element(symbol="N", Z=7, group=15, period=2, valence=3, electronegativity=3.04),
    "o": Element(symbol="O", Z=8, group=16, period=2, valence=2, electronegativity=3.44),
    "oxygen_aromatic": Element(symbol="O", Z=8, group=16, period=2, valence=2, electronegativity=3.44),
    "s": Element(symbol="S", Z=16, group=16, period=3, valence=2, electronegativity=2.58),
    "sulfur_aromatic": Element(symbol="S", Z=16, group=16, period=3, valence=2, electronegativity=2.58),
    "p": Element(symbol="P", Z=15, group=15, period=3, valence=3, electronegativity=2.19),
    "phosphorus_aromatic": Element(symbol="P", Z=15, group=15, period=3, valence=3, electronegativity=2.19),
    "h": Element(symbol="H", Z=1, group=1, period=1, valence=1, electronegativity=2.20),
    "f": Element(symbol="F", Z=9, group=17, period=2, valence=1, electronegativity=3.98),
    "cl": Element(symbol="Cl", Z=17, group=17, period=3, valence=1, electronegativity=3.16),
    "br": Element(symbol="Br", Z=35, group=17, period=4, valence=1, electronegativity=2.96),
    "i": Element(symbol="I", Z=53, group=17, period=5, valence=1, electronegativity=2.66),
    "si": Element(symbol="Si", Z=14, group=14, period=3, valence=4, electronegativity=1.90),
    "se": Element(symbol="Se", Z=34, group=16, period=4, valence=2, electronegativity=2.55),
    "as": Element(symbol="As", Z=33, group=15, period=4, valence=3, electronegativity=2.18),
    "na": Element(symbol="Na", Z=11, group=1, period=3, valence=1, electronegativity=0.93),
    "mg": Element(symbol="Mg", Z=12, group=2, period=3, valence=2, electronegativity=1.31),
    "al": Element(symbol="Al", Z=13, group=13, period=3, valence=3, electronegativity=1.61),
    "ca": Element(symbol="Ca", Z=20, group=2, period=4, valence=2, electronegativity=1.00),
    "fe": Element(symbol="Fe", Z=26, group=8, period=4, valence=2, electronegativity=1.83),
    "cu": Element(symbol="Cu", Z=29, group=11, period=4, valence=2, electronegativity=1.90),
    "zn": Element(symbol="Zn", Z=30, group=12, period=4, valence=2, electronegativity=1.65),
    "b": Element(symbol="B", Z=5, group=13, period=2, valence=3, electronegativity=2.04),
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
    "then": "RELATION",
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
    "molecular": {
        "c": "ENTITY",
        "n": "ENTITY",
        "o": "ENTITY",
        "s": "ENTITY",
        "p": "ENTITY",
        "carbon_aromatic": "ENTITY",
        "nitrogen_aromatic": "ENTITY",
        "oxygen_aromatic": "ENTITY",
        "sulfur_aromatic": "ENTITY",
        "phosphorus_aromatic": "ENTITY",
        "double_bond": "ACTION",
        "triple_bond": "ACTION",
        "branch_open": "RELATION",
        "branch_close": "RELATION",
        "ring_1": "TEMPORAL",
        "ring_2": "TEMPORAL",
        "ring_3": "TEMPORAL",
        "ring_4": "TEMPORAL",
        "ring_5": "TEMPORAL",
        "ring_6": "TEMPORAL",
        "ring_7": "TEMPORAL",
        "ring_8": "TEMPORAL",
        "ring_9": "TEMPORAL",
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


def classify_token_semantic(
    token: str,
    *,
    language: Language = None,
    context_class: ContextClass = None,
) -> SemanticClass:
    """
    Deterministic semantic classifier implementing the runtime approximation of
    phi: V x L x C -> P.
    """
    t = _normalized_token(token)
    lang = _normalized_language(language)
    context = _normalized_context(context_class)

    if not t:
        return "INERT_WITNESS"

    context_overrides = CONTEXT_TOKEN_OVERRIDES.get(context)
    if context_overrides and t in context_overrides:
        return context_overrides[t]

    language_overrides = LANGUAGE_TOKEN_OVERRIDES.get(lang)
    if language_overrides and t in language_overrides:
        return language_overrides[t]

    if t in TOKEN_CLASS_OVERRIDES:
        return TOKEN_CLASS_OVERRIDES[t]

    if t.endswith("ing") or t.endswith("ed"):
        return "ACTION"

    if t.endswith("ly"):
        return "MODIFIER"

    return "ENTITY"


def map_token_to_element(
    token: str,
    *,
    language: Language = None,
    context_class: ContextClass = None,
    element_table: Optional[Dict[SemanticClass, Element]] = None,
) -> Element:
    t = _normalized_token(token)
    lang = _normalized_language(language)
    context = _normalized_context(context_class)

    # Chemistry mode: use real periodic-table elements
    if lang == "chemistry" or context == "molecular":
        chem_el = CHEMISTRY_ELEMENTS.get(t)
        if chem_el is not None:
            return chem_el

    element_table = element_table or DEFAULT_ELEMENTS
    semantic_class = classify_token_semantic(token, language=language, context_class=context_class)
    return element_table[semantic_class]


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
    base += (float(element.group % 6) / 10.0)
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
        **{
            tongue: trit(values[tongue], pos=thresholds[tongue][0], neg=thresholds[tongue][1])
            for tongue in TONGUES
        }
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
    semantic_class = classify_token_semantic(token, language=language, context_class=context_class)
    element = map_token_to_element(token, language=language, context_class=context_class)
    if element_table and semantic_class in element_table:
        element = element_table[semantic_class]
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
