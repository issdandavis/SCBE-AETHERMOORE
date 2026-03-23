# Lightweight Authorize Gateway

This gateway is a minimal Express service that wraps the `UnifiedKernel` decision flow from `src/ai_brain/unified-kernel.ts` and exposes `POST /authorize`.

## Runtime Behavior

- Startup validates required governance variables and **fails closed** if missing:
  - `GOVERNANCE_POLICY_ID`
  - `GOVERNANCE_ISSUER`
  - `GOVERNANCE_TOKEN`
- Startup diagnostics redact token material.
- Decision mapping:
  - `ALLOW` -> `ALLOW`
  - `TRANSFORM` -> `QUARANTINE`
  - `BLOCK` -> `DENY`

## Local profile

```bash
docker compose -f docker-compose.gateway.local.yml --profile gateway-local up --build
```

## Production profile

```bash
docker compose -f deploy/gateway/docker-compose.gateway.prod.yml up --build -d
```


The production compose file enforces required governance variables at compose-evaluation time.

### Port override behavior

`decision-gateway` now binds host/container ports from the same `PORT` value:

- Default mapping: `8081:8081`
- Override mapping: set `PORT` and Compose maps `${PORT}:${PORT}` (for example `PORT=9090` gives `9090:9090`).

The container runtime, startup command, and Docker healthcheck all read the same `PORT` value, so the service and `/health` probe stay aligned when the port is overridden.
