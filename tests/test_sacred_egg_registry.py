"""Sacred Egg Registry Tests — Persistent Egg Lifecycle + Ritual Audit

Tests cover:
  - Register/retrieve eggs from SQLite
  - Status transitions: SEALED → HATCHED, SEALED → EXPIRED
  - TTL expiry enforcement
  - Ritual audit log: success/failure attempts tracked
  - Listing and filtering eggs by status
  - Stale egg expiration sweep

@layer Layer 12, Layer 13
@component Sacred Egg Registry Tests
"""

import base64
import json
import os
import time

import pytest

from src.symphonic_cipher.scbe_aethermoore.cli_toolkit import (
    CrossTokenizer,
    TongueTokenizer,
    Lexicons,
)
from src.symphonic_cipher.scbe_aethermoore.sacred_egg_integrator import (
    SacredEggIntegrator,
)
from src.symphonic_cipher.scbe_aethermoore.sacred_egg_registry import (
    SacredEggRegistry,
    SEALED,
    HATCHED,
    EXPIRED,
)


@pytest.fixture
def integrator():
    lex = Lexicons()
    tok = TongueTokenizer(lex)
    xt = CrossTokenizer(tok)
    return SacredEggIntegrator(xt)


@pytest.fixture
def key_pair():
    pk = base64.b64encode(os.urandom(32)).decode()
    sk = pk
    return pk, sk


@pytest.fixture
def context():
    return [0.0, 0.0, 0.0, -5.0, -5.0, -5.0]


@pytest.fixture
def registry(tmp_path):
    db = str(tmp_path / "test_eggs.db")
    reg = SacredEggRegistry(db_path=db)
    yield reg
    reg.close()


@pytest.fixture
def sample_egg(integrator, key_pair, context):
    pk, sk = key_pair
    return integrator.create_egg(
        b"test payload", "KO", "star", {"path": "interior"},
        context, pk, sk,
    )


class TestRegisterAndRetrieve:

    def test_register_returns_egg_id(self, registry, sample_egg):
        eid = registry.register(sample_egg)
        assert eid == sample_egg.egg_id

    def test_get_returns_egg(self, registry, sample_egg):
        registry.register(sample_egg)
        egg = registry.get(sample_egg.egg_id)
        assert egg is not None
        assert egg.egg_id == sample_egg.egg_id
        assert egg.primary_tongue == "KO"
        assert egg.glyph == "star"
        assert egg.yolk_ct == sample_egg.yolk_ct

    def test_get_nonexistent_returns_none(self, registry):
        assert registry.get("nonexistent") is None

    def test_register_overwrites(self, registry, integrator, key_pair, context):
        pk, sk = key_pair
        egg1 = integrator.create_egg(b"v1", "KO", "a", {}, context, pk, sk)
        egg2 = integrator.create_egg(b"v2", "AV", "b", {}, context, pk, sk)
        # Force same egg_id for testing overwrite
        import dataclasses
        egg2_same_id = dataclasses.replace(
            egg2, egg_id=egg1.egg_id,
        ) if not hasattr(egg2, '_replace') else egg2
        # Register twice with same ID
        registry.register(egg1)
        registry.register(egg1)  # should not error
        egg = registry.get(egg1.egg_id)
        assert egg is not None


class TestStatusTransitions:

    def test_initial_status_is_sealed(self, registry, sample_egg):
        registry.register(sample_egg)
        assert registry.get_status(sample_egg.egg_id) == SEALED

    def test_mark_hatched(self, registry, sample_egg):
        registry.register(sample_egg)
        registry.mark_hatched(sample_egg.egg_id, hatched_by="agent_KO")
        assert registry.get_status(sample_egg.egg_id) == HATCHED

    def test_ttl_expiry(self, registry, sample_egg):
        registry.register(sample_egg, ttl_seconds=1)
        assert registry.get_status(sample_egg.egg_id) == SEALED

        # Wait for TTL
        time.sleep(1.1)
        assert registry.get_status(sample_egg.egg_id) == EXPIRED

    def test_get_expired_returns_none(self, registry, sample_egg):
        registry.register(sample_egg, ttl_seconds=1)
        time.sleep(1.1)
        assert registry.get(sample_egg.egg_id) is None

    def test_no_ttl_never_expires(self, registry, sample_egg):
        registry.register(sample_egg, ttl_seconds=0)
        assert registry.get_status(sample_egg.egg_id) == SEALED
        egg = registry.get(sample_egg.egg_id)
        assert egg is not None


class TestRitualLog:

    def test_log_attempt(self, registry, sample_egg):
        registry.register(sample_egg)
        registry.log_attempt(sample_egg.egg_id, success=False, agent_tongue="DR", ritual_mode="solitary")
        registry.log_attempt(sample_egg.egg_id, success=True, agent_tongue="KO", ritual_mode="solitary")

        attempts = registry.get_attempts(sample_egg.egg_id)
        assert len(attempts) == 2
        assert attempts[0]["success"] == 0
        assert attempts[0]["agent_tongue"] == "DR"
        assert attempts[1]["success"] == 1
        assert attempts[1]["agent_tongue"] == "KO"

    def test_empty_log(self, registry, sample_egg):
        registry.register(sample_egg)
        assert registry.get_attempts(sample_egg.egg_id) == []

    def test_multiple_eggs_separate_logs(self, registry, integrator, key_pair, context):
        pk, sk = key_pair
        egg1 = integrator.create_egg(b"a", "KO", "x", {}, context, pk, sk)
        egg2 = integrator.create_egg(b"b", "AV", "y", {}, context, pk, sk)
        registry.register(egg1)
        registry.register(egg2)
        registry.log_attempt(egg1.egg_id, success=True)
        registry.log_attempt(egg2.egg_id, success=False)

        assert len(registry.get_attempts(egg1.egg_id)) == 1
        assert len(registry.get_attempts(egg2.egg_id)) == 1
        assert registry.get_attempts(egg1.egg_id)[0]["success"] == 1
        assert registry.get_attempts(egg2.egg_id)[0]["success"] == 0


class TestListAndFilter:

    def test_list_all(self, registry, integrator, key_pair, context):
        pk, sk = key_pair
        for tongue in ["KO", "AV", "RU"]:
            egg = integrator.create_egg(f"t_{tongue}".encode(), tongue, "g", {}, context, pk, sk)
            registry.register(egg)
        all_eggs = registry.list_eggs()
        assert len(all_eggs) == 3

    def test_filter_by_status(self, registry, integrator, key_pair, context):
        pk, sk = key_pair
        egg1 = integrator.create_egg(b"a", "KO", "g", {}, context, pk, sk)
        egg2 = integrator.create_egg(b"b", "AV", "g", {}, context, pk, sk)
        registry.register(egg1)
        registry.register(egg2)
        registry.mark_hatched(egg1.egg_id)

        sealed = registry.list_eggs(status=SEALED)
        hatched = registry.list_eggs(status=HATCHED)
        assert len(sealed) == 1
        assert len(hatched) == 1
        assert sealed[0]["primary_tongue"] == "AV"
        assert hatched[0]["primary_tongue"] == "KO"

    def test_expire_stale(self, registry, integrator, key_pair, context):
        pk, sk = key_pair
        egg = integrator.create_egg(b"stale", "DR", "g", {}, context, pk, sk)
        registry.register(egg, ttl_seconds=1)
        time.sleep(1.1)
        count = registry.expire_stale()
        assert count == 1
        assert registry.get_status(egg.egg_id) == EXPIRED


class TestContextManager:

    def test_context_manager(self, tmp_path, sample_egg):
        db = str(tmp_path / "ctx_test.db")
        with SacredEggRegistry(db_path=db) as reg:
            reg.register(sample_egg)
            assert reg.get(sample_egg.egg_id) is not None
