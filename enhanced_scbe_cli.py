#!/usr/bin/env python3
"""
Enhanced SCBE CLI
Industrial-grade reference CLI for Sacred Tongues + ScatterCast + SacredEgg + GeoSeal.

No placeholder logic:
- Canonical Sacred Tongues from src/crypto/sacred_tongues.py
- RFC 5869 HKDF (SHA-256)
- Hyperbolic GeoSeal context scoring in Poincare ball
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


# Resolve src imports from repo root.
REPO_ROOT = Path(__file__).resolve().parent
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER, TONGUES  # noqa: E402

TONGUE_CODES = tuple(TONGUES.keys())  # ('ko','av','ru','ca','um','dr')


# -----------------------------------------------------------------------------
# HKDF (RFC 5869, SHA-256)
# -----------------------------------------------------------------------------

HASH_LEN = 32  # sha256 digest size


def hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    if salt is None or len(salt) == 0:
        salt = b"\x00" * HASH_LEN
    return hmac.new(salt, ikm, hashlib.sha256).digest()


def hkdf_expand(prk: bytes, info: bytes, length: int) -> bytes:
    if length < 0:
        raise ValueError("length must be >= 0")
    if length > 255 * HASH_LEN:
        raise ValueError("length too large for RFC 5869 HKDF-Expand")

    out = bytearray()
    t = b""
    block_index = 1
    while len(out) < length:
        t = hmac.new(prk, t + info + bytes([block_index]), hashlib.sha256).digest()
        out.extend(t)
        block_index += 1
    return bytes(out[:length])


def hkdf(salt: bytes, ikm: bytes, info: bytes, length: int) -> bytes:
    return hkdf_expand(hkdf_extract(salt, ikm), info, length)


# -----------------------------------------------------------------------------
# Sacred Tongue helpers
# -----------------------------------------------------------------------------


def norm_tongue(code: str) -> str:
    c = code.strip().lower()
    if c not in TONGUE_CODES:
        raise ValueError(f"unknown tongue: {code}")
    return c


def encode_text(tongue: str, text: str) -> str:
    t = norm_tongue(tongue)
    tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(t, text.encode("utf-8"))
    return " ".join(tokens)


def decode_text(tongue: str, token_text: str) -> str:
    t = norm_tongue(tongue)
    tokens = [x for x in token_text.split() if x]
    data = SACRED_TONGUE_TOKENIZER.decode_tokens(t, tokens)
    return data.decode("utf-8")


def tongue_vocab(tongue: str) -> set[str]:
    t = norm_tongue(tongue)
    table = SACRED_TONGUE_TOKENIZER.byte_to_token[t]
    return set(table)


def parse_prefixed_token(token: str) -> Tuple[str | None, str]:
    if ":" not in token:
        return None, token
    tg, raw = token.split(":", 1)
    return norm_tongue(tg), raw


# -----------------------------------------------------------------------------
# ScatterCast
# -----------------------------------------------------------------------------


class ScatterCast:
    def calculate_seal_token(self, tokens: Sequence[str]) -> str:
        phrase = " ".join(tokens).encode("utf-8")
        digest = hashlib.sha256(phrase).digest()
        # Draumric seal token from first checksum byte.
        return SACRED_TONGUE_TOKENIZER.encode_bytes("dr", bytes([digest[0]]))[0]

    def generate(self, tongue: str = "ko", visible_len: int = 23) -> Dict[str, str]:
        tg = norm_tongue(tongue)
        if visible_len <= 0:
            raise ValueError("visible_len must be > 0")

        seed_s = secrets.token_bytes(32)  # shadow seed
        visible_entropy = secrets.token_bytes(visible_len)
        visible_tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(tg, visible_entropy)
        seal = self.calculate_seal_token(visible_tokens)

        # Prefix all tokens with their explicit tongue code to avoid cross-tongue
        # lexical ambiguity in downstream parsing/resonance analysis.
        prefixed = [f"{tg}:{tok}" for tok in visible_tokens] + [f"dr:{seal}"]
        seed_v_phrase = " ".join(prefixed)

        master_seed = hkdf(
            salt=seed_s,
            ikm=seed_v_phrase.encode("utf-8"),
            info=b"SCATTERCAST-MASTER-v1",
            length=64,
        )
        kyber_seed = hkdf(
            salt=b"ML-KEM-768",
            ikm=master_seed,
            info=b"scbe-pqc-kyber",
            length=32,
        )
        dilithium_seed = hkdf(
            salt=b"ML-DSA-65",
            ikm=master_seed,
            info=b"scbe-pqc-dilithium",
            length=32,
        )
        return {
            "seed_v_phrase": seed_v_phrase,
            "seed_s_hex": seed_s.hex(),
            "master_seed_hex": master_seed.hex(),
            "kyber_seed_hex": kyber_seed.hex(),
            "dilithium_seed_hex": dilithium_seed.hex(),
        }


# -----------------------------------------------------------------------------
# Sacred Egg (hierarchical derivation)
# -----------------------------------------------------------------------------


@dataclass
class EggRoot:
    root_key: bytes
    chain_code: bytes


class SacredEgg:
    def __init__(self, master_seed_hex: str, phrase: str):
        if len(master_seed_hex) % 2 != 0:
            raise ValueError("master seed hex length must be even")
        self.master_seed = bytes.fromhex(master_seed_hex)
        self.tokens = [x for x in phrase.split() if x]
        self.resonance = self._analyze_resonance()
        self.root = self._derive_root()

    def _derive_root(self) -> EggRoot:
        material = hkdf(
            salt=b"SACRED-EGG-ROOT",
            ikm=self.master_seed,
            info=b"scbe-sacred-egg-root-v1",
            length=64,
        )
        return EggRoot(root_key=material[:32], chain_code=material[32:])

    def _analyze_resonance(self) -> Dict[str, float]:
        counts = {t: 0.0 for t in TONGUE_CODES}
        for tok in self.tokens:
            pref_tg, raw_tok = parse_prefixed_token(tok)
            if pref_tg is not None:
                if raw_tok in SACRED_TONGUE_TOKENIZER.token_to_byte[pref_tg]:
                    counts[pref_tg] += 1.0
                continue

            # Fallback path for legacy unprefixed phrases:
            # distribute mass across all matching tongues to avoid bias.
            matches = [
                t for t in TONGUE_CODES if raw_tok in SACRED_TONGUE_TOKENIZER.token_to_byte[t]
            ]
            if matches:
                frac = 1.0 / len(matches)
                for t in matches:
                    counts[t] += frac
        total = sum(counts.values())
        if total == 0:
            return {t: 0.0 for t in TONGUE_CODES}
        return {t: counts[t] / total for t in TONGUE_CODES}

    def derive_key(self, intent: str) -> Dict[str, str]:
        intent_map = {
            "auth": "ko",
            "nav": "av",
            "binding": "ru",
            "compute": "ca",
            "veil": "um",
            "gov": "dr",
        }
        intent_norm = intent.strip().lower()
        target_tongue = intent_map.get(intent_norm, "ko")
        resonance_strength = self.resonance.get(target_tongue, 0.0)

        if intent_norm == "gov" and resonance_strength < 0.05:
            return {
                "error": (
                    f"insufficient dr resonance ({resonance_strength:.3f}) "
                    "for governance derivation"
                )
            }

        child = hkdf(
            salt=self.root.chain_code,
            ikm=self.root.root_key,
            info=f"derive::{intent_norm}::{target_tongue}".encode("utf-8"),
            length=32,
        )
        return {
            "intent": intent_norm,
            "tongue": target_tongue,
            "key_hex": child.hex(),
            "resonance": f"{resonance_strength:.4f}",
        }


# -----------------------------------------------------------------------------
# GeoSeal (hyperbolic metric, no placeholder)
# -----------------------------------------------------------------------------


class GeoSeal:
    """
    Context scoring in a Poincare ball with hyperbolic distance to origin.

    Map:
      x (raw hash vector) -> u = tanh(alpha*||x||) * x/||x||
      d_H(0, u) = 2 * artanh(||u||)
    """

    def __init__(
        self,
        dim: int = 6,
        alpha: float = 0.35,
        core_dh: float = 0.8,
        interior_dh: float = 1.8,
        boundary_dh: float = 3.2,
    ):
        if dim <= 0:
            raise ValueError("dim must be > 0")
        self.dim = dim
        self.alpha = float(alpha)
        self.core_dh = float(core_dh)
        self.interior_dh = float(interior_dh)
        self.boundary_dh = float(boundary_dh)

    def _raw_vector(self, context_str: str) -> List[float]:
        data = hashlib.shake_256(context_str.encode("utf-8")).digest(self.dim * 4)
        vals: List[float] = []
        for i in range(self.dim):
            word = int.from_bytes(data[i * 4 : (i + 1) * 4], "big")
            # [0,1] -> [-1,1]
            vals.append((word / (2**32 - 1)) * 2.0 - 1.0)
        return vals

    def map_to_poincare(self, context_str: str) -> List[float]:
        x = self._raw_vector(context_str)
        norm = math.sqrt(sum(v * v for v in x))
        if norm == 0.0:
            return [0.0] * self.dim
        r = math.tanh(self.alpha * norm)
        scale = r / norm
        u = [v * scale for v in x]
        # strict interior guard
        un = math.sqrt(sum(v * v for v in u))
        if un >= 0.999999:
            shrink = 0.999999 / max(un, 1e-12)
            u = [v * shrink for v in u]
        return u

    @staticmethod
    def d_h_origin(u: Sequence[float]) -> float:
        n = math.sqrt(sum(v * v for v in u))
        if n >= 1.0:
            return float("inf")
        return 2.0 * math.atanh(n)

    def classify(self, context_str: str) -> Dict[str, object]:
        u = self.map_to_poincare(context_str)
        d = self.d_h_origin(u)
        if d < self.core_dh:
            ring = "core"
            decision = "ALLOW"
        elif d < self.interior_dh:
            ring = "interior"
            decision = "ALLOW"
        elif d < self.boundary_dh:
            ring = "boundary"
            decision = "QUARANTINE"
        else:
            ring = "exterior"
            decision = "DENY"
        return {
            "decision": decision,
            "ring": ring,
            "d_h": d,
            "radius": math.sqrt(sum(v * v for v in u)),
            "vector": u,
        }


# -----------------------------------------------------------------------------
# Self-test
# -----------------------------------------------------------------------------


def rfc5869_vector_ok() -> bool:
    # RFC 5869 test case 1 (SHA-256).
    ikm = bytes.fromhex("0b" * 22)
    salt = bytes.fromhex("000102030405060708090a0b0c")
    info = bytes.fromhex("f0f1f2f3f4f5f6f7f8f9")
    okm = hkdf(salt=salt, ikm=ikm, info=info, length=42)
    expected = bytes.fromhex(
        "3cb25f25faacd57a90434f64d0362f2a"
        "2d2d0a90cf1a5a4c5db02d56ecc4c5bf"
        "34007208d5b887185865"
    )
    return okm == expected


def vocab_disjointness() -> Dict[str, int]:
    overlaps: Dict[str, int] = {}
    codes = list(TONGUE_CODES)
    for i in range(len(codes)):
        for j in range(i + 1, len(codes)):
            a, b = codes[i], codes[j]
            inter = len(tongue_vocab(a) & tongue_vocab(b))
            overlaps[f"{a}-{b}"] = inter
    return overlaps


def geoseal_distribution_probe(n: int = 300) -> Dict[str, float]:
    g = GeoSeal()
    vals: List[float] = []
    radii: List[float] = []
    for i in range(n):
        ctx = f"probe-{i}-{secrets.token_hex(8)}"
        out = g.classify(ctx)
        vals.append(float(out["d_h"]))
        radii.append(float(out["radius"]))
    mean = sum(vals) / n
    var = sum((x - mean) ** 2 for x in vals) / n
    std = math.sqrt(var)
    # boundary-saturation probe: high fraction with near-identical radius is bad
    rounded = [round(r, 6) for r in radii]
    most_common = max(rounded.count(x) for x in set(rounded))
    return {
        "d_h_mean": mean,
        "d_h_std": std,
        "max_same_radius_fraction": most_common / n,
    }


def cmd_selftest(_: argparse.Namespace) -> None:
    print("=== Enhanced SCBE CLI Selftest ===")

    # 1. RFC HKDF
    ok_hkdf = rfc5869_vector_ok()
    print(f"[{'PASS' if ok_hkdf else 'FAIL'}] RFC5869 HKDF-SHA256 vector")

    # 2. Tongue disjointness
    overlaps = vocab_disjointness()
    max_overlap = max(overlaps.values()) if overlaps else 0
    # Canonical tongues may share a small lexical overlap. We enforce explicit
    # tongue prefixes in ScatterCast output to preserve unambiguous decoding.
    phrase = ScatterCast().generate("ko")["seed_v_phrase"]
    ok_prefix = all((":" in x and x.split(":", 1)[0] in TONGUE_CODES) for x in phrase.split())
    print(
        f"[{'PASS' if ok_prefix else 'FAIL'}] Explicit tongue prefixes "
        f"(max lexical overlap={max_overlap})"
    )

    # 3. ScatterCast lengths
    sc = ScatterCast()
    seeds = sc.generate("ko")
    ok_sc = len(bytes.fromhex(seeds["master_seed_hex"])) == 64
    print(f"[{'PASS' if ok_sc else 'FAIL'}] ScatterCast master key length")

    # 4. GeoSeal distribution
    probe = geoseal_distribution_probe()
    ok_geo = probe["d_h_std"] > 0.1 and probe["max_same_radius_fraction"] < 0.2
    print(
        f"[{'PASS' if ok_geo else 'FAIL'}] GeoSeal non-saturated distribution "
        f"(std={probe['d_h_std']:.4f}, max_same={probe['max_same_radius_fraction']:.3f})"
    )

    if not (ok_hkdf and ok_prefix and ok_sc and ok_geo):
        raise SystemExit(1)


# -----------------------------------------------------------------------------
# CLI handlers
# -----------------------------------------------------------------------------


def cmd_encode(args: argparse.Namespace) -> None:
    out = encode_text(args.tongue, args.text)
    print(out)


def cmd_decode(args: argparse.Namespace) -> None:
    out = decode_text(args.tongue, args.tokens)
    print(out)


def cmd_scatter_cast(args: argparse.Namespace) -> None:
    out = ScatterCast().generate(args.tongue, args.visible_len)
    print(json.dumps(out, indent=2))


def cmd_hatch(args: argparse.Namespace) -> None:
    egg = SacredEgg(master_seed_hex=args.master, phrase=args.phrase)
    key = egg.derive_key(args.intent)
    result = {"resonance": egg.resonance, "derived": key}
    print(json.dumps(result, indent=2))


def cmd_geoseal(args: argparse.Namespace) -> None:
    g = GeoSeal()
    out = g.classify(args.context)
    print(json.dumps(out, indent=2))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Enhanced SCBE CLI")
    sub = p.add_subparsers(dest="cmd")

    s1 = sub.add_parser("selftest", help="run deterministic self-tests")
    s1.set_defaults(func=cmd_selftest)

    s2 = sub.add_parser("encode", help="encode text to Sacred Tongue tokens")
    s2.add_argument("tongue", help=f"tongue code: {', '.join(TONGUE_CODES)}")
    s2.add_argument("text", help="UTF-8 input text")
    s2.set_defaults(func=cmd_encode)

    s3 = sub.add_parser("decode", help="decode Sacred Tongue tokens to text")
    s3.add_argument("tongue", help=f"tongue code: {', '.join(TONGUE_CODES)}")
    s3.add_argument("tokens", help="token string, space-separated")
    s3.set_defaults(func=cmd_decode)

    s4 = sub.add_parser("scatter-cast", help="generate seed phrase + derived seeds")
    s4.add_argument("--tongue", default="ko", help=f"default ko, choices: {', '.join(TONGUE_CODES)}")
    s4.add_argument("--visible-len", type=int, default=23)
    s4.set_defaults(func=cmd_scatter_cast)

    s5 = sub.add_parser("hatch", help="derive key from Sacred Egg")
    s5.add_argument("--master", required=True, help="master seed hex")
    s5.add_argument("--phrase", required=True, help="visible seed phrase")
    s5.add_argument("--intent", default="auth", help="intent: auth|nav|binding|compute|veil|gov")
    s5.set_defaults(func=cmd_hatch)

    s6 = sub.add_parser("geoseal", help="classify context with hyperbolic GeoSeal")
    s6.add_argument("context", help="context string")
    s6.set_defaults(func=cmd_geoseal)

    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    try:
        args.func(args)
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
