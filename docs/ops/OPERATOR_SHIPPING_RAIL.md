# Operator shipping rail (agent tasks → SCBE surfaces)

Goal: run **one-command agent tasks**, emit auditable artifacts, and route external tooling through **SCBE-first** surfaces (GeoSeal CLI, FastAPI harness, n8n bridge, MCP) instead of ad hoc scripts.

## Entrypoint

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
python scripts/agents/run_agent_task.py --help
```

Each run writes under `artifacts/agent_task_runs/` (see script defaults) and attaches **`tool_bridge`** payload **`scbe_agent_tool_bridge_v1`**: GeoSeal CLI hints, service URLs, n8n routes, MCP lane notes.

## Harness HTTP (local API)

With the API app mounted (e.g. `src/api/main.py` including GeoSeal routes):

- **`POST /v1/harness/tool-bridge`** — builds the same bridge from an optional inline goal (`src/api/geoseal_service.py`).

Use this to smoke-check the bridge without writing a full agent task packet.

## Billing (production)

| Variable | Purpose |
|----------|---------|
| `STRIPE_SECRET_KEY` | Stripe API |
| `STRIPE_WEBHOOK_SECRET` | Verify webhooks (`whsec_*`) |
| `SCBE_BILLING_BASE_URL` | Public base for checkout return URLs |
| `SCBE_BILLING_DB_PATH` | SQLite path (default: repo `.scbe/billing.sqlite3`) |
| `SCBE_OWNER_API_TOKEN` | Required for `GET /billing/purchases` via header `x-owner-token` |
| `SCBE_ALLOW_UNSIGNED_STRIPE_WEBHOOK` | Dev-only: allow unsigned webhook payloads (do not set in prod) |

## Verification snippets

```powershell
# Billing hardening regression
$env:PYTHONPATH='.'
python -m pytest tests/api/test_stripe_billing_hardening.py -v --tb=short

# Curated CI-equivalent Python lane
python scripts/system/run_core_python_checks.py
```

## Related docs

- Merge and stash: `docs/ops/MERGE_AND_STASH_PLAYBOOK.md`
- PR body template: `docs/ops/PR_BODY_feat_agent_bus_spaceready.md`
