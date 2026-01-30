# Metrics & Telemetry

## Overview
The metrics module currently supports a **stdout** backend only. If you set any other backend (`datadog`, `prom`, or `otlp`), the runtime will log a warning once and drop metrics until an exporter is implemented. This makes runtime behavior explicit and avoids silent failures.

## Configuration

### Common
- `SCBE_METRICS_BACKEND` (default: `stdout`)
  - `stdout`: logs metrics to stdout.
  - `datadog`: **not yet implemented** (warning + drop).
  - `prom`: **not yet implemented** (warning + drop).
  - `otlp`: **not yet implemented** (warning + drop).

### Datadog (planned)
> Not currently wired. These are reserved for future use.

- `SCBE_METRICS_DATADOG_ENDPOINT` (default: `http://localhost:8126`)
- `SCBE_METRICS_DATADOG_API_KEY` (if using a hosted endpoint)

### Prometheus (planned)
> Not currently wired. These are reserved for future use.

- `SCBE_METRICS_PROM_ENDPOINT` (default: `http://localhost:9091/metrics/job/scbe-aethermoore` for a Pushgateway)

### OTLP (planned)
> Not currently wired. These are reserved for future use.

- `SCBE_METRICS_OTLP_ENDPOINT` (default: `http://localhost:4318/v1/metrics`)
- `SCBE_METRICS_OTLP_HEADERS` (comma-separated `key=value` pairs)
- `SCBE_METRICS_OTLP_AUTH` (optional auth token; if set, typically sent as `Authorization: Bearer <token>`)

## Example
```bash
export SCBE_METRICS_BACKEND=stdout
node your-app.js
```

If you set `SCBE_METRICS_BACKEND=datadog` (or `prom` / `otlp`), you should expect a warning similar to:
```
[metrics] Backend 'datadog' is configured but not implemented. Metrics will be dropped.
```
