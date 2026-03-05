# Code To Profit Runbook (AetherBrowse / SCBE)

## Goal
Turn product traffic into paid Stripe subscriptions with minimum friction.

## What Is Live In This Patch
- Public checkout API: `POST /v1/billing/public-checkout`
- Stripe webhook endpoint: `POST /v1/billing/webhooks/stripe`
- Landing page CTA flow wired to checkout (`product-landing.html`)
- Billing router mounted in `api/main.py`

## Required Env Vars
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_STARTER`
- `STRIPE_PRICE_PRO`
- `STRIPE_PRICE_ENTERPRISE`
- `STRIPE_SUCCESS_URL`
- `STRIPE_CANCEL_URL`
- `STRIPE_PORTAL_RETURN_URL`

## Local Smoke Test
1. Start API: `uvicorn api.main:app --host 127.0.0.1 --port 8080`
2. Test checkout:
   - `curl -X POST http://127.0.0.1:8080/v1/billing/public-checkout -H "Content-Type: application/json" -d "{\"email\":\"you@company.com\",\"tier\":\"PRO\",\"source\":\"manual-smoke\"}"`
3. Open `product-landing.html`, enter email, click a checkout button.

## Stripe Webhook Setup
1. Add endpoint in Stripe Dashboard:
   - `https://<your-domain>/v1/billing/webhooks/stripe`
2. Subscribe at minimum to:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.paid`
   - `invoice.payment_failed`

## Weekly Profit KPIs
- Landing visits
- Checkout starts
- Paid conversions
- MRR delta
- 30-day churn

## Execution Loop
1. Improve conversion copy on pricing cards.
2. Run outbound traffic to the landing page.
3. Review checkout-start and paid-conversion ratio daily.
4. Patch the biggest drop-off first.
