# Notion MCP Token Fix — 2026-02-22

## Goal
Restore the direct Notion MCP route (`mcp/notion_server.py`) while keeping Zapier/Codex Notion routes as fallback.

## What Was Fixed
- Added `notion-sweep` to `.mcp.json` so the direct Notion MCP server is registered.
- Updated `mcp/notion_server.py` to accept all token aliases:
  - `NOTION_API_KEY`
  - `NOTION_TOKEN`
  - `NOTION_MCP_TOKEN`
- Added runtime token resolution (no process restart needed after env updates).
- Added `notion_health_check` MCP tool for direct route verification.

## Required Environment Setup
Use the same token value for all three variables to avoid route drift.

```powershell
$env:NOTION_API_KEY = "<your_notion_integration_token>"
$env:NOTION_TOKEN = $env:NOTION_API_KEY
$env:NOTION_MCP_TOKEN = $env:NOTION_API_KEY
```

Optional persistence (new shell needed after setx):

```powershell
setx NOTION_API_KEY "<token>"
setx NOTION_TOKEN "<token>"
setx NOTION_MCP_TOKEN "<token>"
```

## Validation
1. Direct API route:

```powershell
python scripts/connector_health_check.py --checks notion --strict
```

2. Page-access route:

```powershell
python scripts/notion_access_check.py --all
```

3. Fallback route:
- Run Zapier/Codex Notion fetch workflow used in current automation.
- Confirm the same page IDs are reachable from both routes.

## Expected Result
- Direct route status: `ok`
- Fallback route status: `ok`
- Nightly connector health report includes `notion: ok`.
