# Product Launch Readiness

This repo now treats launch as an auditable gate, not a vibe check.

## Sources Distilled

- Shopify launch guidance emphasizes complete product pages, policy pages, checkout/payment readiness, store navigation, and post-launch channels.
- Stripe checkout guidance emphasizes reducing checkout friction and using a conversion-optimized hosted checkout for simple purchases.
- YC launch guidance emphasizes getting a narrow product in front of users quickly, then iterating from real feedback.

## SCBE Rule

Launch one clear offer at a time:

1. A buyer can understand the offer from the proof page.
2. The offer has a real price and real checkout URL.
3. The policy/support path exists before payment.
4. The checkout route is testable.
5. The offer feeds back into delivery, support, and training capture.

## Command

```powershell
python scripts\system\product_launch_readiness.py
```

Outputs:

- `artifacts/marketing/product_launch_readiness/latest/product-launch-readiness.json`
- `artifacts/marketing/product_launch_readiness/latest/product-launch-readiness.md`

Use `--fail-on-not-ready` in CI when the public offer surface must block deploy.
