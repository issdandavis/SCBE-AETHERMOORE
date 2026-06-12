"""Liveness tests for the unsealed-audit witness fallback in geoseal_execution_gate.

When append_sealed_exec_audit has no audit secret, it must still leave a durable
unsealed witness row (gate="geoseal_exec", event="unsealed_audit") while keeping
the SEALED contract: it returns False and writes nothing to the sealed log.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.crypto.geoseal_execution_gate import (
    DEFAULT_AUDIT_SECRET_ENV,
    append_sealed_exec_audit,
)


def _witness_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _record() -> dict:
    return {
        "version": "geoseal-exec-audit-v1",
        "timestamp": 1234567890.0,
        "command": "python -c \"print('ok')\"",
        "max_tier": "QUARANTINE",
        "decision": {"command_sha256": "a" * 64, "tier": "QUARANTINE"},
    }


def test_no_secret_returns_false_but_leaves_unsealed_witness(tmp_path, monkeypatch):
    witness_path = tmp_path / "w.jsonl"
    audit_log = tmp_path / "exec_audit.sealed.jsonl"
    monkeypatch.setenv("SCBE_GATE_WITNESS_PATH", str(witness_path))
    monkeypatch.delenv("SCBE_GATE_WITNESS_DISABLE", raising=False)
    monkeypatch.delenv(DEFAULT_AUDIT_SECRET_ENV, raising=False)

    written = append_sealed_exec_audit(_record(), audit_log=audit_log)

    assert written is False  # SEALED contract unchanged: no secret -> audit_written stays False
    assert not audit_log.exists()  # no sealed record was written
    [row] = _witness_rows(witness_path)
    assert row["gate"] == "geoseal_exec"
    assert row["event"] == "unsealed_audit"
    assert row["subject"] == "a" * 64
    assert row["detail"]["tier"] == "QUARANTINE"
    assert row["detail"]["sealed"] is False


def test_no_secret_with_missing_decision_uses_empty_subject(tmp_path, monkeypatch):
    witness_path = tmp_path / "w.jsonl"
    monkeypatch.setenv("SCBE_GATE_WITNESS_PATH", str(witness_path))
    monkeypatch.delenv("SCBE_GATE_WITNESS_DISABLE", raising=False)
    monkeypatch.delenv(DEFAULT_AUDIT_SECRET_ENV, raising=False)

    written = append_sealed_exec_audit({"version": "geoseal-exec-audit-v1"}, audit_log=tmp_path / "a.jsonl")

    assert written is False
    [row] = _witness_rows(witness_path)
    assert row["event"] == "unsealed_audit"
    assert row["subject"] == ""


def test_with_secret_seals_audit_and_writes_no_unsealed_witness(tmp_path, monkeypatch):
    witness_path = tmp_path / "w.jsonl"
    audit_log = tmp_path / "exec_audit.sealed.jsonl"
    monkeypatch.setenv("SCBE_GATE_WITNESS_PATH", str(witness_path))
    monkeypatch.delenv("SCBE_GATE_WITNESS_DISABLE", raising=False)
    monkeypatch.delenv(DEFAULT_AUDIT_SECRET_ENV, raising=False)

    written = append_sealed_exec_audit(_record(), audit_log=audit_log, audit_secret="unit-test-secret")

    assert written is True
    packet = json.loads(audit_log.read_text(encoding="utf-8").splitlines()[0])
    assert packet["metadata"]["kind"] == "geoseal_exec_audit"
    unsealed_rows = [r for r in _witness_rows(witness_path) if r["event"] == "unsealed_audit"]
    assert unsealed_rows == []  # sealed path leaves NO unsealed witness


def test_secret_from_env_var_also_seals_without_witness(tmp_path, monkeypatch):
    witness_path = tmp_path / "w.jsonl"
    audit_log = tmp_path / "exec_audit.sealed.jsonl"
    monkeypatch.setenv("SCBE_GATE_WITNESS_PATH", str(witness_path))
    monkeypatch.delenv("SCBE_GATE_WITNESS_DISABLE", raising=False)
    monkeypatch.setenv(DEFAULT_AUDIT_SECRET_ENV, "env-test-secret")

    written = append_sealed_exec_audit(_record(), audit_log=audit_log)

    assert written is True
    assert audit_log.exists()
    assert _witness_rows(witness_path) == []
