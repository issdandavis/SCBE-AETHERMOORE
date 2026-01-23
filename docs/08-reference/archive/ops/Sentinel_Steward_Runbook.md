# Sentinel & Steward Loop — Ops Runbook (SCBE Edition)

Purpose

- Gate and verify every envelope with adaptive dwell + explainable risk signals.
- Steward lane handles review; Sentinel automates fast-path.

Daily Checklist

1. Review `gcm_failures`, `nonce_reuse`, `replay_rejects`, `aad_mismatch`.
2. p95/p99 `envelope_create_ms` and `envelope_verify_ms` within targets (<10ms / <25ms).
3. Phase skew p99 < 2000ms across providers.
4. Verify canary flags and circuit-breakers (no unintended trips).
5. Audit 5 random ALLOW decisions (attest reasonability).
6. Export yesterday’s metrics and lock/audit.

Escalations

- Sev2: review queue SLA breach or sustained `review` > 10% for 10m.
- Sev1: any nonce reuse or GCM auth failure rate > 0.5% for 5m.
