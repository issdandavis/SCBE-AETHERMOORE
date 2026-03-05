---
name: aetherbrowse-ops
description: Use when starting, stopping, monitoring, or managing the AetherBrowse browser stack. Triggers on "start aetherbrowse", "launch browser", "aetherbrowse health", "browser profiles", "governance logs", "hydra armor usage", "aetherbrowse status", or "runtime health".
version: 0.1.0
---

# AetherBrowse Operations Guide

Operate the AetherBrowse governed AI browser stack.

## Stack Components

The full AetherBrowse stack has 3 processes:

| Process | Command | Port | Required |
|---------|---------|------|----------|
| Agent runtime | `python aetherbrowse/runtime/server.py` | 8400 | Yes |
| Playwright worker | `python aetherbrowse/worker/browser_worker.py` | connects to 8400 | For automation |
| Electron shell | `cd aetherbrowse && npm run dev` | connects to 8400 | For GUI |

## Starting the Stack

### Minimal (runtime only)

```bash
cd C:\Users\issda\SCBE-AETHERMOORE
python -m uvicorn aetherbrowse.runtime.server:app --host 127.0.0.1 --port 8400
```

### Runtime + Worker

```bash
# Terminal 1: Runtime
python -m uvicorn aetherbrowse.runtime.server:app --host 127.0.0.1 --port 8400

# Terminal 2: Worker
python aetherbrowse/worker/browser_worker.py
```

### Full stack with Electron

```bash
# Terminal 1: Runtime
python -m uvicorn aetherbrowse.runtime.server:app --host 127.0.0.1 --port 8400

# Terminal 2: Worker
python aetherbrowse/worker/browser_worker.py

# Terminal 3: Electron
cd aetherbrowse && npm run dev
```

## Health Checks

### Runtime health
```bash
curl http://127.0.0.1:8400/health
```
Returns: `{"status": "ok", "electron": bool, "worker": bool, "agents": {...}}`

### Full system status
```bash
curl http://127.0.0.1:8400/api/status
```
Returns runtime connection state, current URL, action count, and agent statuses.

### Hydra Armor health
```bash
curl http://127.0.0.1:8400/v1/armor/health
```
Returns OctoArmor and SCBE governance availability.

### Agent usage stats
```bash
curl http://127.0.0.1:8400/v1/armor/usage/{agent_id}
```

## Browser Profiles

Persistent browser profiles with storage state live at:
```
aetherbrowse/profiles/<profile_id>/storage_state.json
```

### Commands via runtime
- `switch profile to <profile_id>` — switch active browser profile
- `list profiles` — show available profiles
- `autofill login for <domain> [submit]` — autofill saved credentials

### Import Google passwords
```powershell
python scripts/system/import_google_password_export.py `
  --csv "C:\path\to\Google Passwords.csv" `
  --profile-id creator-main
```

## Governance Logs

| Log File | Content |
|----------|---------|
| `artifacts/aetherbrowse/governance.jsonl` | All governance decisions |
| `artifacts/aetherbrowse/actions.jsonl` | Browser actions taken |
| `artifacts/agent_comm/aetherbrowse/runs.jsonl` | Plan execution runs |
| `artifacts/agent_comm/aetherbrowse/search_queries.jsonl` | Search query history |
| `artifacts/aetherbrowse/hydra_usage.jsonl` | Hydra Armor API usage |
| `artifacts/aetherbrowse/cost_log.jsonl` | LLM cost tracking |
| `training-data/aetherbrowse/governance_pairs.jsonl` | SFT training pairs |

### View recent runs
```bash
curl http://127.0.0.1:8400/api/runs/latest?limit=5
```

### View specific run
```bash
curl http://127.0.0.1:8400/api/runs/{run_id}
```

## Search Engine Configuration

Multi-engine search with roundtable, DuckDuckGo, Bing, and fallback routing. Test via:
```bash
curl "http://127.0.0.1:8400/api/search?q=test+query&limit=5"
```

## Model Routing

LLM provider configuration lives in `aetherbrowse/config/model_routing.yaml`:
- `governance_check` → free tier (Groq/Cerebras)
- `page_understanding` → cheap tier (Gemini Flash)
- `action_planning` → cheap tier (Gemini/OpenRouter)
- `complex_reasoning` → premium tier (Claude/Grok)

Daily budget: `$1.00` (configurable in `cost_tracking.daily_budget_usd`).

## Electron Desktop Build

```bash
cd aetherbrowse
npm run build:win    # Windows (NSIS + portable + zip)
npm run build:dir    # Directory output only
```

Output: `artifacts/releases/aetherbrowse-desktop/`

## Troubleshooting

- **Runtime won't start**: Check `fastapi` and `uvicorn` are installed: `pip install fastapi uvicorn websockets`
- **Worker can't connect**: Ensure runtime is running first, worker connects to `ws://127.0.0.1:8400/ws/worker`
- **Electron shows blank**: Runtime must be running before Electron launches
- **No search results**: Check DuckDuckGo rate limiting; fallback URLs will be returned
- **Governance DENY on everything**: Check `governance_policies.yaml` domain lists and coherence thresholds
