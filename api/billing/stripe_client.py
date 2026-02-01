"""
Stripe API client wrapper for SCBE billing.

Handles checkout sessions, customer portal, and subscription management.
"""

import os
from typing import Optional

import stripe

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# URLs for redirects
SUCCESS_URL = os.getenv("STRIPE_SUCCESS_URL", "https://scbe.dev/billing/success")
CANCEL_URL = os.getenv("STRIPE_CANCEL_URL", "https://scbe.dev/billing/cancel")
PORTAL_RETURN_URL = os.getenv("STRIPE_PORTAL_RETURN_URL", "https://scbe.dev/dashboard")


class StripeClient:
    """Wrapper for Stripe operations."""

    @staticmethod
    def create_checkout_session(
        tier: str,
        price_id: str,
        customer_email: Optional[str] = None,
        customer_id: Optional[str] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> dict:
        """
        Create a Stripe Checkout session for subscription signup.

        Returns dict with session_id and checkout_url.
        """
        session_params = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success_url or f"{SUCCESS_URL}?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": cancel_url or CANCEL_URL,
            "metadata": {"tier": tier},
        }

        if customer_id:
            session_params["customer"] = customer_id
        elif customer_email:
            session_params["customer_email"] = customer_email

        session = stripe.checkout.Session.create(**session_params)

        return {
            "session_id": session.id,
            "checkout_url": session.url,
            "tier": tier,
        }

    @staticmethod
    def create_portal_session(
        stripe_customer_id: str,
        return_url: Optional[str] = None,
    ) -> dict:
        """
        Create a Stripe Customer Portal session for self-service management.

        Returns dict with portal_url.
        """
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=return_url or PORTAL_RETURN_URL,
        )

        return {
            "portal_url": session.url,
        }

    @staticmethod
    def get_subscription(subscription_id: str) -> dict:
        """Get subscription details from Stripe."""
        sub = stripe.Subscription.retrieve(subscription_id)
        return {
            "id": sub.id,
            "status": sub.status,
            "current_period_start": sub.current_period_start,
            "current_period_end": sub.current_period_end,
            "cancel_at_period_end": sub.cancel_at_period_end,
            "price_id": sub.items.data[0].price.id if sub.items.data else None,
        }

    @staticmethod
    def cancel_subscription(subscription_id: str, at_period_end: bool = True) -> dict:
        """Cancel a subscription (optionally at period end)."""
        if at_period_end:
            sub = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True,
            )
        else:
            sub = stripe.Subscription.delete(subscription_id)

        return {
            "id": sub.id,
            "status": sub.status,
            "cancel_at_period_end": getattr(sub, "cancel_at_period_end", True),
        }

    @staticmethod
    def reactivate_subscription(subscription_id: str) -> dict:
        """Reactivate a subscription that was set to cancel at period end."""
        sub = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=False,
        )

        return {
            "id": sub.id,
            "status": sub.status,
            "cancel_at_period_end": sub.cancel_at_period_end,
        }

    @staticmethod
    def update_subscription_price(subscription_id: str, new_price_id: str) -> dict:
        """Change the subscription to a new price (upgrade/downgrade)."""
        sub = stripe.Subscription.retrieve(subscription_id)

        # Update the subscription item with new price
        stripe.Subscription.modify(
            subscription_id,
            items=[
                {
                    "id": sub.items.data[0].id,
                    "price": new_price_id,
                }
            ],
            proration_behavior="create_prorations",
        )

        # Fetch updated subscription
        updated_sub = stripe.Subscription.retrieve(subscription_id)

        return {
            "id": updated_sub.id,
            "status": updated_sub.status,
            "price_id": updated_sub.items.data[0].price.id,
        }

    @staticmethod
    def get_customer(customer_id: str) -> dict:
        """Get customer details from Stripe."""
        customer = stripe.Customer.retrieve(customer_id)
        return {
            "id": customer.id,
            "email": customer.email,
            "name": customer.name,
        }

    @staticmethod
    def list_invoices(customer_id: str, limit: int = 10) -> list:
        """List invoices for a customer."""
        invoices = stripe.Invoice.list(customer=customer_id, limit=limit)
        return [
            {
                "id": inv.id,
                "amount_due": inv.amount_due,
                "amount_paid": inv.amount_paid,
                "currency": inv.currency,
                "status": inv.status,
                "created": inv.created,
                "hosted_invoice_url": inv.hosted_invoice_url,
                "invoice_pdf": inv.invoice_pdf,
            }
            for inv in invoices.data
        ]

    @staticmethod
    def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
        """Construct and verify a Stripe webhook event."""
        return stripe.Webhook.construct_event(
            payload,
            sig_header,
            STRIPE_WEBHOOK_SECRET,
        )
