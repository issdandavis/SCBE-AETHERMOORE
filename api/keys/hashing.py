"""API key hashing helpers with migration-safe legacy support."""

from __future__ import annotations

import hashlib
import os
from typing import List


API_KEY_HASH_ITERATIONS = 310_000


def _api_key_hash_salt() -> bytes:
    raw = os.getenv("SCBE_API_KEY_HASH_SALT", "scbe-api-key-hash-v2")
    return raw.encode("utf-8")


def hash_api_key(api_key: str) -> str:
    """Derive a storage hash for API key lookup using PBKDF2-HMAC-SHA256."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        api_key.encode("utf-8"),
        _api_key_hash_salt(),
        API_KEY_HASH_ITERATIONS,
    ).hex()


def legacy_hash_api_key(api_key: str) -> str:
    """Legacy SHA-256 hash kept only for migration compatibility."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def api_key_hash_candidates(api_key: str) -> List[str]:
    """Return primary and legacy hashes so existing records keep working."""
    primary = hash_api_key(api_key)
    legacy = legacy_hash_api_key(api_key)
    return [primary] if primary == legacy else [primary, legacy]
