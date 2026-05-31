# Low-Cost Download Ladder - 2026-05-31

Goal: make SCBE easy to buy without pricing out small builders. The free SDK
builds trust; low-cost downloads create first revenue; services stay small and
bounded unless a buyer asks for deeper integration.

## Market Signal

Agentic AI is moving fast, but production trust is the bottleneck:

- Gartner warns that uniform governance across all AI agents can lead to
  enterprise agent failure, and predicts many enterprises will demote or
  decommission agents because governance gaps are discovered after incidents.
- Gartner's 2026 agentic AI hype-cycle coverage puts agentic AI governance,
  security, and FinOps on the adoption-critical path.
- AI governance market reports show strong growth, with Grand View Research
  estimating a 36% CAGR from 2026 to 2033.
- Agentic AI security is being priced as a separate fast-growing category, with
  MarketsandMarkets projecting growth from $1.65B in 2026 to $13.52B by 2032.

Implication: do not sell "receipts" as the product. Sell the shortest path from
"my agent works in a demo" to "I can safely put this in front of users."

## Offer Ladder

| Offer | Type | Price | Delivery rail | Notes |
| --- | --- | ---: | --- | --- |
| `scbe-govern` | Free SDK | Free | PyPI + GitHub | Trust builder; no checkout. |
| Agent Safety Starter Pack | Digital download | $7 | Stripe webhook ZIP | Examples, checklist, LangChain/n8n snippets. |
| Workflow Snapshot Lite | Small service | $29 | Stripe + intake form | One short written note, 3 risks, 3 fixes. |
| Governed Agent Setup | Small service | $79 | Stripe + intake form | Help wrap one simple tool/action path. |
| Small Team Agent Review | Service | $149 | Stripe + intake form | One workflow review packet, no enterprise theater. |
| Governance Snapshot | Service | $300-$500 | Stripe + intake form | Only for buyers needing procurement/audit packet. |

## Download System Mapping

Existing rails:

- Product builder: `scripts/package_products.py`
- Buyer ZIP staging: `products/packaged/`
- Manual/product pages: `docs/product-manual/`
- Offer registry: `docs/offers.json`
- Commerce responder: `api/polly/commerce.js`
- Stripe delivery runbook: `docs/ops/STRIPE_DIGITAL_DELIVERY.md`

Add the $7 starter pack as the next download SKU:

```text
id: agent_safety_starter_pack
name: SCBE Agent Safety Starter Pack
price_label: $7
package_name: SCBE_Agent_Safety_Starter_Pack_v1.zip
manual_url: https://aethermoore.com/SCBE-AETHERMOORE/product-manual/agent-safety-starter-pack.html
stripe metadata: metadata[scbe_product]=agent_safety_starter
download env: SCBE_AGENT_SAFETY_STARTER_DOWNLOAD_URL
```

Package contents should be small and useful:

- `README.md` - first 10 minutes
- `examples/langchain_shell_guard.py`
- `examples/n8n_govern_check.json`
- `examples/autogen_pre_tool_hook.py`
- `checklists/agent-production-readiness.md`
- `checklists/tool-risk-tiering.md`
- `templates/workflow-risk-note.md`
- `templates/command-denylist-review.md`
- `sdk/scbe-govern-quickstart.md`

## Service Fulfillment Mapping

For $29/$79/$149 services, do not create large downloads first. Use checkout plus
intake:

1. Stripe Payment Link sends buyer to a thank-you/intake page.
2. Intake form captures:
   - buyer email
   - agent framework
   - workflow/tool description
   - repo or diagram link if any
   - one goal and one fear
3. We deliver a Markdown/PDF packet by email.
4. Optional: delivery packet can later become a downloadable artifact if repeatable.

## Implementation Order

1. Publish `scbe-govern` to PyPI.
2. Add `agent_safety_starter_pack` to `scripts/package_products.py`.
3. Add `docs/product-manual/agent-safety-starter-pack.html`.
4. Add offer entry to `docs/offers.json`.
5. Add product entry in `api/polly/commerce.js`.
6. Create a live Stripe link with metadata `scbe_product=agent_safety_starter`.
7. Set `SCBE_AGENT_SAFETY_STARTER_DOWNLOAD_URL` once the ZIP is hosted.
8. Update `docs/products.html`, `docs/payments.html`, and `docs/governance-sdk.html`.

## Pricing Rule

Keep first purchase easy. The download should feel like buying a practical tool,
not hiring a consultancy. Service prices should stay bounded and plain-language
until a buyer explicitly asks for enterprise integration.
