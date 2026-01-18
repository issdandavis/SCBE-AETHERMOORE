"""
Sacred Tongues Tokenizer

Encodes raw bytes into Sacred-Tongue tokens using deterministic 256-word lists.
Each tongue has 16 prefixes × 16 suffixes = 256 unique tokens.

Token mapping: byte = prefix_index * 16 + suffix_index
Token format: prefix'suffix (apostrophe is morpheme seam)

The Six Sacred Tongues and their domains:
- Kor'aelin (ko): Control Flow & Collaboration → nonce (flow/intent)
- Avali (av): I/O, Messaging & Modules → aad (context/greeting)
- Runethic (ru): Scope, Constraints & Seals → salt (binding)
- Cassisivadan (ca): Logic, Math & Bitcraft → ciphertext (bits/maths)
- Umbroth (um): Privacy, Redaction & Shadow → redaction wrapper (veil)
- Draumric (dr): Types, Structures & Build → auth tag (structure stands)
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class SacredTongue(Enum):
    """The Six Sacred Tongues of the Spiralverse."""
    KORAELIN = "ko"      # Control Flow & Collaboration
    AVALI = "av"         # I/O, Messaging & Modules
    RUNETHIC = "ru"      # Scope, Constraints & Seals
    CASSISIVADAN = "ca"  # Logic, Math & Bitcraft
    UMBROTH = "um"       # Privacy, Redaction & Shadow
    DRAUMRIC = "dr"      # Types, Structures & Build


# =============================================================================
# SACRED TONGUE WORDLISTS (v1)
# =============================================================================
# DO NOT CHANGE without bumping version SS1 → SS2 (breaks existing secrets)

TONGUE_WORDLISTS: Dict[SacredTongue, Tuple[List[str], List[str]]] = {
    # Kor'aelin - Flow/Intent (for nonce encoding)
    SacredTongue.KORAELIN: (
        # Prefixes (16)
        ["sil", "kor", "vel", "zar", "keth", "thul", "nav", "ael",
         "ra", "med", "gal", "lan", "joy", "good", "nex", "vara"],
        # Suffixes (16)
        ["a", "ae", "ei", "ia", "oa", "uu", "eth", "ar",
         "or", "il", "an", "en", "un", "ir", "oth", "esh"]
    ),

    # Avali - Diplomacy/Context (for aad encoding)
    SacredTongue.AVALI: (
        # Prefixes (16)
        ["saina", "talan", "vessa", "maren", "oriel", "serin", "nurel", "lirea",
         "kiva", "lumen", "calma", "ponte", "verin", "nava", "sela", "tide"],
        # Suffixes (16)
        ["a", "e", "i", "o", "u", "y", "la", "re",
         "na", "sa", "to", "mi", "ve", "ri", "en", "ul"]
    ),

    # Runethic - Binding (for salt encoding)
    SacredTongue.RUNETHIC: (
        # Prefixes (16)
        ["khar", "drath", "bront", "vael", "ur", "mem", "krak", "tharn",
         "groth", "basalt", "rune", "sear", "oath", "gnarl", "rift", "iron"],
        # Suffixes (16)
        ["ak", "eth", "ik", "ul", "or", "ar", "um", "on",
         "ir", "esh", "nul", "vek", "dra", "kh", "va", "th"]
    ),

    # Cassisivadan - Bitcraft (for ciphertext encoding)
    SacredTongue.CASSISIVADAN: (
        # Prefixes (16)
        ["bip", "bop", "klik", "loopa", "ifta", "thena", "elsa", "spira",
         "rythm", "quirk", "fizz", "gear", "pop", "zip", "mix", "chass"],
        # Suffixes (16)
        ["a", "e", "i", "o", "u", "y", "ta", "na",
         "sa", "ra", "lo", "mi", "ki", "zi", "qwa", "sh"]
    ),

    # Umbroth - Shadow/Veil (for redaction wrapper)
    SacredTongue.UMBROTH: (
        # Prefixes (16)
        ["veil", "zhur", "nar", "shul", "math", "hollow", "hush", "thorn",
         "dusk", "echo", "ink", "wisp", "bind", "ache", "null", "shade"],
        # Suffixes (16)
        ["a", "e", "i", "o", "u", "ae", "sh", "th",
         "ak", "ul", "or", "ir", "en", "on", "vek", "nul"]
    ),

    # Draumric - Structure (for auth tag encoding)
    SacredTongue.DRAUMRIC: (
        # Prefixes (16)
        ["anvil", "tharn", "mek", "grond", "draum", "ektal", "temper", "forge",
         "stone", "steam", "oath", "seal", "frame", "pillar", "rivet", "ember"],
        # Suffixes (16)
        ["a", "e", "i", "o", "u", "ae", "rak", "mek",
         "tharn", "grond", "vek", "ul", "or", "ar", "en", "on"]
    ),
}


@dataclass
class Token:
    """A single Sacred Tongue token."""
    tongue: SacredTongue
    prefix: str
    suffix: str
    byte_value: int

    def __str__(self) -> str:
        """Format: tongue:prefix'suffix"""
        return f"{self.tongue.value}:{self.prefix}'{self.suffix}"

    @property
    def short(self) -> str:
        """Format without tongue prefix: prefix'suffix"""
        return f"{self.prefix}'{self.suffix}"


class SacredTongueTokenizer:
    """
    Encodes/decodes bytes to Sacred Tongue tokens.

    Each byte maps to one token via:
    - prefix_index = byte >> 4 (high nibble, 0-15)
    - suffix_index = byte & 0x0F (low nibble, 0-15)
    - token = prefix[prefix_index]'suffix[suffix_index]

    Usage:
        tokenizer = SacredTongueTokenizer()

        # Encode bytes to tokens
        tokens = tokenizer.encode(b"hello", SacredTongue.KORAELIN)

        # Decode tokens back to bytes
        data = tokenizer.decode(tokens)

        # Encode to string format
        spell_text = tokenizer.encode_to_string(b"hello", SacredTongue.KORAELIN)
        # "ko:vel'eth ko:vel'ar ko:vel'uu ko:vel'uu ko:vel'eth"
    """

    def __init__(self):
        # Build lookup tables for each tongue
        self._encode_tables: Dict[SacredTongue, List[Token]] = {}
        self._decode_tables: Dict[SacredTongue, Dict[str, int]] = {}

        for tongue in SacredTongue:
            prefixes, suffixes = TONGUE_WORDLISTS[tongue]
            encode_table = []
            decode_table = {}

            for byte_val in range(256):
                prefix_idx = byte_val >> 4
                suffix_idx = byte_val & 0x0F
                prefix = prefixes[prefix_idx]
                suffix = suffixes[suffix_idx]

                token = Token(
                    tongue=tongue,
                    prefix=prefix,
                    suffix=suffix,
                    byte_value=byte_val
                )
                encode_table.append(token)

                # Decode key is just prefix'suffix (without tongue prefix)
                decode_key = f"{prefix}'{suffix}"
                decode_table[decode_key] = byte_val

            self._encode_tables[tongue] = encode_table
            self._decode_tables[tongue] = decode_table

    def encode(self, data: bytes, tongue: SacredTongue) -> List[Token]:
        """Encode bytes to a list of tokens in the specified tongue."""
        table = self._encode_tables[tongue]
        return [table[b] for b in data]

    def decode(self, tokens: List[Token]) -> bytes:
        """Decode a list of tokens back to bytes."""
        return bytes(t.byte_value for t in tokens)

    def encode_to_string(self, data: bytes, tongue: SacredTongue,
                         separator: str = " ") -> str:
        """Encode bytes to a spell-text string."""
        tokens = self.encode(data, tongue)
        return separator.join(str(t) for t in tokens)

    def decode_from_string(self, spell_text: str, tongue: SacredTongue,
                           separator: str = " ") -> bytes:
        """Decode a spell-text string back to bytes."""
        decode_table = self._decode_tables[tongue]
        tongue_prefix = f"{tongue.value}:"

        result = []
        for token_str in spell_text.split(separator):
            # Remove tongue prefix if present
            if token_str.startswith(tongue_prefix):
                token_str = token_str[len(tongue_prefix):]

            if token_str in decode_table:
                result.append(decode_table[token_str])
            else:
                raise ValueError(f"Unknown token: {token_str}")

        return bytes(result)

    def get_token_for_byte(self, byte_val: int, tongue: SacredTongue) -> Token:
        """Get the token for a specific byte value."""
        return self._encode_tables[tongue][byte_val]

    def get_byte_for_token(self, token_str: str, tongue: SacredTongue) -> int:
        """Get the byte value for a token string (prefix'suffix format)."""
        return self._decode_tables[tongue][token_str]


# =============================================================================
# TONGUE DOMAIN MAPPINGS (for SS1 format)
# =============================================================================

# Maps data types to their assigned tongues
DOMAIN_TONGUE_MAP = {
    "aad": SacredTongue.AVALI,        # Associated Authenticated Data
    "salt": SacredTongue.RUNETHIC,    # KDF salt (binding)
    "nonce": SacredTongue.KORAELIN,   # AEAD nonce (flow/intent)
    "ct": SacredTongue.CASSISIVADAN,  # Ciphertext (bitcraft)
    "tag": SacredTongue.DRAUMRIC,     # Auth tag (structure)
    "veil": SacredTongue.UMBROTH,     # Redaction wrapper (shadow)
}


def get_tongue_for_domain(domain: str) -> SacredTongue:
    """Get the appropriate tongue for a data domain."""
    if domain not in DOMAIN_TONGUE_MAP:
        raise ValueError(f"Unknown domain: {domain}. Valid: {list(DOMAIN_TONGUE_MAP.keys())}")
    return DOMAIN_TONGUE_MAP[domain]


# =============================================================================
# COMBINED ALPHABET (Full 26-letter reconstruction)
# =============================================================================

def get_combined_alphabet() -> Dict[str, List[str]]:
    """
    When you break up all six tongues' alphabets, you get a full alphabet.
    This returns the unique letters/sounds from all tongues combined.
    """
    all_prefixes = set()
    all_suffixes = set()

    for tongue in SacredTongue:
        prefixes, suffixes = TONGUE_WORDLISTS[tongue]
        all_prefixes.update(prefixes)
        all_suffixes.update(suffixes)

    return {
        "prefixes": sorted(all_prefixes),
        "suffixes": sorted(all_suffixes),
        "total_unique_prefixes": len(all_prefixes),
        "total_unique_suffixes": len(all_suffixes)
    }


def get_magical_signature(tongue: SacredTongue) -> str:
    """
    Each tongue has a unique 'magical signature' based on its wordlist.
    This is the hash of its prefix+suffix set - used for authentication.
    """
    import hashlib

    prefixes, suffixes = TONGUE_WORDLISTS[tongue]
    signature_data = "|".join(prefixes) + "||" + "|".join(suffixes)
    return hashlib.sha256(signature_data.encode()).hexdigest()[:16]


# =============================================================================
# SPIRALSCRIPT KEYWORDS BY TONGUE
# =============================================================================

SPIRALSCRIPT_KEYWORDS = {
    SacredTongue.KORAELIN: {
        "vel": "invite (begin cooperative intent)",
        "sil": "together (synchronize/barrier)",
        "sil'thara": "grow-together (merge/consensus)",
        "thul": "spiral (iteration/fold)",
        "keth": "time (budgeted/time-cost)",
        "ra>": "flow (pipe operator)",
        "nav'een": "map/transform"
    },
    SacredTongue.AVALI: {
        "oriel": "council (import module)",
        "serin": "send (send event/message)",
        "nurel": "receive (return/await)",
        "talan": "bridge (connect tool/API)",
        "saina": "greeting (friendly output/log)"
    },
    SacredTongue.RUNETHIC: {
        "drath{}": "ward (scoped block)",
        "khar": "lock (immutable binding)",
        "khar-vek": "lock firmly (freeze/deny mutation)",
        "bront": "ordinance (declare rule/constraint)",
        "vael": "leyline (global shared context)"
    },
    SacredTongue.CASSISIVADAN: {
        "ifta": "if (conditional)",
        "thena": "then (conditional branch)",
        "elsa": "else (alternative branch)",
        "loopa": "loop (repeat execution)",
        "klik": "toggle (boolean/bit flip)"
    },
    SacredTongue.UMBROTH: {
        "veil()": "shroud (redact in logs)",
        "hollow": "safe-dark (sandboxed secure scope)",
        "math()": "witness (auditable log)",
        "nar'shul()": "remember (write to protected memory)",
        "zhur": "comment (silent ink)"
    },
    SacredTongue.DRAUMRIC: {
        "anvil": "foundation (variable binding)",
        "tharn": "structure (function/struct declaration)",
        "tharn'mek": "structure stands (finalize schema)",
        "grondrak": "forge (compile/build artifact)",
        "temper": "refine (optimize pass)"
    }
}


def get_tongue_keywords(tongue: SacredTongue) -> Dict[str, str]:
    """Get the SpiralScript keywords for a specific tongue."""
    return SPIRALSCRIPT_KEYWORDS.get(tongue, {})


# Global tokenizer instance
_tokenizer = None


def get_tokenizer() -> SacredTongueTokenizer:
    """Get the global tokenizer instance (lazy initialization)."""
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = SacredTongueTokenizer()
    return _tokenizer
