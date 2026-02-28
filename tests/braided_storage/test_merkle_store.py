"""Tests for BraidedVoxelStore — MerkleChain."""

import time

import pytest

from src.braided_storage.merkle_store import MerkleChain, merkle_root
from src.braided_storage.types import BraidedPayload, SemanticBits


def _make_braided(tongue="KO", quarantined=False, **overrides) -> BraidedPayload:
    bits = SemanticBits(
        dominant_tongue=tongue,
        tongue_trits=[1, 0, -1, 0, 1, -1],
        fingerprint_ids=["fp1"],
        sha256_hash=overrides.pop("sha256_hash", "a" * 64),
        threat_score=0.0,
        governance_decision="ALLOW",
    )
    defaults = dict(
        strand_intent=0.8,
        strand_memory=0.9,
        strand_governance=0.1,
        braided_time=0.072,
        d_braid=0.5,
        harmonic_cost=1.3,
        phase_state=(0, 0),
        phase_label="equilibrium",
        semantic_bits=bits,
        raw_bytes=b"merkle test data",
        source="test://merkle",
        mime_type="text/plain",
        quarantined=quarantined,
    )
    defaults.update(overrides)
    return BraidedPayload(**defaults)


@pytest.fixture
def chain():
    return MerkleChain()


class TestAppendVerify:
    def test_append_verify(self, chain):
        braided = _make_braided()
        entry_hash = chain.append(braided)
        assert isinstance(entry_hash, str)
        assert len(entry_hash) == 64  # SHA-256 hex

        # Verify the entry
        assert chain.verify(entry_hash) is True

    def test_verify_nonexistent(self, chain):
        assert chain.verify("nonexistent_hash") is False


class TestChainIntegrity:
    def test_chain_integrity(self, chain):
        for i in range(5):
            braided = _make_braided(sha256_hash=f"{i:064d}")
            chain.append(braided)

        valid, broken_idx, reason = chain.verify_chain()
        assert valid is True
        assert broken_idx is None


class TestTemporalQuery:
    def test_temporal_query(self, chain):
        t_before = time.time() - 1
        for i in range(3):
            braided = _make_braided(sha256_hash=f"{i:064d}")
            chain.append(braided)
        t_after = time.time() + 1

        results = chain.query_by_time(t_before, t_after)
        assert len(results) == 3


class TestTongueQuery:
    def test_tongue_query(self, chain):
        chain.append(_make_braided(tongue="KO"))
        chain.append(_make_braided(tongue="AV", sha256_hash="b" * 64))
        chain.append(_make_braided(tongue="KO", sha256_hash="c" * 64))

        ko_entries = chain.query_by_tongue("KO")
        assert len(ko_entries) == 2

        av_entries = chain.query_by_tongue("AV")
        assert len(av_entries) == 1


class TestQuarantine:
    def test_quarantine_query(self, chain):
        chain.append(_make_braided(quarantined=False))
        chain.append(_make_braided(quarantined=True, sha256_hash="q" * 64))
        chain.append(_make_braided(quarantined=True, sha256_hash="r" * 64))

        quarantined = chain.query_quarantined()
        assert len(quarantined) == 2
        assert all(e.quarantined for e in quarantined)

    def test_quarantine_count(self, chain):
        chain.append(_make_braided(quarantined=False))
        chain.append(_make_braided(quarantined=True, sha256_hash="q" * 64))
        assert chain.quarantine_count == 1


class TestMerkleRoot:
    def test_merkle_root(self, chain):
        chain.append(_make_braided(sha256_hash="1" * 64))
        chain.append(_make_braided(sha256_hash="2" * 64))
        root = chain.compute_merkle_root()
        assert isinstance(root, str)
        assert len(root) == 64

    def test_merkle_root_empty(self, chain):
        root = chain.compute_merkle_root()
        assert isinstance(root, str)

    def test_merkle_root_deterministic(self):
        hashes = ["abc", "def", "ghi"]
        r1 = merkle_root(hashes)
        r2 = merkle_root(hashes)
        assert r1 == r2
