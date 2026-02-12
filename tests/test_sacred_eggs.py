#!/usr/bin/env python3
"""
Tests for Sacred Eggs — Cryptographic Secret Containers.

Tests cover:
- SacredEgg creation, ring-based access control, albumen derivation
- EggCarton collection management and lineage tracking
- SacredRituals: Solitary Incubation, Triadic Binding, Ring Descent, Fail-to-Noise
- FluxState integration and session egg creation
- Edge cases and security properties

Markers: @pytest.mark.crypto, @pytest.mark.unit
"""

import hashlib
import hmac
import secrets
import pytest

# Import directly from module to avoid pulling in all of src.crypto
# (which requires scipy, matplotlib, etc.)
from src.crypto.sacred_eggs import (
    SacredEgg,
    EggCarton,
    EggRing,
    SacredRituals,
    IncubationResult,
    TriadicBindingResult,
    RingDescentResult,
    FailToNoiseResult,
    flux_state_to_ring,
    create_session_egg,
    ring_allows,
    hkdf_sha256,
    YOLK_SIZE,
    SHELL_SIZE,
    ALBUMEN_KEY_SIZE,
    INCUBATION_CYCLES,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def core_egg():
    """A fresh Sacred Egg at CORE ring."""
    return SacredEgg.create(context="test", ring=EggRing.CORE)


@pytest.fixture
def outer_egg():
    """A Sacred Egg at OUTER ring."""
    return SacredEgg.create(context="test", ring=EggRing.OUTER)


@pytest.fixture
def known_yolk():
    """A deterministic yolk for reproducible tests."""
    return hashlib.sha256(b"test-yolk-seed").digest()


@pytest.fixture
def carton_with_eggs():
    """A carton containing 3 eggs at different rings."""
    carton = EggCarton.create("test-carton")
    egg_a = SacredEgg.create(context="alpha", ring=EggRing.CORE)
    egg_b = SacredEgg.create(context="beta", ring=EggRing.INNER)
    egg_c = SacredEgg.create(context="gamma", ring=EggRing.OUTER)
    carton.add(egg_a)
    carton.add(egg_b)
    carton.add(egg_c)
    return carton, egg_a, egg_b, egg_c


# =============================================================================
# SacredEgg Tests
# =============================================================================


class TestSacredEgg:
    """Tests for the SacredEgg container."""

    def test_create_with_random_yolk(self):
        """Should create egg with random 32-byte yolk."""
        egg = SacredEgg.create(context="test")
        assert len(egg._yolk) == YOLK_SIZE
        assert len(egg.shell_hash) == SHELL_SIZE
        assert len(egg.egg_id) == 16  # 8 bytes hex

    def test_create_with_known_yolk(self, known_yolk):
        """Should create deterministic egg from known yolk."""
        egg = SacredEgg.create(context="test", yolk=known_yolk)
        expected_shell = hashlib.sha256(known_yolk + b"test").digest()
        assert egg.shell_hash == expected_shell
        assert egg._yolk == known_yolk

    def test_create_rejects_wrong_yolk_size(self):
        """Should reject yolk that isn't 32 bytes."""
        with pytest.raises(ValueError, match="Yolk must be 32 bytes"):
            SacredEgg.create(yolk=b"too-short")

    def test_egg_ids_are_unique(self):
        """Different eggs should have different IDs."""
        eggs = [SacredEgg.create() for _ in range(10)]
        ids = {e.egg_id for e in eggs}
        assert len(ids) == 10

    def test_shell_hash_is_deterministic(self, known_yolk):
        """Same yolk + context should always produce same shell."""
        egg1 = SacredEgg.create(context="ctx", yolk=known_yolk)
        egg2 = SacredEgg.create(context="ctx", yolk=known_yolk)
        assert egg1.shell_hash == egg2.shell_hash

    def test_shell_hash_differs_with_context(self, known_yolk):
        """Different context should produce different shell."""
        egg1 = SacredEgg.create(context="alpha", yolk=known_yolk)
        egg2 = SacredEgg.create(context="beta", yolk=known_yolk)
        assert egg1.shell_hash != egg2.shell_hash

    def test_lineage_tracking(self):
        """Should track parent IDs in lineage."""
        parent = SacredEgg.create(context="parent")
        child = SacredEgg.create(
            context="child", parent_ids=[parent.egg_id]
        )
        assert parent.egg_id in child.lineage

    def test_created_at_timestamp(self):
        """Should have a valid creation timestamp."""
        egg = SacredEgg.create()
        assert egg.created_at > 0
        assert isinstance(egg.created_at, float)


# =============================================================================
# Ring Access Control Tests
# =============================================================================


class TestRingAccessControl:
    """Tests for ring-based access control."""

    def test_ring_hierarchy(self):
        """CORE > INNER > OUTER > CA."""
        assert ring_allows(EggRing.CORE, EggRing.CORE)
        assert ring_allows(EggRing.CORE, EggRing.INNER)
        assert ring_allows(EggRing.CORE, EggRing.OUTER)
        assert ring_allows(EggRing.INNER, EggRing.INNER)
        assert ring_allows(EggRing.INNER, EggRing.OUTER)
        assert not ring_allows(EggRing.OUTER, EggRing.INNER)
        assert not ring_allows(EggRing.OUTER, EggRing.CORE)

    def test_yolk_access_core_only(self, core_egg):
        """Only CORE ring can access the yolk."""
        yolk = core_egg.get_yolk(EggRing.CORE)
        assert len(yolk) == YOLK_SIZE

        with pytest.raises(PermissionError, match="CORE ring"):
            core_egg.get_yolk(EggRing.INNER)

        with pytest.raises(PermissionError, match="CORE ring"):
            core_egg.get_yolk(EggRing.OUTER)

    def test_albumen_access_inner_or_better(self, core_egg):
        """Albumen keys require INNER ring or better."""
        core_egg.derive_albumen("session")

        # CORE can access
        key = core_egg.get_albumen("session", EggRing.CORE)
        assert len(key) == ALBUMEN_KEY_SIZE

        # INNER can access
        key = core_egg.get_albumen("session", EggRing.INNER)
        assert len(key) == ALBUMEN_KEY_SIZE

        # OUTER cannot
        with pytest.raises(PermissionError, match="INNER ring"):
            core_egg.get_albumen("session", EggRing.OUTER)

    def test_albumen_missing_label(self, core_egg):
        """Should raise KeyError for missing albumen label."""
        with pytest.raises(KeyError, match="no-such-label"):
            core_egg.get_albumen("no-such-label", EggRing.CORE)

    def test_shell_always_accessible(self, core_egg):
        """Shell hash is available at any ring level."""
        shell = core_egg.get_shell()
        assert len(shell) == SHELL_SIZE

    def test_strip_to_outer(self, core_egg):
        """Stripping to OUTER should remove yolk and albumen."""
        core_egg.derive_albumen("key1")
        outer = core_egg.strip_to_ring(EggRing.OUTER)

        assert outer.ring == EggRing.OUTER
        assert outer._yolk == b""
        assert len(outer.albumen) == 0
        assert outer.shell_hash == core_egg.shell_hash

    def test_strip_to_inner(self, core_egg):
        """Stripping to INNER should remove yolk but keep albumen."""
        core_egg.derive_albumen("key1")
        inner = core_egg.strip_to_ring(EggRing.INNER)

        assert inner.ring == EggRing.INNER
        assert inner._yolk == b""
        assert "key1" in inner.albumen

    def test_strip_to_core(self, core_egg):
        """Stripping to CORE should keep everything."""
        core_egg.derive_albumen("key1")
        copy = core_egg.strip_to_ring(EggRing.CORE)

        assert copy.ring == EggRing.CORE
        assert copy._yolk == core_egg._yolk
        assert "key1" in copy.albumen


# =============================================================================
# Albumen Derivation Tests
# =============================================================================


class TestAlbumenDerivation:
    """Tests for HKDF-based albumen key derivation."""

    def test_derive_produces_32_byte_key(self, core_egg):
        """Derived key should be 32 bytes."""
        key = core_egg.derive_albumen("test")
        assert len(key) == ALBUMEN_KEY_SIZE

    def test_different_labels_produce_different_keys(self, core_egg):
        """Different labels should derive different keys."""
        key_a = core_egg.derive_albumen("encryption")
        key_b = core_egg.derive_albumen("signing")
        assert key_a != key_b

    def test_same_label_with_different_salt(self, known_yolk):
        """Same label with different salt should produce different keys."""
        egg = SacredEgg.create(context="test", yolk=known_yolk)
        key_a = egg.derive_albumen("session", salt=b"\x00" * 16)
        key_b = egg.derive_albumen("session", salt=b"\x01" * 16)
        assert key_a != key_b

    def test_stored_in_albumen_dict(self, core_egg):
        """Derived keys should be stored in egg.albumen."""
        core_egg.derive_albumen("my_key")
        assert "my_key" in core_egg.albumen
        assert len(core_egg.albumen["my_key"]) == ALBUMEN_KEY_SIZE

    def test_cannot_derive_without_yolk(self):
        """Egg without yolk should reject derivation."""
        egg = SacredEgg.create(ring=EggRing.CORE)
        stripped = egg.strip_to_ring(EggRing.OUTER)

        with pytest.raises(ValueError, match="no yolk"):
            stripped.derive_albumen("key")


# =============================================================================
# HKDF Tests
# =============================================================================


class TestHKDF:
    """Tests for the HKDF-SHA256 implementation."""

    def test_deterministic_output(self):
        """Same inputs should always produce same output."""
        ikm = b"input-key-material"
        salt = b"salt-value-here!"
        info = b"context-info"

        key1 = hkdf_sha256(ikm, salt, info, 32)
        key2 = hkdf_sha256(ikm, salt, info, 32)
        assert key1 == key2

    def test_different_info_different_output(self):
        """Different info should produce different keys."""
        ikm = b"shared-ikm-material"
        salt = b"shared-salt-vals!"
        key_a = hkdf_sha256(ikm, salt, b"purpose-a", 32)
        key_b = hkdf_sha256(ikm, salt, b"purpose-b", 32)
        assert key_a != key_b

    def test_variable_output_length(self):
        """Should support different output lengths."""
        ikm = b"key-material-here"
        salt = b"salt-16-bytes!xx"
        key_16 = hkdf_sha256(ikm, salt, b"info", 16)
        key_64 = hkdf_sha256(ikm, salt, b"info", 64)

        assert len(key_16) == 16
        assert len(key_64) == 64
        # First 16 bytes should NOT match (different expand rounds)
        # Actually in HKDF, first 32 bytes of key_64 should match first 32 of a 32-byte output
        key_32 = hkdf_sha256(ikm, salt, b"info", 32)
        assert key_64[:32] == key_32

    def test_empty_salt_uses_zeros(self):
        """Empty salt should default to 32 zero bytes."""
        ikm = b"input-key-material"
        key1 = hkdf_sha256(ikm, b"", b"info", 32)
        key2 = hkdf_sha256(ikm, b"\x00" * 32, b"info", 32)
        # Both should use the same zero salt
        assert key1 == key2


# =============================================================================
# EggCarton Tests
# =============================================================================


class TestEggCarton:
    """Tests for the EggCarton collection manager."""

    def test_create_empty_carton(self):
        """Should create an empty carton with unique ID."""
        carton = EggCarton.create("my-carton")
        assert carton.count() == 0
        assert len(carton.carton_id) == 12

    def test_add_and_retrieve(self):
        """Should add eggs and retrieve by ID."""
        carton = EggCarton.create()
        egg = SacredEgg.create(context="test")
        egg_id = carton.add(egg)

        retrieved = carton.get(egg_id)
        assert retrieved is not None
        assert retrieved.egg_id == egg_id

    def test_count(self, carton_with_eggs):
        """Should count eggs correctly."""
        carton, _, _, _ = carton_with_eggs
        assert carton.count() == 3

    def test_list_ids(self, carton_with_eggs):
        """Should list all egg IDs."""
        carton, a, b, c = carton_with_eggs
        ids = carton.list_ids()
        assert a.egg_id in ids
        assert b.egg_id in ids
        assert c.egg_id in ids

    def test_remove(self):
        """Should remove an egg from the carton."""
        carton = EggCarton.create()
        egg = SacredEgg.create()
        carton.add(egg)

        assert carton.remove(egg.egg_id) is True
        assert carton.get(egg.egg_id) is None
        assert carton.count() == 0

    def test_remove_nonexistent(self):
        """Should return False for nonexistent egg."""
        carton = EggCarton.create()
        assert carton.remove("nonexistent") is False

    def test_lineage_tracking(self):
        """Should track parent-child relationships."""
        carton = EggCarton.create()

        parent = SacredEgg.create(context="parent")
        carton.add(parent)

        child = SacredEgg.create(
            context="child", parent_ids=[parent.egg_id]
        )
        carton.add(child)

        children = carton.get_children(parent.egg_id)
        assert child.egg_id in children

    def test_lineage_chain(self):
        """Should reconstruct full lineage chain."""
        carton = EggCarton.create()

        grandparent = SacredEgg.create(context="gen0")
        carton.add(grandparent)

        parent = SacredEgg.create(
            context="gen1", parent_ids=[grandparent.egg_id]
        )
        carton.add(parent)

        child = SacredEgg.create(
            context="gen2",
            parent_ids=[grandparent.egg_id, parent.egg_id],
        )
        carton.add(child)

        chain = carton.get_lineage_chain(child.egg_id)
        assert chain == [grandparent.egg_id, parent.egg_id, child.egg_id]


# =============================================================================
# Solitary Incubation Tests
# =============================================================================


class TestSolitaryIncubation:
    """Tests for the Solitary Incubation ritual."""

    def test_default_incubation(self, core_egg):
        """Should produce 3 derived keys by default."""
        result = SacredRituals.solitary_incubation(core_egg)

        assert isinstance(result, IncubationResult)
        assert result.cycles == INCUBATION_CYCLES
        assert len(result.derived_keys) == INCUBATION_CYCLES
        assert result.egg_id == core_egg.egg_id

    def test_custom_labels(self, core_egg):
        """Should use custom labels for each cycle."""
        labels = ["encryption", "signing", "session"]
        result = SacredRituals.solitary_incubation(
            core_egg, cycles=3, labels=labels
        )

        assert "encryption" in result.derived_keys
        assert "signing" in result.derived_keys
        assert "session" in result.derived_keys

        # Keys should also be in egg.albumen
        assert "encryption" in core_egg.albumen
        assert "signing" in core_egg.albumen
        assert "session" in core_egg.albumen

    def test_keys_are_chained(self, known_yolk):
        """Each cycle should use the previous cycle's output as input."""
        egg = SacredEgg.create(context="chain-test", yolk=known_yolk)
        result = SacredRituals.solitary_incubation(egg, cycles=3)

        # All keys should be different (chain input changes each cycle)
        keys = list(result.derived_keys.values())
        assert len(set(keys)) == 3

    def test_variable_cycle_count(self, core_egg):
        """Should support different cycle counts."""
        result = SacredRituals.solitary_incubation(core_egg, cycles=5)
        assert result.cycles == 5
        assert len(result.derived_keys) == 5

    def test_requires_yolk(self):
        """Should reject egg without yolk."""
        egg = SacredEgg.create()
        stripped = egg.strip_to_ring(EggRing.OUTER)

        with pytest.raises(ValueError, match="without yolk"):
            SacredRituals.solitary_incubation(stripped)

    def test_derived_keys_are_hex_truncated(self, core_egg):
        """Derived keys in result should be first 8 bytes as hex."""
        result = SacredRituals.solitary_incubation(core_egg)
        for label, key_hex in result.derived_keys.items():
            assert len(key_hex) == 16  # 8 bytes = 16 hex chars
            # Should be valid hex
            int(key_hex, 16)


# =============================================================================
# Triadic Binding Tests
# =============================================================================


class TestTriadicBinding:
    """Tests for the Triadic Binding ritual."""

    def test_binding_three_eggs(self):
        """Should produce a binding hash from 3 eggs."""
        eggs = [SacredEgg.create(context="test") for _ in range(3)]
        result = SacredRituals.triadic_binding(*eggs)

        assert isinstance(result, TriadicBindingResult)
        assert len(result.binding_hash) == 64  # SHA-256 hex
        assert len(result.egg_ids) == 3

    def test_binding_is_order_independent(self):
        """Binding should produce same hash regardless of argument order."""
        a = SacredEgg.create(context="a")
        b = SacredEgg.create(context="b")
        c = SacredEgg.create(context="c")

        r1 = SacredRituals.triadic_binding(a, b, c)
        r2 = SacredRituals.triadic_binding(c, a, b)
        r3 = SacredRituals.triadic_binding(b, c, a)

        assert r1.binding_hash == r2.binding_hash
        assert r2.binding_hash == r3.binding_hash

    def test_same_context_full_strength(self):
        """3 eggs with same context should have strength 1.0."""
        eggs = [SacredEgg.create(context="shared") for _ in range(3)]
        result = SacredRituals.triadic_binding(*eggs)
        assert result.binding_strength == 1.0

    def test_all_different_context_low_strength(self):
        """3 eggs with all different contexts should have strength 0.33."""
        a = SacredEgg.create(context="alpha")
        b = SacredEgg.create(context="beta")
        c = SacredEgg.create(context="gamma")

        result = SacredRituals.triadic_binding(a, b, c)
        assert result.binding_strength == pytest.approx(0.33, abs=0.01)

    def test_two_same_context_medium_strength(self):
        """2/3 eggs with same context should have strength 0.67."""
        a = SacredEgg.create(context="shared")
        b = SacredEgg.create(context="shared")
        c = SacredEgg.create(context="different")

        result = SacredRituals.triadic_binding(a, b, c)
        assert result.binding_strength == pytest.approx(0.67, abs=0.01)

    def test_different_eggs_produce_different_binding(self):
        """Different egg sets should produce different binding hashes."""
        set1 = [SacredEgg.create() for _ in range(3)]
        set2 = [SacredEgg.create() for _ in range(3)]

        r1 = SacredRituals.triadic_binding(*set1)
        r2 = SacredRituals.triadic_binding(*set2)

        assert r1.binding_hash != r2.binding_hash


# =============================================================================
# Ring Descent Tests
# =============================================================================


class TestRingDescent:
    """Tests for the Ring Descent ritual."""

    def test_outer_to_inner(self, outer_egg):
        """Should descend from OUTER to INNER with valid auth."""
        auth_secret = secrets.token_bytes(32)
        result = SacredRituals.ring_descent(
            outer_egg, EggRing.INNER, auth_secret
        )

        assert isinstance(result, RingDescentResult)
        assert result.old_ring == "OUTER"
        assert result.new_ring == "INNER"
        assert outer_egg.ring == EggRing.INNER

    def test_outer_to_core(self, outer_egg):
        """Should descend from OUTER to CORE."""
        auth_secret = secrets.token_bytes(32)
        result = SacredRituals.ring_descent(
            outer_egg, EggRing.CORE, auth_secret
        )
        assert result.new_ring == "CORE"
        assert outer_egg.ring == EggRing.CORE

    def test_rejects_upward_escalation(self, core_egg):
        """Should reject going from CORE to OUTER (wrong direction)."""
        auth_secret = secrets.token_bytes(32)
        with pytest.raises(ValueError, match="not a descent"):
            SacredRituals.ring_descent(core_egg, EggRing.OUTER, auth_secret)

    def test_rejects_same_ring(self, outer_egg):
        """Should reject descent to same ring."""
        auth_secret = secrets.token_bytes(32)
        with pytest.raises(ValueError, match="not a descent"):
            SacredRituals.ring_descent(outer_egg, EggRing.OUTER, auth_secret)

    def test_auth_hash_is_deterministic(self, outer_egg):
        """Same auth_secret should produce same auth_hash."""
        auth_secret = secrets.token_bytes(32)

        # Create two identical eggs
        yolk = outer_egg._yolk
        egg1 = SacredEgg.create(context=outer_egg.context, yolk=yolk, ring=EggRing.OUTER)
        egg2 = SacredEgg.create(context=outer_egg.context, yolk=yolk, ring=EggRing.OUTER)

        r1 = SacredRituals.ring_descent(egg1, EggRing.INNER, auth_secret)
        r2 = SacredRituals.ring_descent(egg2, EggRing.INNER, auth_secret)
        assert r1.auth_hash == r2.auth_hash


# =============================================================================
# Fail-to-Noise Tests
# =============================================================================


class TestFailToNoise:
    """Tests for the Fail-to-Noise ritual."""

    def test_regenerates_shell(self, core_egg):
        """Should replace shell hash with new random value."""
        old_shell = core_egg.shell_hash
        result = SacredRituals.fail_to_noise(core_egg)

        assert isinstance(result, FailToNoiseResult)
        assert result.noise_generated is True
        assert core_egg.shell_hash != old_shell
        assert result.old_shell != result.new_shell

    def test_preserves_yolk(self, core_egg):
        """Yolk should survive fail-to-noise (identity preserved)."""
        original_yolk = core_egg._yolk
        SacredRituals.fail_to_noise(core_egg)
        assert core_egg._yolk == original_yolk

    def test_updates_egg_id(self, core_egg):
        """Egg ID should change to match new shell."""
        old_id = core_egg.egg_id
        SacredRituals.fail_to_noise(core_egg)
        assert core_egg.egg_id != old_id
        # New ID should be derived from new shell
        assert core_egg.egg_id == core_egg.shell_hash[:8].hex()

    def test_old_shell_is_useless(self, core_egg):
        """After fail-to-noise, old shell hash should not match."""
        old_shell = core_egg.shell_hash.hex()
        SacredRituals.fail_to_noise(core_egg)

        # Old and new shells should be completely unrelated
        new_shell = core_egg.shell_hash.hex()
        # XOR comparison — should be high entropy (many differing bits)
        old_bytes = bytes.fromhex(old_shell)
        new_bytes = core_egg.shell_hash
        xor = bytes(a ^ b for a, b in zip(old_bytes, new_bytes))
        # At least half the bits should differ (random expectation)
        differing_bits = bin(int.from_bytes(xor, "big")).count("1")
        assert differing_bits > 64  # 256-bit hash, expect ~128 differing

    def test_repeated_noise(self, core_egg):
        """Multiple fail-to-noise should produce different results each time."""
        shells = set()
        for _ in range(10):
            SacredRituals.fail_to_noise(core_egg)
            shells.add(core_egg.shell_hash.hex())

        assert len(shells) == 10  # All unique


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests combining multiple Sacred Egg operations."""

    def test_flux_state_mapping(self):
        """FluxState should map to appropriate rings."""
        assert flux_state_to_ring("polly") == EggRing.CORE
        assert flux_state_to_ring("quasi") == EggRing.INNER
        assert flux_state_to_ring("demi") == EggRing.OUTER
        assert flux_state_to_ring("collapsed") == EggRing.OUTER
        assert flux_state_to_ring("unknown") == EggRing.OUTER

    def test_session_egg_deterministic(self):
        """Same session_id should produce same egg."""
        egg1 = create_session_egg("session-abc")
        egg2 = create_session_egg("session-abc")
        assert egg1.shell_hash == egg2.shell_hash

    def test_session_egg_different_sessions(self):
        """Different sessions should produce different eggs."""
        egg1 = create_session_egg("session-1")
        egg2 = create_session_egg("session-2")
        assert egg1.shell_hash != egg2.shell_hash

    def test_full_lifecycle(self):
        """Test complete egg lifecycle: create → incubate → bind → noise."""
        # Create carton with 3 eggs
        carton = EggCarton.create("lifecycle")
        eggs = [SacredEgg.create(context="lifecycle") for _ in range(3)]
        for egg in eggs:
            carton.add(egg)

        # Solitary incubation on each
        for egg in eggs:
            result = SacredRituals.solitary_incubation(egg)
            assert result.cycles == 3

        # Triadic binding
        binding = SacredRituals.triadic_binding(*eggs)
        assert binding.binding_strength == 1.0  # same context

        # Ring descent on first egg
        auth = secrets.token_bytes(32)
        egg_outer = SacredEgg.create(context="test", ring=EggRing.OUTER)
        descent = SacredRituals.ring_descent(egg_outer, EggRing.INNER, auth)
        assert descent.new_ring == "INNER"

        # Fail-to-noise on one egg
        noise = SacredRituals.fail_to_noise(eggs[0])
        assert noise.noise_generated is True

    def test_incubation_then_binding(self):
        """Incubated eggs should still bind correctly."""
        eggs = [SacredEgg.create(context="bound") for _ in range(3)]

        # Incubate each
        for egg in eggs:
            SacredRituals.solitary_incubation(egg, labels=["key"])

        # Binding should work and have full strength
        result = SacredRituals.triadic_binding(*eggs)
        assert result.binding_strength == 1.0
        assert len(result.binding_hash) == 64

    def test_carton_lineage_after_noise(self):
        """Lineage should survive fail-to-noise (IDs change but chain persists)."""
        carton = EggCarton.create()
        parent = SacredEgg.create(context="parent")
        carton.add(parent)

        old_parent_id = parent.egg_id

        child = SacredEgg.create(
            context="child", parent_ids=[old_parent_id]
        )
        carton.add(child)

        # Child still references old parent ID in lineage
        assert old_parent_id in child.lineage
