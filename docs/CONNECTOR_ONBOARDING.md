# Connector Onboarding (Zapier / n8n / Shopify)

Date: 2026-02-20  
Scope: Bring-your-own service connectors for mobile goal execution

## What is implemented

In `src/api/main.py`:

- `GET /mobile/connectors/templates`
- `POST /mobile/connectors`
- `GET /mobile/connectors`
- `GET /mobile/connectors/{connector_id}`
- `DELETE /mobile/connectors/{connector_id}`
- `POST /mobile/goals/{goal_id}/bind-connector`
- `POST /mobile/connectors/policy-check`

Goal execution mode:

- `execution_mode=connector` calls the registered connector endpoint from `/mobile/goals/{goal_id}/advance`.
- High-risk approval gate remains active before dispatch.

Supported connector kinds:

- `n8n`
- `zapier`
- `shopify` (auto Shopify Admin GraphQL endpoint when only `shop_domain` is provided)
- `slack`
- `notion`
- `airtable`
- `github_actions`
- `linear`
- `discord`
- `generic_webhook`

## Discover templates

```bash
curl -X GET http://localhost:8000/mobile/connectors/templates \
  -H "x-api-key: demo_key_12345"
```

## Terminal-first control

To run the same connector + goal flow from terminal, use:

- `scripts/scbe_terminal_ops.py`
- `docs/TERMINAL_OPS_QUICKSTART.md`

## Register a connector

Example (n8n):

```bash
curl -X POST http://localhost:8000/mobile/connectors \
  -H "x-api-key: demo_key_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "n8n-store-ops",
    "kind": "n8n",
    "endpoint_url": "https://YOUR-N8N/webhook/store-ops",
    "auth_type": "header",
    "auth_header_name": "x-n8n-key",
    "auth_token": "YOUR_SECRET",
    "enabled": true
  }'
```

Example (Zapier Catch Hook):

```json
{
  "name": "zapier-store-ops",
  "kind": "zapier",
  "endpoint_url": "https://hooks.zapier.com/hooks/catch/XXX/YYY/",
  "auth_type": "none",
  "enabled": true
}
```

Example (Shopify orchestrator webhook):

```json
{
  "name": "shopify-orchestrator",
  "kind": "shopify",
  "endpoint_url": "https://YOUR-AUTOMATION-SERVICE/shopify/run",
  "auth_type": "bearer",
  "auth_token": "YOUR_BEARER_TOKEN",
  "enabled": true
}
```

Example (direct Shopify Admin read connector, auto endpoint):

```json
{
  "name": "shopify-admin-read",
  "kind": "shopify",
  "shop_domain": "your-shop.myshopify.com",
  "auth_type": "header",
  "auth_header_name": "X-Shopify-Access-Token",
  "auth_token": "YOUR_SHOPIFY_ADMIN_TOKEN",
  "enabled": true
}
```

Optional connector fields:

- `http_method`: `POST` (default), `PUT`, `PATCH`, `DELETE`, `GET`
- `timeout_seconds`: default `8`
- `payload_mode`: `scbe_step`, `raw_step`, `shopify_graphql_read`
- `default_headers`: object of additional outbound headers

## Bind connector to goal

1. Create goal (`POST /mobile/goals`) in simulate mode, or set:
   - `execution_mode: "connector"`
   - `connector_id: "<connector_id>"`
2. Bind after creation (optional):
   - `POST /mobile/goals/{goal_id}/bind-connector`

## Payload sent to connector

```json
{
  "goal_id": "abc123",
  "channel": "store_ops",
  "priority": "high",
  "step": {"name": "collect_store_state", "risk": "low"},
  "targets": ["https://example-store/admin"],
  "metadata": {"owner": "demo_user", "ts": 1739999999}
}
```

Headers include:

- `Content-Type: application/json`
- optional auth header/bearer
- `x-scbe-ts`
- `x-scbe-signature` (when `SCBE_CONNECTOR_SIGNING_KEY` is set)
- For local runs, store this key via the local tokenized vault:
  - `python scripts/system/secret_store.py set SCBE_CONNECTOR_SIGNING_KEY "your_local_key"`
  - `python scripts/system/secret_store.py get SCBE_CONNECTOR_SIGNING_KEY`

## Governance policy-check endpoint

Use `POST /mobile/connectors/policy-check` to get deterministic policy verdicts for pending connector actions before dispatch.

Supported decision tiers:

- `ALLOW`
- `QUARANTINE`
- `DENY`

Example:

```bash
curl -X POST http://localhost:8000/mobile/connectors/policy-check \
  -H "x-api-key: demo_key_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "submit",
    "goal": "Update product title",
    "channel": "store_ops",
    "priority": "high",
    "step_risk": "medium",
    "owner": "shopify-app",
    "targets": ["gid://shopify/Product/123"],
    "connector_id": "conn_xxx",
    "emit_webhook": true
  }'
```

Response includes:

- `action` (echoed request action)
- `policy.verdict` (`ALLOW` | `QUARANTINE` | `DENY`)
- `policy.risk_score` and `policy.coherence`
- optional `webhook` result when `emit_webhook=true`

## Recommended production hardening

1. Store connector secrets in KMS/Secrets Manager.
2. Add per-connector retry policy and dead-letter queue.
3. Add per-connector allowlists for endpoint domains.
4. Persist connector + goal state to durable database.
5. Add webhook callback verification for connector responses.
