# SCBE Agent Bus User Guide

Updated: 2026-04-30

This guide covers the working bus surfaces in this repository: the Python Agent Bus, the GitHub Actions Agent Router, the Vercel bridge, and the cross-agent relay packet lane.

## What Works Now

### Python Agent Bus

The Python bus lives in `agents/`.

Core entrypoints:

- `agents/agent_bus.py` - ask, summarize, analyze, monitor, team decisions, tool generation, training trigger.
- `agents/agent_bus_cli.py` - operator CLI.
- `agents/agent_bus_signing.py` - event signing with fallback chain.
- `agents/agent_bus_schema.py` - event schema validation.
- `agents/agent_bus_replay.py` - read-only replay/postmortem from `events.jsonl`.
- `agents/agent_bus_extensions.py` - generated tool validation and live test harness.

Current synced Tier-1 features from GitHub:

- fallback signing chain: ML-DSA-65 when available, then Ed25519, then HMAC fallback;
- schema enforcement: rejects unknown future major event versions;
- live test harness for generated tools;
- replay CLI for event logs.

### GitHub Actions Agent Router

The router workflow is `.github/workflows/agent-router.yml`.

It can run these tasks:

- `research`
- `monitor`
- `ask`
- `scrape`
- `web_search`
- `coding`
- `system_build`
- `agentic_ladder`
- `pair_benchmark`
- `poly_coding_seed`

The newest branch proof runs passed:

- `pair_benchmark`: https://github.com/issdandavis/SCBE-AETHERMOORE/actions/runs/25148293991
- `poly_coding_seed`: https://github.com/issdandavis/SCBE-AETHERMOORE/actions/runs/25148325259

Both were run with `publish=false`, so they verified execution without changing GitHub Pages data.

### Vercel Bridge

The public Vercel bridge is:

`https://scbe-agent-bridge-vercel.vercel.app`

Health check:

```powershell
Invoke-RestMethod -Uri "https://scbe-agent-bridge-vercel.vercel.app/api/agent/health" -Method Get
```

Current production status:

- bridge is online;
- dispatch is configured;
- dispatch secret is required;
- production currently points at `main`;
- production still advertises only `research`, `monitor`, `ask`, and `scrape`.

That means Vercel is usable for the older web-task bus today, but the newer coding/router lanes need the feature branch merged to `main` or the Vercel environment variable `AGENT_ROUTER_REF` pointed at `feat/agent-bus-spaceready`.

Do not put the SAM.gov API key in a public browser path. Keep SAM.gov scans in GitHub Actions secrets or local scripts.

## Common Commands

### Local Agent Bus CLI

Show recent performance:

```powershell
python -m agents.agent_bus_cli perf
```

Validate a bus event log:

```powershell
python -m agents.agent_bus_cli verify artifacts/agent-bus/events.jsonl
```

Replay a bus event log:

```powershell
python -m agents.agent_bus_cli replay artifacts/agent-bus/events.jsonl --by-task
```

Ask without web search:

```powershell
python -m agents.agent_bus_cli run "Summarize the bus status in one sentence." --no-search
```

Local browser-backed commands require Playwright Chromium. If it is missing, install it with:

```powershell
python -m playwright install chromium
```

Because Chromium is large, skip that install on a low-disk machine and use the GitHub Actions router instead.

### GitHub Actions Router

Run the paired coding benchmark on the feature branch:

```powershell
gh workflow run agent-router.yml --ref feat/agent-bus-spaceready -f task=pair_benchmark -f query="Run dual-agent pair benchmark" -f publish=false
```

Run the poly-coded external training seed builder on the feature branch:

```powershell
gh workflow run agent-router.yml --ref feat/agent-bus-spaceready -f task=poly_coding_seed -f query="Regenerate external poly coding seed corpus" -f publish=false
```

Watch the latest router run:

```powershell
gh run list --workflow agent-router.yml --branch feat/agent-bus-spaceready --limit 3
```

### Vercel Dispatch

After Vercel is redeployed with the new allowed task list, dispatch through the bridge:

```powershell
$body = @{
  task = "pair_benchmark"
  query = "Run dual-agent pair benchmark"
  publish = "false"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "https://scbe-agent-bridge-vercel.vercel.app/api/agent/dispatch" `
  -Method Post `
  -ContentType "application/json" `
  -Headers @{ "X-Agent-Dispatch-Secret" = $env:AGENT_DISPATCH_SECRET } `
  -Body $body
```

Check Vercel bridge run status:

```powershell
Invoke-RestMethod -Uri "https://scbe-agent-bridge-vercel.vercel.app/api/agent/status?limit=5" -Method Get
```

## Cross-Agent Relay

Use `scripts/system/crosstalk_relay.py` when Codex, Claude, Cursor, or another worker needs to pass a bounded status packet.

Emit a packet:

```powershell
python scripts/system/crosstalk_relay.py emit `
  --sender codex `
  --recipient claude `
  --intent sync `
  --task-id agent-bus-sync `
  --summary "Synced Agent Bus modules from origin/main and verified focused bus tests." `
  --status done `
  --proof "python -m pytest tests/test_agentbus_self_review.py tests/test_agentbus_user_e2e.py tests/benchmark/test_agentbus_competitive_wedge.py -q" `
  --next-action "Merge feature branch or redeploy Vercel so production bridge exposes the new router lanes." `
  --risk low `
  --branch feat/agent-bus-spaceready
```

Verify a packet:

```powershell
python scripts/system/crosstalk_relay.py verify --packet-id <packet-id>
```

Acknowledge receipt:

```powershell
python scripts/system/crosstalk_relay.py ack --packet-id <packet-id> --agent claude
```

## Current Local Caveats

- The local working tree has other active Cursor/Claude changes. Do not broad-merge `origin/main` until those are reviewed or stashed.
- A broad merge currently conflicts in `.gitignore`, `agents/agent_bus.py`, `agents/agent_bus_cli.py`, `agents/agent_bus_extensions.py`, `agents/agent_bus_signing.py`, and `docs/static/polly-sidebar.js`.
- The Agent Bus modules themselves have been synced from `origin/main` into this branch.
- Local Playwright Chromium is missing, so full local browser-backed `AgentBus.start()` fails until Chromium is installed.
- GitHub Actions installs Chromium during router runs, so the CI router path is currently the safest working bus path.

## Recommended Nightly Operating Loop

1. Keep local dirty work isolated.
2. Fetch GitHub:

```powershell
git fetch origin --prune
```

3. Run bus tests:

```powershell
python -m pytest tests/test_agentbus_self_review.py tests/test_agentbus_user_e2e.py tests/benchmark/test_agentbus_competitive_wedge.py -q
```

4. Run router tests:

```powershell
python -m pytest tests/test_agent_router_bridge_tasks.py tests/test_dual_agent_pair_benchmark.py tests/test_build_external_poly_coding_sft.py -q
```

5. Dispatch branch router smokes with `publish=false`.
6. Merge to `main` only after conflicts are resolved.
7. Confirm Vercel health advertises the full task list.

