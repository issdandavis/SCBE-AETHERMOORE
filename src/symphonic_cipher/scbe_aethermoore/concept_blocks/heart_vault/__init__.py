"""
Heart Vault — Cultural Intelligence for the SCBE Fleet
=========================================================

The Heart Vault is the qualitative soul of SCBE-AETHERMOORE.  While the
14-layer governance pipeline provides the mathematical "bouncer," the
Heart Vault provides the cultural data that lets AI agents navigate
human nuance — metaphors, emotions, proverbs, and literary depth.

Modules:
    graph         — SQLite knowledge graph (nodes + edges + queries)
    emotions      — Plutchik emotion taxonomy + Poincaré Ball projection
    literary      — Literary device detection + metaphor resolution
    heart_credit  — Heart Credit extension of MMCCL

Architecture mapping:
    Layer 1–2  (Complex Context) ← emotion/literary metadata
    Layer 3–4  (Poincaré Ball)   ← valence/arousal → hyperbolic coords
    Layer 5    (Governance Mesh) ← Runethic quality gates
    Layer 10   (Constitutional)  ← cultural bias filtering
    MMCCL      (Credit Ledger)   ← Heart Credits for contribute/query

Sacred Tongue governance:
    KO (Kor'aelin)    — Orchestrates data ingestion (ATOMIC, ECoK)
    AV (Avali)        — Manages API connections (Gutendex, Wikiquote)
    RU (Runethic)     — Quality gates (prevents toxic/biased wisdom)
    CA (Cassisivadan) — Structural analysis of literary patterns
    UM (Umbroth)      — Handles ambiguity and mystery in metaphor
    DR (Draumric)     — Deep structural ordering and taxonomy
"""

from .graph import (
    HeartVaultGraph,
    Node,
    Edge,
    NodeType,
    EdgeType,
    TongueAffinity,
)
from .emotions import (
    EMOTION_LIBRARY,
    EmotionFamily,
    EmotionIntensity,
    EmotionSpec,
    classify_emotion,
    emotion_to_poincare,
    emotional_distance,
    poincare_distance,
    valence_arousal_to_poincare,
)
from .literary import (
    METAPHOR_MAP,
    LiteraryDevice,
    LiteraryHit,
    MetaphorMapping,
    detect_literary_devices,
    resolve_metaphor,
)
from .heart_credit import (
    HeartCreditEntry,
    HeartCreditLedger,
    CreditAction,
    TONGUE_WEIGHTS,
    BASE_CONTRIBUTE_REWARD,
    BASE_QUERY_COST,
    VALIDATION_BONUS,
    PENALTY_AMOUNT,
)

__all__ = [
    # Graph
    "HeartVaultGraph",
    "Node",
    "Edge",
    "NodeType",
    "EdgeType",
    "TongueAffinity",
    # Emotions
    "EMOTION_LIBRARY",
    "EmotionFamily",
    "EmotionIntensity",
    "EmotionSpec",
    "classify_emotion",
    "emotion_to_poincare",
    "emotional_distance",
    "poincare_distance",
    "valence_arousal_to_poincare",
    # Literary
    "METAPHOR_MAP",
    "LiteraryDevice",
    "LiteraryHit",
    "MetaphorMapping",
    "detect_literary_devices",
    "resolve_metaphor",
    # Heart Credits
    "HeartCreditEntry",
    "HeartCreditLedger",
    "CreditAction",
    "TONGUE_WEIGHTS",
    "BASE_CONTRIBUTE_REWARD",
    "BASE_QUERY_COST",
    "VALIDATION_BONUS",
    "PENALTY_AMOUNT",
]
