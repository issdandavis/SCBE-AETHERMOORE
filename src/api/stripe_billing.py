"""Stripe billing integration for SCBE SaaS API.

Provides:
- Checkout session creation for 3 plan tiers
- Webhook handler for subscription lifecycle events
- API key provisioning on payment
- Usage-based overage reporting to Stripe

Env vars required:
- STRIPE_SECRET_KEY: Stripe API key (rk_live_* or sk_test_*)
- STRIPE_WEBHOOK_SECRET: Webhook signing secret (whsec_*)
- SCBE_BILLING_BASE_URL: Public URL for success/cancel redirects
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

billing_router = APIRouter(prefix="/billing", tags=["Billing"])

# ---------------------------------------------------------------------------
# Plan definitions
# ---------------------------------------------------------------------------

PLANS: Dict[str, Dict[str, Any]] = {
    "starter": {
        "name": "Starter",
        "stripe_price_id": "price_1TBnUmJTF2SuUODIbz41CUFZ",
        "stripe_product_id": "prod_UA7k4QNcyyt2Ta",
        "price_monthly_cents": 4900,
        "description": "1 flock, 8 agents, 5K governance checks/mo",
        "limits": {"flocks": 1, "agents": 8, "monthly_governance": 5000},
        "overage_cents_per_check": 1,  # $0.01 per extra governance check
    },
    "growth": {
        "name": "Growth",
        "stripe_price_id": "price_1TBnUmJTF2SuUODIevRegHf0",
        "stripe_product_id": "prod_UA7kQq6zDwMa8W",
        "price_monthly_cents": 14900,
        "description": "5 flocks, 40 agents, 25K governance checks/mo",
        "limits": {"flocks": 5, "agents": 40, "monthly_governance": 25000},
        "overage_cents_per_check": 0.5,
    },
    "enterprise": {
        "name": "Enterprise",
        "stripe_price_id": "price_1TBnUnJTF2SuUODIZwBEak7Q",
        "stripe_product_id": "prod_UA7kPel50bZDqr",
        "price_monthly_cents": 49900,
        "description": "25 flocks, 250 agents, 100K governance checks/mo",
        "limits": {"flocks": 25, "agents": 250, "monthly_governance": 100000},
        "overage_cents_per_check": 0.25,
    },
}

# In-memory mapping: stripe_customer_id -> tenant record
# In production this would be a database table.
BILLING_CUSTOMERS: Dict[str, Dict[str, Any]] = {}

# API keys issued via billing (api_key -> {customer_id, plan, tenant_id, ...})
BILLING_API_KEYS: Dict[str, Dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Stripe HTTP helpers (no SDK dependency — just urllib)
# ---------------------------------------------------------------------------

def _stripe_key() -> str:
    key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not key:
        raise HTTPException(503, "Stripe not configured")
    return key


def _stripe_request(
    method: str,
    path: str,
    *,
    form_data: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Make a Stripe API request using form-encoded data (no SDK needed)."""
    url = f"https://api.stripe.com/v1/{path.lstrip('/')}"
    key = _stripe_key()

    encoded_data = None
    if form_data:
        encoded_data = "&".join(
            f"{urllib.request.quote(k)}={urllib.request.quote(str(v))}"
            for k, v in form_data.items()
            if v is not None
        ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=encoded_data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            err = json.loads(body)
        except json.JSONDecodeError:
            err = {"raw": body}
        raise HTTPException(exc.code, detail=err.get("error", {}).get("message", body))


def _generate_api_key() -> str:
    """Generate a secure random API key."""
    return f"scbe_live_{secrets.token_urlsafe(32)}"


def _verify_stripe_signature(payload: bytes, sig_header: str) -> bool:
    """Verify Stripe webhook signature."""
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    if not secret:
        return False

    # Parse signature header
    parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
    timestamp = parts.get("t", "")
    v1_sig = parts.get("v1", "")
    if not timestamp or not v1_sig:
        return False

    # Check timestamp (reject if > 5 min old)
    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False
    except ValueError:
        return False

    # Compute expected signature
    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    expected = hmac.new(
        secret.encode("utf-8"), signed_payload, hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, v1_sig)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CheckoutRequest(BaseModel):
    plan: str = Field(..., pattern="^(starter|growth|enterprise)$")
    email: Optional[str] = Field(default=None, max_length=254)
    success_url: Optional[str] = Field(default=None, max_length=2048)
    cancel_url: Optional[str] = Field(default=None, max_length=2048)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@billing_router.get("/plans")
async def list_plans():
    """List available subscription plans and pricing."""
    return {
        "status": "ok",
        "data": {
            plan_id: {
                "name": plan["name"],
                "price_monthly_usd": plan["price_monthly_cents"] / 100,
                "description": plan["description"],
                "limits": plan["limits"],
                "overage_per_check_usd": plan["overage_cents_per_check"] / 100,
            }
            for plan_id, plan in PLANS.items()
        },
    }


@billing_router.post("/checkout")
async def create_checkout(request: CheckoutRequest):
    """Create a Stripe Checkout session for a subscription.

    Returns a checkout URL — redirect the customer there.
    No custom payment UI needed.
    """
    plan = PLANS.get(request.plan)
    if not plan:
        raise HTTPException(400, f"Unknown plan: {request.plan}")

    base_url = os.getenv("SCBE_BILLING_BASE_URL", "http://localhost:8000").rstrip("/")
    success_url = request.success_url or f"{base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = request.cancel_url or f"{base_url}/billing/cancel"

    form_data: Dict[str, str] = {
        "mode": "subscription",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "line_items[0][price]": plan["stripe_price_id"],
        "line_items[0][quantity]": "1",
        "metadata[scbe_plan]": request.plan,
    }
    if request.email:
        form_data["customer_email"] = request.email

    session = _stripe_request("POST", "checkout/sessions", form_data=form_data)

    return {
        "status": "ok",
        "checkout_url": session.get("url"),
        "session_id": session.get("id"),
    }


@billing_router.get("/success")
async def checkout_success(session_id: str = ""):
    """Landing page after successful checkout. Returns API key if ready."""
    if not session_id:
        return {"status": "ok", "message": "Payment successful. Your API key will be emailed."}

    # Look up if we've already provisioned
    for api_key, record in BILLING_API_KEYS.items():
        if record.get("checkout_session_id") == session_id:
            return {
                "status": "ok",
                "message": "Subscription active",
                "api_key": api_key,
                "plan": record["plan"],
            }

    return {"status": "pending", "message": "Payment processing. API key will be available shortly."}


@billing_router.get("/cancel")
async def checkout_cancel():
    """Landing page after canceled checkout."""
    return {"status": "canceled", "message": "Checkout was canceled. No charge was made."}


@billing_router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events.

    Events handled:
    - checkout.session.completed: Provision API key
    - customer.subscription.updated: Update plan limits
    - customer.subscription.deleted: Revoke API key
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # Verify signature (skip in dev if no secret configured)
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    if webhook_secret and not _verify_stripe_signature(payload, sig_header):
        raise HTTPException(400, "Invalid signature")

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(data)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data)

    return {"status": "ok"}


def _handle_checkout_completed(session: Dict[str, Any]) -> None:
    """Provision a new API key when checkout completes."""
    customer_id = session.get("customer", "")
    plan_id = session.get("metadata", {}).get("scbe_plan", "starter")
    subscription_id = session.get("subscription", "")
    email = session.get("customer_email") or session.get("customer_details", {}).get("email", "")

    api_key = _generate_api_key()
    now = int(time.time())

    record = {
        "customer_id": customer_id,
        "subscription_id": subscription_id,
        "plan": plan_id,
        "email": email,
        "api_key": api_key,
        "checkout_session_id": session.get("id", ""),
        "created_at": now,
        "active": True,
    }

    BILLING_CUSTOMERS[customer_id] = record
    BILLING_API_KEYS[api_key] = record

    # Also register in the SaaS API key store so endpoints accept it
    from src.api.saas_routes import VALID_API_KEYS
    VALID_API_KEYS[api_key] = email or customer_id


def _handle_subscription_updated(subscription: Dict[str, Any]) -> None:
    """Update plan when subscription changes."""
    customer_id = subscription.get("customer", "")
    record = BILLING_CUSTOMERS.get(customer_id)
    if not record:
        return

    # Check for plan change via metadata or items
    items = subscription.get("items", {}).get("data", [])
    new_plan = subscription.get("metadata", {}).get("scbe_plan")
    if new_plan and new_plan in PLANS:
        record["plan"] = new_plan

    record["active"] = subscription.get("status") == "active"


def _handle_subscription_deleted(subscription: Dict[str, Any]) -> None:
    """Revoke API key when subscription is canceled."""
    customer_id = subscription.get("customer", "")
    record = BILLING_CUSTOMERS.get(customer_id)
    if not record:
        return

    record["active"] = False
    api_key = record.get("api_key", "")

    # Remove from valid API keys
    from src.api.saas_routes import VALID_API_KEYS
    VALID_API_KEYS.pop(api_key, None)


@billing_router.get("/status/{api_key}")
async def billing_status(api_key: str):
    """Check billing status for an API key."""
    record = BILLING_API_KEYS.get(api_key)
    if not record:
        raise HTTPException(404, "API key not found")

    plan = PLANS.get(record["plan"], {})
    return {
        "status": "ok",
        "data": {
            "plan": record["plan"],
            "plan_name": plan.get("name", "Unknown"),
            "active": record.get("active", False),
            "limits": plan.get("limits", {}),
            "created_at": record.get("created_at"),
        },
    }
