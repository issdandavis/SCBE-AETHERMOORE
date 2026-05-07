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


def test_onetime_product_manual_urls_are_live_buyer_routes():
    assert stripe_billing.ONETIME_PRODUCTS["toolkit"]["manual_url"].endswith(
        "/product-manual/ai-governance-toolkit.html"
    )
    assert stripe_billing.ONETIME_PRODUCTS["vault"]["manual_url"].endswith("/product-manual/training-vault.html")
    for product in stripe_billing.ONETIME_PRODUCTS.values():
        assert "/docs/product-manual/" not in product["manual_url"]


def test_onetime_product_download_urls_can_use_buyer_only_overrides(monkeypatch):
    monkeypatch.setenv("SCBE_TOOLKIT_DOWNLOAD_URL", "https://delivery.aethermoore.com/toolkit.zip")
    monkeypatch.setenv("SCBE_TRAINING_VAULT_DOWNLOAD_URL", "https://delivery.aethermoore.com/vault.zip")

    products = stripe_billing.get_onetime_products()

    assert products["toolkit"]["download_url"] == "https://delivery.aethermoore.com/toolkit.zip"
    assert products["vault"]["download_url"] == "https://delivery.aethermoore.com/vault.zip"


def test_onetime_purchase_uses_configured_buyer_delivery_url(monkeypatch):
    sent: list[tuple[str, str, str, str]] = []

    monkeypatch.setenv("SCBE_TOOLKIT_DOWNLOAD_URL", "https://delivery.aethermoore.com/toolkit.zip")
    monkeypatch.setattr(
        stripe_billing,
        "_send_delivery_email",
        lambda to_email, product_name, download_url, manual_url: sent.append(
            (to_email, product_name, download_url, manual_url)
        )
        or True,
    )
    monkeypatch.setattr(stripe_billing, "_notify_owner", lambda *args, **kwargs: None)
    stripe_billing.PURCHASE_LOG.clear()

    session = {
        "id": "cs_test_toolkit_delivery_url",
        "customer_email": "buyer@example.com",
        "amount_total": 2900,
        "payment_status": "paid",
        "metadata": {"scbe_product": "toolkit"},
    }

    stripe_billing._handle_onetime_purchase(session)

    assert sent == [
        (
            "buyer@example.com",
            "SCBE AI Governance Toolkit",
            "https://delivery.aethermoore.com/toolkit.zip",
            "https://aethermoore.com/product-manual/ai-governance-toolkit.html",
        )
    ]
