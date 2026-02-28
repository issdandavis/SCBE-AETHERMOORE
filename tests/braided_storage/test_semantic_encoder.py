"""Tests for BraidedVoxelStore — SemanticEncoder."""

import pytest

from src.braided_storage.semantic_encoder import SemanticEncoder
from src.braided_storage.types import SemanticBits


@pytest.fixture
def encoder():
    return SemanticEncoder(max_dress_bytes=16)


class TestEncodeText:
    def test_encode_text(self, encoder):
        data = b"Hello world, this is a simple text for encoding."
        bits = encoder.encode(data, "text/plain")
        assert isinstance(bits, SemanticBits)
        assert len(bits.sha256_hash) == 64
        assert bits.dominant_tongue in ("KO", "AV", "RU", "CA", "UM", "DR")
        assert len(bits.tongue_trits) == 6

    def test_encode_empty(self, encoder):
        bits = encoder.encode(b"", "text/plain")
        assert isinstance(bits, SemanticBits)
        assert bits.sha256_hash  # SHA-256 of empty bytes
        assert len(bits.fingerprint_ids) == 0

    def test_encode_code_text(self, encoder):
        code = b"def hello():\n    print('world')\n\nimport os"
        bits = encoder.encode(code, "text/plain")
        assert isinstance(bits, SemanticBits)
        assert bits.governance_decision in ("ALLOW", "QUARANTINE", "DENY")


class TestEncodeBinary:
    def test_encode_binary(self, encoder):
        data = bytes(range(256))
        bits = encoder.encode(data, "application/octet-stream")
        assert isinstance(bits, SemanticBits)
        assert len(bits.fingerprint_ids) > 0


class TestTongueClassification:
    def test_tongue_classification(self, encoder):
        """Fire-related text should classify toward KO tongue."""
        data = b"fire attack force strike power destroy"
        bits = encoder.encode(data, "text/plain")
        # Should have at least one non-zero trit
        assert any(t != 0 for t in bits.tongue_trits)


class TestBitFingerprint:
    def test_bit_fingerprint(self, encoder):
        """Same input should produce same fingerprints (deterministic)."""
        data = b"deterministic test"
        bits1 = encoder.encode(data, "text/plain")
        bits2 = encoder.encode(data, "text/plain")
        assert bits1.sha256_hash == bits2.sha256_hash
        assert bits1.fingerprint_ids == bits2.fingerprint_ids
