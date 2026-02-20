#!/usr/bin/env python3
"""
Six Tongues + GeoSeal CLI — SCBE-AETHERMOORE Cryptographic Toolkit.

Pure-stdlib Python CLI for conlang bijective tokenization and context-aware sealing.

Features:
  - Six Sacred Tongues bijective tokenization (256 tokens per tongue: KO, AV, RU, CA, UM, DR)
  - Cross-tongue translation preserving byte payload (with HMAC attestation)
  - Blend / unblend multi-tongue streams by pattern
  - GeoSeal: context-aware encryption with HEALPix/Morton projection + PQC-ready structure
  - ConcentricRingPolicy: ring-based access control integrated into GeoSeal
  - EvolvingLexicons: self-mutating language driven by coherence and hyperbolic drift
  - Built-in selftest for round-trip and integrity checks

Usage:
  python six-tongues-cli.py                     # Run selftest
  python six-tongues-cli.py encode --tongue KO   # Encode stdin to KO tokens
  python six-tongues-cli.py decode --tongue KO   # Decode KO tokens to bytes
  python six-tongues-cli.py xlate --src KO --dst AV  # Cross-translate
  python six-tongues-cli.py blend --pattern KO:2,AV:1,DR:1
  python six-tongues-cli.py unblend
  python six-tongues-cli.py geoseal-encrypt --context '[0.2,-0.3,0.7]' --kem-key <b64> --dsa-key <b64>
  python six-tongues-cli.py geoseal-decrypt --context '[0.2,-0.3,0.7]' --kem-key <b64> --dsa-pk <b64>

@module cli/six-tongues
@layer Layer 14
@component Six Tongues + GeoSeal CLI
@version 1.0.0
"""

import argparse
import base64
import dataclasses
import hashlib
import hmac
import json
import math
import os
import random
import secrets
import sys
import time
from typing import Dict, Iterable, List, Optional, Tuple

# ═══════════════════════════════════════════════════════════════
# Core Lexicon & Tokenizer
# ═══════════════════════════════════════════════════════════════

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]

# ---------------------------------------------------------------------------
# Canonical Sacred Tongue tables — must match packages/kernel/src/sacredTongues.ts
# Each tongue has 16 prefixes x 16 suffixes = 256 unique tokens.
# Token for byte b = prefix[b >> 4] + "'" + suffix[b & 0x0F]
# ---------------------------------------------------------------------------
_CANONICAL_TONGUES: Dict[str, Tuple[List[str], List[str]]] = {
    "KO": (
        ["sil", "kor", "vel", "zar", "keth", "thul", "nav", "ael",
         "ra", "med", "gal", "lan", "joy", "good", "nex", "vara"],
        ["a", "ae", "ei", "ia", "oa", "uu", "eth", "ar",
         "or", "il", "an", "en", "un", "ir", "oth", "esh"],
    ),
    "AV": (
        ["saina", "talan", "vessa", "maren", "oriel", "serin", "nurel", "lirea",
         "kiva", "lumen", "calma", "ponte", "verin", "nava", "sela", "tide"],
        ["a", "e", "i", "o", "u", "y", "la", "re",
         "na", "sa", "to", "mi", "ve", "ri", "en", "ul"],
    ),
    "RU": (
        ["khar", "drath", "bront", "vael", "ur", "mem", "krak", "tharn",
         "groth", "basalt", "rune", "sear", "oath", "gnarl", "rift", "iron"],
        ["ak", "eth", "ik", "ul", "or", "ar", "um", "on",
         "ir", "esh", "nul", "vek", "dra", "kh", "va", "th"],
    ),
    "CA": (
        ["bip", "bop", "klik", "loopa", "ifta", "thena", "elsa", "spira",
         "rythm", "quirk", "fizz", "gear", "pop", "zip", "mix", "chass"],
        ["a", "e", "i", "o", "u", "y", "ta", "na",
         "sa", "ra", "lo", "mi", "ki", "zi", "qwa", "sh"],
    ),
    "UM": (
        ["veil", "zhur", "nar", "shul", "math", "hollow", "hush", "thorn",
         "dusk", "echo", "ink", "wisp", "bind", "ache", "null", "shade"],
        ["a", "e", "i", "o", "u", "ae", "sh", "th",
         "ak", "ul", "or", "ir", "en", "on", "vek", "nul"],
    ),
    "DR": (
        ["anvil", "tharn", "mek", "grond", "draum", "ektal", "temper", "forge",
         "stone", "steam", "oath", "seal", "frame", "pillar", "rivet", "ember"],
        ["a", "e", "i", "o", "u", "ae", "rak", "mek",
         "tharn", "grond", "vek", "ul", "or", "ar", "en", "on"],
    ),
}


class Lexicons:
    """Bijective 256-token lexicon per Sacred Tongue.

    Each tongue maps bytes 0..255 to unique tokens via a nibble scheme:
    token = prefix[b >> 4] + "'" + suffix[b & 0x0F]
    This gives 16x16 = 256 unique tokens per tongue, guaranteed bijective.
    """

    def __init__(self, table: Optional[Dict[str, Dict[str, str]]] = None):
        if table is None:
            table = self._canonical_lexicons()
        self.by_idx: Dict[str, List[str]] = {}
        self.by_tok: Dict[str, Dict[str, int]] = {}
        for tg in TONGUES:
            m = table.get(tg)
            if not m:
                raise ValueError(f"missing tongue {tg} in lexicons")
            lst: List[Optional[str]] = [None] * 256
            for k, v in m.items():
                idx = int(k)
                if not (0 <= idx <= 255):
                    raise ValueError("lexicon indices must be 0..255")
                lst[idx] = v
            if any(x is None for x in lst):
                raise ValueError(f"lexicon {tg} incomplete")
            # Enforce uniqueness to guarantee bijection
            if len(set(lst)) != 256:
                raise ValueError(f"lexicon {tg} contains duplicate tokens; need a bijection")
            self.by_idx[tg] = lst  # type: ignore[assignment]
            inv = {tok: i for i, tok in enumerate(lst)}
            self.by_tok[tg] = inv

    def token_of(self, tongue: str, b: int) -> str:
        """Map byte value to token in the given tongue."""
        return self.by_idx[tongue][b]

    def byte_of(self, tongue: str, token: str) -> int:
        """Map token back to byte value in the given tongue."""
        inv = self.by_tok[tongue]
        if token not in inv:
            raise KeyError(f"unknown token in {tongue}: {token}")
        return inv[token]

    @staticmethod
    def _canonical_lexicons() -> Dict[str, Dict[str, str]]:
        """Build 256-token lexicons from canonical Sacred Tongue tables."""
        result: Dict[str, Dict[str, str]] = {}
        for tg, (prefixes, suffixes) in _CANONICAL_TONGUES.items():
            out: Dict[str, str] = {}
            for i in range(256):
                p = prefixes[(i >> 4) & 0xF]
                s = suffixes[i & 0xF]
                out[str(i)] = f"{p}'{s}"
            result[tg] = out
        return result


class TongueTokenizer:
    """Encode/decode bytes to/from Sacred Tongue token streams."""

    def __init__(self, lex: Lexicons):
        self.lex = lex

    def encode_bytes(self, tongue: str, data: bytes) -> List[str]:
        """Encode raw bytes into token stream for the given tongue."""
        return [self.lex.token_of(tongue, b) for b in data]

    def decode_tokens(self, tongue: str, tokens: Iterable[str]) -> bytes:
        """Decode token stream back to raw bytes."""
        arr = bytearray()
        for tok in tokens:
            if not tok:
                continue
            arr.append(self.lex.byte_of(tongue, tok))
        return bytes(arr)

    def normalize_token_stream(self, text: str) -> List[str]:
        """Parse a whitespace/comma-separated token string into a list."""
        toks = []
        for part in text.replace(",", " ").split():
            part = part.strip()
            if part:
                toks.append(part)
        return toks


# ═══════════════════════════════════════════════════════════════
# Cross-Tokenization
# ═══════════════════════════════════════════════════════════════


@dataclasses.dataclass
class XlateAttestation:
    """Attestation record for a cross-tongue translation."""
    src: str
    dst: str
    mode: str
    ts: float
    phase_delta: float
    weight_ratio: float
    sha256_bytes: str
    hmac_attest: str


class CrossTokenizer:
    """Cross-tongue translation with attestation and blend/unblend."""

    # Phase offsets (radians) and golden-ratio weights per tongue
    PHASE = {
        "KO": 0,
        "AV": math.pi / 3,
        "RU": 2 * math.pi / 3,
        "CA": math.pi,
        "UM": 4 * math.pi / 3,
        "DR": 5 * math.pi / 3,
    }
    WEIGHT = {
        "KO": 1.00,
        "AV": 1.618,
        "RU": 2.618,
        "CA": 4.236,
        "UM": 6.854,
        "DR": 11.090,
    }

    def __init__(self, tok: TongueTokenizer):
        self.tok = tok

    def to_bytes_from_tokens(self, tongue: str, token_text: str) -> bytes:
        """Decode a token text string to bytes."""
        toks = self.tok.normalize_token_stream(token_text)
        return self.tok.decode_tokens(tongue, toks)

    def to_tokens_from_bytes(self, tongue: str, data: bytes) -> List[str]:
        """Encode bytes to token list."""
        return self.tok.encode_bytes(tongue, data)

    def retokenize(
        self,
        src_tg: str,
        dst_tg: str,
        token_text: str,
        mode: str = "byte",
        attest_key: Optional[bytes] = None,
    ) -> Tuple[List[str], XlateAttestation]:
        """Re-encode token stream from src tongue to dst tongue.

        Preserves exact byte payload. Produces HMAC attestation.
        """
        if mode not in ("byte", "semantic"):
            raise ValueError("mode must be 'byte' or 'semantic'")
        b = self.to_bytes_from_tokens(src_tg, token_text)
        out_tokens = self.to_tokens_from_bytes(dst_tg, b)
        sha = hashlib.sha256(b).hexdigest()
        phase_delta = (self.PHASE[dst_tg] - self.PHASE[src_tg]) % (2 * math.pi)
        weight_ratio = self.WEIGHT[dst_tg] / self.WEIGHT[src_tg]
        msg = (
            f"{src_tg}->{dst_tg}|{mode}|{sha}|{phase_delta:.6f}"
            f"|{weight_ratio:.6f}|{int(time.time())}"
        ).encode()
        h = base64.b64encode(
            hmac.new(
                attest_key or b"aether-attest-default", msg, hashlib.sha256
            ).digest()
        ).decode()
        attest = XlateAttestation(
            src_tg, dst_tg, mode, time.time(), phase_delta, weight_ratio, sha, h
        )
        return out_tokens, attest

    def blend(self, pattern: List[str], data: bytes) -> List[Tuple[str, str]]:
        """Interleave bytes across tongues according to pattern."""
        out: List[Tuple[str, str]] = []
        for i, byte in enumerate(data):
            tg = pattern[i % len(pattern)]
            out.append((tg, self.tok.lex.token_of(tg, byte)))
        return out

    def unblend(self, pattern: List[str], pairs: List[Tuple[str, str]]) -> bytes:
        """Reverse a blended stream using the same pattern."""
        arr = bytearray()
        for i, (tg, tok) in enumerate(pairs):
            expected = pattern[i % len(pattern)]
            if tg != expected:
                raise ValueError(f"blend pattern mismatch at index {i}: expected {expected}, got {tg}")
            arr.append(self.tok.lex.byte_of(tg, tok))
        return bytes(arr)


# ═══════════════════════════════════════════════════════════════
# GeoSeal — Context-Aware Encryption
# ═══════════════════════════════════════════════════════════════


def _zscore(xs: List[float]) -> List[float]:
    """Z-score normalization."""
    mu = sum(xs) / len(xs)
    var = sum((x - mu) * (x - mu) for x in xs) / max(1, len(xs) - 1)
    sd = math.sqrt(var) if var > 0 else 1.0
    return [(x - mu) / sd for x in xs]


def project_to_sphere(ctx: List[float]) -> List[float]:
    """Project context vector onto unit sphere (first 3 dims)."""
    take = (ctx[:3] if len(ctx) >= 3 else (ctx + [0, 0, 0])[:3])
    z = _zscore(list(take))
    norm = math.sqrt(sum(v * v for v in z)) or 1.0
    return [v / norm for v in z]


def project_to_cube(ctx: List[float], m: int = 6) -> List[float]:
    """Project context vector into [0,1]^m cube via tanh normalization."""
    arr = [(math.tanh(x / 5) + 1) / 2 for x in (ctx[:m] if len(ctx) >= m else ctx + [0] * (m - len(ctx)))]
    return [min(1.0, max(0.0, x)) for x in arr]


def healpix_id(u: List[float], L: int) -> str:
    """Compute HEALPix-style tile ID from sphere coordinates."""
    q = tuple(int((v + 1) * 1000) for v in u)
    return f"S{L}:{q}"


def morton_id(v: List[float], L: int) -> str:
    """Compute Morton-code tile ID from cube coordinates."""
    q = tuple(int(x * (10 ** min(3, 1 + L))) for x in v[: min(6, len(v))])
    return f"C{L}:{q}"


def potentials(u: List[float], v: List[float]) -> Tuple[float, float]:
    """Compute risk potential P and safety margin from projections."""
    R = sum(abs(x) for x in u) + 0.1 * sum(v)
    T = 0.5 + 0.05 * len([x for x in v if x < 0.2])
    P = 0.7 * R - 0.3 * T
    margin = 0.5 - abs(u[0])
    return P, margin


def classify_context(h: str, z: str, P: float, margin: float) -> str:
    """Classify context as interior or exterior based on projections and potentials."""
    return "interior" if ("S" in h and "C" in z and P < 0.6 and margin > 0.05) else "exterior"


# ═══════════════════════════════════════════════════════════════
# Concentric Ring Policy
# ═══════════════════════════════════════════════════════════════


class ConcentricRingPolicy:
    """Ring-based access control for GeoSeal.

    Maps radial distance from context center to security rings
    with escalating latency, signature, and PoW requirements.
    """

    RINGS = [
        (0.0, 0.3, "core", 5, 1, 8, 0.001),
        (0.3, 0.5, "inner", 20, 1, 8, 0.005),
        (0.5, 0.7, "middle", 100, 2, 16, 0.01),
        (0.7, 0.9, "outer", 500, 3, 24, 0.05),
        (0.9, 1.0, "edge", 5000, 4, 32, 0.2),
    ]

    def classify(self, r: float) -> dict:
        """Classify radial distance to ring policy parameters."""
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


# ═══════════════════════════════════════════════════════════════
# Envelope Crypto — Real PQC with Fallback
# ═══════════════════════════════════════════════════════════════

# Try to import real PQC (NIST FIPS 203/204) from pqcrypto
_REAL_PQC = False
try:
    from pqcrypto.kem.ml_kem_768 import (
        generate_keypair as _kem_keygen,
        encrypt as _kem_encrypt,
        decrypt as _kem_decrypt,
    )
    from pqcrypto.sign.ml_dsa_65 import (
        generate_keypair as _dsa_keygen,
        sign as _dsa_sign_real,
        verify as _dsa_verify_real,
    )
    _REAL_PQC = True
except ImportError:
    pass


def hkdf(key: bytes, info: str) -> bytes:
    """RFC 5869 HKDF-SHA256 (single 32-byte output block)."""
    salt = b"\x00" * 32
    # Extract
    prk = hmac.new(salt, key, hashlib.sha256).digest()
    # Expand (T1 only for 32-byte output)
    return hmac.new(prk, info.encode() + b"\x01", hashlib.sha256).digest()


def pqc_available() -> bool:
    """Check if real post-quantum crypto is available."""
    return _REAL_PQC


def kem_keygen() -> Tuple[bytes, bytes]:
    """Generate ML-KEM-768 keypair (pk, sk). Falls back to mock."""
    if _REAL_PQC:
        return _kem_keygen()
    # Mock mode: derive pk deterministically from sk for encaps/decaps consistency.
    sk = secrets.token_bytes(32)
    pk = hashlib.sha256(b"ml-kem-mock:pk:" + sk).digest()
    return pk, sk


def kyber_encaps(pk: bytes) -> Tuple[bytes, bytes]:
    """ML-KEM-768 encapsulation. Returns (shared_secret, ciphertext).

    Uses real ML-KEM-768 when pqcrypto is available, HMAC-SHA256 mock otherwise.
    """
    if _REAL_PQC:
        ct, ss = _kem_encrypt(pk)
        return ss, ct
    # Mock mode: ciphertext carries an ephemeral nonce; shared secret binds pk + nonce.
    ct = secrets.token_bytes(32)
    ss = hmac.new(pk, b"ml-kem-mock:ss:" + ct, hashlib.sha256).digest()
    return ss, ct


def kyber_decaps(sk: bytes, ct: bytes) -> bytes:
    """ML-KEM-768 decapsulation. Returns shared_secret.

    Uses real ML-KEM-768 when pqcrypto is available, HMAC-SHA256 mock otherwise.
    """
    if _REAL_PQC:
        return _kem_decrypt(sk, ct)
    pk = hashlib.sha256(b"ml-kem-mock:pk:" + sk).digest()
    return hmac.new(pk, b"ml-kem-mock:ss:" + ct, hashlib.sha256).digest()


def dsa_keygen() -> Tuple[bytes, bytes]:
    """Generate ML-DSA-65 keypair (pk, sk). Falls back to mock."""
    if _REAL_PQC:
        return _dsa_keygen()
    # Mock mode: derive pk deterministically from sk for sign/verify consistency.
    sk = secrets.token_bytes(32)
    pk = hashlib.sha256(b"ml-dsa-mock:pk:" + sk).digest()
    return pk, sk


def dsa_sign(sk: bytes, msg: bytes) -> bytes:
    """ML-DSA-65 sign. Uses real ML-DSA-65 when pqcrypto is available."""
    if _REAL_PQC:
        return _dsa_sign_real(sk, msg)
    pk = hashlib.sha256(b"ml-dsa-mock:pk:" + sk).digest()
    return hmac.new(pk, b"ml-dsa-mock:sig:" + msg, hashlib.sha256).digest()


def dsa_verify(pk: bytes, msg: bytes, sig: bytes) -> bool:
    """ML-DSA-65 verify. Uses real ML-DSA-65 when pqcrypto is available."""
    if _REAL_PQC:
        try:
            result = _dsa_verify_real(pk, msg, sig)
            # pqcrypto may return bool or raise on failure
            return result is True or result is None
        except Exception:
            return False
    expected = hmac.new(pk, b"ml-dsa-mock:sig:" + msg, hashlib.sha256).digest()
    return hmac.compare_digest(expected, sig)


# ═══════════════════════════════════════════════════════════════
# GeoSeal Encrypt / Decrypt
# ═══════════════════════════════════════════════════════════════

_RING_POLICY = ConcentricRingPolicy()


def geoseal_encrypt(
    plaintext_b64: str,
    context: List[float],
    pk_kem_b64: str,
    sk_dsa_b64: str,
    Ls: int = 2,
    Lc: int = 2,
) -> dict:
    """Wrap plaintext with context-aware GeoSeal envelope.

    Integrates ConcentricRingPolicy for ring-based access control.
    """
    pt = base64.b64decode(plaintext_b64)
    u = project_to_sphere(context)
    v = project_to_cube(context)
    h = healpix_id(u, Ls)
    z = morton_id(v, Lc)
    P, margin = potentials(u, v)
    path = classify_context(h, z, P, margin)

    # Ring classification based on radial distance
    r = math.sqrt(sum(x * x for x in u)) / max(1.0, math.sqrt(len(u)))
    ring_policy = _RING_POLICY.classify(r)

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
        "ring": ring_policy,
    }
    sig_payload = hashlib.sha256(
        json.dumps(attest, sort_keys=True).encode() + ct_k + ct_spec
    ).digest()
    sig = dsa_sign(base64.b64decode(sk_dsa_b64), sig_payload)
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
) -> Tuple[bool, Optional[bytes]]:
    """Verify and unwrap a GeoSeal envelope."""
    ct_k = base64.b64decode(env["ct_k"]) if isinstance(env["ct_k"], str) else env["ct_k"]
    ct_spec = base64.b64decode(env["ct_spec"]) if isinstance(env["ct_spec"], str) else env["ct_spec"]
    attest = env["attest"]
    sig = base64.b64decode(env["sig"]) if isinstance(env["sig"], str) else env["sig"]

    # Context binding check: same context must recreate the same realm projection.
    Ls = int(attest.get("L_s", 2))
    Lc = int(attest.get("L_c", 2))
    u = project_to_sphere(context)
    v = project_to_cube(context)
    h_expected = healpix_id(u, Ls)
    z_expected = morton_id(v, Lc)
    if h_expected != attest.get("h") or z_expected != attest.get("z"):
        return False, None

    sig_payload = hashlib.sha256(
        json.dumps(attest, sort_keys=True).encode() + ct_k + ct_spec
    ).digest()
    if not dsa_verify(base64.b64decode(pk_dsa_b64), sig_payload, sig):
        return False, None

    ss = kyber_decaps(base64.b64decode(sk_kem_b64), ct_k)
    Ks = hkdf(ss, f"geo:sphere|{attest['h']}|{attest['L_s']}")
    Kc = hkdf(ss, f"geo:cube|{attest['z']}|{attest['L_c']}")
    Kmsg = hkdf(bytes(x ^ y for x, y in zip(Ks, Kc)), "geo:msg")
    mask_seed = hashlib.sha256(Kmsg).digest()
    mask = (mask_seed * ((len(ct_spec) // len(mask_seed)) + 2))[: len(ct_spec)]
    pt = bytes(a ^ b for a, b in zip(ct_spec, mask))
    return True, pt


# ═══════════════════════════════════════════════════════════════
# EvolvingLexicons — Self-Mutating Language
# ═══════════════════════════════════════════════════════════════


class EvolvingLexicons(Lexicons):
    """Mutable lexicon with hyperbolic drift toward realm centers.

    After each successful cross-translation, tokens can mutate based on
    coherence scores and proximity to realm centers in 6D Poincare space.
    Two agents using the system separately will slowly grow mutually
    unintelligible dialects — cryptographic speciation.
    """

    # Realm centers in 6D (one per tongue)
    REALM_CENTERS = {
        "KO": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "AV": [0.3, 0.1, 0.0, 0.0, 0.0, 0.0],
        "RU": [0.0, 0.4, 0.2, 0.0, 0.0, 0.0],
        "CA": [-0.2, -0.3, 0.4, 0.1, 0.0, 0.0],
        "UM": [0.0, 0.0, -0.5, 0.3, 0.2, 0.0],
        "DR": [0.1, -0.2, 0.0, -0.4, 0.3, 0.1],
    }

    # Phonotactic syllable pools for mutation
    _SYLLABLES = [
        "ka", "ke", "ki", "ko", "ku", "sa", "se", "si", "so", "su",
        "ra", "re", "ri", "ro", "ru", "za", "na", "ne", "ni", "no",
        "nu", "la", "le", "li", "lo", "lu", "ta", "te", "ti", "to",
        "tu", "ma", "ve", "vi", "da", "de", "di", "do", "du", "ba",
        "be", "bi", "bo", "bu", "ga", "ge", "gi", "go", "gu", "ha",
    ]

    def __init__(
        self,
        table: Optional[Dict[str, Dict[str, str]]] = None,
        mutation_rate: float = 0.01,
        drift_strength: float = 0.05,
    ):
        super().__init__(table)
        self.mutation_rate = mutation_rate
        self.drift_strength = drift_strength
        self.mutation_log: List[dict] = []

    def evolve_after_use(
        self,
        src_tg: str,
        dst_tg: str,
        payload_bytes: bytes,
        coherence: float = 1.0,
    ) -> Optional[dict]:
        """Mutate lexicon after a successful cross-translation.

        Returns mutation record if a mutation occurred, None otherwise.
        """
        if random.random() > self.mutation_rate * coherence:
            return None

        if len(payload_bytes) == 0:
            return None

        byte_idx = random.randint(0, len(payload_bytes) - 1)
        b = payload_bytes[byte_idx]
        current_token = self.token_of(dst_tg, b)

        # Compute meaning vector from realm centers
        meaning_vec = [0.0] * 6
        for tg in [src_tg, dst_tg]:
            center = self.REALM_CENTERS.get(tg, [0] * 6)
            for j in range(6):
                meaning_vec[j] += center[j] * (1 + coherence)

        norm = math.sqrt(sum(x * x for x in meaning_vec)) or 1.0
        drift = [x / norm * self.drift_strength * coherence for x in meaning_vec]

        # Generate new token via phonotactic mutation
        new_token = self._drift_token(current_token, dst_tg, drift)

        # Ensure bijection: if new token already exists, abandon
        if new_token in self.by_tok[dst_tg]:
            return None

        # Apply mutation
        old_token = self.by_idx[dst_tg][b]
        self.by_idx[dst_tg][b] = new_token
        del self.by_tok[dst_tg][old_token]
        self.by_tok[dst_tg][new_token] = b

        record = {
            "byte": b,
            "tongue": dst_tg,
            "old_token": old_token,
            "new_token": new_token,
            "coherence": coherence,
            "drift": drift,
        }
        self.mutation_log.append(record)
        return record

    def _drift_token(self, token: str, tg: str, drift: List[float]) -> str:
        """Apply phonotactic drift based on realm direction.

        Uses drift vector combined with current token to select replacement syllables
        from the phonotactic pool, preserving the tongue prefix and delimiter structure.
        """
        prefix = tg.lower()
        # Combine drift with current token for uniqueness
        seed = hash((token, tuple(round(d, 4) for d in drift), random.random()))
        idx1 = abs(seed) % len(self._SYLLABLES)
        idx2 = abs(seed >> 16) % len(self._SYLLABLES)
        hi_syl = self._SYLLABLES[idx1]
        lo_syl = self._SYLLABLES[idx2]
        return f"{prefix}{hi_syl}'{lo_syl}"


# ═══════════════════════════════════════════════════════════════
# SemanticNavigator — Living 6D Meaning Space (requires numpy/scipy)
# ═══════════════════════════════════════════════════════════════

_HAS_NUMPY = False
try:
    import numpy as np
    from scipy.integrate import odeint as _odeint

    _HAS_NUMPY = True
except ImportError:
    pass


def numpy_available() -> bool:
    """Check if numpy/scipy are available for SemanticNavigator."""
    return _HAS_NUMPY


class SemanticNavigator:
    """Tracks agent position in 6D Poincare ball semantic space.

    Position = semantic state = cryptographic fingerprint.
    Uses a chaotic ODE (Lorenz-like in 6D) driven by intent tongues,
    coherence scores, and mutation events.

    Requires numpy and scipy. Check `numpy_available()` before constructing.
    """

    REALM_CENTERS = {
        "KO": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "AV": [0.3, 0.1, 0.0, 0.0, 0.0, 0.0],
        "RU": [0.0, 0.4, 0.2, 0.0, 0.0, 0.0],
        "CA": [-0.2, -0.3, 0.4, 0.1, 0.0, 0.0],
        "UM": [0.0, 0.0, -0.5, 0.3, 0.2, 0.0],
        "DR": [0.1, -0.2, 0.0, -0.4, 0.3, 0.1],
    }

    def __init__(
        self,
        initial_pos: Optional[List[float]] = None,
        chaos_strength: float = 0.1,
    ):
        if not _HAS_NUMPY:
            raise ImportError("SemanticNavigator requires numpy and scipy")
        self.position = np.array(initial_pos or [0.0] * 6, dtype=float)
        self.chaos_strength = chaos_strength
        self.velocity = np.zeros(6)
        self.history: List[np.ndarray] = [self.position.copy()]

    def poincare_project(self, vec: np.ndarray) -> np.ndarray:
        """Keep position inside Poincare ball (norm < 1)."""
        norm = np.linalg.norm(vec)
        if norm >= 0.99:
            vec = vec * 0.98 / norm
        return vec

    def _drift_ode(
        self,
        pos: np.ndarray,
        t: float,
        target_realms: List[str],
        coherence: float,
        mutation_events: int,
    ) -> np.ndarray:
        """Chaotic ODE governing semantic drift."""
        # Attraction to realm centers
        attraction = np.zeros(6)
        for tg in target_realms:
            center = np.array(self.REALM_CENTERS.get(tg, [0] * 6))
            attraction += (center - pos) * coherence

        # Repulsion from mutations
        rng = np.random.default_rng()
        repulsion = rng.standard_normal(6) * mutation_events * 0.05

        # Chaotic term (Lorenz-like in 6D)
        chaos = np.array([
            10 * (pos[1] - pos[0]),
            pos[0] * (28 - pos[2]) - pos[1],
            pos[0] * pos[1] - 2.667 * pos[2],
            np.sin(pos[3]) * 0.5,
            np.cos(pos[4]) * 0.3,
            (pos[5] ** 2 - 0.5) * 0.2,
        ]) * self.chaos_strength

        return attraction + repulsion + chaos

    def update_position(
        self,
        intent_tongues: List[str],
        coherence: float = 1.0,
        mutation_count: int = 0,
        dt: float = 0.1,
    ) -> np.ndarray:
        """Update position based on recent intent.

        Returns updated 6D position vector.
        """
        t = np.linspace(0, dt, 10)
        trajectory = _odeint(
            self._drift_ode,
            self.position,
            t,
            args=(intent_tongues, coherence, mutation_count),
        )
        self.position = self.poincare_project(trajectory[-1])
        self.velocity = (self.position - self.history[-1]) / dt
        self.history.append(self.position.copy())
        return self.position

    def distance_to(self, other: "SemanticNavigator") -> float:
        """Hyperbolic distance to another agent in 6D Poincare space."""
        a, b = self.position, other.position
        aa = np.dot(a, a)
        bb = np.dot(b, b)
        if aa >= 1 or bb >= 1:
            return float("inf")
        ab = np.dot(a - b, a - b)
        denom = (1 - aa) * (1 - bb)
        if denom <= 0:
            return float("inf")
        return float(np.arccosh(1 + 2 * ab / denom))

    def export_trajectory(self) -> np.ndarray:
        """Export position history as numpy array (N x 6)."""
        return np.array(self.history)


# ═══════════════════════════════════════════════════════════════
# CLI Commands
# ═══════════════════════════════════════════════════════════════


def load_lexicons(path: Optional[str]) -> Lexicons:
    """Load lexicons from JSON file or use demo defaults."""
    if not path:
        return Lexicons()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Lexicons(data)


def cmd_encode(args: argparse.Namespace) -> int:
    lex = load_lexicons(args.lexicons)
    tok = TongueTokenizer(lex)
    if getattr(args, "text", None) is not None:
        data = args.text.encode("utf-8")
    elif args.infile:
        data = open(args.infile, "rb").read()
    else:
        data = sys.stdin.buffer.read()
    tokens = tok.encode_bytes(args.tongue, data)
    out = (" ".join(tokens) + "\n").encode()
    if not args.outfile:
        sys.stdout.buffer.write(out)
    else:
        open(args.outfile, "wb").write(out)
    return 0


def cmd_decode(args: argparse.Namespace) -> int:
    lex = load_lexicons(args.lexicons)
    tok = TongueTokenizer(lex)
    if getattr(args, "text", None) is not None:
        text = args.text
    elif args.infile:
        text = open(args.infile, "r", encoding="utf-8").read()
    else:
        text = sys.stdin.read()
    tokens = tok.normalize_token_stream(text)
    data = tok.decode_tokens(args.tongue, tokens)
    if not args.outfile:
        if getattr(args, "as_text", False):
            sys.stdout.write(data.decode("utf-8", errors="replace"))
            sys.stdout.write("\n")
        else:
            sys.stdout.buffer.write(data)
    else:
        open(args.outfile, "wb").write(data)
    return 0


def cmd_xlate(args: argparse.Namespace) -> int:
    lex = load_lexicons(args.lexicons)
    tok = TongueTokenizer(lex)
    xt = CrossTokenizer(tok)
    text = sys.stdin.read() if not args.infile else open(args.infile, "r", encoding="utf-8").read()
    out_tokens, attest = xt.retokenize(
        args.src,
        args.dst,
        text,
        mode=args.mode,
        attest_key=(base64.b64decode(args.attest_key) if args.attest_key else None),
    )
    bundle = {"tokens": " ".join(out_tokens), "attestation": dataclasses.asdict(attest)}
    s = json.dumps(bundle, ensure_ascii=False)
    if not args.outfile:
        print(s)
    else:
        open(args.outfile, "w", encoding="utf-8").write(s)
    return 0


def cmd_blend(args: argparse.Namespace) -> int:
    lex = load_lexicons(args.lexicons)
    tok = TongueTokenizer(lex)
    xt = CrossTokenizer(tok)
    data = sys.stdin.buffer.read() if not args.infile else open(args.infile, "rb").read()
    pattern: List[str] = []
    for seg in args.pattern.split(","):
        parts = seg.split(":") if ":" in seg else [seg, "1"]
        name, count = parts[0], parts[1]
        for _ in range(int(count)):
            pattern.append(name)
    pairs = xt.blend(pattern, data)
    s = json.dumps({"pattern": pattern, "pairs": pairs}, ensure_ascii=False)
    if not args.outfile:
        print(s)
    else:
        open(args.outfile, "w", encoding="utf-8").write(s)
    return 0


def cmd_unblend(args: argparse.Namespace) -> int:
    lex = load_lexicons(args.lexicons)
    tok = TongueTokenizer(lex)
    xt = CrossTokenizer(tok)
    js = json.load(sys.stdin if not args.infile else open(args.infile, "r", encoding="utf-8"))
    pattern = js["pattern"]
    pairs = [(tg, t) for tg, t in js["pairs"]]
    data = xt.unblend(pattern, pairs)
    if not args.outfile:
        sys.stdout.buffer.write(data)
    else:
        open(args.outfile, "wb").write(data)
    return 0


def cmd_gencore(args: argparse.Namespace) -> int:
    pt_b64 = sys.stdin.read().strip() if args.plaintext_b64 is None else args.plaintext_b64
    ctx = json.loads(args.context)
    env = geoseal_encrypt(pt_b64, ctx, args.kem_key, args.dsa_key)
    print(json.dumps(env))
    return 0


def cmd_gendec(args: argparse.Namespace) -> int:
    env = json.load(sys.stdin if not args.env else open(args.env, "r"))
    ctx = json.loads(args.context)
    ok, pt = geoseal_decrypt(env, ctx, args.kem_key, args.dsa_pk)
    if not ok:
        print("GeoSeal verification failed", file=sys.stderr)
        return 1
    sys.stdout.buffer.write(pt)
    return 0


# ═══════════════════════════════════════════════════════════════
# Self-Test
# ═══════════════════════════════════════════════════════════════


def selftest() -> int:
    """Run comprehensive self-test suite."""
    errors = 0

    def check(label: str, condition: bool) -> None:
        nonlocal errors
        if not condition:
            print(f"  FAIL: {label}")
            errors += 1

    print("=== Six Tongues + GeoSeal Self-Test ===\n")

    # --- Lexicon & Tokenizer ---
    print("[1] Lexicon & Tokenizer")
    lex = Lexicons()
    tok = TongueTokenizer(lex)
    payload = os.urandom(1024)

    for tg in TONGUES:
        toks = tok.encode_bytes(tg, payload)
        dec = tok.decode_tokens(tg, toks)
        check(f"{tg} round-trip 1024 bytes", dec == payload)
        # Bijection: all 256 bytes produce unique tokens
        all_tokens = tok.encode_bytes(tg, bytes(range(256)))
        check(f"{tg} bijection (256 unique)", len(set(all_tokens)) == 256)

    print(f"  Tongues tested: {len(TONGUES)}")

    # --- Cross-Retokenization ---
    print("[2] Cross-Retokenization")
    xt = CrossTokenizer(tok)

    for s in TONGUES:
        for d in TONGUES:
            ttext = " ".join(tok.encode_bytes(s, payload))
            out_tokens, attest = xt.retokenize(s, d, ttext, attest_key=b"k")
            back = tok.decode_tokens(d, out_tokens)
            check(f"{s}->{d} byte-mode preserves payload", back == payload)
            check(f"{s}->{d} attestation present", isinstance(attest.hmac_attest, str) and len(attest.hmac_attest) > 0)
            out_tokens2, _ = xt.retokenize(s, d, ttext, mode="semantic", attest_key=b"k")
            check(f"{s}->{d} semantic-mode preserves payload", tok.decode_tokens(d, out_tokens2) == payload)

    print(f"  Cross-translations tested: {len(TONGUES) * len(TONGUES)}")

    # --- Blend / Unblend ---
    print("[3] Blend / Unblend")
    pattern = ["KO", "KO", "AV", "RU", "CA", "UM", "DR"]
    pairs = xt.blend(pattern, payload)
    un = xt.unblend(pattern, pairs)
    check("blend/unblend round-trip", un == payload)
    check("blend pairs count matches payload", len(pairs) == len(payload))

    # --- GeoSeal ---
    print(f"[4] GeoSeal Encrypt / Decrypt (PQC: {'REAL ML-KEM-768 + ML-DSA-65' if pqc_available() else 'mocked'})")
    ctx = [0.2, -0.3, 0.7, 1.0, -2.0, 0.5, 3.1, -9.9, 0.0]
    pt = b"hello aethermoore"
    pt_b64 = base64.b64encode(pt).decode()

    # Always use keygen so real and mock modes follow the same interface contract.
    kem_pk, kem_sk = kem_keygen()
    dsa_pk, dsa_sk = dsa_keygen()
    kem_pk_b64 = base64.b64encode(kem_pk).decode()
    kem_sk_b64 = base64.b64encode(kem_sk).decode()
    dsa_pk_b64 = base64.b64encode(dsa_pk).decode()
    dsa_sk_b64 = base64.b64encode(dsa_sk).decode()

    env = geoseal_encrypt(pt_b64, ctx, kem_pk_b64, dsa_sk_b64)
    check("envelope has ct_k", "ct_k" in env)
    check("envelope has ct_spec", "ct_spec" in env)
    check("envelope has attest", "attest" in env)
    check("envelope has sig", "sig" in env)
    check("attest has ring policy", "ring" in env["attest"])

    ok, decpt = geoseal_decrypt(env, ctx, kem_sk_b64, dsa_pk_b64)
    check("GeoSeal decrypt succeeds", ok)
    check("GeoSeal round-trip payload", decpt == pt)

    # Tampered envelope should fail
    tampered = dict(env)
    tampered["sig"] = base64.b64encode(b"bad-sig-xxxxxxxxxxxxxxxxxxxxxxxxxxxx").decode()
    ok_bad, _ = geoseal_decrypt(tampered, ctx, kem_sk_b64, dsa_pk_b64)
    check("GeoSeal rejects tampered sig", not ok_bad)

    # --- Concentric Ring Policy ---
    print("[5] Concentric Ring Policy")
    policy = ConcentricRingPolicy()
    check("r=0.1 -> core", policy.classify(0.1)["ring"] == "core")
    check("r=0.4 -> inner", policy.classify(0.4)["ring"] == "inner")
    check("r=0.6 -> middle", policy.classify(0.6)["ring"] == "middle")
    check("r=0.8 -> outer", policy.classify(0.8)["ring"] == "outer")
    check("r=0.95 -> edge", policy.classify(0.95)["ring"] == "edge")
    check("r=1.5 -> beyond/REJECT", policy.classify(1.5).get("action") == "REJECT")

    # --- EvolvingLexicons ---
    print("[6] EvolvingLexicons")
    evo = EvolvingLexicons(mutation_rate=1.0, drift_strength=0.1)
    small_payload = os.urandom(64)
    # Force mutations by setting mutation_rate=1.0 and coherence=1.0
    mutations = 0
    for _ in range(20):
        result = evo.evolve_after_use("KO", "AV", small_payload, coherence=1.0)
        if result is not None:
            mutations += 1
    check("EvolvingLexicons produced mutations", mutations > 0)
    check("mutation log recorded", len(evo.mutation_log) > 0)

    # Verify bijection is preserved after mutations
    for tg in TONGUES:
        all_tokens = [evo.token_of(tg, b) for b in range(256)]
        check(f"{tg} bijection preserved after evolution", len(set(all_tokens)) == 256)

    # Verify evolved lexicon still round-trips
    for tg in TONGUES:
        toks = [evo.token_of(tg, b) for b in small_payload]
        dec = bytearray()
        for t in toks:
            dec.append(evo.byte_of(tg, t))
        check(f"{tg} round-trip after evolution", bytes(dec) == small_payload)

    # --- SemanticNavigator ---
    if numpy_available():
        print("[7] SemanticNavigator (numpy/scipy)")
        nav1 = SemanticNavigator(chaos_strength=0.01)
        nav2 = SemanticNavigator(initial_pos=[0.1, 0.0, 0.0, 0.0, 0.0, 0.0], chaos_strength=0.01)
        check("navigator starts at origin", float(np.linalg.norm(nav1.position)) < 1e-10)
        check("navigator2 starts at custom pos", float(np.linalg.norm(nav2.position)) > 0)

        # Update positions
        pos1 = nav1.update_position(["KO", "AV"], coherence=0.9, dt=0.01)
        pos2 = nav2.update_position(["DR", "CA"], coherence=0.5, dt=0.01)
        check("nav1 position updated", len(nav1.history) == 2)
        check("nav2 position updated", len(nav2.history) == 2)
        check("nav1 inside Poincare ball", float(np.linalg.norm(pos1)) < 1.0)
        check("nav2 inside Poincare ball", float(np.linalg.norm(pos2)) < 1.0)

        # Distance
        d = nav1.distance_to(nav2)
        check("inter-agent distance non-negative", d >= 0)
        check("self-distance near zero", nav1.distance_to(nav1) < 1e-6)

        # Trajectory export
        traj = nav1.export_trajectory()
        check("trajectory shape correct", traj.shape == (2, 6))
    else:
        print("[7] SemanticNavigator (SKIPPED — numpy/scipy not available)")

    # --- Error Handling ---
    print("[8] Error Handling")
    bad_tokens = tok.encode_bytes("KO", b"\x00\x01")
    bad_tokens[1] = bad_tokens[1] + "x"
    try:
        tok.decode_tokens("KO", bad_tokens)
        check("bad token raises KeyError", False)
    except KeyError:
        check("bad token raises KeyError", True)

    # --- Summary ---
    print(f"\n{'=' * 40}")
    if errors == 0:
        print("selftest ok — all checks passed")
    else:
        print(f"selftest FAILED — {errors} check(s) failed")
    return 1 if errors > 0 else 0


# ═══════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════


def build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="six-tongues-cli",
        description="Six Tongues + GeoSeal — SCBE-AETHERMOORE Cryptographic Toolkit",
    )
    sub = p.add_subparsers(dest="cmd")

    pe = sub.add_parser("encode", help="Encode bytes to Sacred Tongue tokens")
    pe.add_argument("--tongue", required=True, choices=TONGUES + [t.lower() for t in TONGUES])
    pe.add_argument("--text", help="Inline text to encode (instead of stdin)")
    pe.add_argument("--lexicons", help="Path to custom lexicon JSON")
    pe.add_argument("--in", dest="infile", help="Input file (default: stdin)")
    pe.add_argument("--out", dest="outfile", help="Output file (default: stdout)")
    pe.set_defaults(func=cmd_encode)

    pd = sub.add_parser("decode", help="Decode Sacred Tongue tokens to bytes")
    pd.add_argument("--tongue", required=True, choices=TONGUES + [t.lower() for t in TONGUES])
    pd.add_argument("--text", help="Inline token string to decode (instead of stdin)")
    pd.add_argument("--as-text", action="store_true", help="Output as UTF-8 text instead of raw bytes")
    pd.add_argument("--lexicons")
    pd.add_argument("--in", dest="infile")
    pd.add_argument("--out", dest="outfile")
    pd.set_defaults(func=cmd_decode)

    px = sub.add_parser("xlate", help="Cross-translate between tongues")
    px.add_argument("--src", required=True, choices=TONGUES + [t.lower() for t in TONGUES])
    px.add_argument("--dst", required=True, choices=TONGUES + [t.lower() for t in TONGUES])
    px.add_argument("--mode", default="byte", choices=["byte", "semantic"])
    px.add_argument("--lexicons")
    px.add_argument("--attest-key", dest="attest_key", help="Base64-encoded HMAC key")
    px.add_argument("--in", dest="infile")
    px.add_argument("--out", dest="outfile")
    px.set_defaults(func=cmd_xlate)

    pb = sub.add_parser("blend", help="Blend multi-tongue stream by pattern")
    pb.add_argument("--pattern", required=True, help="e.g. KO:2,AV:1,DR:1")
    pb.add_argument("--lexicons")
    pb.add_argument("--in", dest="infile")
    pb.add_argument("--out", dest="outfile")
    pb.set_defaults(func=cmd_blend)

    pub = sub.add_parser("unblend", help="Reverse a blended stream")
    pub.add_argument("--lexicons")
    pub.add_argument("--in", dest="infile")
    pub.add_argument("--out", dest="outfile")
    pub.set_defaults(func=cmd_unblend)

    ge = sub.add_parser("geoseal-encrypt", help="GeoSeal context-aware encrypt")
    ge.add_argument("--context", required=True, help="JSON array of context floats")
    ge.add_argument("--kem-key", required=True, help="Base64-encoded KEM public key")
    ge.add_argument("--dsa-key", required=True, help="Base64-encoded DSA secret key")
    ge.add_argument("--plaintext-b64", help="Base64-encoded plaintext (default: stdin)")
    ge.set_defaults(func=cmd_gencore)

    gd = sub.add_parser("geoseal-decrypt", help="GeoSeal context-aware decrypt")
    gd.add_argument("--context", required=True, help="JSON array of context floats")
    gd.add_argument("--kem-key", required=True, help="Base64-encoded KEM secret key")
    gd.add_argument("--dsa-pk", required=True, help="Base64-encoded DSA public key")
    gd.add_argument("--env", help="Envelope JSON file (default: stdin)")
    gd.set_defaults(func=cmd_gendec)

    st = sub.add_parser("selftest", help="Run built-in self-test suite")
    st.set_defaults(func=lambda _args: selftest())

    return p


if __name__ == "__main__":
    # Handle SIGPIPE gracefully (e.g. piping through head/grep)
    import signal
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    cli = build_cli()
    if len(sys.argv) == 1:
        sys.exit(selftest())
    args = cli.parse_args()
    # Normalize tongue codes to uppercase for case-insensitive input
    for attr in ("tongue", "src", "dst"):
        v = getattr(args, attr, None)
        if isinstance(v, str):
            setattr(args, attr, v.upper())
    if not hasattr(args, "func"):
        print("no subcommand specified; running selftest")
        sys.exit(selftest())
    sys.exit(args.func(args) or 0)
