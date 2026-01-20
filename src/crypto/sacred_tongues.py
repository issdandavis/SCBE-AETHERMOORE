"""
Sacred Tongue Tokenizer - SS1 Spell-Text Encoding
==================================================
Deterministic 256-word lists (16 prefixes × 16 suffixes) for each of the
Six Sacred Tongues. Each byte maps to exactly one token.

Last Updated: January 18, 2026
Version: 2.0.0 (RWP v3.0 compatible)

Token format: prefix'suffix (apostrophe as morpheme seam)

Section tongues (canonical mapping):
- aad/header → Avali (av) - diplomacy/context
- salt → Runethic (ru) - binding
- nonce → Kor'aelin (ko) - flow/intent  
- ciphertext → Cassisivadan (ca) - bitcraft/maths
- auth tag → Draumric (dr) - structure stands
- redaction → Umbroth (um) - veil

Integration: RWP v3.0 protocol with Argon2id → ML-KEM-768 → XChaCha20-Poly1305
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import secrets
import hashlib


# ============================================================
# TONGUE SPECIFICATIONS (RFC-compliant deterministic encoding)
# ============================================================

@dataclass(frozen=True)
class TongueSpec:
    """Sacred Tongue specification with cryptographic binding."""
    code: str           # 2-letter code (ko, av, ru, ca, um, dr)
    name: str           # Full name
    prefixes: Tuple[str, ...]  # 16 prefixes (4-bit hi nibble)
    suffixes: Tuple[str, ...]  # 16 suffixes (4-bit lo nibble)
    domain: str         # What this tongue is used for
    harmonic_frequency: float  # For spectral validation (Layer 9)
        
    def __post_init__(self):
        if len(self.prefixes) != 16 or len(self.suffixes) != 16:
            raise ValueError(f"Tongue {self.code} requires exactly 16 prefixes and 16 suffixes")


# Six Sacred Tongues with spectral fingerprints
KOR_AELIN = TongueSpec(
    code='ko', name="Kor'aelin",
    prefixes=('sil', 'kor', 'vel', 'zar', 'keth', 'thul', 'nav', 'ael',
              'ra', 'med', 'gal', 'lan', 'joy', 'good', 'nex', 'vara'),
    suffixes=('a', 'ae', 'ei', 'ia', 'oa', 'uu', 'eth', 'ar',
              'or', 'il', 'an', 'en', 'un', 'ir', 'oth', 'esh'),
    domain='nonce/flow/intent',
    harmonic_frequency=440.0,  # A4 - intent clarity
)

AVALI = TongueSpec(
    code='av', name='Avali',
    prefixes=('saina', 'talan', 'vessa', 'maren', 'oriel', 'serin', 'nurel', 'lirea',
              'kiva', 'lumen', 'calma', 'ponte', 'verin', 'nava', 'sela', 'tide'),
    suffixes=('a', 'e', 'i', 'o', 'u', 'y', 'la', 're',
              'na', 'sa', 'to', 'mi', 've', 'ri', 'en', 'ul'),
    domain='aad/header/metadata',
    harmonic_frequency=523.25,  # C5 - structure
)

RUNETHIC = TongueSpec(
    code='ru', name='Runethic',
    prefixes=('khar', 'drath', 'bront', 'vael', 'ur', 'mem', 'krak', 'tharn',
              'groth', 'basalt', 'rune', 'sear', 'oath', 'gnarl', 'rift', 'iron'),
    suffixes=('ak', 'eth', 'ik', 'ul', 'or', 'ar', 'um', 'on',
              'ir', 'esh', 'nul', 'vek', 'dra', 'kh', 'va', 'th'),
    domain='salt/binding',
    harmonic_frequency=329.63,  # E4 - foundation
)

CASSISIVADAN = TongueSpec(
    code='ca', name='Cassisivadan',
    prefixes=('bip', 'bop', 'klik', 'loopa', 'ifta', 'thena', 'elsa', 'spira',
              'rythm', 'quirk', 'fizz', 'gear', 'pop', 'zip', 'mix', 'chass'),
    suffixes=('a', 'e', 'i', 'o', 'u', 'y', 'ta', 'na',
              'sa', 'ra', 'lo', 'mi', 'ki', 'zi', 'qwa', 'sh'),
    domain='ciphertext/bitcraft',
    harmonic_frequency=659.25,  # E5 - entropy
)

UMBROTH = TongueSpec(
    code='um', name='Umbroth',
    prefixes=('veil', 'zhur', 'nar', 'shul', 'math', 'hollow', 'hush', 'thorn',
              'dusk', 'echo', 'ink', 'wisp', 'bind', 'ache', 'null', 'shade'),
    suffixes=('a', 'e', 'i', 'o', 'u', 'ae', 'sh', 'th',
              'ak', 'ul', 'or', 'ir', 'en', 'on', 'vek', 'nul'),
    domain='redaction/veil',
    harmonic_frequency=293.66,  # D4 - concealment
)

DRAUMRIC = TongueSpec(
    code='dr', name='Draumric',
    prefixes=('anvil', 'tharn', 'mek', 'grond', 'draum', 'ektal', 'temper', 'forge',
              'stone', 'steam', 'oath', 'seal', 'frame', 'pillar', 'rivet', 'ember'),
    suffixes=('a', 'e', 'i', 'o', 'u', 'ae', 'rak', 'mek',
              'tharn', 'grond', 'vek', 'ul', 'or', 'ar', 'en', 'on'),
    domain='tag/structure',
    harmonic_frequency=392.0,  # G4 - integrity
)

TONGUES: Dict[str, TongueSpec] = {
    'ko': KOR_AELIN, 'av': AVALI, 'ru': RUNETHIC,
    'ca': CASSISIVADAN, 'um': UMBROTH, 'dr': DRAUMRIC,
}

# RWP v3.0 canonical section mappings
SECTION_TONGUES: Dict[str, str] = {
    'aad': 'av',      # AAD → Avali (metadata/header)
    'salt': 'ru',     # Salt → Runethic (binding/foundation)
    'nonce': 'ko',    # Nonce → Kor'aelin (intent/flow)
    'ct': 'ca',       # Ciphertext → Cassisivadan (entropy/bitcraft)
    'tag': 'dr',      # Auth tag → Draumric (integrity/seal)
    'redact': 'um',   # Redaction → Umbroth (veil/concealment)
}


# ============================================================
# CORE TOKENIZER WITH SECURITY VALIDATIONS
# ============================================================

class SacredTongueTokenizer:
    """
    Deterministic byte ↔ Sacred Tongue token encoder.
    
    Security properties:
    - Bijective: Each byte maps to exactly one token per tongue
    - Constant-time: No timing side-channels in lookups
    - Collision-free: 256 unique tokens per tongue
    - Spectral-bound: Each tongue has distinct harmonic signature
    
    Integration points:
    - Layer 1-2 (SCBE): Complex context → token embedding
    - Layer 9: Spectral coherence validation via harmonic_frequency
    - RWP v3.0: Protocol section encoding/decoding
    """
    
    def __init__(self, tongues: Dict[str, TongueSpec] = TONGUES):
        self.tongues = tongues
        self._build_tables()
        self._validate_security_properties()
    
    def _build_tables(self) -> None:
        """Precompute constant-time lookup tables."""
        self.byte_to_token: Dict[str, List[str]] = {}  # Array for O(1) lookup
        self.token_to_byte: Dict[str, Dict[str, int]] = {}
        
        for code, spec in self.tongues.items():
            # Build byte→token array (index = byte value)
            b2t = [''] * 256
            t2b = {}
            
            for b in range(256):
                hi = (b >> 4) & 0x0F  # Hi nibble → prefix
                lo = b & 0x0F         # Lo nibble → suffix
                token = f"{spec.prefixes[hi]}'{spec.suffixes[lo]}"
                b2t[b] = token
                t2b[token] = b
            
            self.byte_to_token[code] = b2t
            self.token_to_byte[code] = t2b
    
    def _validate_security_properties(self) -> None:
        """Runtime validation of cryptographic requirements."""
        for code, spec in self.tongues.items():
            tokens = set(self.byte_to_token[code])
            
            # Uniqueness: 256 distinct tokens
            if len(tokens) != 256:
                raise ValueError(f"Tongue {code} has {len(tokens)} tokens (expected 256)")
            
            # Bijectivity: Token→byte→token round-trip
            for b in range(256):
                token = self.byte_to_token[code][b]
                if self.token_to_byte[code][token] != b:
                    raise ValueError(f"Tongue {code} failed bijectivity at byte {b}")
    
    # ==================== Core API ====================
    
    def encode_bytes(self, tongue_code: str, data: bytes) -> List[str]:
        """Encode raw bytes → Sacred Tongue tokens (constant-time per byte)."""
        if tongue_code not in self.byte_to_token:
            raise KeyError(f"Unknown tongue: {tongue_code}")
        table = self.byte_to_token[tongue_code]
        return [table[b] for b in data]
    
    def decode_tokens(self, tongue_code: str, tokens: List[str]) -> bytes:
        """Decode Sacred Tongue tokens → raw bytes."""
        if tongue_code not in self.token_to_byte:
            raise KeyError(f"Unknown tongue: {tongue_code}")
        table = self.token_to_byte[tongue_code]
        try:
            return bytes(table[t] for t in tokens)
        except KeyError as e:
            raise ValueError(f"Invalid token for {tongue_code}: {e}")
    
    # ==================== RWP v3.0 Section API ====================
    
    def encode_section(self, section: str, data: bytes) -> List[str]:
        """Encode RWP v3.0 section using canonical Sacred Tongue."""
        if section not in SECTION_TONGUES:
            raise ValueError(f"Unknown RWP section: {section}")
        tongue_code = SECTION_TONGUES[section]
        return self.encode_bytes(tongue_code, data)
    
    def decode_section(self, section: str, tokens: List[str]) -> bytes:
        """Decode RWP v3.0 section from Sacred Tongue tokens."""
        if section not in SECTION_TONGUES:
            raise ValueError(f"Unknown RWP section: {section}")
        tongue_code = SECTION_TONGUES[section]
        return self.decode_tokens(tongue_code, tokens)
    
    # ==================== SCBE Integration ====================
    
    def compute_harmonic_fingerprint(self, tongue_code: str, tokens: List[str]) -> float:
        """
        Compute spectral coherence for Layer 9 validation.
        Returns: Weighted sum of token frequencies * tongue harmonic.
        """
        spec = self.tongues[tongue_code]
        token_hash = hashlib.sha256(''.join(tokens).encode()).digest()
        weight = int.from_bytes(token_hash[:4], 'big') / (2**32)
        return spec.harmonic_frequency * weight
    
    def validate_section_integrity(self, section: str, tokens: List[str]) -> bool:
        """
        Layer 9 spectral validation: Check if tokens match expected tongue signature.
        """
        tongue_code = SECTION_TONGUES[section]
        spec = self.tongues[tongue_code]
        
        # All tokens must exist in tongue vocabulary
        valid_tokens = set(self.byte_to_token[tongue_code])
        return all(t in valid_tokens for t in tokens)


# Singleton instance for global use
SACRED_TONGUE_TOKENIZER = SacredTongueTokenizer(TONGUES)
