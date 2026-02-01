"""
Python-side interoperability tests.

Validates that Python Sacred Tongue encoding matches the test vectors
and can decode tokens that TypeScript would produce.
"""

import json
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.crypto.sacred_tongues import (
    SACRED_TONGUE_TOKENIZER,
    SECTION_TONGUES,
    TONGUES,
)


# Load test vectors
VECTORS_PATH = Path(__file__).parent / "test_vectors.json"


@pytest.fixture
def vectors():
    """Load test vectors from JSON file."""
    with open(VECTORS_PATH) as f:
        return json.load(f)


class TestSacredTongueEncode:
    """Validate Sacred Tongue encoding matches test vectors."""

    def test_vectors_exist(self, vectors):
        """Test vectors should be loaded."""
        assert len(vectors["sacred_tongue_encode"]) > 0

    def test_all_encode_vectors(self, vectors):
        """All encode vectors should produce expected tokens."""
        for vector in vectors["sacred_tongue_encode"]:
            input_bytes = bytes.fromhex(vector["input_hex"])
            expected = vector["expected_tokens"]
            actual = SACRED_TONGUE_TOKENIZER.encode_bytes(vector["tongue"], input_bytes)
            assert actual == expected, f"Mismatch in {vector['description']}"


class TestSectionMapping:
    """Validate section to tongue mapping."""

    def test_vectors_exist(self, vectors):
        """Test vectors should be loaded."""
        assert len(vectors["section_mapping"]) > 0

    def test_all_section_vectors(self, vectors):
        """All section vectors should map correctly."""
        for vector in vectors["section_mapping"]:
            # Check tongue mapping
            actual_tongue = SECTION_TONGUES[vector["section"]]
            assert actual_tongue == vector["expected_tongue"]

            # Check token encoding
            input_bytes = bytes.fromhex(vector["input_hex"])
            expected = vector["expected_tokens"]
            actual = SACRED_TONGUE_TOKENIZER.encode_section(vector["section"], input_bytes)
            assert actual == expected


class TestBijectivity:
    """Validate encoding is bijective (roundtrips correctly)."""

    def test_vectors_exist(self, vectors):
        """Test vectors should be loaded."""
        assert len(vectors["bijectivity"]) > 0

    def test_all_bijectivity_vectors(self, vectors):
        """All bijectivity vectors should roundtrip."""
        for vector in vectors["bijectivity"]:
            tongue = vector["tongue"]
            byte_value = vector["byte_value"]
            expected_token = vector["token"]

            # Encode
            tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(tongue, bytes([byte_value]))
            assert len(tokens) == 1
            assert tokens[0] == expected_token

            # Decode
            decoded = SACRED_TONGUE_TOKENIZER.decode_tokens(tongue, tokens)
            assert decoded == bytes([byte_value])
            assert decoded.hex() == vector["roundtrip_hex"]


class TestTongueSpecs:
    """Validate tongue specifications match."""

    def test_vectors_exist(self, vectors):
        """Test vectors should be loaded."""
        assert len(vectors["tongue_specs"]) == 6

    def test_all_spec_vectors(self, vectors):
        """All tongue specs should match."""
        for vector in vectors["tongue_specs"]:
            spec = TONGUES[vector["tongue"]]

            assert spec.name == vector["name"]
            assert len(spec.prefixes) == vector["prefix_count"]
            assert len(spec.suffixes) == vector["suffix_count"]
            assert spec.prefixes[0] == vector["first_prefix"]
            assert spec.prefixes[15] == vector["last_prefix"]
            assert spec.suffixes[0] == vector["first_suffix"]
            assert spec.suffixes[15] == vector["last_suffix"]

            # Verify sample tokens
            token_00 = SACRED_TONGUE_TOKENIZER.encode_bytes(vector["tongue"], b"\x00")[0]
            token_ff = SACRED_TONGUE_TOKENIZER.encode_bytes(vector["tongue"], b"\xff")[0]
            assert token_00 == vector["sample_token_0x00"]
            assert token_ff == vector["sample_token_0xFF"]


class TestPBKDF2:
    """Validate PBKDF2 key derivation matches."""

    def test_vectors_exist(self, vectors):
        """Test vectors should be loaded."""
        assert len(vectors["pbkdf2"]) > 0

    def test_all_pbkdf2_vectors(self, vectors):
        """All PBKDF2 vectors should match."""
        import hashlib

        for vector in vectors["pbkdf2"]:
            password = bytes.fromhex(vector["password_hex"])
            salt = bytes.fromhex(vector["salt_hex"])

            key = hashlib.pbkdf2_hmac(
                "sha256",
                password,
                salt,
                vector["iterations"],
                dklen=vector["key_length"],
            )

            assert key.hex() == vector["expected_key_hex"]


class TestCrossLanguageTokens:
    """Test that Python can decode TypeScript-style tokens."""

    def test_decode_typescript_tokens(self):
        """Python should decode tokens that TypeScript would produce."""
        # These are the tokens TypeScript produces for byte 0x00
        typescript_tokens = {
            "ko": "sil'a",
            "av": "saina'a",
            "ru": "khar'ak",
            "ca": "bip'a",
            "um": "veil'a",
            "dr": "anvil'a",
        }

        for tongue, token in typescript_tokens.items():
            decoded = SACRED_TONGUE_TOKENIZER.decode_tokens(tongue, [token])
            assert decoded == b"\x00", f"Failed to decode {tongue}:{token}"

    def test_encode_matches_typescript_expectation(self):
        """Python encoding should match what TypeScript expects."""
        # Verify specific bytes produce specific tokens
        test_cases = [
            ("ko", 0x00, "sil'a"),
            ("ko", 0xFF, "vara'esh"),
            ("av", 0x00, "saina'a"),
            ("av", 0xFF, "tide'ul"),
            ("ru", 0x00, "khar'ak"),
            ("ru", 0xFF, "iron'th"),
            ("ca", 0x00, "bip'a"),
            ("ca", 0xFF, "chass'sh"),
            ("um", 0x00, "veil'a"),
            ("um", 0xFF, "shade'nul"),
            ("dr", 0x00, "anvil'a"),
            ("dr", 0xFF, "ember'on"),
        ]

        for tongue, byte_val, expected_token in test_cases:
            actual = SACRED_TONGUE_TOKENIZER.encode_bytes(tongue, bytes([byte_val]))[0]
            assert actual == expected_token, f"Mismatch: {tongue}[{byte_val}] = {actual}, expected {expected_token}"


class TestSummary:
    """Validate test vector summary."""

    def test_vector_counts(self, vectors):
        """Summary counts should be accurate."""
        summary = vectors["summary"]
        assert summary["total_vectors"] == 93
        assert summary["sacred_tongue_encode"] == 42
        assert summary["section_mapping"] == 6
        assert summary["bijectivity"] == 36
        assert summary["tongue_specs"] == 6
        assert summary["pbkdf2"] == 3
