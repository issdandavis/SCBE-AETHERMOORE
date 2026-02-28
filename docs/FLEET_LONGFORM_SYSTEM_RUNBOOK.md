# Fleet Long-Form System Runbook

Date: 2026-02-27  
Scope: SCBE fleet-mode execution (n8n + bridge + Playwright + GitHub Actions + connector mesh)

## 1) Objective

Build a governed long-form work system where:

- `n8n` orchestrates multi-step flows
- SCBE bridge enforces governance gates
- Playwright swarm executes browser tasks
- GitHub Actions continuously validates system health
- free + paid connectors feed training and operations pipelines

## 2) Quick OAuth Bootstrap

Generate connector env template:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/quick_oauth_bootstrap.ps1 -Profile all -IncludeCurrentSession -PrintStatus
```

Output file:

- `config/connector_oauth/.env.connector.oauth`

## 3) Start Stable Local Stack (Isolated Ports)

```powershell
powershell -ExecutionPolicy Bypass -File workflows/n8n/start_n8n_local.ps1 `
  -ProjectRoot "C:\Users\issda\SCBE-AETHERMOORE" `
  -N8nUserFolder "C:\Users\issda\SCBE-AETHERMOORE\.n8n_local_iso" `
  -BridgePort 8002 `
  -BrowserPort 8012 `
  -N8nPort 5680 `
  -N8nTaskBrokerPort 5681 `
  -StartBrowserAgent
```

## 4) Validate Full System

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/smoke_n8n_bridge.ps1 `
  -BridgeUrl http://127.0.0.1:8002 `
  -BrowserUrl http://127.0.0.1:8012 `
  -N8nUrl http://127.0.0.1:5680 `
  -StartupWaitSec 10 `
  -ProbeWebhook `
  -Output artifacts/system_smoke/fleet_stack_smoke.json
```

## 5) Validate Connector Matrix (Free + Paid)

```bash
python scripts/connector_health_check.py \
  --checks github notion drive huggingface airtable n8n bridge playwright zapier telegram \
  --n8n-base-url http://127.0.0.1:5680 \
  --bridge-base-url http://127.0.0.1:8002 \
  --playwright-base-url http://127.0.0.1:8012 \
  --output artifacts/connector_health/fleet_connector_health.json
```

## 6) Register Connectors In Two Commands

Free profile:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/register_connector_profiles.ps1 `
  -Profile free `
  -BaseUrl http://127.0.0.1:8000 `
  -N8nBaseUrl http://127.0.0.1:5680 `
  -Output artifacts/connector_health/connector_registration_free.json
```

Paid profile:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/register_connector_profiles.ps1 `
  -Profile paid `
  -BaseUrl http://127.0.0.1:8000 `
  -N8nBaseUrl http://127.0.0.1:5680 `
  -Output artifacts/connector_health/connector_registration_paid.json
```

Use `-ReplaceExisting` to re-apply updates.

## 7) One-Command Fleet Bootstrap

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/fleet_longform_bootstrap.ps1 `
  -ApiBaseUrl http://127.0.0.1:8000 `
  -BridgeUrl http://127.0.0.1:8002 `
  -BrowserUrl http://127.0.0.1:8012 `
  -N8nUrl http://127.0.0.1:5680
```

Add `-FullConnectorHealth` to include external cloud checks (GitHub/Notion/Drive/HF/Airtable/Zapier/Telegram) in the final step.
If your keys differ by service:

- `-MobileApiKey` should target `src.api.main` (`/mobile/connectors`).
- `-BridgeApiKey` should target n8n bridge (`/v1/*` endpoints).

## 7b) Telegram Bring-Up (OpenClaw-Hardened)

Set bot token + numeric chat id (avoid `@username` targets):

```powershell
$env:TELEGRAM_BOT_TOKEN="<bot_token>"
$env:TELEGRAM_CHAT_ID="<numeric_chat_id>"
```

Validate Telegram connectivity:

```bash
python scripts/connector_health_check.py --checks telegram --telegram-chat-id "$TELEGRAM_CHAT_ID" --output artifacts/connector_health/telegram_health.json
```

Optional connector profile endpoint (for n8n webhook routing):

- `TELEGRAM_CONNECTOR_WEBHOOK_URL` or `SCBE_TELEGRAM_WEBHOOK_URL`

## 7c) Telegram Cloud Webhook (BotFather HTTPS Requirement)

Use the cloud-safe workflow with no Telegram credential-ID dependency:

- `workflows/n8n/scbe_telegram_webhook_cloud.workflow.json`

Set required variables in your n8n environment:

```powershell
$env:TELEGRAM_BOT_TOKEN="<bot_token>"
$env:SCBE_BRIDGE_URL="http://127.0.0.1:8002"
$env:SCBE_API_KEY="<bridge_api_key>"
```

Activate workflow and set BotFather webhook to production URL:

`https://<your-n8n-domain>/webhook/telegram-clayofsand`

Set webhook from terminal:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/telegram_webhook_ops.ps1 `
  -Action set `
  -WebhookUrl "https://<your-n8n-domain>/webhook/telegram-clayofsand"
```

Validate webhook status:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/telegram_webhook_ops.ps1 -Action get
```

## 8) CI Layer

- Stack smoke CI:
  - `.github/workflows/full-system-stack-smoke.yml`
- Nightly connector health:
  - `.github/workflows/nightly-connector-health.yml`

Runbook target:

1. stack smoke green
2. connector matrix green for free services
3. paid services move from `needs_configuration` to `ok` as credentials are added

## 9) Fleet Execution Pattern

1. Intake from Notion/GitHub/Zapier/webhooks
2. n8n action builder creates browse/work tasks
3. Bridge routes to Playwright and applies governance scan
4. approved outputs go to:
   - training ingest
   - content buffers
   - GitHub actions/artifacts
5. telemetry and health reports feed recurring ops loops

## 10) Priority Build Order (Patent-Aligned)

1. Keep governance + provenance always-on in every path.
2. Stabilize fleet operations (`n8n`, bridge, Playwright, Actions).
3. Expand data loop (free connectors first, paid connectors second).
4. Continue GeoSeed/F1-F2-F3 implementation behind the validated ops substrate.
