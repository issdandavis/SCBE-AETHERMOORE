# Stripe Heartbeat Activation

Generated: 2026-05-10

## Status

The local Stripe connector is pointed at a sandbox account, not the live Stripe account.

Sandbox objects created:

- Product: `prod_UUQSk8tzQsQ1eK`
- Price: `price_1TVRc3JjzxXjWlGn5Vr36BYc`
- Payment Link ID: `plink_1TVRcAJjzxXjWlGnCMjblKK0`
- Test checkout URL: `https://buy.stripe.com/test_00w14oaPgdEJejL6I35Ne05`

Do not put the test checkout URL in `docs/offers.json`, Vercel production env, or public offer pages.

## Production Activation

In the live Stripe Dashboard:

1. Create product: `Governance Heartbeat`.
2. Create recurring price: `$99.00 USD / month`.
3. Create a Payment Link for quantity `1`.
4. Copy the public live checkout URL, which should look like:
   - `https://buy.stripe.com/...`
   - not `https://buy.stripe.com/test_...`
5. Copy the live Payment Link ID, which starts with `plink_`.

Then set Vercel production environment variables:

```text
SCBE_PAYMENT_LINK_HEARTBEAT=https://buy.stripe.com/<live_heartbeat_subscription_link>
STRIPE_HEARTBEAT_PAYMENT_LINK_ID=plink_<live_heartbeat_payment_link_id>
```

`SCBE_PAYMENT_LINK_HEARTBEAT` controls what Polly and the catalog give customers.
`STRIPE_HEARTBEAT_PAYMENT_LINK_ID` lets the Stripe webhook classify the checkout as `polly_heartbeat_started`.

The commerce layer rejects `plink_...` and `https://buy.stripe.com/test_...` as public checkout overrides.

