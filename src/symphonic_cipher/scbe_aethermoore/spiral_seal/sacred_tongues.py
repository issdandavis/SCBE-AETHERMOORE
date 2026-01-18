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
    
    Each byte maps deterministically to one token:
        byte b → prefix[b >> 4] + "'" + suffix[b & 0x0F]
    
    Example:
        byte 0x2A (42) → prefix[2] + "'" + suffix[10]
        In Kor'aelin: vel'an
    """
    
    def __init__(self, tongue_code: str = 'ko'):
        """
        Initialize tokenizer for a specific Sacred Tongue.
        
        Args:
            tongue_code: One of 'ko', 'av', 'ru', 'ca', 'um', 'dr'
        """
        if tongue_code not in TONGUES:
            raise ValueError(f"Unknown tongue: {tongue_code}. Valid: {list(TONGUES.keys())}")
        
        self.tongue = TONGUES[tongue_code]
        self._build_lookup_tables()
    
    def _build_lookup_tables(self):
        """Build forward and reverse lookup tables."""
        # Forward: byte → token
        self._byte_to_token: List[str] = []
        for b in range(256):
            pi = b >> 4        # High nibble (0-15)
            si = b & 0x0F      # Low nibble (0-15)
            token = f"{self.tongue.prefixes[pi]}'{self.tongue.suffixes[si]}"
            self._byte_to_token.append(token)
        
        # Reverse: token → byte
        self._token_to_byte: Dict[str, int] = {
            token: b for b, token in enumerate(self._byte_to_token)
        }
    
    def encode_byte(self, b: int) -> str:
        """Encode a single byte to a token."""
        if not 0 <= b <= 255:
            raise ValueError(f"Byte must be 0-255, got {b}")
        return self._byte_to_token[b]
    
    def decode_token(self, token: str) -> int:
        """Decode a single token to a byte."""
        if token not in self._token_to_byte:
            raise ValueError(f"Unknown token: {token}")
        return self._token_to_byte[token]
    
    def encode(self, data: bytes) -> str:
        """
        Encode bytes to space-separated spell-text tokens.
        
        Args:
            data: Raw bytes to encode
        
        Returns:
            Space-separated token string with tongue prefix
            Example: "ko:sil'a ko:vel'an ko:thul'ir"
        """
        tokens = [f"{self.tongue.code}:{self._byte_to_token[b]}" for b in data]
        return ' '.join(tokens)
    
    def decode(self, spelltext: str) -> bytes:
        """
        Decode spell-text tokens back to bytes.
        
        Args:
            spelltext: Space-separated tokens (with or without tongue prefix)
        
        Returns:
            Decoded bytes
        """
        result = []
        for token in spelltext.split():
            # Strip tongue prefix if present (e.g., "ko:sil'a" → "sil'a")
            if ':' in token:
                _, token = token.split(':', 1)
            result.append(self._token_to_byte[token])
        return bytes(result)


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
        Spell-text encoded string
    """
    tongue_code = SECTION_TONGUES.get(section, 'ca')  # Default to Cassisivadan
    tokenizer = SacredTongueTokenizer(tongue_code)
    return tokenizer.encode(data)


def decode_from_spelltext(spelltext: str, section: str) -> bytes:
    """
    Decode spell-text using the canonical tongue for a given section.
    """
    tongue_code = SECTION_TONGUES.get(section, 'ca')
    tokenizer = SacredTongueTokenizer(tongue_code)
    return tokenizer.decode(spelltext)


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
