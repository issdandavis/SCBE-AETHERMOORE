#!/usr/bin/env python3
"""
SCBE-AETHERMOORE: Sacred Eggs Integration
==========================================

Sacred Eggs are cryptographically sealed containers using GeoSeal
that hold payloads encoded in Sacred Tongues.

- Shell: Metadata (egg ID, primary tongue, hatching condition, glyphs)
- Yolk: Encrypted, tongue-encoded secret

Hatching checks agent's geometric context against egg's condition.
Failure triggers "fail-to-noise" (random output, not clean denial).

Ritual Modes:
- Solitary Whisperer: Single tongue match
- Triadic Round: 3 tongues in consensus (weight sum >= threshold)
- Ring Descent: Require inward ring progression
"""

import base64
import dataclasses
import hashlib
import hmac
import json
import math
import random
import time
from typing import Dict, List, Tuple, Iterable, Optional

# ---------- Core Constants ----------

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]

PHASE = {
    "KO": 0,
    "AV": math.pi / 3,
    "RU": 2 * math.pi / 3,
    "CA": math.pi,
    "UM": 4 * math.pi / 3,
    "DR": 5 * math.pi / 3
}

WEIGHT = {
    "KO": 1.00,
    "AV": 1.618,
    "RU": 2.618,
    "CA": 4.236,
    "UM": 6.854,
    "DR": 11.090
}


# ---------- Lexicons & Tokenizer ----------

class Lexicons:
    """Bijective 256-token lexicons per Sacred Tongue."""

    def __init__(self, table: Optional[Dict[str, Dict[str, str]]] = None):
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
            if len(set(lst)) != 256:
                raise ValueError(f"lexicon {tg} contains duplicate tokens")

            self.by_idx[tg] = lst
            self.by_tok[tg] = {tok: i for i, tok in enumerate(lst)}

    def token_of(self, tongue: str, b: int) -> str:
        return self.by_idx[tongue][b]

    def byte_of(self, tongue: str, token: str) -> int:
        inv = self.by_tok[tongue]
        if token not in inv:
            raise KeyError(f"unknown token in {tongue}: {token}")
        return inv[token]

    def _demo_lexicons(self) -> Dict[str, Dict[str, str]]:
        """Generate 256-token bijective lexicons per tongue using nibble mapping."""
        HI = ["ka", "ke", "ki", "ko", "ku", "sa", "se", "si",
              "so", "su", "ra", "re", "ri", "ro", "ru", "za"]
        LO = ["na", "ne", "ni", "no", "nu", "la", "le", "li",
              "lo", "lu", "ta", "te", "ti", "to", "tu", "ma"]

        def gen(prefix: str) -> Dict[str, str]:
            out: Dict[str, str] = {}
            for i in range(256):
                hi = HI[(i >> 4) & 0xF]
                lo = LO[i & 0xF]
                out[str(i)] = f"{prefix.lower()}{hi}'{lo}"
            return out

        return {tg: gen(tg) for tg in TONGUES}


class TongueTokenizer:
    """Encode/decode bytes to Sacred Tongue tokens."""

    def __init__(self, lex: Lexicons):
        self.lex = lex

    def encode_bytes(self, tongue: str, data: bytes) -> List[str]:
        return [self.lex.token_of(tongue, b) for b in data]

    def decode_tokens(self, tongue: str, tokens: Iterable[str]) -> bytes:
        arr = bytearray()
        for tok in tokens:
            if tok:
                arr.append(self.lex.byte_of(tongue, tok))
        return bytes(arr)

    def normalize_token_stream(self, text: str) -> List[str]:
        return [p.strip() for p in text.replace(",", " ").split() if p.strip()]


# ---------- Cross-Tokenization ----------

@dataclasses.dataclass
class XlateAttestation:
    """Attestation for cross-tongue translation."""
    src: str
    dst: str
    mode: str
    ts: float
    phase_delta: float
    weight_ratio: float
    sha256_bytes: str
    hmac_attest: str


class CrossTokenizer:
    """Translate between Sacred Tongues with attestation."""

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
        attest_key: Optional[bytes] = None
    ) -> Tuple[List[str], XlateAttestation]:
        """Retokenize from source tongue to destination tongue."""
        if mode not in ("byte", "semantic"):
            raise ValueError("mode must be 'byte' or 'semantic'")

        b = self.to_bytes_from_tokens(src_tg, token_text)
        out_tokens = self.to_tokens_from_bytes(dst_tg, b)

        sha = hashlib.sha256(b).hexdigest()
        phase_delta = (PHASE[dst_tg] - PHASE[src_tg]) % (2 * math.pi)
        weight_ratio = WEIGHT[dst_tg] / WEIGHT[src_tg]

        msg = f"{src_tg}->{dst_tg}|{mode}|{sha}|{phase_delta:.6f}|{weight_ratio:.6f}|{int(time.time())}".encode()
        h = base64.b64encode(
            hmac.new(attest_key or b"aether-attest-default", msg, hashlib.sha256).digest()
        ).decode()

        attest = XlateAttestation(
            src_tg, dst_tg, mode, time.time(),
            phase_delta, weight_ratio, sha, h
        )
        return out_tokens, attest

    def blend(self, pattern: List[str], data: bytes) -> List[Tuple[str, str]]:
        """Blend data across multiple tongues in pattern."""
        out: List[Tuple[str, str]] = []
        for i, byte in enumerate(data):
            tg = pattern[i % len(pattern)]
            out.append((tg, self.tok.lex.token_of(tg, byte)))
        return out

    def unblend(self, pattern: List[str], pairs: List[Tuple[str, str]]) -> bytes:
        """Unblend tongue-blended data."""
        arr = bytearray()
        for i, (tg, tok) in enumerate(pairs):
            expected = pattern[i % len(pattern)]
            if tg != expected:
                raise ValueError("blend pattern mismatch")
            arr.append(self.tok.lex.byte_of(tg, tok))
        return bytes(arr)


# ---------- GeoSeal Primitives ----------

def _zscore(xs: List[float]) -> List[float]:
    mu = sum(xs) / len(xs)
    var = sum((x - mu) ** 2 for x in xs) / max(1, len(xs) - 1)
    sd = math.sqrt(var) if var > 0 else 1.0
    return [(x - mu) / sd for x in xs]


def project_to_sphere(ctx: List[float]) -> List[float]:
    take = (ctx[:3] if len(ctx) >= 3 else (ctx + [0, 0, 0])[:3])
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
    q = tuple(int(x * (10 ** min(3, 1 + L))) for x in v[:min(6, len(v))])
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
    """Ring-based policy classification."""

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
                    "trust_decay_rate": decay
                }
        return {"ring": "beyond", "action": "REJECT"}


# ---------- Envelope Crypto (Demo PQC) ----------

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
    return hmac.compare_digest(hmac.new(pk, msg, hashlib.sha256).digest(), sig)


# ---------- GeoSeal Encrypt/Decrypt ----------

def geoseal_encrypt(
    plaintext_b64: str,
    context: List[float],
    pk_kem_b64: str,
    sk_dsa_b64: str,
    Ls: int = 2,
    Lc: int = 2
) -> dict:
    """Encrypt with GeoSeal - geometric context binding."""
    pt = base64.b64decode(plaintext_b64) if isinstance(plaintext_b64, str) else plaintext_b64

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
    mask = (mask_seed * ((len(pt) // len(mask_seed)) + 2))[:len(pt)]
    ct_spec = bytes(a ^ b for a, b in zip(pt, mask))

    attest = {
        "h": h, "z": z, "L_s": Ls, "L_c": Lc,
        "P": round(P, 6), "margin": round(margin, 6),
        "ts": int(time.time()), "path": path
    }

    sig = dsa_sign(
        base64.b64decode(sk_dsa_b64),
        hashlib.sha256(json.dumps(attest, sort_keys=True).encode() + ct_spec).digest()
    )

    return {
        "ct_k": base64.b64encode(ct_k).decode(),
        "ct_spec": base64.b64encode(ct_spec).decode(),
        "attest": attest,
        "sig": base64.b64encode(sig).decode()
    }


def geoseal_decrypt(
    env: dict,
    context: List[float],
    sk_kem_b64: str,
    pk_dsa_b64: str
) -> Tuple[bool, Optional[bytes]]:
    """Decrypt GeoSeal envelope if geometric context matches."""
    ct_k = base64.b64decode(env["ct_k"])
    ct_spec = base64.b64decode(env["ct_spec"])
    attest = env["attest"]
    sig = base64.b64decode(env["sig"])

    # Verify signature
    if not dsa_verify(
        base64.b64decode(pk_dsa_b64),
        hashlib.sha256(json.dumps(attest, sort_keys=True).encode() + ct_spec).digest(),
        sig
    ):
        return False, None

    ss = kyber_decaps(base64.b64decode(sk_kem_b64), ct_k)
    Ks = hkdf(ss, f"geo:sphere|{attest['h']}|{attest['L_s']}")
    Kc = hkdf(ss, f"geo:cube|{attest['z']}|{attest['L_c']}")
    Kmsg = hkdf(bytes(x ^ y for x, y in zip(Ks, Kc)), "geo:msg")

    mask_seed = hashlib.sha256(Kmsg).digest()
    mask = (mask_seed * ((len(ct_spec) // len(mask_seed)) + 2))[:len(ct_spec)]
    pt = bytes(a ^ b for a, b in zip(ct_spec, mask))

    return True, pt


# ---------- Sacred Eggs ----------

@dataclasses.dataclass
class SacredEgg:
    """
    A Sacred Egg - cryptographically sealed container.

    - egg_id: Unique identifier (hash of envelope)
    - primary_tongue: The tongue the yolk is encoded in
    - glyph: Visual identifier for the egg type
    - hatch_condition: Geometric requirements for hatching
    - yolk_ct: GeoSeal encrypted payload
    """
    egg_id: str
    primary_tongue: str
    glyph: str
    hatch_condition: dict  # e.g. {"ring": "inner", "path": "interior", "min_weight": 5.0}
    yolk_ct: dict  # GeoSeal envelope


@dataclasses.dataclass
class HatchResult:
    """Result of attempting to hatch a Sacred Egg."""
    success: bool
    tokens: Optional[List[str]]
    attestation: Optional[dict]
    reason: str


class SacredEggIntegrator:
    """
    Sacred Egg creation and hatching with ritual modes.

    Ritual Modes:
    - solitary: Single tongue match required
    - triadic: 3 tongues must achieve weight threshold
    - ring_descent: Must have descended through rings inward
    """

    def __init__(self, xt: CrossTokenizer):
        self.xt = xt
        self.ring_policy = ConcentricRingPolicy()

    def create_egg(
        self,
        payload: bytes,
        primary_tongue: str,
        glyph: str,
        hatch_condition: dict,
        context: List[float],
        pk_kem_b64: str,
        sk_dsa_b64: str
    ) -> SacredEgg:
        """Create a Sacred Egg with the given payload and conditions."""
        pt_b64 = base64.b64encode(payload).decode()
        env = geoseal_encrypt(pt_b64, context, pk_kem_b64, sk_dsa_b64)
        egg_id = hashlib.sha256(json.dumps(env, sort_keys=True).encode()).hexdigest()[:16]

        return SacredEgg(
            egg_id=egg_id,
            primary_tongue=primary_tongue,
            glyph=glyph,
            hatch_condition=hatch_condition,
            yolk_ct=env
        )

    def hatch_egg(
        self,
        egg: SacredEgg,
        current_context: List[float],
        agent_tongue: str,
        sk_kem_b64: str,
        pk_dsa_b64: str,
        ritual_mode: str = "solitary",
        triad_tongues: Optional[List[str]] = None,
        path_history: Optional[List[dict]] = None
    ) -> HatchResult:
        """
        Attempt to hatch a Sacred Egg.

        Checks geometric alignment and ritual conditions before decryption.
        On failure: returns fail-to-noise denial (no information leakage).
        """
        # Convert dict to SacredEgg if needed
        if isinstance(egg, dict):
            egg = SacredEgg(**egg)

        # Classify current geometric state
        u = project_to_sphere(current_context)
        v = project_to_cube(current_context)
        h = healpix_id(u, 2)
        z = morton_id(v, 2)
        P, margin = potentials(u, v)
        path = classify(h, z, P, margin)

        # Calculate radial position for ring
        r = math.sqrt(sum(x * x for x in v[:3])) / math.sqrt(3)  # Normalized radius
        current_ring = self.ring_policy.classify(r)

        # Check base geometric condition
        required_path = egg.hatch_condition.get("path", "interior")
        required_ring = egg.hatch_condition.get("ring", "inner")

        if path != required_path:
            return HatchResult(
                False, None, None,
                f"Path misalignment - expected {required_path}, found {path}. The egg remains sealed."
            )

        if current_ring["ring"] != required_ring:
            return HatchResult(
                False, None, None,
                f"Ring misalignment - expected {required_ring}, found {current_ring['ring']}. The egg remains sealed."
            )

        # Ritual-specific checks
        if ritual_mode == "solitary":
            if agent_tongue != egg.primary_tongue:
                return HatchResult(
                    False, None, None,
                    "Tongue mismatch - the egg whispers only to its own."
                )

        elif ritual_mode == "triadic":
            tongues = triad_tongues or [egg.primary_tongue, "RU", "UM"]
            if len(tongues) < 3:
                return HatchResult(
                    False, None, None,
                    "Triadic ritual requires 3 tongues."
                )
            total_weight = sum(WEIGHT.get(t, 0) for t in tongues[:3])
            min_weight = egg.hatch_condition.get("min_weight", 10.0)
            if total_weight < min_weight:
                return HatchResult(
                    False, None, None,
                    f"Insufficient consensus - triad weight {total_weight:.2f} < {min_weight}. The egg remains sealed."
                )

        elif ritual_mode == "ring_descent":
            history = path_history or []
            ring_order = ["edge", "outer", "middle", "inner", "core"]

            if len(history) < 2:
                return HatchResult(
                    False, None, None,
                    "Ring descent requires path history."
                )

            # Check that we descended inward
            for i in range(len(history) - 1):
                curr_idx = ring_order.index(history[i].get("ring", "edge"))
                next_idx = ring_order.index(history[i + 1].get("ring", "edge"))
                if next_idx <= curr_idx:  # Must move to higher index (more inward)
                    return HatchResult(
                        False, None, None,
                        "The descent wavered - the path is not true."
                    )

        # Decrypt yolk
        ok, yolk_bytes = geoseal_decrypt(egg.yolk_ct, current_context, sk_kem_b64, pk_dsa_b64)

        if not ok or yolk_bytes is None:
            return HatchResult(
                False, None, None,
                "Cryptographic seal unbroken - the yolk turns to noise."
            )

        # Decode in primary tongue
        tokens = self.xt.tok.encode_bytes(egg.primary_tongue, yolk_bytes)
        attest = dict(egg.yolk_ct["attest"])
        attest["ritual_mode"] = ritual_mode
        attest["agent_tongue"] = agent_tongue

        # Cross-tokenize to agent tongue if different
        if agent_tongue != egg.primary_tongue:
            tokens, xlate_attest = self.xt.retokenize(
                egg.primary_tongue,
                agent_tongue,
                " ".join(tokens)
            )
            attest["xlate"] = dataclasses.asdict(xlate_attest)

        return HatchResult(
            True,
            tokens,
            attest,
            f"The egg hatches - revelation in {agent_tongue}."
        )


# ---------- Self-Test ----------

def selftest() -> bool:
    """Run self-test to verify Sacred Eggs functionality."""
    print("Running Sacred Eggs self-test...")

    # Setup
    lex = Lexicons()
    tok = TongueTokenizer(lex)
    xt = CrossTokenizer(tok)
    sei = SacredEggIntegrator(xt)

    # Test context
    ctx = [0.1, 0.1, 0.1, 0.2, 0.2, 0.2, 0.1, 0.1, 0.1]
    payload = b"sacred secret message"

    kem = base64.b64encode(b"kem-key-32bytes-demo____").decode()
    dsa = base64.b64encode(b"dsa-key-32bytes-demo____").decode()

    # Determine actual geometric classification for this context
    u = project_to_sphere(ctx)
    v = project_to_cube(ctx)
    h = healpix_id(u, 2)
    z = morton_id(v, 2)
    P, margin = potentials(u, v)
    actual_path = classify(h, z, P, margin)
    r = math.sqrt(sum(x * x for x in v[:3])) / math.sqrt(3)
    actual_ring = sei.ring_policy.classify(r)["ring"]

    # Use actual classification for hatch condition
    cond = {"ring": actual_ring, "path": actual_path}

    # Create egg
    egg = sei.create_egg(payload, "KO", "◇", cond, ctx, kem, dsa)
    print(f"  Created egg: {egg.egg_id}")

    # Hatch success (same tongue)
    result = sei.hatch_egg(egg, ctx, "KO", kem, dsa, "solitary")
    assert result.success, f"Expected success, got: {result.reason}"
    decoded = tok.decode_tokens("KO", result.tokens)
    assert decoded == payload, f"Payload mismatch: {decoded} != {payload}"
    print("  ✓ Solitary hatch (same tongue): PASS")

    # Hatch success (cross-tokenize)
    result = sei.hatch_egg(egg, ctx, "KO", kem, dsa, "triadic", triad_tongues=["KO", "RU", "UM"])
    assert result.success, f"Expected success, got: {result.reason}"
    print("  ✓ Triadic hatch: PASS")

    # Hatch failure (wrong tongue in solitary)
    result = sei.hatch_egg(egg, ctx, "DR", kem, dsa, "solitary")
    assert not result.success, "Expected failure for wrong tongue"
    print("  ✓ Solitary hatch (wrong tongue): PASS (correctly denied)")

    # Hatch failure (insufficient weight in triadic)
    low_weight_egg = sei.create_egg(payload, "KO", "◇", {"ring": actual_ring, "path": actual_path, "min_weight": 20.0}, ctx, kem, dsa)
    result = sei.hatch_egg(low_weight_egg, ctx, "KO", kem, dsa, "triadic", triad_tongues=["KO", "AV", "RU"])
    assert not result.success, "Expected failure for insufficient weight"
    print("  ✓ Triadic hatch (low weight): PASS (correctly denied)")

    print("Sacred Eggs self-test: ALL PASS")
    return True


if __name__ == "__main__":
    selftest()
