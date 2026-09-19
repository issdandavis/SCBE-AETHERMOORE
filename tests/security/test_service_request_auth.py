from __future__ import annotations

import hashlib

import pytest

from src.service_request_auth import (
    AUTH_HEADER_NONCE,
    AUTH_HEADER_SIGNATURE,
    AUTH_HEADER_TIMESTAMP,
    AUTH_HEADER_VERSION,
    AUTH_VERSION,
    DECISION_VERSION,
    canonical_service_request,
    sign_decision_receipt,
    sign_service_request,
    validate_service_secret,
    verify_decision_receipt,
)

SERVICE_KEY = "0123456789abcdef0123456789abcdef"


def test_service_request_auth_matches_public_cross_language_vector() -> None:
    headers = sign_service_request(
        secret=SERVICE_KEY,
        method="post",
        path="/api/run",
        body=b"x",
        timestamp_ms=1_700_000_000_000,
        nonce="ABCDEFGHIJKLMNOPQRSTUV",
    )

    assert headers == {
        AUTH_HEADER_VERSION: AUTH_VERSION,
        AUTH_HEADER_TIMESTAMP: "1700000000000",
        AUTH_HEADER_NONCE: "ABCDEFGHIJKLMNOPQRSTUV",
        AUTH_HEADER_SIGNATURE: "791d5491861f47a3826e1136548c3cd0fc552f5954f3c2dacb0fac0292c0854a",
    }


def test_service_request_auth_binds_method_path_and_body() -> None:
    common = {
        "timestamp_ms": 1_700_000_000_000,
        "nonce": "ABCDEFGHIJKLMNOPQRSTUV",
    }
    base = canonical_service_request(
        method="POST", path="/api/run", body=b"x", **common
    )

    assert (
        canonical_service_request(method="PUT", path="/api/run", body=b"x", **common)
        != base
    )
    assert (
        canonical_service_request(
            method="POST", path="/api/preflight", body=b"x", **common
        )
        != base
    )
    assert (
        canonical_service_request(method="POST", path="/api/run", body=b"y", **common)
        != base
    )


def test_service_request_auth_rejects_short_secret() -> None:
    with pytest.raises(ValueError, match="at least 32"):
        validate_service_secret("short")


def test_service_request_auth_generates_fresh_nonce() -> None:
    first = sign_service_request(
        secret=SERVICE_KEY, method="POST", path="/api/run", body=b"x"
    )
    second = sign_service_request(
        secret=SERVICE_KEY, method="POST", path="/api/run", body=b"x"
    )

    assert first[AUTH_HEADER_NONCE] != second[AUTH_HEADER_NONCE]
    assert first[AUTH_HEADER_SIGNATURE] != second[AUTH_HEADER_SIGNATURE]


def test_decision_receipt_matches_javascript_vector_and_binds_request() -> None:
    receipt = {
        "request_method": "POST",
        "request_path": "/api/run",
        "request_digest": hashlib.sha256(b"x").hexdigest(),
        "request_nonce": "ABCDEFGHIJKLMNOPQRSTUV",
        "timestamp": "2026-09-19T12:34:56.000Z",
        "action": "ALLOW",
        "confidence": 0.92,
        "state_vector": {"coherence": 1, "energy": 0.75, "drift": 0},
        "reason": "Verification scores passed policy.",
    }
    signature = sign_decision_receipt(secret=SERVICE_KEY, **receipt)

    assert DECISION_VERSION == "scbe-kernel-decision-v2"
    assert (
        signature == "d3bf7a3822ba5e783612e10840a960014d7ac95f494594c430d5aaa0cc1a1704"
    )
    assert verify_decision_receipt(secret=SERVICE_KEY, signature=signature, **receipt)
    changed = {**receipt, "request_path": "/api/preflight"}
    assert not verify_decision_receipt(secret=SERVICE_KEY, signature=signature, **changed)
