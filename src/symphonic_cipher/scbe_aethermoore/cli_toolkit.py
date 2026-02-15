#!/usr/bin/env python3
"""
Aethermoore Suite CLI — GeoSeal + SCBE + Six-Tongue Toolkit

Unified command-line tool for:
  - encode/decode: Sacred Tongue bijective byte encoding
  - xlate: Cross-tongue retokenization with HMAC attestation
  - blend/unblend: Multi-tongue stripe encoding
  - geoseal-encrypt/decrypt: Context-bound envelope encryption

Run without args for selftest.

Usage:
  python cli_toolkit.py                     # selftest
  python cli_toolkit.py encode --tongue KO  # encode stdin
  python cli_toolkit.py xlate --src KO --dst AV  # cross-tongue
"""

import argparse
import base64
import dataclasses
import hashlib
import hmac
import json
import math
import os
import sys
import time
from typing import Dict, List, Tuple, Iterable

# ---------- Core lexicon & tokenizer ----------

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]

# Token normalization: make decoding resilient across case differences and common
# unicode apostrophes that may appear when copying tokens from docs or chat.
_SMART_APOSTROPHES = {
    "\u2019": "'",  # right single quotation mark
    "\u2018": "'",  # left single quotation mark
    "\u201b": "'",  # single high-reversed-9 quotation mark
    "`": "'",       # grave accent
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
            table = self._demo_lexicons()
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
            raise KeyError(
                f"unknown token in {tongue}: {token!r} (canonical: {key!r})"
            )
        return inv[key]

    def _demo_lexicons(self) -> Dict[str, Dict[str, str]]:
        """256-token bijective generator per tongue using nibble mapping (16x16)."""
        HI = [
            "ka", "ke", "ki", "ko", "ku", "sa", "se", "si",
            "so", "su", "ra", "re", "ri", "ro", "ru", "za",
        ]
        LO = [
            "na", "ne", "ni", "no", "nu", "la", "le", "li",
            "lo", "lu", "ta", "te", "ti", "to", "tu", "ma",
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

    def blend(
        self, pattern: List[str], data: bytes
    ) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        for i, byte in enumerate(data):
            tg = pattern[i % len(pattern)]
            out.append((tg, self.tok.lex.token_of(tg, byte)))
        return out

    def unblend(
        self, pattern: List[str], pairs: List[Tuple[str, str]]
    ) -> bytes:
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
    arr = [
        (math.tanh(x / 5) + 1) / 2
        for x in (ctx[:m] if len(ctx) >= m else ctx + [0] * (m - len(ctx)))
    ]
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
    return (
        "interior"
        if ("S" in h and "C" in z and P < 0.6 and margin > 0.05)
        else "exterior"
    )


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


def dsa_sign(sk: bytes, msg: bytes) -> bytes:
    return hmac.new(sk, msg, hashlib.sha256).digest()


def dsa_verify(pk: bytes, msg: bytes, sig: bytes) -> bool:
    return hmac.compare_digest(
        hmac.new(pk, msg, hashlib.sha256).digest(), sig
    )


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
        hashlib.sha256(
            json.dumps(attest, sort_keys=True).encode() + ct_spec
        ).digest(),
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
    ct_k = (
        base64.b64decode(env["ct_k"])
        if isinstance(env["ct_k"], str)
        else env["ct_k"]
    )
    ct_spec = (
        base64.b64decode(env["ct_spec"])
        if isinstance(env["ct_spec"], str)
        else env["ct_spec"]
    )
    attest = env["attest"]
    sig = (
        base64.b64decode(env["sig"])
        if isinstance(env["sig"], str)
        else env["sig"]
    )
    if not dsa_verify(
        base64.b64decode(pk_dsa_b64),
        hashlib.sha256(
            json.dumps(attest, sort_keys=True).encode() + ct_spec
        ).digest(),
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
    data = (
        sys.stdin.buffer.read()
        if not args.infile
        else open(args.infile, "rb").read()
    )
    tokens = tok.encode_bytes(args.tongue, data)
    out = (" ".join(tokens) + "\n").encode()
    if not args.outfile:
        sys.stdout.buffer.write(out)
    else:
        open(args.outfile, "wb").write(out)


def cmd_decode(args):
    lex = load_lexicons(args.lexicons)
    tok = TongueTokenizer(lex)
    text = (
        sys.stdin.read()
        if not args.infile
        else open(args.infile, "r", encoding="utf-8").read()
    )
    tokens = tok.normalize_token_stream(text)
    data = tok.decode_tokens(args.tongue, tokens)
    if not args.outfile:
        sys.stdout.buffer.write(data)
    else:
        open(args.outfile, "wb").write(data)


def cmd_xlate(args):
    lex = load_lexicons(args.lexicons)
    tok = TongueTokenizer(lex)
    xt = CrossTokenizer(tok)
    text = (
        sys.stdin.read()
        if not args.infile
        else open(args.infile, "r", encoding="utf-8").read()
    )
    out_tokens, attest = xt.retokenize(
        args.src,
        args.dst,
        text,
        mode=args.mode,
        attest_key=(
            base64.b64decode(args.attest_key) if args.attest_key else None
        ),
    )
    bundle = {
        "tokens": " ".join(out_tokens),
        "attestation": dataclasses.asdict(attest),
    }
    s = json.dumps(bundle, ensure_ascii=False)
    if not args.outfile:
        print(s)
    else:
        open(args.outfile, "w", encoding="utf-8").write(s)


def cmd_blend(args):
    lex = load_lexicons(args.lexicons)
    tok = TongueTokenizer(lex)
    xt = CrossTokenizer(tok)
    data = (
        sys.stdin.buffer.read()
        if not args.infile
        else open(args.infile, "rb").read()
    )
    pattern = []
    for seg in args.pattern.split(","):
        name, count = (
            seg.split(":") if ":" in seg else (seg, "1")
        )
        for _ in range(int(count)):
            pattern.append(name)
    pairs = xt.blend(pattern, data)
    s = json.dumps({"pattern": pattern, "pairs": pairs}, ensure_ascii=False)
    if not args.outfile:
        print(s)
    else:
        open(args.outfile, "w", encoding="utf-8").write(s)


def cmd_unblend(args):
    lex = load_lexicons(args.lexicons)
    tok = TongueTokenizer(lex)
    xt = CrossTokenizer(tok)
    js = json.load(
        sys.stdin
        if not args.infile
        else open(args.infile, "r", encoding="utf-8")
    )
    pattern = js["pattern"]
    pairs = [(tg, t) for tg, t in js["pairs"]]
    data = xt.unblend(pattern, pairs)
    if not args.outfile:
        sys.stdout.buffer.write(data)
    else:
        open(args.outfile, "wb").write(data)


def cmd_gencore(args):
    pt_b64 = (
        sys.stdin.read().strip()
        if args.plaintext_b64 is None
        else args.plaintext_b64
    )
    ctx = json.loads(args.context)
    env = geoseal_encrypt(pt_b64, ctx, args.kem_key, args.dsa_key)
    print(json.dumps(env))


def cmd_gendec(args):
    env = json.load(
        sys.stdin if not args.env else open(args.env, "r")
    )
    ctx = json.loads(args.context)
    ok, pt = geoseal_decrypt(env, ctx, args.kem_key, args.dsa_pk)
    if not ok:
        sys.exit(1)
    sys.stdout.buffer.write(pt)


# ---------- Selftest ----------

def selftest() -> int:
    lex = Lexicons()
    tok = TongueTokenizer(lex)
    xt = CrossTokenizer(tok)
    payload = os.urandom(1024)

    # roundtrip per tongue
    for tg in TONGUES:
        toks = tok.encode_bytes(tg, payload)
        dec = tok.decode_tokens(tg, toks)
        assert dec == payload
        assert len(set(tok.encode_bytes(tg, bytes(range(256))))) == 256

    # decoding robustness: case + smart quotes + punctuation shouldn't break
    for tg in TONGUES:
        toks = tok.encode_bytes(tg, payload)
        noisy = [
            (
                t.upper().replace("'", "\u2019")
                + ("," if i % 7 == 0 else "")
            )
            if i % 2 == 0
            else (
                t.replace("'", "\u02bc")
                + (";" if i % 11 == 0 else "")
            )
            for i, t in enumerate(toks)
        ]
        assert tok.decode_tokens(tg, noisy) == payload
        assert (
            tok.decode_tokens(tg, tok.normalize_token_stream(" ".join(noisy)))
            == payload
        )

    # canonical-collision guard
    try:
        base = Lexicons()._demo_lexicons()
        base["KO"]["0"] = "X"
        base["KO"]["1"] = "x"  # canonical collision
        Lexicons(base)
        raise AssertionError("expected canonical collision to be rejected")
    except ValueError:
        pass

    # cross-retokenize (byte + semantic)
    for s in TONGUES:
        for d in TONGUES:
            ttext = " ".join(tok.encode_bytes(s, payload))
            out_tokens, attest = xt.retokenize(
                s, d, ttext, attest_key=b"k"
            )
            back = tok.decode_tokens(d, out_tokens)
            assert back == payload
            assert isinstance(attest.hmac_attest, str)
            out_tokens2, _ = xt.retokenize(
                s, d, ttext, mode="semantic", attest_key=b"k"
            )
            assert tok.decode_tokens(d, out_tokens2) == payload

    # blend/unblend
    pattern = ["KO", "KO", "AV", "RU", "CA", "UM", "DR"]
    pairs = xt.blend(pattern, payload)
    un = xt.unblend(pattern, pairs)
    assert un == payload

    # geoseal
    ctx = [0.2, -0.3, 0.7, 1.0, -2.0, 0.5, 3.1, -9.9, 0.0]
    pt = b"hello aethermoore"
    pt_b64 = base64.b64encode(pt).decode()
    kem = base64.b64encode(b"kem-key-32bytes-demo____").decode()
    dsa = base64.b64encode(b"dsa-key-32bytes-demo____").decode()
    env = geoseal_encrypt(pt_b64, ctx, kem, dsa)
    ok, decpt = geoseal_decrypt(env, ctx, kem, dsa)
    assert ok and decpt == pt

    # negative: corrupted token should fail reverse map
    bad = tok.encode_bytes("KO", b"\x00\x01")
    bad[1] = bad[1] + "x"
    try:
        tok.decode_tokens("KO", bad)
        raise AssertionError("expected KeyError for bad token")
    except KeyError:
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
    pb.add_argument(
        "--pattern", required=True, help="e.g. KO:2,AV:1,DR:1"
    )
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

    gd = sub.add_parser("geoseal-decrypt")
    gd.add_argument("--context", required=True)
    gd.add_argument("--kem-key", required=True)
    gd.add_argument("--dsa-pk", required=True)
    gd.add_argument("--env")
    gd.set_defaults(func=cmd_gendec)

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
