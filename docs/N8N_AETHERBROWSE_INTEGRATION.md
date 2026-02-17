# n8n + AetherBrowse Integration

This connects n8n tasks to the SCBE browser governance layer using the n8n-compatible
`/v1/integrations/n8n/browse` endpoint.

## What was added

- `agents/browser/main.py`
  - Added env-driven API key loading.
  - Added `/v1/integrations/n8n/browse` endpoint for compact action payloads.
  - Added `X-API-Key` and `Authorization: Bearer` support for API authentication.
- `.env.example`
  - Added browser/n8n key placeholders.
- `scripts/n8n_aetherbrowse_bridge.py`
  - Local CLI to send action payloads to the n8n-compatible endpoint.

## Environment variables

- `BROWSER_AGENT_API_KEYS` (recommended):  
  Comma-separated list of `key:user` pairs, e.g.  
  `BROWSER_AGENT_API_KEYS=n8n-key-1:n8n-agent,n8n-key-2:ops`
- `SCBE_API_KEYS`: legacy pair format (`key:user,...`)
- `SCBE_API_KEY`: legacy single keys
- `N8N_API_KEY`: single n8n callback key
- `N8N_WEBHOOK_TOKEN`: optional alternate n8n token

At runtime, the browser service loads keys from the above and keeps existing defaults:
`browser-agent-key` and `test-key` (dev only).

## Start the browser API service

```powershell
python -m uvicorn agents.browser.main:app --host 0.0.0.0 --port 8001
```

## Test via local bridge script

```bash
setx SCBE_API_KEY "your-browser-api-key"
python scripts/n8n_aetherbrowse_bridge.py --actions '[{"action":"navigate","target":"https://example.com"}]' --workflow-id "wf-001" --run-id "run-001"
```

## n8n Workflow idea

1. Add an **HTTP Request** node.
2. Method: `POST`
3. URL: `http://<host>:8001/v1/integrations/n8n/browse`
4. Headers:
   - `X-API-Key: {{ $env.N8N_API_KEY }}`
   - `Content-Type: application/json`
5. JSON body template:

```json
{
  "workflow_id": "{{ $json.workflow.id }}",
  "run_id": "{{ $json.id }}",
  "source": "n8n",
  "dry_run": false,
  "actions": [
    {"action": "navigate", "target": "{{ $json.payload.url }}"},
    {"action": "screenshot", "target": "full_page"}
  ]
}
```

## Security notes

- Keep production endpoints behind VPN/TLS.
- Rotate API keys regularly.
- Limit payloads to a max of 10 actions per request.
- Keep browser service `safe_radius` and validator thresholds aligned with your trust policy.

