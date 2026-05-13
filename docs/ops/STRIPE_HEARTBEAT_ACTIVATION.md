# Stripe Heartbeat Activation

Generated: 2026-05-10
Updated: 2026-05-12

## Live Status

Live production objects created 2026-05-12:

- Workflow Snapshot checkout URL: `https://buy.stripe.com/aFafZiggOdyn9gQ11Ydby0l`
- Workflow Snapshot Payment Link ID: `plink_1TW71yJTF2SuUODIqYFRU9JY`
- Workflow Snapshot Price ID: `price_1TW71xJTF2SuUODIRvBZKUa9`
- Governance Heartbeat checkout URL: `https://buy.stripe.com/5kQ6oI0hQgKz9gQ6midby0m`
- Governance Heartbeat Payment Link ID: `plink_1TW71zJTF2SuUODICZLQCCS3`
- Governance Heartbeat Price ID: `price_1TW71zJTF2SuUODIkHVk4Ws0`

The public checkout URL and Payment Link ID are now baked in as safe public
fallbacks. These Vercel production environment variables are still allowed as
overrides, but the Heartbeat path no longer depends on setting them before use:

```text
SCBE_PAYMENT_LINK_HEARTBEAT=https://buy.stripe.com/5kQ6oI0hQgKz9gQ6midby0m
STRIPE_HEARTBEAT_PAYMENT_LINK_ID=plink_1TW71zJTF2SuUODICZLQCCS3
```

## Historical Sandbox Status

The local Stripe connector is pointed at a sandbox account, not the live Stripe account.

Sandbox objects created:

- Product: `prod_UUQSk8tzQsQ1eK`
- Price: `price_1TVRc3JjzxXjWlGn5Vr36BYc`
- Payment Link ID: `plink_1TVRcAJjzxXjWlGnCMjblKK0`
- Test checkout URL: redacted sandbox URL, intentionally not stored as a clickable public link.

Do not put the test checkout URL in `docs/offers.json`, Vercel production env, or public offer pages.

## Production Activation

In the live Stripe Dashboard:

1. Create product: `Governance Heartbeat`.
2. Create recurring price: `$99.00 USD / month`.
3. Create a Payment Link for quantity `1`.
4. Copy the public live checkout URL, which should look like:
   - `https://buy.stripe.com/...`
   - never a sandbox checkout URL
5. Copy the live Payment Link ID, which starts with `plink_`.

Then set Vercel production environment variables if you want to override the
checked-in production defaults:

```text
SCBE_PAYMENT_LINK_HEARTBEAT=https://buy.stripe.com/<live_heartbeat_subscription_link>
STRIPE_HEARTBEAT_PAYMENT_LINK_ID=plink_<live_heartbeat_payment_link_id>
```

`SCBE_PAYMENT_LINK_HEARTBEAT` controls what Polly and the catalog give customers.
`STRIPE_HEARTBEAT_PAYMENT_LINK_ID` lets the Stripe webhook classify the checkout
as `polly_heartbeat_started`. If either variable is unset, the code falls back
to the live 2026-05-12 Heartbeat link and `plink_1TW71zJTF2SuUODICZLQCCS3`.

The commerce layer rejects internal `plink_...` IDs and sandbox checkout URLs as public checkout overrides.

## Digital Product Delivery

For paid Toolkit and Vault package delivery, also pin the live Payment Link IDs.
Both products are `$29`, so the webhook deliberately refuses to guess by price
alone.

Set these Vercel production environment variables:

```text
STRIPE_TOOLKIT_PAYMENT_LINK_ID=plink_<live_toolkit_payment_link_id>
STRIPE_VAULT_PAYMENT_LINK_ID=plink_<live_vault_payment_link_id>
```

The webhook also accepts the older already-deployed aliases:

```text
SCBE_PAYMENT_LINK_TOOLKIT=plink_<live_toolkit_payment_link_id>
SCBE_PAYMENT_LINK_VAULT=plink_<live_vault_payment_link_id>
```

Set these GitHub Actions secrets if the product-delivery workflow should email
buyers a direct access link:

```text
SCBE_DELIVERY_BASE_URL=https://scbe-agent-bridge-vercel.vercel.app/api/agent/download
SCBE_DELIVERY_TOKEN=<buyer_delivery_token>
POLLY_LEAD_SMTP_HOST=<smtp host>
POLLY_LEAD_SMTP_PORT=<smtp port>
POLLY_LEAD_SMTP_USER=<smtp user>
POLLY_LEAD_SMTP_PASS=<smtp password>
POLLY_LEAD_SMTP_FROM=<from address>
POLLY_LEAD_SMTP_TO=<operator copy>
```

If SMTP or delivery secrets are missing, the workflow still files a
`product-delivery` issue so manual fulfillment does not disappear.
