from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api import auth_config
from src.api import stripe_billing
from src.api.billing_store import reset_loaded_flag_for_tests


def _scrub_scbe_live_keys() -> None:
    for key in list(auth_config.VALID_API_KEYS.keys()):
        if key.startswith("scbe_live_"):
            auth_config.VALID_API_KEYS.pop(key, None)


@pytest.fixture(autouse=True)
def _billing_sqlite_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("SCBE_BILLING_DB_PATH", str(tmp_path / "billing.sqlite3"))
    reset_loaded_flag_for_tests()
    stripe_billing.BILLING_CUSTOMERS.clear()
    stripe_billing.BILLING_API_KEYS.clear()
    stripe_billing.PURCHASE_LOG.clear()
    _scrub_scbe_live_keys()


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


def test_checkout_completed_persists_to_sqlite_and_reloads():
    session = {
        "id": "cs_test_provision_1",
        "customer": "cus_test_1",
        "metadata": {"scbe_plan": "starter"},
        "subscription": "sub_test_1",
        "customer_email": "sub@example.com",
        "mode": "subscription",
    }
    stripe_billing._handle_checkout_completed(session)
    assert stripe_billing.BILLING_API_KEYS

    stripe_billing.BILLING_CUSTOMERS.clear()
    stripe_billing.BILLING_API_KEYS.clear()
    _scrub_scbe_live_keys()
    reset_loaded_flag_for_tests()

    stripe_billing._ensure_billing_loaded()
    assert any(r.get("checkout_session_id") == "cs_test_provision_1" for r in stripe_billing.BILLING_API_KEYS.values())


def test_webhook_dedupes_duplicate_event_ids(monkeypatch):
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    monkeypatch.setenv("SCBE_ALLOW_UNSIGNED_STRIPE_WEBHOOK", "1")
    client = _client()
    body = {"id": "evt_dup_test_1", "type": "ping", "data": {"object": {}}}
    first = client.post("/billing/webhook", json=body)
    second = client.post("/billing/webhook", json=body)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json().get("deduped") is True
