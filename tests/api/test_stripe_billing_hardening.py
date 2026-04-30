from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api import stripe_billing


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(stripe_billing.billing_router)
    return TestClient(app)


def test_purchases_requires_owner_token(monkeypatch):
    monkeypatch.setenv("SCBE_OWNER_API_TOKEN", "owner-secret")
    client = _client()
    response = client.get("/billing/purchases")
    assert response.status_code == 401


def test_purchases_allows_with_owner_token(monkeypatch):
    monkeypatch.setenv("SCBE_OWNER_API_TOKEN", "owner-secret")
    client = _client()
    response = client.get("/billing/purchases", headers={"x-owner-token": "owner-secret"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_webhook_requires_secret_or_explicit_unsigned_override(monkeypatch):
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("SCBE_ALLOW_UNSIGNED_STRIPE_WEBHOOK", raising=False)
    client = _client()
    response = client.post("/billing/webhook", json={"type": "noop", "data": {"object": {}}})
    assert response.status_code == 503


def test_onetime_purchase_without_product_metadata_is_marked_unresolved(monkeypatch):
    monkeypatch.setattr(stripe_billing, "_send_delivery_email", lambda *args, **kwargs: True)
    monkeypatch.setattr(stripe_billing, "_notify_owner", lambda *args, **kwargs: None)
    stripe_billing.PURCHASE_LOG.clear()
    session = {
        "id": "cs_test_unresolved",
        "customer_email": "buyer@example.com",
        "amount_total": 2900,
        "payment_status": "paid",
        "metadata": {},
    }
    stripe_billing._handle_onetime_purchase(session)
    assert stripe_billing.PURCHASE_LOG
    latest = stripe_billing.PURCHASE_LOG[-1]
    assert latest["product"] == "unknown"
    assert latest["unresolved_product"] is True
