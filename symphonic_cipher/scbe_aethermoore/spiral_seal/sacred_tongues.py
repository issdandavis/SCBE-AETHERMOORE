"""
Sacred Tongue Tokenizer - SS1 Spell-Text Encoding

Deterministic 256-word lists (16 prefixes × 16 suffixes) for each of the
six Sacred Tongues. Each byte maps to exactly one token of the form
"prefix'suffix". Section helpers add tongue prefixes (e.g., "ko:" for nonce).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple, Any


# =============================================================================
# Tongue specifications
# =============================================================================


@dataclass(frozen=True)
class TongueSpec:
    code: str
    name: str
    prefixes: Tuple[str, ...]
    suffixes: Tuple[str, ...]
    domain: str


KOR_AELIN = TongueSpec(
    code="ko",
    name="Kor'aelin",
    prefixes=(
        "sil", "kor", "vel", "zar", "keth", "thul", "nav", "ael",
        "ra", "med", "gal", "lan", "joy", "good", "nex", "vara",
    ),
    suffixes=(
        "a", "ae", "ei", "ia", "oa", "uu", "eth", "ar",
        "or", "il", "an", "en", "un", "ir", "oth", "esh",
    ),
    domain="nonce/flow/intent",
)

AVALI = TongueSpec(
    code="av",
    name="Avali",
    prefixes=(
        "saina", "talan", "vessa", "maren", "oriel", "serin", "nurel", "lirea",
        "kiva", "lumen", "calma", "ponte", "verin", "nava", "sela", "tide",
    ),
    suffixes=(
        "a", "e", "i", "o", "u", "y", "la", "re",
        "na", "sa", "to", "mi", "ve", "ri", "en", "ul",
    ),
    domain="aad/header/metadata",
)

RUNETHIC = TongueSpec(
    code="ru",
    name="Runethic",
    prefixes=(
        "khar", "drath", "bront", "vael", "ur", "mem", "krak", "tharn",
        "groth", "basalt", "rune", "sear", "oath", "gnarl", "rift", "iron",
    ),
    suffixes=(
        "ak", "eth", "ik", "ul", "or", "ar", "um", "on",
        "ir", "esh", "nul", "vek", "dra", "kh", "va", "th",
    ),
    domain="salt/binding",
)

CASSISIVADAN = TongueSpec(
    code="ca",
    name="Cassisivadan",
    prefixes=(
        "bip", "bop", "klik", "loopa", "ifta", "thena", "elsa", "spira",
        "rythm", "quirk", "fizz", "gear", "pop", "zip", "mix", "chass",
    ),
    suffixes=(
        "a", "e", "i", "o", "u", "y", "ta", "na",
        "sa", "ra", "lo", "mi", "ki", "zi", "qwa", "sh",
    ),
    domain="ciphertext/bitcraft",
)

UMBROTH = TongueSpec(
    code="um",
    name="Umbroth",
    prefixes=(
        "veil", "zhur", "nar", "shul", "math", "hollow", "hush", "thorn",
        "dusk", "echo", "ink", "wisp", "bind", "ache", "null", "shade",
    ),
    suffixes=(
        "a", "e", "i", "o", "u", "ae", "sh", "th",
        "ak", "ul", "or", "ir", "en", "on", "vek", "nul",
    ),
    domain="redaction/veil",
)

DRAUMRIC = TongueSpec(
    code="dr",
    name="Draumric",
    prefixes=(
        "anvil", "tharn", "mek", "grond", "draum", "ektal", "temper", "forge",
        "stone", "steam", "oath", "seal", "frame", "pillar", "rivet", "ember",
    ),
    suffixes=(
        "a", "e", "i", "o", "u", "ae", "rak", "mek",
        "tharn", "grond", "vek", "ul", "or", "ar", "en", "on",
    ),
    domain="tag/structure",
)


TONGUES: Dict[str, TongueSpec] = {
    "ko": KOR_AELIN,
    "av": AVALI,
    "ru": RUNETHIC,
    "ca": CASSISIVADAN,
    "um": UMBROTH,
    "dr": DRAUMRIC,
}


SECTION_TONGUES: Dict[str, str] = {
    "aad": "av",
    "salt": "ru",
    "nonce": "ko",
    "ct": "ca",
    "tag": "dr",
    "redact": "um",
    "veil": "um",
}
DOMAIN_TONGUE_MAP = SECTION_TONGUES


class SacredTongue(Enum):
    KORAELIN = "ko"
    AVALI = "av"
    RUNETHIC = "ru"
    CASSISIVADAN = "ca"
    UMBROTH = "um"
    DRAUMRIC = "dr"


# Alias for compatibility with older tests
Token = str


TONGUE_WORDLISTS: Dict[SacredTongue, Tuple[Tuple[str, ...], Tuple[str, ...]]] = {
    SacredTongue.KORAELIN: (KOR_AELIN.prefixes, KOR_AELIN.suffixes),
    SacredTongue.AVALI: (AVALI.prefixes, AVALI.suffixes),
    SacredTongue.RUNETHIC: (RUNETHIC.prefixes, RUNETHIC.suffixes),
    SacredTongue.CASSISIVADAN: (CASSISIVADAN.prefixes, CASSISIVADAN.suffixes),
    SacredTongue.UMBROTH: (UMBROTH.prefixes, UMBROTH.suffixes),
    SacredTongue.DRAUMRIC: (DRAUMRIC.prefixes, DRAUMRIC.suffixes),
}


# =============================================================================
# Tokenizer
# =============================================================================


class SacredTongueTokenizer:
    """Encode/decode bytes to Sacred Tongue spell-text tokens."""

    def __init__(self, tongue_code: str = "ko"):
        if tongue_code not in TONGUES:
            raise ValueError(f"Unknown tongue: {tongue_code}")
        self.tongue_code = tongue_code
        spec = TONGUES[tongue_code]

        tokens: List[str] = []
        reverse: Dict[str, int] = {}
        for b in range(256):
            prefix = spec.prefixes[b >> 4]
            suffix = spec.suffixes[b & 0x0F]
            tok = f"{prefix}'{suffix}"
            tokens.append(tok)
            reverse[tok] = b

        self._byte_to_token = tokens
        self._token_to_byte = reverse

    def encode_byte(self, b: int) -> str:
        if not 0 <= b <= 255:
            raise ValueError(f"Byte must be 0-255, got {b}")
        return self._byte_to_token[b]

    def decode_token(self, token: str) -> int:
        if token not in self._token_to_byte:
            raise ValueError("Unknown token")
        return self._token_to_byte[token]

    def encode(self, data: bytes) -> str:
        if not data:
            return ""
        return " ".join(f"{self.tongue_code}:{self.encode_byte(b)}" for b in data)

    def decode(self, spelltext: str) -> bytes:
        if not spelltext:
            return b""
        result = bytearray()
        for part in spelltext.split():
            token = part.split(":", 1)[-1]  # strip optional prefix
            result.append(self.decode_token(token))
        return bytes(result)

    def encode_to_string(self, data: bytes, separator: str = " ") -> str:
        if not data:
            return ""
        return separator.join(f"{self.tongue_code}:{self.encode_byte(b)}" for b in data)

    def decode_from_string(self, spelltext: str, separator: str = " ") -> bytes:
        if not spelltext:
            return b""
        parts = [p for p in spelltext.split(separator) if p]
        result = bytearray()
        for part in parts:
            token = part.split(":", 1)[-1]
            result.append(self.decode_token(token))
        return bytes(result)


_GLOBAL_TOKENIZER: SacredTongueTokenizer | None = None


def get_tokenizer(tongue: SacredTongue | str = "ko") -> SacredTongueTokenizer:
    global _GLOBAL_TOKENIZER
    code = tongue.value if isinstance(tongue, SacredTongue) else tongue
    if _GLOBAL_TOKENIZER is None or _GLOBAL_TOKENIZER.tongue_code != code:
        _GLOBAL_TOKENIZER = SacredTongueTokenizer(code)
    return _GLOBAL_TOKENIZER


def get_tongue_for_domain(section: str) -> SacredTongue:
    code = SECTION_TONGUES.get(section)
    if not code:
        raise ValueError(f"Unknown section: {section}")
    return SacredTongue(code)


def get_combined_alphabet() -> Dict[str, Any]:
    prefixes: List[str] = []
    suffixes: List[str] = []
    for pre, suf in TONGUE_WORDLISTS.values():
        prefixes.extend(pre)
        suffixes.extend(suf)
    return {
        "prefixes": prefixes,
        "suffixes": suffixes,
        "total_unique_prefixes": len(set(prefixes)),
        "total_unique_suffixes": len(set(suffixes)),
    }


def get_magical_signature(tongue: SacredTongue | str = SacredTongue.KORAELIN) -> str:
    code = tongue.value if isinstance(tongue, SacredTongue) else tongue
    import hashlib
    return hashlib.blake2s(code.encode("utf-8"), digest_size=8).hexdigest()


def get_tongue_signature(tongue_code: str) -> bytes:
    import hashlib
    spec = TONGUES[tongue_code]
    vocab = "|".join(spec.prefixes) + "||" + "|".join(spec.suffixes)
    return hashlib.sha256(vocab.encode("utf-8")).digest()


# =============================================================================
# Section helpers
# =============================================================================


def encode_to_spelltext(data: bytes, section: str) -> str:
    tongue_code = SECTION_TONGUES.get(section, "ca")
    tokenizer = SacredTongueTokenizer(tongue_code)
    return tokenizer.encode_to_string(data, " ")


def decode_from_spelltext(spelltext: str, section: str) -> bytes:
    tongue_code = SECTION_TONGUES.get(section, "ca")
    tokenizer = SacredTongueTokenizer(tongue_code)
    return tokenizer.decode_from_string(spelltext, " ")


def format_ss1_blob(
    kid: str,
    aad: str,
    salt: bytes,
    nonce: bytes,
    ciphertext: bytes,
    tag: bytes,
) -> str:
    parts = [
        "SS1",
        f"kid={kid}",
        f"aad={aad}",
        f"salt={encode_to_spelltext(salt, 'salt')}",
        f"nonce={encode_to_spelltext(nonce, 'nonce')}",
        f"ct={encode_to_spelltext(ciphertext, 'ct')}",
        f"tag={encode_to_spelltext(tag, 'tag')}",
    ]
    return "|".join(parts)


def parse_ss1_blob(blob: str) -> Dict[str, Any]:
    if not blob.startswith("SS1|"):
        raise ValueError("Invalid SS1 blob: must start with 'SS1|'")
    parts = blob.split("|")
    result: Dict[str, Any] = {"version": "SS1"}
    for part in parts[1:]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key in ("salt", "nonce", "ct", "tag"):
            section_map = {"salt": "salt", "nonce": "nonce", "ct": "ct", "tag": "tag"}
            result[key] = decode_from_spelltext(value, section_map[key])
        else:
            result[key] = value
    return result


# =============================================================================
# Langues Weighting System (for compatibility with existing interfaces)
# =============================================================================


def compute_lws_weights(tongue_code: str) -> List[float]:
    PHI = 1.618033988749895
    weights = [PHI ** i for i in range(16)]
    total = sum(weights)
    return [w / total for w in weights]
