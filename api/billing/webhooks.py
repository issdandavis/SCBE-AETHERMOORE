"""
Stripe webhook event handlers.

Handles subscription lifecycle events from Stripe.
"""

import logging
from datetime import datetime
from typing import Callable, Dict

import stripe

from .database import get_db, Customer, Subscription, ApiKey, BillingEvent
from .tiers import get_tier_from_price_id
from ..keys.generator import generate_api_key

logger = logging.getLogger(__name__)


async def handle_checkout_completed(event: stripe.Event) -> dict:
    """
    Handle checkout.session.completed event.

    Creates customer, subscription, and initial API key.
    """
    session = event.data.object
    logger.info(f"Checkout completed: {session.id}")

    with get_db() as db:
        # Get or create customer
        customer = db.query(Customer).filter(
            Customer.stripe_customer_id == session.customer
        ).first()

        if not customer:
            customer = Customer(
                stripe_customer_id=session.customer,
                email=session.customer_email or session.customer_details.get("email", ""),
            )
            db.add(customer)
            db.flush()

        # Get subscription details from Stripe
        stripe_sub = stripe.Subscription.retrieve(session.subscription)
        price_id = stripe_sub.items.data[0].price.id if stripe_sub.items.data else None
        tier = get_tier_from_price_id(price_id) if price_id else "STARTER"

        # Create subscription record
        subscription = Subscription(
            customer_id=customer.id,
            stripe_subscription_id=session.subscription,
            stripe_price_id=price_id,
            tier=tier,
            status="active",
            current_period_start=datetime.fromtimestamp(stripe_sub.current_period_start),
            current_period_end=datetime.fromtimestamp(stripe_sub.current_period_end),
        )
        db.add(subscription)

        # Generate initial API key
        key, key_record = generate_api_key(customer.id, name="Default Key")
        db.add(key_record)

        # Log billing event
        billing_event = BillingEvent(
            customer_id=customer.id,
            stripe_event_id=event.id,
            event_type="checkout.session.completed",
        )
        db.add(billing_event)

        logger.info(f"Created customer {customer.id} with {tier} subscription")

    return {"status": "success", "customer_id": customer.id}


async def handle_subscription_created(event: stripe.Event) -> dict:
    """Handle customer.subscription.created event."""
    stripe_sub = event.data.object
    logger.info(f"Subscription created: {stripe_sub.id}")

    # Usually handled by checkout.completed, but handle edge cases
    with get_db() as db:
        existing = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_sub.id
        ).first()

        if existing:
            return {"status": "already_exists"}

        # Find customer
        customer = db.query(Customer).filter(
            Customer.stripe_customer_id == stripe_sub.customer
        ).first()

        if not customer:
            logger.warning(f"Customer not found for subscription {stripe_sub.id}")
            return {"status": "customer_not_found"}

        price_id = stripe_sub.items.data[0].price.id if stripe_sub.items.data else None
        tier = get_tier_from_price_id(price_id) if price_id else "FREE"

        subscription = Subscription(
            customer_id=customer.id,
            stripe_subscription_id=stripe_sub.id,
            stripe_price_id=price_id,
            tier=tier,
            status=stripe_sub.status,
            current_period_start=datetime.fromtimestamp(stripe_sub.current_period_start),
            current_period_end=datetime.fromtimestamp(stripe_sub.current_period_end),
        )
        db.add(subscription)

    return {"status": "created"}


async def handle_subscription_updated(event: stripe.Event) -> dict:
    """Handle customer.subscription.updated event."""
    stripe_sub = event.data.object
    logger.info(f"Subscription updated: {stripe_sub.id}")

    with get_db() as db:
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_sub.id
        ).first()

        if not subscription:
            logger.warning(f"Subscription not found: {stripe_sub.id}")
            return {"status": "not_found"}

        # Update subscription
        price_id = stripe_sub.items.data[0].price.id if stripe_sub.items.data else None
        if price_id:
            subscription.stripe_price_id = price_id
            subscription.tier = get_tier_from_price_id(price_id)

        subscription.status = stripe_sub.status
        subscription.current_period_start = datetime.fromtimestamp(stripe_sub.current_period_start)
        subscription.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
        subscription.cancel_at_period_end = stripe_sub.cancel_at_period_end

        # Log event
        billing_event = BillingEvent(
            customer_id=subscription.customer_id,
            stripe_event_id=event.id,
            event_type="customer.subscription.updated",
        )
        db.add(billing_event)

    return {"status": "updated", "tier": subscription.tier}


async def handle_subscription_deleted(event: stripe.Event) -> dict:
    """Handle customer.subscription.deleted event."""
    stripe_sub = event.data.object
    logger.info(f"Subscription deleted: {stripe_sub.id}")

    with get_db() as db:
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_sub.id
        ).first()

        if not subscription:
            return {"status": "not_found"}

        subscription.status = "canceled"

        # Log event
        billing_event = BillingEvent(
            customer_id=subscription.customer_id,
            stripe_event_id=event.id,
            event_type="customer.subscription.deleted",
        )
        db.add(billing_event)

    return {"status": "canceled"}


async def handle_invoice_paid(event: stripe.Event) -> dict:
    """Handle invoice.paid event."""
    invoice = event.data.object
    logger.info(f"Invoice paid: {invoice.id}")

    with get_db() as db:
        customer = db.query(Customer).filter(
            Customer.stripe_customer_id == invoice.customer
        ).first()

        if not customer:
            return {"status": "customer_not_found"}

        billing_event = BillingEvent(
            customer_id=customer.id,
            stripe_event_id=event.id,
            event_type="invoice.paid",
            amount_cents=invoice.amount_paid,
            currency=invoice.currency,
            invoice_url=invoice.hosted_invoice_url,
            invoice_pdf=invoice.invoice_pdf,
        )
        db.add(billing_event)

    return {"status": "recorded"}


async def handle_payment_failed(event: stripe.Event) -> dict:
    """Handle invoice.payment_failed event."""
    invoice = event.data.object
    logger.warning(f"Payment failed: {invoice.id}")

    with get_db() as db:
        customer = db.query(Customer).filter(
            Customer.stripe_customer_id == invoice.customer
        ).first()

        if not customer:
            return {"status": "customer_not_found"}

        # Update subscription status
        subscription = db.query(Subscription).filter(
            Subscription.customer_id == customer.id,
            Subscription.status == "active",
        ).first()

        if subscription:
            subscription.status = "past_due"

        # Log event
        billing_event = BillingEvent(
            customer_id=customer.id,
            stripe_event_id=event.id,
            event_type="invoice.payment_failed",
            amount_cents=invoice.amount_due,
            currency=invoice.currency,
        )
        db.add(billing_event)

    return {"status": "recorded"}


# Event handler registry
WEBHOOK_HANDLERS: Dict[str, Callable] = {
    "checkout.session.completed": handle_checkout_completed,
    "customer.subscription.created": handle_subscription_created,
    "customer.subscription.updated": handle_subscription_updated,
    "customer.subscription.deleted": handle_subscription_deleted,
    "invoice.paid": handle_invoice_paid,
    "invoice.payment_failed": handle_payment_failed,
}


async def process_webhook_event(event: stripe.Event) -> dict:
    """Process a Stripe webhook event."""
    handler = WEBHOOK_HANDLERS.get(event.type)

    if handler:
        return await handler(event)
    else:
        logger.debug(f"Unhandled event type: {event.type}")
        return {"status": "ignored", "event_type": event.type}
