"""
Tests for the document verification pipeline (Round Table consensus).

@module tests/test_doc_verifier
@layer Layer 14
@version 1.0.0
"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

# Add training/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))
from doc_verifier import (
    COUNCIL_MEMBERS,
    DEFAULT_QUORUM,
    attest_document,
    build_manifest,
    compute_attestation_hash,
    compute_manifest_hash,
    discover_docs,
    verify_manifest,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestCouncilConfig:
    def test_five_council_members(self):
        assert len(COUNCIL_MEMBERS) == 5

    def test_unique_provider_ids(self):
        ids = [m["id"] for m in COUNCIL_MEMBERS]
        assert len(set(ids)) == 5

    def test_unique_tongues(self):
        tongues = [m["tongue"] for m in COUNCIL_MEMBERS]
        assert len(set(tongues)) == 5

    def test_all_required_fields(self):
        for m in COUNCIL_MEMBERS:
            assert "id" in m
            assert "provider" in m
            assert "role" in m
            assert "tongue" in m
            assert "signature_suffix" in m

    def test_quorum_is_bft(self):
        # BFT requires >2/3 — with 5 members, 3 is minimum
        assert DEFAULT_QUORUM >= 3
        assert DEFAULT_QUORUM <= len(COUNCIL_MEMBERS)


class TestDocDiscovery:
    def test_discovers_docs(self):
        docs = discover_docs()
        assert len(docs) > 0

    def test_doc_has_required_fields(self):
        docs = discover_docs()
        for d in docs[:5]:  # Check first 5
            assert "id" in d
            assert "filename" in d
            assert d["content_hash"].startswith("sha256:")
            assert len(d["content_hash"]) == 7 + 64  # sha256: + 64 hex
            assert "category" in d
            assert "verification" in d

    def test_readme_is_discovered(self):
        docs = discover_docs()
        filenames = [d["filename"] for d in docs]
        assert "README.md" in filenames

    def test_content_hash_is_correct(self):
        docs = discover_docs()
        for d in docs[:3]:
            filepath = REPO_ROOT / d["filename"]
            actual = f"sha256:{hashlib.sha256(filepath.read_bytes()).hexdigest()}"
            assert d["content_hash"] == actual

    def test_all_unverified_initially(self):
        docs = discover_docs()
        for d in docs:
            assert d["verification"]["status"] == "unverified"


class TestAttestation:
    def test_single_attestation_stays_pending(self):
        doc = discover_docs()[0]
        attest_document(doc, ["claude"])
        assert doc["verification"]["status"] == "pending"
        assert "claude" in doc["verification"]["verified_by"]

    def test_quorum_attestation_verifies(self):
        doc = discover_docs()[0]
        attest_document(doc, ["claude", "gpt", "sonar"])
        assert doc["verification"]["status"] == "verified"
        assert len(doc["verification"]["verified_by"]) == 3
        assert "attestation_hash" in doc["verification"]

    def test_no_duplicate_attestations(self):
        doc = discover_docs()[0]
        attest_document(doc, ["claude"])
        attest_document(doc, ["claude", "gpt"])
        assert doc["verification"]["verified_by"].count("claude") == 1

    def test_unknown_member_raises(self):
        doc = discover_docs()[0]
        with pytest.raises(ValueError, match="Unknown council member"):
            attest_document(doc, ["unknown_ai"])

    def test_attestation_hash_deterministic(self):
        h1 = compute_attestation_hash("sha256:abc", ["claude", "gpt"], "2026-01-01T00:00:00Z")
        h2 = compute_attestation_hash("sha256:abc", ["gpt", "claude"], "2026-01-01T00:00:00Z")
        # Sorted internally, so order doesn't matter
        assert h1 == h2

    def test_different_content_different_hash(self):
        h1 = compute_attestation_hash("sha256:abc", ["claude"], "2026-01-01T00:00:00Z")
        h2 = compute_attestation_hash("sha256:def", ["claude"], "2026-01-01T00:00:00Z")
        assert h1 != h2


class TestManifest:
    def test_build_manifest_structure(self):
        docs = discover_docs()[:5]
        manifest = build_manifest(docs)
        assert manifest["schema_version"] == "1.0.0"
        assert manifest["verification_protocol"] == "roundtable-consensus"
        assert "council" in manifest
        assert "documents" in manifest
        assert "manifest_hash" in manifest
        assert len(manifest["manifest_hash"]) == 64

    def test_manifest_hash_changes_with_docs(self):
        docs1 = discover_docs()[:3]
        docs2 = discover_docs()[:5]
        h1 = compute_manifest_hash(docs1)
        h2 = compute_manifest_hash(docs2)
        assert h1 != h2

    def test_verify_valid_manifest(self):
        docs = discover_docs()[:5]
        manifest = build_manifest(docs)
        errors = verify_manifest(manifest)
        assert errors == []

    def test_verify_detects_tampered_hash(self):
        docs = discover_docs()[:5]
        manifest = build_manifest(docs)
        manifest["manifest_hash"] = "0" * 64
        errors = verify_manifest(manifest)
        assert any("Manifest hash mismatch" in e for e in errors)

    def test_verify_detects_missing_file(self):
        docs = [{"id": "fake", "filename": "nonexistent.md",
                 "content_hash": "sha256:" + "0" * 64,
                 "category": "reference", "verification": {"status": "unverified",
                 "consensus_required": 3, "verified_by": []}}]
        manifest = build_manifest(docs)
        errors = verify_manifest(manifest)
        assert any("Missing file" in e for e in errors)
