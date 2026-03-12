"""
Billing API routes.

Endpoints for subscription management, checkout, and usage.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel

from .database import get_db, Customer, Subscription, UsageRecord, BillingEvent, AccessPass
from .stripe_client import StripeClient
from .tiers import PRICING_TIERS, get_price_id_for_tier, ACCESS_PASS_PRICE_CENTS
from .webhooks import process_webhook_event
from ..auth import verify_api_key, CustomerContext

router = APIRouter(prefix="/v1/billing", tags=["Billing"])


# Request/Response models
class CheckoutRequest(BaseModel):
    tier: str
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class PublicCheckoutRequest(BaseModel):
    email: str
    tier: str
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    source: Optional[str] = "landing"


class CheckoutResponse(BaseModel):
    session_id: str
    checkout_url: str
    tier: str


class PortalResponse(BaseModel):
    portal_url: str


class SubscriptionResponse(BaseModel):
    tier: str
    status: str
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool


class UsageResponse(BaseModel):
    period: str
    total_requests: int
    tier: str
    limit: Optional[int]
    remaining: Optional[int]


class InvoiceItem(BaseModel):
    id: str
    amount_cents: int
    currency: str
    status: str
    created: datetime
    invoice_url: Optional[str]


# Endpoints
@router.post("/public-checkout", response_model=CheckoutResponse)
async def create_public_checkout_session(request: PublicCheckoutRequest):
    """
    Public checkout endpoint for landing-page conversion.

    This route intentionally avoids API-key auth to support first-time buyers.
    """
    tier = request.tier.upper().strip()
    if tier not in {"STARTER", "PRO"}:
        raise HTTPException(status_code=400, detail="Public checkout supports STARTER or PRO tiers.")
    if "@" not in request.email:
        raise HTTPException(status_code=400, detail="Valid email is required.")

    price_id = get_price_id_for_tier(tier)
    if not price_id:
        raise HTTPException(status_code=503, detail=f"Tier {tier} is not configured for checkout.")

    result = StripeClient.create_checkout_session(
        tier=tier,
        price_id=price_id,
        customer_email=request.email.strip(),
        success_url=request.success_url,
        cancel_url=request.cancel_url,
        metadata={"source": (request.source or "landing").strip()[:64]},
    )
    return CheckoutResponse(**result)


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CheckoutRequest,
    customer: CustomerContext = Depends(verify_api_key),
):
    """
    Create a Stripe Checkout session for subscription signup/upgrade.
    """
    if request.tier not in PRICING_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {request.tier}")

    price_id = get_price_id_for_tier(request.tier)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Tier {request.tier} has no price configured")

    # Get Stripe customer ID if exists
    with get_db() as db:
        db_customer = db.query(Customer).get(customer.customer_id)
        stripe_customer_id = db_customer.stripe_customer_id if db_customer else None

    result = StripeClient.create_checkout_session(
        tier=request.tier,
        price_id=price_id,
        customer_id=stripe_customer_id,
        customer_email=customer.customer_email if not stripe_customer_id else None,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
    )

    return CheckoutResponse(**result)


@router.post("/portal", response_model=PortalResponse)
async def create_portal_session(
    customer: CustomerContext = Depends(verify_api_key),
):
    """
    Create a Stripe Customer Portal session for self-service management.
    """
    with get_db() as db:
        db_customer = db.query(Customer).get(customer.customer_id)

        if not db_customer or not db_customer.stripe_customer_id:
            raise HTTPException(
                status_code=400,
                detail="No billing account found. Please complete checkout first.",
            )

        result = StripeClient.create_portal_session(db_customer.stripe_customer_id)

    return PortalResponse(**result)


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    customer: CustomerContext = Depends(verify_api_key),
):
    """
    Get current subscription status.
    """
    with get_db() as db:
        subscription = (
            db.query(Subscription)
            .filter(Subscription.customer_id == customer.customer_id)
            .order_by(Subscription.created_at.desc())
            .first()
        )

        if not subscription:
            return SubscriptionResponse(
                tier="FREE",
                status="active",
                current_period_end=None,
                cancel_at_period_end=False,
            )

        return SubscriptionResponse(
            tier=subscription.tier,
            status=subscription.status,
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
        )


@router.post("/subscription/cancel")
async def cancel_subscription(
    customer: CustomerContext = Depends(verify_api_key),
):
    """
    Cancel subscription at period end.
    """
    with get_db() as db:
        subscription = (
            db.query(Subscription)
            .filter(
                Subscription.customer_id == customer.customer_id,
                Subscription.status == "active",
            )
            .first()
        )

        if not subscription or not subscription.stripe_subscription_id:
            raise HTTPException(status_code=400, detail="No active subscription found")

        result = StripeClient.cancel_subscription(subscription.stripe_subscription_id)
        subscription.cancel_at_period_end = True

    return {"status": "cancellation_scheduled", "cancel_at_period_end": True}


@router.post("/subscription/reactivate")
async def reactivate_subscription(
    customer: CustomerContext = Depends(verify_api_key),
):
    """
    Reactivate a subscription that was set to cancel.
    """
    with get_db() as db:
        subscription = (
            db.query(Subscription)
            .filter(
                Subscription.customer_id == customer.customer_id,
                Subscription.cancel_at_period_end == True,
            )
            .first()
        )

        if not subscription or not subscription.stripe_subscription_id:
            raise HTTPException(status_code=400, detail="No subscription to reactivate")

        result = StripeClient.reactivate_subscription(subscription.stripe_subscription_id)
        subscription.cancel_at_period_end = False

    return {"status": "reactivated", "cancel_at_period_end": False}


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    customer: CustomerContext = Depends(verify_api_key),
):
    """
    Get current usage statistics.
    """
    now = datetime.utcnow()
    billing_period = now.strftime("%Y-%m")

    with get_db() as db:
        total_requests = (
            db.query(UsageRecord)
            .filter(
                UsageRecord.customer_id == customer.customer_id,
                UsageRecord.billing_period == billing_period,
            )
            .count()
        )

    tier_config = PRICING_TIERS.get(customer.tier, PRICING_TIERS["FREE"])
    monthly_limit = tier_config["rate_limits"].get("monthly")

    return UsageResponse(
        period=billing_period,
        total_requests=total_requests,
        tier=customer.tier,
        limit=monthly_limit,
        remaining=monthly_limit - total_requests if monthly_limit else None,
    )


@router.get("/invoices")
async def list_invoices(
    limit: int = 10,
    customer: CustomerContext = Depends(verify_api_key),
):
    """
    List invoice history.
    """
    with get_db() as db:
        db_customer = db.query(Customer).get(customer.customer_id)

        if not db_customer or not db_customer.stripe_customer_id:
            return {"invoices": []}

        invoices = StripeClient.list_invoices(db_customer.stripe_customer_id, limit=limit)

    return {"invoices": invoices}


# --- Access Pass (one-time $2 payment to unlock API access) ---

class AccessPassCheckoutRequest(BaseModel):
    email: str
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    source: Optional[str] = "landing"


class AccessPassCheckoutResponse(BaseModel):
    session_id: str
    checkout_url: str
    amount_cents: int


class AccessPassStatusResponse(BaseModel):
    has_access: bool
    tier: str
    paid_at: Optional[datetime] = None


@router.post("/access-pass/checkout", response_model=AccessPassCheckoutResponse)
async def create_access_pass_checkout(request: AccessPassCheckoutRequest):
    """
    Create a one-time $2 payment checkout to unlock API access.

    No auth required — this is the entry point for new users.
    """
    email = (request.email or "").strip()
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required.")

    result = StripeClient.create_payment_checkout(
        price_cents=ACCESS_PASS_PRICE_CENTS,
        product_name="SCBE-AETHERMOORE Access Pass",
        customer_email=email,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
        metadata={
            "type": "access_pass",
            "source": (request.source or "landing").strip()[:64],
        },
    )

    return AccessPassCheckoutResponse(
        session_id=result["session_id"],
        checkout_url=result["checkout_url"],
        amount_cents=ACCESS_PASS_PRICE_CENTS,
    )


@router.get("/access-pass/status", response_model=AccessPassStatusResponse)
async def check_access_pass(
    customer: CustomerContext = Depends(verify_api_key),
):
    """Check if the caller has a paid access pass or active subscription."""
    with get_db() as db:
        # Check for an active subscription first (subscriptions outrank access passes)
        subscription = (
            db.query(Subscription)
            .filter(
                Subscription.customer_id == customer.customer_id,
                Subscription.status == "active",
            )
            .first()
        )
        if subscription:
            return AccessPassStatusResponse(
                has_access=True, tier=subscription.tier
            )

        # Check for a paid access pass
        access_pass = (
            db.query(AccessPass)
            .filter(
                AccessPass.customer_id == customer.customer_id,
                AccessPass.status == "paid",
            )
            .first()
        )
        if access_pass:
            return AccessPassStatusResponse(
                has_access=True,
                tier="ACCESS_PASS",
                paid_at=access_pass.paid_at,
            )

    return AccessPassStatusResponse(has_access=False, tier="FREE")


# Stripe Webhook endpoint (no auth - uses Stripe signature verification)
@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
):
    """
    Receive Stripe webhook events.
    """
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    payload = await request.body()

    try:
        event = StripeClient.construct_webhook_event(payload, stripe_signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {str(e)}")

    result = await process_webhook_event(event)

    return {"received": True, **result}
