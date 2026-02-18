# AetherBrowse Governance Contract

This defines browser execution governance for the SCBE execution plane.

## Risk Tiers

- `REFLEX`: read-style actions (`navigate`, `screenshot`, `extract`, `scroll`)
- `DELIBERATION`: write/act actions (`click`, `type`) or any job explicitly marked `risk_tier=DELIBERATION`

## Capability Gate

- `REFLEX`: capability token not required
- `DELIBERATION`: requires `capability_token` in job payload
- Missing token at DELIBERATION tier blocks execution before any remote call

## Verification Scoring

Per job score comes from deterministic checks:

- action success checks
- `verify.must_contain` string checks
- `verify.selectors_present` checks
- `verify.max_redirects` check

Decision mapping:

- `score >= 0.90` and capability valid -> `ALLOW`
- `0.60 <= score < 0.90` and capability valid -> `QUARANTINE`
- `score < 0.60` -> `DENY` (or `NOISE` when runner uses `--noise-on-deny`)
- capability invalid -> `DENY`/`NOISE`

## DecisionRecord

Each job emits a DecisionRecord at:

- `artifacts/aetherbrowse_runs/<run_id>/decision_records/<job_id>.json`

Each job also emits a trace payload:

- `artifacts/aetherbrowse_runs/<run_id>/traces/<job_id>.json`

Each trace generates deterministic `trace_hash` (sha256 over canonical JSON).

## Screenshot Hashes

Runner emits `screenshot_hashes` per job. If raw image bytes are available, hash is over image bytes. If API returns truncated base64, hash is over the returned base64 string.

## Replay

Given a DecisionRecord + trace file:

1. recompute `trace_hash` from the trace JSON
2. compare with DecisionRecord `trace_hash`
3. re-run verification checks from trace response payload
4. verify resulting score maps to stored decision

## One-Command Autopilot

Local service + swarm run (starts and stops service automatically):

```powershell
.\scripts\run_aetherbrowse_autopilot.ps1
```

Cloud endpoint mode (no local service):

```powershell
.\scripts\run_aetherbrowse_autopilot.ps1 `
  -UseLocalService:$false `
  -EndpointUrl "https://<cloud-run-host>/v1/integrations/n8n/browse" `
  -ApiKey "<scbe-browser-api-key>"
```
