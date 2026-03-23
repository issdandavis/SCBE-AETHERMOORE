# Stripe + Shopify Status Check

## Stripe (current repo status)

Files:
- `api/billing/routes.py`
- `api/billing/stripe_client.py`
- `api/billing/webhooks.py`
- `api/billing/database.py`

What is present:
- Checkout endpoint: `POST /v1/billing/checkout`
- Stripe signature verification on webhook route
- Webhook handlers for checkout/subscription/invoice events
- Billing event table includes unique `stripe_event_id`

What to verify before production:
- Idempotency key strategy on outbound checkout/session create calls
- Duplicate-event handling behavior in webhook processing path
- Success/cancel/receipt URLs match live domain

## Shopify (current repo status)

Files:
- `scripts/shopify_bridge.py`
- `src/symphonic_cipher/scbe_aethermoore/concept_blocks/earn_engine/shopify_bridge.py`

What is present:
- Monetization product catalog payloads
- CLI status/product/blog/theme operations
- Live product sync command:
  - `python scripts/shopify_bridge.py products --publish-live`
- Live sync performs SKU-based upsert (create/update)

Required environment for live publish:
- `SHOPIFY_SHOP` (or full `<shop>.myshopify.com`)
- `SHOPIFY_ACCESS_TOKEN` (or `SHOPIFY_ADMIN_TOKEN`)
- optional: `SHOPIFY_API_VERSION` (default `2025-10`)

## Daily Operating Rule

Do not run broad launches without:
1. One verified checkout path.
2. One fulfillment path.
3. One daily cash scorecard node in Obsidian.
