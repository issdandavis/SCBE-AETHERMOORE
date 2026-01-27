#!/usr/bin/env python3
"""
spiralverse_core.py (stdlib-only)
=================================

Core primitives for SpiralVerse demo:
- Deterministic envelope sealing
- Multi-tongue HMAC signatures (Roundtable quorum)
- Replay protection (nonce cache)
- Fail-to-noise external behavior
- Time-dilation security gate
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import math
import os
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple


# ---------------------------------------------------------------------------
# Helpers: base64url + canonical JSON
# ---------------------------------------------------------------------------

def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def b64url_decode(text: str) -> bytes:
    text = text + "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text.encode("ascii"))


def canonical_json_bytes(obj: Dict[str, Any]) -> bytes:
    """
    Minimal deterministic JSON serialization (demo).
    - sort keys
    - no whitespace
    - UTF-8
    Avoid floats in signed objects unless you define float canonicalization.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def hmac_sha256(key: bytes, msg: bytes) -> bytes:
    return hmac.new(key, msg, hashlib.sha256).digest()


def timing_safe_eq_bytes(a: bytes, b: bytes) -> bool:
    return hmac.compare_digest(a, b)


# ---------------------------------------------------------------------------
# Six Sacred Tongues (labels only for demo)
# ---------------------------------------------------------------------------

TONGUES: Dict[str, str] = {
    "KO": "Aelindra - Control Flow",
    "AV": "Voxmara - Communication",
    "RU": "Thalassic - Context",
    "CA": "Numerith - Math & Logic",
    "UM": "Glyphara - Security & Encryption",
    "DR": "Morphael - Data Types",
}


# ---------------------------------------------------------------------------
# Harmonic complexity (pricing / work factor metaphor)
# ---------------------------------------------------------------------------

def harmonic_complexity(depth: int, ratio: float = 1.5) -> float:
    if depth < 0:
        raise ValueError("depth must be >= 0")
    return ratio ** (depth * depth)


def pricing_tier(depth: int) -> Dict[str, Any]:
    H = harmonic_complexity(depth)
    if H < 2:
        tier = "FREE"
        desc = "Simple single-step tasks"
    elif H < 10:
        tier = "STARTER"
        desc = "Basic workflows"
    elif H < 100:
        tier = "PRO"
        desc = "Advanced multi-step"
    else:
        tier = "ENTERPRISE"
        desc = "Complex orchestration"
    return {"tier": tier, "complexity": H, "description": desc}


# ---------------------------------------------------------------------------
# 6D agent model (stdlib-only)
# ---------------------------------------------------------------------------

@dataclass
class Agent6D:
    name: str
    position: Tuple[float, float, float, float, float, float]
    trust_score: float = 1.0
    last_seen: float = 0.0

    def __post_init__(self) -> None:
        if self.last_seen == 0.0:
            self.last_seen = time.time()

    def distance_to(self, other: "Agent6D") -> float:
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(self.position, other.position)))

    def decay_trust(self, decay_rate: float = 0.01) -> float:
        now = time.time()
        dt = max(0.0, now - self.last_seen)
        self.trust_score *= math.exp(-decay_rate * dt)
        return self.trust_score

    def check_in(self) -> None:
        self.last_seen = time.time()


# ---------------------------------------------------------------------------
# Replay protection: nonce cache with TTL
# ---------------------------------------------------------------------------

class NonceCache:
    def __init__(self, window_ms: int = 60_000) -> None:
        self.window_ms = window_ms
        self._seen: Dict[str, int] = {}

    def _prune(self, now_ms: int) -> None:
        cutoff = now_ms - self.window_ms
        for nonce, ts in list(self._seen.items()):
            if ts < cutoff:
                del self._seen[nonce]

    def check_and_insert(self, nonce_b64: str, ts_ms: int, now_ms: int) -> bool:
        """
        Atomic-ish check-and-insert for a single-process demo.
        Returns False if nonce already seen within window.
        """
        self._prune(now_ms)
        if nonce_b64 in self._seen:
            return False
        self._seen[nonce_b64] = ts_ms
        return True


# ---------------------------------------------------------------------------
# Demo encryption: HMAC-based stream XOR (not production AEAD)
# ---------------------------------------------------------------------------

def stream_xor_encrypt(key: bytes, nonce: bytes, aad_bytes: bytes, plaintext: bytes) -> bytes:
    """
    Per-message keystream from HMAC(key, nonce||counter||aad) blocks.
    XOR with plaintext. Decrypt is same function.
    """
    out = bytearray()
    counter = 0
    offset = 0

    while offset < len(plaintext):
        counter_bytes = counter.to_bytes(4, "little")
        block = hmac_sha256(key, b"KS" + nonce + counter_bytes + aad_bytes)
        chunk = plaintext[offset:offset + len(block)]
        out.extend(bytes(p ^ block[i] for i, p in enumerate(chunk)))
        offset += len(block)
        counter += 1

    return bytes(out)


def deterministic_noise(key: bytes, context_bytes: bytes, length: int = 32) -> bytes:
    """
    Deterministic fail-to-noise: stable for the same failure context.
    """
    seed = hmac_sha256(key, b"NOISE" + context_bytes)
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hmac_sha256(seed, counter.to_bytes(4, "little")))
        counter += 1
    return bytes(out[:length])


# ---------------------------------------------------------------------------
# Roundtable consensus (multi-signature approval tiers)
# ---------------------------------------------------------------------------

class Roundtable:
    TIERS = {
        "low": ["KO"],
        "medium": ["KO", "RU"],
        "high": ["KO", "RU", "UM"],
        "critical": ["KO", "RU", "UM", "DR"],
    }

    @staticmethod
    def required_tongues(action: str) -> List[str]:
        if action in {"read", "query"}:
            return Roundtable.TIERS["low"]
        if action in {"write", "update"}:
            return Roundtable.TIERS["medium"]
        if action in {"delete", "grant_access"}:
            return Roundtable.TIERS["high"]
        return Roundtable.TIERS["critical"]


# ---------------------------------------------------------------------------
# Tongue key derivation (per-tongue + per-kid)
# ---------------------------------------------------------------------------

def derive_tongue_key(master_key: bytes, tongue: str, kid: str) -> bytes:
    """
    Deterministic per-tongue key derivation from master key.
    Demo only: production would use a proper keyring store.
    """
    if tongue not in TONGUES:
        raise ValueError(f"Unknown tongue: {tongue}")
    return hmac_sha256(master_key, b"TONGUE|" + tongue.encode("ascii") + b"|" + kid.encode("ascii"))


# ---------------------------------------------------------------------------
# RWP demo envelope with multi-signature + policy
# ---------------------------------------------------------------------------

@dataclass
class RWPEnvelope:
    ver: str
    primary_tongue: str
    origin: str
    ts_ms: int
    nonce_b64: str
    aad: Dict[str, Any]
    payload_b64: str
    kid: Dict[str, str]          # per tongue key id
    sigs: Dict[str, str]         # per tongue signature (b64url of raw HMAC bytes)
    enc: str

    @staticmethod
    def seal(
        master_key: bytes,
        primary_tongue: str,
        origin: str,
        payload_obj: Dict[str, Any],
        aad: Optional[Dict[str, Any]] = None,
        signing_tongues: Optional[List[str]] = None,
        kid_default: str = "k1",
        enc_label: str = "demo-hmac-stream-xor"
    ) -> "RWPEnvelope":
        if primary_tongue not in TONGUES:
            raise ValueError(f"Unknown tongue: {primary_tongue}")

        if aad is None:
            aad = {}

        # Determine quorum based on action (must be in AAD to be enforceable pre-decrypt)
        action = str(aad.get("action", "unknown"))
        required = Roundtable.required_tongues(action)

        # Default signing tongues = required quorum
        if signing_tongues is None:
            signing_tongues = required[:]
        # Ensure primary tongue is always present
        if primary_tongue not in signing_tongues:
            signing_tongues = [primary_tongue] + signing_tongues

        ts_ms = int(time.time() * 1000)
        nonce = os.urandom(16)
        nonce_b64 = b64url_encode(nonce)

        payload_bytes = canonical_json_bytes(payload_obj)
        aad_bytes = canonical_json_bytes(aad)

        ct = stream_xor_encrypt(master_key, nonce, aad_bytes, payload_bytes)
        payload_b64 = b64url_encode(ct)

        # kid per tongue (demo: all kid_default)
        kid = {t: kid_default for t in signing_tongues}

        # SignObject excluding sigs
        sign_obj = {
            "ver": "2.1-demo",
            "primary_tongue": primary_tongue,
            "origin": origin,
            "ts_ms": ts_ms,
            "nonce": nonce_b64,
            "aad": aad,
            "payload": payload_b64,
            "kid": kid,
            "enc": enc_label,
        }
        sign_bytes = canonical_json_bytes(sign_obj)

        sigs: Dict[str, str] = {}
        for t in signing_tongues:
            key_t = derive_tongue_key(master_key, t, kid[t])
            sig = hmac_sha256(key_t, sign_bytes)
            sigs[t] = b64url_encode(sig)

        return RWPEnvelope(
            ver="2.1-demo",
            primary_tongue=primary_tongue,
            origin=origin,
            ts_ms=ts_ms,
            nonce_b64=nonce_b64,
            aad=aad,
            payload_b64=payload_b64,
            kid=kid,
            sigs=sigs,
            enc=enc_label
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ver": self.ver,
            "primary_tongue": self.primary_tongue,
            "origin": self.origin,
            "ts_ms": self.ts_ms,
            "nonce": self.nonce_b64,
            "aad": self.aad,
            "payload": self.payload_b64,
            "kid": self.kid,
            "sigs": self.sigs,
            "enc": self.enc,
        }

    @staticmethod
    def verify_and_open(
        envelope: Dict[str, Any],
        master_key: bytes,
        nonce_cache: NonceCache,
        replay_window_ms: int = 60_000,
        skew_ms: int = 5_000,
        debug: bool = True
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Returns (decision, result)

        decision in {"ALLOW","QUARANTINE","DENY"}

        External-safe behavior:
        - DENY returns NOISE
        - QUARANTINE returns NOISE (but debug may show reason locally)

        ALLOW returns decrypted payload.
        """
        now_ms = int(time.time() * 1000)

        required_fields = ["ver", "primary_tongue", "origin", "ts_ms", "nonce", "aad", "payload", "kid", "sigs", "enc"]
        if any(k not in envelope for k in required_fields):
            noise = deterministic_noise(master_key, b"missing_fields", 32).hex()
            return "DENY", {"error": "NOISE", "data": noise}

        ts_ms = int(envelope["ts_ms"])
        if ts_ms > now_ms + skew_ms or ts_ms < now_ms - replay_window_ms:
            noise = deterministic_noise(master_key, b"bad_time" + str(ts_ms).encode(), 32).hex()
            return "DENY", {"error": "NOISE", "data": noise}

        primary = envelope["primary_tongue"]
        if primary not in TONGUES:
            noise = deterministic_noise(master_key, b"bad_tongue", 32).hex()
            return "DENY", {"error": "NOISE", "data": noise}

        # Determine required quorum from action in AAD (must be unencrypted)
        action = str(envelope["aad"].get("action", "unknown"))
        required_t = Roundtable.required_tongues(action)

        # Rebuild sign_obj exactly as in seal (exclude sigs)
        sign_obj = {
            "ver": envelope["ver"],
            "primary_tongue": primary,
            "origin": envelope["origin"],
            "ts_ms": ts_ms,
            "nonce": envelope["nonce"],
            "aad": envelope["aad"],
            "payload": envelope["payload"],
            "kid": envelope["kid"],
            "enc": envelope["enc"],
        }
        sign_bytes = canonical_json_bytes(sign_obj)

        sigs = envelope["sigs"]
        kid = envelope["kid"]

        # Primary signature must verify or we DENY immediately (no oracle)
        if primary not in sigs or primary not in kid:
            noise = deterministic_noise(master_key, b"missing_primary_sig", 32).hex()
            return "DENY", {"error": "NOISE", "data": noise}

        key_primary = derive_tongue_key(master_key, primary, kid[primary])
        expected_primary = hmac_sha256(key_primary, sign_bytes)
        got_primary = b64url_decode(sigs[primary])

        if not timing_safe_eq_bytes(expected_primary, got_primary):
            ctx = sign_bytes[:64]
            noise = deterministic_noise(master_key, b"bad_sig" + ctx, 32).hex()
            return "DENY", {"error": "NOISE", "data": noise}

        # Replay check AFTER crypto success, BEFORE policy (and record even if policy fails)
        nonce_b64 = envelope["nonce"]
        if not nonce_cache.check_and_insert(nonce_b64, ts_ms=ts_ms, now_ms=now_ms):
            noise = deterministic_noise(master_key, b"replay" + nonce_b64.encode(), 32).hex()
            return "DENY", {"error": "NOISE", "data": noise}

        # Verify all signatures we have; compute valid_tongues
        valid_tongues: List[str] = []
        for t, sig_b64 in sigs.items():
            if t not in kid:
                continue
            if t not in TONGUES:
                continue
            try:
                sig_bytes = b64url_decode(sig_b64)
            except Exception:
                continue
            key_t = derive_tongue_key(master_key, t, kid[t])
            exp = hmac_sha256(key_t, sign_bytes)
            if timing_safe_eq_bytes(exp, sig_bytes):
                valid_tongues.append(t)

        # Policy: do we have required tongues?
        quorum_ok = all(t in valid_tongues for t in required_t)

        # If quorum missing -> QUARANTINE (external: NOISE)
        if not quorum_ok:
            noise = deterministic_noise(master_key, b"quarantine|" + ("|".join(required_t)).encode(), 32).hex()
            if debug:
                return "QUARANTINE", {
                    "error": "NOISE",
                    "data": noise,
                    "debug": {
                        "reason": "missing_quorum",
                        "required": required_t,
                        "valid_tongues": valid_tongues
                    }
                }
            return "QUARANTINE", {"error": "NOISE", "data": noise}

        # Decrypt only on ALLOW
        nonce = b64url_decode(nonce_b64)
        aad_bytes = canonical_json_bytes(envelope["aad"])
        ct = b64url_decode(envelope["payload"])
        pt = stream_xor_encrypt(master_key, nonce, aad_bytes, ct)

        try:
            payload_obj = json.loads(pt.decode("utf-8"))
            if debug:
                return "ALLOW", {"payload": payload_obj, "valid_tongues": valid_tongues, "required": required_t}
            return "ALLOW", payload_obj
        except Exception:
            noise = deterministic_noise(master_key, b"decode_fail", 32).hex()
            return "DENY", {"error": "NOISE", "data": noise}


# ---------------------------------------------------------------------------
# Security Gate (time dilation + score-based decision)
# ---------------------------------------------------------------------------

class SecurityGate:
    def __init__(self) -> None:
        self.min_wait_ms = 100
        self.max_wait_ms = 5000
        self.alpha = 1.5  # risk multiplier base

    def assess_risk(self, agent: Agent6D, action: str, context: Dict[str, Any]) -> float:
        risk = 0.0
        risk += (1.0 - float(agent.trust_score)) * 2.0
        dangerous = {"delete", "deploy", "rotate_keys", "grant_access", "transfer_funds"}
        if action in dangerous:
            risk += 3.0
        if context.get("source") == "external":
            risk += 1.5
        return risk

    async def check(self, agent: Agent6D, action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        risk = self.assess_risk(agent, action, context)
        dwell_ms = min(self.max_wait_ms, self.min_wait_ms * (self.alpha ** risk))
        await asyncio.sleep(dwell_ms / 1000.0)

        trust_component = float(agent.trust_score) * 0.4
        action_component = (1.0 if action not in {"delete", "deploy", "transfer_funds"} else 0.3) * 0.3
        context_component = (0.8 if context.get("source") == "internal" else 0.4) * 0.3
        score = trust_component + action_component + context_component

        if score > 0.8:
            return {"status": "allow", "score": score, "dwell_ms": dwell_ms}
        elif score > 0.5:
            return {"status": "review", "score": score, "dwell_ms": dwell_ms, "reason": "Manual approval required"}
        else:
            return {"status": "deny", "score": score, "dwell_ms": dwell_ms, "reason": "Security threshold not met"}
