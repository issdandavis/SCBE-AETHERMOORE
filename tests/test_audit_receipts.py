"""Receipt-system invariants: every issued receipt is sealed, and tampering is detectable.

Runs in deterministic mode (no model needed): issue() exercises the gate over the fixed
evaluation set and seals each result. These pin that the seal covers the receipt content
and that altering a receipt breaks its seal.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("attest_mod", ROOT / "scripts" / "audit" / "generate_attestation.py")
attest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(attest)


def test_issue_produces_sealed_receipts():
    run = attest.issue("2026-01-01T00-00-00Z")
    assert run["total"] == 17
    assert len(run["receipts"]) == 17
    for rec in run["receipts"]:
        assert rec["receipt_seal_sha256"] == attest._seal(rec), f"seal mismatch on {rec['receipt_no']}"
        assert rec["subject"]["input_sha256"]
        assert rec["evaluation"]["decision"] in ("ALLOW", "QUARANTINE", "ESCALATE", "DENY")


def test_run_seal_binds_all_receipts():
    run = attest.issue("2026-01-01T00-00-00Z")
    assert isinstance(run["run_seal"], str) and len(run["run_seal"]) == 64


def test_tampering_breaks_the_seal():
    run = attest.issue("2026-01-01T00-00-00Z")
    rec = run["receipts"][0]
    assert rec["receipt_seal_sha256"] == attest._seal(rec)
    rec["evaluation"]["decision"] = "ALLOW"  # alter the verdict after issuance
    assert rec["receipt_seal_sha256"] != attest._seal(rec)
