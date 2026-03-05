# Connector Closure Plan (To Cash)

Date: 2026-03-04
Owner: issdandavis
Scope: Stripe + X/Twitter + Shopify + Zapier + HF rails required for monetization ops

## Verified Baseline

- Stripe billing connector code exists:
  - `api/billing/routes.py`
  - `api/billing/stripe_client.py`
  - `api/billing/webhooks.py`
- Stripe key validity:
  - `STRIPE_SECRET_KEY` in local secret store is valid (`/v1/account` probe succeeded).
- X posting script exists:
  - `scripts/publish/post_to_x.py` (expects `X_BEARER_TOKEN` for v2 post).
- GitHub repo secrets currently include:
  - `ANTHROPIC_API_KEY`, `HF_TOKEN`, `SHOPIFY_ACCESS_TOKEN`, `XAI_API_KEY`
- GitHub repo secrets currently missing (for this plan):
  - `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, X posting tokens (`X_BEARER_TOKEN` etc.)
- Local connector health snapshot:
  - `github`: ok
  - `notion`: ok
  - `huggingface`: ok
  - `zapier`: error (webhook points at `127.0.0.1:5680`, n8n offline)

## Objective

Get all monetization-critical connectors to `green` in one lane so revenue workflows can run without manual patching.

## Priority Order

1. Stripe (cash collection + webhook truth)
2. X/Twitter (distribution)
3. Zapier/n8n (automation transport)
4. Shopify (offer delivery/sync)
5. Monitoring + matrix gate

## Phase 0 (Today, 30 minutes): Secret Canonicalization

### Actions
- Standardize secret names for scripts and CI:
  - Stripe: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
  - X: `X_BEARER_TOKEN` (primary), optional `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET`
  - Shopify: `SHOPIFY_ACCESS_TOKEN`, `SHOPIFY_SHOP`
  - Automation: `ZAPIER_WEBHOOK_URL`, `N8N_BASE_URL`

### Done when
- All keys above exist either in local secret store or GitHub secrets (depending on usage path).

## Phase 1 (Today, 60 minutes): Stripe Production-Ready Gate

### Actions
1. Add missing webhook secret:
- local: set `STRIPE_WEBHOOK_SECRET`
- GitHub: set `STRIPE_WEBHOOK_SECRET`

2. Add Stripe key to GitHub Actions secrets (if workflows rely on it):
- `STRIPE_SECRET_KEY`

3. Run local endpoint smoke (read-only + webhook signature check path).

### Done when
- Checkout, webhook verification, and event ingestion are all validated.
- `billing_events.stripe_event_id` duplicate protection remains active.

## Phase 2 (Today, 45 minutes): X/Twitter Posting Enablement

### Actions
1. Acquire X API credentials from developer portal.
2. Store `X_BEARER_TOKEN` (minimum needed by `post_to_x.py`).
3. Run script dry-run, then live single tweet.

### Commands
```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
python scripts/publish/post_to_x.py --text "SCBE connector lane online" --dry-run
python scripts/publish/post_to_x.py --text "SCBE connector lane online"
```

### Done when
- One successful tweet ID returned and logged.

## Phase 3 (Today, 45 minutes): Zapier/n8n Transport Recovery

### Actions
1. Decide transport mode:
- Remote Zapier hook (preferred for reliability), or
- Local n8n webhook (requires always-on n8n service).

2. Update `ZAPIER_WEBHOOK_URL` to chosen live endpoint.
3. Re-run connector health check.

### Done when
- `zapier` status = `ok` in `scripts/connector_health_check.py` output.

## Phase 4 (Today, 30 minutes): Shopify Lane Finalization

### Actions
1. Ensure `SHOPIFY_SHOP` + `SHOPIFY_ACCESS_TOKEN` are set in runtime where publishing occurs.
2. Run product sync command.

### Commands
```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
python scripts/shopify_bridge.py status
python scripts/shopify_bridge.py products --publish-live
```

### Done when
- Catalog sync returns created/updated counts with zero critical errors.

## Phase 5 (Daily, 10 minutes): Green Gate + Revenue Loop

### Actions
1. Run connector check and archive output.
2. Run one monetization action (post, publish, lead dispatch).
3. Record daily cash scorecard.

### Commands
```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
$env:PYTHONPATH='.'
python scripts/connector_health_check.py --checks github notion huggingface zapier --output artifacts/connector_health/monetization_core_health.json
python C:\Users\issda\.codex\skills\scbe-monetization-thought-to-cash\scripts\build_cash_scorecard.py --cash-today 0 --orders 0 --top-offer "Hydra Armor API" --next-action "Ship one direct revenue action now."
```

## Risk Controls

- Do not launch broad outreach if Stripe webhook secret is missing.
- Do not rely on local `127.0.0.1` hooks for unattended workflows.
- Keep key names canonical to prevent hidden fallback failures.

## 24-Hour Outcome Target

- Stripe: fully green (key + webhook secret + smoke).
- X posting: live.
- Zapier: reachable endpoint.
- Shopify: publish-live verified.
- Daily scorecard generated.
