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
import logging
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request
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

LOGGER = logging.getLogger("scbe.billing")

_KEYS_FILE = Path(__file__).resolve().parents[2] / "artifacts" / "revenue" / "api_keys.jsonl"


def _billing_cipher():
    """Fernet cipher for encrypting API keys at rest, or None if unconfigured.

    Without SCBE_BILLING_ENC_KEY the store runs IN-MEMORY ONLY and never writes a
    secret to disk in clear text. Generate a key with:
      python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    """
    raw = os.getenv("SCBE_BILLING_ENC_KEY", "").strip()
    if not raw:
        return None
    try:
        from cryptography.fernet import Fernet

        return Fernet(raw.encode("utf-8"))
    except Exception as exc:
        LOGGER.warning("SCBE_BILLING_ENC_KEY invalid; billing keys will not persist: %s", exc)
        return None


def _load_keys() -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Load persisted billing records from disk on startup."""
    customers: Dict[str, Any] = {}
    keys: Dict[str, Any] = {}
    if not _KEYS_FILE.exists():
        return customers, keys
    cipher = _billing_cipher()
    try:
        with open(_KEYS_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                enc = record.pop("api_key_enc", None)
                if enc and cipher is not None:
                    try:
                        record["api_key"] = cipher.decrypt(enc.encode("ascii")).decode("utf-8")
                    except Exception:
                        continue  # cannot decrypt (wrong/rotated key) — skip record
                cid = record.get("customer_id", "")
                key = record.get("api_key", "")
                if cid:
                    customers[cid] = record
                if key:
                    keys[key] = record
    except Exception as exc:
        LOGGER.warning("Failed to load billing keys from disk: %s", exc)
    return customers, keys


def _persist_key(record: Dict[str, Any]) -> None:
    """Append an API key record to disk with the API key ENCRYPTED at rest.

    If no encryption key is configured the record is NOT written (in-memory only),
    so a raw key is never stored in clear text.
    """
    cipher = _billing_cipher()
    if cipher is None:
        return
    _KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    raw_api_key = str(record.get("api_key") or "")
    if not raw_api_key:
        return
    stored_record = {
        "customer_id": record.get("customer_id", ""),
        "subscription_id": record.get("subscription_id", ""),
        "plan": record.get("plan", ""),
        "email": record.get("email", ""),
        "created_at": record.get("created_at", int(time.time())),
        "api_key_enc": cipher.encrypt(raw_api_key.encode("utf-8")).decode("ascii"),
    }
    try:
        with open(_KEYS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(stored_record, sort_keys=True) + "\n")
    except Exception as exc:
        LOGGER.warning("Failed to persist API key record: %s", exc)


# Load persisted state on import
BILLING_CUSTOMERS, BILLING_API_KEYS = _load_keys()


def _owner_token() -> str:
    token = os.getenv("SCBE_OWNER_API_TOKEN", "").strip()
    if not token:
        raise HTTPException(503, "Owner API token is not configured")
    return token


def _require_owner_token(x_owner_token: str | None) -> None:
    expected = _owner_token()
    provided = (x_owner_token or "").strip()
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(401, "Unauthorized")


# ---------------------------------------------------------------------------
# Stripe HTTP helpers (no SDK dependency - just urllib)
# ---------------------------------------------------------------------------


def _safe_for_log(value: object) -> str:
    """Collapse control characters before emitting user-controlled values to logs."""
    return str(value).replace("\r", "\\r").replace("\n", "\\n")


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
        encoded_data = urllib.parse.urlencode({k: str(v) for k, v in form_data.items() if v is not None}).encode(
            "utf-8"
        )

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
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()

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
        return {
            "status": "ok",
            "message": "Payment successful. Your API key will be emailed.",
        }

    # Look up if we've already provisioned
    for api_key, record in BILLING_API_KEYS.items():
        if record.get("checkout_session_id") == session_id:
            return {
                "status": "ok",
                "message": "Subscription active",
                "api_key": api_key,
                "plan": record["plan"],
            }

    return {
        "status": "pending",
        "message": "Payment processing. API key will be available shortly.",
    }


@billing_router.get("/cancel")
async def checkout_cancel():
    """Landing page after canceled checkout."""
    return {
        "status": "canceled",
        "message": "Checkout was canceled. No charge was made.",
    }


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

    # Verify signature. Unsigned webhooks are only allowed when explicitly enabled.
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    allow_unsigned = os.getenv("SCBE_ALLOW_UNSIGNED_STRIPE_WEBHOOK", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if not webhook_secret and not allow_unsigned:
        raise HTTPException(503, "Webhook secret is not configured")
    if webhook_secret and not _verify_stripe_signature(payload, sig_header):
        raise HTTPException(400, "Invalid signature")

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        mode = data.get("mode", "")
        if mode == "payment":
            _handle_onetime_purchase(data)
        else:
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
    _persist_key(record)

    # Also register in the SaaS API key store so endpoints accept it
    try:
        from src.api.saas_routes import VALID_API_KEYS

        VALID_API_KEYS[api_key] = email or customer_id
    except ImportError:
        pass


def _handle_subscription_updated(subscription: Dict[str, Any]) -> None:
    """Update plan when subscription changes."""
    customer_id = subscription.get("customer", "")
    record = BILLING_CUSTOMERS.get(customer_id)
    if not record:
        return

    # Check for plan change via metadata
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


# ---------------------------------------------------------------------------
# One-time product purchases (Payment Links)
# ---------------------------------------------------------------------------

DEFAULT_PRODUCT_RELEASE_URL = "https://github.com/issdandavis/SCBE-AETHERMOORE/releases/latest"


def _delivery_url(*env_names: str) -> str:
    """Resolve a buyer delivery URL, with public release fallback for dev/smoke use."""
    for env_name in env_names:
        value = os.getenv(env_name, "").strip()
        if value:
            return value
    return DEFAULT_PRODUCT_RELEASE_URL


def get_onetime_products() -> Dict[str, Dict[str, str]]:
    """Map one-time product keys to delivery info.

    Payment Links should set metadata[scbe_product] to one of these keys.
    Production should set buyer-only product URLs so paid packets do not depend
    on the public open-source release surface.
    """
    return {
        # AI Governance Toolkit - $29
        "toolkit": {
            "name": "SCBE AI Governance Toolkit",
            "download_url": _delivery_url("SCBE_TOOLKIT_DOWNLOAD_URL"),
            "manual_url": "https://aethermoore.com/product-manual/ai-governance-toolkit.html",
            "package_filename": "SCBE_AI_Governance_Toolkit_v1.zip",
            "support_url": "https://aethermoore.com/support.html",
        },
        # AI Security Training Vault - $29
        "vault": {
            "name": "SCBE AI Security Training Vault",
            "download_url": _delivery_url("SCBE_TRAINING_VAULT_DOWNLOAD_URL", "SCBE_VAULT_DOWNLOAD_URL"),
            "manual_url": "https://aethermoore.com/product-manual/training-vault.html",
            "package_filename": "SCBE_AI_Security_Training_Vault_v1.zip",
            "support_url": "https://aethermoore.com/support.html",
        },
    }


# Backwards-compatible default snapshot for tests and diagnostics.
ONETIME_PRODUCTS: Dict[str, Dict[str, str]] = get_onetime_products()

# Purchase log for tracking (in production, use a database)
PURCHASE_LOG: list = []


def _payment_link_product_map() -> Dict[str, str]:
    """Return optional Stripe Payment Link ID -> product key mapping from env."""
    mapping: Dict[str, str] = {}
    for product_key in ONETIME_PRODUCTS:
        env_name = f"SCBE_PAYMENT_LINK_{product_key.upper()}"
        payment_link_id = os.getenv(env_name, "").strip()
        if payment_link_id:
            mapping[payment_link_id] = product_key
    return mapping


def _normalize_product_key(value: object) -> str:
    """Normalize product selector text into a known one-time product key."""
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "ai_governance_toolkit": "toolkit",
        "governance_toolkit": "toolkit",
        "scbe_ai_governance_toolkit": "toolkit",
        "ai_security_training_vault": "vault",
        "training_vault": "vault",
        "security_training_vault": "vault",
        "scbe_ai_security_training_vault": "vault",
    }
    return aliases.get(normalized, normalized)


def _resolve_onetime_product_key(session: Dict[str, Any]) -> str:
    """Resolve a one-time product from signed Stripe session data.

    Metadata is the preferred path because it is explicit and deterministic.
    Payment Link ID mapping is an operational fallback for existing links.
    """
    metadata = session.get("metadata", {}) or {}
    for metadata_key in ("scbe_product", "product", "product_key", "offer"):
        product_key = _normalize_product_key(metadata.get(metadata_key, ""))
        if product_key in ONETIME_PRODUCTS:
            return product_key

    client_reference_id = _normalize_product_key(session.get("client_reference_id", ""))
    if client_reference_id in ONETIME_PRODUCTS:
        return client_reference_id

    payment_link = str(session.get("payment_link", "") or "").strip()
    if payment_link:
        mapped_key = _payment_link_product_map().get(payment_link, "")
        if mapped_key in ONETIME_PRODUCTS:
            return mapped_key

    return ""


def _delivery_plaintext(product_name: str, download_url: str, manual_url: str, package_filename: str) -> str:
    return "\n".join(
        [
            f"Thank you for your purchase. Your {product_name} is ready.",
            "",
            f"Download: {download_url}",
            f"Manual:   {manual_url}",
            f"Package:  {package_filename}",
            "",
            "First steps:",
            "1. Download the package.",
            "2. Open README.md or BUYER_START_GUIDE.md first.",
            "3. Use the manual if you need the web instructions.",
            "",
            "Support: ai@aethermoore.com or https://aethermoore.com/support.html",
        ]
    )


def _send_delivery_email(
    to_email: str,
    product_name: str,
    download_url: str,
    manual_url: str,
    package_filename: str = "",
    support_url: str = "https://aethermoore.com/support.html",
) -> bool:
    """Send product delivery email via SMTP.

    Uses Porkbun email (ai@aethermoore.com) configured in .secrets/email_credentials.txt.
    Falls back to logging if SMTP is not configured.
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    smtp_host = os.getenv("SCBE_SMTP_HOST", "smtp.protonmail.ch")
    smtp_port = int(os.getenv("SCBE_SMTP_PORT", "587"))
    smtp_user = os.getenv("SCBE_SMTP_USER") or os.getenv("PM_USER", "")
    smtp_pass = os.getenv("SCBE_SMTP_PASS") or os.getenv("PM_PW", "")

    subject = f"Your {product_name} is ready"
    html_body = f"""<html><body style="font-family: Georgia, serif; color: #333; max-width: 600px;">
<h2 style="color: #d6a756;">Thank you for your purchase!</h2>
<p>Your <strong>{product_name}</strong> is ready for download.</p>
<p>Expected package: <code>{package_filename or 'product ZIP'}</code></p>
<p><a href="{download_url}" style="display:inline-block;padding:12px 24px;background:#d6a756;color:#14110c;
text-decoration:none;border-radius:6px;font-weight:bold;">Download Your Product</a></p>
<p><a href="{manual_url}">Read the Manual</a></p>
<p><a href="{support_url}">Delivery support</a></p>
<hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
<p style="font-size:14px;color:#888;">
If you have any questions, reply to this email or reach us at ai@aethermoore.com.<br>
&mdash; Issac Davis, AetherMoore
</p>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    from_addr = os.getenv("PM_FROM") or smtp_user
    msg["From"] = f"AetherMoore <{from_addr}>"
    msg["To"] = to_email
    msg["Reply-To"] = "ai@aethermoore.com"
    msg.attach(
        MIMEText(
            _delivery_plaintext(product_name, download_url, manual_url, package_filename),
            "plain",
        )
    )
    msg.attach(MIMEText(html_body, "html"))

    if not smtp_pass:
        # No SMTP configured - log instead
        LOGGER.warning(
            "SMTP not configured. Would send delivery to %s for %s. Download: %s",
            _safe_for_log(to_email),
            _safe_for_log(product_name),
            _safe_for_log(download_url),
        )
        return False

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as exc:
        LOGGER.error(
            "Failed to send delivery email to %s: %s",
            _safe_for_log(to_email),
            _safe_for_log(exc),
        )
        return False


def _notify_owner(product_name: str, buyer_email: str, amount_cents: int) -> None:
    """Forward purchase notification to owner via email forwarding."""
    _send_delivery_email(
        to_email="ai@aethermoore.com",  # forwards to issdandavis@gmail.com
        product_name=f"NEW SALE: {product_name}",
        download_url=f"Buyer: {buyer_email} | Amount: ${amount_cents / 100:.2f}",
        manual_url="https://dashboard.stripe.com/payments",
        package_filename="owner-notification",
    )


def _handle_onetime_purchase(session: Dict[str, Any]) -> None:
    """Handle a one-time product purchase from Payment Links."""
    email = session.get("customer_email") or session.get("customer_details", {}).get("email", "")
    amount = session.get("amount_total", 0)
    payment_status = session.get("payment_status", "")

    if payment_status != "paid":
        return

    product_key = _resolve_onetime_product_key(session)

    # Do not guess from amount to avoid mis-delivery between similarly priced products.
    product = get_onetime_products().get(product_key) if product_key else None
    unresolved_product = product is None
    if unresolved_product:
        product = {
            "name": "UNRESOLVED_PRODUCT",
            "download_url": "",
            "manual_url": "",
            "package_filename": "",
            "support_url": "https://aethermoore.com/support.html",
        }

    # Log the purchase
    record = {
        "session_id": session.get("id", ""),
        "email": email,
        "product": product_key or "unknown",
        "product_name": product["name"],
        "unresolved_product": unresolved_product,
        "amount_cents": amount,
        "download_url": product["download_url"],
        "manual_url": product["manual_url"],
        "package_filename": product.get("package_filename", ""),
        "timestamp": int(time.time()),
    }
    PURCHASE_LOG.append(record)

    # Save to disk for persistence
    _persist_purchase(record)

    # Send delivery email to buyer
    if email and not unresolved_product:
        _send_delivery_email(
            email,
            product["name"],
            product["download_url"],
            product["manual_url"],
            product.get("package_filename", ""),
            product.get("support_url", "https://aethermoore.com/support.html"),
        )
        _notify_owner(product["name"], email, amount)
    elif unresolved_product:
        LOGGER.warning(
            "One-time purchase unresolved product mapping; session=%s amount_cents=%s email=%s",
            _safe_for_log(session.get("id", "")),
            _safe_for_log(amount),
            _safe_for_log(email),
        )


def _persist_purchase(record: Dict[str, Any]) -> None:
    """Append purchase record to JSONL file."""
    log_dir = Path(__file__).resolve().parents[2] / "artifacts" / "revenue"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "purchases.jsonl"

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError as exc:
        LOGGER.warning(
            "Failed to persist purchase record to %s: %s",
            _safe_for_log(log_file),
            _safe_for_log(exc),
        )


@billing_router.get("/purchases")
async def list_purchases(x_owner_token: str | None = Header(default=None)):
    """List recent purchases (owner-only)."""
    _require_owner_token(x_owner_token)
    return {"status": "ok", "count": len(PURCHASE_LOG), "purchases": PURCHASE_LOG[-20:]}


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
