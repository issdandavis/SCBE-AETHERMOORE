"""Tests for the Aether governance seam (offline: real light gate + a fake gate).

No model load, no Hermes engine — exercises the seam's logic: gate→decision
mapping, command scanning, deny-blocks-dispatch, and receipt emission.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from governance_seam import GovernanceSeam, SeamDecision, install  # noqa: E402


@dataclass
class _FakeDecision:
    name: str


class _FakeGateResult:
    def __init__(self, name, signals=None, cost=0.0):
        self.decision = _FakeDecision(name)
        self.signals = signals or []
        self.cost = cost


class _FakeGate:
    """Deterministic gate stub: returns a fixed decision for every action."""

    def __init__(self, name="ALLOW", signals=None, cost=0.0):
        self._name, self._signals, self._cost = name, signals, cost
        self.seen = []

    def evaluate(self, action_text, tool_name=""):
        self.seen.append((tool_name, action_text))
        return _FakeGateResult(self._name, self._signals, self._cost)


@pytest.fixture
def receipts(tmp_path):
    return tmp_path / "receipts.jsonl"


def test_benign_write_is_allowed_and_receipted(receipts):
    seam = GovernanceSeam(gate=_FakeGate("ALLOW"), receipts_path=receipts)
    d = seam.govern("write_file", {"path": "notes.txt", "content": "hello world"})
    assert d.allowed and d.decision == "ALLOW" and not d.tripped
    assert receipts.exists()
    rec = json.loads(receipts.read_text(encoding="utf-8").splitlines()[-1])
    assert rec["tool"] == "write_file" and rec["decision"] == "ALLOW"
    assert rec["audit_id"] and rec["args_sha256"]


def test_gate_deny_blocks(receipts):
    seam = GovernanceSeam(gate=_FakeGate("DENY", signals=["council_UM_redaction=FAIL"]), receipts_path=receipts)
    d = seam.govern("read_file", {"path": "/etc/shadow"})
    assert d.decision == "DENY" and not d.allowed and d.tripped
    assert "UM_redaction" in d.reason


def test_quarantine_proceeds_by_default_but_can_block(receipts):
    seam = GovernanceSeam(gate=_FakeGate("QUARANTINE"), receipts_path=receipts)
    assert seam.govern("write_file", {"path": "x"}).allowed  # default: only DENY blocks
    strict = GovernanceSeam(gate=_FakeGate("QUARANTINE"), receipts_path=receipts, quarantine_blocks=True)
    sd = strict.govern("write_file", {"path": "x"})
    assert sd.tripped and not sd.allowed


def test_install_blocks_dispatch_on_deny(receipts):
    seam = GovernanceSeam(gate=_FakeGate("DENY"), receipts_path=receipts)
    calls = []
    wrapped = install(lambda name, args, *r, **k: calls.append((name, args)) or {"ok": True}, seam)
    out = wrapped("execute_code", {"code": "print(1)"})
    assert calls == []  # underlying dispatch NOT called
    assert "error" in out and "BLOCKED by governance" in out["error"]


def test_install_passes_dispatch_on_allow(receipts):
    seam = GovernanceSeam(gate=_FakeGate("ALLOW"), receipts_path=receipts)
    calls = []
    wrapped = install(lambda name, args, *r, **k: calls.append((name, args)) or {"ok": True}, seam)
    out = wrapped("write_file", {"path": "a", "content": "b"})
    assert calls == [("write_file", {"path": "a", "content": "b"})]
    assert out == {"ok": True}


def test_destructive_command_is_caught_by_real_gate_and_scanner(receipts):
    """With the REAL light gate + GeoSeal scanner, a destructive shell command
    must not come back ALLOW."""
    seam = GovernanceSeam(receipts_path=receipts)  # real RuntimeGate(stats)
    d = seam.govern("execute_code", {"code": "rm -rf / --no-preserve-root"})
    assert d.tripped, f"destructive command should trip the seam, got {d.decision}"


def test_receipt_emitted_per_call(receipts):
    seam = GovernanceSeam(gate=_FakeGate("ALLOW"), receipts_path=receipts)
    for i in range(3):
        seam.govern("read_file", {"path": f"f{i}.txt"})
    lines = receipts.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
