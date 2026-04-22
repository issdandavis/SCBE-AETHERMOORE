#!/usr/bin/env python3
"""Register Stripe webhook endpoint for SCBE product delivery.

Creates a webhook in Stripe that sends checkout.session.completed events
to the SCBE API server. Prints the webhook signing secret for .secrets/env.local.

Usage:
    # For deployed API (Cloud Run, VPS, etc.):
    python scripts/setup_stripe_webhook.py --url https://api.aethermoore.com/billing/webhook

    # For local development with Stripe CLI forwarding:
    python scripts/setup_stripe_webhook.py --local

    # List existing webhooks:
    python scripts/setup_stripe_webhook.py --list

    # Delete a webhook:
    python scripts/setup_stripe_webhook.py --delete we_xxxxx
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Load .secrets/env.local if present
_secrets = Path(__file__).resolve().parents[1] / ".secrets" / "env.local"
if _secrets.is_file():
    with open(_secrets) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip()
                if k and v and k not in os.environ:
                    os.environ[k] = v

try:
    import stripe
except ImportError:
    print("ERROR: stripe SDK not installed. Run: pip install stripe")
    sys.exit(1)


WEBHOOK_EVENTS = [
    "checkout.session.completed",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_failed",
]


def get_stripe_key() -> str:
    key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not key:
        print("ERROR: STRIPE_SECRET_KEY not set.")
        print("  Paste it into .secrets/env.local or set as env var.")
        print("  Get it from: https://dashboard.stripe.com/apikeys")
        sys.exit(1)
    return key


def list_webhooks():
    stripe.api_key = get_stripe_key()
    endpoints = stripe.WebhookEndpoint.list(limit=20)
    if not endpoints.data:
        print("No webhook endpoints configured.")
        return
    print(f"\n{'ID':<30} {'URL':<60} {'Status':<10}")
    print("-" * 100)
    for ep in endpoints.data:
        print(f"{ep.id:<30} {ep.url:<60} {ep.status:<10}")
    print()


def create_webhook(url: str):
    stripe.api_key = get_stripe_key()

    # Check if webhook already exists for this URL
    existing = stripe.WebhookEndpoint.list(limit=50)
    for ep in existing.data:
        if ep.url == url:
            print(f"Webhook already exists for {url}")
            print(f"  ID: {ep.id}")
            print(f"  Status: {ep.status}")
            print(f"  Events: {', '.join(ep.enabled_events)}")
            print(f"\nTo recreate, delete first: python scripts/setup_stripe_webhook.py --delete {ep.id}")
            return

    endpoint = stripe.WebhookEndpoint.create(
        url=url,
        enabled_events=WEBHOOK_EVENTS,
        description="SCBE-AETHERMOORE product delivery + subscription lifecycle",
    )

    print(f"\nWebhook created successfully!")
    print(f"  ID:     {endpoint.id}")
    print(f"  URL:    {endpoint.url}")
    print(f"  Secret: {endpoint.secret}")
    print(f"  Events: {', '.join(WEBHOOK_EVENTS)}")
    print()

    # Update .secrets/env.local with the webhook secret
    env_file = Path(__file__).resolve().parents[1] / ".secrets" / "env.local"
    if env_file.is_file():
        content = env_file.read_text()
        if "STRIPE_WEBHOOK_SECRET=" in content:
            lines = content.splitlines()
            new_lines = []
            for line in lines:
                if line.strip().startswith("STRIPE_WEBHOOK_SECRET="):
                    new_lines.append(f"STRIPE_WEBHOOK_SECRET={endpoint.secret}")
                else:
                    new_lines.append(line)
            env_file.write_text("\n".join(new_lines) + "\n")
            print(f"Updated .secrets/env.local with webhook secret.")
        else:
            with open(env_file, "a") as f:
                f.write(f"\n# Stripe Webhook Secret (auto-generated)\nSTRIPE_WEBHOOK_SECRET={endpoint.secret}\n")
            print(f"Appended webhook secret to .secrets/env.local")
    else:
        print(f"\nAdd this to your .secrets/env.local:")
        print(f"  STRIPE_WEBHOOK_SECRET={endpoint.secret}")


def delete_webhook(webhook_id: str):
    stripe.api_key = get_stripe_key()
    try:
        stripe.WebhookEndpoint.delete(webhook_id)
        print(f"Deleted webhook {webhook_id}")
    except stripe.error.InvalidRequestError as e:
        print(f"Error: {e}")


def setup_local():
    """Print instructions for local dev with Stripe CLI."""
    print("""
Local Development Setup (Stripe CLI)
=====================================

1. Download Stripe CLI:
   https://stripe.com/docs/stripe-cli#install

2. Login to Stripe:
   stripe login

3. Forward webhooks to local API:
   stripe listen --forward-to localhost:8000/billing/webhook

4. Copy the webhook signing secret (whsec_...) shown in the output
   and paste it into .secrets/env.local as STRIPE_WEBHOOK_SECRET

5. In another terminal, start the API:
   python -m uvicorn src.api.main:app --reload --port 8000

6. Test with:
   stripe trigger checkout.session.completed
""")


def main():
    parser = argparse.ArgumentParser(description="Configure Stripe webhooks for SCBE")
    parser.add_argument("--url", help="Public webhook URL (e.g., https://api.aethermoore.com/billing/webhook)")
    parser.add_argument("--local", action="store_true", help="Show local dev setup instructions")
    parser.add_argument("--list", action="store_true", help="List existing webhooks")
    parser.add_argument("--delete", metavar="WEBHOOK_ID", help="Delete a webhook by ID")
    args = parser.parse_args()

    if args.list:
        list_webhooks()
    elif args.delete:
        delete_webhook(args.delete)
    elif args.local:
        setup_local()
    elif args.url:
        create_webhook(args.url)
    else:
        # Default: show what's configured
        print("Stripe Webhook Setup for SCBE-AETHERMOORE")
        print("=" * 45)
        list_webhooks()
        print("Usage:")
        print("  --url <URL>   Create webhook for deployed API")
        print("  --local       Show local dev setup with Stripe CLI")
        print("  --list        List existing webhooks")
        print("  --delete <ID> Delete a webhook")


if __name__ == "__main__":
    main()
