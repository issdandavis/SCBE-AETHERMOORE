"""
Comprehensive Tests for PQC Module

Tests cover:
- Kyber768 key encapsulation
- Dilithium3 digital signatures
- PQC HMAC chain operations
- PQC audit chain operations
- Graceful fallback behavior
- Edge cases and error handling
"""

import pytest
import hashlib
import os
import time
import secrets

# Import PQC module
from symphonic_cipher.scbe_aethermoore.pqc import (
    # Core
    Kyber768, KyberKeyPair, EncapsulationResult,
    Dilithium3, DilithiumKeyPair, SignatureResult,
    PQCBackend, get_backend, is_liboqs_available,
    derive_hybrid_key, generate_pqc_session_keys, verify_pqc_session,

    # Constants
    KYBER768_PUBLIC_KEY_SIZE, KYBER768_SECRET_KEY_SIZE,
    KYBER768_CIPHERTEXT_SIZE, KYBER768_SHARED_SECRET_SIZE,
    DILITHIUM3_PUBLIC_KEY_SIZE, DILITHIUM3_SECRET_KEY_SIZE,
    DILITHIUM3_SIGNATURE_SIZE,

    # HMAC
    KeyDerivationMode, PQCKeyMaterial, PQCHMACState,
    pqc_derive_hmac_key, pqc_recover_hmac_key,
    pqc_hmac_chain_tag, pqc_verify_hmac_chain,
    PQCHMACChain, create_pqc_hmac_state, migrate_classical_chain,
    NONCE_BYTES, KEY_LEN, AUDIT_CHAIN_IV,

    # Audit
    AuditDecision, PQCAuditEntry, AuditChainVerification,
    PQCAuditChain, create_audit_entry_signature,
    verify_audit_entry_signature, PQCAuditIntegration,
)


# =============================================================================
# Backend Detection Tests
# =============================================================================

class TestBackendDetection:
    """Tests for PQC backend detection."""

    def test_get_backend_returns_valid_type(self):
        """Backend should return a valid PQCBackend enum."""
        backend = get_backend()
        assert isinstance(backend, PQCBackend)
        assert backend in [PQCBackend.LIBOQS, PQCBackend.MOCK]

    def test_is_liboqs_available_returns_bool(self):
        """is_liboqs_available should return boolean."""
        result = is_liboqs_available()
        assert isinstance(result, bool)

    def test_backend_consistency(self):
        """Backend detection should be consistent."""
        backend1 = get_backend()
        backend2 = get_backend()
        assert backend1 == backend2


# =============================================================================
# Kyber768 Tests
# =============================================================================

class TestKyber768:
    """Tests for Kyber768 key encapsulation."""

    def test_generate_keypair(self):
        """Should generate valid Kyber768 keypair."""
        keypair = Kyber768.generate_keypair()

        assert isinstance(keypair, KyberKeyPair)
        assert isinstance(keypair.public_key, bytes)
        assert isinstance(keypair.secret_key, bytes)
        assert len(keypair.public_key) == KYBER768_PUBLIC_KEY_SIZE
        assert len(keypair.secret_key) == KYBER768_SECRET_KEY_SIZE

    def test_keypair_uniqueness(self):
        """Each keypair generation should produce unique keys."""
        keypair1 = Kyber768.generate_keypair()
        keypair2 = Kyber768.generate_keypair()

        assert keypair1.public_key != keypair2.public_key
        assert keypair1.secret_key != keypair2.secret_key

    def test_encapsulate(self):
        """Should encapsulate with valid public key."""
        keypair = Kyber768.generate_keypair()
        result = Kyber768.encapsulate(keypair.public_key)

        assert isinstance(result, EncapsulationResult)
        assert isinstance(result.ciphertext, bytes)
        assert isinstance(result.shared_secret, bytes)
        assert len(result.ciphertext) == KYBER768_CIPHERTEXT_SIZE
        assert len(result.shared_secret) == KYBER768_SHARED_SECRET_SIZE

    def test_encapsulate_randomness(self):
        """Each encapsulation should produce different results."""
        keypair = Kyber768.generate_keypair()
        result1 = Kyber768.encapsulate(keypair.public_key)
        result2 = Kyber768.encapsulate(keypair.public_key)

        assert result1.ciphertext != result2.ciphertext
        assert result1.shared_secret != result2.shared_secret

    def test_decapsulate(self):
        """Should decapsulate to same shared secret."""
        keypair = Kyber768.generate_keypair()
        encap_result = Kyber768.encapsulate(keypair.public_key)

        shared_secret = Kyber768.decapsulate(
            keypair.secret_key,
            encap_result.ciphertext
        )

        assert shared_secret == encap_result.shared_secret

    def test_full_key_exchange(self):
        """Full key exchange should produce matching secrets."""
        # Alice generates keypair
        alice_keypair = Kyber768.generate_keypair()

        # Bob encapsulates with Alice's public key
        bob_result = Kyber768.encapsulate(alice_keypair.public_key)

        # Alice decapsulates with her secret key
        alice_secret = Kyber768.decapsulate(
            alice_keypair.secret_key,
            bob_result.ciphertext
        )

        # Both should have same shared secret
        assert alice_secret == bob_result.shared_secret

    def test_key_exchange_method(self):
        """key_exchange method should work correctly."""
        sender_keypair = Kyber768.generate_keypair()
        recipient_keypair = Kyber768.generate_keypair()

        shared_secret, ciphertext, sender_pk = Kyber768.key_exchange(
            sender_keypair,
            recipient_keypair.public_key
        )

        # Recipient decapsulates
        recipient_secret = Kyber768.decapsulate(
            recipient_keypair.secret_key,
            ciphertext
        )

        assert shared_secret == recipient_secret
        assert sender_pk == sender_keypair.public_key

    def test_encapsulate_invalid_key_size(self):
        """Should raise on invalid public key size."""
        with pytest.raises(ValueError):
            Kyber768.encapsulate(b"invalid_key")

    def test_decapsulate_invalid_key_size(self):
        """Should raise on invalid secret key size."""
        keypair = Kyber768.generate_keypair()
        result = Kyber768.encapsulate(keypair.public_key)

        with pytest.raises(ValueError):
            Kyber768.decapsulate(b"invalid_key", result.ciphertext)

    def test_decapsulate_invalid_ciphertext_size(self):
        """Should raise on invalid ciphertext size."""
        keypair = Kyber768.generate_keypair()

        with pytest.raises(ValueError):
            Kyber768.decapsulate(keypair.secret_key, b"invalid_ct")


# =============================================================================
# Dilithium3 Tests
# =============================================================================

class TestDilithium3:
    """Tests for Dilithium3 digital signatures."""

    def test_generate_keypair(self):
        """Should generate valid Dilithium3 keypair."""
        keypair = Dilithium3.generate_keypair()

        assert isinstance(keypair, DilithiumKeyPair)
        assert isinstance(keypair.public_key, bytes)
        assert isinstance(keypair.secret_key, bytes)
        assert len(keypair.public_key) == DILITHIUM3_PUBLIC_KEY_SIZE
        assert len(keypair.secret_key) == DILITHIUM3_SECRET_KEY_SIZE

    def test_keypair_uniqueness(self):
        """Each keypair generation should produce unique keys."""
        keypair1 = Dilithium3.generate_keypair()
        keypair2 = Dilithium3.generate_keypair()

        assert keypair1.public_key != keypair2.public_key
        assert keypair1.secret_key != keypair2.secret_key

    def test_sign(self):
        """Should sign message with valid secret key."""
        keypair = Dilithium3.generate_keypair()
        message = b"Hello, quantum world!"

        signature = Dilithium3.sign(keypair.secret_key, message)

        assert isinstance(signature, bytes)
        assert len(signature) == DILITHIUM3_SIGNATURE_SIZE

    def test_sign_deterministic(self):
        """Signing same message should produce same signature."""
        keypair = Dilithium3.generate_keypair()
        message = b"Deterministic test"

        sig1 = Dilithium3.sign(keypair.secret_key, message)
        sig2 = Dilithium3.sign(keypair.secret_key, message)

        # Note: Dilithium is deterministic for same key+message
        # Mock implementation is also deterministic
        assert sig1 == sig2

    def test_verify_valid(self):
        """Should verify valid signature."""
        keypair = Dilithium3.generate_keypair()
        message = b"Test message"

        signature = Dilithium3.sign(keypair.secret_key, message)
        is_valid = Dilithium3.verify(keypair.public_key, message, signature)

        assert is_valid is True

    def test_verify_invalid_signature(self):
        """Should reject invalid signature."""
        keypair = Dilithium3.generate_keypair()
        message = b"Test message"

        # Create invalid signature
        invalid_sig = os.urandom(DILITHIUM3_SIGNATURE_SIZE)
        is_valid = Dilithium3.verify(keypair.public_key, message, invalid_sig)

        assert is_valid is False

    def test_verify_wrong_message(self):
        """Should reject signature for wrong message."""
        keypair = Dilithium3.generate_keypair()
        message1 = b"Original message"
        message2 = b"Different message"

        signature = Dilithium3.sign(keypair.secret_key, message1)
        is_valid = Dilithium3.verify(keypair.public_key, message2, signature)

        assert is_valid is False

    def test_verify_wrong_key(self):
        """Should reject signature with wrong public key."""
        keypair1 = Dilithium3.generate_keypair()
        keypair2 = Dilithium3.generate_keypair()
        message = b"Test message"

        signature = Dilithium3.sign(keypair1.secret_key, message)
        is_valid = Dilithium3.verify(keypair2.public_key, message, signature)

        assert is_valid is False

    def test_sign_with_result(self):
        """sign_with_result should return structured result."""
        keypair = Dilithium3.generate_keypair()
        message = b"Test message"

        result = Dilithium3.sign_with_result(keypair.secret_key, message)

        assert isinstance(result, SignatureResult)
        assert result.message == message
        assert len(result.signature) == DILITHIUM3_SIGNATURE_SIZE

    def test_sign_empty_message(self):
        """Should handle empty message."""
        keypair = Dilithium3.generate_keypair()
        message = b""

        signature = Dilithium3.sign(keypair.secret_key, message)
        is_valid = Dilithium3.verify(keypair.public_key, message, signature)

        assert is_valid is True

    def test_sign_large_message(self):
        """Should handle large messages."""
        keypair = Dilithium3.generate_keypair()
        message = os.urandom(1024 * 1024)  # 1MB

        signature = Dilithium3.sign(keypair.secret_key, message)
        is_valid = Dilithium3.verify(keypair.public_key, message, signature)

        assert is_valid is True

    def test_sign_invalid_key_size(self):
        """Should raise on invalid secret key size."""
        with pytest.raises(ValueError):
            Dilithium3.sign(b"invalid_key", b"message")


# =============================================================================
# Hybrid Key Derivation Tests
# =============================================================================

class TestHybridKeyDerivation:
    """Tests for hybrid key derivation functions."""

    def test_derive_hybrid_key_pqc_only(self):
        """Should derive key from PQC secret only."""
        pqc_secret = os.urandom(32)
        key = derive_hybrid_key(pqc_secret)

        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_derive_hybrid_key_with_classical(self):
        """Should derive key from PQC + classical secrets."""
        pqc_secret = os.urandom(32)
        classical_secret = os.urandom(32)

        key = derive_hybrid_key(pqc_secret, classical_secret)

        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_derive_hybrid_key_different_inputs(self):
        """Different inputs should produce different keys."""
        secret1 = os.urandom(32)
        secret2 = os.urandom(32)

        key1 = derive_hybrid_key(secret1)
        key2 = derive_hybrid_key(secret2)

        assert key1 != key2

    def test_derive_hybrid_key_with_salt(self):
        """Salt should affect key derivation."""
        secret = os.urandom(32)
        salt1 = os.urandom(32)
        salt2 = os.urandom(32)

        key1 = derive_hybrid_key(secret, salt=salt1)
        key2 = derive_hybrid_key(secret, salt=salt2)

        assert key1 != key2

    def test_derive_hybrid_key_with_info(self):
        """Info should affect key derivation."""
        secret = os.urandom(32)

        key1 = derive_hybrid_key(secret, info=b"context1")
        key2 = derive_hybrid_key(secret, info=b"context2")

        assert key1 != key2

    def test_derive_hybrid_key_deterministic(self):
        """Same inputs should produce same key."""
        secret = os.urandom(32)
        salt = os.urandom(32)

        key1 = derive_hybrid_key(secret, salt=salt, info=b"test")
        key2 = derive_hybrid_key(secret, salt=salt, info=b"test")

        assert key1 == key2


class TestPQCSessionKeys:
    """Tests for PQC session key generation."""

    def test_generate_session_keys(self):
        """Should generate valid session keys."""
        initiator_kem = Kyber768.generate_keypair()
        responder_kem = Kyber768.generate_keypair()
        initiator_sig = Dilithium3.generate_keypair()

        session = generate_pqc_session_keys(
            initiator_kem,
            responder_kem.public_key,
            initiator_sig
        )

        assert "session_id" in session
        assert "encryption_key" in session
        assert "mac_key" in session
        assert "ciphertext" in session
        assert "signature" in session
        assert len(session["encryption_key"]) == 32
        assert len(session["mac_key"]) == 32

    def test_verify_session(self):
        """Responder should verify and complete session."""
        initiator_kem = Kyber768.generate_keypair()
        responder_kem = Kyber768.generate_keypair()
        initiator_sig = Dilithium3.generate_keypair()

        # Initiator generates session
        session = generate_pqc_session_keys(
            initiator_kem,
            responder_kem.public_key,
            initiator_sig
        )

        # Responder verifies
        verified = verify_pqc_session(
            session,
            responder_kem,
            initiator_sig.public_key
        )

        assert verified is not None
        assert verified["encryption_key"] == session["encryption_key"]
        assert verified["mac_key"] == session["mac_key"]

    def test_verify_session_invalid_signature(self):
        """Should reject session with invalid signature."""
        initiator_kem = Kyber768.generate_keypair()
        responder_kem = Kyber768.generate_keypair()
        initiator_sig = Dilithium3.generate_keypair()
        wrong_sig = Dilithium3.generate_keypair()

        session = generate_pqc_session_keys(
            initiator_kem,
            responder_kem.public_key,
            initiator_sig
        )

        # Try to verify with wrong public key
        verified = verify_pqc_session(
            session,
            responder_kem,
            wrong_sig.public_key  # Wrong key
        )

        assert verified is None


# =============================================================================
# PQC HMAC Chain Tests
# =============================================================================

class TestPQCKeyMaterial:
    """Tests for PQC key material."""

    def test_derive_hmac_key(self):
        """Should derive valid HMAC key."""
        keypair = Kyber768.generate_keypair()
        material = pqc_derive_hmac_key(keypair.public_key)

        assert isinstance(material, PQCKeyMaterial)
        assert len(material.hmac_key) == KEY_LEN
        assert len(material.pqc_shared_secret) == KYBER768_SHARED_SECRET_SIZE
        assert len(material.ciphertext) == KYBER768_CIPHERTEXT_SIZE

    def test_derive_hmac_key_modes(self):
        """Should support different derivation modes."""
        keypair = Kyber768.generate_keypair()

        for mode in KeyDerivationMode:
            material = pqc_derive_hmac_key(keypair.public_key, mode=mode)
            assert material.derivation_mode == mode
            assert len(material.hmac_key) == KEY_LEN

    def test_recover_hmac_key(self):
        """Should recover same HMAC key."""
        keypair = Kyber768.generate_keypair()
        material = pqc_derive_hmac_key(keypair.public_key, mode=KeyDerivationMode.PQC_ONLY)

        recovered_key = pqc_recover_hmac_key(
            keypair.secret_key,
            material.ciphertext,
            material.salt,
            mode=KeyDerivationMode.PQC_ONLY
        )

        assert recovered_key == material.hmac_key


class TestPQCHMACChainTag:
    """Tests for PQC HMAC chain tag computation."""

    def test_chain_tag_computation(self):
        """Should compute valid chain tag."""
        keypair = Kyber768.generate_keypair()
        material = pqc_derive_hmac_key(keypair.public_key)

        message = b"test message"
        nonce = os.urandom(NONCE_BYTES)
        prev_tag = AUDIT_CHAIN_IV

        tag = pqc_hmac_chain_tag(message, nonce, prev_tag, material)

        assert isinstance(tag, bytes)
        assert len(tag) == 32

    def test_chain_tag_deterministic(self):
        """Same inputs should produce same tag."""
        keypair = Kyber768.generate_keypair()
        material = pqc_derive_hmac_key(keypair.public_key)

        message = b"test message"
        nonce = os.urandom(NONCE_BYTES)
        prev_tag = AUDIT_CHAIN_IV

        tag1 = pqc_hmac_chain_tag(message, nonce, prev_tag, material)
        tag2 = pqc_hmac_chain_tag(message, nonce, prev_tag, material)

        assert tag1 == tag2

    def test_chain_tag_changes_with_message(self):
        """Different messages should produce different tags."""
        keypair = Kyber768.generate_keypair()
        material = pqc_derive_hmac_key(keypair.public_key)

        nonce = os.urandom(NONCE_BYTES)
        prev_tag = AUDIT_CHAIN_IV

        tag1 = pqc_hmac_chain_tag(b"message1", nonce, prev_tag, material)
        tag2 = pqc_hmac_chain_tag(b"message2", nonce, prev_tag, material)

        assert tag1 != tag2


class TestPQCHMACChain:
    """Tests for PQC HMAC chain class."""

    def test_create_new(self):
        """Should create new chain."""
        chain = PQCHMACChain.create_new()

        assert chain.chain_length == 0
        assert isinstance(chain.public_key, bytes)

    def test_append_entry(self):
        """Should append entry to chain."""
        chain = PQCHMACChain.create_new()
        tag = chain.append(b"entry 1")

        assert chain.chain_length == 1
        assert isinstance(tag, bytes)
        assert len(tag) == 32

    def test_append_multiple_entries(self):
        """Should append multiple entries."""
        chain = PQCHMACChain.create_new()

        for i in range(10):
            chain.append(f"entry {i}".encode())

        assert chain.chain_length == 10

    def test_verify_valid_chain(self):
        """Should verify valid chain."""
        chain = PQCHMACChain.create_new()

        for i in range(5):
            chain.append(f"entry {i}".encode())

        assert chain.verify() is True

    def test_verify_empty_chain(self):
        """Should verify empty chain."""
        chain = PQCHMACChain.create_new()
        assert chain.verify() is True

    def test_get_entry(self):
        """Should get entry by index."""
        chain = PQCHMACChain.create_new()
        chain.append(b"entry 0")
        chain.append(b"entry 1")

        entry = chain.get_entry(1)
        assert entry is not None
        assert entry[0] == b"entry 1"

    def test_get_entry_invalid_index(self):
        """Should return None for invalid index."""
        chain = PQCHMACChain.create_new()
        assert chain.get_entry(100) is None

    def test_get_latest_tag(self):
        """Should get latest tag."""
        chain = PQCHMACChain.create_new()

        # Empty chain returns IV
        assert chain.get_latest_tag() == AUDIT_CHAIN_IV

        # After append, returns new tag
        tag = chain.append(b"entry")
        assert chain.get_latest_tag() == tag

    def test_export_state(self):
        """Should export chain state."""
        chain = PQCHMACChain.create_new()
        chain.append(b"entry 1")

        state = chain.export_state()

        assert "chain" in state
        assert "public_key" in state
        assert "backend" in state
        assert len(state["chain"]) == 1

    def test_from_keypair(self):
        """Should create chain from existing keypair and key exchange data."""
        # Create original chain
        chain1 = PQCHMACChain.create_new(mode=KeyDerivationMode.PQC_ONLY)
        chain1.append(b"entry 1")

        # Create new chain with same key material
        chain2 = PQCHMACChain.from_keypair(
            Kyber768.generate_keypair(),
            chain1.key_material.ciphertext,
            chain1.key_material.salt,
            mode=KeyDerivationMode.PQC_ONLY
        )

        # Both should work independently
        chain2.append(b"entry 2")
        assert chain2.verify() is True

    def test_rotate_key(self):
        """Should rotate to new key."""
        chain = PQCHMACChain.create_new()
        old_key = chain.key_material.hmac_key

        new_material = chain.rotate_key()

        assert new_material.hmac_key != old_key


class TestMigrateClassicalChain:
    """Tests for classical chain migration."""

    def test_migrate_chain(self):
        """Should migrate classical chain to PQC."""
        messages = [b"msg1", b"msg2", b"msg3"]
        nonces = [os.urandom(NONCE_BYTES) for _ in messages]
        tags = [os.urandom(32) for _ in messages]  # Dummy tags
        classical_key = os.urandom(32)

        new_chain, success = migrate_classical_chain(
            classical_key, messages, nonces, tags
        )

        assert isinstance(new_chain, PQCHMACChain)
        assert new_chain.chain_length == 3
        assert new_chain.verify() is True


# =============================================================================
# PQC Audit Chain Tests
# =============================================================================

class TestPQCAuditEntry:
    """Tests for PQC audit entries."""

    def test_entry_to_bytes(self):
        """Should serialize entry to bytes."""
        entry = PQCAuditEntry(
            identity="user1",
            intent="read",
            timestamp=time.time(),
            decision=AuditDecision.ALLOW,
            chain_position=0,
            nonce=os.urandom(NONCE_BYTES),
            hmac_tag=os.urandom(32),
            prev_tag=AUDIT_CHAIN_IV,
            signature=os.urandom(DILITHIUM3_SIGNATURE_SIZE),
            signer_public_key=os.urandom(DILITHIUM3_PUBLIC_KEY_SIZE)
        )

        data = entry.to_bytes()
        assert isinstance(data, bytes)
        assert b"user1" in data
        assert b"read" in data

    def test_entry_to_dict(self):
        """Should convert entry to dict."""
        entry = PQCAuditEntry(
            identity="user1",
            intent="read",
            timestamp=123456.789,
            decision=AuditDecision.ALLOW,
            chain_position=0,
            nonce=os.urandom(NONCE_BYTES),
            hmac_tag=os.urandom(32),
            prev_tag=AUDIT_CHAIN_IV,
            signature=os.urandom(DILITHIUM3_SIGNATURE_SIZE),
            signer_public_key=os.urandom(DILITHIUM3_PUBLIC_KEY_SIZE)
        )

        d = entry.to_dict()
        assert d["identity"] == "user1"
        assert d["intent"] == "read"
        assert d["decision"] == "ALLOW"

    def test_entry_from_dict(self):
        """Should create entry from dict."""
        entry = PQCAuditEntry(
            identity="user1",
            intent="read",
            timestamp=123456.789,
            decision=AuditDecision.ALLOW,
            chain_position=0,
            nonce=os.urandom(NONCE_BYTES),
            hmac_tag=os.urandom(32),
            prev_tag=AUDIT_CHAIN_IV,
            signature=os.urandom(DILITHIUM3_SIGNATURE_SIZE),
            signer_public_key=os.urandom(DILITHIUM3_PUBLIC_KEY_SIZE)
        )

        d = entry.to_dict()
        restored = PQCAuditEntry.from_dict(d)

        assert restored.identity == entry.identity
        assert restored.intent == entry.intent
        assert restored.decision == entry.decision


class TestPQCAuditChain:
    """Tests for PQC audit chain."""

    def test_create_new(self):
        """Should create new audit chain."""
        chain = PQCAuditChain.create_new()

        assert chain.chain_length == 0
        assert isinstance(chain.sig_public_key, bytes)
        assert isinstance(chain.kem_public_key, bytes)

    def test_add_entry(self):
        """Should add entry to audit chain."""
        chain = PQCAuditChain.create_new()

        entry = chain.add_entry(
            identity="user1",
            intent="read_data",
            decision=AuditDecision.ALLOW
        )

        assert chain.chain_length == 1
        assert entry.identity == "user1"
        assert entry.decision == AuditDecision.ALLOW

    def test_add_multiple_entries(self):
        """Should add multiple entries."""
        chain = PQCAuditChain.create_new()

        for i in range(5):
            chain.add_entry(
                identity=f"user{i}",
                intent=f"action{i}",
                decision=AuditDecision.ALLOW
            )

        assert chain.chain_length == 5

    def test_entry_signature_valid(self):
        """Entry signature should be valid."""
        chain = PQCAuditChain.create_new()

        entry = chain.add_entry(
            identity="user1",
            intent="read",
            decision=AuditDecision.ALLOW
        )

        assert entry.verify_signature() is True

    def test_verify_chain(self):
        """Should verify valid chain."""
        chain = PQCAuditChain.create_new()

        for i in range(5):
            chain.add_entry(
                identity=f"user{i}",
                intent=f"action{i}",
                decision=AuditDecision.ALLOW if i % 2 == 0 else AuditDecision.DENY
            )

        result = chain.verify_chain()

        assert result.is_valid is True
        assert result.hmac_valid is True
        assert result.signatures_valid is True
        assert result.entries_checked == 5

    def test_verify_empty_chain(self):
        """Should verify empty chain."""
        chain = PQCAuditChain.create_new()
        result = chain.verify_chain()

        assert result.is_valid is True
        assert result.entries_checked == 0

    def test_verify_entry(self):
        """Should verify individual entry."""
        chain = PQCAuditChain.create_new()
        entry = chain.add_entry("user", "action", AuditDecision.ALLOW)

        is_valid, message = chain.verify_entry(entry)
        assert is_valid is True

    def test_get_entries_by_identity(self):
        """Should filter entries by identity."""
        chain = PQCAuditChain.create_new()

        chain.add_entry("user1", "action1", AuditDecision.ALLOW)
        chain.add_entry("user2", "action2", AuditDecision.DENY)
        chain.add_entry("user1", "action3", AuditDecision.ALLOW)

        user1_entries = chain.get_entries_by_identity("user1")
        assert len(user1_entries) == 2

    def test_get_entries_by_decision(self):
        """Should filter entries by decision."""
        chain = PQCAuditChain.create_new()

        chain.add_entry("user1", "action1", AuditDecision.ALLOW)
        chain.add_entry("user2", "action2", AuditDecision.DENY)
        chain.add_entry("user3", "action3", AuditDecision.ALLOW)

        allow_entries = chain.get_entries_by_decision(AuditDecision.ALLOW)
        assert len(allow_entries) == 2

    def test_get_chain_digest(self):
        """Should compute chain digest."""
        chain = PQCAuditChain.create_new()
        chain.add_entry("user", "action", AuditDecision.ALLOW)

        digest = chain.get_chain_digest()
        assert isinstance(digest, bytes)
        assert len(digest) == 32

    def test_export_state(self):
        """Should export audit chain state."""
        chain = PQCAuditChain.create_new()
        chain.add_entry("user", "action", AuditDecision.ALLOW)

        state = chain.export_state()

        assert "entries" in state
        assert "hmac_chain" in state
        assert "sig_public_key" in state
        assert len(state["entries"]) == 1

    def test_get_audit_summary(self):
        """Should get audit summary."""
        chain = PQCAuditChain.create_new()

        chain.add_entry("user1", "action1", AuditDecision.ALLOW)
        chain.add_entry("user2", "action2", AuditDecision.DENY)
        chain.add_entry("user1", "action3", AuditDecision.ALLOW)

        summary = chain.get_audit_summary()

        assert summary["total_entries"] == 3
        assert summary["decisions"]["ALLOW"] == 2
        assert summary["decisions"]["DENY"] == 1
        assert len(summary["identities"]) == 2

    def test_decisions_enum(self):
        """Should support all decision types."""
        chain = PQCAuditChain.create_new()

        for decision in AuditDecision:
            chain.add_entry("user", "action", decision)

        assert chain.chain_length == len(AuditDecision)


class TestStandaloneAuditSignatures:
    """Tests for standalone audit signature functions."""

    def test_create_signature(self):
        """Should create audit entry signature."""
        keypair = Dilithium3.generate_keypair()
        chain_tag = os.urandom(32)

        sig = create_audit_entry_signature(
            "user1", "read", "ALLOW", time.time(),
            chain_tag, keypair
        )

        assert isinstance(sig, bytes)
        assert len(sig) == DILITHIUM3_SIGNATURE_SIZE

    def test_verify_signature(self):
        """Should verify audit entry signature."""
        keypair = Dilithium3.generate_keypair()
        chain_tag = os.urandom(32)
        timestamp = time.time()

        sig = create_audit_entry_signature(
            "user1", "read", "ALLOW", timestamp,
            chain_tag, keypair
        )

        is_valid = verify_audit_entry_signature(
            "user1", "read", "ALLOW", timestamp,
            chain_tag, sig, keypair.public_key
        )

        assert is_valid is True

    def test_verify_invalid_signature(self):
        """Should reject invalid signature."""
        keypair = Dilithium3.generate_keypair()
        chain_tag = os.urandom(32)

        is_valid = verify_audit_entry_signature(
            "user1", "read", "ALLOW", time.time(),
            chain_tag,
            os.urandom(DILITHIUM3_SIGNATURE_SIZE),  # Random signature
            keypair.public_key
        )

        assert is_valid is False


class TestPQCAuditIntegration:
    """Tests for PQC audit integration helper."""

    def test_integration_create(self):
        """Should create integration helper."""
        integration = PQCAuditIntegration()
        assert isinstance(integration.public_key, bytes)

    def test_integration_sign_verify(self):
        """Should sign and verify entries."""
        integration = PQCAuditIntegration()
        audit_data = b"user|action|timestamp|ALLOW"
        chain_tag = os.urandom(32)

        sig = integration.sign_entry(audit_data, chain_tag)
        is_valid = integration.verify_entry(audit_data, chain_tag, sig)

        assert is_valid is True

    def test_integration_batch_sign(self):
        """Should batch sign entries."""
        integration = PQCAuditIntegration()
        entries = [
            (b"entry1", os.urandom(32)),
            (b"entry2", os.urandom(32)),
            (b"entry3", os.urandom(32)),
        ]

        signatures = integration.batch_sign(entries)
        assert len(signatures) == 3

    def test_integration_batch_verify(self):
        """Should batch verify entries."""
        integration = PQCAuditIntegration()
        entries = [
            (b"entry1", os.urandom(32)),
            (b"entry2", os.urandom(32)),
        ]

        signatures = integration.batch_sign(entries)

        verify_entries = [
            (entries[0][0], entries[0][1], signatures[0]),
            (entries[1][0], entries[1][1], signatures[1]),
        ]

        results = integration.batch_verify(verify_entries)
        assert all(results)


# =============================================================================
# State Management Tests
# =============================================================================

class TestCreatePQCHMACState:
    """Tests for PQC HMAC state creation."""

    def test_create_state(self):
        """Should create valid PQC HMAC state."""
        state = create_pqc_hmac_state()

        assert isinstance(state, PQCHMACState)
        assert isinstance(state.kem_keypair, KyberKeyPair)
        assert isinstance(state.key_material, PQCKeyMaterial)

    def test_create_state_modes(self):
        """Should support different modes."""
        for mode in KeyDerivationMode:
            state = create_pqc_hmac_state(mode=mode)
            assert state.mode == mode


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_kyber_keypair_type_validation(self):
        """KyberKeyPair should validate types."""
        with pytest.raises(TypeError):
            KyberKeyPair(public_key="not bytes", secret_key=b"bytes")

    def test_dilithium_keypair_type_validation(self):
        """DilithiumKeyPair should validate types."""
        with pytest.raises(TypeError):
            DilithiumKeyPair(public_key=b"bytes", secret_key="not bytes")

    def test_pqc_key_material_validation(self):
        """PQCKeyMaterial should validate key length."""
        with pytest.raises(ValueError):
            PQCKeyMaterial(
                hmac_key=b"too_short",
                pqc_shared_secret=os.urandom(KYBER768_SHARED_SECRET_SIZE),
                ciphertext=os.urandom(KYBER768_CIPHERTEXT_SIZE),
                derivation_mode=KeyDerivationMode.HYBRID
            )

    def test_verify_chain_mismatched_lengths(self):
        """Should handle mismatched input lengths."""
        keypair = Kyber768.generate_keypair()
        material = pqc_derive_hmac_key(keypair.public_key)

        result = pqc_verify_hmac_chain(
            [b"msg1", b"msg2"],
            [os.urandom(NONCE_BYTES)],  # Only one nonce
            [os.urandom(32), os.urandom(32)],
            material
        )

        assert result is False

    def test_dilithium_verify_handles_exceptions(self):
        """Dilithium verify should handle exceptions gracefully."""
        # Invalid public key should not raise, just return False
        is_valid = Dilithium3.verify(
            b"invalid",
            b"message",
            os.urandom(DILITHIUM3_SIGNATURE_SIZE)
        )
        assert is_valid is False


# =============================================================================
# Performance Tests (Optional)
# =============================================================================

class TestPerformance:
    """Basic performance sanity checks."""

    def test_key_generation_performance(self):
        """Key generation should complete in reasonable time."""
        import time

        start = time.time()
        for _ in range(10):
            Kyber768.generate_keypair()
            Dilithium3.generate_keypair()
        elapsed = time.time() - start

        # Should complete in under 10 seconds even with mock
        assert elapsed < 10

    def test_chain_operations_performance(self):
        """Chain operations should be reasonably fast."""
        import time

        chain = PQCHMACChain.create_new()

        start = time.time()
        for i in range(100):
            chain.append(f"entry {i}".encode())
        elapsed = time.time() - start

        # 100 entries should complete in under 5 seconds
        assert elapsed < 5
        assert chain.verify() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
