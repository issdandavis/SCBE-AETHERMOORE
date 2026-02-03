"""
RWP2 Envelope Architecture - Secure Multi-Tongue Message Structure
==================================================================

Hybrid envelope combining human-readable spelltext with
machine-optimized Base64URL payloads.

Structure:
    {
        "spelltext": "AXIOM<origin>KO</origin><seq>42</seq><ts>...",
        "payload": "<Base64URL-encoded operation>",
        "sig_KO": "<HMAC-SHA256>",  # Per-tongue signatures
        "sig_RU": "<HMAC-SHA256>",
        "sig_UM": "<HMAC-SHA256>",
        "aad": "context=...",  # Additional authenticated data
        "nonce": "<replay-protection>",
        "ts": 1737244800000  # Timestamp
    }

Security Properties:
    - Additive Verification: Each tongue signature validates independently
    - Cascade Failure: Missing any required signature -> total rejection
    - Temporal Binding: All signatures use same nonce + timestamp
    - Replay Protection: Nonce/timestamp pair valid for single use only

"The envelope carries the weight of many tongues."
"""

import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
import re


# =============================================================================
# Tongue Definitions (Protocol Domains)
# =============================================================================

class ProtocolTongue(Enum):
    """
    The Six Sacred Tongues as protocol domains.

    Each tongue governs a class of operations:
    - KO: Control & Intent (orchestration, delegation)
    - AV: I/O & Messaging (transport, routing)
    - RU: Policy & Constraints (state binding, governance)
    - CA: Logic & Computation (math, algorithms)
    - UM: Security & Secrets (encryption, access control)
    - DR: Types & Schema (data structures, validation)
    """
    KO = "KO"  # Kor'aelin - Control Flow
    AV = "AV"  # Avali - I/O & Messaging
    RU = "RU"  # Runethic - Policy & Constraints
    CA = "CA"  # Cassisivadan - Logic & Computation
    UM = "UM"  # Umbroth - Security & Secrets
    DR = "DR"  # Draumric - Types & Schema


# Tongue-specific HMAC keys (in production, these would be securely managed)
# Using deterministic seeds for reproducibility in this implementation
TONGUE_KEYS = {
    ProtocolTongue.KO: hashlib.sha256(b"SCBE_KO_KEY_v1").digest(),
    ProtocolTongue.AV: hashlib.sha256(b"SCBE_AV_KEY_v1").digest(),
    ProtocolTongue.RU: hashlib.sha256(b"SCBE_RU_KEY_v1").digest(),
    ProtocolTongue.CA: hashlib.sha256(b"SCBE_CA_KEY_v1").digest(),
    ProtocolTongue.UM: hashlib.sha256(b"SCBE_UM_KEY_v1").digest(),
    ProtocolTongue.DR: hashlib.sha256(b"SCBE_DR_KEY_v1").digest(),
}


# =============================================================================
# Tier Classification
# =============================================================================

class OperationTier(Enum):
    """
    Tiered operation classification by risk level.

    Security scales exponentially: S(N) = B * R^(N^2)
    where B = base bits (256), R = harmonic ratio (1.5), N = tongue count
    """
    TIER_1 = 1  # Single tongue (KO) - Basic coordination
    TIER_2 = 2  # Dual tongue (KO+RU) - State modifications
    TIER_3 = 3  # Triple tongue (KO+RU+UM) - Security operations
    TIER_4 = 4  # Quad+ tongues - Irreversible operations


# Required tongues per tier
TIER_REQUIRED_TONGUES = {
    OperationTier.TIER_1: {ProtocolTongue.KO},
    OperationTier.TIER_2: {ProtocolTongue.KO, ProtocolTongue.RU},
    OperationTier.TIER_3: {ProtocolTongue.KO, ProtocolTongue.RU, ProtocolTongue.UM},
    OperationTier.TIER_4: {ProtocolTongue.KO, ProtocolTongue.RU, ProtocolTongue.UM, ProtocolTongue.CA},
}

# Security multipliers (approximate, for display)
TIER_SECURITY_MULTIPLIERS = {
    OperationTier.TIER_1: 1.5,
    OperationTier.TIER_2: 5.06,
    OperationTier.TIER_3: 38.4,
    OperationTier.TIER_4: 656.0,
}


# =============================================================================
# Spelltext Parser
# =============================================================================

@dataclass
class SpelltextData:
    """Parsed spelltext components."""
    command: str
    origin: str
    sequence: int
    timestamp: datetime
    context: Dict[str, str] = field(default_factory=dict)


def parse_spelltext(spelltext: str) -> SpelltextData:
    """
    Parse human-readable spelltext into structured data.

    Format: COMMAND<origin>TONGUE</origin><seq>N</seq><ts>ISO8601</ts>
    """
    # Extract command (first word)
    command_match = re.match(r'^(\w+)', spelltext)
    command = command_match.group(1) if command_match else "UNKNOWN"

    # Extract origin tongue
    origin_match = re.search(r'<origin>(\w+)</origin>', spelltext)
    origin = origin_match.group(1) if origin_match else "KO"

    # Extract sequence number
    seq_match = re.search(r'<seq>(\d+)</seq>', spelltext)
    sequence = int(seq_match.group(1)) if seq_match else 0

    # Extract timestamp
    ts_match = re.search(r'<ts>([^<]+)</ts>', spelltext)
    if ts_match:
        timestamp = datetime.fromisoformat(ts_match.group(1).replace('Z', '+00:00'))
    else:
        timestamp = datetime.utcnow()

    # Extract any additional context
    context = {}
    context_matches = re.findall(r'<(\w+)>([^<]+)</\1>', spelltext)
    for key, value in context_matches:
        if key not in ['origin', 'seq', 'ts']:
            context[key] = value

    return SpelltextData(
        command=command,
        origin=origin,
        sequence=sequence,
        timestamp=timestamp,
        context=context
    )


def build_spelltext(
    command: str,
    origin: ProtocolTongue,
    sequence: int,
    timestamp: Optional[datetime] = None,
    **context
) -> str:
    """Build spelltext from components."""
    ts = timestamp or datetime.utcnow()
    ts_str = ts.strftime('%Y-%m-%dT%H:%M:%SZ')

    parts = [
        command,
        f"<origin>{origin.value}</origin>",
        f"<seq>{sequence}</seq>",
        f"<ts>{ts_str}</ts>",
    ]

    for key, value in context.items():
        parts.append(f"<{key}>{value}</{key}>")

    return ''.join(parts)


# =============================================================================
# RWP2 Envelope
# =============================================================================

@dataclass
class RWP2Envelope:
    """
    Hybrid envelope with spelltext + Base64 payload + multi-tongue signatures.
    """
    # Core fields
    version: str = "2"
    spelltext: str = ""
    payload: bytes = b""

    # Signatures (per tongue)
    signatures: Dict[ProtocolTongue, str] = field(default_factory=dict)

    # Security fields
    aad: str = ""  # Additional authenticated data
    nonce: str = ""
    timestamp_ms: int = 0

    # Metadata
    kid: str = ""  # Key ID
    tier: OperationTier = OperationTier.TIER_1

    def __post_init__(self):
        if not self.nonce:
            self.nonce = secrets.token_urlsafe(16)
        if not self.timestamp_ms:
            self.timestamp_ms = int(time.time() * 1000)

    @property
    def payload_b64(self) -> str:
        """Base64URL encoded payload."""
        return base64.urlsafe_b64encode(self.payload).decode('ascii')

    @payload_b64.setter
    def payload_b64(self, value: str):
        """Decode Base64URL payload."""
        self.payload = base64.urlsafe_b64decode(value)

    @property
    def signed_tongues(self) -> Set[ProtocolTongue]:
        """Set of tongues that have signed this envelope."""
        return set(self.signatures.keys())

    @property
    def timestamp(self) -> datetime:
        """Timestamp as datetime."""
        return datetime.utcfromtimestamp(self.timestamp_ms / 1000)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (for JSON)."""
        result = {
            "ver": self.version,
            "spelltext": self.spelltext,
            "payload": self.payload_b64,
            "aad": self.aad,
            "nonce": self.nonce,
            "ts": self.timestamp_ms,
            "kid": self.kid,
            "tier": self.tier.value,
        }

        # Add signatures with sig_ prefix
        for tongue, sig in self.signatures.items():
            result[f"sig_{tongue.value}"] = sig

        return result

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'RWP2Envelope':
        """Deserialize from dictionary."""
        # Extract signatures
        signatures = {}
        for key, value in d.items():
            if key.startswith("sig_"):
                tongue_name = key[4:]
                try:
                    tongue = ProtocolTongue(tongue_name)
                    signatures[tongue] = value
                except ValueError:
                    pass  # Unknown tongue, skip

        envelope = cls(
            version=d.get("ver", "2"),
            spelltext=d.get("spelltext", ""),
            aad=d.get("aad", ""),
            nonce=d.get("nonce", ""),
            timestamp_ms=d.get("ts", 0),
            kid=d.get("kid", ""),
            tier=OperationTier(d.get("tier", 1)),
            signatures=signatures
        )

        # Decode payload
        if "payload" in d:
            envelope.payload_b64 = d["payload"]

        return envelope

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_json(cls, json_str: str) -> 'RWP2Envelope':
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


# =============================================================================
# Signature Engine
# =============================================================================

class SignatureEngine:
    """
    Multi-tongue signature generation and verification.

    Uses HMAC-SHA256 per tongue with temporal binding.
    """

    def __init__(self, keys: Optional[Dict[ProtocolTongue, bytes]] = None):
        self.keys = keys or TONGUE_KEYS

    def _compute_signature_input(self, envelope: RWP2Envelope) -> bytes:
        """
        Compute the canonical input for signature.

        Includes: spelltext + payload + aad + nonce + timestamp
        """
        parts = [
            envelope.spelltext.encode('utf-8'),
            envelope.payload,
            envelope.aad.encode('utf-8'),
            envelope.nonce.encode('utf-8'),
            str(envelope.timestamp_ms).encode('utf-8'),
        ]
        return b'|'.join(parts)

    def sign(
        self,
        envelope: RWP2Envelope,
        tongues: Set[ProtocolTongue]
    ) -> RWP2Envelope:
        """
        Sign envelope with specified tongues.

        Returns new envelope with signatures added.
        """
        sig_input = self._compute_signature_input(envelope)

        new_signatures = dict(envelope.signatures)
        for tongue in tongues:
            key = self.keys.get(tongue)
            if key:
                sig = hmac.new(key, sig_input, hashlib.sha256).hexdigest()
                new_signatures[tongue] = sig

        # Return new envelope with signatures
        return RWP2Envelope(
            version=envelope.version,
            spelltext=envelope.spelltext,
            payload=envelope.payload,
            signatures=new_signatures,
            aad=envelope.aad,
            nonce=envelope.nonce,
            timestamp_ms=envelope.timestamp_ms,
            kid=envelope.kid,
            tier=envelope.tier
        )

    def verify(
        self,
        envelope: RWP2Envelope,
        required_tongues: Optional[Set[ProtocolTongue]] = None
    ) -> Tuple[bool, Dict[ProtocolTongue, bool]]:
        """
        Verify envelope signatures.

        Args:
            envelope: Envelope to verify
            required_tongues: Tongues that must be valid (defaults to tier requirement)

        Returns:
            (overall_valid, per_tongue_results)
        """
        sig_input = self._compute_signature_input(envelope)

        # Determine required tongues
        if required_tongues is None:
            required_tongues = TIER_REQUIRED_TONGUES.get(envelope.tier, {ProtocolTongue.KO})

        results = {}
        for tongue in required_tongues:
            key = self.keys.get(tongue)
            sig = envelope.signatures.get(tongue)

            if not key or not sig:
                results[tongue] = False
                continue

            expected_sig = hmac.new(key, sig_input, hashlib.sha256).hexdigest()
            results[tongue] = hmac.compare_digest(sig, expected_sig)

        # Overall valid only if ALL required tongues verify
        overall_valid = all(results.values()) and len(results) == len(required_tongues)

        return overall_valid, results


# =============================================================================
# Replay Protection
# =============================================================================

class ReplayProtector:
    """
    Prevents replay attacks by tracking used nonces.

    Nonce + timestamp pairs are valid for single use only.
    """

    def __init__(
        self,
        max_age_seconds: int = 300,  # 5 minutes
        max_cache_size: int = 10000
    ):
        self.max_age = max_age_seconds
        self.max_cache = max_cache_size
        self.used_nonces: Dict[str, int] = {}  # nonce -> timestamp_ms

    def is_valid(self, envelope: RWP2Envelope) -> Tuple[bool, str]:
        """
        Check if envelope passes replay protection.

        Returns (valid, reason).
        """
        now_ms = int(time.time() * 1000)

        # Check timestamp freshness
        age_ms = now_ms - envelope.timestamp_ms
        if age_ms > self.max_age * 1000:
            return False, f"Envelope too old: {age_ms/1000:.1f}s"

        if age_ms < -60000:  # 1 minute future tolerance
            return False, "Envelope timestamp in future"

        # Check nonce uniqueness
        nonce_key = f"{envelope.nonce}:{envelope.timestamp_ms}"
        if nonce_key in self.used_nonces:
            return False, "Nonce already used (replay detected)"

        # Mark nonce as used
        self.used_nonces[nonce_key] = envelope.timestamp_ms

        # Cleanup old nonces
        self._cleanup()

        return True, "OK"

    def _cleanup(self):
        """Remove expired nonces."""
        now_ms = int(time.time() * 1000)
        cutoff_ms = now_ms - (self.max_age * 1000)

        # Remove old entries
        to_remove = [k for k, v in self.used_nonces.items() if v < cutoff_ms]
        for k in to_remove:
            del self.used_nonces[k]

        # Enforce cache size limit
        if len(self.used_nonces) > self.max_cache:
            # Remove oldest entries
            sorted_items = sorted(self.used_nonces.items(), key=lambda x: x[1])
            remove_count = len(self.used_nonces) - self.max_cache
            for k, _ in sorted_items[:remove_count]:
                del self.used_nonces[k]


# =============================================================================
# Envelope Factory
# =============================================================================

class EnvelopeFactory:
    """
    Factory for creating and validating RWP2 envelopes.
    """

    def __init__(self):
        self.signature_engine = SignatureEngine()
        self.replay_protector = ReplayProtector()
        self.sequence_counter = 0

    def create(
        self,
        command: str,
        payload: bytes,
        origin_tongue: ProtocolTongue,
        tier: OperationTier,
        aad: str = "",
        **context
    ) -> RWP2Envelope:
        """
        Create a signed RWP2 envelope.
        """
        self.sequence_counter += 1

        # Build spelltext
        spelltext = build_spelltext(
            command=command,
            origin=origin_tongue,
            sequence=self.sequence_counter,
            **context
        )

        # Create envelope
        envelope = RWP2Envelope(
            spelltext=spelltext,
            payload=payload,
            aad=aad,
            tier=tier,
            kid=f"v1:{origin_tongue.value.lower()}_master"
        )

        # Sign with required tongues for tier
        required = TIER_REQUIRED_TONGUES.get(tier, {origin_tongue})
        envelope = self.signature_engine.sign(envelope, required)

        return envelope

    def validate(self, envelope: RWP2Envelope) -> Tuple[bool, List[str]]:
        """
        Fully validate an envelope.

        Returns (valid, list of issues).
        """
        issues = []

        # Check replay protection
        replay_valid, replay_reason = self.replay_protector.is_valid(envelope)
        if not replay_valid:
            issues.append(f"Replay check failed: {replay_reason}")

        # Verify signatures
        sig_valid, sig_results = self.signature_engine.verify(envelope)
        if not sig_valid:
            failed_tongues = [t.value for t, v in sig_results.items() if not v]
            issues.append(f"Signature verification failed for: {failed_tongues}")

        return len(issues) == 0, issues


# =============================================================================
# Demo
# =============================================================================

def demo():
    """Demonstrate RWP2 envelope system."""
    print("=" * 70)
    print("  RWP2 ENVELOPE ARCHITECTURE - Multi-Tongue Secure Messaging")
    print("=" * 70)
    print()

    factory = EnvelopeFactory()

    # Create a Tier 1 envelope (single tongue)
    print("[TIER 1] Basic coordination message (KO only):")
    print("-" * 50)
    payload1 = b'{"action": "status_update", "status": "active"}'
    envelope1 = factory.create(
        command="STATUS",
        payload=payload1,
        origin_tongue=ProtocolTongue.KO,
        tier=OperationTier.TIER_1,
        aad="agent=alpha;mission=recon"
    )

    print(f"  Spelltext: {envelope1.spelltext}")
    print(f"  Payload: {len(payload1)} bytes")
    print(f"  Signatures: {[t.value for t in envelope1.signed_tongues]}")
    print(f"  Nonce: {envelope1.nonce}")
    print()

    # Validate it
    valid1, issues1 = factory.validate(envelope1)
    print(f"  Validation: {'PASS' if valid1 else 'FAIL'}")
    if issues1:
        print(f"  Issues: {issues1}")
    print()

    # Create a Tier 3 envelope (triple tongue - security operation)
    print("[TIER 3] Security operation (KO + RU + UM):")
    print("-" * 50)
    payload3 = b'{"action": "rotate_keys", "key_version": 5}'
    envelope3 = factory.create(
        command="KEY_ROTATE",
        payload=payload3,
        origin_tongue=ProtocolTongue.UM,
        tier=OperationTier.TIER_3,
        aad="critical=true;approval_id=9f8e7d6c"
    )

    print(f"  Spelltext: {envelope3.spelltext}")
    print(f"  Tier: {envelope3.tier.name}")
    print(f"  Signatures: {[t.value for t in envelope3.signed_tongues]}")
    print(f"  Security multiplier: {TIER_SECURITY_MULTIPLIERS[envelope3.tier]}x")
    print()

    valid3, issues3 = factory.validate(envelope3)
    print(f"  Validation: {'PASS' if valid3 else 'FAIL'}")
    print()

    # JSON serialization
    print("[SERIALIZATION] JSON format:")
    print("-" * 50)
    json_str = envelope3.to_json()
    print(f"  Length: {len(json_str)} bytes")
    print(f"  Preview: {json_str[:100]}...")
    print()

    # Deserialize and re-validate
    restored = RWP2Envelope.from_json(json_str)
    print(f"  Restored signatures: {[t.value for t in restored.signed_tongues]}")
    print()

    # Replay attack demonstration
    print("[REPLAY PROTECTION] Detecting replay attacks:")
    print("-" * 50)

    # First use should pass
    replay_valid1, _ = factory.replay_protector.is_valid(envelope1)
    print(f"  First submission: {'ACCEPTED' if replay_valid1 else 'REJECTED'}")

    # Create new envelope with same nonce (simulated replay)
    replay_envelope = RWP2Envelope(
        spelltext=envelope1.spelltext,
        payload=envelope1.payload,
        signatures=envelope1.signatures,
        nonce=envelope1.nonce,
        timestamp_ms=envelope1.timestamp_ms
    )
    replay_valid2, reason = factory.replay_protector.is_valid(replay_envelope)
    print(f"  Replay attempt: {'ACCEPTED' if replay_valid2 else 'REJECTED'} ({reason})")
    print()

    # Signature verification
    print("[SIGNATURE VERIFICATION] Per-tongue validation:")
    print("-" * 50)
    _, sig_results = factory.signature_engine.verify(envelope3)
    for tongue, valid in sig_results.items():
        status = "VALID" if valid else "INVALID"
        print(f"  {tongue.value}: {status}")
    print()

    # Tamper detection
    print("[TAMPER DETECTION] Modifying payload:")
    print("-" * 50)
    tampered = RWP2Envelope(
        spelltext=envelope3.spelltext,
        payload=b'{"action": "MALICIOUS_ACTION"}',  # Modified!
        signatures=envelope3.signatures,
        nonce=envelope3.nonce,
        timestamp_ms=envelope3.timestamp_ms,
        tier=envelope3.tier
    )
    tamper_valid, tamper_results = factory.signature_engine.verify(tampered)
    print(f"  Tampered envelope: {'VALID' if tamper_valid else 'INVALID (tampering detected)'}")
    print()

    print("=" * 70)
    print("  RWP2 Envelope Demo Complete")
    print("=" * 70)


if __name__ == "__main__":
    demo()
