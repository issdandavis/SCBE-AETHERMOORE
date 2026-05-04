# SCBE Encore Infrastructure Seed

This folder bootstraps an Encore.ts app with a `metrics` service and core infrastructure declarations:

- `SQLDatabase`: `scbe-metrics`
- `Topic` + `Subscription`: `metrics-events`
- `CronJob`: `metrics-cleanup-hourly`
- `CacheCluster` + `IntKeyspace`: source metric counters
- `Bucket`: `scbe-metrics-archive`
- `secret()`: `SCBEThirdPartyApiKey`

Applied production hardening:
- at-least-once Pub/Sub consumer is idempotent (`event_id` unique + `ON CONFLICT DO NOTHING`)
- optional request-level `idempotencyKey` on `/metrics/ingest`
- retention cleanup endpoint on hourly cron

## Run locally

1. Install Encore CLI and authenticate.
2. From this folder run:

```bash
encore run
```

## Set secret (dev)

```bash
encore secret set --dev SCBEThirdPartyApiKey
```
