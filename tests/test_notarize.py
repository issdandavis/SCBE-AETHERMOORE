"""Tests for SCBE Notarization Service."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from notarize import notarize, verify, batch_notarize, cert_to_json, cert_from_json, NotarizationCert


class TestNotarize:
    def test_basic_notarize(self):
        cert = notarize(b"hello world", signer="test")
        assert cert.sha256
        assert cert.sha3_256
        assert cert.tongue_encoded_hash
        assert cert.hmac_sha256
        assert cert.signer == "test"
        assert cert.data_size == 11

    def test_verify_valid(self):
        cert = notarize(b"test data", signer="test")
        assert verify(cert) is True

    def test_verify_tampered(self):
        cert = notarize(b"test data", signer="test")
        cert.description = "tampered"
        assert verify(cert) is False

    def test_verify_wrong_key(self):
        cert = notarize(b"test data", signer="test", signing_key="secret")
        assert verify(cert, signing_key="wrong") is False
        assert verify(cert, signing_key="secret") is True

    def test_different_tongues(self):
        tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]
        certs = [notarize(b"same data", tongue=t) for t in tongues]
        # All should have same SHA-256 but different tongue encodings
        hashes = set(c.sha256 for c in certs)
        assert len(hashes) == 1  # Same hash
        encodings = set(c.tongue_encoded_hash for c in certs)
        assert len(encodings) == 6  # Different tongue encodings

    def test_different_data_different_hash(self):
        c1 = notarize(b"data one")
        c2 = notarize(b"data two")
        assert c1.sha256 != c2.sha256
        assert c1.tongue_encoded_hash != c2.tongue_encoded_hash

    def test_batch_notarize(self):
        items = [(b"doc1", "first"), (b"doc2", "second"), (b"doc3", "third")]
        certs = batch_notarize(items)
        assert len(certs) == 3
        assert all(verify(c) for c in certs)
        assert certs[0].description == "first"
        assert certs[2].description == "third"

    def test_json_roundtrip(self):
        cert = notarize(b"roundtrip test", tongue="KO", signer="issac")
        json_str = cert_to_json(cert)
        restored = cert_from_json(json_str)
        assert restored.sha256 == cert.sha256
        assert restored.tongue_encoded_hash == cert.tongue_encoded_hash
        assert restored.hmac_sha256 == cert.hmac_sha256
        assert verify(restored)

    def test_cert_has_timestamp(self):
        cert = notarize(b"timestamp test")
        assert cert.timestamp > 0
        assert "T" in cert.timestamp_iso
        assert cert.timestamp_iso.endswith("Z")

    def test_cert_has_nonce(self):
        c1 = notarize(b"same data")
        c2 = notarize(b"same data")
        assert c1.nonce != c2.nonce  # Different nonces each time

    def test_empty_data(self):
        cert = notarize(b"")
        assert cert.sha256  # Empty data still gets a hash
        assert cert.data_size == 0
        assert verify(cert)

    def test_large_data(self):
        data = b"x" * 100000
        cert = notarize(data)
        assert cert.data_size == 100000
        assert verify(cert)

    def test_patent_reference(self):
        cert = notarize(b"test")
        assert cert.patent == "USPTO #63/961,403"
        assert cert.system == "SCBE-AETHERMOORE"
