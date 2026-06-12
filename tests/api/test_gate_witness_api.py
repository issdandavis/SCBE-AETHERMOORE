"""Liveness tests: API/auth enforcement points write gate_witness rows on deny-side outcomes."""

from __future__ import annotations

import json

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.api import auth_config, llm_routes, stripe_billing
from src.governance.gate_witness import hash_subject


def _rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _witness_path(tmp_path, monkeypatch):
    out = tmp_path / "w.jsonl"
    monkeypatch.setenv("SCBE_GATE_WITNESS_PATH", str(out))
    monkeypatch.delenv("SCBE_GATE_WITNESS_DISABLE", raising=False)
    return out


def _llm_client() -> TestClient:
    app = FastAPI()

    @app.get("/probe")
    async def probe(user: str = Depends(llm_routes.verify_api_key)):
        return {"user": user}

    return TestClient(app)


def _billing_client() -> TestClient:
    app = FastAPI()
    app.include_router(stripe_billing.billing_router)
    return TestClient(app)


def test_verify_api_key_401_writes_auth_reject_with_hashed_subject(tmp_path, monkeypatch):
    out = _witness_path(tmp_path, monkeypatch)
    response = _llm_client().get("/probe", headers={"x-api-key": "bogus_key_for_witness"})
    assert response.status_code == 401
    [row] = _rows(out)
    assert row["gate"] == "api.auth"
    assert row["event"] == "auth_reject"
    assert row["subject"] == hash_subject("bogus_key_for_witness")
    assert row["detail"]["route_family"] == "llm_routes"


def test_unsigned_webhook_bypass_writes_bypass_flag_per_use(tmp_path, monkeypatch):
    out = _witness_path(tmp_path, monkeypatch)
    monkeypatch.setenv("SCBE_ALLOW_UNSIGNED_STRIPE_WEBHOOK", "true")
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    client = _billing_client()
    for _ in range(2):
        response = client.post("/billing/webhook", json={"type": "noop", "data": {"object": {}}})
        assert response.status_code == 200
    rows = [r for r in _rows(out) if r["gate"] == "stripe.webhook"]
    assert [r["event"] for r in rows] == ["bypass_flag", "bypass_flag"]
    assert rows[0]["detail"]["flag"] == "SCBE_ALLOW_UNSIGNED_STRIPE_WEBHOOK"


def test_owner_token_401_writes_auth_reject(tmp_path, monkeypatch):
    out = _witness_path(tmp_path, monkeypatch)
    monkeypatch.setenv("SCBE_OWNER_API_TOKEN", "owner-secret")
    response = _billing_client().get("/billing/purchases")
    assert response.status_code == 401
    [row] = _rows(out)
    assert row["gate"] == "stripe.owner"
    assert row["event"] == "auth_reject"
    assert row["subject"] == hash_subject("<empty>")


def test_demo_keys_activation_writes_bypass_flag(tmp_path, monkeypatch):
    out = _witness_path(tmp_path, monkeypatch)
    monkeypatch.delenv("SCBE_API_KEYS", raising=False)
    monkeypatch.setenv("SCBE_ALLOW_DEMO_KEYS", "1")
    keys = auth_config.load_api_keys()
    assert keys
    [row] = _rows(out)
    assert row["gate"] == "api.auth_config"
    assert row["event"] == "bypass_flag"
    assert row["detail"]["flag"] == "SCBE_ALLOW_DEMO_KEYS"


def test_witness_file_never_contains_raw_secrets(tmp_path, monkeypatch):
    out = _witness_path(tmp_path, monkeypatch)
    raw_key = "raw_api_key_MUST_NOT_APPEAR_IN_WITNESS"
    raw_token = "raw_owner_token_MUST_NOT_APPEAR_IN_WITNESS"
    assert _llm_client().get("/probe", headers={"x-api-key": raw_key}).status_code == 401
    monkeypatch.setenv("SCBE_OWNER_API_TOKEN", "owner-secret")
    assert _billing_client().get("/billing/purchases", headers={"x-owner-token": raw_token}).status_code == 401
    content = out.read_text(encoding="utf-8")
    assert raw_key not in content
    assert raw_token not in content
    assert hash_subject(raw_key) in content
    assert hash_subject(raw_token) in content
