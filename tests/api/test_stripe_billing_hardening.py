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


def test_onetime_purchase_metadata_triggers_delivery_record(monkeypatch):
    sent = {}

    def fake_send_delivery_email(*args, **kwargs):
        sent["args"] = args
        sent["kwargs"] = kwargs
        return True

    monkeypatch.setattr(stripe_billing, "_send_delivery_email", fake_send_delivery_email)
    monkeypatch.setattr(stripe_billing, "_notify_owner", lambda *args, **kwargs: None)
    stripe_billing.PURCHASE_LOG.clear()

    session = {
        "id": "cs_test_toolkit",
        "customer_email": "buyer@example.com",
        "amount_total": 2900,
        "payment_status": "paid",
        "metadata": {"scbe_product": "toolkit"},
    }

    stripe_billing._handle_onetime_purchase(session)

    latest = stripe_billing.PURCHASE_LOG[-1]
    assert latest["product"] == "toolkit"
    assert latest["unresolved_product"] is False
    assert latest["package_filename"] == "SCBE_AI_Governance_Toolkit_v1.zip"
    assert latest["manual_url"].endswith("/product-manual/ai-governance-toolkit.html")
    assert sent["args"][0] == "buyer@example.com"
    assert sent["args"][4] == "SCBE_AI_Governance_Toolkit_v1.zip"


def test_onetime_purchase_resolves_existing_payment_link_from_env(monkeypatch):
    monkeypatch.setenv("SCBE_PAYMENT_LINK_VAULT", "plink_vault_live")
    monkeypatch.setattr(stripe_billing, "_send_delivery_email", lambda *args, **kwargs: True)
    monkeypatch.setattr(stripe_billing, "_notify_owner", lambda *args, **kwargs: None)
    stripe_billing.PURCHASE_LOG.clear()

    session = {
        "id": "cs_test_vault",
        "customer_details": {"email": "buyer@example.com"},
        "amount_total": 2900,
        "payment_status": "paid",
        "payment_link": "plink_vault_live",
        "metadata": {},
    }

    stripe_billing._handle_onetime_purchase(session)

    latest = stripe_billing.PURCHASE_LOG[-1]
    assert latest["product"] == "vault"
    assert latest["unresolved_product"] is False
    assert latest["package_filename"] == "SCBE_AI_Security_Training_Vault_v1.zip"


def test_webhook_payment_event_records_onetime_delivery(monkeypatch):
    monkeypatch.setenv("SCBE_ALLOW_UNSIGNED_STRIPE_WEBHOOK", "true")
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    monkeypatch.setattr(stripe_billing, "_send_delivery_email", lambda *args, **kwargs: True)
    monkeypatch.setattr(stripe_billing, "_notify_owner", lambda *args, **kwargs: None)
    stripe_billing.PURCHASE_LOG.clear()

    client = _client()
    response = client.post(
        "/billing/webhook",
        json={
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_webhook_toolkit",
                    "mode": "payment",
                    "customer_email": "buyer@example.com",
                    "amount_total": 2900,
                    "payment_status": "paid",
                    "metadata": {"scbe_product": "toolkit"},
                }
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    latest = stripe_billing.PURCHASE_LOG[-1]
    assert latest["session_id"] == "cs_test_webhook_toolkit"
    assert latest["product"] == "toolkit"
    assert latest["unresolved_product"] is False


def test_delivery_plaintext_includes_fast_start_paths():
    body = stripe_billing._delivery_plaintext(
        "SCBE AI Governance Toolkit",
        "https://example.com/download",
        "https://example.com/manual",
        "SCBE_AI_Governance_Toolkit_v1.zip",
    )

    assert "Download: https://example.com/download" in body
    assert "Manual:   https://example.com/manual" in body
    assert "Package:  SCBE_AI_Governance_Toolkit_v1.zip" in body
    assert "Open README.md or BUYER_START_GUIDE.md first." in body


def test_onetime_product_manual_urls_are_live_buyer_routes():
    assert stripe_billing.ONETIME_PRODUCTS["toolkit"]["manual_url"].endswith(
        "/product-manual/ai-governance-toolkit.html"
    )
    assert stripe_billing.ONETIME_PRODUCTS["vault"]["manual_url"].endswith("/product-manual/training-vault.html")
    for product in stripe_billing.ONETIME_PRODUCTS.values():
        assert "/docs/product-manual/" not in product["manual_url"]
