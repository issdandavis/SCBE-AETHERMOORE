"""Tests for the Braided Dual-Primitive Key Vault.

Covers: braid word operations, dual hashing, strand initialization,
crossing mechanics, vault CRUD, key rotation, TTL expiry, and
the non-commutativity property that gives topological security.
"""

from __future__ import annotations

import time


from src.crypto.braid_vault import (
    BraidCrossing,
    BraidStrand,
    BraidVault,
    BraidWord,
    TONGUE_PAIRS,
    _apply_braid,
    _apply_crossing,
    _dual_hash,
    _finalize,
    _h_a,
    _h_b,
    _init_strands,
    _xor_bytes,
    create_vault,
    create_vault_deterministic,
)

# ── Dual Hash Primitives ─────────────────────────────────────────────────


class TestDualPrimitives:
    def test_h_a_produces_32_bytes(self):
        assert len(_h_a(b"test")) == 32

    def test_h_b_produces_32_bytes(self):
        assert len(_h_b(b"test")) == 32

    def test_h_a_and_h_b_differ(self):
        """SHA3-256 and BLAKE2b must produce different digests."""
        assert _h_a(b"same input") != _h_b(b"same input")

    def test_dual_hash_returns_pair(self):
        a, b = _dual_hash(b"data")
        assert len(a) == 32 and len(b) == 32
        assert a != b

    def test_h_a_is_deterministic(self):
        assert _h_a(b"x") == _h_a(b"x")

    def test_h_b_is_deterministic(self):
        assert _h_b(b"x") == _h_b(b"x")

    def test_xor_identity(self):
        data = b"\xaa" * 32
        assert _xor_bytes(data, b"\x00" * 32) == data

    def test_xor_self_is_zero(self):
        data = _h_a(b"anything")
        assert _xor_bytes(data, data) == b"\x00" * 32


# ── Braid Strands ────────────────────────────────────────────────────────


class TestBraidStrand:
    def test_from_seed_produces_dual_channels(self):
        s = BraidStrand.from_seed(b"seed")
        assert len(s.h_a) == 32 and len(s.h_b) == 32
        assert s.h_a != s.h_b

    def test_context_changes_output(self):
        s1 = BraidStrand.from_seed(b"seed", b"ctx_a")
        s2 = BraidStrand.from_seed(b"seed", b"ctx_b")
        assert s1.h_a != s2.h_a

    def test_as_bytes_is_64(self):
        s = BraidStrand.from_seed(b"x")
        assert len(s.as_bytes()) == 64

    def test_rehash_swaps_primitives(self):
        s = BraidStrand.from_seed(b"data")
        r = s.rehash()
        # Rehash feeds each channel through the OTHER primitive
        assert r.h_a == _h_a(s.h_b)
        assert r.h_b == _h_b(s.h_a)


# ── Tongue Pair Initialization ───────────────────────────────────────────


class TestStrandInit:
    def test_init_produces_three_strands(self):
        strands = _init_strands(b"master")
        assert len(strands) == 3

    def test_strands_are_all_different(self):
        strands = _init_strands(b"master")
        keys = [s.as_bytes() for s in strands]
        assert keys[0] != keys[1] != keys[2]

    def test_tongue_pairs_are_correct(self):
        assert len(TONGUE_PAIRS) == 3
        assert TONGUE_PAIRS[0] == (b"KO", b"AV")
        assert TONGUE_PAIRS[1] == (b"RU", b"CA")
        assert TONGUE_PAIRS[2] == (b"UM", b"DR")

    def test_same_seed_same_strands(self):
        a = _init_strands(b"fixed")
        b = _init_strands(b"fixed")
        for sa, sb in zip(a, b):
            assert sa.as_bytes() == sb.as_bytes()

    def test_different_seed_different_strands(self):
        a = _init_strands(b"alpha")
        b = _init_strands(b"beta")
        assert a[0].as_bytes() != b[0].as_bytes()


# ── Braid Crossings ─────────────────────────────────────────────────────


class TestBraidCrossings:
    def test_sigma1_changes_state(self):
        strands = _init_strands(b"test")
        original = [s.as_bytes() for s in strands]
        crossed = _apply_crossing(strands, BraidCrossing.SIGMA_1)
        assert [s.as_bytes() for s in crossed] != original

    def test_sigma2_changes_state(self):
        strands = _init_strands(b"test")
        original = [s.as_bytes() for s in strands]
        crossed = _apply_crossing(strands, BraidCrossing.SIGMA_2)
        assert [s.as_bytes() for s in crossed] != original

    def test_crossing_preserves_strand_count(self):
        strands = _init_strands(b"test")
        for crossing in BraidCrossing:
            result = _apply_crossing(strands, crossing)
            assert len(result) == 3

    def test_all_four_crossings_produce_different_results(self):
        strands = _init_strands(b"test")
        results = {}
        for crossing in BraidCrossing:
            result = _apply_crossing(strands, crossing)
            key = b"".join(s.as_bytes() for s in result)
            results[crossing] = key
        # All 4 crossings should produce distinct states
        unique = set(results.values())
        assert len(unique) == 4

    def test_non_commutativity_sigma1_sigma2(self):
        """Core security property: s1*s2 != s2*s1."""
        strands = _init_strands(b"braid_test")

        # Apply s1 then s2
        path_a = _apply_crossing(strands, BraidCrossing.SIGMA_1)
        path_a = _apply_crossing(path_a, BraidCrossing.SIGMA_2)

        # Apply s2 then s1
        path_b = _apply_crossing(strands, BraidCrossing.SIGMA_2)
        path_b = _apply_crossing(path_b, BraidCrossing.SIGMA_1)

        state_a = b"".join(s.as_bytes() for s in path_a)
        state_b = b"".join(s.as_bytes() for s in path_b)
        assert state_a != state_b, "Braid crossings must be non-commutative"

    def test_crossing_does_not_mutate_input(self):
        strands = _init_strands(b"immutable")
        originals = [(s.h_a, s.h_b) for s in strands]
        _apply_crossing(strands, BraidCrossing.SIGMA_1)
        for i, s in enumerate(strands):
            assert s.h_a == originals[i][0]
            assert s.h_b == originals[i][1]


# ── Braid Words ──────────────────────────────────────────────────────────


class TestBraidWord:
    def test_generate_has_correct_length(self):
        w = BraidWord.generate(8)
        assert len(w) == 8

    def test_encode_decode_roundtrip(self):
        w = BraidWord.generate(16)
        encoded = w.encode()
        decoded = BraidWord.decode(encoded)
        assert decoded.crossings == w.crossings

    def test_inverse_has_same_length(self):
        w = BraidWord.generate(10)
        assert len(w.inverse()) == 10

    def test_inverse_reverses_and_flips(self):
        w = BraidWord(
            crossings=[
                BraidCrossing.SIGMA_1,
                BraidCrossing.SIGMA_2,
            ]
        )
        inv = w.inverse()
        assert inv.crossings == [
            BraidCrossing.SIGMA_2_INV,
            BraidCrossing.SIGMA_1_INV,
        ]

    def test_double_inverse_is_identity(self):
        w = BraidWord.generate(12)
        assert w.inverse().inverse().crossings == w.crossings

    def test_different_words_produce_different_states(self):
        seed = b"fixed_seed"
        w1 = BraidWord(crossings=[BraidCrossing.SIGMA_1, BraidCrossing.SIGMA_2])
        w2 = BraidWord(crossings=[BraidCrossing.SIGMA_2, BraidCrossing.SIGMA_1])
        s1 = _finalize(_apply_braid(_init_strands(seed), w1))
        s2 = _finalize(_apply_braid(_init_strands(seed), w2))
        assert s1 != s2

    def test_same_word_same_state(self):
        seed = b"fixed"
        w = BraidWord(crossings=[BraidCrossing.SIGMA_1, BraidCrossing.SIGMA_2])
        s1 = _finalize(_apply_braid(_init_strands(seed), w))
        s2 = _finalize(_apply_braid(_init_strands(seed), w))
        assert s1 == s2


# ── Finalization ─────────────────────────────────────────────────────────


class TestFinalization:
    def test_finalize_produces_32_bytes(self):
        strands = _init_strands(b"fin")
        result = _finalize(strands)
        assert len(result) == 32

    def test_finalize_is_deterministic(self):
        strands = _init_strands(b"det")
        assert _finalize(strands) == _finalize(strands)


# ── Vault CRUD ───────────────────────────────────────────────────────────


class TestVaultCRUD:
    def setup_method(self):
        self.vault = create_vault_deterministic("test-passphrase", "s1.s2.s1.s2.s1.s2")

    def test_store_and_retrieve(self):
        secret = b"my_api_key_12345"
        self.vault.store("hf_token", secret)
        retrieved = self.vault.retrieve("hf_token")
        assert retrieved == secret

    def test_retrieve_nonexistent_returns_none(self):
        assert self.vault.retrieve("nope") is None

    def test_store_long_secret(self):
        secret = b"A" * 256
        self.vault.store("long_key", secret)
        assert self.vault.retrieve("long_key") == secret

    def test_store_binary_secret(self):
        secret = bytes(range(256))
        self.vault.store("binary", secret)
        assert self.vault.retrieve("binary") == secret

    def test_multiple_entries_independent(self):
        self.vault.store("key_a", b"alpha")
        self.vault.store("key_b", b"beta")
        assert self.vault.retrieve("key_a") == b"alpha"
        assert self.vault.retrieve("key_b") == b"beta"

    def test_overwrite_entry(self):
        self.vault.store("dup", b"first")
        self.vault.store("dup", b"second")
        assert self.vault.retrieve("dup") == b"second"

    def test_list_entries(self):
        self.vault.store("a", b"1")
        self.vault.store("b", b"2")
        entries = self.vault.list_entries()
        assert set(entries) == {"a", "b"}

    def test_revoke(self):
        self.vault.store("doomed", b"bye")
        assert self.vault.revoke("doomed") is True
        assert self.vault.retrieve("doomed") is None

    def test_revoke_nonexistent(self):
        assert self.vault.revoke("ghost") is False

    def test_entry_count(self):
        assert self.vault.entry_count == 0
        self.vault.store("x", b"y")
        assert self.vault.entry_count == 1

    def test_tongue_affinity_stored(self):
        entry = self.vault.store("tongued", b"data", tongue_affinity="DR")
        assert entry.tongue_affinity == "DR"

    def test_metadata_stored(self):
        entry = self.vault.store("meta", b"data", metadata={"source": "api"})
        assert entry.metadata["source"] == "api"


# ── TTL / Expiry ─────────────────────────────────────────────────────────


class TestVaultTTL:
    def test_ttl_not_expired(self):
        vault = create_vault_deterministic("ttl", "s1.s2")
        vault.store("fresh", b"alive", ttl_seconds=3600)
        assert vault.retrieve("fresh") == b"alive"

    def test_ttl_expired(self):
        vault = create_vault_deterministic("ttl", "s1.s2")
        entry = vault.store("stale", b"dead", ttl_seconds=0.001)
        time.sleep(0.01)
        assert vault.retrieve("stale") is None

    def test_no_ttl_never_expires(self):
        vault = create_vault_deterministic("ttl", "s1.s2")
        entry = vault.store("eternal", b"forever")
        assert entry.expires_at is None
        assert not entry.is_expired


# ── Key Rotation ─────────────────────────────────────────────────────────


class TestKeyRotation:
    def test_rotate_preserves_secret(self):
        vault = create_vault_deterministic("rot", "s1.s2.s1")
        vault.store("token", b"secret_value")

        new_key = BraidWord.decode("s2.s1.s2.s1")
        vault.rotate("token", new_key)

        assert vault.retrieve("token") == b"secret_value"

    def test_rotate_changes_ciphertext(self):
        vault = create_vault_deterministic("rot", "s1.s2.s1")
        entry1 = vault.store("token", b"secret_value")
        ct1 = entry1.ciphertext

        new_key = BraidWord.decode("s2.s1.s2.s1")
        entry2 = vault.rotate("token", new_key)

        # Ciphertext must change (different key + different salt)
        assert entry2.ciphertext != ct1

    def test_rotate_nonexistent_returns_none(self):
        vault = create_vault_deterministic("rot", "s1.s2")
        result = vault.rotate("nope", BraidWord.decode("s1"))
        assert result is None


# ── Braid Verification ──────────────────────────────────────────────────


class TestBraidVerification:
    def test_correct_braid_verifies(self):
        vault = create_vault_deterministic("verify", "s1.s2.s1i.s2i")
        assert vault.verify_braid(BraidWord.decode("s1.s2.s1i.s2i"))

    def test_wrong_braid_fails(self):
        vault = create_vault_deterministic("verify", "s1.s2.s1i.s2i")
        assert not vault.verify_braid(BraidWord.decode("s2.s1.s2i.s1i"))

    def test_empty_braid_fails(self):
        vault = create_vault_deterministic("verify", "s1.s2")
        assert not vault.verify_braid(BraidWord(crossings=[]))


# ── Strand Fingerprints ─────────────────────────────────────────────────


class TestStrandFingerprints:
    def test_fingerprints_are_three_hex_strings(self):
        vault = create_vault_deterministic("fp", "s1.s2")
        fps = vault.strand_fingerprints()
        assert len(fps) == 3
        for fp in fps:
            assert len(fp) == 16
            int(fp, 16)  # valid hex

    def test_fingerprints_differ(self):
        vault = create_vault_deterministic("fp", "s1.s2")
        fps = vault.strand_fingerprints()
        assert len(set(fps)) == 3


# ── Audit Log ────────────────────────────────────────────────────────────


class TestAuditLog:
    def test_operations_logged(self):
        vault = create_vault_deterministic("audit", "s1.s2")
        vault.store("a", b"1")
        vault.retrieve("a")
        vault.revoke("a")
        actions = [e["action"] for e in vault._audit_log]
        assert actions == ["store", "retrieve", "revoke"]

    def test_log_entries_have_timestamps(self):
        vault = create_vault_deterministic("audit", "s1")
        vault.store("x", b"y")
        assert "timestamp" in vault._audit_log[0]
        assert vault._audit_log[0]["timestamp"] > 0


# ── Convenience Constructors ─────────────────────────────────────────────


class TestConstructors:
    def test_create_vault_works(self):
        vault = create_vault("my-pass", braid_length=8)
        assert vault.braid_length == 8
        vault.store("k", b"v")
        assert vault.retrieve("k") == b"v"

    def test_create_vault_deterministic_is_reproducible(self):
        v1 = create_vault_deterministic("pass", "s1.s2.s1")
        v2 = create_vault_deterministic("pass", "s1.s2.s1")
        assert v1._vault_key == v2._vault_key

    def test_different_passphrase_different_key(self):
        v1 = create_vault_deterministic("alpha", "s1.s2")
        v2 = create_vault_deterministic("beta", "s1.s2")
        assert v1._vault_key != v2._vault_key

    def test_different_braid_different_key(self):
        v1 = create_vault_deterministic("same", "s1.s2")
        v2 = create_vault_deterministic("same", "s2.s1")
        assert v1._vault_key != v2._vault_key


# ── Full Integration: Store-Rotate-Retrieve Cycle ────────────────────────


class TestIntegration:
    def test_full_lifecycle(self):
        """Store 3 secrets, rotate key, verify all survive."""
        vault = create_vault("lifecycle-test", braid_length=10)

        secrets = {
            "hf_token": b"hf_newtoken12345",
            "notion_key": b"ntn_secret_notion_key",
            "stripe_key": b"sk_live_stripe_prod_key",
        }

        for k, v in secrets.items():
            vault.store(k, v)

        # All retrievable
        for k, v in secrets.items():
            assert vault.retrieve(k) == v

        # Rotate
        new_braid = BraidWord.generate(14)
        for k in secrets:
            vault.rotate(k, new_braid)

        # Still retrievable after rotation
        for k, v in secrets.items():
            assert vault.retrieve(k) == v

        # Revoke one
        vault.revoke("stripe_key")
        assert vault.retrieve("stripe_key") is None
        assert vault.retrieve("hf_token") == b"hf_newtoken12345"

    def test_braid_word_is_the_key(self):
        """Two vaults with same seed but different braids cannot read each other."""
        seed = _h_a(b"shared_seed")
        w1 = BraidWord.decode("s1.s2.s1.s2")
        w2 = BraidWord.decode("s2.s1.s2.s1")

        v1 = BraidVault(master_seed=seed, braid_key=w1)
        v2 = BraidVault(master_seed=seed, braid_key=w2)

        v1.store("secret", b"only_for_v1")

        # v2 can't read v1's secrets (different derived key)
        # They don't share entries, but the point is the vault keys differ
        assert v1._vault_key != v2._vault_key
