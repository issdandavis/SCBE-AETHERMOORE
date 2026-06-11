"""Regression tests for /api/ops/* authentication (CWE-306 hardening).

The ops endpoints in scripts/aetherbrowser/api_server.py trigger local
subprocesses (email reader, test runner, tor sweep, git status, momentum) and
can disclose operator data. They were previously reachable with no auth; these
tests pin the fail-closed API-key gate so the exposure cannot return.
"""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.aetherbrowser.api_server import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)

_KEY = "secret-test-key"


def test_ops_blocks_request_without_key(monkeypatch):
    monkeypatch.setenv("AETHERBROWSER_OPS_API_KEY", _KEY)
    assert client.get("/api/ops/git-status").status_code == 401


def test_ops_rejects_wrong_key(monkeypatch):
    monkeypatch.setenv("AETHERBROWSER_OPS_API_KEY", _KEY)
    assert client.get("/api/ops/git-status", headers={"X-API-Key": "wrong"}).status_code == 401


def test_check_email_unauthenticated_is_blocked(monkeypatch):
    # Exact regression for the reported vuln: an unauthenticated POST must not
    # reach the email_reader subprocess.
    monkeypatch.setenv("AETHERBROWSER_OPS_API_KEY", _KEY)
    assert client.post("/api/ops/check-email").status_code == 401


def test_ops_fails_closed_when_key_unset(monkeypatch):
    monkeypatch.delenv("AETHERBROWSER_OPS_API_KEY", raising=False)
    assert client.get("/api/ops/git-status", headers={"X-API-Key": "anything"}).status_code == 503


def test_ops_allows_with_valid_key(monkeypatch):
    monkeypatch.setenv("AETHERBROWSER_OPS_API_KEY", _KEY)
    assert client.get("/api/ops/git-status", headers={"X-API-Key": _KEY}).status_code == 200
