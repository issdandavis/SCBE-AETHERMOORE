---
name: aetherbrowse-dev
description: Use when developing, extending, or debugging the AetherBrowse governed AI browser. Triggers on mentions of "aetherbrowse", "agent runtime", "perceiver", "planner", "browser worker", "hydra armor", "hydra bridge", "governance policy", "model routing", "octoarmor", or "aether://".
version: 0.1.0
---

# AetherBrowse Development Guide

Build and extend the SCBE-governed AI browser. All source lives under `aetherbrowse/` in the SCBE-AETHERMOORE repo.

## Architecture

AetherBrowse is a three-process system:

1. **Electron shell** (`aetherbrowse/electron/main.js`) — tabbed browser window with agent sidebar and governance log panel. Communicates with the runtime via WebSocket at `ws://127.0.0.1:8400/ws`.

2. **Python agent runtime** (`aetherbrowse/runtime/server.py`) — FastAPI + WebSocket server on port 8400. Hosts the agent loop and HTTP API. The central `AgentRuntime` class manages 4 named agents:
   - **Zara** (leader, tongue KO) — evaluates commands, owns the PLAN phase
   - **Kael** (executor, tongue CA) — carries out action plans, owns EXECUTE
   - **Aria** (validator, tongue AV) — reviews governance, flags risky steps
   - **Polly** (observer, tongue UM) — perceives pages, read-only

3. **Playwright browser worker** (`aetherbrowse/worker/browser_worker.py`) — drives real Chromium via Playwright. Connects to runtime at `ws://127.0.0.1:8400/ws/worker`. Supports multi-profile persistent sessions, network profile switching (clear/dark), and connector-bridge actions (Telegram, GitHub, HuggingFace).

## Agent Loop

```
PERCEIVE → PLAN → GOVERN → EXECUTE
  (Polly)   (Zara)  (Aria)   (Kael)
```

- **PERCEIVE**: `aetherbrowse/runtime/perceiver.py` — transforms accessibility tree / screenshots / DOM into `PagePerception` objects. `HydraPerceiver` runs 3-head consensus (vision + DOM + governance).
- **PLAN**: `aetherbrowse/runtime/planner.py` — takes user command + `PagePerception`, produces `ActionPlan` (list of `BrowserAction` steps). Routes through OctoArmor for LLM reasoning, falls back to rule-based planning.
- **GOVERN**: Governance policies in `aetherbrowse/config/governance_policies.yaml` define domain allow/deny lists, action-level coherence thresholds, rate limits, and agent permissions.
- **EXECUTE**: Runtime's `_execute_plan()` sends each step to the Playwright worker with retry budgets and deterministic waits.

## Key Files

| File | Purpose |
|------|---------|
| `aetherbrowse/electron/main.js` | Electron main process, tab management, IPC |
| `aetherbrowse/electron/preload.js` | Context bridge for renderer |
| `aetherbrowse/renderer/index.html` | Shell UI (sidebar, address bar, governance log) |
| `aetherbrowse/runtime/server.py` | Agent runtime, WebSocket server, HTTP API |
| `aetherbrowse/runtime/perceiver.py` | Page perception (Perceiver + HydraPerceiver) |
| `aetherbrowse/runtime/planner.py` | Action planning (rule-based + LLM) |
| `aetherbrowse/runtime/hydra_bridge.py` | Hydra Armor API routes (`/v1/armor/verify`, `/v1/hydra-armor`) |
| `aetherbrowse/runtime/env_bootstrap.py` | Environment variable alias expansion |
| `aetherbrowse/runtime/landing.html` | Browser landing page |
| `aetherbrowse/runtime/search.html` | Search results page with engine selector |
| `aetherbrowse/runtime/dashboard.html` | Kerrigan home dashboard |
| `aetherbrowse/worker/browser_worker.py` | Playwright automation worker |
| `aetherbrowse/config/model_routing.yaml` | LLM provider routing config |
| `aetherbrowse/config/governance_policies.yaml` | Governance rules and agent permissions |
| `aetherbrowse/config/hydra_armor_api.md` | Hydra Armor API documentation |

## How to Extend

### Adding a new browser action

1. Add the action handler in `browser_worker.py` inside the command dispatch (`_handle_command()` method).
2. Add a `BrowserAction` pattern in `planner.py` — either as a rule-based shortcut or in the LLM prompt template.
3. If the action needs governance review, set `governance_required=True` on the `BrowserAction` and add a policy entry in `governance_policies.yaml`.
4. Add retry budget in `AgentRuntime._retry_budget_for_action()` in `server.py`.

### Adding a new planner shortcut

Add a pattern match in `planner.py`'s `_rule_based_plan()` method. Return an `ActionPlan` with `method="rule"`.

### Adding a new agent

1. Add the agent entry in `AgentRuntime.__init__()` agents dict in `server.py`.
2. Define its role, tongue, and allowed actions in `governance_policies.yaml` under `agent_permissions`.
3. Add message handling for the new agent's events.

### Adding a Hydra Armor endpoint

Add a new route in `hydra_bridge.py`'s `register_hydra_routes()` function. Follow the pattern of `/v1/armor/verify`.

### Modifying search routing

Search engines are configured in `server.py`. The `_aether_search()` function handles DuckDuckGo HTML scraping. Multi-engine routing (roundtable, DDG, Bing, fallback) is in `_multi_engine_search()`. The search UI engine selector is in `search.html`.

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `AETHERBROWSE_RUNTIME_HOST` | `127.0.0.1` | Runtime server host |
| `AETHERBROWSE_RUNTIME_PORT` | `8400` | Runtime server port |
| `AETHERBROWSE_HOME_URL` | `http://127.0.0.1:8400/landing` | Browser home page |
| `AETHERBROWSE_APP_ICON` | (auto-detect) | Window icon path |
| `AETHERSCREEN_MOBILE` | `false` | Enable mobile viewport |
| `GOOGLE_AI_API_KEY` | — | Gemini API key for planning |
| `GROQ_API_KEY` | — | Groq API key for governance |

## Testing

```bash
# Unit tests
pytest -q tests/test_aetherbrowse_search_routing.py tests/test_aetherbrowse_planner_workspace.py

# Cross-browser smoke test (requires runtime running)
python scripts/system/aetherbrowse_competitive_smoke.py --base-url http://127.0.0.1:8400

# Install additional browsers
python -m playwright install firefox webkit
```

## Training Data Flywheel

Every governance decision generates SFT/DPO training pairs:
- `training-data/aetherbrowse/governance_pairs.jsonl` — from Hydra Armor API calls
- `training-data/aetherbrowse/planning_pairs.jsonl` — from planner decisions
- Run logs: `artifacts/agent_comm/aetherbrowse/runs.jsonl`
- Search logs: `artifacts/agent_comm/aetherbrowse/search_queries.jsonl`
