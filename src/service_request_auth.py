"""Standard HMAC request binding for local SCBE service-to-service calls.

The 14-layer governance score decides what an authenticated request may do.
This module establishes who produced the request, what bytes they approved,
which route they targeted, and when they produced it.  It deliberately uses
standard SHA-256 and HMAC-SHA-256 rather than a custom cryptographic primitive.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import secrets
import time
from typing import Final, Mapping

AUTH_VERSION: Final = "scbe-kernel-v1"
DECISION_VERSION: Final = "scbe-kernel-decision-v2"
MIN_SECRET_BYTES: Final = 32

AUTH_HEADER_VERSION: Final = "X-SCBE-Auth-Version"
AUTH_HEADER_TIMESTAMP: Final = "X-SCBE-Timestamp"
AUTH_HEADER_NONCE: Final = "X-SCBE-Nonce"
AUTH_HEADER_SIGNATURE: Final = "X-SCBE-Signature"


def validate_service_secret(secret: str) -> bytes:
    """Return UTF-8 key bytes or reject keys below the 256-bit byte floor."""
    key = secret.encode("utf-8")
    if len(key) < MIN_SECRET_BYTES:
        raise ValueError(
            f"service secret must be at least {MIN_SECRET_BYTES} UTF-8 bytes"
        )
    return key


def canonical_service_request(
    *,
    method: str,
    path: str,
    timestamp_ms: int,
    nonce: str,
    body: bytes,
) -> bytes:
    """Bind method, destination, freshness fields, and exact body bytes."""
    normalized_method = method.strip().upper()
    if not normalized_method or "\n" in normalized_method:
        raise ValueError("invalid service request method")
    if not path.startswith("/") or "\n" in path:
        raise ValueError("service request path must be an absolute path")
    if timestamp_ms <= 0:
        raise ValueError("service request timestamp must be positive")
    if not nonce or "\n" in nonce:
        raise ValueError("service request nonce is required")

    body_digest = hashlib.sha256(body).hexdigest()
    canonical = "\n".join(
        (
            AUTH_VERSION,
            normalized_method,
            path,
            str(timestamp_ms),
            nonce,
            body_digest,
        )
    )
    return canonical.encode("utf-8")


def sign_service_request(
    *,
    secret: str,
    method: str,
    path: str,
    body: bytes,
    timestamp_ms: int | None = None,
    nonce: str | None = None,
) -> dict[str, str]:
    """Create headers for a replay-bounded, destination-bound request."""
    key = validate_service_secret(secret)
    issued_at = int(time.time() * 1000) if timestamp_ms is None else int(timestamp_ms)
    request_nonce = secrets.token_urlsafe(18) if nonce is None else nonce
    canonical = canonical_service_request(
        method=method,
        path=path,
        timestamp_ms=issued_at,
        nonce=request_nonce,
        body=body,
    )
    signature = hmac.new(key, canonical, hashlib.sha256).hexdigest()
    return {
        AUTH_HEADER_VERSION: AUTH_VERSION,
        AUTH_HEADER_TIMESTAMP: str(issued_at),
        AUTH_HEADER_NONCE: request_nonce,
        AUTH_HEADER_SIGNATURE: signature,
    }


def canonical_decision_receipt(
    *,
    request_method: str,
    request_path: str,
    request_digest: str,
    request_nonce: str,
    timestamp: str,
    action: str,
    confidence: float,
    state_vector: Mapping[str, float],
    reason: str,
) -> bytes:
    """Serialize a runner decision exactly as the JavaScript verifier does."""

    method = request_method.strip().upper()
    digest = request_digest.lower()
    numeric = (
        float(confidence),
        float(state_vector.get("coherence", math.nan)),
        float(state_vector.get("energy", math.nan)),
        float(state_vector.get("drift", math.nan)),
    )
    if not method or "\n" in method:
        raise ValueError("invalid receipt method")
    if not request_path.startswith("/") or "\n" in request_path:
        raise ValueError("invalid receipt path")
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ValueError("invalid receipt request digest")
    if not 22 <= len(request_nonce) <= 128 or any(
        not (character.isascii() and (character.isalnum() or character in "_-"))
        for character in request_nonce
    ):
        raise ValueError("invalid receipt nonce")
    if not timestamp or not action or not reason:
        raise ValueError("incomplete decision receipt")
    if not all(math.isfinite(value) for value in numeric):
        raise ValueError("non-finite decision receipt value")

    fields = [
        DECISION_VERSION,
        method,
        request_path,
        digest,
        request_nonce,
        timestamp,
        action,
        *(f"{value:.4f}" for value in numeric),
        reason,
    ]
    return json.dumps(fields, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def sign_decision_receipt(*, secret: str, **receipt: object) -> str:
    key = validate_service_secret(secret)
    canonical = canonical_decision_receipt(**receipt)  # type: ignore[arg-type]
    return hmac.new(key, canonical, hashlib.sha256).hexdigest()


def verify_decision_receipt(
    *,
    secret: str,
    signature: str,
    **receipt: object,
) -> bool:
    try:
        expected = sign_decision_receipt(secret=secret, **receipt)
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(expected, signature)
