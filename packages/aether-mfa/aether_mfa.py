"""Aether MFA -- an owned, standard-primitive multi-factor library.

Two layers, no rolled crypto:

1. TOTP / HOTP (RFC 6238 / RFC 4226) -- stdlib only (hmac + hashlib). Interoperable with any
   authenticator app (Google/Microsoft/Aegis): emit an ``otpauth://`` URI, the app scans it, and
   the 6-digit codes match. This is the classic "second factor" you own end to end.

2. Push approval (challenge -> phone ping -> approve) -- Ed25519 signatures via ``cryptography``.
   This is the "AI MFA" layer: an agent (or a login) requests a SPECIFIC sensitive action; a
   challenge is pushed to your enrolled device; you confirm a match-number and approve; the device
   signs the challenge; the server verifies the signature against your enrolled public key. The
   server never holds your signing key. Approval is BOUND to the exact action, single-use, and
   expires -- so it cannot be replayed or redirected to a different action.

Why this fits SCBE: layer 2 is L13 ESCALATE made concrete -- a governed agent action that needs a
human's cryptographic yes before it proceeds.

Design choices (the "good, not toy" parts):
- Asymmetric (Ed25519): device keeps the private key; server stores only the public key.
- Action-binding: the signature covers ``id|action|nonce|match`` so a yes for "read" can't be
  replayed as a yes for "delete".
- Number-matching: a code shown on the requesting surface must be echoed from the phone -> defeats
  blind-approve fatigue and push-phishing.
- Single-use + expiry: each challenge is consumed on first verdict and dies after its TTL.
- Constant-time comparisons on all secret-bearing checks.

The verifier store here is in-memory (a dict) for reference; swap ``ChallengeStore`` for Redis/DB
in production. Everything else is transport-agnostic -- drop it behind a Flask/FastAPI endpoint for
web, or an MQTT/APNs push for mobile.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

# ===================================================================== #
#  Layer 1: TOTP / HOTP (RFC 6238 / RFC 4226) -- stdlib only            #
# ===================================================================== #

DEFAULT_DIGITS = 6
DEFAULT_PERIOD = 30


def generate_secret(num_bytes: int = 20) -> str:
    """Return a fresh base32 TOTP secret (20 bytes = 160 bits, the RFC 4226 recommendation)."""
    return base64.b32encode(secrets.token_bytes(num_bytes)).decode("ascii").rstrip("=")


def _b32_decode(secret_b32: str) -> bytes:
    pad = "=" * (-len(secret_b32) % 8)
    return base64.b32decode(secret_b32.upper() + pad)


def hotp(secret_b32: str, counter: int, digits: int = DEFAULT_DIGITS) -> str:
    """HMAC-based one-time password (RFC 4226) with dynamic truncation."""
    key = _b32_decode(secret_b32)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = (
        (digest[offset] & 0x7F) << 24
        | (digest[offset + 1] & 0xFF) << 16
        | (digest[offset + 2] & 0xFF) << 8
        | (digest[offset + 3] & 0xFF)
    )
    return str(binary % (10**digits)).zfill(digits)


def totp(
    secret_b32: str,
    at: Optional[float] = None,
    period: int = DEFAULT_PERIOD,
    digits: int = DEFAULT_DIGITS,
) -> str:
    """Time-based one-time password (RFC 6238)."""
    moment = time.time() if at is None else at
    return hotp(secret_b32, int(moment // period), digits=digits)


def verify_totp(
    secret_b32: str,
    code: str,
    at: Optional[float] = None,
    period: int = DEFAULT_PERIOD,
    digits: int = DEFAULT_DIGITS,
    window: int = 1,
) -> bool:
    """Verify a TOTP code, tolerating +/- ``window`` periods of clock drift. Constant-time."""
    moment = time.time() if at is None else at
    counter = int(moment // period)
    candidate = str(code).strip()
    ok = False
    for offset in range(-window, window + 1):
        expected = hotp(secret_b32, counter + offset, digits=digits)
        # OR-accumulate without early exit to keep the comparison count independent of the match.
        ok |= hmac.compare_digest(expected, candidate)
    return ok


def provisioning_uri(
    secret_b32: str,
    account: str,
    issuer: str = "AetherMFA",
    period: int = DEFAULT_PERIOD,
    digits: int = DEFAULT_DIGITS,
) -> str:
    """Build an ``otpauth://`` URI. Encode it as a QR and any authenticator app can enroll."""
    # otpauth label is "Issuer:account" -- the colon is the literal separator; encode each side.
    label = f"{quote(issuer)}:{quote(account)}"
    params = f"secret={secret_b32}&issuer={quote(issuer)}&algorithm=SHA1&digits={digits}&period={period}"
    return f"otpauth://totp/{label}?{params}"


# ===================================================================== #
#  Layer 2: Push approval (Ed25519 challenge / response)                #
# ===================================================================== #


@dataclass
class Device:
    """An enrolled approver device. The server stores only ``public_key`` (never the private key)."""

    device_id: str
    public_key: bytes  # raw 32-byte Ed25519 public key
    label: str = ""


@dataclass
class Challenge:
    """A pending approval request, pushed to the device and bound to one specific action."""

    challenge_id: str
    device_id: str
    action: str
    nonce: str
    match_number: (
        str  # shown on the requesting surface; the human echoes it from the phone
    )
    created_at: float
    expires_at: float
    status: str = "pending"  # pending | approved | denied | expired | consumed

    def signing_payload(self) -> bytes:
        """The exact bytes the device signs. Binds the approval to id+action+nonce+match."""
        return f"{self.challenge_id}|{self.action}|{self.nonce}|{self.match_number}".encode(
            "utf-8"
        )


@dataclass
class Verdict:
    allow: bool
    reason: str
    action: str = ""


@dataclass
class ChallengeStore:
    """In-memory reference store. Swap for Redis/DB in production (same method surface).

    SINGLE-USE IS ONLY AS ATOMIC AS THIS STORE. The in-memory dict gives atomicity for free
    (single-threaded). A real backend MUST make the "is it still pending? -> consume it" step a single
    atomic compare-and-set, e.g. ``UPDATE challenges SET status='consumed' WHERE id=? AND
    status='pending'`` and treat rows-affected==0 as already-used, or Redis WATCH/Lua. Without that,
    two concurrent ``verify_approval`` calls with the same valid signature can BOTH pass the
    pending-check before either writes -> double-approval (a replay hole the sequential tests cannot
    catch)."""

    _devices: dict[str, Device] = field(default_factory=dict)
    _challenges: dict[str, Challenge] = field(default_factory=dict)

    def put_device(self, device: Device) -> None:
        self._devices[device.device_id] = device

    def get_device(self, device_id: str) -> Optional[Device]:
        return self._devices.get(device_id)

    def put_challenge(self, challenge: Challenge) -> None:
        self._challenges[challenge.challenge_id] = challenge

    def get_challenge(self, challenge_id: str) -> Optional[Challenge]:
        return self._challenges.get(challenge_id)


# ---- device side (runs on the phone / approver) ---------------------- #


def enroll_device(label: str = "") -> tuple[str, bytes, Device]:
    """Generate an Ed25519 keypair on the device. Returns (device_id, private_key_bytes, Device).

    The private_key_bytes never leave the device; hand the returned ``Device`` to the server.
    """
    private = Ed25519PrivateKey.generate()
    private_bytes = private.private_bytes_raw()
    public_bytes = private.public_key().public_bytes_raw()
    device_id = secrets.token_hex(8)
    return (
        device_id,
        private_bytes,
        Device(device_id=device_id, public_key=public_bytes, label=label),
    )


def approve(
    challenge: Challenge, private_key_bytes: bytes, entered_match_number: str
) -> bytes:
    """Device-side approval: the human enters the match-number they see on the requesting surface;
    if it matches, the device signs the challenge. Returns the Ed25519 signature.

    Raising on mismatch models the phone refusing to sign a number the user didn't actually see.
    """
    if not hmac.compare_digest(str(entered_match_number), challenge.match_number):
        raise ValueError(
            "match-number mismatch -- refusing to sign (possible push-phishing)"
        )
    private = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    return private.sign(challenge.signing_payload())


# ---- server side (the verifier) -------------------------------------- #


class PushVerifier:
    """Issues action-bound challenges and verifies Ed25519 approvals. Transport-agnostic."""

    def __init__(
        self, store: Optional[ChallengeStore] = None, ttl_seconds: int = 120
    ) -> None:
        self.store = store or ChallengeStore()
        self.ttl_seconds = ttl_seconds

    def register_device(self, device: Device) -> None:
        self.store.put_device(device)

    def create_challenge(
        self, device_id: str, action: str, at: Optional[float] = None
    ) -> Challenge:
        """Create a challenge for a SPECIFIC action and 'push' it to the device. The returned
        ``match_number`` is shown on the requesting surface for the human to confirm on the phone.
        """
        if self.store.get_device(device_id) is None:
            raise KeyError(f"unknown device: {device_id}")
        now = time.time() if at is None else at
        challenge = Challenge(
            challenge_id=secrets.token_hex(16),
            device_id=device_id,
            action=action,
            nonce=secrets.token_hex(16),
            match_number=f"{secrets.randbelow(100):02d}",
            created_at=now,
            expires_at=now + self.ttl_seconds,
        )
        self.store.put_challenge(challenge)
        return challenge

    def verify_approval(
        self,
        challenge_id: str,
        signature: bytes,
        presented_match_number: str,
        at: Optional[float] = None,
    ) -> Verdict:
        """Verify a device approval. Single-use: the challenge is consumed on the first verdict."""
        now = time.time() if at is None else at
        challenge = self.store.get_challenge(challenge_id)
        if challenge is None:
            return Verdict(False, "unknown challenge")
        if challenge.status != "pending":
            return Verdict(
                False, f"challenge already {challenge.status}", challenge.action
            )
        if now > challenge.expires_at:
            challenge.status = "expired"
            return Verdict(False, "challenge expired", challenge.action)
        # Do NOT mutate state on a bad match/signature: a wrong guess (or a griefer who only knows the
        # challenge_id) must not be able to permanently deny a pending challenge the real user can still
        # approve. Only a genuine approval consumes it. Explicit user denial goes through deny().
        if not hmac.compare_digest(str(presented_match_number), challenge.match_number):
            return Verdict(False, "match-number mismatch", challenge.action)

        device = self.store.get_device(challenge.device_id)
        if device is None:
            return Verdict(False, "device de-registered", challenge.action)

        try:
            Ed25519PublicKey.from_public_bytes(device.public_key).verify(
                signature, challenge.signing_payload()
            )
        except InvalidSignature:
            return Verdict(False, "invalid signature", challenge.action)

        # Single-use consume. In-memory this is atomic; a real store MUST make this a compare-and-set
        # (see ChallengeStore docstring) or concurrent identical approvals can both pass.
        challenge.status = "consumed"
        return Verdict(True, "approved", challenge.action)

    def deny(self, challenge_id: str) -> None:
        challenge = self.store.get_challenge(challenge_id)
        if challenge is not None and challenge.status == "pending":
            challenge.status = "denied"
