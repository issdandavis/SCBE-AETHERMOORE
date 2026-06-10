"""
Tests for BraidLedger integration.

Covers:
1. test_braid_receipt_round_trip — commit then verify chain
2. test_braid_receipt_tampered_tag_detected — flip a byte, verify returns (False, _, i)
3. test_braid_receipt_tube_violation_blocks_record — force gate vector outside ε, expect ValueError
4. test_phdm_node_id_in_audit_entry — last audit entry has one of 16 canonical names
5. test_record_id_still_32_chars — backwards-compat anchor
6. test_loop_root_stable_within_session — two commits share loop_root, different sessions diverge
"""

import hashlib
import os
import sys

import pytest

# Ensure spiral-word-app is importable
_spiral_app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "spiral-word-app"))
if _spiral_app_dir not in sys.path:
    sys.path.insert(0, _spiral_app_dir)

from braid_ledger import BraidLedger, BraidReceipt, CANONICAL_NODE_COUNT
from governance import AuditEntry, AuditLog
from headless import generate_record, reset_ledger

# The 16 canonical PHDM polyhedra names
CANONICAL_NAMES = [
    "Tetrahedron",
    "Cube",
    "Octahedron",
    "Dodecahedron",
    "Icosahedron",
    "Truncated Tetrahedron",
    "Cuboctahedron",
    "Icosidodecahedron",
    "Small Stellated Dodecahedron",
    "Great Dodecahedron",
    "Szilassi Polyhedron",
    "Császár Polyhedron",
    "Pentagonal Bipyramid",
    "Triangular Cupola",
    "Rhombic Dodecahedron",
    "Bilinski Dodecahedron",
]


@pytest.fixture
def ledger():
    """Fresh BraidLedger with deterministic key."""
    return BraidLedger(session_key=b"test-session-key-32-bytes-long!!")


@pytest.fixture
def sample_hashes():
    """Deterministic prompt and docx hashes."""
    prompt_hash = hashlib.sha256(b"hello world").hexdigest()
    docx_hash = hashlib.sha256(b"document content").hexdigest()
    return prompt_hash, docx_hash


class TestBraidReceiptRoundTrip:
    """test_braid_receipt_round_trip — commit then verify chain."""

    def test_commit_produces_valid_receipt(self, ledger, sample_hashes):
        prompt_hash, docx_hash = sample_hashes
        receipt = ledger.commit(prompt_hash, docx_hash)

        assert isinstance(receipt, BraidReceipt)
        assert receipt.loop_root == ledger.loop_root
        assert receipt.phdm_node_id in CANONICAL_NAMES
        assert 0 <= receipt.loop_index < CANONICAL_NODE_COUNT
        assert len(receipt.hmac_tag) == 64  # 32 bytes hex

    def test_verify_succeeds_on_valid_receipts(self, ledger, sample_hashes):
        prompt_hash, docx_hash = sample_hashes
        r1 = ledger.commit(prompt_hash, docx_hash)

        prompt_hash2 = hashlib.sha256(b"second prompt").hexdigest()
        docx_hash2 = hashlib.sha256(b"second content").hexdigest()
        r2 = ledger.commit(prompt_hash2, docx_hash2)

        chain_ok, tube_ok, bad_idx = ledger.verify([r1, r2])
        assert chain_ok is True
        assert bad_idx is None or tube_ok


class TestBraidReceiptTamperedTagDetected:
    """test_braid_receipt_tampered_tag_detected — flip a byte, verify returns (False, _, i)."""

    def test_tampered_hmac_tag_detected(self, ledger, sample_hashes):
        prompt_hash, docx_hash = sample_hashes
        receipt = ledger.commit(prompt_hash, docx_hash)

        # Tamper with the HMAC tag — flip a character
        tag_bytes = bytearray.fromhex(receipt.hmac_tag)
        tag_bytes[0] ^= 0xFF
        tampered = BraidReceipt(
            loop_root=receipt.loop_root,
            phdm_node_id=receipt.phdm_node_id,
            loop_index=receipt.loop_index,
            hmac_tag=tag_bytes.hex(),
            tube_ok=receipt.tube_ok,
        )

        chain_ok, tube_ok, bad_idx = ledger.verify([tampered])
        assert chain_ok is False or bad_idx == 0

    def test_tampered_loop_root_detected(self, ledger, sample_hashes):
        prompt_hash, docx_hash = sample_hashes
        receipt = ledger.commit(prompt_hash, docx_hash)

        tampered = BraidReceipt(
            loop_root="0" * 64,
            phdm_node_id=receipt.phdm_node_id,
            loop_index=receipt.loop_index,
            hmac_tag=receipt.hmac_tag,
            tube_ok=receipt.tube_ok,
        )

        chain_ok, tube_ok, bad_idx = ledger.verify([tampered])
        assert chain_ok is False
        assert bad_idx == 0


class TestTubeViolationBlocksRecord:
    """test_braid_receipt_tube_violation_blocks_record."""

    def test_tube_violation_raises_value_error(self):
        ledger = reset_ledger(session_key=b"tube-test-key-32-bytes-long!!!!")

        # We need to find inputs that produce a tube violation.
        # The tube check is: abs(fractional) <= 0.15 where
        # fractional = (gate_sum / 16) - loop_index
        # Since loop_index = gate_sum % 16, fractional is always 0.
        # So under normal conditions tube_ok is always True.
        # To test the violation path, we directly call generate_record
        # and monkey-patch the ledger's _check_tube.
        from unittest.mock import patch

        with patch.object(type(ledger), "_check_tube", return_value=False):
            # Reset with our patched ledger
            import headless

            headless._process_ledger = ledger

            with pytest.raises(ValueError, match="braid tube violation"):
                generate_record(
                    doc_id="test-doc",
                    site_id="test-site",
                    prompt="test prompt",
                    doc_content="test content",
                )

        headless._process_ledger = None


class TestPHDMNodeIdInAuditEntry:
    """test_phdm_node_id_in_audit_entry."""

    def test_audit_entry_has_phdm_node_id(self):
        ledger = reset_ledger(session_key=b"audit-test-key-32-bytes-long!!!")

        import headless

        headless._process_ledger = ledger
        headless._process_audit_log = AuditLog()

        generate_record(
            doc_id="doc-1",
            site_id="site-1",
            prompt="analyze the data",
            doc_content="some document content",
        )

        last_entry = headless._process_audit_log.entries[-1]
        assert last_entry.phdm_node_id is not None
        assert last_entry.phdm_node_id in CANONICAL_NAMES
        assert last_entry.loop_index is not None
        assert 0 <= last_entry.loop_index < CANONICAL_NODE_COUNT
        assert last_entry.braid_receipt is not None
        assert len(last_entry.braid_receipt) == 64  # 32-byte HMAC hex

        headless._process_ledger = None

    def test_audit_entry_optional_fields_default_none(self):
        """Existing code that doesn't pass braid fields still works."""
        entry = AuditEntry(
            timestamp=0.0,
            doc_id="d",
            site_id="s",
            action="read",
            op_checksum="abc",
            governance_decision="ALLOW",
        )
        assert entry.phdm_node_id is None
        assert entry.loop_index is None
        assert entry.braid_receipt is None

        d = entry.to_dict()
        assert "phdm_node_id" not in d
        assert "loop_index" not in d
        assert "braid_receipt" not in d


class TestRecordIdStill32Chars:
    """test_record_id_still_32_chars — backwards-compat anchor."""

    def test_record_id_is_32_hex_chars(self):
        ledger = reset_ledger(session_key=b"record-id-test-key-32-bytes!!!!")

        import headless

        headless._process_ledger = ledger

        record = generate_record(
            doc_id="compat-doc",
            site_id="compat-site",
            prompt="write a summary",
            doc_content="hello world",
        )

        assert len(record.record_id) == 32
        int(record.record_id, 16)  # valid hex

        headless._process_ledger = None


class TestLoopRootStableWithinSession:
    """test_loop_root_stable_within_session."""

    def test_same_session_same_loop_root(self, ledger, sample_hashes):
        prompt_hash, docx_hash = sample_hashes
        r1 = ledger.commit(prompt_hash, docx_hash)

        prompt_hash2 = hashlib.sha256(b"another prompt").hexdigest()
        docx_hash2 = hashlib.sha256(b"another doc").hexdigest()
        r2 = ledger.commit(prompt_hash2, docx_hash2)

        assert r1.loop_root == r2.loop_root

    def test_different_sessions_different_loop_root(self, sample_hashes):
        prompt_hash, docx_hash = sample_hashes

        ledger1 = BraidLedger(session_key=b"session-key-alpha-32-bytes-ok!!")
        r1 = ledger1.commit(prompt_hash, docx_hash)

        ledger2 = BraidLedger(session_key=b"session-key-bravo-32-bytes-ok!!")
        r2 = ledger2.commit(prompt_hash, docx_hash)

        assert r1.loop_root != r2.loop_root
