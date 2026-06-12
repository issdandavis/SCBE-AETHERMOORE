"""Contract tests for the gate_witness sink (src/governance/gate_witness.py)."""

from __future__ import annotations

import json

from src.governance import gate_witness as gw


def _rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_witness_writes_durable_schema_row(tmp_path, monkeypatch):
    out = tmp_path / "witness.jsonl"
    monkeypatch.setenv("SCBE_GATE_WITNESS_PATH", str(out))
    monkeypatch.delenv("SCBE_GATE_WITNESS_DISABLE", raising=False)

    ok = gw.gate_witness("kernel_antivirus", "deny", subject="proc:evil", detail={"suspicion": 0.97})

    assert ok is True
    [row] = _rows(out)
    assert row["schema"] == gw.SCHEMA
    assert row["gate"] == "kernel_antivirus"
    assert row["event"] == "deny"
    assert row["subject"] == "proc:evil"
    assert row["detail"]["suspicion"] == 0.97
    assert "ts" in row


def test_witness_appends_not_truncates(tmp_path, monkeypatch):
    out = tmp_path / "witness.jsonl"
    monkeypatch.setenv("SCBE_GATE_WITNESS_PATH", str(out))
    gw.gate_witness("g", "deny")
    gw.gate_witness("g", "quarantine")
    assert [r["event"] for r in _rows(out)] == ["deny", "quarantine"]


def test_witness_never_raises_on_unwritable_path(monkeypatch):
    # A path that cannot exist as a file (its parent is an existing FILE).
    monkeypatch.setenv("SCBE_GATE_WITNESS_PATH", __file__ + "/nope/witness.jsonl")
    assert gw.gate_witness("g", "deny") is False  # no exception escapes


def test_witness_disable_env(tmp_path, monkeypatch):
    out = tmp_path / "witness.jsonl"
    monkeypatch.setenv("SCBE_GATE_WITNESS_PATH", str(out))
    monkeypatch.setenv("SCBE_GATE_WITNESS_DISABLE", "1")
    assert gw.gate_witness("g", "deny") is False
    assert not out.exists()


def test_hash_subject_is_short_stable_and_not_reversible_material():
    key = "scbe_live_super_secret_key_value"
    h = gw.hash_subject(key)
    assert h == gw.hash_subject(key)
    assert len(h) == 16
    assert key not in h


def test_non_json_safe_detail_does_not_break_witness(tmp_path, monkeypatch):
    out = tmp_path / "witness.jsonl"
    monkeypatch.setenv("SCBE_GATE_WITNESS_PATH", str(out))

    class Weird:
        def __str__(self):
            return "weird-object"

    ok = gw.gate_witness("g", "deny", detail={"obj": Weird()})
    assert ok is True
    [row] = _rows(out)
    assert row["detail"]["obj"] == "weird-object"
