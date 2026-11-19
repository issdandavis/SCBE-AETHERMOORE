# Stripe Digital Delivery

This is the buyer-only fulfillment rail for AetherMoore digital products.

## Security contract

A download is available only when all of these checks pass:

1. the request contains a Stripe Checkout Session ID;
2. the Vercel function retrieves that session directly from Stripe with a restricted key;
3. the session is a completed one-time payment with `payment_status=paid`;
4. the Payment Link ID or merchant-controlled metadata maps to exactly one product;
5. a requested product, when supplied, matches the product attached to the session;
6. the corresponding private Vercel Blob URL is configured.

The public endpoint must not use a shared bearer token. One leaked shared token
would otherwise unlock every product for every visitor.

## Runtime endpoints

- Stripe webhook: `api/billing/stripe_webhook.js`
- Verified download: `api/agent/download.js`

The webhook accepts these fulfillment events:

- `checkout.session.completed`
- `checkout.session.async_payment_succeeded`
- `checkout.session.async_payment_failed` (acknowledged; never fulfilled)

`checkout.session.completed` is not enough by itself. The handler dispatches
delivery only when the embedded Checkout Session is already paid. Delayed
payment methods are fulfilled from `checkout.session.async_payment_succeeded`.

## Environment

```text
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_DELIVERY_RESTRICTED_KEY=rk_live_...

STRIPE_TOOLKIT_PAYMENT_LINK_ID=plink_...
STRIPE_VAULT_PAYMENT_LINK_ID=plink_...
STRIPE_MAKING_OF_PAYMENT_LINK_ID=plink_...

SCBE_TOOLKIT_BLOB_URL=https://...
SCBE_VAULT_BLOB_URL=https://...
SCBE_MAKING_OF_BLOB_URL=https://...
BLOB_READ_WRITE_TOKEN=vercel_blob_...
```

Create the Stripe key as a restricted live key with read access to Checkout
Sessions only. `STRIPE_SECRET_KEY` remains a compatibility fallback, but the
restricted key is the intended production configuration.

## Payment Link redirects

After the verified endpoint is deployed, set each Payment Link's completion
redirect to its product URL. Stripe replaces the literal session placeholder:

```text
https://scbe-agent-bridge-vercel.vercel.app/api/agent/download?product=toolkit&session_id={CHECKOUT_SESSION_ID}
https://scbe-agent-bridge-vercel.vercel.app/api/agent/download?product=vault&session_id={CHECKOUT_SESSION_ID}
https://scbe-agent-bridge-vercel.vercel.app/api/agent/download?product=making_of&session_id={CHECKOUT_SESSION_ID}
```

Do not change the live Payment Links before the new Vercel function and its
restricted key are present. Doing so would send paid buyers to a closed door.

## Buyer email

`.github/workflows/polly-product-delivery.yml` builds a recovery link from the
Stripe session ID in the signed webhook payload. It does not email a shared
delivery secret. The workflow also files a session-keyed operator issue so a
retry does not create duplicate issue records.

## Deployment order

1. Run the targeted tests below.
2. Add the restricted Stripe key and private Blob variables to Vercel.
3. Deploy the Vercel function.
4. Verify one test-mode Checkout Session end to end.
5. Update the three live Payment Link redirects with the session placeholder.
6. Complete one low-cost live purchase and confirm the exact product downloads.
7. Remove the legacy shared delivery token from Vercel and GitHub Actions.

Rollback is the reverse: restore the previous Payment Link redirects first,
then roll back the function. Never remove the current delivery path before the
redirects stop pointing at it.

## Tests

```powershell
npx vitest run tests/api/download_js.test.ts tests/api/stripe_webhook_js.test.ts
```

The regression suite covers missing and forged sessions, unpaid sessions,
wrong-product requests, unknown Payment Links, paid exact-product delivery,
delayed-payment success, and delayed-payment failure.
