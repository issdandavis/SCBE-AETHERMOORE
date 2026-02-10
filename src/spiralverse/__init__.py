"""
Spiralverse 6-Language Interoperability Codex System v2.0
=========================================================

Multi-dimensional AI communication protocol with creative worldbuilding integration.

Modules:
- hive_memory: Auto-save & distributed backup (AET protocol)
- polyglot_alphabet: 6-tongue modular alphabets with signatures
- vector_6d: 6D navigation system (AXIOM, FLOW, GLYPH, ORACLE, CHARM, LEDGER)
- proximity_optimizer: Distance-based protocol compression
- rwp2_envelope: Secure message structure with multi-tongue signatures

Core Theorems:
- Theorem 1: Six Sacred Tongues as Protocol Domains (6D orthogonal basis)
- Theorem 2: Roundtable Multi-Signature Governance (S(N) = B * R^(N^2))
- Theorem 3: Topology-Gated Dual-Lane Authorization
- Theorem 4: Hybrid Envelope Architecture (RWP2)

"Invitation over Command, Connection over Control"
"""

__version__ = "2.0.0"

# === Hive Memory Management (AET Protocol) ===
from .hive_memory import (
    MemoryTier,
    EvictionPriority,
    MemoryBlock,
    AgentSnapshot,
    MemoryEvictionEngine,
    AdaptiveSyncScheduler,
    HiveClient,
    AgentMemorySystem,
    AutoSaveWorker,
    OfflineResilience,
)

# === Polyglot Alphabet System ===
from .polyglot_alphabet import (
    TongueID,
    TongueAlphabet,
    AXIOM_ALPHABET,
    FLOW_ALPHABET,
    GLYPH_ALPHABET,
    ORACLE_ALPHABET,
    CHARM_ALPHABET,
    LEDGER_ALPHABET,
    TONGUE_ALPHABETS,
    UNIVERSAL_LETTERS,
    UNIVERSAL_SYMBOLS,
    verify_tongue_signature,
    identify_tongue,
    compose_polyglot_message,
    decompose_polyglot_message,
    PolyglotSDK,
    calculate_cipher_strength,
)

# === 6D Vector Navigation ===
from .vector_6d import (
    Axis,
    AXIS_INFO,
    Position6D,
    euclidean_distance_6d,
    weighted_distance_6d,
    hyperbolic_distance_6d,
    DockingLock,
    DockingSystem,
    SwarmFormation,
    ConvergenceDetector,
)

# === Proximity-Based Optimization ===
from .proximity_optimizer import (
    ProtocolLevel,
    DISTANCE_THRESHOLDS,
    LEVEL_TONGUES,
    LEVEL_BYTE_SIZES,
    HysteresisController,
    OptimizedMessage,
    ProximityEncoder,
    ProximityDecoder,
    BandwidthStats,
    BandwidthMonitor,
    FormationOptimizer,
)

# === RWP2 Envelope Architecture ===
from .rwp2_envelope import (
    ProtocolTongue,
    TONGUE_KEYS,
    OperationTier,
    TIER_REQUIRED_TONGUES,
    TIER_SECURITY_MULTIPLIERS,
    SpelltextData,
    parse_spelltext,
    build_spelltext,
    RWP2Envelope,
    SignatureEngine,
    ReplayProtector,
    EnvelopeFactory,
)

# === Temporal Intent Scaling ===
from .temporal_intent import (
    IntentState,
    IntentSample,
    IntentHistory,
    TemporalSecurityGate,
    harmonic_wall_basic,
    harmonic_wall_temporal,
    compare_scaling,
    R_HARMONIC,
    INTENT_DECAY_RATE,
    MAX_INTENT_ACCUMULATION,
)

# === Aethercode Interpreter ===
from .aethercode import (
    AetherVerse,
    AetherProgram,
    AetherContext,
    AethercodeInterpreter,
    ChantSynthesizer,
    parse_verse,
    parse_program,
    TONGUE_FREQUENCIES,
    TONGUE_DOMAINS,
    HELLO_WORLD,
    FIBONACCI,
    FULL_DEMO,
)

__all__ = [
    # Version
    "__version__",

    # === Hive Memory ===
    "MemoryTier",
    "EvictionPriority",
    "MemoryBlock",
    "AgentSnapshot",
    "MemoryEvictionEngine",
    "AdaptiveSyncScheduler",
    "HiveClient",
    "AgentMemorySystem",
    "AutoSaveWorker",
    "OfflineResilience",

    # === Polyglot Alphabet ===
    "TongueID",
    "TongueAlphabet",
    "AXIOM_ALPHABET",
    "FLOW_ALPHABET",
    "GLYPH_ALPHABET",
    "ORACLE_ALPHABET",
    "CHARM_ALPHABET",
    "LEDGER_ALPHABET",
    "TONGUE_ALPHABETS",
    "UNIVERSAL_LETTERS",
    "UNIVERSAL_SYMBOLS",
    "verify_tongue_signature",
    "identify_tongue",
    "compose_polyglot_message",
    "decompose_polyglot_message",
    "PolyglotSDK",
    "calculate_cipher_strength",

    # === 6D Vector Navigation ===
    "Axis",
    "AXIS_INFO",
    "Position6D",
    "euclidean_distance_6d",
    "weighted_distance_6d",
    "hyperbolic_distance_6d",
    "DockingLock",
    "DockingSystem",
    "SwarmFormation",
    "ConvergenceDetector",

    # === Proximity Optimization ===
    "ProtocolLevel",
    "DISTANCE_THRESHOLDS",
    "LEVEL_TONGUES",
    "LEVEL_BYTE_SIZES",
    "HysteresisController",
    "OptimizedMessage",
    "ProximityEncoder",
    "ProximityDecoder",
    "BandwidthStats",
    "BandwidthMonitor",
    "FormationOptimizer",

    # === RWP2 Envelope ===
    "ProtocolTongue",
    "TONGUE_KEYS",
    "OperationTier",
    "TIER_REQUIRED_TONGUES",
    "TIER_SECURITY_MULTIPLIERS",
    "SpelltextData",
    "parse_spelltext",
    "build_spelltext",
    "RWP2Envelope",
    "SignatureEngine",
    "ReplayProtector",
    "EnvelopeFactory",

    # === Temporal Intent Scaling ===
    "IntentState",
    "IntentSample",
    "IntentHistory",
    "TemporalSecurityGate",
    "harmonic_wall_basic",
    "harmonic_wall_temporal",
    "compare_scaling",
    "R_HARMONIC",
    "INTENT_DECAY_RATE",
    "MAX_INTENT_ACCUMULATION",

    # === Aethercode Interpreter ===
    "AetherVerse",
    "AetherProgram",
    "AetherContext",
    "AethercodeInterpreter",
    "ChantSynthesizer",
    "parse_verse",
    "parse_program",
    "TONGUE_FREQUENCIES",
    "TONGUE_DOMAINS",
    "HELLO_WORLD",
    "FIBONACCI",
    "FULL_DEMO",
]
