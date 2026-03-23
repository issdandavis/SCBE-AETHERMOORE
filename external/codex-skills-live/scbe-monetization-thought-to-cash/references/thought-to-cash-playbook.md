# Thought-To-Cash Playbook

## Mission

Convert one validated idea into cash with the shortest safe path.

## Execution Sequence

1. Define offer in one sentence.
- Problem solved.
- Target buyer.
- Concrete result.

2. Set package and price.
- Core offer.
- One upsell.
- Delivery window.

3. Pick rail.
- `Stripe`: recurring subscriptions or SaaS tiers.
- `Shopify`: one-time digital products, bundles, templates.

4. Wire launch path.
- Checkout route.
- Success destination.
- Fulfillment step.
- Webhook handling and event logging.

5. Publish and distribute.
- One channel first (email, X, LinkedIn, community).
- One CTA per message.

6. Track daily cash KPI.
- Revenue today.
- Orders today.
- Conversion rate.
- Top blocker.
- Next 24h action.

## Fast Command Set

```powershell
# Shopify product catalog preview
python scripts/shopify_bridge.py products

# Shopify live publish (create/update by SKU)
python scripts/shopify_bridge.py products --publish-live
```

## Quality Gates

- Keep claims factual and testable.
- Keep fulfillment path clear before launch.
- Keep webhook verification active.
- Keep daily cash report in Obsidian.
