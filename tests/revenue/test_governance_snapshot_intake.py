from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.revenue.governance_snapshot_intake import create_snapshot_packet


def test_create_snapshot_packet_generates_fulfillment_files(tmp_path: Path) -> None:
    paths = create_snapshot_packet(
        buyer_email="buyer@example.com",
        workflow_name="Customer support chatbot",
        payment_reference="stripe:cs_test_123",
        deadline="2026-05-15",
        notes="Review public docs only.",
        out_root=tmp_path,
    )

    assert paths["folder"].exists()
    assert paths["intake"].exists()
    assert paths["memo"].exists()
    assert paths["evidence"].exists()
    assert paths["delivery"].exists()

    intake = json.loads(paths["intake"].read_text(encoding="utf-8"))
    assert intake["buyer_email"] == "buyer@example.com"
    assert intake["workflow_name"] == "Customer support chatbot"
    assert intake["payment_reference"] == "stripe:cs_test_123"

    memo = paths["memo"].read_text(encoding="utf-8")
    assert "AI Governance Snapshot Findings Memo" in memo
    assert "three prioritized fixes" in memo

    delivery = paths["delivery"].read_text(encoding="utf-8")
    assert "not legal advice" in delivery
    assert "Final package delivered by email" in delivery


def test_create_snapshot_packet_rejects_bad_intake(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="buyer_email"):
        create_snapshot_packet(
            buyer_email="not-an-email",
            workflow_name="Workflow",
            out_root=tmp_path,
        )

    with pytest.raises(ValueError, match="workflow_name"):
        create_snapshot_packet(
            buyer_email="buyer@example.com",
            workflow_name="",
            out_root=tmp_path,
        )
