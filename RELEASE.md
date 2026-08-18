# SCBE product release

One sentence: users send agent traffic through SCBE; SCBE PQC-seals it, gates it, writes a receipt, and bills **provider cost + 2%**.

## What to run

```powershell
python -m uvicorn src.api.main:app --port 8000
```

That is the only public process. `api.main:app` on 8080 stays in-tree for old scripts. It is not the product.

## What it is

- Agentic loop: register → turn/tool call → gate → allow/deny/quarantine → signed receipt
- Channel: **ML-KEM-768**. Receipts: **ML-DSA-65**. No hash stand-ins on this path.
- Money: `src/api/stripe_billing.py` + `docs/offers.json`. Existing Stripe Payment Links start a customer. Usage lines are `provider_cost_cents + ceil(provider_cost_cents * 0.02)`.
- Operator UI (optional client): AetherDesk in its own repo, `npm run aetherdesk` → `http://127.0.0.1:5717`
- Browser client (later): AetherBrowse in `src/browser/`. Not an app-store ship for this cut.

## What is not the product

- GitHub `kernel-data-sync-*` tags (training dumps; created as prereleases so they are not Latest)
- Bookforge, AetherMon, webtoon, gacha/isekai, patent workbench, research/ops dumps
- `api/billing/` placeholder $99/$499 seat table

Do not delete those trees. Do not link them as the product.

## Verify

```powershell
pytest tests/api/test_provider_pass_through_fee.py -q
npm run typecheck
```

Next product tag only after the fee math, the single API, and the Releases page (Latest ≠ a dataset zip) all hold.
