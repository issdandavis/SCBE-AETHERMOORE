# SCBE 24x7 Agent Operations

## Scope
This runbook defines a practical path for continuous agent runtime plus continuous development.

It covers:
- merge conflict containment for active PR work,
- local 24x7 operations on Windows via n8n + bridge + browser watchdog,
- cloud path for true always-on runtime,
- development lanes that keep shipping velocity without breaking core services.

## Current Merge Status
- PR: `https://github.com/issdandavis/SCBE-AETHERMOORE/pull/293`
- Head branch: `codex/implement-gateway-service-with-/authorize-endpoint`
- Status after fix: `mergeable = MERGEABLE`
- Conflict files resolved:
  - `Dockerfile.gateway`
  - `package.json`

## Local 24x7 Runtime (Windows)
Use isolated service ports to avoid collisions with legacy local processes:
- n8n: `5680`
- n8n task broker: `5681`
- bridge: `8002`
- browser agent: `8012`
- OpenClaw Gateway: `18789`
- OpenClaw Bridge: `18790`
- user folder: `.n8n_local_iso`

### Start stack once
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\system\bootstrap_openclaw_sources.ps1

# first run / repair
powershell -NoProfile -ExecutionPolicy Bypass -File workflows\n8n\start_n8n_local.ps1 `
  -ProjectRoot C:\Users\issda\SCBE-AETHERMOORE `
  -N8nUserFolder C:\Users\issda\SCBE-AETHERMOORE\.n8n_local_iso `
  -BridgePort 8002 -BrowserPort 8012 -N8nPort 5680 -N8nTaskBrokerPort 5681 `
  -StartBrowserAgent `
  -StartOpenClaw `
  -OpenClawGatewayPort 18789 `
  -OpenClawBridgePort 18790
```

### Register background auto-start + watchdog
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\system\register_agent_stack_tasks.ps1 `
  -ProjectRoot C:\Users\issda\SCBE-AETHERMOORE `
  -N8nUserFolder C:\Users\issda\SCBE-AETHERMOORE\.n8n_local_iso `
  -BridgePort 8002 -BrowserPort 8012 -N8nPort 5680 -N8nTaskBrokerPort 5681 `
  -StartOpenClaw `
  -OpenClawGatewayPort 18789 `
  -OpenClawBridgePort 18790 `
  -WatchdogMinutes 5
```

### Manual watchdog run
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\system\watchdog_agent_stack.ps1 `
  -ProjectRoot C:\Users\issda\SCBE-AETHERMOORE `
  -N8nUserFolder C:\Users\issda\SCBE-AETHERMOORE\.n8n_local_iso `
  -BridgePort 8002 -BrowserPort 8012 -N8nPort 5680 -N8nTaskBrokerPort 5681 `
  -StartOpenClaw -OpenClawGatewayPort 18789 -OpenClawBridgePort 18790
```

Optional OpenClaw env overrides (before startup):
```powershell
$env:OPENCLAW_CONFIG_DIR = "$env:USERPROFILE\\.openclaw"
$env:OPENCLAW_WORKSPACE_DIR = "$env:OPENCLAW_CONFIG_DIR\\workspace"
$env:OPENCLAW_GATEWAY_TOKEN = "replace-with-strong-token"
```

### Telegram incident alerts (recommended)
Set these once in your shell profile or system environment:
```powershell
$env:SCBE_TELEGRAM_BOT_TOKEN = "123456:telegram-bot-token"
$env:SCBE_TELEGRAM_CHAT_ID = "123456789"
```

Then run watchdog normally. On restart/failure events it will send Telegram alerts:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\system\watchdog_agent_stack.ps1 `
  -ProjectRoot C:\Users\issda\SCBE-AETHERMOORE `
  -N8nUserFolder C:\Users\issda\SCBE-AETHERMOORE\.n8n_local_iso `
  -BridgePort 8002 -BrowserPort 8012 -N8nPort 5680 -N8nTaskBrokerPort 5681 `
  -StartOpenClaw -OpenClawGatewayPort 18789 -OpenClawBridgePort 18790
```

## Cloud 24x7 Runtime (Production)
For true 24x7 (even when the workstation is off), move runtime to managed infra:
1. Containerize bridge + browser agent + queue worker.
2. Run them on Cloud Run / GKE / Fly.io / Railway with health probes.
3. Persist queue and state outside local disk (managed Postgres/Redis).
4. Keep n8n in dedicated instance with protected webhook ingress.
5. Wire uptime checks and alerting (Slack/Telegram/email).

## Development Lanes (Avoid Blocking Runtime)
Use two lanes:
- Lane A (ops): stable branch + hotfix only for runtime scripts and service health.
- Lane B (dev): feature branches + PR gates + merge queue.

Controls:
1. Keep conflict marker guard enabled in CI.
2. Keep smoke test gate on every PR:
   - bridge health
   - browser health
   - n8n webhook execution
3. Keep `main` rebases frequent for long-lived feature branches.
4. Use isolated worktrees for merge resolution to avoid dirty local workspace collisions.

## Minimal SLOs
- Service availability:
  - bridge >= 99.0%
  - browser agent >= 99.0%
  - n8n webhook trigger success >= 99.0%
- Recovery:
  - automated watchdog restart within 5 minutes
- Data:
  - zero dropped queue events after restart

## Next Operational Step
After registering tasks, validate with:
```powershell
schtasks /Query /TN SCBE-AgentStack-Boot /FO LIST
schtasks /Query /TN SCBE-AgentStack-Watchdog /FO LIST
```
