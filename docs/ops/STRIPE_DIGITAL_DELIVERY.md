# Stripe Digital Delivery

This is the one-time product fulfillment rail for AetherMoore digital products.

## Required Stripe event

Configure the Stripe webhook to send:

- `checkout.session.completed`

The handler lives at:

- `src/api/stripe_billing.py`
- route: `POST /billing/webhook`

Webhook signature verification must stay enabled in production with:

- `STRIPE_WEBHOOK_SECRET`

## Product routing

Preferred setup: set product metadata on each Stripe Payment Link.

- Toolkit Payment Link: `metadata[scbe_product]=toolkit`
- Training Vault Payment Link: `metadata[scbe_product]=vault`

Fallback setup for existing links: map Stripe Payment Link IDs in environment.

```text
SCBE_PAYMENT_LINK_TOOLKIT=plink_...
SCBE_PAYMENT_LINK_VAULT=plink_...
```

Do not route by price. Both current products are low-cost one-time offers and
price-based routing can mis-deliver when products have the same price.

## Delivery links

Set direct product download URLs in environment when the ZIPs are hosted.

```text
SCBE_TOOLKIT_DOWNLOAD_URL=https://...
SCBE_VAULT_DOWNLOAD_URL=https://...
```

If these are not set, the delivery email falls back to the latest GitHub release:

```text
https://github.com/issdandavis/SCBE-AETHERMOORE/releases/latest
```

`SCBE_TRAINING_VAULT_DOWNLOAD_URL` is also accepted as the clearer alias for
the Training Vault buyer-only ZIP link. Keep `SCBE_VAULT_DOWNLOAD_URL` for
backwards compatibility with the earlier billing patch.

The default package builder writes buyer ZIPs under `products/packaged/`, which
is intentionally ignored by git. That lane is for staging paid packets, not for
public GitHub Pages.

## SMTP

Buyer delivery email uses:

```text
SCBE_SMTP_HOST=smtp.porkbun.com
SCBE_SMTP_PORT=587
SCBE_SMTP_USER=ai@aethermoore.com
SCBE_SMTP_PASS=...
```

If SMTP is not configured, the webhook does not crash. It logs the delivery
attempt and records the purchase as an audit trail item.

## Buyer email includes

- product name
- download URL
- manual URL
- expected ZIP filename
- support URL

## Smoke test

```powershell
python -m pytest tests\api\test_stripe_billing_hardening.py tests\test_package_products.py -q
python scripts\package_products.py --product all --output-dir artifacts\product_delivery_current_smoke
```
