# SCBE API and Tunnel Agent Handoff - 2026-05-31

Purpose: give the next local agent a current, tested map of the SCBE API, Cloudflare tunnel, authentication fix, and known degraded lanes.

## Current Runtime State

- Working directory: `C:\Users\issda\SCBE-AETHERMOORE`
- Main API: `src.api.main:app` on `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Cloudflare tunnel: `scbe-billing`
- Cloudflare metrics: `http://127.0.0.1:20241/metrics`
- Tunnel protocol observed: QUIC
- Tunnel health observed: 4 HA connections, 0 request errors
- Core API smoke observed: `GET /health` returns `status=healthy`

## Authentication Fix

The local API was rejecting authenticated endpoints because `SCBE_API_KEYS` was set in colon format:

```powershell
$env:SCBE_API_KEYS='scbe_<local-key>:local'
```

That is invalid for the current `src.api.auth_config` loader. Use JSON object format instead:

```powershell
$env:SCBE_ENV='production'
$env:SCBE_API_KEYS='{"scbe_<local-key>":"local"}'
python -m uvicorn src.api.main:app --reload --port 8000
```

Do not commit local API keys. Keep the real key in the operator shell, local environment manager, or a private machine-local config.

For authenticated smoke checks:

```powershell
$headers = @{ 'x-api-key' = $env:SCBE_LOCAL_API_KEY }
Invoke-RestMethod -Uri 'http://localhost:8000/metrics' -Headers $headers
```

## Smoke Commands

Core API:

```powershell
Invoke-RestMethod -Uri 'http://localhost:8000/health'
```

Authenticated metrics:

```powershell
$headers = @{ 'x-api-key' = $env:SCBE_LOCAL_API_KEY }
Invoke-RestMethod -Uri 'http://localhost:8000/metrics' -Headers $headers
```

HYDRA status:

```powershell
$headers = @{ 'x-api-key' = $env:SCBE_LOCAL_API_KEY }
Invoke-RestMethod -Uri 'http://localhost:8000/hydra/status' -Headers $headers
```

Expected result today: HTTP 500 until HYDRA spine initialization is fixed.

Cloudflare tunnel:

```powershell
Invoke-WebRequest -Uri 'http://127.0.0.1:20241/metrics' |
  Select-String -Pattern 'cloudflared_tunnel_ha_connections|cloudflared_tunnel_request_errors'
```

Expected healthy indicators:

- `cloudflared_tunnel_ha_connections 4`
- `cloudflared_tunnel_request_errors 0`

## Known Degraded or Optional Lanes

HYDRA:

- Startup log observed: `[HYDRA-API] Spine initialization failed (non-fatal)`
- Auth is no longer the blocker for HYDRA status.
- `/hydra/status` reaches the authenticated handler and returns 500.
- Next debug step: call the HYDRA spine initialization path with traceback enabled, then isolate the missing import, config, or runtime dependency.

Operation panel / system cards:

- Startup log observed: `src.contracts not available - operation panel / system cards endpoints disabled`
- Treat this as optional lane degradation unless the task explicitly needs operation panel/system card endpoints.

Postgres Lite:

- `/health` reports `postgres_lite.configured=false`.
- This is not a core API blocker for the current tunnel/API smoke.

## Agent Rules

- Do not store or commit real API keys.
- Prefer environment variables for local secrets.
- Keep HYDRA spine repair separate from tunnel/auth repair.
- Treat tunnel health, API auth, and HYDRA spine as three independent layers:
  - tunnel can be healthy while API auth is bad;
  - API auth can be fixed while HYDRA is degraded;
  - HYDRA degradation does not invalidate core `/health` or `/metrics`.

