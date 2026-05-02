"""PHDM braid receipt tests for SpiralWord headless records."""

from __future__ import annotations

from dataclasses import replace

import pytest

pytest.importorskip("docx", reason="python-docx not installed")

from braid_ledger import BraidLedger  # noqa: E402
from headless import generate_record  # noqa: E402
from sync_engine import SyncEngine  # noqa: E402
from src.symphonic_cipher.scbe_aethermoore.qc_lattice.phdm import get_phdm_family  # noqa: E402


def test_braid_receipt_round_trip():
    ledger = BraidLedger(session_key=b"test-session-key")
    receipt = ledger.commit("a" * 64, "b" * 64)

    chain_ok, tube_ok, first_bad = ledger.verify([receipt])

    assert chain_ok is True
    assert tube_ok is True
    assert first_bad is None
    assert receipt.loop_root == ledger.loop_root
    assert len(receipt.hmac_tag) == 64


def test_braid_receipt_tampered_tag_detected():
    ledger = BraidLedger(session_key=b"test-session-key")
    receipt = ledger.commit("a" * 64, "b" * 64)
    tampered = replace(receipt, hmac_tag="00" + receipt.hmac_tag[2:])

    chain_ok, tube_ok, first_bad = ledger.verify([tampered])

    assert chain_ok is False
    assert tube_ok is True
    assert first_bad == 0


def test_braid_receipt_tube_violation_detected():
    ledger = BraidLedger(session_key=b"test-session-key")
    receipt = ledger.commit("a" * 64, "b" * 64, gate_vector=[0, 255])

    chain_ok, tube_ok, first_bad = ledger.verify([receipt])

    assert chain_ok is True
    assert tube_ok is False
    assert first_bad == 0


def test_loop_root_stable_within_session_and_differs_by_key():
    left = BraidLedger(session_key=b"left-session")
    right = BraidLedger(session_key=b"right-session")

    first = left.commit("1" * 64, "2" * 64)
    second = left.commit("3" * 64, "4" * 64)

    assert first.loop_root == second.loop_root == left.loop_root
    assert left.loop_root != right.loop_root


def test_generate_record_attaches_braid_fields():
    sync = SyncEngine()
    _, record, _ = generate_record(
        sync=sync,
        doc_id="braid-doc",
        prompt="Write a governed braid memo.",
        provider="echo",
        site_id="braid-agent",
    )

    family_names = {poly.name for poly in get_phdm_family()}
    assert len(record.record_id) == 32
    assert record.phdm_node_id in family_names
    assert record.loop_index is not None
    assert 0 <= record.loop_index < 16
    assert record.braid_receipt is not None
    assert len(record.braid_receipt) == 64
    assert record.loop_root is not None
    assert len(record.loop_root) == 64


def test_generate_record_writes_braid_audit_fields():
    from governance import audit_log

    sync = SyncEngine()
    before = len(audit_log.entries)
    _, record, _ = generate_record(
        sync=sync,
        doc_id="braid-audit-doc",
        prompt="Draft an audit trace.",
        provider="echo",
    )

    assert len(audit_log.entries) == before + 1
    last = audit_log.entries[-1]
    assert last.phdm_node_id == record.phdm_node_id
    assert last.loop_index == record.loop_index
    assert last.braid_receipt == record.braid_receipt
    assert record.record_id in last.governance_decision
