# Stripe Digital Delivery

Purpose: keep paid SCBE products deliverable without exposing buyer-only packets through the public GitHub Pages site.

## Product Packets

Build the current buyer packets with:

```bash
python scripts/package_products.py
```

Expected local outputs:

- `products/packaged/SCBE_AI_Governance_Toolkit_v1.zip`
- `products/packaged/SCBE_AI_Security_Training_Vault_v1.zip`

The `products/packaged/` directory is intentionally ignored by git. It is a delivery staging lane, not a public docs lane.

## Runtime Delivery URLs

Set these environment variables in production before promoting paid traffic:

- `SCBE_TOOLKIT_DOWNLOAD_URL`
- `SCBE_TRAINING_VAULT_DOWNLOAD_URL`

If a variable is unset, `src/api/stripe_billing.py` falls back to the public GitHub Releases URL. That fallback is acceptable for smoke tests, but buyer-only delivery should use product-specific links.

## Checkout Mapping

Stripe Checkout Session metadata must include:

- `scbe_product=toolkit` for the AI Governance Toolkit
- `scbe_product=vault` for the AI Security Training Vault

Purchases without this metadata are logged as unresolved and do not trigger automatic buyer delivery. This prevents same-price product misdelivery.

## Verification

Focused checks:

```bash
python -m pytest tests/test_package_products.py tests/api/test_stripe_billing_hardening.py -q
```

Before launch, also send a test checkout or Stripe CLI webhook using each product key and confirm the buyer email contains the expected buyer-only URL and manual URL.
