"""
Property-Based Tests for RWP v3.0 Protocol
==========================================
Uses Hypothesis to generate random inputs and verify invariants.

Properties tested:
1. All messages roundtrip correctly (encryption is reversible)
2. Wrong password always fails
3. Tampered ciphertext always fails
4. Tampered tag always fails
5. Different nonces produce different ciphertexts
6. AAD modification fails authentication

Iterations: 100+ per property (configurable via hypothesis settings)
"""

import pytest
from hypothesis import given, settings, strategies as st, assume, HealthCheck
import json

# Import with fallback for missing dependencies
try:
    from src.crypto.rwp_v3 import (
        RWPv3Protocol,
        RWPEnvelope,
        rwp_encrypt_message,
        rwp_decrypt_message,
        ARGON2_AVAILABLE,
        CHACHA_AVAILABLE,
    )
    RWP_AVAILABLE = ARGON2_AVAILABLE and CHACHA_AVAILABLE
except ImportError:
    RWP_AVAILABLE = False
    ARGON2_AVAILABLE = False
    CHACHA_AVAILABLE = False

from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER


# Skip all tests if dependencies not available
pytestmark = pytest.mark.skipif(
    not RWP_AVAILABLE,
    reason="RWP v3.0 dependencies not installed (argon2-cffi, pycryptodome)"
)

# Hypothesis settings for thorough testing
THOROUGH = settings(
    max_examples=100,
    deadline=None,  # Disable deadline for crypto operations
    suppress_health_check=[HealthCheck.too_slow],
)


class TestEncryptDecryptRoundtrip:
    """Property: All valid inputs roundtrip through encrypt/decrypt."""

    @given(
        password=st.binary(min_size=1, max_size=64),
        plaintext=st.binary(min_size=0, max_size=1024),
    )
    @settings(max_examples=100, deadline=None)
    def test_roundtrip_bytes(self, password: bytes, plaintext: bytes):
        """All byte combinations should roundtrip."""
        protocol = RWPv3Protocol(enable_pqc=False)
        envelope = protocol.encrypt(password, plaintext)
        decrypted = protocol.decrypt(password, envelope)
        assert decrypted == plaintext

    @given(
        password=st.binary(min_size=1, max_size=64),
        plaintext=st.binary(min_size=0, max_size=1024),
        aad=st.binary(min_size=0, max_size=256),
    )
    @settings(max_examples=100, deadline=None)
    def test_roundtrip_with_aad(self, password: bytes, plaintext: bytes, aad: bytes):
        """Roundtrip should work with arbitrary AAD."""
        protocol = RWPv3Protocol(enable_pqc=False)
        envelope = protocol.encrypt(password, plaintext, aad=aad)
        decrypted = protocol.decrypt(password, envelope)
        assert decrypted == plaintext

    @given(
        password=st.text(min_size=1, max_size=32),
        message=st.text(min_size=0, max_size=500),
    )
    @settings(max_examples=100, deadline=None)
    def test_roundtrip_strings(self, password: str, message: str):
        """String messages should roundtrip through convenience API."""
        envelope = rwp_encrypt_message(password, message)
        decrypted = rwp_decrypt_message(password, envelope)
        assert decrypted == message

    @given(
        password=st.text(min_size=1, max_size=32),
        message=st.text(min_size=0, max_size=500),
        metadata=st.dictionaries(
            keys=st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnop"),
            values=st.text(min_size=0, max_size=50),
            max_size=5,
        ),
    )
    @settings(max_examples=50, deadline=None)
    def test_roundtrip_with_metadata(self, password: str, message: str, metadata: dict):
        """Metadata should be preserved in AAD."""
        envelope = rwp_encrypt_message(password, message, metadata=metadata)
        decrypted = rwp_decrypt_message(password, envelope)
        assert decrypted == message

        # Verify metadata is in AAD
        aad_bytes = SACRED_TONGUE_TOKENIZER.decode_section("aad", envelope["aad"])
        aad_dict = json.loads(aad_bytes.decode("utf-8"))
        assert aad_dict == metadata


class TestWrongPasswordFails:
    """Property: Wrong password always fails decryption."""

    @given(
        password=st.binary(min_size=1, max_size=64),
        wrong_suffix=st.binary(min_size=1, max_size=16),
        plaintext=st.binary(min_size=1, max_size=256),
    )
    @settings(max_examples=100, deadline=None)
    def test_wrong_password_fails(self, password: bytes, wrong_suffix: bytes, plaintext: bytes):
        """Different password should always fail."""
        protocol = RWPv3Protocol(enable_pqc=False)
        envelope = protocol.encrypt(password, plaintext)

        wrong_password = password + wrong_suffix
        assume(wrong_password != password)

        with pytest.raises(ValueError, match="AEAD authentication failed"):
            protocol.decrypt(wrong_password, envelope)

    @given(
        password=st.binary(min_size=2, max_size=64),
        plaintext=st.binary(min_size=1, max_size=256),
    )
    @settings(max_examples=100, deadline=None)
    def test_truncated_password_fails(self, password: bytes, plaintext: bytes):
        """Truncated password should fail."""
        protocol = RWPv3Protocol(enable_pqc=False)
        envelope = protocol.encrypt(password, plaintext)

        truncated = password[:-1]
        assume(len(truncated) > 0)

        with pytest.raises(ValueError, match="AEAD authentication failed"):
            protocol.decrypt(truncated, envelope)

    @given(
        password=st.binary(min_size=1, max_size=64),
        plaintext=st.binary(min_size=1, max_size=256),
        bit_position=st.integers(min_value=0, max_value=7),
        byte_position=st.integers(min_value=0),
    )
    @settings(max_examples=100, deadline=None)
    def test_bit_flipped_password_fails(
        self, password: bytes, plaintext: bytes, bit_position: int, byte_position: int
    ):
        """Single bit flip in password should fail."""
        protocol = RWPv3Protocol(enable_pqc=False)
        envelope = protocol.encrypt(password, plaintext)

        # Flip a bit in the password
        byte_pos = byte_position % len(password)
        password_list = list(password)
        password_list[byte_pos] ^= (1 << bit_position)
        wrong_password = bytes(password_list)

        assume(wrong_password != password)

        with pytest.raises(ValueError, match="AEAD authentication failed"):
            protocol.decrypt(wrong_password, envelope)


class TestTamperedCiphertextFails:
    """Property: Any modification to ciphertext fails authentication."""

    @given(
        password=st.binary(min_size=1, max_size=32),
        plaintext=st.binary(min_size=16, max_size=256),
        token_index=st.integers(min_value=0),
    )
    @settings(max_examples=100, deadline=None)
    def test_modified_ct_token_fails(
        self, password: bytes, plaintext: bytes, token_index: int
    ):
        """Modifying any ciphertext token should fail."""
        protocol = RWPv3Protocol(enable_pqc=False)
        envelope = protocol.encrypt(password, plaintext)

        # Modify a ciphertext token
        idx = token_index % len(envelope.ct)
        original_token = envelope.ct[idx]

        # Replace with a different valid Cassisivadan token
        envelope.ct[idx] = "bip'u" if original_token != "bip'u" else "bip'a"

        with pytest.raises(ValueError, match="AEAD authentication failed"):
            protocol.decrypt(password, envelope)


class TestTamperedTagFails:
    """Property: Any modification to auth tag fails authentication."""

    @given(
        password=st.binary(min_size=1, max_size=32),
        plaintext=st.binary(min_size=1, max_size=256),
        token_index=st.integers(min_value=0),
    )
    @settings(max_examples=100, deadline=None)
    def test_modified_tag_token_fails(
        self, password: bytes, plaintext: bytes, token_index: int
    ):
        """Modifying any tag token should fail."""
        protocol = RWPv3Protocol(enable_pqc=False)
        envelope = protocol.encrypt(password, plaintext)

        # Modify a tag token
        idx = token_index % len(envelope.tag)
        original_token = envelope.tag[idx]

        # Replace with a different valid Draumric token
        envelope.tag[idx] = "anvil'u" if original_token != "anvil'u" else "anvil'a"

        with pytest.raises(ValueError, match="AEAD authentication failed"):
            protocol.decrypt(password, envelope)


class TestNonceUniqueness:
    """Property: Different encryptions produce different nonces."""

    @given(
        password=st.binary(min_size=1, max_size=32),
        plaintext=st.binary(min_size=1, max_size=256),
    )
    @settings(max_examples=50, deadline=None)
    def test_nonces_are_unique(self, password: bytes, plaintext: bytes):
        """Two encryptions should produce different nonces."""
        protocol = RWPv3Protocol(enable_pqc=False)

        env1 = protocol.encrypt(password, plaintext)
        env2 = protocol.encrypt(password, plaintext)

        assert env1.nonce != env2.nonce

    @given(
        password=st.binary(min_size=1, max_size=32),
        plaintext=st.binary(min_size=1, max_size=256),
    )
    @settings(max_examples=50, deadline=None)
    def test_salts_are_unique(self, password: bytes, plaintext: bytes):
        """Two encryptions should produce different salts."""
        protocol = RWPv3Protocol(enable_pqc=False)

        env1 = protocol.encrypt(password, plaintext)
        env2 = protocol.encrypt(password, plaintext)

        assert env1.salt != env2.salt

    @given(
        password=st.binary(min_size=1, max_size=32),
        plaintext=st.binary(min_size=1, max_size=256),
    )
    @settings(max_examples=50, deadline=None)
    def test_ciphertexts_differ_for_same_plaintext(self, password: bytes, plaintext: bytes):
        """Same plaintext should produce different ciphertext each time."""
        protocol = RWPv3Protocol(enable_pqc=False)

        env1 = protocol.encrypt(password, plaintext)
        env2 = protocol.encrypt(password, plaintext)

        assert env1.ct != env2.ct


class TestSacredTongueBijectivity:
    """Property: Sacred Tongue encoding is bijective for all bytes."""

    @given(data=st.binary(min_size=1, max_size=512))
    @settings(max_examples=100, deadline=None)
    def test_all_bytes_roundtrip_ko(self, data: bytes):
        """Kor'aelin encoding should be bijective."""
        tokenizer = SACRED_TONGUE_TOKENIZER
        tokens = tokenizer.encode_bytes("ko", data)
        decoded = tokenizer.decode_tokens("ko", tokens)
        assert decoded == data

    @given(data=st.binary(min_size=1, max_size=512))
    @settings(max_examples=100, deadline=None)
    def test_all_bytes_roundtrip_av(self, data: bytes):
        """Avali encoding should be bijective."""
        tokenizer = SACRED_TONGUE_TOKENIZER
        tokens = tokenizer.encode_bytes("av", data)
        decoded = tokenizer.decode_tokens("av", tokens)
        assert decoded == data

    @given(data=st.binary(min_size=1, max_size=512))
    @settings(max_examples=100, deadline=None)
    def test_all_bytes_roundtrip_ru(self, data: bytes):
        """Runethic encoding should be bijective."""
        tokenizer = SACRED_TONGUE_TOKENIZER
        tokens = tokenizer.encode_bytes("ru", data)
        decoded = tokenizer.decode_tokens("ru", tokens)
        assert decoded == data

    @given(data=st.binary(min_size=1, max_size=512))
    @settings(max_examples=100, deadline=None)
    def test_all_bytes_roundtrip_ca(self, data: bytes):
        """Cassisivadan encoding should be bijective."""
        tokenizer = SACRED_TONGUE_TOKENIZER
        tokens = tokenizer.encode_bytes("ca", data)
        decoded = tokenizer.decode_tokens("ca", tokens)
        assert decoded == data

    @given(data=st.binary(min_size=1, max_size=512))
    @settings(max_examples=100, deadline=None)
    def test_all_bytes_roundtrip_um(self, data: bytes):
        """Umbroth encoding should be bijective."""
        tokenizer = SACRED_TONGUE_TOKENIZER
        tokens = tokenizer.encode_bytes("um", data)
        decoded = tokenizer.decode_tokens("um", tokens)
        assert decoded == data

    @given(data=st.binary(min_size=1, max_size=512))
    @settings(max_examples=100, deadline=None)
    def test_all_bytes_roundtrip_dr(self, data: bytes):
        """Draumric encoding should be bijective."""
        tokenizer = SACRED_TONGUE_TOKENIZER
        tokens = tokenizer.encode_bytes("dr", data)
        decoded = tokenizer.decode_tokens("dr", tokens)
        assert decoded == data


class TestEnvelopeSerialization:
    """Property: Envelope survives JSON serialization."""

    @given(
        password=st.binary(min_size=1, max_size=32),
        plaintext=st.binary(min_size=1, max_size=256),
    )
    @settings(max_examples=50, deadline=None)
    def test_json_roundtrip_preserves_decryption(
        self, password: bytes, plaintext: bytes
    ):
        """Envelope should decrypt after JSON roundtrip."""
        protocol = RWPv3Protocol(enable_pqc=False)
        envelope = protocol.encrypt(password, plaintext)

        # Serialize to JSON
        d = envelope.to_dict()
        json_str = json.dumps(d)

        # Deserialize
        d2 = json.loads(json_str)
        envelope2 = RWPEnvelope.from_dict(d2)

        # Decrypt should still work
        decrypted = protocol.decrypt(password, envelope2)
        assert decrypted == plaintext


class TestAADIntegrity:
    """Property: Modifying AAD breaks authentication."""

    @given(
        password=st.binary(min_size=1, max_size=32),
        plaintext=st.binary(min_size=1, max_size=256),
        aad=st.binary(min_size=1, max_size=128),
    )
    @settings(max_examples=50, deadline=None)
    def test_aad_modification_fails(
        self, password: bytes, plaintext: bytes, aad: bytes
    ):
        """Modifying AAD after encryption should fail."""
        protocol = RWPv3Protocol(enable_pqc=False)
        envelope = protocol.encrypt(password, plaintext, aad=aad)

        # Modify AAD token
        if len(envelope.aad) > 0:
            original = envelope.aad[0]
            envelope.aad[0] = "saina'u" if original != "saina'u" else "saina'a"

            with pytest.raises(ValueError, match="AEAD authentication failed"):
                protocol.decrypt(password, envelope)
