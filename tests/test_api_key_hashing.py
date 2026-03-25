from __future__ import annotations

import pytest

try:
    from api.keys.generator import generate_api_key
    from api.keys.hashing import api_key_hash_candidates, hash_api_key, legacy_hash_api_key
except ImportError:
    generate_api_key = None
    api_key_hash_candidates = hash_api_key = legacy_hash_api_key = None

pytestmark = pytest.mark.skipif(
    generate_api_key is None, reason="api.keys modules not importable (missing sqlalchemy?)"
)


def test_api_key_hash_uses_pbkdf2_and_differs_from_legacy_sha256() -> None:
    raw_key = "scbe_test_example_key"

    current = hash_api_key(raw_key)
    legacy = legacy_hash_api_key(raw_key)

    assert len(current) == 64
    assert current != legacy


def test_api_key_hash_candidates_include_legacy_for_migration() -> None:
    raw_key = "scbe_test_example_key"
    candidates = api_key_hash_candidates(raw_key)

    assert hash_api_key(raw_key) in candidates
    assert legacy_hash_api_key(raw_key) in candidates


def test_generate_api_key_persists_hardened_hash() -> None:
    raw_key, record = generate_api_key("cust_123")

    assert record.key_hash == hash_api_key(raw_key)
    assert record.key_hash != legacy_hash_api_key(raw_key)
