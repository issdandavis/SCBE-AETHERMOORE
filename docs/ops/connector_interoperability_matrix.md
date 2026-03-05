# Connector Interoperability Matrix

Date: 2026-03-04

| Platform | Connector Surface | Auth Key(s) | Current Status | Evidence | Blocker | Next Action |
|---|---|---|---|---|---|---|
| Stripe | `api/billing/*` | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | Partial | Stripe account probe succeeded with local `STRIPE_SECRET_KEY` | `STRIPE_WEBHOOK_SECRET` not present in active config/GitHub secrets | Add webhook secret local + GitHub and run webhook smoke |
| X/Twitter | `scripts/publish/post_to_x.py` | `X_BEARER_TOKEN` (primary), optional OAuth1 keys | Blocked | Script exists and targets X API v2 | No X posting token configured | Add `X_BEARER_TOKEN` and test `--dry-run` then live post |
| Shopify | `scripts/shopify_bridge.py` | `SHOPIFY_SHOP`, `SHOPIFY_ACCESS_TOKEN` | Green | Terminal live publish succeeded: `updated=7 errors=0` on `aethermore-works.myshopify.com` | None | Keep daily publish/update in terminal sell lane |
| Hugging Face | `scripts/connector_health_check.py`, workflows | `HF_TOKEN` | Green | `hf auth whoami` ok, health check ok, GitHub secret exists | None | Keep as baseline provider for dataset/model lanes |
| GitHub | `gh` + workflows | `GITHUB_TOKEN` | Green | Health check ok, authenticated CLI | None | Keep nightly workflow checks |
| Notion | connector health + workflows | `NOTION_TOKEN`/`NOTION_API_KEY` | Green | Health check ok | None | Continue as knowledge source |
| Zapier | webhook dispatch | `ZAPIER_WEBHOOK_URL` | Red | health check returns connection refused at `127.0.0.1:5680` | Local webhook endpoint offline | Switch to always-on webhook or ensure n8n service is always running |
| xAI/Grok (LLM) | provider routing | `XAI_API_KEY` / `GROK_API_KEY` | Green | API model list probe succeeded | Alias drift between key names | Keep `XAI_API_KEY` as canonical and map `GROK_API_KEY` as alias |
| Anthropic (LLM) | provider routing | `ANTHROPIC_API_KEY` | Green | API model list probe succeeded | None | Keep in model council lane |

## Gate Rule

Only treat monetization lane as "ready" when Stripe, X posting, Shopify, and Zapier are all green simultaneously.
