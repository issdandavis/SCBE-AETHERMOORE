---
name: scbe-mobile-connector-orchestrator
description: Operate the SCBE mobile-goal control plane with external service connectors (Shopify, Zapier, n8n, Slack, Notion, Airtable, GitHub Actions, Linear, Discord, generic webhook). Use when asked to register connectors, bind goals to connectors, run step execution, enforce high-risk approval gates, or troubleshoot connector dispatch failures.
---

# SCBE Mobile Connector Orchestrator

Use this skill to run phone-driven autonomous workflows through `src/api/main.py` safely.

## Scope

1. Register and inspect connectors.
2. Create and manage mobile goals.
3. Bind connectors to goals.
4. Advance execution with high-risk approval gates.
5. Troubleshoot connector dispatch and auth failures.

## Canonical API Endpoints

1. `GET /mobile/connectors/templates`
2. `POST /mobile/connectors`
3. `GET /mobile/connectors`
4. `GET /mobile/connectors/{connector_id}`
5. `DELETE /mobile/connectors/{connector_id}`
6. `POST /mobile/goals`
7. `GET /mobile/goals`
8. `GET /mobile/goals/{goal_id}`
9. `POST /mobile/goals/{goal_id}/bind-connector`
10. `POST /mobile/goals/{goal_id}/advance`
11. `POST /mobile/goals/{goal_id}/approve`

## Required Safety Rules

1. Never auto-approve high-risk steps when `require_human_for_high_risk=true`.
2. Never execute if connector auth material is missing for protected endpoints.
3. Keep Shopify operations read-safe by default (`payload_mode=shopify_graphql_read`).
4. Treat non-2xx connector responses as failed step dispatch.
5. Preserve deterministic event history and return latest goal state.

## Standard Workflow

1. List templates and pick connector profile.
2. Register connector with minimal valid fields.
3. Create goal in `execution_mode=connector` with that `connector_id`.
4. Call `advance` until:
   - `review_required`: request explicit user approval, then call `approve`.
   - `completed`: return final state and summary.
   - `failed`: return failure reason and dispatch details.

## Shopify Path (Preferred Default)

1. Register connector with:
   - `kind=shopify`
   - `shop_domain=<store>.myshopify.com`
   - `auth_type=header`
   - `auth_header_name=X-Shopify-Access-Token`
   - `auth_token=<admin_api_token>`
2. Let API auto-build endpoint:
   - `https://<store>.myshopify.com/admin/api/<version>/graphql.json`
3. Keep first runs read-only and inspect goal events before adding write workflows.

## Quick Command Templates (PowerShell)

```powershell
$api = "http://localhost:8000"
$key = "demo_key_12345"

Invoke-RestMethod -Method Get -Uri "$api/mobile/connectors/templates" -Headers @{"x-api-key"=$key}
```

```powershell
# register connector
$conn = Invoke-RestMethod -Method Post -Uri "$api/mobile/connectors" `
  -Headers @{"x-api-key"=$key} -ContentType "application/json" `
  -Body (@{
    name = "shopify-admin-read"
    kind = "shopify"
    shop_domain = "your-store.myshopify.com"
    auth_type = "header"
    auth_header_name = "X-Shopify-Access-Token"
    auth_token = "<TOKEN>"
    enabled = $true
  } | ConvertTo-Json)

$connectorId = $conn.data.connector_id
```

```powershell
# create and advance goal
$goal = Invoke-RestMethod -Method Post -Uri "$api/mobile/goals" `
  -Headers @{"x-api-key"=$key} -ContentType "application/json" `
  -Body (@{
    goal = "Run storefront operations and publish report"
    channel = "store_ops"
    priority = "high"
    execution_mode = "connector"
    connector_id = $connectorId
    targets = @("https://your-store.myshopify.com/admin")
    require_human_for_high_risk = $true
  } | ConvertTo-Json)

$goalId = $goal.data.goal_id
Invoke-RestMethod -Method Post -Uri "$api/mobile/goals/$goalId/advance" -Headers @{"x-api-key"=$key} -ContentType "application/json" -Body "{}"
Invoke-RestMethod -Method Get -Uri "$api/mobile/goals/$goalId" -Headers @{"x-api-key"=$key}
```

## Troubleshooting Matrix

1. `401 Invalid API key` -> confirm `x-api-key` and environment.
2. `404 connector not found` -> connector owner mismatch or deleted connector.
3. `blocked / review_required` -> call `approve` before next `advance`.
4. `connector_http_error` -> inspect endpoint auth/header contract.
5. `connector_network_error` -> endpoint unreachable, TLS/DNS/firewall issue.

## Output Contract

Return:

1. `connector_id` and profile summary.
2. `goal_id`, current `status`, and current step index.
3. Actionable next command (`approve`, `advance`, or fix auth/endpoint).
4. Brief risk note if high-risk steps are pending.
