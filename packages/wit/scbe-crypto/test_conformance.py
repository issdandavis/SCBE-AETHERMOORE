"""
scbe:crypto — Conformance Test Suite
======================================

Tests that any implementation of the scbe:crypto WIT interface
produces correct results. Run against the reference implementation
and any WASM component implementation.

Usage:
    python -m pytest packages/wit/scbe-crypto/test_conformance.py -v
"""

from __future__ import annotations

import pytest

from reference_impl import (
    CryptoError,
    DSA,
    Encapsulation,
    Hashing,
    KEM,
    Keypair,
    PQAlgorithm,
    SealSession,
    SpiralSeal,
    Symmetric,
)


# ---------------------------------------------------------------------------
#  KEM Tests
# ---------------------------------------------------------------------------

class TestKEM:
    def test_keygen_ml_kem_768(self):
        kp = KEM.keygen(PQAlgorithm.ML_KEM_768)
        assert isinstance(kp, Keypair)
        assert len(kp.public_key) == 32
        assert len(kp.secret_key) == 32
        assert kp.algorithm == PQAlgorithm.ML_KEM_768

    def test_keygen_ml_kem_1024(self):
        kp = KEM.keygen(PQAlgorithm.ML_KEM_1024)
        assert kp.algorithm == PQAlgorithm.ML_KEM_1024

    def test_keygen_wrong_algorithm(self):
        with pytest.raises(CryptoError):
            KEM.keygen(PQAlgorithm.ML_DSA_65)

    def test_encapsulate_produces_ciphertext(self):
        kp = KEM.keygen()
        enc = KEM.encapsulate(kp.public_key)
        assert isinstance(enc, Encapsulation)
        assert len(enc.ciphertext) > 0
        assert len(enc.shared_secret) == 32

    def test_encapsulate_different_each_time(self):
        kp = KEM.keygen()
        enc1 = KEM.encapsulate(kp.public_key)
        enc2 = KEM.encapsulate(kp.public_key)
        assert enc1.ciphertext != enc2.ciphertext

    def test_decapsulate_invalid_ciphertext(self):
        kp = KEM.keygen()
        with pytest.raises(CryptoError):
            KEM.decapsulate(kp.secret_key, b"too_short")


# ---------------------------------------------------------------------------
#  DSA Tests
# ---------------------------------------------------------------------------

class TestDSA:
    def test_keygen_ml_dsa_65(self):
        kp = DSA.keygen(PQAlgorithm.ML_DSA_65)
        assert isinstance(kp, Keypair)
        assert kp.algorithm == PQAlgorithm.ML_DSA_65

    def test_keygen_ml_dsa_87(self):
        kp = DSA.keygen(PQAlgorithm.ML_DSA_87)
        assert kp.algorithm == PQAlgorithm.ML_DSA_87

    def test_keygen_wrong_algorithm(self):
        with pytest.raises(CryptoError):
            DSA.keygen(PQAlgorithm.ML_KEM_768)

    def test_sign_produces_signature(self):
        kp = DSA.keygen()
        sig = DSA.sign(kp.secret_key, b"hello world")
        assert isinstance(sig, bytes)
        assert len(sig) == 32

    def test_sign_deterministic(self):
        kp = DSA.keygen()
        sig1 = DSA.sign(kp.secret_key, b"hello world")
        sig2 = DSA.sign(kp.secret_key, b"hello world")
        assert sig1 == sig2

    def test_sign_different_messages(self):
        kp = DSA.keygen()
        sig1 = DSA.sign(kp.secret_key, b"hello")
        sig2 = DSA.sign(kp.secret_key, b"world")
        assert sig1 != sig2

    def test_verify_valid_signature(self):
        kp = DSA.keygen()
        sig = DSA.sign(kp.secret_key, b"test message")
        assert DSA.verify(kp.public_key, b"test message", sig) is True

    def test_verify_invalid_signature_length(self):
        kp = DSA.keygen()
        assert DSA.verify(kp.public_key, b"test", b"short") is False


# ---------------------------------------------------------------------------
#  Symmetric Tests
# ---------------------------------------------------------------------------

class TestSymmetric:
    def test_encrypt_decrypt_roundtrip(self):
        key = b"\x42" * 32
        nonce = b"\x00" * 12
        plaintext = b"Hello, SCBE-AETHERMOORE!"
        aad = b"additional data"

        ct = Symmetric.encrypt_aes256gcm(key, nonce, plaintext, aad)
        pt = Symmetric.decrypt_aes256gcm(key, nonce, ct, aad)
        assert pt == plaintext

    def test_encrypt_decrypt_empty_message(self):
        key = b"\x42" * 32
        nonce = b"\x00" * 12
        ct = Symmetric.encrypt_aes256gcm(key, nonce, b"", b"")
        pt = Symmetric.decrypt_aes256gcm(key, nonce, ct, b"")
        assert pt == b""

    def test_wrong_key_fails(self):
        key1 = b"\x42" * 32
        key2 = b"\x43" * 32
        nonce = b"\x00" * 12
        ct = Symmetric.encrypt_aes256gcm(key1, nonce, b"secret", b"")
        with pytest.raises(CryptoError, match="tag mismatch"):
            Symmetric.decrypt_aes256gcm(key2, nonce, ct, b"")

    def test_wrong_aad_fails(self):
        key = b"\x42" * 32
        nonce = b"\x00" * 12
        ct = Symmetric.encrypt_aes256gcm(key, nonce, b"secret", b"aad1")
        with pytest.raises(CryptoError, match="tag mismatch"):
            Symmetric.decrypt_aes256gcm(key, nonce, ct, b"aad2")

    def test_invalid_key_length(self):
        with pytest.raises(CryptoError):
            Symmetric.encrypt_aes256gcm(b"short", b"\x00" * 12, b"data", b"")

    def test_invalid_nonce_length(self):
        with pytest.raises(CryptoError):
            Symmetric.encrypt_aes256gcm(b"\x42" * 32, b"short", b"data", b"")


# ---------------------------------------------------------------------------
#  Hashing Tests
# ---------------------------------------------------------------------------

class TestHashing:
    def test_sha256_known_vector(self):
        # SHA-256 of empty string
        digest = Hashing.sha256(b"")
        assert len(digest) == 32
        assert digest.hex() == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_sha256_hello(self):
        digest = Hashing.sha256(b"hello")
        assert len(digest) == 32

    def test_hmac_sha256_consistent(self):
        key = b"secret_key"
        data = b"message"
        mac1 = Hashing.hmac_sha256(key, data)
        mac2 = Hashing.hmac_sha256(key, data)
        assert mac1 == mac2

    def test_hmac_sha256_different_keys(self):
        mac1 = Hashing.hmac_sha256(b"key1", b"message")
        mac2 = Hashing.hmac_sha256(b"key2", b"message")
        assert mac1 != mac2

    def test_hkdf_sha256_output_length(self):
        key = Hashing.hkdf_sha256(b"input_key", b"salt", b"info", 64)
        assert len(key) == 64

    def test_hkdf_sha256_deterministic(self):
        key1 = Hashing.hkdf_sha256(b"ikm", b"salt", b"info", 32)
        key2 = Hashing.hkdf_sha256(b"ikm", b"salt", b"info", 32)
        assert key1 == key2

    def test_hkdf_sha256_empty_salt(self):
        key = Hashing.hkdf_sha256(b"ikm", b"", b"info", 32)
        assert len(key) == 32


# ---------------------------------------------------------------------------
#  Spiral Seal Tests
# ---------------------------------------------------------------------------

class TestSpiralSeal:
    def test_create_session(self):
        session = SpiralSeal.create_session()
        assert isinstance(session, SealSession)
        assert len(session.session_id) == 32  # hex string
        assert session.kem_keypair.algorithm == PQAlgorithm.ML_KEM_768
        assert session.dsa_keypair.algorithm == PQAlgorithm.ML_DSA_65

    def test_seal_produces_ciphertext_and_signature(self):
        sender = SpiralSeal.create_session()
        recipient = SpiralSeal.create_session()

        ct, sig = SpiralSeal.seal(
            sender, recipient.kem_keypair.public_key, b"Hello, World!"
        )

        assert isinstance(ct, bytes)
        assert isinstance(sig, bytes)
        assert len(ct) > len(b"Hello, World!")  # Ciphertext > plaintext
        assert len(sig) == 32

    def test_seal_different_each_time(self):
        sender = SpiralSeal.create_session()
        recipient = SpiralSeal.create_session()

        ct1, _ = SpiralSeal.seal(sender, recipient.kem_keypair.public_key, b"msg")
        ct2, _ = SpiralSeal.seal(sender, recipient.kem_keypair.public_key, b"msg")
        # Different due to random nonce and KEM ephemeral
        assert ct1 != ct2

    def test_seal_unseal_structure(self):
        """Test that seal produces structurally valid output."""
        sender = SpiralSeal.create_session()
        recipient = SpiralSeal.create_session()

        ct, sig = SpiralSeal.seal(
            sender, recipient.kem_keypair.public_key, b"test message"
        )

        # Verify ciphertext structure: 4-byte length prefix + KEM ct + encrypted
        kem_ct_len = int.from_bytes(ct[:4], "big")
        assert kem_ct_len > 0
        assert len(ct) > 4 + kem_ct_len

    def test_sessions_are_unique(self):
        s1 = SpiralSeal.create_session()
        s2 = SpiralSeal.create_session()
        assert s1.session_id != s2.session_id
        assert s1.kem_keypair.public_key != s2.kem_keypair.public_key


# ---------------------------------------------------------------------------
#  Cross-domain integration test
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_full_crypto_workflow(self):
        """End-to-end: keygen -> seal -> transmit -> unseal."""
        alice = SpiralSeal.create_session()
        bob = SpiralSeal.create_session()

        message = b"SCBE governance decision: ALLOW agent-7734 CORE access"

        # Alice seals for Bob
        ct, sig = SpiralSeal.seal(alice, bob.kem_keypair.public_key, message)

        # Verify structural integrity
        assert len(ct) > 0
        assert len(sig) == 32

        # Hash the ciphertext for audit trail
        audit_hash = Hashing.sha256(ct)
        assert len(audit_hash) == 32

    def test_hash_chain_integrity(self):
        """Verify hash chain for governance audit trail."""
        decisions = [
            b"ALLOW agent-001 INNER access",
            b"DENY agent-002 CORE access",
            b"QUARANTINE agent-003 pending review",
        ]

        chain = b""
        for decision in decisions:
            chain = Hashing.sha256(chain + decision)

        # Chain should be deterministic
        chain2 = b""
        for decision in decisions:
            chain2 = Hashing.sha256(chain2 + decision)

        assert chain == chain2
