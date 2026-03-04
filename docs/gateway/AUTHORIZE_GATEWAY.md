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
