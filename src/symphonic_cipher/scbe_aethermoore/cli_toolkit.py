#!/usr/bin/env python3
"""
Aethermoore Suite CLI — GeoSeal + SCBE + Six-Tongue Toolkit

Unified command-line tool for:
  - encode/decode: Sacred Tongue bijective byte encoding
  - xlate: Cross-tongue retokenization with HMAC attestation
  - blend/unblend: Multi-tongue stripe encoding
  - geoseal-encrypt/decrypt: Context-bound envelope encryption
  - seed: AetherLex Seed — Sacred Tongue mnemonic to PQC key material

Run without args for selftest.

Usage:
  python cli_toolkit.py                     # selftest
  python cli_toolkit.py encode --tongue KO  # encode stdin
  python cli_toolkit.py xlate --src KO --dst AV  # cross-tongue
  python cli_toolkit.py seed --length 13    # generate mnemonic + derive seed
"""

import argparse
import base64
import dataclasses
import hashlib
import hmac
import json
import math
import os
import re
import statistics
import struct
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Iterable

# ---------- Constants ----------

MAX_PAYLOAD_BYTES = 16 * 1024 * 1024  # 16 MiB safety limit
_REPO_ROOT = Path(__file__).resolve().parents[3]
_ARC_EVAL_DIR = _REPO_ROOT / "artifacts" / "arc-data" / "ARC-AGI-master" / "data" / "evaluation"
_TASK_BALL_TARGET_REPORT = _REPO_ROOT / "artifacts" / "task_ball_target_report.json"
_REPO_SRC = _REPO_ROOT / "src"

# Some NeuroGolf modules still import sibling packages as top-level modules
# (for example `crypto.sacred_tongues`), so expose the repo `src` root when
# this CLI is executed as `python -m src.symphonic_cipher...`.
if str(_REPO_SRC) not in sys.path:
    sys.path.insert(0, str(_REPO_SRC))

# ---------- Core lexicon & tokenizer ----------

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]

# Token normalization: make decoding resilient across case differences and common
# unicode apostrophes that may appear when copying tokens from docs or chat.
_SMART_APOSTROPHES = {
    "\u2019": "'",  # right single quotation mark
    "\u2018": "'",  # left single quotation mark
    "\u201b": "'",  # single high-reversed-9 quotation mark
    "`": "'",  # grave accent
    "\u00b4": "'",  # acute accent
    "\u02bb": "'",  # modifier letter turned comma
    "\u02bc": "'",  # modifier letter apostrophe
}


def canon_token(token: str) -> str:
    """Canonical form for token lookup.

    Goal: make decoding resilient when tokens are copied through rich text
    (docs/chats/CSVs) where casing and apostrophe glyphs may drift.
    - Strips surrounding whitespace and common separators
    - Normalizes common unicode apostrophes to ASCII '
    - Lowercases
    - Removes zero-width spaces / BOM
    """
    if token is None:
        return ""
    s = str(token).replace("\u200b", "").replace("\ufeff", "")
    # tolerate tokens copied from CSV/JSON/prose (trailing separators/quotes)
    s = s.strip(' ,;|[]{}()"')
    for k, v in _SMART_APOSTROPHES.items():
        s = s.replace(k, v)
    return s.lower()


class Lexicons:
    def __init__(self, table: Dict[str, Dict[str, str]] | None = None):
        if table is None:
            table = self._canon_lexicons()
        self.by_idx: Dict[str, List[str]] = {}
        self.by_tok: Dict[str, Dict[str, int]] = {}
        for tg in TONGUES:
            m = table.get(tg)
            if not m:
                raise ValueError(f"missing tongue {tg} in lexicons")
            lst = [None] * 256
            for k, v in m.items():
                idx = int(k)
                if not (0 <= idx <= 255):
                    raise ValueError("lexicon indices must be 0..255")
                lst[idx] = v
            if any(x is None for x in lst):
                raise ValueError(f"lexicon {tg} incomplete")
            # Enforce bijection. We check uniqueness on the canonical form so
            # that tokens that differ only by case or smart apostrophes can't
            # silently collide at decode time.
            canon = [canon_token(x) for x in lst]
            if len(set(canon)) != 256:
                raise ValueError(
                    f"lexicon {tg} contains duplicate tokens under "
                    "canonicalization; ensure tokens remain unique even "
                    "ignoring case/smart quotes"
                )
            self.by_idx[tg] = lst
            inv: Dict[str, int] = {}
            for i, tok in enumerate(lst):
                inv[canon_token(tok)] = i
            self.by_tok[tg] = inv

    def token_of(self, tongue: str, b: int) -> str:
        return self.by_idx[tongue][b]

    def byte_of(self, tongue: str, token: str) -> int:
        inv = self.by_tok[tongue]
        key = canon_token(token)
        if key not in inv:
            raise KeyError(f"unknown token in {tongue}: {token!r} (canonical: {key!r})")
        return inv[key]

    # ── Canonical Sacred Tongues v1.1 (from sacredTongues.ts) ──────────
    # Each tongue: 16 prefixes × 16 suffixes = 256 tokens.
    # Token format: prefix'suffix (apostrophe as morpheme seam).
    # Index = (prefix_idx << 4) | suffix_idx.
    _CANON = {
        "KO": {
            "name": "Kor'aelin",
            "domain": "nonce/flow/intent",
            "prefixes": [
                "kor",
                "ael",
                "lin",
                "dah",
                "ru",
                "mel",
                "ik",
                "sor",
                "in",
                "tiv",
                "ar",
                "ul",
                "mar",
                "vex",
                "yn",
                "zha",
            ],
            "suffixes": [
                "ah",
                "el",
                "in",
                "or",
                "ru",
                "ik",
                "mel",
                "sor",
                "tiv",
                "ul",
                "vex",
                "zha",
                "dah",
                "lin",
                "yn",
                "mar",
            ],
        },
        "AV": {
            "name": "Avali",
            "domain": "aad/header/metadata",
            "prefixes": [
                "saina",
                "talan",
                "vessa",
                "maren",
                "oriel",
                "serin",
                "nurel",
                "lirea",
                "kiva",
                "lumen",
                "calma",
                "ponte",
                "verin",
                "nava",
                "sela",
                "tide",
            ],
            "suffixes": [
                "a",
                "e",
                "i",
                "o",
                "u",
                "y",
                "la",
                "re",
                "na",
                "sa",
                "to",
                "mi",
                "ve",
                "ri",
                "en",
                "ul",
            ],
        },
        "RU": {
            "name": "Runethic",
            "domain": "salt/binding",
            "prefixes": [
                "khar",
                "drath",
                "bront",
                "vael",
                "ur",
                "mem",
                "krak",
                "tharn",
                "groth",
                "basalt",
                "rune",
                "sear",
                "oath",
                "gnarl",
                "rift",
                "iron",
            ],
            "suffixes": [
                "ak",
                "eth",
                "ik",
                "ul",
                "or",
                "ar",
                "um",
                "on",
                "ir",
                "esh",
                "nul",
                "vek",
                "dra",
                "kh",
                "va",
                "th",
            ],
        },
        "CA": {
            "name": "Cassisivadan",
            "domain": "ciphertext/bitcraft",
            "prefixes": [
                "bip",
                "bop",
                "klik",
                "loopa",
                "ifta",
                "thena",
                "elsa",
                "spira",
                "rythm",
                "quirk",
                "fizz",
                "gear",
                "pop",
                "zip",
                "mix",
                "chass",
            ],
            "suffixes": [
                "a",
                "e",
                "i",
                "o",
                "u",
                "y",
                "ta",
                "na",
                "sa",
                "ra",
                "lo",
                "mi",
                "ki",
                "zi",
                "qwa",
                "sh",
            ],
        },
        "UM": {
            "name": "Umbroth",
            "domain": "redaction/veil",
            "prefixes": [
                "veil",
                "zhur",
                "nar",
                "shul",
                "math",
                "hollow",
                "hush",
                "thorn",
                "dusk",
                "echo",
                "ink",
                "wisp",
                "bind",
                "ache",
                "null",
                "shade",
            ],
            "suffixes": [
                "a",
                "e",
                "i",
                "o",
                "u",
                "ae",
                "sh",
                "th",
                "ak",
                "ul",
                "or",
                "ir",
                "en",
                "on",
                "vek",
                "nul",
            ],
        },
        "DR": {
            "name": "Draumric",
            "domain": "tag/structure",
            "prefixes": [
                "anvil",
                "tharn",
                "mek",
                "grond",
                "draum",
                "ektal",
                "temper",
                "forge",
                "stone",
                "steam",
                "oath",
                "seal",
                "frame",
                "pillar",
                "rivet",
                "ember",
            ],
            "suffixes": [
                "a",
                "e",
                "i",
                "o",
                "u",
                "ae",
                "rak",
                "mek",
                "tharn",
                "grond",
                "vek",
                "ul",
                "or",
                "ar",
                "en",
                "on",
            ],
        },
    }

    @classmethod
    def _canon_lexicons(cls) -> Dict[str, Dict[str, str]]:
        """Build 256-token bijective tables from canonical Sacred Tongues.

        Byte value b maps to: prefix[b >> 4] + "'" + suffix[b & 0xF].
        """
        out: Dict[str, Dict[str, str]] = {}
        for tg, spec in cls._CANON.items():
            pfx = spec["prefixes"]
            sfx = spec["suffixes"]
            assert len(pfx) == 16 and len(sfx) == 16, f"{tg}: need 16×16"
            table: Dict[str, str] = {}
            for i in range(256):
                table[str(i)] = f"{pfx[(i >> 4) & 0xF]}'{sfx[i & 0xF]}"
            out[tg] = table
        return out

    @staticmethod
    def _demo_lexicons() -> Dict[str, Dict[str, str]]:
        """Legacy placeholder lexicons (deprecated — use canon)."""
        HI = [
            "ka",
            "ke",
            "ki",
            "ko",
            "ku",
            "sa",
            "se",
            "si",
            "so",
            "su",
            "ra",
            "re",
            "ri",
            "ro",
            "ru",
            "za",
        ]
        LO = [
            "na",
            "ne",
            "ni",
            "no",
            "nu",
            "la",
            "le",
            "li",
            "lo",
            "lu",
            "ta",
            "te",
            "ti",
            "to",
            "tu",
            "ma",
        ]

        def gen(prefix: str) -> Dict[str, str]:
            out: Dict[str, str] = {}
            for i in range(256):
                hi = HI[(i >> 4) & 0xF]
                lo = LO[i & 0xF]
                out[str(i)] = f"{prefix.lower()}{hi}'{lo}"
            return out

        return {tg: gen(tg) for tg in TONGUES}


class TongueTokenizer:
    def __init__(self, lex: Lexicons):
        self.lex = lex

    def encode_bytes(self, tongue: str, data: bytes) -> List[str]:
        return [self.lex.token_of(tongue, b) for b in data]

    def decode_tokens(self, tongue: str, tokens: Iterable[str]) -> bytes:
        arr = bytearray()
        for tok in tokens:
            if not tok:
                continue
            arr.append(self.lex.byte_of(tongue, tok))
        return bytes(arr)

    def normalize_token_stream(self, text: str) -> List[str]:
        """Keep normalization conservative: split on whitespace and common
        separators used in JSON/CSV/text dumps."""
        if text is None:
            return []
        for ch in [",", ";", "|", "\t", "\n", "\r", "[", "]", "{", "}", "(", ")"]:
            text = text.replace(ch, " ")
        toks: List[str] = []
        for part in text.split():
            part = part.strip()
            if part:
                toks.append(part)
        return toks


# ---------- Cross-tokenization ----------


@dataclasses.dataclass
class XlateAttestation:
    src: str
    dst: str
    mode: str
    ts: float
    phase_delta: float
    weight_ratio: float
    sha256_bytes: str
    hmac_attest: str


class CrossTokenizer:
    PHASE = {
        "KO": 0,
        "AV": math.pi / 3,
        "RU": 2 * math.pi / 3,
        "CA": math.pi,
        "UM": 4 * math.pi / 3,
        "DR": 5 * math.pi / 3,
    }
    # PHDM weights (phi^n progression — crisis/governance)
    WEIGHT_PHDM = {
        "KO": 1.000,
        "AV": 1.618,
        "RU": 2.618,
        "CA": 4.236,
        "UM": 6.854,
        "DR": 11.090,
    }
    # LWS weights (linear — base operations)
    WEIGHT_LWS = {
        "KO": 1.000,
        "AV": 1.125,
        "RU": 1.250,
        "CA": 1.333,
        "UM": 1.500,
        "DR": 1.667,
    }
    # Default to PHDM (backwards compatible)
    WEIGHT = WEIGHT_PHDM

    def __init__(self, tok: TongueTokenizer):
        self.tok = tok

    def to_bytes_from_tokens(self, tongue: str, token_text: str) -> bytes:
        toks = self.tok.normalize_token_stream(token_text)
        return self.tok.decode_tokens(tongue, toks)

    def to_tokens_from_bytes(self, tongue: str, data: bytes) -> List[str]:
        return self.tok.encode_bytes(tongue, data)

    def retokenize(
        self,
        src_tg: str,
        dst_tg: str,
        token_text: str,
        mode: str = "byte",
        attest_key: bytes | None = None,
    ) -> Tuple[List[str], XlateAttestation]:
        if mode not in ("byte", "semantic"):
            raise ValueError("mode must be 'byte' or 'semantic'")
        b = self.to_bytes_from_tokens(src_tg, token_text)
        out_tokens = self.to_tokens_from_bytes(dst_tg, b)
        sha = hashlib.sha256(b).hexdigest()
        phase_delta = (self.PHASE[dst_tg] - self.PHASE[src_tg]) % (2 * math.pi)
        weight_ratio = self.WEIGHT[dst_tg] / self.WEIGHT[src_tg]
        msg = (f"{src_tg}->{dst_tg}|{mode}|{sha}|{phase_delta:.6f}" f"|{weight_ratio:.6f}|{int(time.time())}").encode()
        h = base64.b64encode(hmac.new(attest_key or b"aether-attest-default", msg, hashlib.sha256).digest()).decode()
        attest = XlateAttestation(src_tg, dst_tg, mode, time.time(), phase_delta, weight_ratio, sha, h)
        return out_tokens, attest

    def blend(self, pattern: List[str], data: bytes) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        for i, byte in enumerate(data):
            tg = pattern[i % len(pattern)]
            out.append((tg, self.tok.lex.token_of(tg, byte)))
        return out

    def unblend(self, pattern: List[str], pairs: List[Tuple[str, str]]) -> bytes:
        arr = bytearray()
        for i, (tg, tok) in enumerate(pairs):
            expected = pattern[i % len(pattern)]
            if tg != expected:
                raise ValueError("blend pattern mismatch")
            arr.append(self.tok.lex.byte_of(tg, tok))
        return bytes(arr)


# ---------- GeoSeal minimal reference (unchanged API) ----------


def _zscore(xs: List[float]) -> List[float]:
    mu = sum(xs) / len(xs)
    var = sum((x - mu) * (x - mu) for x in xs) / max(1, len(xs) - 1)
    sd = math.sqrt(var) if var > 0 else 1.0
    return [(x - mu) / sd for x in xs]


def project_to_sphere(ctx: List[float]) -> List[float]:
    take = ctx[:3] if len(ctx) >= 3 else (ctx + [0, 0, 0])[:3]
    z = _zscore(list(take))
    norm = math.sqrt(sum(v * v for v in z)) or 1.0
    return [v / norm for v in z]


def project_to_cube(ctx: List[float], m: int = 6) -> List[float]:
    arr = [(math.tanh(x / 5) + 1) / 2 for x in (ctx[:m] if len(ctx) >= m else ctx + [0] * (m - len(ctx)))]
    return [min(1.0, max(0.0, x)) for x in arr]


def healpix_id(u: List[float], L: int) -> str:
    q = tuple(int((v + 1) * 1000) for v in u)
    return f"S{L}:{q}"


def morton_id(v: List[float], L: int) -> str:
    q = tuple(int(x * (10 ** min(3, 1 + L))) for x in v[: min(6, len(v))])
    return f"C{L}:{q}"


def potentials(u: List[float], v: List[float]) -> Tuple[float, float]:
    R = sum(abs(x) for x in u) + 0.1 * sum(v)
    T = 0.5 + 0.05 * len([x for x in v if x < 0.2])
    P = 0.7 * R - 0.3 * T
    margin = 0.5 - abs(u[0])
    return P, margin


def classify(h: str, z: str, P: float, margin: float) -> str:
    return "interior" if ("S" in h and "C" in z and P < 0.6 and margin > 0.05) else "exterior"


class ConcentricRingPolicy:
    RINGS = [
        (0.0, 0.3, "core", 5, 1, 8, 0.001),
        (0.3, 0.5, "inner", 20, 1, 8, 0.005),
        (0.5, 0.7, "middle", 100, 2, 16, 0.01),
        (0.7, 0.9, "outer", 500, 3, 24, 0.05),
        (0.9, 1.0, "edge", 5000, 4, 32, 0.2),
    ]

    def classify(self, r: float) -> dict:
        for rmin, rmax, name, lat, sigs, powb, decay in self.RINGS:
            if rmin <= r < rmax:
                return {
                    "ring": name,
                    "max_latency_ms": lat,
                    "required_signatures": sigs,
                    "pow_bits": powb,
                    "trust_decay_rate": decay,
                }
        return {"ring": "beyond", "action": "REJECT"}


# ---------- Envelope crypto (demo/mocked PQC) ----------


def hkdf(key: bytes, info: str) -> bytes:
    return hmac.new(key, info.encode(), hashlib.sha256).digest()


def kyber_encaps(pk: bytes) -> Tuple[bytes, bytes]:
    ss = hashlib.sha256(b"ss" + pk).digest()
    ct = hashlib.sha256(b"ct" + pk).digest()
    return ss, ct


def kyber_decaps(sk: bytes, ct: bytes) -> bytes:
    return hashlib.sha256(b"ss" + sk).digest()


def _mock_dsa_key(material: bytes) -> bytes:
    """Derive deterministic HMAC key so sign(sk)/verify(pk) round-trip in mock mode."""
    return hashlib.sha256(b"mock-dsa:" + material).digest()


def dsa_sign(sk: bytes, msg: bytes) -> bytes:
    return hmac.new(_mock_dsa_key(sk), msg, hashlib.sha256).digest()


def dsa_verify(pk: bytes, msg: bytes, sig: bytes) -> bool:
    return hmac.compare_digest(hmac.new(_mock_dsa_key(pk), msg, hashlib.sha256).digest(), sig)


# ---------- GeoSeal encrypt/decrypt ----------


def geoseal_encrypt(
    plaintext_b64: str,
    context: List[float],
    pk_kem_b64: str,
    sk_dsa_b64: str,
    Ls: int = 2,
    Lc: int = 2,
) -> dict:
    pt = base64.b64decode(plaintext_b64)
    u = project_to_sphere(context)
    v = project_to_cube(context)
    h = healpix_id(u, Ls)
    z = morton_id(v, Lc)
    P, margin = potentials(u, v)
    path = classify(h, z, P, margin)
    ss, ct_k = kyber_encaps(base64.b64decode(pk_kem_b64))
    Ks = hkdf(ss, f"geo:sphere|{h}|{Ls}")
    Kc = hkdf(ss, f"geo:cube|{z}|{Lc}")
    Kmsg = hkdf(bytes(x ^ y for x, y in zip(Ks, Kc)), "geo:msg")
    mask_seed = hashlib.sha256(Kmsg).digest()
    mask = (mask_seed * ((len(pt) // len(mask_seed)) + 2))[: len(pt)]
    ct_spec = bytes(a ^ b for a, b in zip(pt, mask))
    attest = {
        "h": h,
        "z": z,
        "L_s": Ls,
        "L_c": Lc,
        "P": round(P, 6),
        "margin": round(margin, 6),
        "ts": int(time.time()),
        "path": path,
    }
    sig = dsa_sign(
        base64.b64decode(sk_dsa_b64),
        hashlib.sha256(json.dumps(attest, sort_keys=True).encode() + ct_spec).digest(),
    )
    return {
        "ct_k": base64.b64encode(ct_k).decode(),
        "ct_spec": base64.b64encode(ct_spec).decode(),
        "attest": attest,
        "sig": base64.b64encode(sig).decode(),
    }


def geoseal_decrypt(
    env: dict,
    context: List[float],
    sk_kem_b64: str,
    pk_dsa_b64: str,
) -> Tuple[bool, bytes | None]:
    ct_k = base64.b64decode(env["ct_k"]) if isinstance(env["ct_k"], str) else env["ct_k"]
    ct_spec = base64.b64decode(env["ct_spec"]) if isinstance(env["ct_spec"], str) else env["ct_spec"]
    attest = env["attest"]
    sig = base64.b64decode(env["sig"]) if isinstance(env["sig"], str) else env["sig"]
    if not dsa_verify(
        base64.b64decode(pk_dsa_b64),
        hashlib.sha256(json.dumps(attest, sort_keys=True).encode() + ct_spec).digest(),
        sig,
    ):
        return False, None
    ss = kyber_decaps(base64.b64decode(sk_kem_b64), ct_k)
    Ks = hkdf(ss, f"geo:sphere|{attest['h']}|{attest['L_s']}")
    Kc = hkdf(ss, f"geo:cube|{attest['z']}|{attest['L_c']}")
    Kmsg = hkdf(bytes(x ^ y for x, y in zip(Ks, Kc)), "geo:msg")
    mask_seed = hashlib.sha256(Kmsg).digest()
    mask = (mask_seed * ((len(ct_spec) // len(mask_seed)) + 2))[: len(ct_spec)]
    pt = bytes(a ^ b for a, b in zip(ct_spec, mask))
    return True, pt


# ---------- AetherLex Seed — Sacred Tongue mnemonic for PQC key material ----------

# Global index: tongue_order * 256 + byte_index → [0, 1535]
_TONGUE_ORDER = {"KO": 0, "AV": 1, "RU": 2, "CA": 3, "UM": 4, "DR": 5}
BITS_PER_TOKEN = math.log2(6 * 256)  # ~10.585 bits per token
SEED_DOMAIN = b"AETHERLEX-SEED-v1"
SEED_SEPARATOR = b"\x1f"


def token_to_global_index(tongue: str, byte_val: int) -> int:
    """Map a (tongue, byte) pair to global index [0, 1535]."""
    return _TONGUE_ORDER[tongue] * 256 + byte_val


def global_index_to_token(lex: Lexicons, idx: int) -> Tuple[str, str]:
    """Map global index [0, 1535] to (tongue_code, token_string)."""
    tg_idx = idx // 256
    byte_val = idx % 256
    tg = TONGUES[tg_idx]
    return tg, lex.token_of(tg, byte_val)


def parse_aetherlex_phrase(lex: Lexicons, phrase: str) -> List[Tuple[str, int]]:
    """Parse a space-separated phrase of Sacred Tongue tokens.

    Returns list of (tongue_code, global_index) pairs.
    Identifies the tongue by checking which tongue can decode each token.
    """
    results: List[Tuple[str, int]] = []
    for raw_tok in phrase.strip().split():
        raw_tok = raw_tok.strip()
        if not raw_tok:
            continue
        found = False
        for tg in TONGUES:
            try:
                byte_val = lex.byte_of(tg, raw_tok)
                results.append((tg, token_to_global_index(tg, byte_val)))
                found = True
                break
            except KeyError:
                continue
        if not found:
            raise ValueError(f"token {raw_tok!r} not found in any tongue")
    return results


def encode_token_indices(indices: List[int], bits: int = 11) -> bytes:
    """Pack global indices as 11-bit values into a byte string."""
    total_bits = len(indices) * bits
    total_bytes = (total_bits + 7) // 8
    buf = bytearray(total_bytes)
    bit_pos = 0
    for idx in indices:
        for b in range(bits):
            if idx & (1 << (bits - 1 - b)):
                byte_off = (bit_pos + b) // 8
                bit_off = 7 - ((bit_pos + b) % 8)
                buf[byte_off] |= 1 << bit_off
        bit_pos += bits
    return bytes(buf)


def derive_seed(
    lex: Lexicons,
    phrase: str,
    output_len: int = 64,
    weight_system: str = "lws",
    supplemental: bytes = b"",
) -> bytes:
    """Derive PQC key material from a Sacred Tongue mnemonic phrase.

    1. Parse phrase → token indices
    2. Encode as 11-bit packed bitstring
    3. Compute LWS weight header (float32)
    4. Domain separation: SEED_DOMAIN || 0x1F || weight || 0x1F || tokenBits || [supplemental]
    5. SHA-512 hash
    6. Truncate to output_len (32 or 64 bytes)
    """
    parsed = parse_aetherlex_phrase(lex, phrase)
    if len(parsed) < 6:
        raise ValueError("AetherLex phrase must have at least 6 tokens")

    indices = [gi for _, gi in parsed]
    token_bits = encode_token_indices(indices)

    # Weight header: sum of weights for all tokens
    weights = CrossTokenizer.WEIGHT_LWS if weight_system == "lws" else CrossTokenizer.WEIGHT_PHDM
    total_weight = sum(weights[tg] for tg, _ in parsed)
    weight_bytes = struct.pack(">f", total_weight)

    # Domain-separated input
    preimage = SEED_DOMAIN + SEED_SEPARATOR + weight_bytes + SEED_SEPARATOR + token_bits
    if supplemental:
        preimage += SEED_SEPARATOR + supplemental

    digest = hashlib.sha512(preimage).digest()
    return digest[:output_len]


def generate_random_phrase(lex: Lexicons, length: int = 13) -> str:
    """Generate a CSPRNG-backed random AetherLex mnemonic phrase."""
    tokens: List[str] = []
    for _ in range(length):
        global_idx = int.from_bytes(os.urandom(2), "big") % (6 * 256)
        _, tok = global_index_to_token(lex, global_idx)
        tokens.append(tok)
    return " ".join(tokens)


def split_for_mlkem(seed: bytes) -> Tuple[bytes, bytes]:
    """Split a 64-byte seed into ML-KEM-768 (d, z) pair."""
    if len(seed) < 64:
        raise ValueError("need 64-byte seed for ML-KEM split")
    return seed[:32], seed[32:64]


def split_for_mldsa(seed: bytes) -> bytes:
    """Extract ML-DSA-65 xi (32 bytes) from seed."""
    if len(seed) < 32:
        raise ValueError("need ≥32-byte seed for ML-DSA split")
    return seed[:32]


# ---------- Semantic / atomic trace helpers ----------


def _infer_code_lane(tokens: List[str]) -> str:
    joined = " ".join(tok.lower() for tok in tokens)
    if any(marker in joined for marker in ("def ", "class ", "return", "import ")):
        return "python"
    if any(marker in joined for marker in ("function ", "const ", "let ", "=>")):
        return "javascript"
    if any(marker in joined for marker in ("select ", "from ", "where ", "join ")):
        return "sql"
    return "prose"


def _atomic_trace_summary(tokens: List[str], language: str | None, context_class: str | None) -> dict:
    from python.scbe.history_reducer import reduce_atomic_history

    inferred_lane = _infer_code_lane(tokens)
    _history_state, step = reduce_atomic_history(
        tokens,
        language=language,
        context_class=context_class,
    )
    semantic_hist: Dict[str, int] = {}
    resilience: List[float] = []
    adaptivity: List[float] = []
    trust_baselines: List[float] = []
    band_flags: List[int] = []
    witness_states: List[int] = []
    tau_mass: List[float] = []

    for state in step.states:
        semantic_hist[state.semantic_class] = semantic_hist.get(state.semantic_class, 0) + 1
        resilience.append(float(state.resilience))
        adaptivity.append(float(state.adaptivity))
        trust_baselines.append(float(state.trust_baseline))
        band_flags.append(int(state.band_flag))
        witness_states.append(int(state.witness_state))
        tau_mass.append(float(sum(abs(int(v)) for v in state.tau.as_tuple())))

    return {
        "token_count": len(tokens),
        "inferred_lane": inferred_lane,
        "semantic_histogram": semantic_hist,
        "mean_resilience": round(statistics.fmean(resilience), 6) if resilience else 0.0,
        "mean_adaptivity": round(statistics.fmean(adaptivity), 6) if adaptivity else 0.0,
        "mean_trust_baseline": round(statistics.fmean(trust_baselines), 6) if trust_baselines else 0.0,
        "mean_tau_mass": round(statistics.fmean(tau_mass), 6) if tau_mass else 0.0,
        "band_flag_histogram": {str(flag): band_flags.count(flag) for flag in sorted(set(band_flags))},
        "witness_histogram": {str(flag): witness_states.count(flag) for flag in sorted(set(witness_states))},
        "fusion": {
            "tau_hat": dict(step.fusion.tau_hat),
            "reconstruction_votes": {str(k): round(float(v), 6) for k, v in step.fusion.reconstruction_votes.items()},
            "signed_edge_tension": round(float(step.fusion.signed_edge_tension), 6),
            "coherence_penalty": round(float(step.fusion.coherence_penalty), 6),
            "valence_pressure": round(float(step.fusion.valence_pressure), 6),
        },
        "rhombic": {
            "score": round(float(step.rhombic_score), 6),
            "energy": round(float(step.rhombic_energy), 6),
        },
        "trust": {
            "trust_level": round(float(step.trust_level), 6),
            "trust_factor": round(float(step.trust_factor), 6),
            "betrayal_delta": round(float(step.betrayal_delta), 6),
            "negative_ratio": round(float(step.negative_ratio), 6),
        },
        "lane_alignment": step.lane_alignment,
        "drift": {
            "norm": round(float(step.drift_norm), 6),
            "components": [
                {
                    "token": row["token"],
                    "negative_state": bool(row["negative_state"]),
                    "dual_state": int(row["dual_state"]),
                    "drift_scale": round(float(row["drift_scale"]), 6),
                    "drift_norm": round(float(row["drift_norm"]), 6),
                }
                for row in step.drift_components
            ],
        },
        "checkpoint": step.checkpoint,
    }


_ATOMIC_WORD_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_'\-]*")
_ATOMIC_MATH_TOKEN_RE = re.compile(r"(?:\d+\.\d+|\d+|[A-Za-z_]+|==|!=|<=|>=|->|=>|[-+*/^=(){}\[\],.:;<>%])")
_ATOMIC_CHEM_TOKEN_RE = re.compile(r"(?:[A-Z][a-z]?\d*|\d+\.\d+|\d+|->|=>|\+|=|\(|\)|\[|\]|,|[a-zA-Z_]+)")
_ATOMIC_INT_TOKEN_RE = re.compile(r"[-+]?\d+")


def _decode_payload_text(payload: bytes) -> str:
    return payload.decode("utf-8", errors="replace")


def _parse_custom_atomic_tokens(raw: str | None) -> List[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item)]
    except json.JSONDecodeError:
        pass
    if "," in raw:
        return [part.strip() for part in raw.split(",") if part.strip()]
    return [part for part in raw.split() if part]


def _variant_tokens_for_payload(
    payload: bytes,
    *,
    text: str | None,
    variant: str,
    custom_tokens: List[str] | None,
) -> List[str]:
    custom_tokens = custom_tokens or []
    if variant == "bytes":
        return [f"0x{b:02x}" for b in payload]
    if variant == "custom":
        return list(custom_tokens)

    source = text if text is not None else _decode_payload_text(payload)
    if variant == "words":
        return _ATOMIC_WORD_TOKEN_RE.findall(source)
    if variant == "math":
        return _ATOMIC_MATH_TOKEN_RE.findall(source)
    if variant == "chemistry":
        return _ATOMIC_CHEM_TOKEN_RE.findall(source)
    if variant == "integers":
        return _ATOMIC_INT_TOKEN_RE.findall(source)
    raise ValueError(f"Unsupported atomic variant: {variant}")


def _bijective_atomic_trace(
    tokens: List[str],
    *,
    variant: str,
    language: str | None,
    context_class: str | None,
    top_k: int,
) -> dict:
    from python.scbe.atomic_tokenization import map_token_to_atomic_state

    semantic_hist: Dict[str, int] = {}
    element_hist: Dict[str, int] = {}
    band_hist: Dict[str, int] = {}
    witness_hist: Dict[str, int] = {}
    dual_hist: Dict[str, int] = {}
    resilience: List[float] = []
    adaptivity: List[float] = []
    trust_baselines: List[float] = []
    tau_mass: List[float] = []
    negative_count = 0
    states_preview: List[dict] = []

    for idx, token in enumerate(tokens):
        state = map_token_to_atomic_state(
            token,
            language=language,
            context_class=context_class,
        )
        semantic_hist[state.semantic_class] = semantic_hist.get(state.semantic_class, 0) + 1
        element_hist[state.element.symbol] = element_hist.get(state.element.symbol, 0) + 1
        band_hist[str(state.band_flag)] = band_hist.get(str(state.band_flag), 0) + 1
        witness_hist[str(state.witness_state)] = witness_hist.get(str(state.witness_state), 0) + 1
        dual_key = "none" if state.dual_state is None else str(state.dual_state)
        dual_hist[dual_key] = dual_hist.get(dual_key, 0) + 1
        resilience.append(float(state.resilience))
        adaptivity.append(float(state.adaptivity))
        trust_baselines.append(float(state.trust_baseline))
        tau_mass.append(float(sum(abs(int(v)) for v in state.tau.as_tuple())))
        negative_count += int(bool(state.negative_state))
        if idx < top_k:
            states_preview.append(
                {
                    "token": token,
                    "semantic_class": state.semantic_class,
                    "element": state.element.symbol,
                    "tau": state.tau.as_dict(),
                    "negative_state": bool(state.negative_state),
                    "dual_state": state.dual_state,
                    "band_flag": int(state.band_flag),
                    "witness_state": int(state.witness_state),
                    "resilience": round(float(state.resilience), 6),
                    "adaptivity": round(float(state.adaptivity), 6),
                    "trust_baseline": round(float(state.trust_baseline), 6),
                }
            )

    count = len(tokens)
    return {
        "variant": variant,
        "token_count": count,
        "tokens_preview": tokens[: min(top_k, count)],
        "states_preview": states_preview,
        "semantic_histogram": semantic_hist,
        "element_histogram": element_hist,
        "band_flag_histogram": band_hist,
        "witness_histogram": witness_hist,
        "dual_state_histogram": dual_hist,
        "negative_ratio": round(float(negative_count / count), 6) if count else 0.0,
        "mean_resilience": round(statistics.fmean(resilience), 6) if resilience else 0.0,
        "mean_adaptivity": round(statistics.fmean(adaptivity), 6) if adaptivity else 0.0,
        "mean_trust_baseline": round(statistics.fmean(trust_baselines), 6) if trust_baselines else 0.0,
        "mean_tau_mass": round(statistics.fmean(tau_mass), 6) if tau_mass else 0.0,
    }


def _build_bijective_atomic_variants(
    payload: bytes,
    *,
    text: str | None,
    variants: List[str],
    custom_tokens: List[str] | None,
    language: str | None,
    context_class: str | None,
    top_k: int,
) -> dict:
    built: Dict[str, dict] = {}
    for variant in variants:
        tokens = _variant_tokens_for_payload(
            payload,
            text=text,
            variant=variant,
            custom_tokens=custom_tokens,
        )
        built[variant] = _bijective_atomic_trace(
            tokens,
            variant=variant,
            language=language,
            context_class=context_class,
            top_k=top_k,
        )
    return {"variants": built}


def _sacred_transport_trace(
    payload: bytes,
    lex: Lexicons,
    language: str | None,
    context_class: str | None,
    *,
    top_k: int = 16,
    atomic_variants: List[str] | None = None,
    atomic_custom_tokens: List[str] | None = None,
) -> dict:
    from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER

    tok = TongueTokenizer(lex)
    per_tongue: Dict[str, dict] = {}
    harmonic_values: Dict[str, float] = {}
    for tongue in TONGUES:
        tokens = tok.encode_bytes(tongue, payload)
        fingerprint = float(SACRED_TONGUE_TOKENIZER.compute_harmonic_fingerprint(tongue.lower(), list(tokens)))
        harmonic_values[tongue] = fingerprint
        per_tongue[tongue] = {
            "token_count": len(tokens),
            "tokens_preview": tokens[: min(top_k, len(tokens))],
            "harmonic_fingerprint": round(fingerprint, 6),
            "atomic_summary": _atomic_trace_summary(tokens, language=language, context_class=context_class),
        }
    harmonic_spread = max(harmonic_values.values()) - min(harmonic_values.values()) if harmonic_values else 0.0
    variants = atomic_variants or ["words"]
    return {
        "payload_bytes": len(payload),
        "transport_layers": per_tongue,
        "harmonic_spread": round(float(harmonic_spread), 6),
        "bijective_atomic": _build_bijective_atomic_variants(
            payload,
            text=_decode_payload_text(payload),
            variants=variants,
            custom_tokens=atomic_custom_tokens,
            language=language,
            context_class=context_class,
            top_k=top_k,
        ),
    }


def _load_task_ball_database() -> dict[str, dict]:
    if not _TASK_BALL_TARGET_REPORT.exists():
        return {}
    report = json.loads(_TASK_BALL_TARGET_REPORT.read_text(encoding="utf-8"))
    out: Dict[str, dict] = {}
    for row in report.get("ranked_targets", []):
        task_id = row.get("task_id")
        if task_id and task_id not in out:
            out[task_id] = row
    return out


def _load_arc_task_from_args(task_id: str | None, task_json: str | None):
    from src.neurogolf.arc_io import load_arc_task

    if bool(task_id) == bool(task_json):
        raise ValueError("Provide exactly one of --task-id or --task-json")
    if task_id:
        task_path = _ARC_EVAL_DIR / f"{task_id}.json"
        if not task_path.exists():
            raise FileNotFoundError(f"ARC task not found: {task_path}")
        return load_arc_task(task_path)
    task_path = Path(task_json)
    if not task_path.exists():
        raise FileNotFoundError(f"ARC task json not found: {task_path}")
    return load_arc_task(task_path)


def _arc_task_trace(
    task_id: str | None,
    task_json: str | None,
    top_k: int,
    *,
    atomic_variants: List[str] | None = None,
    atomic_custom_tokens: List[str] | None = None,
) -> dict:
    from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER
    from src.neurogolf.token_braid import _ALL_TONGUES, null_space_report, task_packet, task_tokens

    task = _load_arc_task_from_args(task_id, task_json)
    packet = task_packet(task)
    target_db = _load_task_ball_database()
    corridor = target_db.get(task.task_id, {})
    harmonic: Dict[str, float] = {}
    layers: Dict[str, dict] = {}

    for tongue in _ALL_TONGUES:
        tokens = list(task_tokens(task, tongue))
        fp = float(SACRED_TONGUE_TOKENIZER.compute_harmonic_fingerprint(tongue.lower(), tokens))
        harmonic[tongue] = fp
        layers[tongue] = {
            "token_count": len(tokens),
            "tokens_preview": tokens[: min(top_k, len(tokens))],
            "harmonic_fingerprint": round(fp, 6),
            "atomic_summary": _atomic_trace_summary(tokens, language=None, context_class="arc_task"),
        }

    harmonic_spread = max(harmonic.values()) - min(harmonic.values()) if harmonic else 0.0
    variants = atomic_variants or ["words"]
    return {
        "task_id": task.task_id,
        "packet_len": len(packet),
        "packet_b64": base64.b64encode(packet).decode("ascii"),
        "harmonic_spread": round(float(harmonic_spread), 6),
        "transport_layers": layers,
        "bijective_atomic": _build_bijective_atomic_variants(
            packet,
            text=None,
            variants=variants,
            custom_tokens=atomic_custom_tokens,
            language=None,
            context_class="arc_task",
            top_k=top_k,
        ),
        "nullspace": null_space_report(task),
        "task_ball_corridor": (
            {
                "closest_solved_task": corridor.get("closest_solved_task"),
                "closest_solved_family": corridor.get("closest_solved_family"),
                "closest_distance": corridor.get("closest_distance"),
                "projection": corridor.get("projection"),
                "dominant_void": corridor.get("dominant_void"),
                "stripe_signature": corridor.get("stripe_signature"),
            }
            if corridor
            else {}
        ),
    }


def _read_trace_payload(args) -> bytes:
    if args.text is not None:
        return args.text.encode("utf-8")
    if args.infile:
        return Path(args.infile).read_bytes()
    return sys.stdin.buffer.read()


def cmd_geoseal_trace(args):
    lex = load_lexicons(args.lexicons)
    atomic_variants = getattr(args, "atomic_variant", None) or ["words"]
    atomic_custom_tokens = _parse_custom_atomic_tokens(getattr(args, "atomic_custom_tokens", None))
    task_id = getattr(args, "task_id", None)
    task_json = getattr(args, "task_json", None)
    if task_id or task_json:
        out = {
            "mode": "arc_task",
            "trace": _arc_task_trace(
                task_id,
                task_json,
                max(1, int(args.top_k)),
                atomic_variants=atomic_variants,
                atomic_custom_tokens=atomic_custom_tokens,
            ),
        }
    else:
        payload = _read_trace_payload(args)
        out = {
            "mode": "payload",
            "trace": _sacred_transport_trace(
                payload,
                lex,
                args.language,
                args.context_class,
                top_k=max(1, int(args.top_k)),
                atomic_variants=atomic_variants,
                atomic_custom_tokens=atomic_custom_tokens,
            ),
        }
    rendered = json.dumps(out, indent=2, ensure_ascii=False)
    if args.outfile:
        Path(args.outfile).write_text(rendered, encoding="utf-8")
    else:
        print(rendered)


# ---------- CLI ----------


def load_lexicons(path: str | None) -> Lexicons:
    if not path:
        return Lexicons()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Lexicons(data)


def cmd_encode(args):
    lex = load_lexicons(args.lexicons)
    tok = TongueTokenizer(lex)
    if not args.infile:
        data = sys.stdin.buffer.read()
    else:
        with open(args.infile, "rb") as f:
            data = f.read()
    tokens = tok.encode_bytes(args.tongue, data)
    out = (" ".join(tokens) + "\n").encode()
    if not args.outfile:
        sys.stdout.buffer.write(out)
    else:
        with open(args.outfile, "wb") as f:
            f.write(out)


def cmd_decode(args):
    lex = load_lexicons(args.lexicons)
    tok = TongueTokenizer(lex)
    if not args.infile:
        text = sys.stdin.read()
    else:
        with open(args.infile, "r", encoding="utf-8") as f:
            text = f.read()
    tokens = tok.normalize_token_stream(text)
    data = tok.decode_tokens(args.tongue, tokens)
    if not args.outfile:
        sys.stdout.buffer.write(data)
    else:
        with open(args.outfile, "wb") as f:
            f.write(data)


def cmd_xlate(args):
    lex = load_lexicons(args.lexicons)
    tok = TongueTokenizer(lex)
    xt = CrossTokenizer(tok)
    if not args.infile:
        text = sys.stdin.read()
    else:
        with open(args.infile, "r", encoding="utf-8") as f:
            text = f.read()
    out_tokens, attest = xt.retokenize(
        args.src,
        args.dst,
        text,
        mode=args.mode,
        attest_key=(base64.b64decode(args.attest_key) if args.attest_key else None),
    )
    bundle = {
        "tokens": " ".join(out_tokens),
        "attestation": dataclasses.asdict(attest),
    }
    s = json.dumps(bundle, ensure_ascii=False)
    if not args.outfile:
        print(s)
    else:
        with open(args.outfile, "w", encoding="utf-8") as f:
            f.write(s)


def cmd_blend(args):
    lex = load_lexicons(args.lexicons)
    tok = TongueTokenizer(lex)
    xt = CrossTokenizer(tok)
    if not args.infile:
        data = sys.stdin.buffer.read()
    else:
        with open(args.infile, "rb") as f:
            data = f.read()
    pattern = []
    for seg in args.pattern.split(","):
        name, count = seg.split(":") if ":" in seg else (seg, "1")
        for _ in range(int(count)):
            pattern.append(name)
    pairs = xt.blend(pattern, data)
    s = json.dumps({"pattern": pattern, "pairs": pairs}, ensure_ascii=False)
    if not args.outfile:
        print(s)
    else:
        with open(args.outfile, "w", encoding="utf-8") as f:
            f.write(s)


def cmd_unblend(args):
    lex = load_lexicons(args.lexicons)
    tok = TongueTokenizer(lex)
    xt = CrossTokenizer(tok)
    if not args.infile:
        js = json.load(sys.stdin)
    else:
        with open(args.infile, "r", encoding="utf-8") as f:
            js = json.load(f)
    pattern = js["pattern"]
    pairs = [(tg, t) for tg, t in js["pairs"]]
    data = xt.unblend(pattern, pairs)
    if not args.outfile:
        sys.stdout.buffer.write(data)
    else:
        with open(args.outfile, "wb") as f:
            f.write(data)


def cmd_gencore(args):
    pt_b64 = sys.stdin.read().strip() if args.plaintext_b64 is None else args.plaintext_b64
    ctx = json.loads(args.context)
    env = geoseal_encrypt(pt_b64, ctx, args.kem_key, args.dsa_key)
    print(json.dumps(env))


def cmd_gendec(args):
    if not args.env:
        env = json.load(sys.stdin)
    else:
        with open(args.env, "r") as f:
            env = json.load(f)
    ctx = json.loads(args.context)
    ok, pt = geoseal_decrypt(env, ctx, args.kem_key, args.dsa_pk)
    if not ok:
        sys.exit(1)
    sys.stdout.buffer.write(pt)


def cmd_egg_create(args):
    integrator_module = importlib.import_module(f"{__package__}.sacred_egg_integrator")
    SacredEggIntegrator = integrator_module.SacredEggIntegrator

    lex = Lexicons()
    tok = TongueTokenizer(lex)
    xt = CrossTokenizer(tok)
    integrator = SacredEggIntegrator(xt)

    payload = base64.b64decode(args.payload_b64)
    ctx = json.loads(args.context)
    hatch_cond = json.loads(args.hatch_condition)

    egg = integrator.create_egg(
        payload,
        args.primary_tongue,
        args.glyph,
        hatch_cond,
        ctx,
        args.kem_key,
        args.dsa_key,
    )
    out = integrator.to_json(egg)
    if not args.outfile:
        print(out)
    else:
        with open(args.outfile, "w", encoding="utf-8") as fh:
            fh.write(out)


def cmd_egg_hatch(args):
    integrator_module = importlib.import_module(f"{__package__}.sacred_egg_integrator")
    SacredEggIntegrator = integrator_module.SacredEggIntegrator

    lex = load_lexicons(getattr(args, "lexicons", None))
    tok = TongueTokenizer(lex)
    xt = CrossTokenizer(tok)
    integrator = SacredEggIntegrator(xt)

    with open(args.egg_json, "r", encoding="utf-8") as fh:
        egg_data = fh.read()
    egg = integrator.from_json(egg_data)
    ctx = json.loads(args.context)
    additional = json.loads(args.additional_tongues)
    history = json.loads(args.path_history)

    result = integrator.hatch_egg(
        egg,
        ctx,
        args.agent_tongue,
        args.kem_key,
        args.dsa_pk,
        ritual_mode=args.ritual_mode,
        additional_tongues=additional or None,
        path_history=history or None,
    )
    out = {
        "success": result.success,
        "reason": result.reason,
        "tokens": result.tokens,
        "attestation": result.attestation,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    if not result.success:
        sys.exit(1)


def cmd_egg_paint(args):
    integrator_module = importlib.import_module(f"{__package__}.sacred_egg_integrator")
    SacredEggIntegrator = integrator_module.SacredEggIntegrator

    lex = Lexicons()
    tok = TongueTokenizer(lex)
    xt = CrossTokenizer(tok)
    integrator = SacredEggIntegrator(xt)

    with open(args.egg_json, "r", encoding="utf-8") as fh:
        egg_data = fh.read()
    egg = integrator.from_json(egg_data)

    hatch_cond = json.loads(args.hatch_condition) if args.hatch_condition else None
    painted = integrator.paint_egg(egg, glyph=args.glyph, hatch_condition=hatch_cond)

    out = integrator.to_json(painted)
    if not args.outfile:
        print(out)
    else:
        with open(args.outfile, "w", encoding="utf-8") as fh:
            fh.write(out)


def cmd_seed(args):
    lex = load_lexicons(args.lexicons)
    if args.phrase:
        phrase = args.phrase
    else:
        phrase = generate_random_phrase(lex, args.length)
    seed = derive_seed(
        lex,
        phrase,
        output_len=args.bytes,
        weight_system=args.weights,
    )
    result = {
        "phrase": phrase,
        "seed_hex": seed.hex(),
        "seed_b64": base64.b64encode(seed).decode(),
        "length_bytes": len(seed),
        "entropy_bits": round(len(phrase.split()) * BITS_PER_TOKEN, 2),
        "weight_system": args.weights,
    }
    if args.split == "mlkem":
        d, z = split_for_mlkem(seed)
        result["mlkem_d"] = d.hex()
        result["mlkem_z"] = z.hex()
    elif args.split == "mldsa":
        xi = split_for_mldsa(seed)
        result["mldsa_xi"] = xi.hex()
    print(json.dumps(result, indent=2))


# ---------- Selftest ----------


def selftest() -> int:
    lex = Lexicons()
    tok = TongueTokenizer(lex)
    xt = CrossTokenizer(tok)
    payload = os.urandom(1024)

    # ── Canon verification ──
    # Verify canonical tokens match expected format
    assert lex.token_of("KO", 0) == "kor'ah", "KO byte 0 should be kor'ah"
    assert lex.token_of("AV", 0) == "saina'a", "AV byte 0 should be saina'a"
    assert lex.token_of("RU", 0) == "khar'ak", "RU byte 0 should be khar'ak"
    assert lex.token_of("CA", 0) == "bip'a", "CA byte 0 should be bip'a"
    assert lex.token_of("UM", 0) == "veil'a", "UM byte 0 should be veil'a"
    assert lex.token_of("DR", 0) == "anvil'a", "DR byte 0 should be anvil'a"
    # Spot-check last token (byte 255 = prefix[15]'suffix[15])
    assert lex.token_of("KO", 255) == "zha'mar"
    assert lex.token_of("DR", 255) == "ember'on"

    # ── Roundtrip per tongue ──
    for tg in TONGUES:
        toks = tok.encode_bytes(tg, payload)
        dec = tok.decode_tokens(tg, toks)
        assert dec == payload, f"{tg} roundtrip failed"
        assert len(set(tok.encode_bytes(tg, bytes(range(256))))) == 256

    # ── Decoding robustness: case + smart quotes + punctuation ──
    for tg in TONGUES:
        toks = tok.encode_bytes(tg, payload)
        noisy = [
            (
                (t.upper().replace("'", "\u2019") + ("," if i % 7 == 0 else ""))
                if i % 2 == 0
                else (t.replace("'", "\u02bc") + (";" if i % 11 == 0 else ""))
            )
            for i, t in enumerate(toks)
        ]
        assert tok.decode_tokens(tg, noisy) == payload
        assert tok.decode_tokens(tg, tok.normalize_token_stream(" ".join(noisy))) == payload

    # ── Canonical-collision guard ──
    try:
        base = Lexicons._canon_lexicons()
        base["KO"]["0"] = "X"
        base["KO"]["1"] = "x"  # canonical collision
        Lexicons(base)
        raise AssertionError("expected canonical collision to be rejected")
    except ValueError:
        pass

    # ── Cross-retokenize (byte + semantic) ──
    for s in TONGUES:
        for d in TONGUES:
            ttext = " ".join(tok.encode_bytes(s, payload))
            out_tokens, attest = xt.retokenize(s, d, ttext, attest_key=b"k")
            back = tok.decode_tokens(d, out_tokens)
            assert back == payload
            assert isinstance(attest.hmac_attest, str)
            out_tokens2, _ = xt.retokenize(s, d, ttext, mode="semantic", attest_key=b"k")
            assert tok.decode_tokens(d, out_tokens2) == payload

    # ── Blend/unblend ──
    pattern = ["KO", "KO", "AV", "RU", "CA", "UM", "DR"]
    pairs = xt.blend(pattern, payload)
    un = xt.unblend(pattern, pairs)
    assert un == payload

    # ── GeoSeal ──
    ctx = [0.2, -0.3, 0.7, 1.0, -2.0, 0.5, 3.1, -9.9, 0.0]
    pt = b"hello aethermoore"
    pt_b64 = base64.b64encode(pt).decode()
    kem = base64.b64encode(b"kem-key-32bytes-demo____").decode()
    dsa = base64.b64encode(b"dsa-key-32bytes-demo____").decode()
    env = geoseal_encrypt(pt_b64, ctx, kem, dsa)
    ok, decpt = geoseal_decrypt(env, ctx, kem, dsa)
    assert ok and decpt == pt

    # ── Negative: corrupted token should fail ──
    bad = tok.encode_bytes("KO", b"\x00\x01")
    bad[1] = bad[1] + "x"
    try:
        tok.decode_tokens("KO", bad)
        raise AssertionError("expected KeyError for bad token")
    except KeyError:
        pass

    # ── AetherLex Seed ──
    # Global index space: [0, 1535]
    assert token_to_global_index("KO", 0) == 0
    assert token_to_global_index("DR", 255) == 1535
    tg, tok_str = global_index_to_token(lex, 0)
    assert tg == "KO" and tok_str == "kor'ah"
    tg, tok_str = global_index_to_token(lex, 1535)
    assert tg == "DR" and tok_str == "ember'on"

    # Phrase generation and parsing roundtrip
    phrase = generate_random_phrase(lex, 13)
    parsed = parse_aetherlex_phrase(lex, phrase)
    assert len(parsed) == 13
    for tg_code, gi in parsed:
        assert tg_code in TONGUES
        assert 0 <= gi <= 1535

    # Seed derivation: deterministic
    fixed_phrase = "kor'ah saina'a khar'ak bip'a veil'a anvil'a"
    seed1 = derive_seed(lex, fixed_phrase, output_len=64)
    seed2 = derive_seed(lex, fixed_phrase, output_len=64)
    assert seed1 == seed2, "seed derivation must be deterministic"
    assert len(seed1) == 64

    # Different weight systems give different seeds
    seed_lws = derive_seed(lex, fixed_phrase, weight_system="lws")
    seed_phdm = derive_seed(lex, fixed_phrase, weight_system="phdm")
    assert seed_lws != seed_phdm, "LWS and PHDM should produce different seeds"

    # ML-KEM split
    d, z = split_for_mlkem(seed1)
    assert len(d) == 32 and len(z) == 32
    assert d + z == seed1

    # ML-DSA split
    xi = split_for_mldsa(seed1)
    assert len(xi) == 32 and xi == seed1[:32]

    # Short phrase should fail
    try:
        derive_seed(lex, "kor'ah saina'a khar'ak")
        raise AssertionError("expected ValueError for short phrase")
    except ValueError:
        pass

    # Unknown token should fail
    try:
        parse_aetherlex_phrase(lex, "kor'ah NOTAWORD saina'a")
        raise AssertionError("expected ValueError for unknown token")
    except ValueError:
        pass

    print("selftest ok")
    return 0


# ---------- Entry ----------


def build_cli():
    p = argparse.ArgumentParser(
        prog="aethermoore",
        description="Aethermoore Suite \u2013 GeoSeal + SCBE + Six-Tongue Toolkit",
    )
    sub = p.add_subparsers(dest="cmd")

    pe = sub.add_parser("encode")
    pe.add_argument("--tongue", required=True, choices=TONGUES)
    pe.add_argument("--lexicons")
    pe.add_argument("--in", dest="infile")
    pe.add_argument("--out", dest="outfile")
    pe.set_defaults(func=cmd_encode)

    pd = sub.add_parser("decode")
    pd.add_argument("--tongue", required=True, choices=TONGUES)
    pd.add_argument("--lexicons")
    pd.add_argument("--in", dest="infile")
    pd.add_argument("--out", dest="outfile")
    pd.set_defaults(func=cmd_decode)

    px = sub.add_parser("xlate")
    px.add_argument("--src", required=True, choices=TONGUES)
    px.add_argument("--dst", required=True, choices=TONGUES)
    px.add_argument("--mode", default="byte", choices=["byte", "semantic"])
    px.add_argument("--lexicons")
    px.add_argument("--attest-key", dest="attest_key")
    px.add_argument("--in", dest="infile")
    px.add_argument("--out", dest="outfile")
    px.set_defaults(func=cmd_xlate)

    pb = sub.add_parser("blend")
    pb.add_argument("--pattern", required=True, help="e.g. KO:2,AV:1,DR:1")
    pb.add_argument("--lexicons")
    pb.add_argument("--in", dest="infile")
    pb.add_argument("--out", dest="outfile")
    pb.set_defaults(func=cmd_blend)

    pub = sub.add_parser("unblend")
    pub.add_argument("--lexicons")
    pub.add_argument("--in", dest="infile")
    pub.add_argument("--out", dest="outfile")
    pub.set_defaults(func=cmd_unblend)

    ge = sub.add_parser("geoseal-encrypt")
    ge.add_argument("--context", required=True)
    ge.add_argument("--kem-key", required=True)
    ge.add_argument("--dsa-key", required=True)
    ge.add_argument("--plaintext-b64")
    ge.set_defaults(func=cmd_gencore)

    gt = sub.add_parser(
        "geoseal-trace",
        help="Trace Sacred Tongues transport layers, atomic summaries, and ARC solve corridors",
    )
    gt.add_argument("--text", help="UTF-8 text payload to trace")
    gt.add_argument("--in", dest="infile", help="Binary payload file to trace")
    gt.add_argument("--out", dest="outfile", help="Write JSON trace to file instead of stdout")
    gt.add_argument("--language", help="Optional language code for atomic semantic overrides")
    gt.add_argument("--context-class", default="operator", help="Atomic tokenizer context class")
    gt.add_argument("--task-id", help="ARC evaluation task id to trace against solved corridors")
    gt.add_argument("--task-json", help="Path to an ARC task JSON file")
    gt.add_argument("--top-k", type=int, default=8, help="How many preview tokens to include per layer")
    gt.add_argument(
        "--atomic-variant",
        action="append",
        choices=["words", "math", "chemistry", "integers", "bytes", "custom"],
        help="Direct bijective atomic tokenizer variant to include; repeat to trace multiple variants",
    )
    gt.add_argument(
        "--atomic-custom-tokens",
        help="Comma-separated custom tokens for the custom atomic variant",
    )
    gt.add_argument("--lexicons")
    gt.set_defaults(func=cmd_geoseal_trace)

    gd = sub.add_parser("geoseal-decrypt")
    gd.add_argument("--context", required=True)
    gd.add_argument("--kem-key", required=True)
    gd.add_argument("--dsa-pk", required=True)
    gd.add_argument("--env")
    gd.set_defaults(func=cmd_gendec)

    # ── Sacred Egg commands ──

    ec = sub.add_parser("egg-create", help="Create a Sacred Egg (GeoSeal-encrypted + ritual-gated)")
    ec.add_argument("--payload-b64", required=True, help="Base64-encoded payload to seal")
    ec.add_argument(
        "--primary-tongue",
        required=True,
        choices=TONGUES,
        help="Tongue identity bound to egg",
    )
    ec.add_argument("--glyph", default="egg", help="Visual symbol for the egg")
    ec.add_argument("--hatch-condition", default="{}", help="JSON dict of ritual requirements")
    ec.add_argument("--context", required=True, help="JSON array of 6 floats for GeoSeal context")
    ec.add_argument("--kem-key", required=True, help="Base64 KEM public key")
    ec.add_argument("--dsa-key", required=True, help="Base64 DSA signing key")
    ec.add_argument("--out", dest="outfile", help="Output JSON file (default: stdout)")
    ec.set_defaults(func=cmd_egg_create)

    eh = sub.add_parser("egg-hatch", help="Attempt to hatch a Sacred Egg")
    eh.add_argument("--egg-json", required=True, help="Path to Sacred Egg JSON file")
    eh.add_argument("--agent-tongue", required=True, choices=TONGUES, help="Agent's active tongue")
    eh.add_argument(
        "--ritual-mode",
        default="solitary",
        choices=["solitary", "triadic", "ring_descent"],
    )
    eh.add_argument(
        "--additional-tongues",
        default="[]",
        help="JSON array of extra tongues (triadic mode)",
    )
    eh.add_argument(
        "--path-history",
        default="[]",
        help="JSON array of ring traversal (ring_descent mode)",
    )
    eh.add_argument("--context", required=True, help="JSON array of 6 floats for current context")
    eh.add_argument("--kem-key", required=True, help="Base64 KEM secret key")
    eh.add_argument("--dsa-pk", required=True, help="Base64 DSA verification key")
    eh.add_argument("--lexicons")
    eh.set_defaults(func=cmd_egg_hatch)

    ep = sub.add_parser("egg-paint", help="Paint an egg — change the shell, keep the yolk")
    ep.add_argument("--egg-json", required=True, help="Path to Sacred Egg JSON file")
    ep.add_argument("--glyph", help="New visual symbol for the egg")
    ep.add_argument("--hatch-condition", help="New hatch condition JSON (replaces existing)")
    ep.add_argument("--out", dest="outfile", help="Output JSON file (default: stdout)")
    ep.set_defaults(func=cmd_egg_paint)

    ps = sub.add_parser("seed", help="AetherLex Seed: mnemonic to PQC key material")
    ps.add_argument("--phrase", help="Existing mnemonic phrase (omit to generate)")
    ps.add_argument("--length", type=int, default=13, help="Token count for generated phrase")
    ps.add_argument("--bytes", type=int, default=64, choices=[32, 64], help="Seed output length")
    ps.add_argument("--weights", default="lws", choices=["lws", "phdm"], help="Weight system")
    ps.add_argument("--split", choices=["mlkem", "mldsa"], help="Split seed for PQC algorithm")
    ps.add_argument("--lexicons")
    ps.set_defaults(func=cmd_seed)

    return p


if __name__ == "__main__":
    cli = build_cli()
    if len(sys.argv) == 1:
        sys.exit(selftest())
    args = cli.parse_args()
    if not hasattr(args, "func"):
        print("no subcommand specified; running selftest")
        sys.exit(selftest())
    sys.exit(args.func(args) or 0)
