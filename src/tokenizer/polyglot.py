"""
Polyglot Alphabet System for Spiralverse v2.0

Six domain-specific alphabets mapped to Sacred Tongues and 6D axes:

| Alphabet | Tongue | 6D Axis | Domain               |
|----------|--------|---------|----------------------|
| AXIOM    | KO     | X       | Logic, formal proofs |
| FLOW     | AV     | Y       | Data pipelines       |
| GLYPH    | RU     | Z       | Visual, state UI     |
| ORACLE   | CA     | V       | Queries, uncertainty |
| CHARM    | UM     | H       | Social, trust        |
| LEDGER   | DR     | S       | Finance, auditing    |

@module tokenizer/polyglot
@layer Layer 1, Layer 2
@version 1.0.0
@since 2026-02-02
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
import math
import hashlib

# ============================================================================
# Constants
# ============================================================================

PHI = 1.618033988749895  # Golden ratio


class AlphabetType(Enum):
    """Six polyglot alphabet types."""
    AXIOM = "axiom"    # Logic/formal proofs (KO - X axis)
    FLOW = "flow"      # Data pipelines (AV - Y axis)
    GLYPH = "glyph"    # Visual/UI state (RU - Z axis)
    ORACLE = "oracle"  # Queries/uncertainty (CA - V axis)
    CHARM = "charm"    # Social/trust (UM - H axis)
    LEDGER = "ledger"  # Finance/auditing (DR - S axis)


class SacredTonguePolyglot(Enum):
    """Sacred Tongues for polyglot mapping."""
    KO = "ko"  # Light
    AV = "av"  # Water
    RU = "ru"  # Wood
    CA = "ca"  # Fire
    UM = "um"  # Earth
    DR = "dr"  # Metal


# Tongue to Alphabet mapping
TONGUE_TO_ALPHABET: Dict[SacredTonguePolyglot, AlphabetType] = {
    SacredTonguePolyglot.KO: AlphabetType.AXIOM,
    SacredTonguePolyglot.AV: AlphabetType.FLOW,
    SacredTonguePolyglot.RU: AlphabetType.GLYPH,
    SacredTonguePolyglot.CA: AlphabetType.ORACLE,
    SacredTonguePolyglot.UM: AlphabetType.CHARM,
    SacredTonguePolyglot.DR: AlphabetType.LEDGER,
}

# 6D Axis to Alphabet mapping
AXIS_TO_ALPHABET: Dict[str, AlphabetType] = {
    "x": AlphabetType.AXIOM,   # Physical X
    "y": AlphabetType.FLOW,    # Physical Y
    "z": AlphabetType.GLYPH,   # Physical Z
    "v": AlphabetType.ORACLE,  # Operational V (velocity)
    "h": AlphabetType.CHARM,   # Operational H (harmony)
    "s": AlphabetType.LEDGER,  # Operational S (security)
    # Alternative names
    "axiom": AlphabetType.AXIOM,
    "flow": AlphabetType.FLOW,
    "glyph": AlphabetType.GLYPH,
    "oracle": AlphabetType.ORACLE,
    "charm": AlphabetType.CHARM,
    "ledger": AlphabetType.LEDGER,
}


# ============================================================================
# Alphabet Definitions
# ============================================================================

@dataclass
class AlphabetCharacter:
    """Single character in a polyglot alphabet."""
    symbol: str           # Unicode symbol
    name: str             # Human-readable name
    code_point: int       # Unicode code point
    category: str         # Functional category
    weight: float = 1.0   # Semantic weight


@dataclass
class PolyglotAlphabet:
    """Complete alphabet for a domain."""
    alphabet_type: AlphabetType
    tongue: SacredTonguePolyglot
    axis: str
    domain: str
    description: str
    characters: List[AlphabetCharacter] = field(default_factory=list)
    phi_weight: float = 1.0

    def __post_init__(self):
        # Calculate φ-based weight from tongue position
        tongue_indices = {
            SacredTonguePolyglot.KO: 0,
            SacredTonguePolyglot.AV: 1,
            SacredTonguePolyglot.RU: 2,
            SacredTonguePolyglot.CA: 3,
            SacredTonguePolyglot.UM: 4,
            SacredTonguePolyglot.DR: 5,
        }
        self.phi_weight = PHI ** tongue_indices[self.tongue]

    def get_symbol(self, index: int) -> Optional[str]:
        """Get symbol at index."""
        if 0 <= index < len(self.characters):
            return self.characters[index].symbol
        return None

    def get_index(self, symbol: str) -> int:
        """Get index of symbol (-1 if not found)."""
        for i, char in enumerate(self.characters):
            if char.symbol == symbol:
                return i
        return -1

    def contains(self, symbol: str) -> bool:
        """Check if alphabet contains symbol."""
        return any(c.symbol == symbol for c in self.characters)


# ============================================================================
# Alphabet Definitions - Character Sets
# ============================================================================

# AXIOM Alphabet (KO - Logic/Formal Proofs)
AXIOM_CHARACTERS = [
    # Latin letters for variables
    AlphabetCharacter("A", "alpha", ord("A"), "variable"),
    AlphabetCharacter("B", "beta", ord("B"), "variable"),
    AlphabetCharacter("C", "gamma", ord("C"), "variable"),
    AlphabetCharacter("P", "proposition", ord("P"), "proposition"),
    AlphabetCharacter("Q", "query", ord("Q"), "proposition"),
    AlphabetCharacter("R", "result", ord("R"), "proposition"),
    # Logical operators
    AlphabetCharacter("∀", "for_all", 0x2200, "quantifier", 2.0),
    AlphabetCharacter("∃", "exists", 0x2203, "quantifier", 2.0),
    AlphabetCharacter("∄", "not_exists", 0x2204, "quantifier", 2.0),
    AlphabetCharacter("∧", "and", 0x2227, "connective", 1.5),
    AlphabetCharacter("∨", "or", 0x2228, "connective", 1.5),
    AlphabetCharacter("¬", "not", 0x00AC, "connective", 1.5),
    AlphabetCharacter("→", "implies", 0x2192, "connective", 1.8),
    AlphabetCharacter("↔", "iff", 0x2194, "connective", 2.0),
    AlphabetCharacter("⊢", "proves", 0x22A2, "turnstile", 2.5),
    AlphabetCharacter("⊨", "models", 0x22A8, "turnstile", 2.5),
    AlphabetCharacter("⊥", "contradiction", 0x22A5, "constant", 3.0),
    AlphabetCharacter("⊤", "tautology", 0x22A4, "constant", 3.0),
    # Set operations
    AlphabetCharacter("∈", "element_of", 0x2208, "set", 1.5),
    AlphabetCharacter("∉", "not_element", 0x2209, "set", 1.5),
    AlphabetCharacter("⊆", "subset", 0x2286, "set", 1.5),
    AlphabetCharacter("⊇", "superset", 0x2287, "set", 1.5),
    AlphabetCharacter("∅", "empty_set", 0x2205, "set", 2.0),
    AlphabetCharacter("∪", "union", 0x222A, "set", 1.5),
    AlphabetCharacter("∩", "intersection", 0x2229, "set", 1.5),
    # Modal logic
    AlphabetCharacter("□", "necessary", 0x25A1, "modal", 2.5),
    AlphabetCharacter("◇", "possible", 0x25C7, "modal", 2.5),
    # Equality
    AlphabetCharacter("=", "equals", ord("="), "relation"),
    AlphabetCharacter("≠", "not_equals", 0x2260, "relation"),
    AlphabetCharacter("≡", "equivalent", 0x2261, "relation", 1.5),
]

# FLOW Alphabet (AV - Data Pipelines)
FLOW_CHARACTERS = [
    # Directional arrows
    AlphabetCharacter("→", "right_arrow", 0x2192, "direction"),
    AlphabetCharacter("←", "left_arrow", 0x2190, "direction"),
    AlphabetCharacter("↔", "bidirectional", 0x2194, "direction"),
    AlphabetCharacter("↑", "up_arrow", 0x2191, "direction"),
    AlphabetCharacter("↓", "down_arrow", 0x2193, "direction"),
    # Double arrows (transformations)
    AlphabetCharacter("⇒", "transform_to", 0x21D2, "transform", 1.5),
    AlphabetCharacter("⇐", "transform_from", 0x21D0, "transform", 1.5),
    AlphabetCharacter("⇔", "bidirect_transform", 0x21D4, "transform", 2.0),
    AlphabetCharacter("⇑", "elevate", 0x21D1, "transform", 1.5),
    AlphabetCharacter("⇓", "descend", 0x21D3, "transform", 1.5),
    # Pipeline operators
    AlphabetCharacter("|", "pipe", ord("|"), "operator"),
    AlphabetCharacter("│", "vertical_pipe", 0x2502, "operator"),
    AlphabetCharacter("┃", "heavy_pipe", 0x2503, "operator", 1.5),
    AlphabetCharacter("╏", "dashed_pipe", 0x254F, "operator"),
    # Flow control
    AlphabetCharacter("⊲", "input", 0x22B2, "flow", 1.5),
    AlphabetCharacter("⊳", "output", 0x22B3, "flow", 1.5),
    AlphabetCharacter("⧫", "merge", 0x2666, "flow", 2.0),
    AlphabetCharacter("⬢", "split", 0x2B22, "flow", 2.0),
    # Stream markers
    AlphabetCharacter("∞", "infinite_stream", 0x221E, "stream", 3.0),
    AlphabetCharacter("∂", "partial", 0x2202, "stream"),
    AlphabetCharacter("∆", "delta", 0x2206, "stream", 1.5),
    AlphabetCharacter("∇", "gradient", 0x2207, "stream", 1.5),
    # Buffer/queue
    AlphabetCharacter("[", "buffer_start", ord("["), "buffer"),
    AlphabetCharacter("]", "buffer_end", ord("]"), "buffer"),
    AlphabetCharacter("⟦", "queue_start", 0x27E6, "buffer", 1.5),
    AlphabetCharacter("⟧", "queue_end", 0x27E7, "buffer", 1.5),
]

# GLYPH Alphabet (RU - Visual/UI State)
GLYPH_CHARACTERS = [
    # Basic shapes
    AlphabetCharacter("●", "filled_circle", 0x25CF, "circle"),
    AlphabetCharacter("○", "empty_circle", 0x25CB, "circle"),
    AlphabetCharacter("◉", "target_circle", 0x25C9, "circle", 1.5),
    AlphabetCharacter("◎", "double_circle", 0x25CE, "circle", 1.5),
    AlphabetCharacter("◐", "half_circle_left", 0x25D0, "circle"),
    AlphabetCharacter("◑", "half_circle_right", 0x25D1, "circle"),
    # Squares
    AlphabetCharacter("■", "filled_square", 0x25A0, "square"),
    AlphabetCharacter("□", "empty_square", 0x25A1, "square"),
    AlphabetCharacter("▣", "crossed_square", 0x25A3, "square", 1.5),
    AlphabetCharacter("▤", "horizontal_square", 0x25A4, "square"),
    AlphabetCharacter("▥", "vertical_square", 0x25A5, "square"),
    # Triangles
    AlphabetCharacter("▲", "filled_triangle_up", 0x25B2, "triangle"),
    AlphabetCharacter("△", "empty_triangle_up", 0x25B3, "triangle"),
    AlphabetCharacter("▼", "filled_triangle_down", 0x25BC, "triangle"),
    AlphabetCharacter("▽", "empty_triangle_down", 0x25BD, "triangle"),
    AlphabetCharacter("◀", "filled_triangle_left", 0x25C0, "triangle"),
    AlphabetCharacter("▶", "filled_triangle_right", 0x25B6, "triangle"),
    # Diamonds
    AlphabetCharacter("◆", "filled_diamond", 0x25C6, "diamond"),
    AlphabetCharacter("◇", "empty_diamond", 0x25C7, "diamond"),
    AlphabetCharacter("❖", "ornate_diamond", 0x2756, "diamond", 1.5),
    # Stars
    AlphabetCharacter("★", "filled_star", 0x2605, "star", 1.5),
    AlphabetCharacter("☆", "empty_star", 0x2606, "star", 1.5),
    AlphabetCharacter("✦", "four_star", 0x2726, "star"),
    AlphabetCharacter("✧", "four_star_empty", 0x2727, "star"),
    # State indicators
    AlphabetCharacter("✓", "check", 0x2713, "state", 2.0),
    AlphabetCharacter("✗", "cross", 0x2717, "state", 2.0),
    AlphabetCharacter("⏸", "pause", 0x23F8, "state"),
    AlphabetCharacter("⏹", "stop", 0x23F9, "state"),
    AlphabetCharacter("⏺", "record", 0x23FA, "state", 1.5),
]

# ORACLE Alphabet (CA - Queries/Uncertainty)
ORACLE_CHARACTERS = [
    # Question marks
    AlphabetCharacter("?", "question", ord("?"), "query"),
    AlphabetCharacter("¿", "inverted_question", 0x00BF, "query"),
    AlphabetCharacter("⁇", "double_question", 0x2047, "query", 1.5),
    AlphabetCharacter("⁈", "question_exclaim", 0x2048, "query", 1.5),
    AlphabetCharacter("⁉", "exclaim_question", 0x2049, "query", 1.5),
    # Exclamation
    AlphabetCharacter("!", "exclaim", ord("!"), "assertion"),
    AlphabetCharacter("¡", "inverted_exclaim", 0x00A1, "assertion"),
    AlphabetCharacter("‼", "double_exclaim", 0x203C, "assertion", 1.5),
    # Uncertainty markers
    AlphabetCharacter("≈", "approximately", 0x2248, "uncertainty"),
    AlphabetCharacter("≃", "asymptotically", 0x2243, "uncertainty"),
    AlphabetCharacter("∼", "similar", 0x223C, "uncertainty"),
    AlphabetCharacter("≅", "congruent", 0x2245, "uncertainty"),
    # Probability
    AlphabetCharacter("℘", "probability", 0x2118, "probability", 2.0),
    AlphabetCharacter("∝", "proportional", 0x221D, "probability"),
    AlphabetCharacter("±", "plus_minus", 0x00B1, "probability"),
    # Confidence bounds
    AlphabetCharacter("⌈", "ceiling_left", 0x2308, "bound"),
    AlphabetCharacter("⌉", "ceiling_right", 0x2309, "bound"),
    AlphabetCharacter("⌊", "floor_left", 0x230A, "bound"),
    AlphabetCharacter("⌋", "floor_right", 0x230B, "bound"),
    # Oracle symbols
    AlphabetCharacter("☽", "waning_moon", 0x263D, "oracle", 1.5),
    AlphabetCharacter("☾", "waxing_moon", 0x263E, "oracle", 1.5),
    AlphabetCharacter("☼", "sun", 0x263C, "oracle", 2.0),
    AlphabetCharacter("⚡", "lightning", 0x26A1, "oracle", 2.0),
    # Wildcard
    AlphabetCharacter("*", "wildcard", ord("*"), "wildcard"),
    AlphabetCharacter("⋯", "ellipsis", 0x22EF, "wildcard"),
    AlphabetCharacter("∗", "star_operator", 0x2217, "wildcard"),
]

# CHARM Alphabet (UM - Social/Trust)
CHARM_CHARACTERS = [
    # Card suits (trust/reputation)
    AlphabetCharacter("♠", "spade", 0x2660, "suit"),
    AlphabetCharacter("♥", "heart", 0x2665, "suit"),
    AlphabetCharacter("♦", "diamond", 0x2666, "suit"),
    AlphabetCharacter("♣", "club", 0x2663, "suit"),
    AlphabetCharacter("♤", "white_spade", 0x2664, "suit"),
    AlphabetCharacter("♡", "white_heart", 0x2661, "suit"),
    AlphabetCharacter("♢", "white_diamond", 0x2662, "suit"),
    AlphabetCharacter("♧", "white_club", 0x2667, "suit"),
    # Rating stars
    AlphabetCharacter("★", "star_filled", 0x2605, "rating", 1.5),
    AlphabetCharacter("☆", "star_empty", 0x2606, "rating", 1.5),
    AlphabetCharacter("⯪", "half_star", 0x2BEA, "rating"),
    # Trust indicators
    AlphabetCharacter("✔", "verified", 0x2714, "trust", 2.0),
    AlphabetCharacter("✘", "rejected", 0x2718, "trust", 2.0),
    AlphabetCharacter("⚠", "warning", 0x26A0, "trust", 1.5),
    AlphabetCharacter("⛔", "forbidden", 0x26D4, "trust", 2.5),
    # Social hierarchy
    AlphabetCharacter("♔", "king", 0x2654, "hierarchy", 3.0),
    AlphabetCharacter("♕", "queen", 0x2655, "hierarchy", 2.5),
    AlphabetCharacter("♖", "rook", 0x2656, "hierarchy", 2.0),
    AlphabetCharacter("♗", "bishop", 0x2657, "hierarchy", 1.5),
    AlphabetCharacter("♘", "knight", 0x2658, "hierarchy", 1.5),
    AlphabetCharacter("♙", "pawn", 0x2659, "hierarchy"),
    # Connection/relationship
    AlphabetCharacter("⟷", "linked", 0x27F7, "connection"),
    AlphabetCharacter("⤳", "leads_to", 0x2933, "connection"),
    AlphabetCharacter("⇋", "equilibrium", 0x21CB, "connection", 1.5),
    AlphabetCharacter("⇌", "reversible", 0x21CC, "connection", 1.5),
    # Priority markers
    AlphabetCharacter("‣", "bullet", 0x2023, "priority"),
    AlphabetCharacter("›", "chevron", 0x203A, "priority"),
    AlphabetCharacter("»", "double_chevron", 0x00BB, "priority", 1.5),
]

# LEDGER Alphabet (DR - Finance/Auditing)
LEDGER_CHARACTERS = [
    # Currency symbols
    AlphabetCharacter("$", "dollar", ord("$"), "currency"),
    AlphabetCharacter("€", "euro", 0x20AC, "currency"),
    AlphabetCharacter("£", "pound", 0x00A3, "currency"),
    AlphabetCharacter("¥", "yen", 0x00A5, "currency"),
    AlphabetCharacter("₿", "bitcoin", 0x20BF, "currency", 1.5),
    AlphabetCharacter("₹", "rupee", 0x20B9, "currency"),
    AlphabetCharacter("₽", "ruble", 0x20BD, "currency"),
    AlphabetCharacter("¤", "generic_currency", 0x00A4, "currency"),
    # Transaction symbols
    AlphabetCharacter("+", "credit", ord("+"), "transaction"),
    AlphabetCharacter("-", "debit", ord("-"), "transaction"),
    AlphabetCharacter("×", "multiply", 0x00D7, "transaction"),
    AlphabetCharacter("÷", "divide", 0x00F7, "transaction"),
    # Audit symbols
    AlphabetCharacter("✓", "verified", 0x2713, "audit", 2.0),
    AlphabetCharacter("✗", "rejected", 0x2717, "audit", 2.0),
    AlphabetCharacter("⊙", "audited", 0x2299, "audit", 1.5),
    AlphabetCharacter("⊚", "double_audit", 0x229A, "audit", 2.0),
    # Balance indicators
    AlphabetCharacter("⚖", "balance", 0x2696, "balance", 2.0),
    AlphabetCharacter("≷", "greater_less", 0x2277, "balance"),
    AlphabetCharacter("≶", "less_greater", 0x2276, "balance"),
    # Percentage/rate
    AlphabetCharacter("%", "percent", ord("%"), "rate"),
    AlphabetCharacter("‰", "per_mille", 0x2030, "rate"),
    AlphabetCharacter("‱", "per_ten_thousand", 0x2031, "rate"),
    # Numeric subscripts (for account references)
    AlphabetCharacter("₀", "sub_0", 0x2080, "subscript"),
    AlphabetCharacter("₁", "sub_1", 0x2081, "subscript"),
    AlphabetCharacter("₂", "sub_2", 0x2082, "subscript"),
    AlphabetCharacter("₃", "sub_3", 0x2083, "subscript"),
    # Hash/signature
    AlphabetCharacter("#", "hash", ord("#"), "signature"),
    AlphabetCharacter("※", "reference", 0x203B, "signature", 1.5),
]


# ============================================================================
# Alphabet Registry
# ============================================================================

def _build_alphabet(
    alphabet_type: AlphabetType,
    tongue: SacredTonguePolyglot,
    axis: str,
    domain: str,
    description: str,
    characters: List[AlphabetCharacter],
) -> PolyglotAlphabet:
    """Build a complete alphabet."""
    return PolyglotAlphabet(
        alphabet_type=alphabet_type,
        tongue=tongue,
        axis=axis,
        domain=domain,
        description=description,
        characters=characters,
    )


# Create all alphabets
ALPHABETS: Dict[AlphabetType, PolyglotAlphabet] = {
    AlphabetType.AXIOM: _build_alphabet(
        AlphabetType.AXIOM,
        SacredTonguePolyglot.KO,
        "x",
        "Logic",
        "Formal proofs, constraints, set theory",
        AXIOM_CHARACTERS,
    ),
    AlphabetType.FLOW: _build_alphabet(
        AlphabetType.FLOW,
        SacredTonguePolyglot.AV,
        "y",
        "Data",
        "Pipelines, transformations, streams",
        FLOW_CHARACTERS,
    ),
    AlphabetType.GLYPH: _build_alphabet(
        AlphabetType.GLYPH,
        SacredTonguePolyglot.RU,
        "z",
        "Visual",
        "UI/UX, state visualization, indicators",
        GLYPH_CHARACTERS,
    ),
    AlphabetType.ORACLE: _build_alphabet(
        AlphabetType.ORACLE,
        SacredTonguePolyglot.CA,
        "v",
        "Query",
        "Queries, uncertainty, probability",
        ORACLE_CHARACTERS,
    ),
    AlphabetType.CHARM: _build_alphabet(
        AlphabetType.CHARM,
        SacredTonguePolyglot.UM,
        "h",
        "Social",
        "Trust, reputation, priority, relationships",
        CHARM_CHARACTERS,
    ),
    AlphabetType.LEDGER: _build_alphabet(
        AlphabetType.LEDGER,
        SacredTonguePolyglot.DR,
        "s",
        "Finance",
        "Transactions, auditing, currency",
        LEDGER_CHARACTERS,
    ),
}


# ============================================================================
# Encoding/Decoding Functions
# ============================================================================

@dataclass
class EncodedMessage:
    """Message encoded with polyglot alphabets."""
    segments: List[Tuple[AlphabetType, str]]  # (alphabet, encoded_text) pairs
    original_length: int
    complexity: int  # Number of unique alphabets used
    checksum: str


def get_alphabet(alphabet_type: AlphabetType) -> PolyglotAlphabet:
    """Get alphabet by type."""
    return ALPHABETS[alphabet_type]


def get_alphabet_for_axis(axis: str) -> Optional[PolyglotAlphabet]:
    """Get alphabet for a 6D axis."""
    alphabet_type = AXIS_TO_ALPHABET.get(axis.lower())
    if alphabet_type:
        return ALPHABETS[alphabet_type]
    return None


def get_alphabet_for_tongue(tongue: SacredTonguePolyglot) -> PolyglotAlphabet:
    """Get alphabet for a Sacred Tongue."""
    return ALPHABETS[TONGUE_TO_ALPHABET[tongue]]


def detect_alphabet(text: str) -> Optional[AlphabetType]:
    """Detect which alphabet a text primarily belongs to."""
    scores: Dict[AlphabetType, int] = {t: 0 for t in AlphabetType}

    for char in text:
        for alphabet_type, alphabet in ALPHABETS.items():
            if alphabet.contains(char):
                scores[alphabet_type] += 1

    max_score = max(scores.values())
    if max_score == 0:
        return None

    for alphabet_type, score in scores.items():
        if score == max_score:
            return alphabet_type
    return None


def encode_with_alphabet(
    data: bytes,
    alphabet_type: AlphabetType,
    use_weights: bool = True,
) -> str:
    """
    Encode binary data using a polyglot alphabet.

    Uses a bijective mapping where each byte maps to an alphabet character.
    If the alphabet has fewer than 256 characters, uses base-N encoding.
    """
    alphabet = ALPHABETS[alphabet_type]
    chars = alphabet.characters
    base = len(chars)

    if base == 0:
        raise ValueError(f"Alphabet {alphabet_type} has no characters")

    result = []

    # Convert bytes to integer
    value = int.from_bytes(data, byteorder='big')

    if value == 0:
        return chars[0].symbol

    while value > 0:
        index = value % base
        result.append(chars[index].symbol)
        value //= base

    return ''.join(reversed(result))


def decode_with_alphabet(
    encoded: str,
    alphabet_type: AlphabetType,
) -> bytes:
    """Decode polyglot-encoded string back to bytes."""
    alphabet = ALPHABETS[alphabet_type]
    base = len(alphabet.characters)

    value = 0
    for char in encoded:
        index = alphabet.get_index(char)
        if index == -1:
            raise ValueError(f"Character '{char}' not in alphabet {alphabet_type}")
        value = value * base + index

    # Convert integer back to bytes
    if value == 0:
        return b'\x00'

    byte_length = (value.bit_length() + 7) // 8
    return value.to_bytes(byte_length, byteorder='big')


def encode_multi_alphabet(
    data: bytes,
    alphabets: List[AlphabetType],
) -> EncodedMessage:
    """
    Encode data across multiple alphabets (striped encoding).

    Distributes bytes across specified alphabets for redundancy
    and domain separation.
    """
    if not alphabets:
        raise ValueError("At least one alphabet required")

    segments: List[Tuple[AlphabetType, str]] = []
    chunk_size = max(1, len(data) // len(alphabets))

    for i, alphabet_type in enumerate(alphabets):
        start = i * chunk_size
        end = (i + 1) * chunk_size if i < len(alphabets) - 1 else len(data)
        chunk = data[start:end]

        if chunk:
            encoded = encode_with_alphabet(chunk, alphabet_type)
            segments.append((alphabet_type, encoded))

    # Compute checksum
    checksum = hashlib.sha256(data).hexdigest()[:8]

    return EncodedMessage(
        segments=segments,
        original_length=len(data),
        complexity=len(set(alphabets)),
        checksum=checksum,
    )


def decode_multi_alphabet(encoded_msg: EncodedMessage) -> bytes:
    """Decode multi-alphabet encoded message."""
    chunks = []

    for alphabet_type, encoded in encoded_msg.segments:
        chunk = decode_with_alphabet(encoded, alphabet_type)
        chunks.append(chunk)

    return b''.join(chunks)


# ============================================================================
# Analysis Functions
# ============================================================================

def analyze_text(text: str) -> Dict[str, Any]:
    """
    Analyze text for polyglot alphabet composition.

    Returns breakdown of which alphabets and character categories are used.
    """
    alphabet_counts: Dict[AlphabetType, int] = {t: 0 for t in AlphabetType}
    category_counts: Dict[str, int] = {}
    weight_sum = 0.0
    matched_chars = 0

    for char in text:
        for alphabet_type, alphabet in ALPHABETS.items():
            for ac in alphabet.characters:
                if ac.symbol == char:
                    alphabet_counts[alphabet_type] += 1
                    category_counts[ac.category] = category_counts.get(ac.category, 0) + 1
                    weight_sum += ac.weight * alphabet.phi_weight
                    matched_chars += 1
                    break

    return {
        "total_chars": len(text),
        "matched_chars": matched_chars,
        "unmatched_chars": len(text) - matched_chars,
        "alphabet_breakdown": {k.value: v for k, v in alphabet_counts.items()},
        "category_breakdown": category_counts,
        "weighted_score": weight_sum,
        "dominant_alphabet": max(alphabet_counts, key=alphabet_counts.get).value
            if matched_chars > 0 else None,
    }


def get_all_symbols() -> Dict[str, Tuple[AlphabetType, str]]:
    """Get mapping of all symbols to their alphabet and name."""
    symbols: Dict[str, Tuple[AlphabetType, str]] = {}

    for alphabet_type, alphabet in ALPHABETS.items():
        for char in alphabet.characters:
            symbols[char.symbol] = (alphabet_type, char.name)

    return symbols


def validate_expression(
    expression: str,
    allowed_alphabets: Optional[Set[AlphabetType]] = None,
) -> Tuple[bool, List[str]]:
    """
    Validate that an expression uses only allowed alphabets.

    Returns (is_valid, list_of_errors).
    """
    if allowed_alphabets is None:
        allowed_alphabets = set(AlphabetType)

    errors = []
    all_symbols = get_all_symbols()

    for i, char in enumerate(expression):
        if char.isspace():
            continue

        if char in all_symbols:
            alphabet_type, _ = all_symbols[char]
            if alphabet_type not in allowed_alphabets:
                errors.append(
                    f"Character '{char}' at position {i} belongs to "
                    f"disallowed alphabet {alphabet_type.value}"
                )
        elif not char.isalnum():
            errors.append(f"Unknown symbol '{char}' at position {i}")

    return len(errors) == 0, errors


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enums
    "AlphabetType",
    "SacredTonguePolyglot",
    # Dataclasses
    "AlphabetCharacter",
    "PolyglotAlphabet",
    "EncodedMessage",
    # Constants
    "ALPHABETS",
    "TONGUE_TO_ALPHABET",
    "AXIS_TO_ALPHABET",
    "PHI",
    # Character sets
    "AXIOM_CHARACTERS",
    "FLOW_CHARACTERS",
    "GLYPH_CHARACTERS",
    "ORACLE_CHARACTERS",
    "CHARM_CHARACTERS",
    "LEDGER_CHARACTERS",
    # Functions
    "get_alphabet",
    "get_alphabet_for_axis",
    "get_alphabet_for_tongue",
    "detect_alphabet",
    "encode_with_alphabet",
    "decode_with_alphabet",
    "encode_multi_alphabet",
    "decode_multi_alphabet",
    "analyze_text",
    "get_all_symbols",
    "validate_expression",
]
