from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.billing import routes


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


def test_public_checkout_creates_session(monkeypatch):
    captured = {}

    def fake_create_checkout_session(
        tier,
        price_id,
        customer_email=None,
        customer_id=None,
        success_url=None,
        cancel_url=None,
        metadata=None,
    ):
        captured["tier"] = tier
        captured["price_id"] = price_id
        captured["customer_email"] = customer_email
        captured["success_url"] = success_url
        captured["cancel_url"] = cancel_url
        captured["metadata"] = metadata
        return {
            "session_id": "cs_test_123",
            "checkout_url": "https://checkout.stripe.test/session/cs_test_123",
            "tier": tier,
        }

    monkeypatch.setattr(routes.StripeClient, "create_checkout_session", staticmethod(fake_create_checkout_session))
    client = _client()

    response = client.post(
        "/v1/billing/public-checkout",
        json={
            "email": "buyer@example.com",
            "tier": "pro",
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
            "source": "landing-page",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "cs_test_123"
    assert body["tier"] == "PRO"
    assert captured["tier"] == "PRO"
    assert captured["customer_email"] == "buyer@example.com"
    assert captured["metadata"]["source"] == "landing-page"


def test_public_checkout_rejects_invalid_tier():
    client = _client()
    response = client.post(
        "/v1/billing/public-checkout",
        json={"email": "buyer@example.com", "tier": "enterprise"},
    )
    assert response.status_code == 400


def test_public_checkout_requires_email():
    client = _client()
    response = client.post(
        "/v1/billing/public-checkout",
        json={"email": "invalid-email", "tier": "STARTER"},
    )
    assert response.status_code == 400
