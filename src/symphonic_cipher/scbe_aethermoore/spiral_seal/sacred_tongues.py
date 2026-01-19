"""
Sacred Tongue Tokenizer - SS1 Spell-Text Encoding
==================================================
Deterministic 256-word lists (16 prefixes × 16 suffixes) for each of the
Six Sacred Tongues. Each byte maps to exactly one token.

Last Updated: January 18, 2026
Version: 1.1.0

Token format: prefix'suffix (apostrophe as morpheme seam)

Section tongues (canonical mapping):
- aad/header → Avali (av) - diplomacy/context
- salt → Runethic (ru) - binding
- nonce → Kor'aelin (ko) - flow/intent  
- ciphertext → Cassisivadan (ca) - bitcraft/maths
- auth tag → Draumric (dr) - structure stands
- redaction → Umbroth (um) - veil
"""

from typing import Dict, List, Tuple, Any
from dataclasses import dataclass


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
}


class SacredTongueTokenizer:
    """
    Encode/decode bytes to Sacred Tongue spell-text tokens.

    Design:
      - 1 byte → 1 token via hi/lo nibble:
          hi = (b >> 4) & 0x0F → prefix index
          lo =  b       & 0x0F → suffix index
      - Token string format: prefix + "'" + suffix.
      - Deterministic and bijective per tongue.

    Example:
        byte 0x2A (42) → prefix[2] + "'" + suffix[10]
        In Kor'aelin: vel'an

    Usage:
        # Single-tongue mode (default tongue for operations)
        tokenizer = SacredTongueTokenizer('ko')

        # Multi-tongue mode (all tongues available)
        tokenizer = SacredTongueTokenizer(TONGUES)
    """

    def __init__(self, tongues_or_code):
        """
        Initialize tokenizer with Sacred Tongues.

        Args:
            tongues_or_code: Either:
                - str: A single tongue code ('ko', 'av', 'ru', 'ca', 'um', 'dr')
                       Uses all tongues but sets this as default.
                - Dict[str, TongueSpec]: Dictionary of tongue specs keyed by code
        """
        # Handle both API styles: single tongue code (str) or full dict
        if isinstance(tongues_or_code, str):
            # Single tongue code - use global TONGUES but set default
            if tongues_or_code not in TONGUES:
                raise KeyError(f"Unknown tongue code: {tongues_or_code}")
            self.tongues = TONGUES
            self.default_tongue = tongues_or_code
        else:
            # Full dictionary of tongue specs
            self.tongues = tongues_or_code
            self.default_tongue = 'ko'  # Default to Kor'aelin
        self._build_tables()
    
    def _build_tables(self) -> None:
        """Precompute per-tongue byte↔token lookup tables."""
        self.byte_to_token: Dict[str, Dict[int, str]] = {}
        self.token_to_byte: Dict[str, Dict[str, int]] = {}
        
        for code, spec in self.tongues.items():
            if len(spec.prefixes) != 16 or len(spec.suffixes) != 16:
                raise ValueError(f"Tongue {code} must have 16 prefixes and 16 suffixes")
            
            b2t: Dict[int, str] = {}
            t2b: Dict[str, int] = {}
            
            for b in range(256):
                hi = (b >> 4) & 0x0F      # prefix index
                lo = b & 0x0F            # suffix index
                token = spec.prefixes[hi] + "'" + spec.suffixes[lo]
                b2t[b] = token
                t2b[token] = b
            
            self.byte_to_token[code] = b2t
            self.token_to_byte[code] = t2b
    
    # ---------- low-level, single-tongue API ----------
    
    def encode_bytes(self, tongue_code: str, data: bytes) -> List[str]:
        """Encode raw bytes into tokens of a single Sacred Tongue."""
        if tongue_code not in self.byte_to_token:
            raise KeyError(f"Unknown tongue code: {tongue_code}")
        table = self.byte_to_token[tongue_code]
        return [table[b] for b in data]
    
    def decode_tokens(self, tongue_code: str, tokens: List[str]) -> bytes:
        """Decode tokens of a single Sacred Tongue back into bytes."""
        if tongue_code not in self.token_to_byte:
            raise KeyError(f"Unknown tongue code: {tongue_code}")
        table = self.token_to_byte[tongue_code]
        try:
            return bytes(table[t] for t in tokens)
        except KeyError as e:
            raise ValueError(f"Invalid token for tongue {tongue_code}: {e}")
    
    # ---------- section-aware API (RWP SS1) ----------
    
    def encode_section(self, section: str, data: bytes) -> List[str]:
        """
        Encode a section (aad/salt/nonce/ct/tag/redact) using its canonical tongue.
        """
        tongue_code = SECTION_TONGUES[section]
        return self.encode_bytes(tongue_code, data)
    
    def decode_section(self, section: str, tokens: List[str]) -> bytes:
        """
        Decode tokens from a section (aad/salt/nonce/ct/tag/redact) to raw bytes.
        """
        tongue_code = SECTION_TONGUES[section]
        return self.decode_tokens(tongue_code, tokens)
    
    # ---------- legacy API (backward compatibility) ----------

    def encode_byte(self, b: int, tongue_code: str = None) -> str:
        """Encode a single byte to a token (legacy API)."""
        if tongue_code is None:
            tongue_code = self.default_tongue
        if not 0 <= b <= 255:
            raise ValueError(f"Byte must be 0-255, got {b}")
        return self.byte_to_token[tongue_code][b]

    def decode_token(self, token: str, tongue_code: str = None) -> int:
        """Decode a single token to a byte (legacy API)."""
        if tongue_code is None:
            tongue_code = self.default_tongue
        if token not in self.token_to_byte[tongue_code]:
            raise ValueError(f"Unknown token: {token}")
        return self.token_to_byte[tongue_code][token]

    def encode(self, data: bytes, tongue_code: str = None) -> str:
        """
        Encode bytes to space-separated spell-text tokens (legacy API).

        Args:
            data: Raw bytes to encode
            tongue_code: Tongue to use (default: instance default tongue)

        Returns:
            Space-separated token string with tongue prefix
            Example: "ko:sil'a ko:vel'an ko:thul'ir"
        """
        if tongue_code is None:
            tongue_code = self.default_tongue
        tokens = [f"{tongue_code}:{self.byte_to_token[tongue_code][b]}" for b in data]
        return ' '.join(tokens)

    def decode(self, spelltext: str, tongue_code: str = None) -> bytes:
        """
        Decode spell-text tokens back to bytes (legacy API).

        Args:
            spelltext: Space-separated tokens (with or without tongue prefix)
            tongue_code: Tongue to use (default: instance default tongue)

        Returns:
            Decoded bytes
        """
        if tongue_code is None:
            tongue_code = self.default_tongue
        result = []
        for token in spelltext.split():
            # Strip tongue prefix if present (e.g., "ko:sil'a" → "sil'a")
            if ':' in token:
                _, token = token.split(':', 1)
            result.append(self.token_to_byte[tongue_code][token])
        return bytes(result)


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

# Singleton instance you can import and use
SACRED_TONGUE_TOKENIZER = SacredTongueTokenizer(TONGUES)


# =============================================================================
# HIGH-LEVEL ENCODING FUNCTIONS (legacy API)
# =============================================================================

def encode_to_spelltext(data: bytes, section: str) -> str:
    """
    Encode bytes using the canonical tongue for a given section.
    
    Args:
        data: Raw bytes to encode
        section: One of 'aad', 'salt', 'nonce', 'ct', 'tag', 'redact'
    
    Returns:
        Spell-text encoded string
    """
    tongue_code = SECTION_TONGUES.get(section, 'ca')  # Default to Cassisivadan
    return SACRED_TONGUE_TOKENIZER.encode(data, tongue_code)


def decode_from_spelltext(spelltext: str, section: str) -> bytes:
    """
    Decode spell-text using the canonical tongue for a given section.
    """
    tongue_code = SECTION_TONGUES.get(section, 'ca')
    return SACRED_TONGUE_TOKENIZER.decode(spelltext, tongue_code)


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


def parse_ss1_blob(blob: str) -> Dict[str, Any]:
    """
    Parse an SS1 spell-text blob.
    
    Returns:
        Dict with keys: version, kid, aad, salt, nonce, ct, tag
    """
    if not blob.startswith('SS1|'):
        raise ValueError("Invalid SS1 blob: must start with 'SS1|'")
    
    parts = blob.split('|')
    result: Dict[str, Any] = {'version': 'SS1'}
    
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

def compute_lws_weights(tongue_code: str) -> List[float]:
    """
    Compute Langues Weighting System weights for a Sacred Tongue.
    
    Uses golden ratio powers (φ^i) for importance hierarchy,
    normalized to sum to 1.
    """
    PHI = 1.618033988749895  # Golden ratio
    weights = [PHI ** i for i in range(16)]
    total = sum(weights)
    weights = [w / total for w in weights]
    return weights


def get_tongue_signature(tongue_code: str) -> bytes:
    """
    Get the unique cryptographic signature for a Sacred Tongue.
    
    This is used for authentication and verification in the
    polyglot interoperability layer.
    
    Returns:
        32-byte SHA-256 hash of the tongue's vocabulary
    """
    import hashlib
    tongue = TONGUES[tongue_code]
    vocab_str = '|'.join(tongue.prefixes) + '||' + '|'.join(tongue.suffixes)
    return hashlib.sha256(vocab_str.encode('utf-8')).digest()
