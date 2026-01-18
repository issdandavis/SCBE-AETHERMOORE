"""
Sacred Tongue Tokenizer - SS1 Spell-Text Encoding
==================================================
Deterministic 256-word lists (16 prefixes × 16 suffixes) for each of the
Six Sacred Tongues. Each byte maps to exactly one token.

Token format: prefix'suffix (apostrophe as morpheme seam)

Section tongues (canonical mapping):
- aad/header → Avali (av) - diplomacy/context
- salt → Runethic (ru) - binding
- nonce → Kor'aelin (ko) - flow/intent
- ciphertext → Cassisivadan (ca) - bitcraft/maths
- auth tag → Draumric (dr) - structure stands
- redaction → Umbroth (um) - veil
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class TongueSpec:
    """Specification for a Sacred Tongue's token vocabulary."""
    code: str           # 2-letter code (ko, av, ru, ca, um, dr)
    name: str           # Full name
    prefixes: Tuple[str, ...]  # 16 prefixes
    suffixes: Tuple[str, ...]  # 16 suffixes
    domain: str         # What this tongue is used for


# =============================================================================
# THE SIX SACRED TONGUES - v1 Wordlists
# =============================================================================
# DO NOT CHANGE without bumping version SS1 → SS2 (breaks existing secrets)

KOR_AELIN = TongueSpec(
    code='ko',
    name="Kor'aelin",
    prefixes=('sil', 'kor', 'vel', 'zar', 'keth', 'thul', 'nav', 'ael',
              'ra', 'med', 'gal', 'lan', 'joy', 'good', 'nex', 'vara'),
    suffixes=('a', 'ae', 'ei', 'ia', 'oa', 'uu', 'eth', 'ar',
              'or', 'il', 'an', 'en', 'un', 'ir', 'oth', 'esh'),
    domain='nonce/flow/intent'
)

AVALI = TongueSpec(
    code='av',
    name='Avali',
    prefixes=('saina', 'talan', 'vessa', 'maren', 'oriel', 'serin', 'nurel', 'lirea',
              'kiva', 'lumen', 'calma', 'ponte', 'verin', 'nava', 'sela', 'tide'),
    suffixes=('a', 'e', 'i', 'o', 'u', 'y', 'la', 're',
              'na', 'sa', 'to', 'mi', 've', 'ri', 'en', 'ul'),
    domain='aad/header/metadata'
)

RUNETHIC = TongueSpec(
    code='ru',
    name='Runethic',
    prefixes=('khar', 'drath', 'bront', 'vael', 'ur', 'mem', 'krak', 'tharn',
              'groth', 'basalt', 'rune', 'sear', 'oath', 'gnarl', 'rift', 'iron'),
    suffixes=('ak', 'eth', 'ik', 'ul', 'or', 'ar', 'um', 'on',
              'ir', 'esh', 'nul', 'vek', 'dra', 'kh', 'va', 'th'),
    domain='salt/binding'
)

CASSISIVADAN = TongueSpec(
    code='ca',
    name='Cassisivadan',
    prefixes=('bip', 'bop', 'klik', 'loopa', 'ifta', 'thena', 'elsa', 'spira',
              'rythm', 'quirk', 'fizz', 'gear', 'pop', 'zip', 'mix', 'chass'),
    suffixes=('a', 'e', 'i', 'o', 'u', 'y', 'ta', 'na',
              'sa', 'ra', 'lo', 'mi', 'ki', 'zi', 'qwa', 'sh'),
    domain='ciphertext/bitcraft'
)

UMBROTH = TongueSpec(
    code='um',
    name='Umbroth',
    prefixes=('veil', 'zhur', 'nar', 'shul', 'math', 'hollow', 'hush', 'thorn',
              'dusk', 'echo', 'ink', 'wisp', 'bind', 'ache', 'null', 'shade'),
    suffixes=('a', 'e', 'i', 'o', 'u', 'ae', 'sh', 'th',
              'ak', 'ul', 'or', 'ir', 'en', 'on', 'vek', 'nul'),
    domain='redaction/veil'
)

DRAUMRIC = TongueSpec(
    code='dr',
    name='Draumric',
    prefixes=('anvil', 'tharn', 'mek', 'grond', 'draum', 'ektal', 'temper', 'forge',
              'stone', 'steam', 'oath', 'seal', 'frame', 'pillar', 'rivet', 'ember'),
    suffixes=('a', 'e', 'i', 'o', 'u', 'ae', 'rak', 'mek',
              'tharn', 'grond', 'vek', 'ul', 'or', 'ar', 'en', 'on'),
    domain='tag/structure'
)

# Canonical mapping for SS1 format
TONGUES: Dict[str, TongueSpec] = {
    'ko': KOR_AELIN,
    'av': AVALI,
    'ru': RUNETHIC,
    'ca': CASSISIVADAN,
    'um': UMBROTH,
    'dr': DRAUMRIC,
}

# Section-to-tongue mapping (SS1 canonical)
SECTION_TONGUES = {
    'aad': 'av',      # Avali for metadata/context
    'salt': 'ru',     # Runethic for binding
    'nonce': 'ko',    # Kor'aelin for flow/intent
    'ct': 'ca',       # Cassisivadan for ciphertext
    'tag': 'dr',      # Draumric for auth tag
    'redact': 'um',   # Umbroth for redaction wrapper
    'veil': 'um',     # Alias for redact
}


# =============================================================================
# SACRED TONGUE ENUM (For type-safe domain mappings)
# =============================================================================

class SacredTongue(Enum):
    """The Six Sacred Tongues of the Spiralverse."""
    KORAELIN = "ko"      # Control Flow & Collaboration
    AVALI = "av"         # I/O, Messaging & Modules
    RUNETHIC = "ru"      # Scope, Constraints & Seals
    CASSISIVADAN = "ca"  # Logic, Math & Bitcraft
    UMBROTH = "um"       # Privacy, Redaction & Shadow
    DRAUMRIC = "dr"      # Types, Structures & Build


# Domain mapping using enum
DOMAIN_TONGUE_MAP = {
    "aad": SacredTongue.AVALI,
    "salt": SacredTongue.RUNETHIC,
    "nonce": SacredTongue.KORAELIN,
    "ct": SacredTongue.CASSISIVADAN,
    "tag": SacredTongue.DRAUMRIC,
    "veil": SacredTongue.UMBROTH,
    "redact": SacredTongue.UMBROTH,
}


def get_tongue_for_domain(domain: str) -> SacredTongue:
    """Get the SacredTongue enum for a domain."""
    if domain not in DOMAIN_TONGUE_MAP:
        raise ValueError(f"Unknown domain: {domain}. Valid: {list(DOMAIN_TONGUE_MAP.keys())}")
    return DOMAIN_TONGUE_MAP[domain]


# =============================================================================
# SACRED TONGUE TOKENIZER
# =============================================================================

class SacredTongueTokenizer:
    """
    Encode/decode bytes to Sacred Tongue spell-text tokens.

    Each byte maps deterministically to one token:
        byte b → prefix[b >> 4] + "'" + suffix[b & 0x0F]

    Example:
        byte 0x2A (42) → prefix[2] + "'" + suffix[10]
        In Kor'aelin: vel'an

    Supports both single-tongue mode (init with tongue_code) and
    multi-tongue mode (pass tongue to encode/decode methods).
    """

    def __init__(self, tongue_code: Optional[str] = None):
        """
        Initialize tokenizer.

        Args:
            tongue_code: One of 'ko', 'av', 'ru', 'ca', 'um', 'dr'.
                        If None, creates a multi-tongue tokenizer.
        """
        self._tongue_code = tongue_code
        self._all_lookup_tables: Dict[str, Dict[str, any]] = {}

        if tongue_code is not None:
            if tongue_code not in TONGUES:
                raise ValueError(f"Unknown tongue: {tongue_code}. Valid: {list(TONGUES.keys())}")
            self.tongue = TONGUES[tongue_code]
            self._build_lookup_tables_for_tongue(tongue_code)
        else:
            # Build tables for all tongues
            self.tongue = None
            for code in TONGUES:
                self._build_lookup_tables_for_tongue(code)

    def _build_lookup_tables_for_tongue(self, tongue_code: str):
        """Build forward and reverse lookup tables for a tongue."""
        spec = TONGUES[tongue_code]

        # Forward: byte → token
        byte_to_token: List[str] = []
        for b in range(256):
            pi = b >> 4        # High nibble (0-15)
            si = b & 0x0F      # Low nibble (0-15)
            token = f"{spec.prefixes[pi]}'{spec.suffixes[si]}"
            byte_to_token.append(token)

        # Reverse: token → byte
        token_to_byte: Dict[str, int] = {
            token: b for b, token in enumerate(byte_to_token)
        }

        self._all_lookup_tables[tongue_code] = {
            'byte_to_token': byte_to_token,
            'token_to_byte': token_to_byte,
            'spec': spec,
        }

        # For single-tongue mode, set default tables
        if self._tongue_code == tongue_code:
            self._byte_to_token = byte_to_token
            self._token_to_byte = token_to_byte

    def _get_tongue_code(self, tongue: Optional[SacredTongue] = None) -> str:
        """Get tongue code from enum or default."""
        if tongue is not None:
            return tongue.value
        if self._tongue_code:
            return self._tongue_code
        return 'ko'  # Default fallback

    def _get_tables(self, tongue_code: str) -> Dict[str, any]:
        """Get lookup tables for a tongue, building if needed."""
        if tongue_code not in self._all_lookup_tables:
            self._build_lookup_tables_for_tongue(tongue_code)
        return self._all_lookup_tables[tongue_code]

    def encode_byte(self, b: int, tongue: Optional[SacredTongue] = None) -> str:
        """Encode a single byte to a token."""
        if not 0 <= b <= 255:
            raise ValueError(f"Byte must be 0-255, got {b}")
        tongue_code = self._get_tongue_code(tongue)
        tables = self._get_tables(tongue_code)
        return tables['byte_to_token'][b]

    def decode_token(self, token: str, tongue: Optional[SacredTongue] = None) -> int:
        """Decode a single token to a byte."""
        tongue_code = self._get_tongue_code(tongue)
        tables = self._get_tables(tongue_code)
        if token not in tables['token_to_byte']:
            raise ValueError(f"Unknown token: {token}")
        return tables['token_to_byte'][token]

    def get_token_for_byte(self, byte_val: int, tongue: SacredTongue) -> 'Token':
        """Get a Token object for a byte value in a specific tongue."""
        tongue_code = tongue.value
        tables = self._get_tables(tongue_code)
        spec = tables['spec']

        pi = byte_val >> 4
        si = byte_val & 0x0F

        return Token(
            tongue=tongue,
            prefix=spec.prefixes[pi],
            suffix=spec.suffixes[si],
            byte_value=byte_val
        )

    def encode(self, data: bytes, tongue: Optional[SacredTongue] = None) -> 'List[Token]':
        """
        Encode bytes to a list of Token objects.

        Args:
            data: Raw bytes to encode
            tongue: Sacred tongue to use (uses default if not specified)

        Returns:
            List of Token objects
        """
        tongue_code = self._get_tongue_code(tongue)
        tongue_enum = SacredTongue(tongue_code) if tongue is None else tongue
        return [self.get_token_for_byte(b, tongue_enum) for b in data]

    def decode(self, tokens: 'List[Token]') -> bytes:
        """
        Decode Token objects back to bytes.

        Args:
            tokens: List of Token objects

        Returns:
            Decoded bytes
        """
        return bytes(t.byte_value for t in tokens)

    def encode_to_string(self, data: bytes, tongue: Optional[SacredTongue] = None,
                         separator: str = " ") -> str:
        """
        Encode bytes to a string of tokens.

        Args:
            data: Raw bytes to encode
            tongue: Sacred tongue to use
            separator: Token separator (default: space)

        Returns:
            String of tokens like "ko:sil'a ko:vel'an"
        """
        tongue_code = self._get_tongue_code(tongue)
        tables = self._get_tables(tongue_code)
        tokens = [f"{tongue_code}:{tables['byte_to_token'][b]}" for b in data]
        return separator.join(tokens)

    def decode_from_string(self, token_string: str, tongue: Optional[SacredTongue] = None,
                           separator: str = " ") -> bytes:
        """
        Decode a string of tokens back to bytes.

        Args:
            token_string: Token string like "ko:sil'a ko:vel'an"
            tongue: Sacred tongue to use
            separator: Token separator (default: space)

        Returns:
            Decoded bytes
        """
        tongue_code = self._get_tongue_code(tongue)
        tables = self._get_tables(tongue_code)

        result = []
        for token in token_string.split(separator):
            if not token:
                continue
            # Strip tongue prefix if present
            if ':' in token:
                _, token = token.split(':', 1)
            if token not in tables['token_to_byte']:
                raise ValueError(f"Unknown token: {token}")
            result.append(tables['token_to_byte'][token])
        return bytes(result)

    def encode_simple(self, data: bytes) -> str:
        """
        Simple encode for single-tongue mode (used by TongueSpec-based API).

        Args:
            data: Raw bytes to encode

        Returns:
            Space-separated tokens with tongue prefix
        """
        if self._tongue_code is None:
            self._tongue_code = 'ko'  # Default
        tables = self._get_tables(self._tongue_code)
        tokens = [f"{self._tongue_code}:{tables['byte_to_token'][b]}" for b in data]
        return ' '.join(tokens)

    def decode_simple(self, spelltext: str) -> bytes:
        """
        Simple decode for single-tongue mode.

        Args:
            spelltext: Space-separated tokens

        Returns:
            Decoded bytes
        """
        if self._tongue_code is None:
            self._tongue_code = 'ko'  # Default
        return self.decode_from_string(spelltext, separator=" ")


# Compatibility alias
SacredTongueTokenizerCompat = SacredTongueTokenizer


# =============================================================================
# HIGH-LEVEL ENCODING FUNCTIONS
# =============================================================================

def encode_to_spelltext(data: bytes, section: str) -> str:
    """
    Encode bytes using the canonical tongue for a given section.

    Args:
        data: Raw bytes to encode
        section: One of 'aad', 'salt', 'nonce', 'ct', 'tag', 'redact'

    Returns:
        Spell-text encoded string (with tongue prefix on each token)
        Example: "ru:khar'eth ru:drath'ul"
    """
    tongue_code = SECTION_TONGUES.get(section, 'ca')  # Default to Cassisivadan
    tongue_enum = SacredTongue(tongue_code)
    tokenizer = SacredTongueTokenizer()  # Multi-tongue tokenizer
    return tokenizer.encode_to_string(data, tongue_enum, " ")


def encode_tokens_only(data: bytes, section: str) -> str:
    """
    Encode bytes to tokens WITHOUT the tongue prefix.

    Used by SpiralSealResult.to_ss1_string() which adds the prefix separately.

    Args:
        data: Raw bytes to encode
        section: One of 'aad', 'salt', 'nonce', 'ct', 'tag', 'redact'

    Returns:
        Space-separated tokens without tongue prefix (e.g., "khar'ak drath'eth")
    """
    tongue_code = SECTION_TONGUES.get(section, 'ca')
    tokenizer = SacredTongueTokenizer(tongue_code)
    # Use internal byte_to_token mapping directly
    tokens = [tokenizer._byte_to_token[b] for b in data]
    return ' '.join(tokens)


def decode_tokens_only(tokens: str, section: str) -> bytes:
    """
    Decode tokens (without tongue prefix) back to bytes.

    Args:
        tokens: Space-separated tokens without prefix (e.g., "khar'ak drath'eth")
        section: One of 'aad', 'salt', 'nonce', 'ct', 'tag', 'redact'

    Returns:
        Decoded bytes
    """
    tongue_code = SECTION_TONGUES.get(section, 'ca')
    tokenizer = SacredTongueTokenizer(tongue_code)

    result = []
    for token in tokens.split():
        # Strip tongue prefix if present (handle both formats)
        if ':' in token:
            _, token = token.split(':', 1)
        result.append(tokenizer._token_to_byte[token])
    return bytes(result)


def decode_from_spelltext(spelltext: str, section: str) -> bytes:
    """
    Decode spell-text using the canonical tongue for a given section.

    Args:
        spelltext: Spell-text encoded string
        section: One of 'aad', 'salt', 'nonce', 'ct', 'tag', 'redact'

    Returns:
        Decoded bytes
    """
    tongue_code = SECTION_TONGUES.get(section, 'ca')
    tongue_enum = SacredTongue(tongue_code)
    tokenizer = SacredTongueTokenizer()  # Multi-tongue tokenizer
    return tokenizer.decode_from_string(spelltext, tongue_enum, " ")


def format_ss1_blob(
    kid: str,
    aad: str,
    salt: bytes,
    nonce: bytes,
    ciphertext: bytes,
    tag: bytes
) -> str:
    """
    Format a complete SS1 spell-text blob.

    Returns:
        SS1|kid=...|aad=...|salt=ru:...|nonce=ko:...|ct=ca:...|tag=dr:...
    """
    parts = [
        'SS1',
        f'kid={kid}',
        f'aad={aad}',
        f'salt={encode_to_spelltext(salt, "salt")}',
        f'nonce={encode_to_spelltext(nonce, "nonce")}',
        f'ct={encode_to_spelltext(ciphertext, "ct")}',
        f'tag={encode_to_spelltext(tag, "tag")}',
    ]
    return '|'.join(parts)


def parse_ss1_blob(blob: str) -> Dict[str, any]:
    """
    Parse an SS1 spell-text blob.

    Returns:
        Dict with keys: version, kid, aad, salt, nonce, ct, tag
    """
    if not blob.startswith('SS1|'):
        raise ValueError("Invalid SS1 blob: must start with 'SS1|'")

    parts = blob.split('|')
    result = {'version': 'SS1'}

    for part in parts[1:]:  # Skip 'SS1' prefix
        if '=' not in part:
            continue
        key, value = part.split('=', 1)

        if key in ('salt', 'nonce', 'ct', 'tag'):
            # Decode spell-text to bytes
            section_map = {'salt': 'salt', 'nonce': 'nonce', 'ct': 'ct', 'tag': 'tag'}
            result[key] = decode_from_spelltext(value, section_map[key])
        else:
            result[key] = value

    return result


# =============================================================================
# LANGUES WEIGHTING SYSTEM (LWS) INTEGRATION
# =============================================================================

# AETHERMOORE Constants
PHI = 1.618033988749895  # Golden ratio
R_FIFTH = 1.5           # Perfect fifth harmonic ratio


def compute_lws_weights(tongue_code: str) -> List[float]:
    """
    Compute Langues Weighting System weights for a Sacred Tongue.

    Uses golden ratio powers (φ^i) for importance hierarchy,
    normalized to sum to 1.

    Args:
        tongue_code: Sacred Tongue code

    Returns:
        List of 16 weights (one per prefix)
    """
    # Generate golden ratio powers
    weights = [PHI ** i for i in range(16)]

    # Normalize to sum to 1
    total = sum(weights)
    weights = [w / total for w in weights]

    return weights


def get_tongue_signature(tongue_code: str) -> bytes:
    """
    Get the unique cryptographic signature for a Sacred Tongue.

    This is used for authentication and verification in the
    polyglot interoperability layer.

    Args:
        tongue_code: Sacred Tongue code

    Returns:
        32-byte SHA-256 hash of the tongue's vocabulary
    """
    import hashlib

    tongue = TONGUES[tongue_code]
    vocab_str = '|'.join(tongue.prefixes) + '||' + '|'.join(tongue.suffixes)
    return hashlib.sha256(vocab_str.encode('utf-8')).digest()


def get_magical_signature(tongue: SacredTongue) -> str:
    """
    Get the magical signature (hex) for a Sacred Tongue.

    Args:
        tongue: SacredTongue enum value

    Returns:
        16-character hex string
    """
    sig = get_tongue_signature(tongue.value)
    return sig[:8].hex()


# =============================================================================
# GLOBAL TOKENIZER CACHE
# =============================================================================

_tokenizer_cache: Dict[Optional[str], SacredTongueTokenizer] = {}


def get_tokenizer(tongue_code: Optional[str] = None) -> SacredTongueTokenizer:
    """Get a cached tokenizer.

    Args:
        tongue_code: Specific tongue code, or None for multi-tongue tokenizer.

    Returns:
        Cached SacredTongueTokenizer instance.
    """
    if tongue_code not in _tokenizer_cache:
        _tokenizer_cache[tongue_code] = SacredTongueTokenizer(tongue_code)
    return _tokenizer_cache[tongue_code]


# =============================================================================
# LEGACY COMPATIBILITY EXPORTS
# =============================================================================

@dataclass
class Token:
    """A single Sacred Tongue token (legacy format)."""
    tongue: SacredTongue
    prefix: str
    suffix: str
    byte_value: int

    def __str__(self) -> str:
        return f"{self.tongue.value}:{self.prefix}'{self.suffix}"

    @property
    def short(self) -> str:
        return f"{self.prefix}'{self.suffix}"


# Wordlists in legacy format (for backwards compatibility)
TONGUE_WORDLISTS: Dict[SacredTongue, Tuple[List[str], List[str]]] = {
    SacredTongue.KORAELIN: (list(KOR_AELIN.prefixes), list(KOR_AELIN.suffixes)),
    SacredTongue.AVALI: (list(AVALI.prefixes), list(AVALI.suffixes)),
    SacredTongue.RUNETHIC: (list(RUNETHIC.prefixes), list(RUNETHIC.suffixes)),
    SacredTongue.CASSISIVADAN: (list(CASSISIVADAN.prefixes), list(CASSISIVADAN.suffixes)),
    SacredTongue.UMBROTH: (list(UMBROTH.prefixes), list(UMBROTH.suffixes)),
    SacredTongue.DRAUMRIC: (list(DRAUMRIC.prefixes), list(DRAUMRIC.suffixes)),
}


def get_combined_alphabet() -> Dict[str, any]:
    """Get statistics about the combined vocabulary across all tongues."""
    all_prefixes = set()
    all_suffixes = set()

    for spec in TONGUES.values():
        all_prefixes.update(spec.prefixes)
        all_suffixes.update(spec.suffixes)

    return {
        "prefixes": sorted(all_prefixes),
        "suffixes": sorted(all_suffixes),
        "total_unique_prefixes": len(all_prefixes),
        "total_unique_suffixes": len(all_suffixes),
    }


def get_tongue_keywords(tongue: SacredTongue) -> Dict[str, str]:
    """Get SpiralScript keywords for a tongue."""
    return SPIRALSCRIPT_KEYWORDS.get(tongue, {})


# TongueInfo alias (points to TongueSpec)
TongueInfo = TongueSpec


# SpiralScript keywords
SPIRALSCRIPT_KEYWORDS = {
    SacredTongue.KORAELIN: {
        "vel": "invite (begin cooperative intent)",
        "sil": "together (synchronize/barrier)",
        "thul": "spiral (iteration/fold)",
    },
    SacredTongue.AVALI: {
        "oriel": "council (import module)",
        "serin": "send (send event/message)",
        "nurel": "receive (return/await)",
    },
    SacredTongue.RUNETHIC: {
        "khar": "lock (immutable binding)",
        "drath": "ward (scoped block)",
        "bront": "ordinance (declare rule)",
    },
    SacredTongue.CASSISIVADAN: {
        "ifta": "if (conditional)",
        "thena": "then (conditional branch)",
        "loopa": "loop (repeat execution)",
    },
    SacredTongue.UMBROTH: {
        "veil": "shroud (redact in logs)",
        "hollow": "safe-dark (sandboxed scope)",
        "math": "witness (auditable log)",
    },
    SacredTongue.DRAUMRIC: {
        "anvil": "foundation (variable binding)",
        "tharn": "structure (function/struct)",
        "forge": "compile (build artifact)",
    },
}
