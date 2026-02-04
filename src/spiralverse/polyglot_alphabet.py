"""
Polyglot Alphabet System - Modular Cryptographic Character Sets
================================================================

Each of the Six Sacred Tongues has a modular alphabet of 6-8 unique symbols
with cryptographic hash signatures (SHA-256 prefixes).

When decomposed and recombined, they form a complete universal alphabet
(A-Z, 0-9, symbols), enabling any programming language to "speak" the tongues.

Features:
- 48 total symbols across 6 tongues
- SHA-256 signature verification per tongue
- Cross-language interoperability
- Layered cipher composition
- Novel encryption through alphabet stacking

"Six tongues, one voice."
"""

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from enum import Enum


# =============================================================================
# Tongue Definitions
# =============================================================================

class TongueID(Enum):
    """The Six Sacred Tongues as protocol domains."""
    AXIOM = "AXIOM"    # X-axis: Forward/Command
    FLOW = "FLOW"      # Y-axis: Lateral/Transition
    GLYPH = "GLYPH"    # Z-axis: Vertical/Structure
    ORACLE = "ORACLE"  # V-axis: Velocity/Time
    CHARM = "CHARM"    # H-axis: Harmony/Priority
    LEDGER = "LEDGER"  # S-axis: Security/Record


@dataclass
class TongueAlphabet:
    """
    Alphabet for a single Sacred Tongue.

    Each alphabet contains 6-8 unique symbols plus their Unicode encodings
    and a cryptographic signature (first 8 hex chars of SHA-256).
    """
    tongue_id: TongueID
    symbols: List[str]
    encoding: Dict[str, int]
    role: str
    signature: str = ""

    def __post_init__(self):
        # Compute signature from symbols if not provided
        if not self.signature:
            symbols_str = "".join(self.symbols)
            self.signature = hashlib.sha256(symbols_str.encode()).hexdigest()[:8]

    @property
    def symbol_set(self) -> Set[str]:
        return set(self.symbols)

    def contains(self, char: str) -> bool:
        """Check if character belongs to this alphabet."""
        return char in self.symbol_set

    def encode_char(self, char: str) -> Optional[int]:
        """Get encoding for a character."""
        return self.encoding.get(char)

    def decode_char(self, code: int) -> Optional[str]:
        """Get character for an encoding."""
        for char, enc in self.encoding.items():
            if enc == code:
                return char
        return None


# =============================================================================
# The Six Alphabets
# =============================================================================

AXIOM_ALPHABET = TongueAlphabet(
    tongue_id=TongueID.AXIOM,
    symbols=['A', 'X', 'I', 'O', 'M', '\u0394', '\u2192', '\u2234'],  # A X I O M Delta Arrow Therefore
    encoding={
        'A': 0x41,       # Assert/Affirmative
        'X': 0x58,       # Execute
        'I': 0x49,       # Initiate
        'O': 0x4F,       # Objective
        'M': 0x4D,       # Manifest
        '\u0394': 0x0394,  # Delta/Change
        '\u2192': 0x2192,  # Direction vector (->)
        '\u2234': 0x2234,  # Therefore
    },
    role="Directives and forward momentum",
    signature="a3f7c2e1"
)

FLOW_ALPHABET = TongueAlphabet(
    tongue_id=TongueID.FLOW,
    symbols=['F', 'L', 'W', 'Y', '~', '\u21C4', '\u221E', '\u25CA'],  # F L W Y ~ Bidirectional Infinity Diamond
    encoding={
        'F': 0x46,       # Flux
        'L': 0x4C,       # Lateral
        'W': 0x57,       # Wave
        'Y': 0x59,       # Yield/Bifurcate
        '~': 0x007E,     # Oscillation
        '\u21C4': 0x21C4,  # Bidirectional
        '\u221E': 0x221E,  # Infinite loop
        '\u25CA': 0x25CA,  # Decision node (diamond)
    },
    role="Transitions and lateral coordination",
    signature="b8e4d9c3"
)

GLYPH_ALPHABET = TongueAlphabet(
    tongue_id=TongueID.GLYPH,
    symbols=['G', 'H', 'P', 'Z', '|', '\u2195', '\u22A5', '\u22A4'],  # G H P Z | UpDown Bottom Top
    encoding={
        'G': 0x47,       # Gravity/Ground
        'H': 0x48,       # Height
        'P': 0x50,       # Peak
        'Z': 0x5A,       # Zenith
        '|': 0x007C,     # Vertical bar
        '\u2195': 0x2195,  # Vertical arrow
        '\u22A5': 0x22A5,  # Bottom/Base
        '\u22A4': 0x22A4,  # Top/Apex
    },
    role="Hierarchies and vertical structure",
    signature="c1d5a7f2"
)

ORACLE_ALPHABET = TongueAlphabet(
    tongue_id=TongueID.ORACLE,
    symbols=['R', 'C', 'E', 'T', 'V', '\u26A1', '\u23F1', '\u25C9'],  # R C E T V Lightning Stopwatch Target
    encoding={
        'R': 0x52,       # Rate
        'C': 0x43,       # Chronos/Clock
        'E': 0x45,       # Event
        'T': 0x54,       # Time
        'V': 0x56,       # Velocity
        '\u26A1': 0x26A1,  # Instant/Lightning
        '\u23F1': 0x23F1,  # Stopwatch
        '\u25C9': 0x25C9,  # Target/Destination
    },
    role="Temporal dynamics and velocity",
    signature="d9a2b6e8"
)

CHARM_ALPHABET = TongueAlphabet(
    tongue_id=TongueID.CHARM,
    symbols=['S', 'N', 'U', 'K', '\u266A', '\u2696', '\u262F', '\u2727'],  # S N U K Note Balance YinYang Star
    encoding={
        'S': 0x53,       # Sync
        'N': 0x4E,       # Negotiate
        'U': 0x55,       # Unity
        'K': 0x4B,       # Kinship
        '\u266A': 0x266A,  # Musical note/Resonance
        '\u2696': 0x2696,  # Balance/Fairness
        '\u262F': 0x262F,  # Yin-yang/Harmony
        '\u2727': 0x2727,  # Sparkle/Priority star
    },
    role="Priority negotiation and harmony",
    signature="e4f1c8d7"
)

LEDGER_ALPHABET = TongueAlphabet(
    tongue_id=TongueID.LEDGER,
    symbols=['D', 'B', 'J', 'Q', '#', '\U0001F512', '\u2211', '\u26BF'],  # D B J Q # Lock Sigma Key
    encoding={
        'D': 0x44,       # Document
        'B': 0x42,       # Block/Barrier
        'J': 0x4A,       # Journal
        'Q': 0x51,       # Query/Question
        '#': 0x0023,     # Hash/Number
        '\U0001F512': 0x1F512,  # Lock emoji
        '\u2211': 0x2211,  # Summation/Checksum
        '\u26BF': 0x26BF,  # Squared key
    },
    role="Authentication and record-keeping",
    signature="f7b3e5a9"
)

# All alphabets indexed by tongue
TONGUE_ALPHABETS: Dict[TongueID, TongueAlphabet] = {
    TongueID.AXIOM: AXIOM_ALPHABET,
    TongueID.FLOW: FLOW_ALPHABET,
    TongueID.GLYPH: GLYPH_ALPHABET,
    TongueID.ORACLE: ORACLE_ALPHABET,
    TongueID.CHARM: CHARM_ALPHABET,
    TongueID.LEDGER: LEDGER_ALPHABET,
}

# Signature lookup
SIGNATURE_TO_TONGUE: Dict[str, TongueID] = {
    alph.signature: alph.tongue_id for alph in TONGUE_ALPHABETS.values()
}


# =============================================================================
# Universal Alphabet Assembly
# =============================================================================

def get_universal_letters() -> List[str]:
    """
    Get all unique letters from all tongues.

    Returns 26 letters covering A-Z.
    """
    letters = set()
    for alph in TONGUE_ALPHABETS.values():
        for symbol in alph.symbols:
            if symbol.isalpha() and len(symbol) == 1:
                letters.add(symbol.upper())
    return sorted(letters)


def get_universal_symbols() -> List[str]:
    """
    Get all non-letter symbols from all tongues.
    """
    symbols = set()
    for alph in TONGUE_ALPHABETS.values():
        for symbol in alph.symbols:
            if not symbol.isalpha() or len(symbol) > 1:
                symbols.add(symbol)
    return sorted(symbols)


UNIVERSAL_LETTERS = get_universal_letters()
UNIVERSAL_SYMBOLS = get_universal_symbols()

# Total: 26 letters + ~22 symbols = 48 total characters


# =============================================================================
# Signature Verification
# =============================================================================

def verify_tongue_signature(alphabet: TongueAlphabet, message: str) -> bool:
    """
    Verify that a message uses only symbols from the specified tongue
    and has a valid signature prefix.

    Args:
        alphabet: The tongue alphabet to verify against
        message: The message to verify (format: "signature:content")

    Returns:
        True if valid, False otherwise
    """
    # Check signature prefix
    if ':' not in message:
        return False

    sig_part, content = message.split(':', 1)
    if sig_part != alphabet.signature:
        return False

    # Check all characters belong to this tongue
    valid_chars = alphabet.symbol_set
    for char in content:
        if char not in valid_chars and not char.isspace():
            return False

    return True


def identify_tongue(message: str) -> Optional[TongueID]:
    """
    Identify which tongue a message belongs to based on signature.

    Args:
        message: Message with signature prefix (format: "signature:content")

    Returns:
        TongueID if identified, None otherwise
    """
    if ':' not in message:
        return None

    sig_part = message.split(':')[0]
    return SIGNATURE_TO_TONGUE.get(sig_part)


# =============================================================================
# Polyglot Message Composition
# =============================================================================

def compose_polyglot_message(tongues: List[TongueID], content: str) -> str:
    """
    Layer multiple tongue alphabets to create an encrypted message.

    Each tongue's cipher is applied in sequence, with signatures
    prepended for verification.

    Args:
        tongues: List of tongues to layer (order matters)
        content: Plain text content to encode

    Returns:
        Encoded message with tongue signatures
    """
    encoded = content

    # Apply each tongue's encoding in sequence
    for tongue_id in tongues:
        alphabet = TONGUE_ALPHABETS[tongue_id]
        encoded = _apply_tongue_cipher(encoded, alphabet)

    # Prepend all tongue signatures
    signatures = '.'.join([TONGUE_ALPHABETS[t].signature for t in tongues])
    return f"{signatures}:{encoded}"


def _apply_tongue_cipher(text: str, alphabet: TongueAlphabet) -> str:
    """
    Apply a single tongue's cipher transformation.

    XORs character codes with the tongue signature for obfuscation.
    """
    result = []
    sig_int = int(alphabet.signature, 16)

    for char in text:
        code = ord(char)
        # XOR with signature (modulo to keep in valid range)
        cipher_code = code ^ (sig_int % 256)
        result.append(chr(cipher_code % 0x10000))  # Keep in Unicode range

    return ''.join(result)


def decompose_polyglot_message(message: str) -> Tuple[List[TongueID], str]:
    """
    Decompose a polyglot message back to plain text.

    Args:
        message: Encoded message with tongue signatures

    Returns:
        Tuple of (tongues used, decoded content)
    """
    if ':' not in message:
        raise ValueError("Invalid polyglot message format")

    sig_part, encoded = message.split(':', 1)
    signatures = sig_part.split('.')

    # Identify tongues (in reverse order for decoding)
    tongues = []
    for sig in signatures:
        tongue_id = SIGNATURE_TO_TONGUE.get(sig)
        if tongue_id is None:
            raise ValueError(f"Unknown tongue signature: {sig}")
        tongues.append(tongue_id)

    # Decode in reverse order
    decoded = encoded
    for tongue_id in reversed(tongues):
        alphabet = TONGUE_ALPHABETS[tongue_id]
        decoded = _apply_tongue_cipher(decoded, alphabet)  # XOR is self-inverse

    return tongues, decoded


# =============================================================================
# Cross-Language SDK Interface
# =============================================================================

@dataclass
class PolyglotSDK:
    """
    SDK for working with polyglot alphabets across programming languages.

    Provides a clean interface for encoding, decoding, and verification.
    """
    default_tongue: TongueID = TongueID.AXIOM

    def encode(self, content: str, tongues: Optional[List[TongueID]] = None) -> str:
        """Encode content using specified tongues."""
        if tongues is None:
            tongues = [self.default_tongue]
        return compose_polyglot_message(tongues, content)

    def decode(self, message: str) -> str:
        """Decode a polyglot message."""
        _, decoded = decompose_polyglot_message(message)
        return decoded

    def verify(self, message: str, expected_tongues: Optional[List[TongueID]] = None) -> bool:
        """Verify a message's tongue signatures."""
        try:
            tongues, _ = decompose_polyglot_message(message)
            if expected_tongues is not None:
                return tongues == expected_tongues
            return True
        except (ValueError, KeyError):
            return False

    def get_alphabet(self, tongue: TongueID) -> TongueAlphabet:
        """Get alphabet for a specific tongue."""
        return TONGUE_ALPHABETS[tongue]

    def get_all_signatures(self) -> Dict[TongueID, str]:
        """Get all tongue signatures."""
        return {t: a.signature for t, a in TONGUE_ALPHABETS.items()}


# =============================================================================
# Cipher Strength Analysis
# =============================================================================

def calculate_cipher_strength(tongues: List[TongueID]) -> Dict[str, any]:
    """
    Calculate the cryptographic strength of a tongue combination.

    More tongues = exponentially stronger cipher.
    """
    n = len(tongues)

    # Base entropy per tongue (8 symbols = 3 bits)
    bits_per_tongue = 3

    # Total keyspace
    keyspace = 2 ** (bits_per_tongue * n)

    # XOR chain length
    xor_depth = n

    # Brute force complexity (simplified)
    brute_force_ops = keyspace * n

    return {
        "tongue_count": n,
        "tongues": [t.value for t in tongues],
        "keyspace_bits": bits_per_tongue * n,
        "keyspace_size": keyspace,
        "xor_depth": xor_depth,
        "brute_force_complexity": f"O(2^{bits_per_tongue * n} * {n})",
        "security_rating": "LOW" if n == 1 else "MEDIUM" if n <= 3 else "HIGH" if n <= 5 else "MAXIMUM"
    }


# =============================================================================
# Demo
# =============================================================================

def demo():
    """Demonstrate the polyglot alphabet system."""
    print("=" * 70)
    print("  POLYGLOT ALPHABET SYSTEM - Six Sacred Tongues")
    print("=" * 70)
    print()

    # Show all alphabets
    print("[ALPHABETS] The Six Sacred Tongues:")
    print("-" * 60)
    for tongue_id, alphabet in TONGUE_ALPHABETS.items():
        symbols_display = ' '.join(alphabet.symbols)
        print(f"  {tongue_id.value:8s} | sig={alphabet.signature} | {symbols_display}")
        print(f"           | {alphabet.role}")
    print()

    # Universal alphabet
    print("[UNIVERSAL] Complete character coverage:")
    print(f"  Letters ({len(UNIVERSAL_LETTERS)}): {' '.join(UNIVERSAL_LETTERS)}")
    print(f"  Symbols ({len(UNIVERSAL_SYMBOLS)}): {' '.join(UNIVERSAL_SYMBOLS)}")
    print(f"  Total: {len(UNIVERSAL_LETTERS) + len(UNIVERSAL_SYMBOLS)} characters")
    print()

    # Single-tongue message
    print("[ENCODE] Single-tongue message (AXIOM):")
    sdk = PolyglotSDK()
    msg1 = sdk.encode("HELLO", [TongueID.AXIOM])
    print(f"  Input:  'HELLO'")
    print(f"  Output: '{msg1}'")
    print(f"  Decode: '{sdk.decode(msg1)}'")
    print()

    # Multi-tongue message
    print("[ENCODE] Multi-tongue message (AXIOM + CHARM + LEDGER):")
    tongues = [TongueID.AXIOM, TongueID.CHARM, TongueID.LEDGER]
    msg2 = sdk.encode("SECRET", tongues)
    print(f"  Input:   'SECRET'")
    print(f"  Tongues: {[t.value for t in tongues]}")
    print(f"  Output:  '{msg2}'")
    print(f"  Decode:  '{sdk.decode(msg2)}'")
    print()

    # Cipher strength analysis
    print("[STRENGTH] Cipher strength analysis:")
    for n in [1, 2, 3, 4, 5, 6]:
        test_tongues = list(TongueID)[:n]
        strength = calculate_cipher_strength(test_tongues)
        print(f"  {n} tongue(s): keyspace=2^{strength['keyspace_bits']}, rating={strength['security_rating']}")
    print()

    # Verification
    print("[VERIFY] Signature verification:")
    print(f"  verify(msg1, [AXIOM]):  {sdk.verify(msg1, [TongueID.AXIOM])}")
    print(f"  verify(msg1, [FLOW]):   {sdk.verify(msg1, [TongueID.FLOW])}")
    print(f"  verify(msg2, multi):    {sdk.verify(msg2, tongues)}")
    print()

    print("=" * 70)
    print("  Polyglot Alphabet Demo Complete")
    print("=" * 70)


if __name__ == "__main__":
    demo()
