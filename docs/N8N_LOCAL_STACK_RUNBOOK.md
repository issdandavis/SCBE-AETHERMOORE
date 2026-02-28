# n8n Local Stack Runbook (SCBE)

Date: 2026-02-26

## Purpose

Run SCBE n8n workflows in a deterministic local workspace and avoid duplicate imports.

## Prerequisites

- `n8n` CLI installed (`n8n --version`)
- Python env with FastAPI/Uvicorn dependencies
- Repo path: `C:\Users\issda\SCBE-AETHERMOORE`

## 1) Import Workflows (Idempotent)

```powershell
powershell -ExecutionPolicy Bypass -File workflows\n8n\import_workflows.ps1
```

Behavior:
- Uses `C:\Users\issda\SCBE-AETHERMOORE\.n8n_local`
- Skips workflow names that already exist
- Exports verification file to:
  - `.n8n_local\export_check\workflows.json`

To import and publish (activate) those workflows:

```powershell
powershell -ExecutionPolicy Bypass -File workflows\n8n\import_workflows.ps1 -PublishWorkflows
```

## 2) Clean Reset + Import

Use this when you want a fresh n8n local DB:

```powershell
powershell -ExecutionPolicy Bypass -File workflows\n8n\import_workflows.ps1 -ResetUserFolder
```

## 3) Start Local Stack

Starts both bridge and n8n:

```powershell
powershell -ExecutionPolicy Bypass -File workflows\n8n\start_n8n_local.ps1 -ImportWorkflows -PublishWorkflows
```

Start bridge + n8n + browser agent (Playwright path for swarm/n8n browse):

```powershell
powershell -ExecutionPolicy Bypass -File workflows\n8n\start_n8n_local.ps1 -ImportWorkflows -PublishWorkflows -StartBrowserAgent
```

Health endpoints:
- Bridge: `http://127.0.0.1:8001/health`
- Browser Agent: `http://127.0.0.1:8011/health`
- n8n UI: `http://127.0.0.1:5678`

Integration status:
- `GET http://127.0.0.1:8001/v1/integrations/status` (requires `X-API-Key`)

## 4) Current Verified Result

On this machine, import stabilizes at 7 workflows after reset (including `SCBE M5 Mesh Data Funnel`).

With `-PublishWorkflows`, all 7 are published/active and loaded on next n8n start/restart.

## Files

- `workflows/n8n/scbe_n8n_bridge.py`
- `workflows/n8n/import_workflows.ps1`
- `workflows/n8n/start_n8n_local.ps1`
- `workflows/n8n/m5_mesh_data_funnel.workflow.json`
- `workflows/n8n/notion_github_swarm_research.workflow.json`

## M5 Funnel Env Vars

Set these for full M5 sink behavior:
- `SCBE_API_KEY`
- `AIRTABLE_API_KEY`
- `AIRTABLE_BASE_ID`
- `AIRTABLE_TABLE_ID`
- `HF_DATASET_REPO` (optional, defaults to `issdandavis/scbe-aethermoore-training-data`)
- `M5_FALLBACK_LOCAL_PATH` (optional local folder for HF upload)

## Browser/Swarm Env Vars

- `SCBE_BROWSER_SERVICE_URL` (default: `http://127.0.0.1:8011`)
- `SCBE_BROWSER_API_KEY` (optional override key for browser service; defaults to bridge key)
- `SCBE_BROWSER_TIMEOUT_SEC` (default: `45`)

## Notion + GitHub Swarm Workflow Trigger

Workflow file:
- `workflows/n8n/notion_github_swarm_research.workflow.json`

Sample payload:
- `workflows/n8n/notion_github_swarm_payload.sample.json`

Trigger command (replace webhook URL from your local n8n execution URL):

```powershell
$body = Get-Content -Raw -Path workflows\n8n\notion_github_swarm_payload.sample.json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5678/webhook/scbe-notion-github-swarm" -ContentType "application/json" -Body $body
```
