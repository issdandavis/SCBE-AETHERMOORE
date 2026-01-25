"""
RWP v2.1 Envelope Module

Provides multi-signature signing and verification for the Spiralverse Protocol.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Set

TongueID = Literal["ko", "av", "ru", "ca", "um", "dr"]

# Nonce cache for replay protection
_nonce_cache: Set[str] = set()
_nonce_cache_max = 10000

DEFAULT_MAX_AGE = 300000  # 5 minutes
DEFAULT_MAX_FUTURE_SKEW = 60000  # 1 minute


@dataclass
class RWPEnvelope:
    """RWP v2.1 Envelope structure."""

    ver: str = "2.1"
    primary_tongue: TongueID = "ko"
    aad: str = ""
    payload: str = ""  # base64url encoded
    sigs: Dict[TongueID, str] = field(default_factory=dict)
    nonce: str = ""  # base64url encoded
    ts: int = 0  # milliseconds since epoch
    kid: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "ver": self.ver,
            "primary_tongue": self.primary_tongue,
            "aad": self.aad,
            "payload": self.payload,
            "sigs": self.sigs,
            "nonce": self.nonce,
            "ts": self.ts,
        }
        if self.kid:
            result["kid"] = self.kid
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RWPEnvelope":
        """Create from dictionary."""
        return cls(
            ver=data.get("ver", "2.1"),
            primary_tongue=data.get("primary_tongue", "ko"),
            aad=data.get("aad", ""),
            payload=data.get("payload", ""),
            sigs=data.get("sigs", {}),
            nonce=data.get("nonce", ""),
            ts=data.get("ts", 0),
            kid=data.get("kid"),
        )


def _base64url_encode(data: bytes) -> str:
    """Encode bytes to base64url string."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(s: str) -> bytes:
    """Decode base64url string to bytes."""
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def clear_nonce_cache() -> None:
    """Clear the nonce cache."""
    global _nonce_cache
    _nonce_cache = set()


def sign_roundtable(
    payload: Any,
    primary_tongue: TongueID,
    aad: str,
    keyring: Dict[TongueID, bytes],
    tongues: List[TongueID],
    kid: Optional[str] = None,
) -> RWPEnvelope:
    """
    Sign a payload with multiple tongues (Roundtable consensus).

    Args:
        payload: The data to sign (will be JSON serialized)
        primary_tongue: The primary tongue initiating the signature
        aad: Additional authenticated data
        keyring: Dictionary mapping tongue IDs to secret keys
        tongues: List of tongues that must sign
        kid: Optional key ID

    Returns:
        RWPEnvelope with all signatures
    """
    # Generate nonce
    nonce = os.urandom(16)
    nonce_b64 = _base64url_encode(nonce)

    # Encode payload
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_b64 = _base64url_encode(payload_json.encode("utf-8"))

    # Timestamp
    ts = int(time.time() * 1000)

    # Create signing input
    signing_input = f"{nonce_b64}.{ts}.{aad}.{payload_b64}"

    # Sign with each tongue
    sigs: Dict[TongueID, str] = {}
    for tongue in tongues:
        if tongue not in keyring or keyring[tongue] is None:
            raise ValueError(f"Missing key for tongue: {tongue}")

        key = keyring[tongue]
        sig = hmac.new(key, signing_input.encode("utf-8"), hashlib.sha256).digest()
        sigs[tongue] = _base64url_encode(sig)

    return RWPEnvelope(
        ver="2.1",
        primary_tongue=primary_tongue,
        aad=aad,
        payload=payload_b64,
        sigs=sigs,
        nonce=nonce_b64,
        ts=ts,
        kid=kid,
    )


@dataclass
class VerifyResult:
    """Verification result."""

    valid: bool
    valid_tongues: List[TongueID] = field(default_factory=list)
    payload: Optional[Any] = None
    error: Optional[str] = None


def verify_roundtable(
    envelope: RWPEnvelope,
    keyring: Dict[TongueID, bytes],
    max_age: int = DEFAULT_MAX_AGE,
    max_future_skew: int = DEFAULT_MAX_FUTURE_SKEW,
    required_tongues: Optional[List[TongueID]] = None,
) -> VerifyResult:
    """
    Verify a Roundtable envelope.

    Args:
        envelope: The envelope to verify
        keyring: Dictionary mapping tongue IDs to secret keys
        max_age: Maximum age in milliseconds
        max_future_skew: Maximum future skew in milliseconds
        required_tongues: Optional list of required tongues

    Returns:
        VerifyResult with validation status
    """
    global _nonce_cache

    # Check version
    if envelope.ver != "2.1":
        return VerifyResult(valid=False, error=f"Unsupported version: {envelope.ver}")

    # Check timestamp
    now = int(time.time() * 1000)
    if envelope.ts > now + max_future_skew:
        return VerifyResult(valid=False, error="Timestamp is in the future")
    if now - envelope.ts > max_age:
        return VerifyResult(valid=False, error="Envelope has expired")

    # Check nonce (replay protection)
    if envelope.nonce in _nonce_cache:
        return VerifyResult(valid=False, error="Nonce already used (replay attempt)")

    # Create signing input
    signing_input = f"{envelope.nonce}.{envelope.ts}.{envelope.aad}.{envelope.payload}"

    # Verify each signature
    valid_tongues: List[TongueID] = []
    for tongue, sig_b64 in envelope.sigs.items():
        if tongue not in keyring or keyring[tongue] is None:
            continue

        key = keyring[tongue]
        expected_sig = hmac.new(key, signing_input.encode("utf-8"), hashlib.sha256).digest()
        actual_sig = _base64url_decode(sig_b64)

        if hmac.compare_digest(expected_sig, actual_sig):
            valid_tongues.append(tongue)

    # Check required tongues
    if required_tongues:
        missing = set(required_tongues) - set(valid_tongues)
        if missing:
            return VerifyResult(
                valid=False,
                valid_tongues=valid_tongues,
                error=f"Missing required signatures: {missing}",
            )

    # Must have at least one valid signature
    if not valid_tongues:
        return VerifyResult(valid=False, error="No valid signatures")

    # Add nonce to cache (with cleanup)
    if len(_nonce_cache) >= _nonce_cache_max:
        _nonce_cache.clear()
    _nonce_cache.add(envelope.nonce)

    # Decode payload
    try:
        payload_json = _base64url_decode(envelope.payload).decode("utf-8")
        payload = json.loads(payload_json)
    except Exception as e:
        return VerifyResult(valid=False, error=f"Failed to decode payload: {e}")

    return VerifyResult(valid=True, valid_tongues=valid_tongues, payload=payload)
